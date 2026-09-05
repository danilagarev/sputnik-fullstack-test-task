"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAlerts } from "@/entities/alert/api";
import { hasPendingWork } from "@/entities/file/model";
import { useFiles } from "@/entities/file/api";
import { alertsKey } from "@/shared/api/keys";
import { AlertsTable } from "@/widgets/alerts-table/ui/AlertsTable";
import { DashboardHeader } from "@/widgets/dashboard-header/ui/DashboardHeader";
import { FilesTable } from "@/widgets/files-table/ui/FilesTable";

/**
 * The one place that knows both entities.
 *
 * Files and alerts are fetched here and handed down, so the two tables stay
 * presentational and neither entity has to reach into the other's cache to
 * find out whether processing is still running.
 */
export function Dashboard() {
  const files = useFiles();
  const processing = hasPendingWork(files.data ?? []);
  const alerts = useAlerts(processing);

  // The alert is written in the same transaction as the terminal status, so
  // the moment the last file settles is the moment it appears — and also the
  // moment polling stops. One more read on that edge is what keeps the feed
  // from missing exactly the alert it was waiting for.
  const client = useQueryClient();
  useEffect(() => {
    if (!processing) {
      client.invalidateQueries({ queryKey: alertsKey });
    }
  }, [processing, client]);

  return (
    <>
      <DashboardHeader />
      <FilesTable
        files={files.data ?? []}
        isPending={files.isPending}
        isFetching={files.isFetching}
        error={files.error}
        processing={processing}
      />
      <AlertsTable
        alerts={alerts.data ?? []}
        isPending={alerts.isPending}
        isFetching={alerts.isFetching}
        error={alerts.error}
      />
    </>
  );
}
