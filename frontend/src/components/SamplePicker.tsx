import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  Download,
  GraduationCap,
  Package,
  ShoppingBag,
  Wallet,
} from "lucide-react";
import { api } from "../services/api";
import type { Sample } from "../types";
const icons = [ShoppingBag, GraduationCap, Wallet, Package];
const apiBase = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
export function SamplePicker({
  onSelect,
  busy,
}: {
  onSelect: (sample: Sample) => void;
  busy: boolean;
}) {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let current = true;
    setError("");
    void api
      .samples()
      .then((data) => {
        if (current) setSamples(data);
      })
      .catch((error) => {
        if (current) setError(error.message);
      });
    return () => {
      current = false;
    };
  }, [retry]);
  return (
    <div className="sample-section" id="samples">
      <div className="section-heading">
        <div>
          <span className="eyebrow">TAKE IT FOR A SPIN</span>
          <h2>No spreadsheet handy?</h2>
          <p>Explore a synthetic dataset, processed just like your own.</p>
        </div>
        <span className="tag">Synthetic demo data</span>
      </div>
      {error ? (
        <div className="inline-error">
          {error}
          <button
            className="text-button"
            onClick={() => setRetry((value) => value + 1)}
          >
            Try again
          </button>
        </div>
      ) : (
        <div className="sample-grid">
          {samples.length ? (
            samples.map((sample, index) => {
              const Icon = icons[index % icons.length];
              return (
                <article key={sample.id} className="sample-card">
                  <span className={`sample-icon color-${index}`}>
                    <Icon size={22} />
                  </span>
                  <div>
                    <h3>{sample.name}</h3>
                    <p>{sample.description}</p>
                    <div className="sample-actions">
                      <button
                        className="sample-link"
                        disabled={busy}
                        onClick={() => onSelect(sample)}
                        aria-label={`Explore ${sample.name}`}
                      >
                        Explore dataset <ArrowUpRight size={14} />
                      </button>
                      <a
                        className="sample-download"
                        href={`${apiBase}/api/samples/${encodeURIComponent(sample.id)}`}
                        download={sample.filename}
                        aria-label={`Download ${sample.name} sample`}
                      >
                        <Download size={12} /> Download
                      </a>
                    </div>
                  </div>
                </article>
              );
            })
          ) : (
            <p role="status" className="muted">
              Loading sample datasets…
            </p>
          )}
        </div>
      )}
    </div>
  );
}
