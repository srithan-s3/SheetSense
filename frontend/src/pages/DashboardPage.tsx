import {
  ArrowRight,
  ArrowUpRight,
  ChartNoAxesCombined,
  CheckCircle2,
  CircleAlert,
  Hash,
  Layers3,
  Lightbulb,
  ScanLine,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { Analysis, View } from "../types";
import { ChartCard } from "../components/ChartCard";
import { EmptyState } from "../components/UI";
import { formatNumber } from "../utils/format";
const kpiIcons = [
  Layers3,
  TrendingUp,
  Hash,
  ChartNoAxesCombined,
  Sparkles,
  Hash,
];
export function DashboardPage({
  analysis,
  navigate,
}: {
  analysis: Analysis;
  navigate: (view: View) => void;
}) {
  return (
    <>
      <div className="section-label">
        <h2>The big picture</h2>
        <span>
          Calculated from {formatNumber(analysis.rows)} matching records
        </span>
      </div>
      <div className="kpi-grid">
        {analysis.kpis.map((kpi, index) => {
          const Icon = kpiIcons[index % kpiIcons.length];
          return (
            <article className="kpi-card" key={`${kpi.label}-${index}`}>
              <div>
                <span>{kpi.label}</span>
                <Icon size={17} />
              </div>
              <strong
                className={
                  typeof kpi.value === "string" ? "kpi-text" : undefined
                }
                title={String(kpi.value)}
              >
                {formatNumber(kpi.value, kpi.format)}
              </strong>
              <p>{kpi.description}</p>
            </article>
          );
        })}
      </div>
      {analysis.notes.length > 0 && (
        <div className="analysis-notes">
          <details>
            <summary>
              <CircleAlert size={16} />
              How this analysis was calculated
            </summary>
            <div>
              {analysis.notes.map((note, index) => (
                <p key={index}>{note}</p>
              ))}
            </div>
          </details>
        </div>
      )}
      <div className="section-label chart-section-label">
        <div>
          <h2>Your data, visualized</h2>
          <p>Charts selected for the columns in your spreadsheet.</p>
        </div>
        <button
          className="text-button accent"
          onClick={() => navigate("explore")}
        >
          Build a custom chart
          <ArrowUpRight size={16} />
        </button>
      </div>
      {analysis.charts.length ? (
        <div className="charts-grid">
          {analysis.charts.map((chart) => (
            <ChartCard key={chart.id} chart={chart} />
          ))}
        </div>
      ) : (
        <div className="card">
          <EmptyState
            icon={<ChartNoAxesCombined size={27} />}
            title="A little more data would help"
          >
            There aren’t enough suitable values to create a meaningful chart.
            Try another worksheet or adjust your filters.
          </EmptyState>
        </div>
      )}
      <div className="dashboard-bottom">
        <section className="insights-card">
          <div className="card-header">
            <span className="insights-icon">
              <Sparkles size={18} />
            </span>
            <div>
              <h2>A few things worth noticing</h2>
              <p>Observations calculated from your selected data.</p>
            </div>
            <span className="tag">Data insights</span>
          </div>
          {analysis.insights.length ? (
            <div className="insight-list">
              {analysis.insights.map((insight, index) => (
                <article key={index}>
                  <span className={`insight-icon ${insight.kind}`}>
                    {insight.kind === "warning" ? (
                      <CircleAlert size={17} />
                    ) : insight.kind === "positive" ? (
                      <TrendingUp size={17} />
                    ) : (
                      <Lightbulb size={17} />
                    )}
                  </span>
                  <div>
                    <h3>{insight.title}</h3>
                    <p>{insight.text}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="muted card-padding">
              No additional insights are available for these records.
            </p>
          )}
        </section>
        <aside className="quality-summary">
          <div className="card-header">
            <ScanLine size={20} />
            <h2>Data health</h2>
          </div>
          <div className="quality-status">
            <span
              className={
                analysis.quality.issues.length ? "warning-orb" : "success-orb"
              }
            >
              {analysis.quality.issues.length ? (
                <CircleAlert size={25} />
              ) : (
                <CheckCircle2 size={25} />
              )}
            </span>
            <strong>
              {analysis.quality.issues.length
                ? "A little attention helps"
                : "Looking good"}
            </strong>
            <p>
              {analysis.quality.issues.length
                ? `${analysis.quality.issues.length} observations to review in your data.`
                : "No quality issues were detected in this view."}
            </p>
          </div>
          <div className="quality-stat">
            <span>Missing cells</span>
            <strong>
              {formatNumber(analysis.quality.missing_cells)}{" "}
              <small>({formatNumber(analysis.quality.missing_percent)}%)</small>
            </strong>
          </div>
          <div className="quality-stat">
            <span>Duplicate rows</span>
            <strong>{formatNumber(analysis.quality.duplicate_rows)}</strong>
          </div>
          <button
            className="button secondary full-width"
            onClick={() => navigate("quality")}
          >
            Review data quality
            <ArrowRight size={16} />
          </button>
        </aside>
      </div>
    </>
  );
}
