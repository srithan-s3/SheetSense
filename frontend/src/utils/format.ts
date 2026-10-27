export function formatNumber(value: number | string, format?: string) {
  if (typeof value !== "number") return value;
  if (!Number.isFinite(value)) return "Unavailable";
  return (
    new Intl.NumberFormat("en", {
      maximumFractionDigits: format === "number" ? 0 : 2,
    }).format(value) + (format === "percent" ? "%" : "")
  );
}
export function cellValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
export function compact(value: unknown) {
  return typeof value === "number"
    ? new Intl.NumberFormat("en", {
        notation: "compact",
        maximumFractionDigits: 1,
      }).format(value)
    : String(value ?? "");
}
export const chartLabels = {
  bar: "Bar",
  horizontal_bar: "Horizontal bar",
  line: "Line",
  pie: "Pie",
  doughnut: "Doughnut",
  histogram: "Histogram",
  scatter: "Scatter",
  stacked_bar: "Stacked bar",
};
