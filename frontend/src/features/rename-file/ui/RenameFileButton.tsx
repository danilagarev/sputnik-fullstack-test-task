"use client";

import { useState, type FormEvent } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";

import { useRenameFile } from "@/entities/file/api";
import type { FileItem } from "@/entities/file/model";

/** PATCH /files/{id} existed in the API but had no interface at all. */
export function RenameFileButton({ file }: { file: FileItem }) {
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState(file.title);
  const rename = useRenameFile();

  function open() {
    setTitle(file.title);
    rename.reset();
    setShow(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) {
      return;
    }
    try {
      await rename.mutateAsync({ id: file.id, title: title.trim() });
      setShow(false);
    } catch {
      // Shown in the dialog.
    }
  }

  return (
    <>
      <Button variant="outline-secondary" size="sm" onClick={open}>
        Переименовать
      </Button>
      <Modal show={show} onHide={() => setShow(false)} centered>
        <Form onSubmit={handleSubmit}>
          <Modal.Header closeButton>
            <Modal.Title>Переименовать файл</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {rename.error ? (
              <Alert variant="danger" className="py-2">
                {rename.error.message}
              </Alert>
            ) : null}
            <Form.Control
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              aria-label="Название файла"
            />
          </Modal.Body>
          <Modal.Footer>
            <Button variant="outline-secondary" onClick={() => setShow(false)}>
              Отмена
            </Button>
            <Button type="submit" variant="primary" disabled={rename.isPending}>
              Сохранить
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
}
