"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Card } from "react-bootstrap";

import { alertsKey, filesKey } from "@/shared/api/keys";
import { UploadFileModal } from "@/features/upload-file/ui/UploadFileModal";

export function DashboardHeader() {
  const [showUpload, setShowUpload] = useState(false);
  const client = useQueryClient();

  function refresh() {
    client.invalidateQueries({ queryKey: filesKey });
    client.invalidateQueries({ queryKey: alertsKey });
  }

  return (
    <>
      <Card className="shadow-sm border-0 mb-4">
        <Card.Body className="p-4">
          <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap">
            <div>
              <h1 className="h3 mb-2">Управление файлами</h1>
              <p className="text-secondary mb-0">
                Загрузка файлов, просмотр статусов обработки и ленты алертов.
                Статусы обновляются сами, пока обработка не завершится.
              </p>
            </div>
            <div className="d-flex gap-2">
              <Button variant="outline-secondary" onClick={refresh}>
                Обновить
              </Button>
              <Button variant="primary" onClick={() => setShowUpload(true)}>
                Добавить файл
              </Button>
            </div>
          </div>
        </Card.Body>
      </Card>

      <UploadFileModal show={showUpload} onHide={() => setShowUpload(false)} />
    </>
  );
}
