"""Explicit cleaning operations always start from the original worksheet."""
import pandas as pd

from app.analytics.engine import prepare_frame, preview_frame


def clean_frame(original, operations):
    if not isinstance(operations, list) or not operations or len(operations) > 30:
        raise ValueError("Choose between 1 and 30 cleaning operations.")
    result = original.copy(deep=True)
    changed = 0
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("Each cleaning operation must be an object.")
        action = operation.get("action")
        if action == "drop_duplicates":
            result = result.drop_duplicates().reset_index(drop=True).copy()
            continue
        column = operation.get("column")
        if not isinstance(column, str) or column not in result.columns:
            raise ValueError("Choose a valid column for the cleaning operation.")
        typed, columns, _ = prepare_frame(result)
        column_type = next(item["type"] for item in columns if item["name"] == column)
        method = operation.get("method")
        if action == "fill_numeric":
            if column_type != "numeric" or method not in ("mean", "median", "zero"):
                raise ValueError("Numeric filling requires a numeric column and mean, median, or zero.")
            series = typed[column]
            value = 0 if method == "zero" else getattr(series, method)()
            if pd.isna(value):
                raise ValueError("This column has no valid numbers for the selected fill method.")
        elif action == "fill_category":
            if column_type not in ("category", "text") or method not in ("mode", "unknown"):
                raise ValueError("Category filling requires a text/category column and mode or unknown.")
            series = result[column].replace(r"^\s*$", None, regex=True)
            modes = series.mode(dropna=True)
            if method == "mode" and modes.empty:
                raise ValueError("This column has no category from which to calculate a mode.")
            value = "Unknown" if method == "unknown" else modes.iloc[0]
        else:
            raise ValueError("This cleaning action is unsupported.")
        mask = series.isna()
        changed += int(mask.sum())
        result.loc[mask, column] = value
    return result, {"before_rows": len(original), "after_rows": len(result), "changed_cells": changed,
                    "preview": preview_frame(result, page=1, page_size=10)["rows"]}
