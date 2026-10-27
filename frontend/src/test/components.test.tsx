import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FilterPanel } from "../components/FilterPanel";
import { PreviewPage } from "../pages/PreviewPage";
import { QualityPage } from "../pages/QualityPage";
import { api } from "../services/api";
import type { Analysis, Session } from "../types";
vi.mock("../services/api", () => ({
  api: { preview: vi.fn(), clean: vi.fn() },
}));
afterEach(() => {
  vi.clearAllMocks();
});
const session: Session = {
  session_id: "test",
  token: "token",
  filename: "marks.xlsx",
  sheets: ["Class A", "Class B"],
  expires_at: "",
};
const columns = [
  { name: "Score", type: "numeric" as const, missing: 1, unique: 2 },
];
const analysis: Analysis = {
  filename: "marks.xlsx",
  sheet: "Class A",
  version: "original",
  rows: 2,
  total_rows: 2,
  column_count: 1,
  analyzed_at: "",
  columns,
  kpis: [],
  charts: [],
  insights: [],
  quality: {
    missing_cells: 1,
    missing_percent: 50,
    duplicate_rows: 0,
    issues: [],
  },
  filters: [],
  notes: [],
};
describe("Real-data UI interactions", () => {
  it("keeps filter choices as a draft until explicitly applied", async () => {
    const apply = vi.fn().mockResolvedValue(undefined);
    render(
      <FilterPanel
        definitions={[
          {
            column: "Department",
            type: "category",
            options: ["Science", "Arts"],
          },
        ]}
        filters={{}}
        apply={apply}
        busy={false}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Filters" }));
    fireEvent.change(screen.getByLabelText(/Department/), {
      target: { value: "Science" },
    });
    expect(apply).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() =>
      expect(apply).toHaveBeenCalledWith({
        Department: { values: ["Science"] },
      }),
    );
  });
  it("previews server-provided records and changes worksheet explicitly", async () => {
    vi.mocked(api.preview).mockResolvedValue({
      columns,
      rows: [{ Score: 81 }, { Score: null }],
      total_rows: 2,
      page: 1,
      page_size: 25,
      total_pages: 1,
    });
    const onSheet = vi.fn();
    render(
      <PreviewPage
        session={session}
        context={{ sheet: "Class A", filters: {}, version: "original" }}
        onAnalyze={vi.fn()}
        onSheet={onSheet}
        busy={false}
      />,
    );
    expect(await screen.findByText("81")).toBeInTheDocument();
    expect(screen.getByText("numeric · 1 missing")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Worksheet"), {
      target: { value: "Class B" },
    });
    expect(onSheet).toHaveBeenCalledWith("Class B");
  });
  it("requires a cleaning preview and explicit confirmation, locking operations during the request", async () => {
    let resolve!: (value: Awaited<ReturnType<typeof api.clean>>) => void;
    vi.mocked(api.clean).mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const onCleaned = vi.fn().mockResolvedValue(undefined);
    render(
      <QualityPage
        analysis={analysis}
        session={session}
        onCleaned={onCleaned}
        onOriginal={vi.fn()}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Confirm & apply changes" }),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Remove duplicate rows"));
    fireEvent.click(screen.getByRole("button", { name: "Preview changes" }));
    expect(screen.getByLabelText("Remove duplicate rows")).toBeDisabled();
    expect(screen.getByLabelText("Fill missing values in")).toBeDisabled();
    expect(api.clean).toHaveBeenCalledWith(
      session,
      "Class A",
      [{ action: "drop_duplicates" }],
      false,
    );
    await act(async () =>
      resolve({
        before_rows: 2,
        after_rows: 1,
        changed_cells: 0,
        preview: [{ Score: 81 }],
        version: "original",
      }),
    );
    expect(onCleaned).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Confirm & apply changes" }),
    ).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(
      screen.queryByRole("button", { name: "Confirm & apply changes" }),
    ).not.toBeInTheDocument();
  });
});
