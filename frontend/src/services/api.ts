import type {
  Analysis,
  Chart,
  ChartConfig,
  CleanOperation,
  CleanResult,
  Context,
  Preview,
  Sample,
  Session,
} from "../types";
const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
async function request<T>(
  path: string,
  options: RequestInit = {},
  session?: Session,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${base}/api${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...(session ? { "X-Session-Token": session.token } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      "Cannot connect to the analytics server. Make sure the backend is running, then try again.",
    );
  }
  const result = await response.json().catch(() => null);
  if (!response.ok || !result?.success)
    throw new Error(
      result?.error?.message ||
        "The server could not complete this request. Please try again.",
    );
  return result.data as T;
}
const post = <T>(path: string, session: Session, body: unknown) =>
  request<T>(
    `${path}/${session.session_id}`,
    { method: "POST", body: JSON.stringify(body) },
    session,
  );
export const api = {
  upload(file: File) {
    const body = new FormData();
    body.append("file", file);
    return request<Session>("/upload", { method: "POST", body });
  },
  samples: () => request<Sample[]>("/samples"),
  async sampleFile(sample: Sample) {
    const response = await fetch(
      `${base}/api/samples/${encodeURIComponent(sample.id)}`,
    );
    if (!response.ok)
      throw new Error(
        "The sample could not be loaded. Try uploading a file instead.",
      );
    return new File([await response.blob()], sample.filename);
  },
  analyze: (session: Session, context: Context) =>
    post<Analysis>("/analyze", session, context),
  filter: (session: Session, context: Context) =>
    post<Analysis>("/filter", session, context),
  preview: (session: Session, context: Context, page: number, search: string) =>
    post<Preview>("/preview", session, {
      ...context,
      page,
      page_size: 25,
      search,
    }),
  chart: (session: Session, context: Context, config: ChartConfig) =>
    post<Chart>("/custom-chart", session, { ...context, ...config }),
  clean: (
    session: Session,
    sheet: string,
    operations: CleanOperation[],
    apply: boolean,
  ) => post<CleanResult>("/clean", session, { sheet, operations, apply }),
  delete: (session: Session) =>
    post<{ deleted: boolean }>("/delete", session, {}),
  async export(
    session: Session,
    context: Context,
    format: "pdf" | "csv" | "xlsx",
  ) {
    const response = await fetch(`${base}/api/export/${session.session_id}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Token": session.token,
      },
      body: JSON.stringify({ ...context, format }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(
        body?.error?.message || "Export failed. Please try again.",
      );
    }
    const filename =
      response.headers
        .get("Content-Disposition")
        ?.match(/filename="?([^";]+)"?/)?.[1] || `sheetsense-report.${format}`;
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
