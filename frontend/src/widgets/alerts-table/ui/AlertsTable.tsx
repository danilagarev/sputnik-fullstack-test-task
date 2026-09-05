"use client";

import { Alert, Badge, Card, Spinner, Table } from "react-bootstrap";

import { levelVariant, type AlertItem } from "@/entities/alert/model";
import { formatDate } from "@/shared/lib/format";

type Props = {
  alerts: readonly AlertItem[];
  isPending: boolean;
  isFetching: boolean;
  error: Error | null;
};

export function AlertsTable({ alerts, isPending, isFetching, error }: Props) {
  return (
    <Card className="shadow-sm border-0">
      <Card.Header className="bg-white border-0 pt-4 px-4">
        <div className="d-flex justify-content-between align-items-center">
          <h2 className="h5 mb-0">Алерты</h2>
          <Badge bg="secondary">{alerts.length}</Badge>
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
          <div className="table-responsive" aria-busy={isFetching}>
            <Table hover bordered className="align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>ID</th>
                  <th>File ID</th>
                  <th>Уровень</th>
                  <th>Сообщение</th>
                  <th>Создан</th>
                </tr>
              </thead>
              <tbody>
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center py-4 text-secondary">
                      Алертов пока нет
                    </td>
                  </tr>
                ) : (
                  alerts.map((item) => (
                    <tr key={item.id}>
                      <td>{item.id}</td>
                      <td className="small font-monospace">{item.file_id}</td>
                      <td>
                        <Badge bg={levelVariant(item.level)}>{item.level}</Badge>
                      </td>
                      <td>{item.message}</td>
                      <td className="text-nowrap">{formatDate(item.created_at)}</td>
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
