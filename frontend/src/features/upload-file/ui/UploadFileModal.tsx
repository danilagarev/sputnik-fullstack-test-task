"use client";

import { useState, type FormEvent } from "react";
import { Alert, Button, Form, Modal } from "react-bootstrap";

import { useUploadFile } from "@/entities/file/api";
import { formatSize } from "@/shared/lib/format";

type Props = {
  show: boolean;
  onHide: () => void;
};

export function UploadFileModal({ show, onHide }: Props) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const upload = useUploadFile();

  function reset() {
    setTitle("");
    setFile(null);
    setValidationError(null);
    upload.reset();
  }

  function close() {
    reset();
    onHide();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);

    if (!title.trim() || !file) {
      setValidationError("Укажите название и выберите файл");
      return;
    }
    if (file.size === 0) {
      setValidationError("Файл пустой");
      return;
    }

    try {
      await upload.mutateAsync({ title: title.trim(), file });
      close();
    } catch {
      // Reported below from the mutation's own error state.
    }
  }

  // The upload's own error stays inside this dialog rather than sharing one
  // banner with the file list, where the two used to overwrite each other.
  const message = validationError ?? upload.error?.message ?? null;

  return (
    <Modal show={show} onHide={close} centered>
      <Form onSubmit={handleSubmit}>
        <Modal.Header closeButton>
          <Modal.Title>Добавить файл</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {message ? (
            <Alert variant="danger" className="py-2">
              {message}
            </Alert>
          ) : null}
          <Form.Group className="mb-3" controlId="upload-title">
            <Form.Label>Название</Form.Label>
            <Form.Control
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Например, Договор с подрядчиком"
            />
          </Form.Group>
          <Form.Group controlId="upload-file">
            <Form.Label>Файл</Form.Label>
            <Form.Control
              type="file"
              onChange={(event) =>
                setFile((event.target as HTMLInputElement).files?.[0] ?? null)
              }
            />
            {file ? (
              <Form.Text className="text-secondary">{formatSize(file.size)}</Form.Text>
            ) : null}
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={close}>
            Отмена
          </Button>
          <Button type="submit" variant="primary" disabled={upload.isPending}>
            {upload.isPending ? "Загрузка…" : "Сохранить"}
          </Button>
        </Modal.Footer>
      </Form>
    </Modal>
  );
}
