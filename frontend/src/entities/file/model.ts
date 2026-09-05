/** The file entity: its shape, its states, and how those states are shown. */

export type ProcessingStatus = "uploaded" | "processing" | "processed" | "failed";
export type ScanStatus = "clean" | "suspicious" | "failed";

export type FileItem = {
  id: string;
  title: string;
  original_name: string;
  mime_type: string;
  size: number;
  processing_status: ProcessingStatus | string;
  scan_status: ScanStatus | string | null;
  scan_details: string | null;
  metadata_json: Record<string, unknown> | null;
  requires_attention: boolean;
  created_at: string;
  updated_at: string;
};

const TERMINAL: ReadonlySet<string> = new Set(["processed", "failed"]);

export function isSettled(file: FileItem): boolean {
  return TERMINAL.has(file.processing_status);
}

/** True while anything in the list is still moving through the pipeline. */
export function hasPendingWork(files: readonly FileItem[]): boolean {
  return files.some((file) => !isSettled(file));
}

export function processingVariant(status: string): string {
  switch (status) {
    case "failed":
      return "danger";
    case "processing":
      return "warning";
    case "processed":
      return "success";
    default:
      return "secondary";
  }
}

/**
 * The scan badge follows the scan verdict, not `requires_attention`.
 *
 * Colouring it by that flag alone showed a file as green — "clean" — before
 * anything had looked at it.
 */
export function scanVariant(file: FileItem): string {
  switch (file.scan_status) {
    case "clean":
      return "success";
    case "suspicious":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "secondary";
  }
}

export function scanLabel(file: FileItem): string {
  return file.scan_status ?? "ожидает проверки";
}
