import { Col, Container, Row } from "react-bootstrap";

import { Dashboard } from "@/widgets/dashboard/ui/Dashboard";

/**
 * Composition only.
 *
 * This file used to be 367 lines holding the types, the formatters, the fetch
 * calls, a hardcoded http://localhost:8000, all of the state and the markup.
 */
export default function Page() {
  return (
    <Container fluid className="py-4 px-4 bg-light min-vh-100">
      <Row className="justify-content-center">
        <Col xxl={10} xl={11}>
          <Dashboard />
        </Col>
      </Row>
    </Container>
  );
}
