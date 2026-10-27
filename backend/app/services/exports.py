"""Vector PDF reports and safe spreadsheet exports from current results."""
from __future__ import annotations

from io import BytesIO
import math
import os
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, PolyLine
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PALETTE = [colors.HexColor(value) for value in ("#4f46e5", "#14b8a6", "#f59e0b", "#818cf8", "#ec4899", "#64748b")]
FONT = "Helvetica"
for candidate in (os.environ.get("REPORT_FONT", ""), "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
    if candidate and Path(candidate).is_file():
        try:
            pdfmetrics.registerFont(TTFont("SheetSense", candidate))
            FONT = "SheetSense"
            break
        except Exception:
            pass


def spreadsheet_bytes(frame, format):
    def safe(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + value
        return value
    output = frame.map(safe)
    # Headers are untrusted cells as well.
    output.columns = [safe(str(column)) for column in output.columns]
    if format == "csv":
        return output.to_csv(index=False).encode("utf-8-sig")
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        output.to_excel(writer, index=False, sheet_name="Processed data")
    return buffer.getvalue()


def _number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else 0.0
    except (ValueError, TypeError):
        return 0.0


def _short(value, maximum=19):
    text = str(value)
    return text if len(text) <= maximum else text[:maximum - 1] + "…"


def _finish_drawing(drawing):
    for child in drawing.contents:
        if isinstance(child, String):
            child.fontName = FONT
        elif isinstance(child, Pie):
            child.slices.fontName = FONT
    return drawing


def chart_drawing(chart):
    drawing = Drawing(480, 235)
    rows = chart.get("data", [])
    if not rows:
        drawing.add(String(15, 120, "No data matches the selected filters.", fontSize=10))
        return _finish_drawing(drawing)
    x_key, y_keys = chart["x_key"], chart.get("y_keys", [])
    if not y_keys:
        drawing.add(String(15, 120, "No numerical series available.", fontSize=10))
        return _finish_drawing(drawing)
    kind = chart["type"]
    if kind in ("pie", "doughnut"):
        pie = Pie()
        pie.x, pie.y, pie.width, pie.height = 125, 35, 200, 165
        pie.data = [max(0, _number(row.get(y_keys[0]))) for row in rows]
        magnitude = max(pie.data) or 1
        pie.data = [value / magnitude for value in pie.data]
        pie.labels = [_short(row.get(x_key, ""), 18) for row in rows]
        pie.sideLabels = True
        for index in range(len(rows)):
            pie.slices[index].fillColor = PALETTE[index % len(PALETTE)]
            pie.slices[index].strokeColor = colors.white
        if sum(pie.data):
            drawing.add(pie)
        else:
            drawing.add(String(40, 110, "No positive values for this share chart.", fontSize=10))
        if kind == "doughnut" and sum(pie.data):
            drawing.add(Circle(225, 117.5, 39, fillColor=colors.white, strokeColor=colors.white))
        return _finish_drawing(drawing)
    left, bottom, width, height = 58, 57, 405, 150
    series = [[_number(row.get(key)) for row in rows] for key in y_keys]
    values = [value for group in series for value in group]
    if kind == "stacked_bar":
        values += [sum(max(0, group[i]) for group in series) for i in range(len(rows))]
        values += [sum(min(0, group[i]) for group in series) for i in range(len(rows))]
    if not all(math.isfinite(value) for value in values):
        drawing.add(String(15, 120, "Chart omitted: the combined values exceed the safe numeric range.", fontSize=9))
        return _finish_drawing(drawing)
    low, high = min(0, min(values)), max(0, max(values))
    if high == low:
        high = low + 1
    magnitude = max(abs(low), abs(high), 1)
    scaled_low, scaled_high = low / magnitude, high / magnitude
    scaled_span = scaled_high - scaled_low or 1
    def yp(value):
        return bottom + (value / magnitude - scaled_low) / scaled_span * height
    for step in range(5):
        value = low * (1 - step / 4) + high * (step / 4)
        y = yp(value)
        drawing.add(Line(left, y, left + width, y, strokeColor=colors.HexColor("#e2e8f0"), strokeWidth=.5))
        drawing.add(String(left - 7, y - 3, f"{value:,.2g}", textAnchor="end", fontSize=7, fillColor=colors.HexColor("#64748b")))
    if kind == "scatter":
        xs = [_number(row.get(x_key)) for row in rows]
        xlow, xhigh = min(xs), max(xs)
        xmagnitude = max(abs(xlow), abs(xhigh), 1)
        span = xhigh / xmagnitude - xlow / xmagnitude or 1
        for i, x in enumerate(xs):
            drawing.add(Circle(left + (x / xmagnitude - xlow / xmagnitude) / span * width, yp(series[0][i]), 2.2, fillColor=PALETTE[0], strokeColor=None))
        for step in range(5):
            value = xlow * (1 - step / 4) + xhigh * (step / 4)
            drawing.add(String(left + width * step / 4, bottom - 12, f"{value:,.3g}", textAnchor="middle", fontSize=7))
    elif kind == "horizontal_bar":
        # Rotate the comparison into horizontal bars with category labels.
        drawing = Drawing(480, 235)
        base = 138 + (0 - scaled_low) / scaled_span * 315
        count = len(rows)
        band = 180 / max(1, count)
        for i, row in enumerate(rows):
            y = 27 + (count - i - 1) * band
            end = 138 + (series[0][i] / magnitude - scaled_low) / scaled_span * 315
            drawing.add(Rect(min(base, end), y + 2, max(.6, abs(end - base)), max(2, band - 5), fillColor=PALETTE[0], strokeColor=None))
            drawing.add(String(130, y + band / 2 - 2, _short(row.get(x_key, ""), 24), textAnchor="end", fontSize=7))
            drawing.add(String(min(456, max(base, end) + 3), y + band / 2 - 2, f"{series[0][i]:,.3g}", fontSize=6))
    else:
        band = width / max(1, len(rows))
        for si, group in enumerate(series):
            points = []
            for index, value in enumerate(group):
                center = left + band * (index + .5)
                if kind == "line":
                    points.extend([center, yp(value)])
                    drawing.add(Circle(center, yp(value), 2, fillColor=PALETTE[si % len(PALETTE)], strokeColor=None))
                elif kind == "stacked_bar":
                    previous = sum(series[j][index] for j in range(si) if (series[j][index] >= 0) == (value >= 0))
                    start, end = yp(previous), yp(previous + value)
                    drawing.add(Rect(center - band * .32, min(start, end), band * .64, max(.4, abs(end - start)), fillColor=PALETTE[si % len(PALETTE)], strokeColor=None))
                else:
                    bar_width = band * .7 / max(1, len(series))
                    drawing.add(Rect(center - band * .35 + si * bar_width, min(yp(0), yp(value)), bar_width * .9, max(.4, abs(yp(value) - yp(0))), fillColor=PALETTE[si % len(PALETTE)], strokeColor=None))
            if kind == "line" and len(points) >= 4:
                drawing.add(PolyLine(points, strokeColor=PALETTE[si % len(PALETTE)], strokeWidth=1.5))
        stride = max(1, math.ceil(len(rows) / 7))
        for index in range(0, len(rows), stride):
            drawing.add(String(left + band * (index + .5), bottom - 14, _short(rows[index].get(x_key, ""), 12), textAnchor="middle", fontSize=6.5))
    drawing.add(String(250, 13, _short(chart.get("x_label", x_key), 65), textAnchor="middle", fontSize=8))
    drawing.add(String(12, 222, _short(chart.get("y_label", ", ".join(y_keys)), 75), fontSize=8))
    if len(y_keys) > 1:
        for index, key in enumerate(y_keys[:4]):
            drawing.add(Rect(60 + 103 * index, 30, 6, 6, fillColor=PALETTE[index % len(PALETTE)], strokeColor=None))
            drawing.add(String(70 + 103 * index, 30, _short(chart.get("series_labels", {}).get(key, key), 15), fontSize=7))
    return _finish_drawing(drawing)


def pdf_bytes(analysis, active_filters):
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=(595.28, 841.89), rightMargin=48, leftMargin=48, topMargin=45, bottomMargin=45, title=f"SheetSense report — {analysis['filename']}", author="SheetSense")
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = FONT
    styles["Heading2"].keepWithNext = True
    styles["Heading3"].keepWithNext = True
    styles.add(ParagraphStyle(name="Subtle", parent=styles["BodyText"], fontSize=9, textColor=colors.HexColor("#64748b"), spaceAfter=9))
    styles["Title"].textColor = PALETTE[0]
    body = []
    def p(text, style="BodyText"):
        return Paragraph(escape(str(text)), styles[style])
    body += [p("SheetSense", "Title"), p("Spreadsheet analysis report", "Heading2"), p(analysis["filename"], "Heading2"),
             p(f"Worksheet: {analysis['sheet']} • Version: {analysis['version']} • Analyzed: {analysis['analyzed_at']}", "Subtle"),
             p(f"{analysis['rows']:,} matching records / {analysis['total_rows']:,} records • {analysis['column_count']} columns", "Subtle")]
    if active_filters:
        body += [p("Active filters", "Heading2")]
        for column, condition in active_filters.items():
            details = "; ".join(f"{key}: {', '.join(map(str, value)) if isinstance(value, list) else value}" for key, value in condition.items())
            body.append(p(f"{column} — {details}"))
    else:
        body.append(p("Active filters: none", "Subtle"))
    body.append(p("Key metrics", "Heading2"))
    metric_rows = [[p("Metric"), p("Value"), p("Meaning")]]
    for metric in analysis["kpis"]:
        value = metric["value"]
        if isinstance(value, (int, float)):
            value = f"{value:,.2f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"
        if metric.get("format") == "percent":
            value = f"{value}%"
        metric_rows.append([p(metric["label"]), p(value), p(metric.get("description", ""))])
    table = Table(metric_rows, colWidths=[145, 100, 245], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor("#e2e8f0"))]))
    body += [table, PageBreak(), p("Visual analysis", "Heading2")]
    for chart in analysis["charts"]:
        body.append(KeepTogether([p(chart["title"], "Heading3"), p(chart.get("description", ""), "Subtle"), chart_drawing(chart), Spacer(1, 12)]))
    if not analysis["charts"]:
        body.append(p("No supported chart is available for this selection."))
    body.append(p("Key insights", "Heading2"))
    for insight in analysis["insights"]:
        body += [p(insight["title"], "Heading3"), p(insight["text"])]
    quality = analysis["quality"]
    body += [p("Data quality", "Heading2"), p(f"Missing cells: {quality['missing_cells']:,} ({quality['missing_percent']:.2f}%). Duplicate rows: {quality['duplicate_rows']:,}.")]
    for issue in quality["issues"]:
        body.append(p(f"{issue.get('column', 'Dataset')}: {issue['message']}"))
    if analysis.get("notes"):
        body.append(p("Analysis notes", "Heading2"))
        body += [p(note, "Subtle") for note in analysis["notes"]]
    def footer(canvas, doc):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(48, 25, "SheetSense • Generated from the selected data and filters")
        canvas.drawRightString(548, 25, f"Page {doc.page}")
    document.build(body, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
