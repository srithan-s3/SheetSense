import { lazy, Suspense, useEffect, useState } from "react";
import {
  CheckCircle2,
  Download,
  FileSpreadsheet,
  RefreshCw,
  X,
} from "lucide-react";
import { useTheme } from "./hooks/useTheme";
import { useWorkspace } from "./hooks/useWorkspace";
import { Landing } from "./pages/Landing";
import { UploadPage } from "./pages/UploadPage";
import { PreviewPage } from "./pages/PreviewPage";
import { WorkspaceLayout } from "./layouts/WorkspaceLayout";
import { Notice, Spinner } from "./components/UI";
import { FilterPanel } from "./components/FilterPanel";
import { api } from "./services/api";
import { formatNumber } from "./utils/format";
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
);
const ExplorerPage = lazy(() =>
  import("./pages/ExplorerPage").then((module) => ({
    default: module.ExplorerPage,
  })),
);
const QualityPage = lazy(() =>
  import("./pages/QualityPage").then((module) => ({
    default: module.QualityPage,
  })),
);
export default function App() {
  const theme = useTheme();
  const workspace = useWorkspace();
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState<"pdf" | "csv" | "xlsx">("pdf");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const { view, session, sheet, analysis, busy, context } = workspace;
  useEffect(() => {
    if (!confirmDelete) return;
    const previous = document.activeElement as HTMLElement | null;
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) setConfirmDelete(false);
      if (event.key !== "Tab") return;
      const buttons = Array.from(
        document.querySelectorAll<HTMLButtonElement>(
          '[role="alertdialog"] button:not(:disabled)',
        ),
      );
      const first = buttons[0];
      const last = buttons.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      previous?.focus();
    };
  }, [confirmDelete, busy]);
  async function exportData() {
    if (!session) return;
    setExporting(true);
    workspace.setError("");
    try {
      await api.export(session, context, format);
      workspace.setMessage(`Your ${format.toUpperCase()} export is ready.`);
    } catch (error) {
      workspace.setError(
        error instanceof Error ? error.message : "Export failed. Please retry.",
      );
    } finally {
      setExporting(false);
    }
  }
  const navigate = (next: Parameters<typeof workspace.navigate>[0]) => {
    window.scrollTo({ top: 0, behavior: "instant" });
    void workspace.navigate(next);
  };
  const isAnalysis =
    view === "dashboard" || view === "explore" || view === "quality";
  return (
    <Suspense
      fallback={
        <div className="page-loading">
          <Spinner label="Opening your workspace…" />
        </div>
      }
    >
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {view === "home" ? (
        <Landing
          onStart={() => navigate("upload")}
          onSample={(sample) => void workspace.sample(sample)}
          dark={theme.dark}
          toggleTheme={theme.toggle}
          busy={busy}
        />
      ) : (
        <WorkspaceLayout
          view={view}
          navigate={navigate}
          session={session}
          sheet={sheet}
          dark={theme.dark}
          toggleTheme={theme.toggle}
          onDelete={() => setConfirmDelete(true)}
          busy={busy}
        >
          {view === "upload" && (
            <UploadPage
              upload={workspace.upload}
              session={session}
              busy={busy}
              onChoose={workspace.chooseSheet}
              onSample={(sample) => void workspace.sample(sample)}
              error={workspace.error}
              onClear={() => void workspace.deleteSession()}
            />
          )}
          {view === "preview" && session && (
            <PreviewPage
              key={`${session.session_id}-${sheet}-${context.version}-${JSON.stringify(context.filters)}`}
              session={session}
              context={context}
              onAnalyze={() => navigate("dashboard")}
              onSheet={workspace.chooseSheet}
              busy={busy}
            />
          )}
          {isAnalysis && analysis && session && (
            <>
              <div className="page-heading dashboard-heading">
                <div>
                  <span className="eyebrow">YOUR DATA, A LITTLE CLEARER</span>
                  <h1>
                    {view === "dashboard"
                      ? "Overview"
                      : view === "explore"
                        ? "Chart explorer"
                        : "Data quality"}
                  </h1>
                  <p>
                    <FileSpreadsheet size={15} />
                    <span title={session.filename}>{session.filename}</span>
                    <span className="dot-separator">·</span>
                    {sheet}
                    <span className="dot-separator">·</span>
                    {formatNumber(analysis.rows)} of{" "}
                    {formatNumber(analysis.total_rows)} rows
                    <span className="dot-separator">·</span>
                    {analysis.column_count} columns
                  </p>
                </div>
                <div className="header-actions">
                  <button
                    className="button secondary small"
                    disabled={busy}
                    onClick={() => navigate("upload")}
                  >
                    <RefreshCw size={15} />
                    Change dataset
                  </button>
                  <div className="export-group">
                    <select
                      aria-label="Export format"
                      value={format}
                      onChange={(event) =>
                        setFormat(event.target.value as typeof format)
                      }
                    >
                      <option value="pdf">PDF report</option>
                      <option value="csv">CSV data</option>
                      <option value="xlsx">Excel data</option>
                    </select>
                    <button
                      className="button primary small"
                      disabled={busy || exporting}
                      onClick={() => void exportData()}
                    >
                      {exporting ? (
                        <Spinner label="Exporting…" />
                      ) : (
                        <>
                          <Download size={15} />
                          Export
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
              <div className="analysis-status">
                <CheckCircle2 size={13} />
                <span>
                  Analysis complete ·{" "}
                  {new Date(analysis.analyzed_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                <span className="tag">
                  {context.version === "cleaned"
                    ? "Cleaned working copy"
                    : "Original data"}
                </span>
                {busy && <Spinner label="Updating analysis…" />}
              </div>
              <FilterPanel
                definitions={analysis.filters}
                filters={workspace.filters}
                apply={workspace.applyFilters}
                busy={busy}
              />
              {view === "dashboard" && (
                <DashboardPage analysis={analysis} navigate={navigate} />
              )}
              {view === "explore" && (
                <ExplorerPage
                  key={`${sheet}-${context.version}-${JSON.stringify(context.filters)}`}
                  analysis={analysis}
                  session={session}
                  context={context}
                />
              )}
              {view === "quality" && (
                <QualityPage
                  key={`${sheet}-${context.version}`}
                  analysis={analysis}
                  session={session}
                  onCleaned={() => workspace.changeVersion("cleaned")}
                  onOriginal={() => workspace.changeVersion("original")}
                />
              )}
            </>
          )}
          {busy && view === "preview" && (
            <div className="processing-banner">
              <Spinner label="Finding the story in your data…" />
            </div>
          )}
        </WorkspaceLayout>
      )}
      {workspace.error && view !== "upload" && (
        <Notice
          message={workspace.error}
          error
          onDismiss={() => workspace.setError("")}
        />
      )}
      {workspace.message && (
        <Notice
          message={workspace.message}
          onDismiss={() => workspace.setMessage("")}
        />
      )}
      {confirmDelete && (
        <div
          className="modal-backdrop"
          onClick={() => !busy && setConfirmDelete(false)}
        >
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-title"
            aria-describedby="delete-description"
            className="modal"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="icon-button modal-close"
              disabled={busy}
              aria-label="Close deletion dialog"
              onClick={() => setConfirmDelete(false)}
            >
              <X size={19} />
            </button>
            <h2 id="delete-title">Delete this analysis session?</h2>
            <p id="delete-description">
              The uploaded data, cleaned copies, and results for this session
              will be removed from the server. You can upload your file again
              anytime.
            </p>
            <div className="button-row">
              <button
                className="button secondary"
                disabled={busy}
                autoFocus
                onClick={() => setConfirmDelete(false)}
              >
                Keep session
              </button>
              <button
                className="button danger"
                disabled={busy}
                onClick={() =>
                  void workspace
                    .deleteSession()
                    .then(() => setConfirmDelete(false))
                }
              >
                Delete session
              </button>
            </div>
          </section>
        </div>
      )}
    </Suspense>
  );
}
