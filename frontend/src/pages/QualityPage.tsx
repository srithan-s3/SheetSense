import { useState } from "react";
import {
  CheckCircle2,
  CircleAlert,
  Copy,
  Eraser,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import type { Analysis, CleanOperation, CleanResult, Session } from "../types";
import { api } from "../services/api";
import { cellValue, formatNumber } from "../utils/format";
import { EmptyState, Spinner } from "../components/UI";
export function QualityPage({
  analysis,
  session,
  onCleaned,
  onOriginal,
}: {
  analysis: Analysis;
  session: Session;
  onCleaned: () => Promise<void>;
  onOriginal: () => Promise<void>;
}) {
  const [duplicates, setDuplicates] = useState(false);
  const [column, setColumn] = useState("");
  const [method, setMethod] = useState("median");
  const [result, setResult] = useState<CleanResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selected = analysis.columns.find((item) => item.name === column);
  const operations: CleanOperation[] = [
    ...(duplicates ? [{ action: "drop_duplicates" as const }] : []),
    ...(selected
      ? selected.type === "numeric"
        ? [
            {
              action: "fill_numeric" as const,
              column,
              method: method as "mean" | "median" | "zero",
            },
          ]
        : [
            {
              action: "fill_category" as const,
              column,
              method: method as "mode" | "unknown",
            },
          ]
      : []),
  ];
  async function clean(apply: boolean) {
    setBusy(true);
    setError("");
    try {
      const data = await api.clean(session, analysis.sheet, operations, apply);
      if (apply) {
        await onCleaned();
        setResult(null);
      } else setResult(data);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="section-label">
        <div>
          <h2>A clearer picture of data quality.</h2>
          <p>Review the details, then decide what deserves attention.</p>
        </div>
        <span className="tag">
          <ShieldCheck size={14} />
          Original data preserved
        </span>
      </div>
      <div className="quality-kpis">
        {[
          {
            icon: CircleAlert,
            label: "Missing cells",
            value: formatNumber(analysis.quality.missing_cells),
            detail: `${formatNumber(analysis.quality.missing_percent)}% of cells in this view`,
          },
          {
            icon: Copy,
            label: "Duplicate rows",
            value: formatNumber(analysis.quality.duplicate_rows),
            detail: "Repeated records after the first occurrence",
          },
          {
            icon: ScanLine,
            label: "Quality observations",
            value: analysis.quality.issues.length,
            detail: "Issues and statistical flags to review",
          },
        ].map(({ icon: Icon, label, value, detail }) => (
          <article className="kpi-card" key={label}>
            <div>
              <span>{label}</span>
              <Icon size={18} />
            </div>
            <strong>{value}</strong>
            <p>{detail}</p>
          </article>
        ))}
      </div>
      <section className="card quality-issues">
        <div className="card-header">
          <ScanLine size={19} />
          <h2>What we noticed</h2>
        </div>
        {analysis.quality.issues.length ? (
          <div className="issue-list">
            {analysis.quality.issues.map((issue, index) => (
              <article key={index}>
                <span className={`issue-marker ${issue.severity}`}>
                  <CircleAlert size={17} />
                </span>
                <div>
                  <h3>
                    {issue.column || "Dataset"}
                    <span className="tag">
                      {issue.type.replaceAll("_", " ")}
                    </span>
                  </h3>
                  <p>{issue.message}</p>
                </div>
                {issue.count !== undefined && (
                  <span className="issue-count">
                    {formatNumber(issue.count)} affected
                  </span>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<CheckCircle2 size={26} />}
            title="No quality issues detected"
          >
            Your selected data passed the available checks.
          </EmptyState>
        )}
      </section>
      <section className="card cleaning-card">
        <div className="card-header">
          <Eraser size={19} />
          <div>
            <h2>A thoughtful tidy-up</h2>
            <p>
              Optional cleaning creates a separate working copy from the
              original worksheet.
            </p>
          </div>
          {analysis.version === "cleaned" && (
            <button
              className="button secondary small"
              disabled={busy}
              onClick={() => {
                setBusy(true);
                void onOriginal()
                  .catch((error) => setError(error.message))
                  .finally(() => setBusy(false));
              }}
            >
              Use original data
            </button>
          )}
        </div>
        <div className="cleaning-body">
          <p className="helper-note">
            Cleaning applies to the whole original worksheet, including records
            outside your current filters. Each application replaces the previous
            cleaned copy.
          </p>
          <label className="checkbox-label">
            <input
              type="checkbox"
              disabled={busy}
              checked={duplicates}
              onChange={(event) => {
                setDuplicates(event.target.checked);
                setResult(null);
              }}
            />
            Remove duplicate rows
          </label>
          <div className="cleaning-fields">
            <label className="field">
              Fill missing values in
              <select
                disabled={busy}
                value={column}
                onChange={(event) => {
                  const col = analysis.columns.find(
                    (item) => item.name === event.target.value,
                  );
                  setColumn(event.target.value);
                  setMethod(col?.type === "numeric" ? "median" : "mode");
                  setResult(null);
                }}
              >
                <option value="">Don’t fill any column</option>
                {analysis.columns
                  .filter((item) => item.type !== "date")
                  .map((item) => (
                    <option key={item.name}>{item.name}</option>
                  ))}
              </select>
            </label>
            {selected && (
              <label className="field">
                Fill method
                <select
                  disabled={busy}
                  value={method}
                  onChange={(event) => {
                    setMethod(event.target.value);
                    setResult(null);
                  }}
                >
                  {(selected.type === "numeric"
                    ? [
                        ["median", "Median"],
                        ["mean", "Average"],
                        ["zero", "Zero"],
                      ]
                    : [
                        ["mode", "Most common value"],
                        ["unknown", "“Unknown” label"],
                      ]
                  ).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button
              className="button secondary"
              disabled={!operations.length || busy}
              onClick={() => void clean(false)}
            >
              {busy ? <Spinner label="Processing…" /> : "Preview changes"}
            </button>
          </div>
          {error && (
            <p role="alert" className="inline-error">
              {error}
            </p>
          )}
          {result && (
            <div className="clean-preview">
              <h3>Review before applying</h3>
              <p>
                {formatNumber(result.before_rows)} →{" "}
                {formatNumber(result.after_rows)} rows ·{" "}
                {formatNumber(result.changed_cells)} cells changed
              </p>
              {result.preview.length > 0 && (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(result.preview[0]).map((key) => (
                          <th key={key}>{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.preview.slice(0, 5).map((row, index) => (
                        <tr key={index}>
                          {Object.keys(result.preview[0]).map((key) => (
                            <td key={key}>{cellValue(row[key])}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="helper-note">
                Preview of the resulting data. Applying creates a cleaned
                version for your dashboard and exports. The original remains
                available.
              </p>
              <div className="button-row">
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() => void clean(true)}
                >
                  Confirm & apply changes
                </button>
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => setResult(null)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
