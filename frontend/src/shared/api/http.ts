/**
 * The single place that knows how to talk to the API.
 *
 * Every failure becomes an ApiError carrying the server's own `detail`, so the
 * interface can say "File is empty" instead of a generic "request failed".
 */

import { API_BASE, PAGE_SIZE } from "@/shared/config";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function toError(response: Response): Promise<ApiError> {
  let detail = `Запрос завершился с кодом ${response.status}`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      detail = body.detail;
    }
  } catch {
    // A non-JSON error body is not itself worth reporting.
  }
  return new ApiError(detail, response.status);
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });

  if (!response.ok) {
    throw await toError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/** A list request, with the page size the interface asks for. */
export function listPath(path: string): string {
  return `${path}?limit=${PAGE_SIZE}`;
}
