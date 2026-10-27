import type { ReactNode } from "react";
import {
  ArrowLeft,
  ChevronRight,
  CircleHelp,
  FileSpreadsheet,
  LayoutDashboard,
  ScanLine,
  SlidersHorizontal,
  Table2,
  Trash2,
  Upload,
} from "lucide-react";
import type { Session, View } from "../types";
import { Logo, ThemeButton } from "../components/UI";
const nav = [
  { view: "dashboard", label: "Overview", icon: LayoutDashboard },
  { view: "preview", label: "Data preview", icon: Table2 },
  { view: "explore", label: "Chart explorer", icon: SlidersHorizontal },
  { view: "quality", label: "Data quality", icon: ScanLine },
] as const;
export function WorkspaceLayout({
  children,
  view,
  navigate,
  session,
  sheet,
  dark,
  toggleTheme,
  onDelete,
  busy,
}: {
  children: ReactNode;
  view: View;
  navigate: (view: View) => void;
  session: Session | null;
  sheet: string;
  dark: boolean;
  toggleTheme: () => void;
  onDelete: () => void;
  busy: boolean;
}) {
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Logo onClick={() => navigate("home")} />
        <div className="sidebar-label">WORKSPACE</div>
        <nav aria-label="Workspace navigation">
          {nav.map(({ view: target, label, icon: Icon }) => (
            <button
              key={target}
              className={`nav-item ${view === target ? "active" : ""}`}
              disabled={!session || !sheet || busy}
              onClick={() => navigate(target)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {view === target && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <button
          className={`nav-item upload-nav ${view === "upload" ? "active" : ""}`}
          aria-label="Upload dataset"
          onClick={() => navigate("upload")}
          disabled={busy}
        >
          <Upload size={18} />
          <span>Upload dataset</span>
        </button>
        <div className="sidebar-bottom">
          {session && (
            <div className="dataset-tile">
              <span className="dataset-icon">
                <FileSpreadsheet size={20} />
              </span>
              <strong title={session.filename}>{session.filename}</strong>
              <span>{sheet || "Select a worksheet"}</span>
            </div>
          )}
          <div className="privacy-note">
            <CircleHelp size={17} />
            <p>
              Your data, your control.
              <br />
              <span>Temporary sessions. No AI APIs.</span>
            </p>
          </div>
          {session && (
            <button
              className="text-button delete-link"
              disabled={busy}
              onClick={onDelete}
            >
              <Trash2 size={15} />
              Delete session
            </button>
          )}
          <button className="text-button" onClick={() => navigate("home")}>
            <ArrowLeft size={15} />
            Back to home
          </button>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="workspace-topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {view === "upload"
                ? "Upload dataset"
                : nav.find((item) => item.view === view)?.label}
            </strong>
          </div>
          <div className="topbar-right">
            <span className="local-badge">
              <i />
              Local analytics
            </span>
            <ThemeButton dark={dark} toggle={toggleTheme} />
            <span className="avatar" aria-label="SheetSense workspace">
              SS
            </span>
          </div>
        </header>
        <main className="workspace-content" id="main-content">
          {children}
        </main>
        <footer className="workspace-footer">
          <span>
            SheetSense<span className="brand-dot">.</span>{" "}
            <span className="footer-separator">/</span> A little clarity goes a
            long way.
          </span>
          <span className="footer-tagline">Built for curious minds.</span>
          {session && (
            <button
              className="text-button delete-link mobile-delete"
              aria-label="Delete session"
              disabled={busy}
              onClick={onDelete}
            >
              <Trash2 size={14} />
              Delete session
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
