import { describe, expect, it } from "vitest";

import { formatDate, formatSize } from "@/shared/lib/format";

describe("formatSize", () => {
  it.each([
    [0, "0 B"],
    [1023, "1023 B"],
    [1024, "1.0 KB"],
    [1024 * 1024 - 1, "1024.0 KB"],
    [1024 * 1024, "1.0 MB"],
    [1024 * 1024 * 1024, "1.0 GB"],
  ])("renders %i as %s", (size, expected) => {
    expect(formatSize(size)).toBe(expected);
  });

  it("no longer reports gigabytes as four-digit megabytes", () => {
    // The original stopped at MB, so a 5 GB upload read as "5120.0 MB".
    expect(formatSize(5 * 1024 * 1024 * 1024)).toBe("5.0 GB");
  });
});

describe("formatDate", () => {
  it("renders an ISO timestamp in ru-RU short form", () => {
    expect(formatDate("2026-09-03T18:06:29.691136Z")).toMatch(/^03\.09\.2026,? /);
  });
});
