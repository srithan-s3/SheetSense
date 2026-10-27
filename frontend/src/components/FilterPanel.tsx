import { useState } from "react";
import { Filter, RotateCcw, ChevronDown } from "lucide-react";
import type { FilterDefinition, Filters, FilterValue } from "../types";
export function FilterPanel({
  definitions,
  filters,
  apply,
  busy,
}: {
  definitions: FilterDefinition[];
  filters: Filters;
  apply: (filters: Filters) => Promise<void>;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Filters>(filters);
  const active = Object.keys(filters).length;
  const update = (column: string, value: FilterValue) =>
    setDraft((old) => {
      const next = { ...old };
      if (
        Object.values(value).every(
          (item) =>
            item === undefined ||
            item === "" ||
            (Array.isArray(item) && !item.length),
        )
      )
        delete next[column];
      else next[column] = value;
      return next;
    });
  return (
    <div className="filter-panel">
      <div className="filter-bar">
        <button
          className="filter-toggle"
          onClick={() => {
            if (!open) setDraft(filters);
            setOpen((value) => !value);
          }}
          aria-expanded={open}
        >
          <Filter size={16} />
          <span>Filters</span>
          {active > 0 && <span className="small-count">{active}</span>}
          <ChevronDown size={15} className={open ? "rotate" : ""} />
        </button>
        <span className="filter-hint">
          {active
            ? `${active} active filter${active > 1 ? "s" : ""} · applied across your analysis`
            : "All records · add a filter to focus your analysis"}
        </span>
        {active > 0 && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              setDraft({});
              void apply({}).catch(() => undefined);
            }}
          >
            <RotateCcw size={14} />
            Reset
          </button>
        )}
      </div>
      {open && (
        <div className="filter-content">
          {!definitions.length ? (
            <p className="muted">
              There are no suitable filter columns in this dataset.
            </p>
          ) : (
            <>
              <div className="filter-fields">
                {definitions.map((def) => (
                  <div className="field" key={def.column}>
                    <label htmlFor={`filter-${def.column}`}>
                      {def.column}
                      <span className="field-type">{def.type}</span>
                    </label>
                    {def.type === "category" ? (
                      <select
                        id={`filter-${def.column}`}
                        value={draft[def.column]?.values?.[0] ?? ""}
                        onChange={(event) =>
                          update(def.column, {
                            values: event.target.value
                              ? [event.target.value]
                              : [],
                          })
                        }
                      >
                        <option value="">All values</option>
                        {def.options?.map((value) => (
                          <option key={value} value={value}>
                            {value || "(empty)"}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="range-inputs">
                        <input
                          id={`filter-${def.column}`}
                          aria-label={`${def.column} ${def.type === "date" ? "start date" : "minimum"}`}
                          type={def.type === "date" ? "date" : "number"}
                          step="any"
                          placeholder={
                            def.min === undefined ? "From" : String(def.min)
                          }
                          value={
                            def.type === "date"
                              ? (draft[def.column]?.start ?? "")
                              : (draft[def.column]?.min ?? "")
                          }
                          onChange={(event) =>
                            update(def.column, {
                              ...draft[def.column],
                              [def.type === "date" ? "start" : "min"]:
                                event.target.value === ""
                                  ? undefined
                                  : def.type === "date"
                                    ? event.target.value
                                    : Number(event.target.value),
                            })
                          }
                        />
                        <span>–</span>
                        <input
                          aria-label={`${def.column} ${def.type === "date" ? "end date" : "maximum"}`}
                          type={def.type === "date" ? "date" : "number"}
                          step="any"
                          placeholder={
                            def.max === undefined ? "To" : String(def.max)
                          }
                          value={
                            def.type === "date"
                              ? (draft[def.column]?.end ?? "")
                              : (draft[def.column]?.max ?? "")
                          }
                          onChange={(event) =>
                            update(def.column, {
                              ...draft[def.column],
                              [def.type === "date" ? "end" : "max"]:
                                event.target.value === ""
                                  ? undefined
                                  : def.type === "date"
                                    ? event.target.value
                                    : Number(event.target.value),
                            })
                          }
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
              <div className="filter-actions">
                <span className="muted">
                  Filters also apply to previews, custom charts, and exports.
                </span>
                <button
                  className="button primary small"
                  disabled={busy}
                  onClick={() =>
                    void apply(draft)
                      .then(() => setOpen(false))
                      .catch(() => undefined)
                  }
                >
                  Apply filters
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
