"use client";

import { useState } from "react";
import { Button, Modal } from "react-bootstrap";

import { useDeleteFile } from "@/entities/file/api";
import type { FileItem } from "@/entities/file/model";

/** DELETE /files/{id} existed in the API but had no interface either. */
export function DeleteFileButton({ file }: { file: FileItem }) {
  const [show, setShow] = useState(false);
  const remove = useDeleteFile();

  async function confirm() {
    try {
      await remove.mutateAsync(file.id);
      setShow(false);
    } catch {
      // Shown in the dialog.
    }
  }

  return (
    <>
      <Button variant="outline-danger" size="sm" onClick={() => setShow(true)}>
        Удалить
      </Button>
      <Modal show={show} onHide={() => setShow(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Удалить файл</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p className="mb-0">
            «{file.title}» и связанные с ним алерты будут удалены безвозвратно.
          </p>
          {remove.error ? (
            <p className="text-danger mt-3 mb-0">{remove.error.message}</p>
          ) : null}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setShow(false)}>
            Отмена
          </Button>
          <Button variant="danger" onClick={confirm} disabled={remove.isPending}>
            {remove.isPending ? "Удаление…" : "Удалить"}
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
