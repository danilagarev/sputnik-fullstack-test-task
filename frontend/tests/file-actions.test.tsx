import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { FileItem } from "@/entities/file/model";
import { DeleteFileButton } from "@/features/delete-file/ui/DeleteFileButton";
import { RenameFileButton } from "@/features/rename-file/ui/RenameFileButton";

const file: FileItem = {
  id: "11111111-1111-1111-1111-111111111111",
  title: "Договор",
  original_name: "contract.txt",
  mime_type: "text/plain",
  size: 12,
  processing_status: "processed",
  scan_status: "clean",
  scan_details: "no threats found",
  metadata_json: null,
  requires_attention: false,
  created_at: "2026-09-03T10:00:00Z",
  updated_at: "2026-09-03T10:00:00Z",
};

function renderWithClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function respond(status: number, body: unknown) {
  return vi.fn(
    async () =>
      new Response(status === 204 ? null : JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" },
      }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RenameFileButton", () => {
  it("patches the title the user typed", async () => {
    const fetchMock = respond(200, { ...file, title: "Новый договор" });
    vi.stubGlobal("fetch", fetchMock);
    renderWithClient(<RenameFileButton file={file} />);

    await userEvent.click(screen.getByRole("button", { name: "Переименовать" }));
    const input = screen.getByLabelText("Название файла");
    await userEvent.clear(input);
    await userEvent.type(input, "Новый договор");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [path, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe(`http://localhost:8000/files/${file.id}`);
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ title: "Новый договор" }));
  });

  it("shows the API's own reason for a refusal", async () => {
    vi.stubGlobal("fetch", respond(400, { detail: "Value is too long" }));
    renderWithClient(<RenameFileButton file={file} />);

    await userEvent.click(screen.getByRole("button", { name: "Переименовать" }));
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("Value is too long")).toBeInTheDocument();
  });
});

describe("DeleteFileButton", () => {
  it("asks before deleting, then deletes", async () => {
    const fetchMock = respond(204, null);
    vi.stubGlobal("fetch", fetchMock);
    renderWithClient(<DeleteFileButton file={file} />);

    await userEvent.click(screen.getByRole("button", { name: "Удалить" }));
    expect(fetchMock).not.toHaveBeenCalled();

    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Удалить" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [path, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe(`http://localhost:8000/files/${file.id}`);
    expect(init.method).toBe("DELETE");
  });
});
