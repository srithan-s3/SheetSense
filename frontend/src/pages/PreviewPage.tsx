import { useEffect, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Hash,
  Search,
  Table2,
  Type,
} from "lucide-react";
import type { Context, Preview, Session } from "../types";
import { api } from "../services/api";
import { cellValue, formatNumber } from "../utils/format";
import { EmptyState, Skeleton } from "../components/UI";
export function PreviewPage({
  session,
  context,
  onAnalyze,
  onSheet,
  busy,
}: {
  session: Session;
  context: Context;
  onAnalyze: () => void;
  onSheet: (sheet: string) => void;
  busy: boolean;
}) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const filterKey = JSON.stringify(context.filters);
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void api
      .preview(session, context, page, query)
      .then((data) => {
        if (active) setPreview(data);
      })
      .catch((error) => {
        if (active) setError(error.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [session, context.sheet, context.version, filterKey, page, query, retry]);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">GET TO KNOW YOUR DATA</span>
          <h1>Every insight starts with a row.</h1>
          <p>
            Explore your records and detected column types before diving in.
          </p>
        </div>
        <button
          className="button primary"
          disabled={busy || loading || !!error || !preview?.total_rows}
          onClick={onAnalyze}
        >
          Generate dashboard
          <ArrowRight size={17} />
        </button>
      </div>
      <div className="preview-summary">
        <span className="dataset-icon">
          <Table2 size={23} />
        </span>
        <div>
          <strong>{session.filename}</strong>
          <p>
            {preview
              ? `${formatNumber(preview.total_rows)} matching records · ${preview.columns.length} columns`
              : "Reading your dataset…"}{" "}
            · {context.version} data
          </p>
        </div>
        <label className="worksheet-inline">
          Worksheet
          <select
            aria-label="Worksheet"
            value={context.sheet}
            disabled={busy}
            onChange={(event) => {
              setPage(1);
              setSearch("");
              setQuery("");
              onSheet(event.target.value);
            }}
          >
            {session.sheets.map((sheet) => (
              <option key={sheet}>{sheet}</option>
            ))}
          </select>
        </label>
      </div>
      {error ? (
        <div className="inline-error" role="alert">
          {error}
          <button
            className="text-button"
            onClick={() => setRetry((value) => value + 1)}
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          <div className="table-card">
            <div className="table-toolbar">
              <div>
                <h2>Data preview</h2>
                <span>
                  25 rows per page · search across all filtered records
                </span>
              </div>
              <div className="search-field">
                <Search size={16} />
                <input
                  aria-label="Search records"
                  placeholder="Search your records…"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
            </div>
            {loading ? (
              <Skeleton cards={1} />
            ) : !preview?.rows.length ? (
              <EmptyState
                icon={<Search size={25} />}
                title="No matching records"
              >
                Try a different search or reset your dashboard filters.
              </EmptyState>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th className="row-number">#</th>
                      {preview.columns.map((column) => {
                        const Icon =
                          column.type === "numeric"
                            ? Hash
                            : column.type === "date"
                              ? CalendarDays
                              : Type;
                        return (
                          <th key={column.name}>
                            <div className="column-header">
                              <span>
                                <Icon size={14} />
                                {column.name}
                              </span>
                              <small>
                                {column.type}
                                {column.missing > 0
                                  ? ` · ${column.missing} missing`
                                  : ""}
                              </small>
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, index) => (
                      <tr key={index}>
                        <td className="row-number">
                          {(page - 1) * 25 + index + 1}
                        </td>
                        {preview.columns.map((column) => (
                          <td
                            key={column.name}
                            className={
                              row[column.name] == null
                                ? "missing-cell"
                                : column.type === "numeric"
                                  ? "numeric-cell"
                                  : ""
                            }
                            title={cellValue(row[column.name])}
                          >
                            {cellValue(row[column.name])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="pagination">
              <span>
                {preview?.total_rows
                  ? `${(page - 1) * 25 + 1}–${Math.min(page * 25, preview.total_rows)} of ${formatNumber(preview.total_rows)} records`
                  : "0 records"}
              </span>
              <div>
                <button
                  className="icon-button"
                  aria-label="Previous page"
                  disabled={page <= 1 || loading}
                  onClick={() => setPage((value) => value - 1)}
                >
                  <ChevronLeft size={17} />
                </button>
                <span>
                  Page {page} of {Math.max(1, preview?.total_pages || 1)}
                </span>
                <button
                  className="icon-button"
                  aria-label="Next page"
                  disabled={!preview || page >= preview.total_pages || loading}
                  onClick={() => setPage((value) => value + 1)}
                >
                  <ChevronRight size={17} />
                </button>
              </div>
            </div>
          </div>
          <p className="helper-note">
            Column types and missing-value counts describe the selected
            worksheet. Dates are recognized only when unambiguous; your original
            file is preserved.
          </p>
        </>
      )}
    </>
  );
}
