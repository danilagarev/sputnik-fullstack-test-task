/**
 * Presentation helpers.
 *
 * The date formatter is built once at module level: it used to be constructed
 * inside the render path, so every cell of both tables allocated its own
 * Intl.DateTimeFormat on every render.
 */

const dateFormatter = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "short",
  timeStyle: "short",
});

export function formatDate(value: string): string {
  return dateFormatter.format(new Date(value));
}

export function formatSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  if (size < 1024 * 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}
