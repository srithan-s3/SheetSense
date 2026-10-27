import { BarChart3, LoaderCircle, Moon, Sun, X } from "lucide-react";
import type { ReactNode } from "react";
export function Logo({ onClick }: { onClick?: () => void }) {
  return (
    <button className="brand" onClick={onClick} aria-label="SheetSense home">
      <span className="brand-mark">
        <BarChart3 size={22} strokeWidth={2.4} />
      </span>
      <span>
        Sheet<span className="brand-light">Sense</span>
        <span className="brand-dot">.</span>
      </span>
    </button>
  );
}
export function ThemeButton({
  dark,
  toggle,
}: {
  dark: boolean;
  toggle: () => void;
}) {
  return (
    <button
      className="icon-button"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light theme" : "Dark theme"}
    >
      {dark ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}
export function Spinner({ label = "Working…" }: { label?: string }) {
  return (
    <span className="inline-loading" role="status">
      <LoaderCircle size={18} className="spin" />
      {label}
    </span>
  );
}
export function EmptyState({
  icon,
  title,
  children,
}: {
  icon?: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon && <span className="empty-icon">{icon}</span>}
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function Notice({
  message,
  onDismiss,
  error = false,
}: {
  message: string;
  onDismiss: () => void;
  error?: boolean;
}) {
  return (
    <div
      role={error ? "alert" : "status"}
      className={`notice ${error ? "notice-error" : ""}`}
    >
      <span>{message}</span>
      <button
        className="icon-button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
      >
        <X size={18} />
      </button>
    </div>
  );
}
export function Skeleton({ cards = 3 }: { cards?: number }) {
  return (
    <div aria-label="Loading data" role="status" className="skeleton-grid">
      {Array.from({ length: cards }, (_, index) => (
        <div className="skeleton-card" key={index}>
          <i />
          <i />
          <i />
        </div>
      ))}
    </div>
  );
}
