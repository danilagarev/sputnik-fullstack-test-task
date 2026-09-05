import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AlertItem } from "@/entities/alert/model";
import { AlertsTable } from "@/widgets/alerts-table/ui/AlertsTable";

function alert(overrides: Partial<AlertItem> = {}): AlertItem {
  return {
    id: 1,
    file_id: "11111111-1111-1111-1111-111111111111",
    level: "info",
    message: "File processed successfully",
    created_at: "2026-09-03T10:00:00Z",
    ...overrides,
  };
}

function renderTable(alerts: AlertItem[], overrides = {}) {
  return render(
    <AlertsTable
      alerts={alerts}
      isPending={false}
      isFetching={false}
      error={null}
      {...overrides}
    />,
  );
}

describe("AlertsTable", () => {
  it("says so when the feed is empty", () => {
    renderTable([]);

    expect(screen.getByText("Алертов пока нет")).toBeInTheDocument();
  });

  it("renders an alert with its level and message", () => {
    renderTable([alert({ level: "warning", message: "File requires attention: .exe" })]);

    const row = screen.getByText("File requires attention: .exe").closest("tr")!;
    expect(within(row).getByText("warning")).toBeInTheDocument();
    expect(within(row).getByText("03.09.2026, 13:00")).toBeInTheDocument();
  });

  it("keeps the feed on screen while it refetches", () => {
    renderTable([alert()], { isFetching: true });

    expect(screen.getByText("File processed successfully")).toBeInTheDocument();
  });
});
