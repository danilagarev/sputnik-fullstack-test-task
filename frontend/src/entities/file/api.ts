"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listPath, request } from "@/shared/api/http";
import { alertsKey, filesKey } from "@/shared/api/keys";
import { API_BASE, POLL_INTERVAL_MS } from "@/shared/config";

import { hasPendingWork, type FileItem } from "./model";

export function downloadUrl(fileId: string): string {
  return `${API_BASE}/files/${fileId}/download`;
}

/**
 * The file list.
 *
 * Processing is asynchronous, so a file's status changes after the response
 * that created it: the list used to show "uploaded" until the user pressed
 * "Обновить". Polling runs only while something is still in flight.
 */
export function useFiles() {
  return useQuery({
    queryKey: filesKey,
    queryFn: ({ signal }) => request<FileItem[]>(listPath("/files"), { signal }),
    refetchInterval: (query) =>
      query.state.data && hasPendingWork(query.state.data) ? POLL_INTERVAL_MS : false,
  });
}

function useFileMutation<TArgs, TResult>(mutationFn: (args: TArgs) => Promise<TResult>) {
  const client = useQueryClient();

  return useMutation({
    mutationFn,
    // An upload ends in an alert and a delete takes its alerts with it, so
    // both lists are stale either way.
    onSuccess: () => {
      client.invalidateQueries({ queryKey: filesKey });
      client.invalidateQueries({ queryKey: alertsKey });
    },
  });
}

export function useUploadFile() {
  return useFileMutation(({ title, file }: { title: string; file: File }) => {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    return request<FileItem>("/files", { method: "POST", body: form });
  });
}

export function useRenameFile() {
  return useFileMutation(({ id, title }: { id: string; title: string }) =>
    request<FileItem>(`/files/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  );
}

export function useDeleteFile() {
  return useFileMutation((id: string) => request<void>(`/files/${id}`, { method: "DELETE" }));
}
