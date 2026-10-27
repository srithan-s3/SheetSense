"""Deterministic analytics; no uploaded code, formulas, or expressions are executed.

Parsing policy: native dates and complete, valid ISO-8601 date strings only.
Numeric text accepts decimal/scientific notation or English thousands grouping;
currency symbols and locale-dependent decimal commas are deliberately not guessed.
Leading-zero numbers, long digit strings, and identifier-named columns remain
categories. Nonfinite numbers become missing. Original frames are never mutated.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import math
import re
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype


CHART_TYPES = {"bar", "horizontal_bar", "line", "pie", "doughnut", "histogram", "scatter", "stacked_bar"}
AGGREGATIONS = {"sum", "mean", "count", "min", "max", "median"}
NUMBER = re.compile(r"^[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:?\d{2})?)?$")
DATE_LIKE = re.compile(r"^(?:\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})(?:\s|T|$)")
IDENTIFIER = re.compile(r"(?:^|\W)(?:id|identifier|sku|uuid|code|zip|postcode|postal|phone|telephone|mobile|roll|rollno)(?:$|\W)|(?:^|\W)(?:account|invoice|order|student|employee)\s*(?:number|no)(?:$|\W)", re.I)
NO_SUM = re.compile(r"percent|percentage|rate|ratio|average|avg|score|marks|grade|rating|(?:^|\W)age(?:$|\W)|temperature|price|unit.?cost|mathematics|(?:^|\W)math(?:s|$|\W)|science|english|physics|chemistry|biology|history|geography|gpa", re.I)


def _identifier(name: str) -> bool:
    # Split CamelCase as well as separators so CustomerID and student_id agree.
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(name)).replace("_", " ")
    return bool(IDENTIFIER.search(words))


def _scalar(value: Any) -> Any:
    """Return finite JSON primitives, including for NumPy and pandas values."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date, np.datetime64)):
        timestamp = pd.Timestamp(value)
        if pd.isna(timestamp):
            return None
        return timestamp.isoformat()
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _records(frame: pd.DataFrame) -> list[dict]:
    return [{str(key): _scalar(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]


def _number(value: Any) -> float | int | None:
    parsed = _scalar(value)
    return parsed if isinstance(parsed, (float, int)) and not isinstance(parsed, bool) else None


def _readable_number(value: float | int) -> str:
    """Readable insight text without changing the underlying numeric values."""
    magnitude = abs(value)
    if magnitude == 0:
        return "0"
    if magnitude >= 1e12 or magnitude < 0.0001:
        return f"{value:.4g}"
    decimals = 2 if magnitude >= 1000 else 4
    return f"{value:,.{decimals}f}".rstrip("0").rstrip(".")


def _statistics(series: pd.Series) -> dict:
    """Scale before mean/median/sum so finite observations avoid overflow."""
    valid = series.dropna().astype(float)
    if valid.empty:
        return {key: None for key in ("mean", "median", "min", "max", "sum")}
    scale = float(valid.abs().max())
    normalized = valid / scale if scale else valid
    total = math.fsum(normalized.tolist())
    return {"mean": _number(float(normalized.mean()) * scale), "median": _number(float(normalized.median()) * scale), "sum": _number(total * scale), "min": _number(valid.min()), "max": _number(valid.max())}


def _label(value: Any) -> str:
    parsed = _scalar(value)
    return "(Missing)" if parsed is None else str(parsed)


def _issue(kind: str, message: str, column: str | None = None, count: int | None = None, severity: str = "warning") -> dict:
    issue = {"type": kind, "severity": severity, "message": message}
    if column is not None:
        issue["column"] = column
    if count is not None:
        issue["count"] = int(count)
    return issue


def _names(raw: pd.DataFrame) -> tuple[list[str], list[dict]]:
    names: list[str] = []
    seen: set[str] = set()
    issues = []
    for index, original in enumerate(raw.columns):
        name = str(original).strip() if original is not None else ""
        if not name or name.lower() in {"nan", "none"}:
            name = f"Column {index + 1}"
            issues.append(_issue("column_header", f"Blank column header was named {name}.", name, severity="info"))
        base, suffix = name, 2
        while name in seen:
            name = f"{base} ({suffix})"
            suffix += 1
        if name != base:
            issues.append(_issue("column_header", f"Repeated header {base} was distinguished as {name}.", name, severity="info"))
        seen.add(name)
        names.append(name)
    return names, issues


def _parse_iso(value: Any) -> pd.Timestamp | None:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value.strip()):
        return None
    try:
        parsed = pd.Timestamp(value.strip())
        # Normalize offsets to UTC; naive spreadsheet dates retain their wall time.
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("UTC").tz_localize(None)
        if parsed.year < 1678 or parsed.year > 2261:
            return None
        return parsed
    except (ValueError, TypeError, OverflowError):
        return None


def _categorical_type(series: pd.Series, name: str = "") -> str:
    nonnull = series.dropna()
    if nonnull.empty:
        return "category"
    unique = nonnull.nunique()
    average_length = nonnull.astype(str).str.len().mean()
    if average_length <= 90 and re.search(r"category|department|region|product|country|city|location|status|segment|subject|class|brand|supplier", name, re.I):
        return "category"
    return "category" if unique <= max(30, len(nonnull) * 0.3) and average_length <= 90 else "text"


def prepare_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    if not isinstance(raw, pd.DataFrame):
        raise ValueError("Analysis requires a table of spreadsheet records.")
    frame = raw.copy(deep=True).reset_index(drop=True)
    frame.columns, issues = _names(raw)
    columns = []
    for name in frame.columns:
        series = frame[name].map(lambda value: np.nan if isinstance(value, str) and not value.strip() else value)
        nonfinite = series.map(lambda value: isinstance(value, (float, np.floating)) and not pd.isna(value) and not math.isfinite(float(value)))
        if nonfinite.any():
            issues.append(_issue("nonfinite", "Infinite numeric values are treated as missing for analysis.", name, int(nonfinite.sum())))
            series = series.mask(nonfinite, np.nan)
        nonnull = series.dropna()
        kind = "category"
        if _identifier(name):
            kind = "category"
            series = series.map(lambda value: str(value) if pd.notna(value) else np.nan)
            issues.append(_issue("identifier", "Identifier column is excluded from automatic numeric metrics.", name, severity="info"))
        elif nonnull.empty:
            kind = "numeric" if is_numeric_dtype(series.dtype) and not is_bool_dtype(series.dtype) else "category"
        elif is_bool_dtype(series.dtype) or nonnull.map(lambda value: isinstance(value, (bool, np.bool_))).all():
            kind = "category"
        elif is_datetime64_any_dtype(series.dtype) or nonnull.map(lambda value: isinstance(value, (datetime, date, pd.Timestamp, np.datetime64))).all():
            kind = "date"
            series = pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)
        elif is_numeric_dtype(series.dtype):
            oversized_integers = nonnull.map(lambda value: isinstance(value, (int, np.integer)) and abs(int(value)) > 2**53 - 1)
            if oversized_integers.any():
                kind = "category"
                series = series.map(lambda value: str(value) if pd.notna(value) else np.nan)
                issues.append(_issue("identifier", "Integers beyond exact browser numeric precision are preserved as labels.", name, severity="info"))
            else:
                kind = "numeric"
                # Float arithmetic avoids silent int64 wraparound in sums of
                # otherwise moderate finite integers. Original integers remain
                # in the uploaded frame for export and explicit cleaning.
                series = series.astype(float)
        else:
            texts = nonnull.astype(str).str.strip()
            iso = texts.map(_parse_iso)
            numeric_matches = texts.str.fullmatch(NUMBER)
            leading_zero = texts.str.match(r"^[+-]?0\d+$").any()
            long_integer = texts.str.match(r"^[+-]?\d{16,}$").any()
            if iso.notna().all():
                kind = "date"
                series = series.map(lambda value: _parse_iso(str(value).strip()) if pd.notna(value) else pd.NaT)
                series = pd.to_datetime(series, errors="coerce")
            elif numeric_matches.all() and not leading_zero and not long_integer:
                kind = "numeric"
                converted = pd.to_numeric(series.astype("string").str.strip().str.replace(",", "", regex=False), errors="coerce")
                series = converted.astype(float)
                invalid = converted.isna() & frame[name].notna() & frame[name].map(lambda value: not isinstance(value, str) or bool(value.strip()))
                invalid |= series.notna() & ~np.isfinite(series)
                if invalid.any():
                    issues.append(_issue("nonfinite", "Numbers outside the finite supported range are treated as missing.", name, int(invalid.sum())))
                    series = series.mask(invalid, np.nan)
                text_count = int(nonnull.map(lambda value: isinstance(value, str)).sum())
                if text_count:
                    issues.append(_issue("numeric_text", "Numeric text was parsed using decimal/scientific notation and English thousands grouping; the source is unchanged.", name, text_count, "info"))
            else:
                kind = "category" if leading_zero or long_integer else _categorical_type(series, name)
                if leading_zero or long_integer:
                    issues.append(_issue("identifier", "Leading-zero or long digit strings are preserved as labels to avoid losing identifiers or precision.", name, severity="info"))
                if texts.str.match(DATE_LIKE).any() or iso.notna().any():
                    issues.append(_issue("date_format", "Date-like values include ambiguous, inconsistent, or invalid formats. Only complete valid ISO dates (YYYY-MM-DD) and native Excel dates are inferred.", name, int(texts.str.match(DATE_LIKE).sum())))
                value_types = nonnull.map(lambda value: "number" if isinstance(value, (int, float, np.number)) else "date" if isinstance(value, (date, datetime)) else "text").nunique()
                if (numeric_matches.any() and not numeric_matches.all()) or value_types > 1:
                    issues.append(_issue("mixed_types", "This column mixes numeric and nonnumeric values or native data types; values remain labels.", name, len(nonnull)))
        frame[name] = series
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        if missing:
            issues.append(_issue("missing", f"{missing:,} missing values ({missing / len(frame) * 100:.1f}% of records).", name, missing))
        if unique == 1:
            issues.append(_issue("constant", "All nonmissing records contain the same value.", name, len(series.dropna()), "info"))
        if kind == "numeric" and len(series.dropna()) >= 4:
            numeric = pd.to_numeric(series, errors="coerce").dropna().astype(float)
            scale = float(numeric.abs().max())
            numeric = numeric / scale if scale else numeric
            q1, q3 = numeric.quantile([0.25, 0.75])
            iqr = q3 - q1
            count = int(((numeric < q1 - 1.5 * iqr) | (numeric > q3 + 1.5 * iqr)).sum())
            if count:
                issues.append(_issue("outlier", "Potential unusual values lie outside Q1 − 1.5×IQR and Q3 + 1.5×IQR. These are flags, not confirmed errors.", name, count))
        if kind in {"category", "text"} and not _identifier(name):
            labels = series.dropna().astype(str)
            normalized = labels.str.strip().str.casefold()
            variants = pd.DataFrame({"original": labels, "normalized": normalized}).groupby("normalized")["original"].nunique()
            inconsistent = set(variants[variants > 1].index)
            if inconsistent:
                issues.append(_issue("category_variants", "Labels differ only by surrounding whitespace or letter case. They remain separate until explicitly cleaned.", name, int(normalized.isin(inconsistent).sum())))
        columns.append({"name": name, "type": kind, "missing": missing, "unique": unique})
    return frame, columns, issues


def _finite_bound(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite number.")
    return float(value)


def apply_filters(frame: pd.DataFrame, columns: list[dict], filters: dict | None) -> pd.DataFrame:
    if filters is None:
        return frame.copy()
    if not isinstance(filters, dict):
        raise ValueError("Filters must be an object keyed by column name.")
    schema = {column["name"]: column["type"] for column in columns}
    mask = pd.Series(True, index=frame.index)
    for name, config in filters.items():
        if name not in schema:
            raise ValueError(f"Unknown filter column: {name}.")
        if not isinstance(config, dict):
            raise ValueError(f"Filter for {name} must be an object.")
        kind = schema[name]
        supported = {"min", "max"} if kind == "numeric" else {"start", "end"} if kind == "date" else {"values"}
        if set(config) - supported:
            raise ValueError(f"Unsupported filter options for {name} ({kind}).")
        if kind == "numeric":
            bounds = {key: _finite_bound(value, f"{name} {key}") for key, value in config.items()}
            if "min" in bounds and "max" in bounds and bounds["min"] > bounds["max"]:
                raise ValueError(f"Minimum exceeds maximum for {name}.")
            if "min" in bounds:
                mask &= frame[name] >= bounds["min"]
            if "max" in bounds:
                mask &= frame[name] <= bounds["max"]
        elif kind == "date":
            dates = {}
            for key, value in config.items():
                dates[key] = _parse_iso(value)
                if dates[key] is None:
                    raise ValueError(f"{name} {key} must be a valid ISO date.")
            if "start" in dates and "end" in dates and dates["start"] > dates["end"]:
                raise ValueError(f"Start date exceeds end date for {name}.")
            if "start" in dates:
                mask &= frame[name] >= dates["start"]
            if "end" in dates:
                end = dates["end"]
                if len(str(config["end"])) == 10:
                    mask &= frame[name] < end + pd.Timedelta(days=1)
                else:
                    mask &= frame[name] <= end
        elif "values" in config:
            values = config["values"]
            if not isinstance(values, list) or len(values) > 500 or not all(isinstance(value, str) for value in values):
                raise ValueError(f"Values for {name} must be a list of at most 500 text labels.")
            mask &= frame[name].notna() & frame[name].map(_label).isin(values)
    return frame.loc[mask.fillna(False)].copy()


def _chart(kind: str, title: str, description: str, data: list[dict], x: str = "label", ys: list[str] | None = None, x_label: str = "", y_label: str = "", alternatives: list[str] | None = None, identity: str = "") -> dict:
    return {"id": identity or f"{kind}-{x_label}-{y_label}", "type": kind, "title": title, "description": description, "x_label": x_label, "y_label": y_label, "x_key": x, "y_keys": ys or ["value"], "data": data, "alternatives": alternatives or [kind]}


def _aggregation(name: str) -> str:
    return "mean" if NO_SUM.search(name) else "sum"


def _aggregate(frame: pd.DataFrame, x: str, y: str | None, aggregation: str, sort: str = "desc", top_n: int = 10, group_labels: pd.Series | None = None) -> tuple[list[dict], int]:
    valid = frame.loc[frame[x].notna()].copy()
    labels = valid[x].map(_label) if group_labels is None else group_labels.loc[valid.index]
    if aggregation == "count":
        grouped = valid.groupby(labels, sort=True).size()
    elif y:
        grouped_obj = valid.groupby(labels, sort=True)[y]
        grouped = grouped_obj.sum(min_count=1) if aggregation == "sum" else grouped_obj.agg(aggregation)
    else:
        raise ValueError("Choose a numeric Y column for this aggregation.")
    grouped = grouped.replace([np.inf, -np.inf], np.nan).dropna()
    total_groups = len(grouped)
    if sort == "label":
        grouped = grouped.sort_index()
    else:
        grouped = grouped.sort_values(ascending=sort == "asc", kind="stable")
    return [{"label": str(label), "value": _number(value)} for label, value in grouped.head(top_n).items()], total_groups


def _histogram(frame: pd.DataFrame, name: str) -> dict:
    values = frame[name].dropna().to_numpy(dtype=float)
    if not len(values):
        return _chart("histogram", f"{name} distribution", "No numeric observations in this selection.", [], x_label=name, y_label="Records")
    # A constant input gets one meaningful bucket. Quantile tails remain visible.
    if np.min(values) == np.max(values):
        data = [{"label": f"{values[0]:.6g}", "value": len(values)}]
    else:
        # Scale before bin construction so finite opposite extremes cannot make
        # NumPy overflow while calculating the range or bucket indices.
        scale = max(abs(float(values.min())), abs(float(values.max())))
        with np.errstate(over="ignore", invalid="ignore"):
            counts, edges = np.histogram(values / scale, bins=min(12, max(2, math.ceil(math.sqrt(len(values))))))
            edges = edges * scale
        data = [{"label": f"{edges[index]:.5g} – {edges[index + 1]:.5g}", "value": int(count), "start": _number(edges[index]), "end": _number(edges[index + 1])} for index, count in enumerate(counts)]
    return _chart("histogram", f"{name} distribution", "Frequency in equal-width intervals; the final interval includes its upper boundary. Missing values are excluded.", data, x_label=name, y_label="Records")


def _time_data(frame: pd.DataFrame, x: str, y: str | None, aggregation: str) -> tuple[list[dict], str]:
    valid = frame.loc[frame[x].notna()].copy()
    if valid.empty:
        return [], "day"
    span = (valid[x].max().date() - valid[x].min().date()).days
    frequency, period = ("D", "day") if span <= 90 else ("M", "month") if span <= 3650 else ("Y", "year")
    labels = valid[x].dt.to_period(frequency).astype(str)
    rows, _ = _aggregate(valid, x, y, aggregation, "label", 500, group_labels=labels)
    return rows, period


def _unit(name: str) -> str | None:
    text = name.lower()
    if NO_SUM.search(text):
        return None
    if re.search(r"revenue|expense|spend|cost|sales|amount|profit|income|budget|usd|inr|eur", text):
        # Mixed explicit currencies must never be stacked.
        currency = re.search(r"\b(usd|inr|eur|gbp|jpy)\b", text)
        return f"money:{currency.group(1)}" if currency else "money"
    for unit in ("hours", "minutes", "units", "quantity", "kg", "kilograms", "litres", "liters"):
        if re.search(rf"\b{unit}\b", text):
            return unit
    return None


def _compatible(first: str, second: str) -> bool:
    return bool(_unit(first) and _unit(first) == _unit(second))


def _auto_stackable(first: str, second: str) -> bool:
    """Only explicit components of the same measure can be auto-stacked.

    Revenue with cost/profit, and total/net/gross measures, overlap or have
    different meanings even when their currency units happen to agree.
    """
    if not _compatible(first, second) or re.search(r"\b(total|net|gross|profit|balance|budget)\b", f"{first} {second}", re.I):
        return False
    first_words = set(re.findall(r"[a-z]+", first.lower()))
    second_words = set(re.findall(r"[a-z]+", second.lower()))
    measures = {"revenue", "sales", "expenses", "expense", "cost", "costs", "hours", "minutes", "units", "quantity", "kg", "kilograms", "litres", "liters"}
    shared = first_words & second_words & measures
    return bool(shared and first_words - second_words and second_words - first_words)


def _stacked(frame: pd.DataFrame, x: str, y: str, second: str, aggregation: str, sort: str, top_n: int) -> dict:
    if aggregation != "sum":
        raise ValueError("Stacked charts require sums of compatible measures; choose a bar chart for other aggregations.")
    if not _compatible(y, second):
        raise ValueError("Stacked measures must have compatible explicit units (for example two amount columns).")
    if (frame[[y, second]].dropna(how="all") < 0).any().any():
        raise ValueError("Stacked charts require nonnegative values.")
    valid = frame.loc[frame[x].notna()].copy()
    grouped = valid.groupby(valid[x].map(_label))[[y, second]].sum(min_count=1).replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if sort == "label":
        grouped = grouped.sort_index()
    else:
        grouped = grouped.loc[grouped.sum(axis=1).sort_values(ascending=sort == "asc", kind="stable").index]
    total = len(grouped)
    data = [{"label": str(label), "series_1": _number(row[y]), "series_2": _number(row[second])} for label, row in grouped.head(top_n).iterrows()]
    chart = _chart("stacked_bar", f"{y} and {second} by {x}", f"Sums of {y} and {second}; verify that these are separate, non-overlapping components with the same units. Showing {min(top_n, total)} of {total} categories; missing groups are excluded.", data, ys=["series_1", "series_2"], x_label=x, y_label=f"{y} / {second}", alternatives=["stacked_bar", "bar"])
    chart["series_labels"] = {"series_1": y, "series_2": second}
    return chart


def _numeric_columns(columns: list[dict]) -> list[str]:
    names = [column["name"] for column in columns if column["type"] == "numeric" and not _identifier(column["name"])]
    return sorted(names, key=lambda name: (not bool(re.search(r"revenue|sales|amount|expense|score|marks|quantity|stock", name, re.I)), names.index(name)))


def _auto_charts(frame: pd.DataFrame, columns: list[dict]) -> list[dict]:
    if frame.empty:
        return []
    numeric = [name for name in _numeric_columns(columns) if frame[name].notna().any()]
    categories = [column["name"] for column in columns if column["type"] == "category" and frame[column["name"]].nunique() > 1 and not _identifier(column["name"])]
    dates = [column["name"] for column in columns if column["type"] == "date" and frame[column["name"]].notna().any()]
    charts = []
    if numeric:
        y = numeric[0]
        aggregation = _aggregation(y)
        if dates:
            data, period = _time_data(frame, dates[0], y, aggregation)
            if len(data) > 1:
                charts.append(_chart("line", f"{y} by {period}", f"{aggregation.title()} per observed {period}; absent periods are not filled or estimated.", data, x_label=dates[0], y_label=f"{aggregation.title()} {y}", alternatives=["line", "bar"]))
        if categories:
            x = categories[0]
            data, total = _aggregate(frame, x, y, aggregation)
            kind = "horizontal_bar" if total > 7 or any(len(row["label"]) > 18 for row in data) else "bar"
            charts.append(_chart(kind, f"{y} by {x}", f"{aggregation.title()} of {y}. Top {len(data)} of {total} categories by value; rows missing {x} are excluded.", data, x_label=x, y_label=f"{aggregation.title()} {y}", alternatives=["bar", "horizontal_bar"]))
            if aggregation == "sum" and 2 <= total <= 6 and data and all(row["value"] >= 0 for row in data) and sum(row["value"] for row in data) > 0:
                charts.append(_chart("pie", f"Share of {y}", f"Each category's share of the nonnegative total {y}; rows missing {x} are excluded.", data, x_label=x, y_label=f"Sum {y}", alternatives=["pie", "doughnut", "bar", "horizontal_bar"]))
        charts.append(_histogram(frame, y))
        if len(numeric) >= 2:
            valid = frame[[numeric[0], numeric[1]]].dropna()
            if len(valid) >= 3 and valid.nunique().min() > 1:
                subset = valid.iloc[np.linspace(0, len(valid) - 1, min(500, len(valid)), dtype=int)]
                charts.append(_chart("scatter", f"{numeric[0]} vs {numeric[1]}", f"{len(subset):,} of {len(valid):,} complete observations, sampled evenly by row when needed. Association does not establish causation.", [{"x": _number(a), "y": _number(b)} for a, b in subset.itertuples(index=False, name=None)], x="x", ys=["y"], x_label=numeric[0], y_label=numeric[1]))
            second = next((other for other in numeric[1:] if _auto_stackable(y, other)), None)
            if categories and second and not (frame[[y, second]] < 0).any().any():
                charts.append(_stacked(frame, categories[0], y, second, "sum", "desc", 10))
    if categories and (not numeric or len(charts) < 6):
        x = categories[1] if len(categories) > 1 and numeric else categories[0]
        data, total = _aggregate(frame, x, None, "count")
        kind = "doughnut" if 2 <= total <= 6 else "horizontal_bar"
        charts.append(_chart(kind, f"Records by {x}", f"Record count in each category. Showing {len(data)} of {total} categories; missing labels are excluded.", data, x_label=x, y_label="Records", alternatives=["doughnut", "pie", "bar", "horizontal_bar"] if total <= 6 else ["bar", "horizontal_bar"]))
    return charts[:6]


def _filter_options(frame: pd.DataFrame, columns: list[dict]) -> list[dict]:
    output = []
    for column in columns:
        name, kind = column["name"], column["type"]
        valid = frame[name].dropna()
        if valid.empty:
            continue
        if kind == "category" and valid.nunique() <= 200 and not _identifier(name):
            output.append({"column": name, "type": kind, "options": sorted({_label(value) for value in valid})})
        elif kind in {"numeric", "date"}:
            output.append({"column": name, "type": kind, "min": _scalar(valid.min()), "max": _scalar(valid.max())})
    return output


def _kpis(frame: pd.DataFrame, columns: list[dict]) -> list[dict]:
    kpis = [{"label": "Total records", "value": len(frame), "description": "Rows in the current selection", "format": "number"}]
    numeric = [name for name in _numeric_columns(columns) if frame[name].notna().any()]
    if numeric:
        name = numeric[0]
        series = frame[name].dropna()
        stats = _statistics(series)
        calculations = [("Average", stats["mean"]), ("Median", stats["median"]), ("Minimum", stats["min"]), ("Maximum", stats["max"])]
        if _aggregation(name) == "sum":
            calculations.insert(0, ("Total", stats["sum"]))
        for label, value in calculations:
            if _number(value) is not None:
                kpis.append({"label": f"{label} {name}", "value": _number(value), "description": f"Based on {len(series):,} nonmissing values", "format": "decimal"})
    category = next((column["name"] for column in columns if column["type"] == "category" and not _identifier(column["name"]) and frame[column["name"]].nunique() > 1), None)
    if category:
        kpis.append({"label": f"Unique {category}", "value": int(frame[category].nunique()), "description": "Distinct nonmissing labels", "format": "number"})
    dated = next((column["name"] for column in columns if column["type"] == "date" and frame[column["name"]].notna().any()), None)
    if dated:
        kpis.append({"label": f"{dated} range", "value": f"{frame[dated].min():%d %b %Y} – {frame[dated].max():%d %b %Y}", "description": "First and last observed dates"})
    return kpis


def _insights(frame: pd.DataFrame, columns: list[dict], charts: list[dict], quality: dict) -> list[dict]:
    if frame.empty:
        return [{"title": "No matching records", "text": "Reset or adjust the filters to analyze records.", "kind": "info"}]
    insights = []
    if quality["missing_cells"]:
        insights.append({"title": "Missing values", "text": f"{quality['missing_cells']:,} cells ({quality['missing_percent']:.1f}%) are missing in the current selection. Numeric calculations exclude missing values.", "kind": "warning"})
    if quality["duplicate_rows"]:
        insights.append({"title": "Duplicate records", "text": f"{quality['duplicate_rows']:,} repeated rows beyond their first occurrence are included in the current analysis. Review them before drawing conclusions.", "kind": "warning"})
    numeric = [name for name in _numeric_columns(columns) if frame[name].notna().any()]
    if numeric:
        name = numeric[0]
        series = frame[name].dropna()
        stats = _statistics(series)
        avg, median, minimum, maximum = [stats[key] for key in ("mean", "median", "min", "max")]
        if all(value is not None for value in (avg, median, minimum, maximum)):
            insights.append({"title": f"Understanding {name}", "text": f"{name} averages {_readable_number(avg)}, with median {_readable_number(median)} and observed values from {_readable_number(minimum)} to {_readable_number(maximum)} ({len(series):,} valid records).", "kind": "info"})
    comparison = next((chart for chart in charts if chart["type"] in {"bar", "horizontal_bar"} and chart["data"]), None)
    if comparison:
        top = comparison["data"][0]
        insights.append({"title": f"Highest {comparison['y_label']}", "text": f"{top['label']} has the highest {comparison['y_label'].lower()} at {_readable_number(top['value'])} among observed {comparison['x_label']} categories.", "kind": "info"})
    trend = next((chart for chart in charts if chart["type"] == "line" and len(chart["data"]) > 1), None)
    if trend:
        first, last = trend["data"][0], trend["data"][-1]
        difference = last["value"] - first["value"]
        verb = "increased" if difference > 0 else "decreased" if difference < 0 else "did not change"
        description = f"{trend['y_label']} {verb} from {_readable_number(first['value'])} in {first['label']} to {_readable_number(last['value'])} in {last['label']}."
        if first["value"] > 0:
            change = difference / first["value"] * 100
            if math.isfinite(change):
                description += f" Endpoint change: {change:+.1f}%."
        elif first["value"] == 0:
            description += " Percentage change is undefined because the starting value is zero."
        description += " These are observed periods; incomplete periods and missing records can affect the comparison."
        insights.append({"title": "Observed change over time", "text": description, "kind": "info"})
        peak = max(trend["data"], key=lambda row: row["value"])
        low = min(trend["data"], key=lambda row: row["value"])
        insights.append({"title": "Highest and lowest observed periods", "text": f"{peak['label']} has the highest {trend['y_label'].lower()} ({_readable_number(peak['value'])}); {low['label']} has the lowest ({_readable_number(low['value'])}).", "kind": "info"})
    correlations = []
    for index, first in enumerate(numeric[:8]):
        for second in numeric[index + 1:8]:
            pair = frame[[first, second]].dropna()
            if len(pair) >= 3 and pair.nunique().min() > 1:
                first_scale = float(pair[first].abs().max())
                second_scale = float(pair[second].abs().max())
                coefficient = (pair[first] / first_scale).corr(pair[second] / second_scale)
                if pd.notna(coefficient) and math.isfinite(coefficient):
                    correlations.append((abs(coefficient), coefficient, first, second, len(pair)))
    if correlations:
        _, value, first, second, count = max(correlations)
        insights.append({"title": "Numeric relationship", "text": f"{first} and {second} have Pearson correlation r = {value:.2f} across {count:,} complete records. Correlation measures linear association and does not establish causation.", "kind": "info"})
    flagged = [issue for issue in quality["issues"] if issue["type"] == "outlier"]
    if flagged:
        issue = flagged[0]
        insights.append({"title": "Values worth reviewing", "text": f"{issue['column']} contains {issue['count']:,} potential unusual values using the 1.5×IQR rule. They may be valid observations; they have not been removed.", "kind": "warning"})
    if not numeric:
        insights.append({"title": "Categorical analysis", "text": "No suitable numeric measures were identified. Category frequencies describe the available labels; numeric trends and correlations are unavailable.", "kind": "info"})
    return insights[:9]


def analyze_frame(raw: pd.DataFrame, filename: str, sheet: str, filters: dict | None = None, version: str = "original") -> dict:
    frame, original_columns, original_issues = prepare_frame(raw)
    selected = apply_filters(frame, original_columns, filters)
    columns = [{**column, "missing": int(selected[column["name"]].isna().sum()), "unique": int(selected[column["name"]].nunique(dropna=True))} for column in original_columns]
    issues = original_issues if not filters else prepare_frame(raw.iloc[selected.index])[2]
    missing = int(selected.isna().sum().sum())
    duplicate_rows = int(raw.iloc[selected.index].duplicated().sum())
    if duplicate_rows:
        issues = [*issues, _issue("duplicates", "Repeated rows are included in the analysis until explicitly removed.", count=duplicate_rows)]
    quality = {"missing_cells": missing, "missing_percent": round(missing / selected.size * 100, 4) if selected.size else 0.0, "duplicate_rows": duplicate_rows, "issues": issues}
    charts = _auto_charts(selected, columns)
    notes = ["Original source values are preserved. Analyses treat blank strings and nonfinite numbers as missing. Calculations outside the finite numeric range are omitted.", "Dates are inferred only from native Excel dates or complete, valid ISO values. Numeric text uses decimal/scientific notation or English thousands groups; currency symbols and decimal commas are not guessed.", "Automatic comparisons use averages for scores, academic subjects, rates, ages, prices, and similar measures; other numeric measures use sums. Review the aggregation against your data's meaning.", "Category filters are offered for at most 200 distinct labels. Category charts show their stated top-N; omitted categories are never presented as the whole in a pie or doughnut."]
    if any(issue["type"] == "identifier" for issue in original_issues):
        notes.append("Identifier-like columns are excluded from automatic numeric metrics.")
    if not any(column["type"] == "date" for column in columns):
        notes.append("No unambiguous date column was identified, so no time-series chart is generated.")
    if len(charts) < 2:
        notes.append("This selection has too few suitable columns or observations for additional meaningful charts.")
    return {"filename": filename, "sheet": sheet, "version": version, "rows": len(selected), "total_rows": len(frame), "column_count": len(columns), "analyzed_at": datetime.now(timezone.utc).isoformat(), "columns": columns, "kpis": _kpis(selected, columns), "charts": charts, "insights": _insights(selected, columns, charts, quality), "quality": quality, "filters": _filter_options(frame, original_columns), "notes": notes}


def preview_frame(raw: pd.DataFrame, filters: dict | None = None, page: int = 1, page_size: int = 25, search: str = "") -> dict:
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("Page must be a positive integer.")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 100:
        raise ValueError("Page size must be between 1 and 100.")
    if not isinstance(search, str) or len(search) > 200:
        raise ValueError("Search must be text of at most 200 characters.")
    frame, columns, _ = prepare_frame(raw)
    selected = apply_filters(frame, columns, filters)
    columns = [{**column, "missing": int(selected[column["name"]].isna().sum()), "unique": int(selected[column["name"]].nunique())} for column in columns]
    if search.strip():
        matching = selected.astype("string").apply(lambda values: values.str.contains(search.strip(), case=False, regex=False, na=False)).any(axis=1)
        selected = selected.loc[matching]
    total = len(selected)
    total_pages = max(1, math.ceil(total / page_size))
    page = min(page, total_pages)
    start = (page - 1) * page_size
    return {"columns": columns, "rows": _records(selected.iloc[start:start + page_size]), "total_rows": total, "page": page, "page_size": page_size, "total_pages": total_pages}


def custom_chart(raw: pd.DataFrame, config: dict, filters: dict | None = None) -> dict:
    if not isinstance(config, dict):
        raise ValueError("Chart configuration must be an object.")
    frame, columns, _ = prepare_frame(raw)
    frame = apply_filters(frame, columns, filters)
    schema = {column["name"]: column["type"] for column in columns}
    kind, x, y = config.get("type", "bar"), config.get("x"), config.get("y") or None
    aggregation, sort, top_n = config.get("aggregation", "sum"), config.get("sort", "desc"), config.get("top_n", 10)
    if not isinstance(kind, str) or kind not in CHART_TYPES:
        raise ValueError("Choose a supported chart type.")
    if not isinstance(x, str) or x not in schema:
        raise ValueError("Choose a valid X-axis column.")
    if y is not None and (not isinstance(y, str) or y not in schema or schema[y] != "numeric"):
        raise ValueError("Choose a numeric Y-axis column.")
    if not isinstance(aggregation, str) or aggregation not in AGGREGATIONS:
        raise ValueError("Choose a supported aggregation.")
    if not isinstance(sort, str) or sort not in {"asc", "desc", "label"}:
        raise ValueError("Sort must be asc, desc, or label.")
    if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 50:
        raise ValueError("Top N must be between 1 and 50.")
    if kind == "histogram":
        if schema[x] != "numeric":
            raise ValueError("A histogram needs a numeric X-axis column.")
        return _histogram(frame, x)
    if kind == "scatter":
        if schema[x] != "numeric" or not y or y == x:
            raise ValueError("A scatter plot needs two different numeric columns.")
        valid = frame[[x, y]].dropna()
        subset = valid.iloc[np.linspace(0, len(valid) - 1, min(500, len(valid)), dtype=int)] if len(valid) else valid
        return _chart("scatter", f"{x} vs {y}", f"{len(subset):,} of {len(valid):,} complete records; sampled evenly by row when more than 500. Values are not aggregated.", [{"x": _number(a), "y": _number(b)} for a, b in subset.itertuples(index=False, name=None)], x="x", ys=["y"], x_label=x, y_label=y)
    if not y and aggregation != "count":
        raise ValueError("Choose a numeric Y-axis column, or select the count aggregation.")
    if kind == "line":
        if schema[x] != "date":
            raise ValueError("A trend line needs an unambiguous date X-axis column.")
        data, period = _time_data(frame, x, y, aggregation)
        return _chart("line", f"{'Records' if aggregation == 'count' else y} by {period}", f"{aggregation.title()} per observed {period}; absent periods are not estimated.", data, x_label=x, y_label="Records" if aggregation == "count" else f"{aggregation.title()} {y}", alternatives=["line", "bar"])
    if schema[x] not in {"category", "text"}:
        raise ValueError("Choose a categorical X-axis for comparison charts; use a histogram for numeric distributions or a line for dates.")
    if kind == "stacked_bar":
        if not y:
            raise ValueError("Choose a numeric Y-axis for the stacked chart.")
        second = config.get("y2") or next((column for column, column_type in schema.items() if column_type == "numeric" and column != y and _compatible(y, column)), None)
        if not isinstance(second, str) or second not in schema or schema[second] != "numeric" or second == y:
            raise ValueError("A stacked chart requires a second compatible numeric measure with explicit units.")
        return _stacked(frame, x, y, second, aggregation, sort, top_n)
    data, total = _aggregate(frame, x, y, aggregation, sort, top_n)
    alternatives = ["bar", "horizontal_bar"]
    if kind in {"pie", "doughnut"}:
        if aggregation not in {"sum", "count"}:
            raise ValueError("Part-of-whole charts require sum or count; averages and other statistics are not additive.")
        if total > 8 or total > top_n:
            raise ValueError("Pie and doughnut charts need at most eight categories and must include the whole selection. Filter categories or use a bar chart.")
        if data and (any(row["value"] < 0 for row in data) or sum(row["value"] for row in data) <= 0):
            raise ValueError("Pie and doughnut charts require nonnegative values with a positive total.")
        alternatives = ["pie", "doughnut", "bar", "horizontal_bar"]
    title = f"{'Records' if aggregation == 'count' else y} by {x}"
    return _chart(kind, title, f"{aggregation.title()}; showing {len(data)} of {total} categories. Missing category labels are excluded. Count measures records regardless of missing Y values.", data, x_label=x, y_label="Records" if aggregation == "count" else f"{aggregation.title()} {y}", alternatives=alternatives)
