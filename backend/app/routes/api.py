from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import shutil

from flask import Blueprint, current_app, jsonify, request, send_file
from werkzeug.exceptions import NotFound, RequestEntityTooLarge
from werkzeug.utils import secure_filename

from app.analytics.engine import analyze_frame, prepare_frame, apply_filters, preview_frame, custom_chart
from app.services.cleaning import clean_frame
from app.services.exports import pdf_bytes, spreadsheet_bytes
from app.services.files import InvalidFile, inspect_file, read_sheet

api = Blueprint("api", __name__)

SAMPLES = [
    {"id": "sales", "name": "Sales overview", "description": "Synthetic orders, units, revenue, products, and regions.", "filename": "synthetic_sales.csv"},
    {"id": "students", "name": "Student performance", "description": "Synthetic marks and attendance across academic subjects.", "filename": "synthetic_students.csv"},
    {"id": "expenses", "name": "Personal expenses", "description": "Synthetic spending categories without a date column.", "filename": "synthetic_expenses.csv"},
    {"id": "inventory", "name": "Inventory snapshot", "description": "Synthetic stock levels, costs, and reorder points.", "filename": "synthetic_inventory.csv"},
    {"id": "workbook", "name": "Student workbook", "description": "Synthetic Excel workbook with multiple worksheets.", "filename": "synthetic_student_workbook.xlsx"},
]


def ok(data, status=200):
    return jsonify(success=True, data=data), status


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Send a JSON object with the requested analysis options.")
    return data


def session_for(identifier):
    session = current_app.extensions["sessions"].get(identifier, request.headers.get("X-Session-Token", ""))
    if session is None:
        raise NotFound("This analysis session is unavailable or expired. Upload the file again.")
    return session


def selected_sheet(session, data):
    sheet = data.get("sheet")
    if (sheet is None or sheet == "") and len(session.sheets) == 1:
        sheet = session.sheets[0]
    if not isinstance(sheet, str) or sheet not in session.sheets:
        raise ValueError("Choose a valid worksheet before continuing.")
    return sheet


def selected_frame(session, data):
    sheet = selected_sheet(session, data)
    version = data.get("version", "original")
    if version not in ("original", "cleaned"):
        raise ValueError("Choose either the original or cleaned dataset version.")
    if version == "cleaned":
        if sheet not in session.cleaned:
            raise ValueError("No cleaned version exists for this worksheet. Preview and apply cleaning first.")
        return session.cleaned[sheet].copy(deep=True), sheet, version
    return read_sheet(session.path, sheet, current_app.config), sheet, version


def filters_for(data):
    filters = data.get("filters", {})
    if not isinstance(filters, dict) or len(filters) > current_app.config["MAX_COLUMNS"]:
        raise ValueError("Filters must be an object of column selections.")
    return filters


@api.get("/health")
def health():
    return ok({"status": "ok", "service": "SheetSense", "max_upload_mb": current_app.config["MAX_UPLOAD_BYTES"] / 1024 / 1024})


@api.post("/upload")
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        raise ValueError("Choose a spreadsheet to upload.")
    original_name = file.filename.replace("\\", "/").split("/")[-1]
    extension = Path(original_name).suffix.lower()
    if extension not in (".csv", ".xlsx", ".xls"):
        raise InvalidFile("Choose an .xlsx, .xls, or .csv file.")
    filename = (secure_filename(Path(original_name).stem) or "spreadsheet") + extension
    if len(filename) > 180:
        filename = filename[:150] + extension
    store = current_app.extensions["sessions"]
    directory = store.new_directory()
    path = directory / ("original" + extension)
    try:
        size = 0
        with path.open("wb") as destination:
            while chunk := file.stream.read(65536):
                size += len(chunk)
                if size > current_app.config["MAX_UPLOAD_BYTES"]:
                    raise RequestEntityTooLarge()
                destination.write(chunk)
        if size == 0:
            raise InvalidFile("The file is empty. Choose a spreadsheet containing data.")
        sheets = inspect_file(path, current_app.config)
        session = store.register(filename, path, sheets)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return ok({"session_id": session.id, "token": session.token, "filename": filename, "sheets": sheets,
               "expires_at": datetime.fromtimestamp(session.expires, timezone.utc).isoformat()}, 201)


@api.get("/sheets/<identifier>")
def sheets(identifier):
    return ok({"sheets": session_for(identifier).sheets})


@api.get("/samples")
def samples():
    return ok([sample for sample in SAMPLES if (Path(current_app.config["SAMPLE_DIR"]) / sample["filename"]).is_file()])


@api.get("/samples/<sample_id>")
def sample_file(sample_id):
    sample = next((item for item in SAMPLES if item["id"] == sample_id), None)
    if sample is None:
        raise NotFound("This sample dataset is unavailable.")
    path = Path(current_app.config["SAMPLE_DIR"]) / sample["filename"]
    if not path.is_file():
        raise NotFound("This sample dataset is unavailable.")
    return send_file(path, as_attachment=True, download_name=sample["filename"])


@api.post("/analyze/<identifier>")
@api.post("/filter/<identifier>")
def analyze(identifier):
    session, data = session_for(identifier), body()
    with session.lock:
        raw, sheet, version = selected_frame(session, data)
        result = analyze_frame(raw, session.filename, sheet, filters=filters_for(data), version=version)
    return ok(result)


@api.post("/preview/<identifier>")
def preview(identifier):
    session, data = session_for(identifier), body()
    with session.lock:
        raw, _, _ = selected_frame(session, data)
        result = preview_frame(raw, filters=filters_for(data), page=data.get("page", 1), page_size=data.get("page_size", 25), search=data.get("search", ""))
    return ok(result)


@api.post("/custom-chart/<identifier>")
def chart(identifier):
    session, data = session_for(identifier), body()
    with session.lock:
        raw, _, _ = selected_frame(session, data)
        result = custom_chart(raw, data, filters=filters_for(data))
    return ok(result)


@api.post("/clean/<identifier>")
def clean(identifier):
    session, data = session_for(identifier), body()
    if not isinstance(data.get("apply", False), bool):
        raise ValueError("The apply field must be true or false.")
    with session.lock:
        sheet = selected_sheet(session, data)
        original = read_sheet(session.path, sheet, current_app.config)
        cleaned, result = clean_frame(original, data.get("operations"))
        if data.get("apply", False):
            # A single cleaned worksheet per session bounds memory use.
            session.cleaned = {sheet: cleaned}
        result["version"] = "cleaned" if data.get("apply", False) else "original"
    return ok(result)


@api.route("/export/<identifier>", methods=["POST", "GET"])
def export(identifier):
    session = session_for(identifier)
    data = body() if request.method == "POST" else request.args.to_dict()
    format = data.get("format", "pdf")
    if format not in ("pdf", "csv", "xlsx"):
        raise ValueError("Choose PDF, CSV, or XLSX as the export format.")
    with session.lock:
        raw, sheet, version = selected_frame(session, data)
        filters = filters_for(data)
        if format == "pdf":
            content = pdf_bytes(analyze_frame(raw, session.filename, sheet, filters=filters, version=version), filters)
            mimetype = "application/pdf"
        else:
            typed, columns, _ = prepare_frame(raw)
            filtered = apply_filters(typed, columns, filters)
            content = spreadsheet_bytes(filtered, format)
            mimetype = "text/csv" if format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = f"{Path(session.filename).stem}-{version}-report.{format}"
    return send_file(BytesIO(content), mimetype=mimetype, as_attachment=True, download_name=filename)


@api.post("/delete/<identifier>")
def delete(identifier):
    session = session_for(identifier)
    current_app.extensions["sessions"].delete(session.id)
    return ok({"deleted": True})
