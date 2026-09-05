"use client";

import { Alert, Badge, Card, Spinner, Table } from "react-bootstrap";

import { downloadUrl } from "@/entities/file/api";
import {
  processingVariant,
  scanLabel,
  scanVariant,
  type FileItem,
} from "@/entities/file/model";
import { DeleteFileButton } from "@/features/delete-file/ui/DeleteFileButton";
import { RenameFileButton } from "@/features/rename-file/ui/RenameFileButton";
import { formatDate, formatSize } from "@/shared/lib/format";

type Props = {
  files: readonly FileItem[];
  isPending: boolean;
  isFetching: boolean;
  error: Error | null;
  processing: boolean;
};

export function FilesTable({ files, isPending, isFetching, error, processing }: Props) {
  return (
    <Card className="shadow-sm border-0 mb-4">
      <Card.Header className="bg-white border-0 pt-4 px-4">
        <div className="d-flex justify-content-between align-items-center gap-2">
          <h2 className="h5 mb-0">Файлы</h2>
          <div className="d-flex align-items-center gap-2">
            {processing ? (
              <span className="small text-secondary d-flex align-items-center gap-2">
                <Spinner animation="border" size="sm" /> обработка…
              </span>
            ) : null}
            <Badge bg="secondary">{files.length}</Badge>
          </div>
        </div>
      </Card.Header>
      <Card.Body className="px-4 pb-4">
        {error ? (
          <Alert variant="danger" className="mb-3">
            {error.message}
          </Alert>
        ) : null}

        {isPending ? (
          <div className="d-flex justify-content-center py-5">
            <Spinner animation="border" />
          </div>
        ) : (
          // Kept mounted while refetching: the old version swapped the whole
          // table for a spinner on every refresh.
          <div className="table-responsive" aria-busy={isFetching}>
            <Table hover bordered className="align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>Название</th>
                  <th>Файл</th>
                  <th>MIME</th>
                  <th>Размер</th>
                  <th>Статус</th>
                  <th>Проверка</th>
                  <th>Создан</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {files.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-4 text-secondary">
                      Файлы пока не загружены
                    </td>
                  </tr>
                ) : (
                  files.map((file) => (
                    <tr key={file.id}>
                      <td>
                        <div className="fw-semibold">{file.title}</div>
                        <div className="small text-secondary font-monospace">{file.id}</div>
                      </td>
                      <td>{file.original_name}</td>
                      <td className="small">{file.mime_type}</td>
                      <td className="text-nowrap">{formatSize(file.size)}</td>
                      <td>
                        <Badge bg={processingVariant(file.processing_status)}>
                          {file.processing_status}
                        </Badge>
                      </td>
                      <td>
                        <div className="d-flex flex-column gap-1">
                          <Badge bg={scanVariant(file)}>{scanLabel(file)}</Badge>
                          <span className="small text-secondary">
                            {file.scan_details ?? "Ожидает обработки"}
                          </span>
                        </div>
                      </td>
                      <td className="text-nowrap">{formatDate(file.created_at)}</td>
                      <td>
                        <div className="d-flex gap-2 justify-content-end">
                          <a href={downloadUrl(file.id)} className="btn btn-outline-primary btn-sm">
                            Скачать
                          </a>
                          <RenameFileButton file={file} />
                          <DeleteFileButton file={file} />
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </Table>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}
