"""SheetSense application factory and configuration."""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.services.sessions import SessionStore


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


class SafeJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        kwargs["allow_nan"] = False
        return super().dumps(_json_safe(obj), **kwargs)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.json = SafeJSONProvider(app)
    upload_bytes = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024
    app.config.from_mapping(
        MAX_UPLOAD_BYTES=upload_bytes,
        MAX_CONTENT_LENGTH=upload_bytes + 512 * 1024,
        MAX_FORM_MEMORY_SIZE=512 * 1024,
        MAX_FORM_PARTS=10,
        MAX_ROWS=int(os.environ.get("MAX_ROWS", "50000")),
        MAX_COLUMNS=int(os.environ.get("MAX_COLUMNS", "200")),
        MAX_CELLS=int(os.environ.get("MAX_CELLS", "1000000")),
        MAX_SHEETS=20,
        MAX_EXPANDED_BYTES=50 * 1024 * 1024,
        MAX_SESSIONS=int(os.environ.get("MAX_SESSIONS", "20")),
        SESSION_TTL_SECONDS=int(os.environ.get("SESSION_TTL_SECONDS", "3600")),
        SESSION_DIR=os.environ.get("SESSION_DIR", str(Path(app.instance_path) / "sessions")),
        FRONTEND_ORIGINS=os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
        SAMPLE_DIR=str(Path(__file__).resolve().parents[2] / "sample_data"),
        START_CLEANUP_THREAD=True,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]}},
         allow_headers=["Content-Type", "X-Session-Token"], expose_headers=["Content-Disposition"], methods=["GET", "POST", "OPTIONS"])
    app.extensions["sessions"] = SessionStore(app.config)

    from app.routes.api import api
    app.register_blueprint(api, url_prefix="/api")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.errorhandler(ValueError)
    def validation_error(error):
        return jsonify(success=False, error={"code": "INVALID_INPUT", "message": str(error)}), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        code = "FILE_TOO_LARGE" if error.code == 413 else "REQUEST_ERROR"
        message = f"Choose a file smaller than {app.config['MAX_UPLOAD_BYTES'] / 1024 / 1024:g} MB." if error.code == 413 else error.description
        return jsonify(success=False, error={"code": code, "message": message}), error.code

    @app.errorhandler(Exception)
    def server_error(error):
        # Log only the exception class: spreadsheet contents and filenames stay private.
        app.logger.error("Request failed (%s)", type(error).__name__)
        return jsonify(success=False, error={"code": "PROCESSING_ERROR", "message": "The request could not be completed. Try a smaller or freshly saved spreadsheet."}), 500

    return app
