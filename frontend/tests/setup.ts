import "@testing-library/jest-dom/vitest";

// formatDate renders in the viewer's timezone. That is correct behaviour and
// impossible to assert against unless the suite pins one.
process.env.TZ = "Europe/Moscow";
