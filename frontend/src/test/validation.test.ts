import { describe, expect, it } from "vitest";
import { validateFile } from "../pages/UploadPage";
import { validateChart } from "../pages/ExplorerPage";
import type { ChartConfig, Column } from "../types";
const columns: Column[] = [
  { name: "Department", type: "category", missing: 0, unique: 3 },
  { name: "Score", type: "numeric", missing: 0, unique: 30 },
  { name: "Date", type: "date", missing: 0, unique: 20 },
  { name: "Attendance", type: "numeric", missing: 0, unique: 20 },
];
const base: ChartConfig = {
  x: "Department",
  y: "Score",
  type: "bar",
  aggregation: "sum",
  sort: "desc",
  top_n: 10,
};
describe("Upload safety and useful error messages", () => {
  it("rejects executable and unsupported extensions", () => {
    expect(validateFile(new File(["x"], "run.exe"))).toMatch(/Excel.*CSV/);
    expect(validateFile(new File(["x"], "data.xlsx.exe"))).toMatch(
      /Excel.*CSV/,
    );
  });
  it("rejects empty uploads and files above the configured default limit", () => {
    expect(validateFile(new File([], "empty.csv"))).toMatch(/empty/);
    expect(
      validateFile(
        new File([new ArrayBuffer(10 * 1024 * 1024 + 1)], "large.csv"),
      ),
    ).toMatch(/10 MB/);
  });
  it("accepts supported case-insensitive extensions", () => {
    for (const name of ["DATA.CSV", "marks.xlsx", "legacy.xls"])
      expect(validateFile(new File(["data"], name))).toBeNull();
  });
});
describe("Custom chart validation", () => {
  it("supports categorical counts without a numeric column", () => {
    expect(
      validateChart(
        { ...base, y: undefined, aggregation: "count" },
        { columns },
      ),
    ).toBeNull();
  });
  it("requires a real date column for trends", () => {
    expect(validateChart({ ...base, type: "line" }, { columns })).toMatch(
      /date/,
    );
    expect(
      validateChart({ ...base, type: "line", x: "Date" }, { columns }),
    ).toBeNull();
  });
  it("requires distinct numeric columns for scatter plots", () => {
    expect(validateChart({ ...base, type: "scatter" }, { columns })).toMatch(
      /numeric X-axis/,
    );
    expect(
      validateChart({ ...base, type: "scatter", x: "Score" }, { columns }),
    ).toMatch(/different/);
    expect(
      validateChart({ ...base, type: "scatter", x: "Attendance" }, { columns }),
    ).toBeNull();
  });
  it("prevents invalid aggregates and out-of-range category limits", () => {
    expect(validateChart({ ...base, y: "Department" }, { columns })).toMatch(
      /numeric Y-axis/,
    );
    expect(validateChart({ ...base, top_n: 51 }, { columns })).toMatch(
      /1 and 50/,
    );
    expect(validateChart({ ...base, top_n: 2.5 }, { columns })).toMatch(
      /whole number/,
    );
  });
});
