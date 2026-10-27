"""Private, bounded, expiring local sessions for a single Flask process."""
from __future__ import annotations

import secrets
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    id: str
    token: str
    filename: str
    path: Path
    sheets: list[str]
    expires: float
    cleaned: dict = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)


class SessionStore:
    def __init__(self, config):
        self.config = config
        self.root = Path(config["SESSION_DIR"]).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.sessions = {}
        self.lock = threading.RLock()
        self.cleanup()
        if config.get("START_CLEANUP_THREAD", True):
            threading.Thread(target=self._sweep, daemon=True, name="sheetsense-expiration").start()

    def _sweep(self):
        while True:
            time.sleep(60)
            self.cleanup()

    def cleanup(self):
        with self.lock:
            now = time.time()
            for identifier, session in list(self.sessions.items()):
                if session.expires <= now:
                    self.delete(identifier)
            active_dirs = {session.path.parent for session in self.sessions.values()}
            for folder in self.root.glob("ss-*"):
                if folder.is_dir() and folder not in active_dirs and now - folder.stat().st_mtime > self.config["SESSION_TTL_SECONDS"]:
                    shutil.rmtree(folder, ignore_errors=True)

    def new_directory(self):
        return Path(tempfile.mkdtemp(prefix="ss-", dir=self.root))

    def register(self, filename, path, sheets):
        with self.lock:
            self.cleanup()
            if len(self.sessions) >= self.config["MAX_SESSIONS"]:
                raise ValueError("The server has reached its session limit. Delete an existing session or try again later.")
            session = Session(secrets.token_urlsafe(24), secrets.token_urlsafe(32), filename, path, sheets, time.time() + self.config["SESSION_TTL_SECONDS"])
            self.sessions[session.id] = session
            return session

    def get(self, identifier, token):
        with self.lock:
            self.cleanup()
            session = self.sessions.get(identifier)
            if not session or not token or not secrets.compare_digest(session.token, token):
                return None
            return session

    def delete(self, identifier):
        with self.lock:
            session = self.sessions.pop(identifier, None)
            if session:
                with session.lock:
                    session.cleaned.clear()
                    shutil.rmtree(session.path.parent, ignore_errors=True)
