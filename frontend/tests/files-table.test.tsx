import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { FileItem } from "@/entities/file/model";
import { FilesTable } from "@/widgets/files-table/ui/FilesTable";

function file(overrides: Partial<FileItem> = {}): FileItem {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Договор",
    original_name: "contract.txt",
    mime_type: "text/plain",
    size: 2048,
    processing_status: "uploaded",
    scan_status: null,
    scan_details: null,
    metadata_json: null,
    requires_attention: false,
    created_at: "2026-09-03T10:00:00Z",
    updated_at: "2026-09-03T10:00:00Z",
    ...overrides,
  };
}

function renderTable(files: FileItem[], overrides = {}) {
  function wrapper({ children }: { children: ReactNode }) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return render(
    <FilesTable
      files={files}
      isPending={false}
      isFetching={false}
      error={null}
      processing={false}
      {...overrides}
    />,
    { wrapper },
  );
}

describe("FilesTable", () => {
  it("says so when there is nothing to show", () => {
    renderTable([]);

    expect(screen.getByText("Файлы пока не загружены")).toBeInTheDocument();
  });

  it("renders a row per file with its size and verdict", () => {
    renderTable([file({ scan_status: "suspicious", scan_details: "suspicious extension .exe" })]);

    const row = screen.getByText("Договор").closest("tr")!;
    expect(within(row).getByText("2.0 KB")).toBeInTheDocument();
    expect(within(row).getByText("suspicious")).toBeInTheDocument();
    expect(within(row).getByText("suspicious extension .exe")).toBeInTheDocument();
  });

  it("offers a download link for every file", () => {
    renderTable([file()]);

    expect(screen.getByRole("link", { name: "Скачать" })).toHaveAttribute(
      "href",
      "http://localhost:8000/files/11111111-1111-1111-1111-111111111111/download",
    );
  });

  it("keeps the table on screen while it refetches", () => {
    // The original swapped the whole table for a spinner on every refresh.
    renderTable([file()], { isFetching: true });

    expect(screen.getByText("Договор")).toBeInTheDocument();
  });

  it("reports a failure without hiding what was already loaded", () => {
    renderTable([file()], { error: new Error("Не удалось загрузить данные") });

    expect(screen.getByText("Не удалось загрузить данные")).toBeInTheDocument();
    expect(screen.getByText("Договор")).toBeInTheDocument();
  });
});
