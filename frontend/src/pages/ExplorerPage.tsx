import { useState } from "react";
import { ChartNoAxesCombined, RotateCcw, Sparkles } from "lucide-react";
import type {
  Analysis,
  Chart,
  ChartConfig,
  ChartType,
  Context,
  Session,
} from "../types";
import { api } from "../services/api";
import { ChartCard } from "../components/ChartCard";
import { EmptyState, Spinner } from "../components/UI";
import { chartLabels } from "../utils/format";
export function validateChart(
  config: ChartConfig,
  analysis: Pick<Analysis, "columns">,
): string | null {
  const x = analysis.columns.find((column) => column.name === config.x);
  const y = analysis.columns.find((column) => column.name === config.y);
  if (!x) return "Select an X-axis column.";
  if (
    (config.type === "scatter" || config.type === "histogram") &&
    x.type !== "numeric"
  )
    return "Scatter plots and histograms require a numeric X-axis.";
  if (config.type === "line" && x.type !== "date")
    return "A trend line requires a recognized date column on the X-axis.";
  if (
    config.type !== "histogram" &&
    (config.aggregation !== "count" || config.type === "scatter") &&
    y?.type !== "numeric"
  )
    return "Select a numeric Y-axis column, or use Count to count records.";
  if (config.type === "scatter" && config.x === config.y)
    return "Choose two different numeric columns for a scatter plot.";
  if (config.top_n < 1 || config.top_n > 50 || !Number.isInteger(config.top_n))
    return "Top N must be a whole number between 1 and 50.";
  return null;
}
export function ExplorerPage({
  analysis,
  session,
  context,
}: {
  analysis: Analysis;
  session: Session;
  context: Context;
}) {
  const initial = (): ChartConfig => ({
    x:
      analysis.columns.find((column) => column.type === "category")?.name ||
      analysis.columns[0]?.name ||
      "",
    y:
      analysis.columns.find((column) => column.type === "numeric")?.name ||
      undefined,
    type: "bar",
    aggregation: analysis.columns.some((column) => column.type === "numeric")
      ? "sum"
      : "count",
    sort: "desc",
    top_n: 10,
  });
  const [config, setConfig] = useState<ChartConfig>(initial);
  const [chart, setChart] = useState<Chart | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const update = (patch: Partial<ChartConfig>) => {
    setConfig((old) => ({ ...old, ...patch }));
    setStale(true);
    setError("");
  };
  async function generate() {
    const issue = validateChart(config, analysis);
    if (issue) {
      setError(issue);
      return;
    }
    setBusy(true);
    setError("");
    try {
      setChart(await api.chart(session, context, config));
      setStale(false);
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
          <h2>Follow your curiosity.</h2>
          <p>
            Choose your columns and build a view that answers your question.
          </p>
        </div>
      </div>
      <div className="explorer-layout">
        <section className="explorer-config card">
          <div className="card-header">
            <ChartNoAxesCombined size={18} />
            <h2>Chart configuration</h2>
          </div>
          <div className="config-fields">
            <label className="field">
              Chart type
              <select
                disabled={busy}
                value={config.type}
                onChange={(event) =>
                  update({ type: event.target.value as ChartType })
                }
              >
                {Object.entries(chartLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              X-axis column
              <select
                disabled={busy}
                value={config.x}
                onChange={(event) => update({ x: event.target.value })}
              >
                <option value="">Select a column</option>
                {analysis.columns.map((column) => (
                  <option key={column.name} value={column.name}>
                    {column.name} ({column.type})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Y-axis / measure
              <select
                value={config.y || ""}
                disabled={
                  busy ||
                  config.type === "histogram" ||
                  (config.aggregation === "count" && config.type !== "scatter")
                }
                onChange={(event) =>
                  update({ y: event.target.value || undefined })
                }
              >
                <option value="">Select a numeric column</option>
                {analysis.columns
                  .filter((column) => column.type === "numeric")
                  .map((column) => (
                    <option key={column.name}>{column.name}</option>
                  ))}
              </select>
            </label>
            <label className="field">
              Aggregation
              <select
                value={config.aggregation}
                disabled={
                  busy ||
                  config.type === "scatter" ||
                  config.type === "histogram"
                }
                onChange={(event) =>
                  update({
                    aggregation: event.target
                      .value as ChartConfig["aggregation"],
                  })
                }
              >
                {[
                  ["sum", "Sum"],
                  ["mean", "Average"],
                  ["count", "Count records"],
                  ["min", "Minimum"],
                  ["max", "Maximum"],
                  ["median", "Median"],
                ].map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <div className="config-row">
              <label className="field">
                Sort by
                <select
                  value={config.sort}
                  disabled={
                    busy ||
                    config.type === "scatter" ||
                    config.type === "histogram" ||
                    config.type === "line"
                  }
                  onChange={(event) =>
                    update({ sort: event.target.value as ChartConfig["sort"] })
                  }
                >
                  <option value="desc">Value: high to low</option>
                  <option value="asc">Value: low to high</option>
                  <option value="label">Label / date</option>
                </select>
              </label>
              <label className="field">
                Top N
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={config.top_n}
                  disabled={
                    busy ||
                    config.type === "scatter" ||
                    config.type === "histogram" ||
                    config.type === "line"
                  }
                  onChange={(event) =>
                    update({ top_n: Number(event.target.value) })
                  }
                />
              </label>
            </div>
            {config.type === "line" && (
              <p className="helper-note">
                Trend lines use chronological date periods. Sorting and Top N do
                not apply.
              </p>
            )}
            {config.type === "stacked_bar" && (
              <p className="helper-note">
                The server pairs your measure with a compatible numeric column.
                A stack requires meaningful, nonnegative series.
              </p>
            )}
            {config.type === "scatter" && (
              <p className="helper-note">
                Scatter plots show the relationship between two numeric columns;
                they do not establish cause and effect.
              </p>
            )}
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            <button
              className="button primary full-width"
              disabled={busy}
              onClick={() => void generate()}
            >
              {busy ? (
                <Spinner label="Building chart…" />
              ) : (
                <>
                  <Sparkles size={16} />
                  Generate chart
                </>
              )}
            </button>
            <button
              className="text-button centered"
              disabled={busy}
              onClick={() => {
                setConfig(initial());
                setChart(null);
                setError("");
                setStale(false);
              }}
            >
              <RotateCcw size={14} />
              Reset configuration
            </button>
          </div>
        </section>
        <div className="explorer-result">
          {stale && chart && (
            <p className="helper-note">
              Configuration changed. Generate your chart to update the result.
            </p>
          )}
          {chart ? (
            <ChartCard
              chart={chart}
              key={chart.id + JSON.stringify(chart.data)}
            />
          ) : (
            <div className="card explorer-empty">
              <EmptyState
                icon={<ChartNoAxesCombined size={32} />}
                title="Your next question, visualized."
              >
                Choose your columns on the left, then generate a chart. Active
                dashboard filters are included.
              </EmptyState>
            </div>
          )}
          <div className="explorer-tip">
            <Sparkles size={18} />
            <p>
              <strong>A useful starting point</strong>Compare categories with a
              bar chart, explore numeric distributions with a histogram, or use
              a date column to see a trend.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
