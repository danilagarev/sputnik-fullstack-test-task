import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { UploadFileModal } from "@/features/upload-file/ui/UploadFileModal";

const GIGABYTE = 1024 * 1024 * 1024;

function renderModal({ onHide = () => {} } = {}) {
  function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return render(<UploadFileModal show onHide={onHide} />, { wrapper });
}

/** A File of a given size without allocating one. */
function sized(name: string, size: number): File {
  const file = new File(["x"], name, { type: "text/plain" });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

async function fill(title: string, file: File | null) {
  if (title) {
    await userEvent.type(screen.getByLabelText("Название"), title);
  }
  if (file) {
    await userEvent.upload(screen.getByLabelText("Файл"), file);
  }
  await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));
}

function respond(status: number, body: unknown) {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", respond(201, { id: "1" }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("UploadFileModal", () => {
  it("refuses to send a form with no title and no file", async () => {
    const fetchMock = respond(201, {});
    vi.stubGlobal("fetch", fetchMock);
    renderModal();

    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("Укажите название и выберите файл")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refuses an empty file before sending it", async () => {
    const fetchMock = respond(201, {});
    vi.stubGlobal("fetch", fetchMock);
    renderModal();

    await fill("Пустой", sized("empty.txt", 0));

    expect(await screen.findByText("Файл пустой")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the API's own answer for a file past its limit", async () => {
    const fetchMock = respond(413, { detail: "File is too large" });
    vi.stubGlobal("fetch", fetchMock);
    renderModal();

    await fill("Большой", sized("big.bin", GIGABYTE * 4));

    expect(fetchMock).toHaveBeenCalled();
    expect(await screen.findByText("File is too large")).toBeInTheDocument();
  });

  it("shows the server's own detail rather than a generic failure", async () => {
    // The original threw `detail` away and always printed the same string.
    vi.stubGlobal("fetch", respond(400, { detail: "Value is too long" }));
    renderModal();

    await fill("Заголовок", sized("notes.txt", 12));

    expect(await screen.findByText("Value is too long")).toBeInTheDocument();
  });

  it("closes on success and does not report an error", async () => {
    const onHide = vi.fn();
    renderModal({ onHide });

    await fill("Договор", sized("contract.txt", 12));

    await waitFor(() => expect(onHide).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("sends the title trimmed, as multipart, to the files endpoint", async () => {
    const fetchMock = respond(201, { id: "1" });
    vi.stubGlobal("fetch", fetchMock);
    renderModal();

    await fill("   Договор   ", sized("contract.txt", 12));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [path, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe("http://localhost:8000/files");
    expect(init.method).toBe("POST");
    const body = init.body as FormData;
    expect(body.get("title")).toBe("Договор");
    expect((body.get("file") as File).name).toBe("contract.txt");
  });

  it("does not carry a failed attempt's error into the next one", async () => {
    vi.stubGlobal("fetch", respond(400, { detail: "Value is too long" }));
    renderModal();

    await fill("Заголовок", sized("notes.txt", 12));
    await screen.findByText("Value is too long");

    await userEvent.click(screen.getByRole("button", { name: "Отмена" }));

    expect(screen.queryByText("Value is too long")).not.toBeInTheDocument();
  });
});
