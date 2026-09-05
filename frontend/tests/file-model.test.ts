import { describe, expect, it } from "vitest";

import {
  hasPendingWork,
  isSettled,
  processingVariant,
  scanLabel,
  scanVariant,
  type FileItem,
} from "@/entities/file/model";

function file(overrides: Partial<FileItem> = {}): FileItem {
  return {
    id: "id",
    title: "Файл",
    original_name: "notes.txt",
    mime_type: "text/plain",
    size: 10,
    processing_status: "uploaded",
    scan_status: null,
    scan_details: null,
    metadata_json: null,
    requires_attention: false,
    created_at: "2026-09-03T00:00:00Z",
    updated_at: "2026-09-03T00:00:00Z",
    ...overrides,
  };
}

describe("scan badge", () => {
  it("does not claim an unscanned file is clean", () => {
    // The bug this replaces: the colour came from requires_attention, which is
    // false before the scan has run, so a file nobody had looked at was green.
    const unscanned = file({ scan_status: null, requires_attention: false });

    expect(scanVariant(unscanned)).toBe("secondary");
    expect(scanLabel(unscanned)).toBe("ожидает проверки");
  });

  it.each([
    ["clean", "success"],
    ["suspicious", "warning"],
    ["failed", "danger"],
  ])("colours a %s verdict as %s", (status, variant) => {
    expect(scanVariant(file({ scan_status: status }))).toBe(variant);
  });
});

describe("processing state", () => {
  it.each([
    ["uploaded", false],
    ["processing", false],
    ["processed", true],
    ["failed", true],
  ])("treats %s as settled=%s", (status, settled) => {
    expect(isSettled(file({ processing_status: status }))).toBe(settled);
  });

  it("polls while anything is unfinished and stops when everything is done", () => {
    expect(hasPendingWork([file({ processing_status: "processed" })])).toBe(false);
    expect(
      hasPendingWork([file({ processing_status: "processed" }), file({ processing_status: "uploaded" })]),
    ).toBe(true);
  });

  it.each([
    ["failed", "danger"],
    ["processing", "warning"],
    ["processed", "success"],
    ["uploaded", "secondary"],
  ])("colours %s as %s", (status, variant) => {
    expect(processingVariant(status)).toBe(variant);
  });
});
