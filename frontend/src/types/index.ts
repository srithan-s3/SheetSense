export type View =
  | "home"
  | "upload"
  | "preview"
  | "dashboard"
  | "explore"
  | "quality";
export interface Session {
  session_id: string;
  token: string;
  filename: string;
  sheets: string[];
  expires_at: string;
}
export interface Column {
  name: string;
  type: "numeric" | "category" | "date" | "text";
  missing: number;
  unique: number;
}
export type ChartType =
  | "bar"
  | "horizontal_bar"
  | "line"
  | "pie"
  | "doughnut"
  | "histogram"
  | "scatter"
  | "stacked_bar";
export interface Chart {
  id: string;
  type: ChartType;
  title: string;
  description: string;
  x_label: string;
  y_label: string;
  x_key: string;
  y_keys: string[];
  data: Record<string, unknown>[];
  alternatives: string[];
  series_labels?: Record<string, string>;
}
export interface FilterValue {
  values?: string[];
  min?: number;
  max?: number;
  start?: string;
  end?: string;
}
export type Filters = Record<string, FilterValue>;
export interface FilterDefinition {
  column: string;
  type: "category" | "date" | "numeric";
  options?: string[];
  min?: number | string;
  max?: number | string;
}
export interface Analysis {
  filename: string;
  sheet: string;
  version: "original" | "cleaned";
  rows: number;
  total_rows: number;
  column_count: number;
  analyzed_at: string;
  columns: Column[];
  kpis: {
    label: string;
    value: number | string;
    description: string;
    format?: "number" | "decimal" | "percent";
  }[];
  charts: Chart[];
  insights: {
    title: string;
    text: string;
    kind: "info" | "positive" | "warning";
  }[];
  quality: {
    missing_cells: number;
    missing_percent: number;
    duplicate_rows: number;
    issues: {
      column?: string;
      type: string;
      severity: "info" | "warning";
      message: string;
      count?: number;
    }[];
  };
  filters: FilterDefinition[];
  notes: string[];
}
export interface Preview {
  columns: Column[];
  rows: Record<string, unknown>[];
  total_rows: number;
  page: number;
  page_size: number;
  total_pages: number;
}
export interface Sample {
  id: string;
  name: string;
  description: string;
  filename: string;
}
export interface Context {
  sheet: string;
  filters: Filters;
  version: "original" | "cleaned";
}
export interface ChartConfig {
  x: string;
  y?: string;
  type: ChartType;
  aggregation: "sum" | "mean" | "count" | "min" | "max" | "median";
  sort: "asc" | "desc" | "label";
  top_n: number;
}
export type CleanOperation =
  | { action: "drop_duplicates" }
  | {
      action: "fill_numeric";
      column: string;
      method: "mean" | "median" | "zero";
    }
  | { action: "fill_category"; column: string; method: "mode" | "unknown" };
export interface CleanResult {
  before_rows: number;
  after_rows: number;
  changed_cells: number;
  preview: Record<string, unknown>[];
  version: "original" | "cleaned";
}
