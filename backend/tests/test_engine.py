"""Analytics contracts tested with independent expected numerical results."""

import json

import numpy as np
import pandas as pd
import pytest

from app.analytics.engine import analyze_frame, apply_filters, custom_chart, prepare_frame, preview_frame


def metric(analysis, label):
    return next(item["value"] for item in analysis["kpis"] if item["label"] == label)


def test_strict_inference_preserves_ids_ambiguous_dates_and_original():
    source = pd.DataFrame({
        "StudentID": [123, 456, 789],
        "Account": ["001", "002", "003"],
        "Value": ["1,200.50", "3e2", " -2 "],
        "ISO": ["2025-01-04", "2025-02-04", None],
        "Ambiguous": ["01/02/2025", "02/03/2025", "03/04/2025"],
        "Bad ISO": ["2025-01-04", "2025-02-30", "2025-03-04"],
        "Mixed": [10, "unknown", "20"],
    })
    original = source.copy(deep=True)
    frame, columns, issues = prepare_frame(source)
    types = {column["name"]: column["type"] for column in columns}
    assert types == {"StudentID": "category", "Account": "category", "Value": "numeric", "ISO": "date", "Ambiguous": "category", "Bad ISO": "category", "Mixed": "category"}
    assert frame["Value"].tolist() == [1200.5, 300, -2]
    assert frame["Account"].tolist() == ["001", "002", "003"]
    assert {issue["column"] for issue in issues if issue["type"] == "date_format"} == {"Ambiguous", "Bad ISO"}
    assert any(issue["type"] == "mixed_types" and issue["column"] == "Mixed" for issue in issues)
    pd.testing.assert_frame_equal(source, original)


def test_native_dates_booleans_missing_nonfinite_and_headers():
    source = pd.DataFrame([[pd.Timestamp("2025-01-01"), True, float("inf"), " "], [pd.Timestamp("2025-01-02"), False, 3, None]], columns=["Date", "Flag", "Value", None])
    frame, columns, issues = prepare_frame(source)
    assert [column["type"] for column in columns] == ["date", "category", "numeric", "numeric"]
    assert frame["Value"].isna().sum() == 1
    assert columns[3]["name"] == "Column 4"
    assert columns[3]["missing"] == 2
    assert any(issue["type"] == "nonfinite" for issue in issues)
    repeated = pd.DataFrame([[1, 2, 3]], columns=["A", "A", "A (2)"])
    assert [column["name"] for column in prepare_frame(repeated)[1]] == ["A", "A (2)", "A (2) (2)"]


def test_missing_duplicate_category_variant_and_iqr_counts():
    source = pd.DataFrame({"Group": ["North", "north", "North", "North", "North", None, "North"], "Amount": [10, 10, 10, 10, 100, np.nan, 10]})
    result = analyze_frame(source, "quality.csv", "Data")
    quality = result["quality"]
    assert quality["missing_cells"] == 2
    assert quality["missing_percent"] == pytest.approx(100 * 2 / 14, abs=0.0001)
    assert quality["duplicate_rows"] == 3
    assert next(issue["count"] for issue in quality["issues"] if issue["type"] == "outlier") == 1
    assert next(issue["count"] for issue in quality["issues"] if issue["type"] == "category_variants") == 6


def test_filter_updates_all_analysis_and_keeps_original_filter_choices():
    source = pd.DataFrame({"Department": ["A", "A", "B", "B"], "Revenue": [10, 30, 200, None], "Date": ["2025-01-01", "2025-01-02", "2025-01-01", "2025-01-02"]})
    filtered = analyze_frame(source, "sales.csv", "Data", {"Department": {"values": ["A"]}})
    assert filtered["rows"] == 2
    assert filtered["total_rows"] == 4
    assert metric(filtered, "Total Revenue") == 40
    assert metric(filtered, "Average Revenue") == 20
    assert filtered["quality"]["missing_cells"] == 0
    assert not any(issue["type"] == "missing" for issue in filtered["quality"]["issues"])
    assert next(item["options"] for item in filtered["filters"] if item["column"] == "Department") == ["A", "B"]
    line = next(chart for chart in filtered["charts"] if chart["type"] == "line")
    assert [point["value"] for point in line["data"]] == [10, 30]
    assert any("200.0%" in item["text"] for item in filtered["insights"])


def test_date_end_filter_includes_entire_day_and_numeric_range():
    raw = pd.DataFrame({"Date": ["2025-01-01T10:00:00", "2025-01-01T23:59:00", "2025-01-02T00:00:00"], "Amount": [10, 20, 30]})
    frame, columns, _ = prepare_frame(raw)
    result = apply_filters(frame, columns, {"Date": {"end": "2025-01-01"}, "Amount": {"min": 15}})
    assert result["Amount"].tolist() == [20]


@pytest.mark.parametrize("filters", [[], {"absent": {"min": 1}}, {"Value": {"min": 20, "max": 1}}, {"Value": {"min": float("inf")}}, {"Value": {"min": True}}, {"Value": {"values": ["1"]}}, {"Label": {"values": "A"}}, {"Date": {"start": "01/02/2025"}}, {"Date": {"start": "2025-02-01", "end": "2025-01-01"}}])
def test_invalid_filters_raise_readable_validation_errors(filters):
    raw = pd.DataFrame({"Value": [1, 2], "Label": ["A", "B"], "Date": ["2025-01-01", "2025-01-02"]})
    frame, columns, _ = prepare_frame(raw)
    with pytest.raises(ValueError):
        apply_filters(frame, columns, filters)


def test_no_dates_no_numeric_single_column_and_empty_results():
    text = analyze_frame(pd.DataFrame({"Department": ["Arts", "Science", "Arts"]}), "labels.csv", "Data")
    assert {chart["type"] for chart in text["charts"]} == {"doughnut"}
    assert metric(text, "Total records") == 3
    assert not any("Revenue" in item["label"] for item in text["kpis"])
    marks = analyze_frame(pd.DataFrame({"Marks": [60, 80, 100]}), "marks.csv", "Data")
    assert {chart["type"] for chart in marks["charts"]} == {"histogram"}
    assert metric(marks, "Average Marks") == 80
    assert not any(item["label"] == "Total Marks" for item in marks["kpis"])
    empty = analyze_frame(pd.DataFrame({"Amount": [1, 2]}), "values.csv", "Data", {"Amount": {"min": 100}})
    assert empty["charts"] == []
    assert empty["rows"] == empty["quality"]["missing_cells"] == 0
    assert empty["insights"][0]["title"] == "No matching records"
    json.dumps(empty, allow_nan=False)


def test_auto_charts_select_real_shapes_and_bounded_high_cardinality():
    sales = pd.DataFrame({"Date": pd.date_range("2025-01-01", periods=12), "Region": ["A", "B", "C"] * 4, "Revenue": list(range(10, 130, 10)), "Cost": list(range(2, 26, 2))})
    analysis = analyze_frame(sales, "sales.csv", "Data")
    assert {chart["type"] for chart in analysis["charts"]} == {"line", "bar", "pie", "histogram", "scatter", "doughnut"}
    split_revenue = sales.rename(columns={"Revenue": "Online Revenue", "Cost": "Store Revenue"})
    assert any(chart["type"] == "stacked_bar" for chart in analyze_frame(split_revenue, "split.csv", "Data")["charts"])
    histogram = next(chart for chart in analysis["charts"] if chart["type"] == "histogram")
    assert sum(point["value"] for point in histogram["data"]) == len(sales)
    categories = pd.DataFrame({"Category": [f"Group {index}" for index in range(20)], "Value": list(range(20))})
    result = analyze_frame(categories, "many.csv", "Data")
    assert any(chart["type"] == "horizontal_bar" for chart in result["charts"])
    assert all(len(chart["data"]) <= 12 for chart in result["charts"])
    assert not any(chart["type"] in {"pie", "doughnut"} for chart in result["charts"])


@pytest.mark.parametrize("aggregation,expected", [("sum", 12), ("mean", 4), ("count", 4), ("min", 1), ("max", 9), ("median", 2)])
def test_custom_aggregations_and_missing_value_semantics(aggregation, expected):
    raw = pd.DataFrame({"Group": ["A", "A", "A", "A", "B"], "Value": [1, 2, 9, None, 100]})
    chart = custom_chart(raw, {"x": "Group", "y": "Value", "type": "bar", "aggregation": aggregation, "sort": "label"})
    assert chart["data"][0] == {"label": "A", "value": expected}


@pytest.mark.parametrize("config", [
    {"x": "Missing", "type": "bar"},
    {"x": "Group", "y": "Group", "type": "bar"},
    {"x": "Group", "y": "Value", "type": "line"},
    {"x": "Group", "type": "histogram"},
    {"x": "Value", "y": "Value", "type": "scatter"},
    {"x": "Group", "y": "Value", "type": "pie", "aggregation": "mean"},
    {"x": "Group", "y": "Value", "type": "pie", "aggregation": "sum"},
    {"x": "Group", "y": "Value", "type": "stacked_bar"},
    {"x": "Group", "y": "Value", "type": "bar", "top_n": 100},
    {"x": "Group", "y": "Value", "type": "bar", "sort": {}},
])
def test_custom_chart_rejects_nonsensical_combinations(config):
    raw = pd.DataFrame({"Group": ["A", "B"], "Value": [-10, 1]})
    with pytest.raises(ValueError):
        custom_chart(raw, config)


def test_pie_does_not_present_top_n_subset_as_whole():
    raw = pd.DataFrame({"Group": ["A", "B", "C"], "Amount": [1, 2, 3]})
    with pytest.raises(ValueError, match="whole selection"):
        custom_chart(raw, {"x": "Group", "y": "Amount", "type": "pie", "top_n": 2})


def test_stacked_units_and_nonnegative_values():
    raw = pd.DataFrame({"Group": ["A", "A", "B"], "Revenue": [1, 2, 3], "Cost": [4, 5, 6], "Marks": [80, 90, 100]})
    chart = custom_chart(raw, {"x": "Group", "y": "Revenue", "type": "stacked_bar"})
    assert chart["data"][0] == {"label": "A", "series_1": 3, "series_2": 9}
    with pytest.raises(ValueError, match="compatible"):
        custom_chart(raw, {"x": "Group", "y": "Revenue", "y2": "Marks", "type": "stacked_bar"})


def test_search_spans_all_records_pagination_and_sampling_are_bounded():
    raw = pd.DataFrame({"Name": [f"Person {index}" for index in range(1500)], "Value": range(1500), "Other": range(1500, 3000)})
    found = preview_frame(raw, page=1, page_size=10, search="Person 1499")
    assert found["total_rows"] == 1
    assert found["rows"][0]["Value"] == 1499
    assert preview_frame(raw, page=999, page_size=100)["page"] == 15
    assert len(preview_frame(raw, page_size=25)["rows"]) == 25
    chart = custom_chart(raw, {"x": "Value", "y": "Other", "type": "scatter"})
    assert len(chart["data"]) == 500
    assert chart["data"][0] == {"x": 0, "y": 1500}
    assert chart["data"][-1] == {"x": 1499, "y": 2999}
    with pytest.raises(ValueError):
        preview_frame(raw, page_size=101)
    with pytest.raises(ValueError):
        preview_frame(raw, search="a" * 201)


def test_zero_time_baseline_and_correlation_are_explicit():
    raw = pd.DataFrame({"Date": ["2025-01-01", "2025-01-02", "2025-01-03"], "Amount": [0, 10, 20], "Quantity": [0, 1, 2]})
    result = analyze_frame(raw, "zero.csv", "Data")
    text = " ".join(item["text"] for item in result["insights"])
    assert "undefined" in text
    assert "r = 1.00" in text
    assert "does not establish causation" in text


def test_all_outputs_are_strict_json_even_with_nonfinite_extreme_values():
    raw = pd.DataFrame({"Value": [float("inf"), np.nan, -1e308, 1e308, 1e308], "Group": ["A", "A", "B", "B", "C"]})
    result = analyze_frame(raw, "extremes.csv", "Data")
    json.dumps(result, allow_nan=False)
    json.dumps(preview_frame(raw), allow_nan=False)
    assert result["quality"]["missing_cells"] == 2
    assert sum(row["value"] for chart in result["charts"] if chart["type"] == "histogram" for row in chart["data"]) == 3


def test_large_numeric_identifiers_and_locale_strings_remain_labels():
    raw = pd.DataFrame({"Long": ["12345678901234567", "12345678901234568"], "Comma": ["1,20", "2,30"], "Currency": ["$10", "$20"]})
    _, columns, _ = prepare_frame(raw)
    assert all(column["type"] == "category" for column in columns)


def test_empty_frame_and_constant_numeric_are_valid():
    result = analyze_frame(pd.DataFrame(columns=["A", "B"]), "empty.csv", "Sheet1")
    assert result["rows"] == 0
    assert result["quality"]["missing_percent"] == 0
    json.dumps(result, allow_nan=False)
    constant = custom_chart(pd.DataFrame({"Value": [4, 4, 4]}), {"x": "Value", "type": "histogram"})
    assert constant["data"] == [{"label": "4", "value": 3}]


def test_internal_grouping_names_never_replace_uploaded_columns():
    raw = pd.DataFrame({"Group": ["A", "A", "B"], "__group_label": [10, 20, 30], "__period": [1, 2, 3], "Date": ["2025-01-01", "2025-01-02", "2025-01-03"]})
    chart = custom_chart(raw, {"x": "Group", "y": "__group_label", "type": "bar"})
    assert chart["data"] == [{"label": "A", "value": 30}, {"label": "B", "value": 30}]
    chart = custom_chart(raw, {"x": "Date", "y": "__period", "type": "line"})
    assert [row["value"] for row in chart["data"]] == [1, 2, 3]


def test_missing_nan_is_not_reported_as_infinity_and_subjects_use_means():
    raw = pd.DataFrame({"Math": [70, 90, np.nan], "Science": [75, 95, 85]})
    result = analyze_frame(raw, "students.csv", "Data")
    assert not any(issue["type"] == "nonfinite" for issue in result["quality"]["issues"])
    assert metric(result, "Average Math") == 80
    assert not any(item["label"] == "Total Math" for item in result["kpis"])
    assert not any(chart["type"] == "stacked_bar" for chart in result["charts"])


def test_high_cardinality_named_category_is_aggregated_but_filters_stay_bounded():
    raw = pd.DataFrame({"Product": [f"Item {i}" for i in range(1500)], "Amount": range(1500)})
    result = analyze_frame(raw, "products.csv", "Data")
    comparisons = [chart for chart in result["charts"] if chart["type"] == "horizontal_bar"]
    assert comparisons
    assert all(len(chart["data"]) == 10 for chart in comparisons)
    assert comparisons[0]["data"][0] == {"label": "Item 1499", "value": 1499}
    assert not any(item["column"] == "Product" for item in result["filters"])


def test_numeric_string_overflow_is_reported_without_classifying_blank_as_infinite():
    raw = pd.DataFrame({"Amount": ["1e309", "100", " ", None]})
    frame, _, issues = prepare_frame(raw)
    assert frame["Amount"].isna().sum() == 3
    assert next(issue["count"] for issue in issues if issue["type"] == "nonfinite") == 1


def test_large_native_integer_precision_and_aggregate_wraparound():
    identifiers = pd.DataFrame({"ID": [123456789012345678, 123456789012345679], "Big": [123456789012345678, 123456789012345679]})
    frame, columns, _ = prepare_frame(identifiers)
    assert frame.iloc[0].tolist() == ["123456789012345678", "123456789012345678"]
    assert all(column["type"] == "category" for column in columns)
    large_total = pd.DataFrame({"Amount": [9_000_000_000_000_000] * 1100})
    result = analyze_frame(large_total, "large.csv", "Data")
    assert metric(result, "Total Amount") == pytest.approx(9_900_000_000_000_000_000)


def test_extreme_finite_statistics_and_correlations_remain_correct():
    raw = pd.DataFrame({"Value": [-1e308, 1e308, 0], "Other": [1e308, -1e308, 0]})
    result = analyze_frame(raw, "extremes.csv", "Data")
    assert metric(result, "Average Value") == 0
    assert any("r = -1.00" in item["text"] for item in result["insights"])
    result = analyze_frame(pd.DataFrame({"Value": [1e308, 1e308, 1e308]}), "large.csv", "Data")
    assert metric(result, "Average Value") == 1e308
    assert metric(result, "Median Value") == 1e308
    assert not any(item["label"] == "Total Value" for item in result["kpis"])


def test_line_count_titles_are_records_even_when_y_was_selected():
    raw = pd.DataFrame({"Date": ["2025-01-01", "2025-01-02"], "Revenue": [5, 10]})
    chart = custom_chart(raw, {"type": "line", "x": "Date", "y": "Revenue", "aggregation": "count"})
    assert chart["title"] == "Records by day"
    assert [row["value"] for row in chart["data"]] == [1, 1]
