export type AlertLevel = "info" | "warning" | "critical";

export type AlertItem = {
  id: number;
  file_id: string;
  level: AlertLevel | string;
  message: string;
  created_at: string;
};

export function levelVariant(level: string): string {
  switch (level) {
    case "critical":
      return "danger";
    case "warning":
      return "warning";
    default:
      return "success";
  }
}
