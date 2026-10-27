"""Exercise a running SheetSense API (or Vite proxy) using real HTTP requests.

Usage: python scripts/acceptance_check.py --base-url http://127.0.0.1:5173
Uploads only the bundled synthetic datasets and deletes every created session.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class API:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.sessions = []

    def request(self, path, body=None, token=None, raw=False, method=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Session-Token"] = token
        request = Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                          headers=headers, method=method)
        with urlopen(request, timeout=90) as response:
            data = response.read()
            if raw:
                return data, response.headers
            decoded = json.loads(data)
            assert decoded["success"], decoded
            return decoded["data"]

    def upload(self, filename, content):
        boundary = "sheetsense-" + uuid4().hex
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
                "Content-Type: application/octet-stream\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
        request = Request(self.base + "/api/upload", data=body,
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urlopen(request, timeout=90) as response:
            session = json.load(response)["data"]
        self.sessions.append(session)
        return session

    def call(self, session, action, body=None, **kwargs):
        return self.request(f"/api/{action}/{session['session_id']}", body, session["token"], **kwargs)


def expect_error(operation, statuses):
    try:
        operation()
    except HTTPError as error:
        assert error.code in statuses, f"Unexpected status: {error.code} {error.read()}"
        result = json.load(error)
        assert result["success"] is False and result["error"]["message"]
    else:
        raise AssertionError("Invalid request unexpectedly succeeded")


def run(base):
    api = API(base)
    passed = []
    try:
        api.request("/api/health")
        sales_bytes = (ROOT / "sample_data/synthetic_sales.csv").read_bytes()
        sales = api.upload("synthetic_sales.csv", sales_bytes)
        body = {"sheet": sales["sheets"][0], "filters": {}}
        analysis = api.call(sales, "analyze", body)
        assert analysis["rows"] == 240
        assert analysis["column_count"] == 7
        assert any(chart["type"] == "line" for chart in analysis["charts"])
        preview = api.call(sales, "preview", {**body, "page": 2, "page_size": 10})
        assert len(preview["rows"]) == 10 and preview["total_rows"] == 240
        passed.append("Sales upload, preview and actual analytics")

        students = api.upload("synthetic_student_workbook.xlsx", (ROOT / "sample_data/synthetic_student_workbook.xlsx").read_bytes())
        assert len(students["sheets"]) == 2
        academic = api.call(students, "analyze", {"sheet": students["sheets"][1]})
        assert academic["rows"] == 80
        assert "Revenue" not in [column["name"] for column in academic["columns"]]
        passed.extend(["Student Excel adapts to academic columns", "Multiple worksheets remain selectable"])

        expenses = api.upload("expenses.csv", (ROOT / "sample_data/synthetic_expenses.csv").read_bytes())
        spending = api.call(expenses, "analyze", {"sheet": expenses["sheets"][0]})
        assert spending["charts"] and not any(chart["type"] == "line" for chart in spending["charts"])
        passed.append("Expenses without dates do not invent a time series")

        dirty = api.upload("quality.csv", b"Category,Amount\nA,10\nA,10\nB,\nC,30\n")
        dirty_body = {"sheet": dirty["sheets"][0]}
        quality = api.call(dirty, "analyze", dirty_body)
        assert quality["quality"]["duplicate_rows"] == 1 and quality["quality"]["missing_cells"] == 1
        passed.append("Missing cells and duplicate rows counted accurately")

        filtered_body = {**body, "filters": {"Region": {"values": ["North"]}}}
        filtered = api.call(sales, "filter", filtered_body)
        source = list(csv.DictReader(io.StringIO(sales_bytes.decode())))
        north = [row for row in source if row["Region"] == "North"]
        assert filtered["rows"] == len(north) < analysis["rows"]
        graph = api.call(sales, "custom-chart", {**filtered_body, "x": "Product", "y": "Revenue", "type": "bar", "aggregation": "sum", "top_n": 10, "sort": "desc"})
        assert abs(sum(float(row[graph["y_keys"][0]]) for row in graph["data"]) - sum(float(row["Revenue"]) for row in north)) < .01
        passed.append("Filters and custom chart match independently calculated source totals")

        expect_error(lambda: api.upload("invalid.exe", b"MZnot-a-spreadsheet"), {400, 415, 422})
        expect_error(lambda: api.upload("invalid.xlsx", b"not-a-workbook"), {400, 415, 422})
        passed.append("Unsupported and malformed files rejected safely")

        pdf, headers = api.call(sales, "export", {**filtered_body, "format": "pdf"}, raw=True)
        assert pdf.startswith(b"%PDF-") and "pdf" in headers["Content-Type"]
        exported, _ = api.call(sales, "export", {**filtered_body, "format": "csv"}, raw=True)
        rows = list(csv.DictReader(io.StringIO(exported.decode("utf-8-sig"))))
        assert len(rows) == len(north) and all(row["Region"] == "North" for row in rows)
        excel, _ = api.call(sales, "export", {**filtered_body, "format": "xlsx"}, raw=True)
        assert excel.startswith(b"PK")
        passed.append("PDF, CSV and Excel exports use current filtered analysis")

        text_only = api.upload("categories.csv", b"Team,Status\nBlue,Ready\nGreen,Ready\nBlue,Waiting\n")
        text_analysis = api.call(text_only, "analyze", {"sheet": text_only["sheets"][0]})
        assert not any(column["type"] == "numeric" for column in text_analysis["columns"])
        assert text_analysis["charts"]
        passed.append("Categorical-only data provides frequency summaries")

        operations = [{"action": "drop_duplicates"}, {"action": "fill_numeric", "column": "Amount", "method": "median"}]
        clean_preview = api.call(dirty, "clean", {**dirty_body, "operations": operations, "apply": False})
        assert clean_preview["after_rows"] == 3
        assert api.call(dirty, "analyze", dirty_body)["rows"] == 4
        api.call(dirty, "clean", {**dirty_body, "operations": operations, "apply": True})
        clean = api.call(dirty, "analyze", {**dirty_body, "version": "cleaned"})
        assert clean["rows"] == 3 and clean["quality"]["missing_cells"] == 0
        assert api.call(dirty, "analyze", dirty_body)["rows"] == 4
        passed.append("Cleaning previews before applying and preserves original")

        expect_error(lambda: api.request(f"/api/sheets/{sales['session_id']}", token="wrong-token"), {401, 403, 404})
        passed.append("Session ownership token required")
        api.call(text_only, "delete", {})
        api.sessions.remove(text_only)
        expect_error(lambda: api.call(text_only, "analyze", {}), {404, 410})
        passed.append("Deleting a session revokes access")
    finally:
        for session in api.sessions:
            try:
                api.call(session, "delete", {})
            except Exception as error:
                print(f"Cleanup failed: {type(error).__name__}")
    for check in passed:
        print(f"PASS {check}")
    print(f"\n{len(passed)} acceptance checks passed through {base}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    run(parser.parse_args().base_url)
