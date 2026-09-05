/**
 * Client-side configuration.
 *
 * The API address is a variable rather than the hardcoded
 * `http://localhost:8000` that used to sit in the middle of the page
 * component; the default keeps `docker compose up` working with no extra
 * setup. `NEXT_PUBLIC_` because the browser calls the API directly, which is
 * what the backend's CORS list is for.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** How often to re-check while a file is still being processed. */
export const POLL_INTERVAL_MS = 2000;

/** How many rows to ask for. The API caps its own page size as well. */
export const PAGE_SIZE = 50;
