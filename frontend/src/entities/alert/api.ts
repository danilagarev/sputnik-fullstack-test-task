"use client";

import { useQuery } from "@tanstack/react-query";

import { listPath, request } from "@/shared/api/http";
import { alertsKey } from "@/shared/api/keys";
import { POLL_INTERVAL_MS } from "@/shared/config";

import type { AlertItem } from "./model";

/**
 * The alert feed.
 *
 * Whether anything is being processed is a parameter rather than something
 * read from the file entity here: slices in the same layer do not import each
 * other, so the dependency is stated in the signature and resolved one layer
 * up, in the widget that knows about both.
 */
export function useAlerts(processing: boolean) {
  return useQuery({
    queryKey: alertsKey,
    queryFn: ({ signal }) => request<AlertItem[]>(listPath("/alerts"), { signal }),
    refetchInterval: processing ? POLL_INTERVAL_MS : false,
  });
}
