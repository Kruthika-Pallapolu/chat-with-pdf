import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sqlite3
import threading
import time
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path


SESSION_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


@dataclass(frozen=True)
class Session:
    session_id: str
    token: str
    created: bool
    rotated: bool = False


class SessionStore:
    def __init__(self, data_dir, ttl_seconds=86400, max_sessions=1000,
                 max_session_bytes=64 * 1024 * 1024, max_total_bytes=2 * 1024 * 1024 * 1024,
                 max_history_bytes=2_000_000):
        self.data_dir = Path(data_dir).resolve()
        self.sessions_dir = self.data_dir / "sessions"
        self.database = self.sessions_dir / "sessions.sqlite3"
        self.ttl_seconds = max(300, int(ttl_seconds))
        self.max_sessions = max(1, int(max_sessions))
        self.max_session_bytes = max(1024 * 1024, int(max_session_bytes))
        self.max_total_bytes = max(self.max_session_bytes, int(max_total_bytes))
        self.max_history_bytes = max(1024, int(max_history_bytes))
        self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.sessions_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(self.sessions_dir, 0o700)
        except OSError:
            pass
        self._ip_hash_key = self._load_or_create_ip_hash_key()
        self._guard = threading.RLock()
        self._cleanup_guard = threading.Lock()
        self._locks = {}
        self._last_cleanup = 0.0
        self._initialize()

    def _load_or_create_ip_hash_key(self):
        key_path = self.sessions_dir / ".rate-key"
        try:
            descriptor = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            key = key_path.read_bytes()
            if len(key) != 32:
                raise RuntimeError("Invalid session rate-limit key.") from None
            return key
        key = secrets.token_bytes(32)
        with os.fdopen(descriptor, "wb") as key_file:
            key_file.write(key)
            key_file.flush()
            os.fsync(key_file.fileno())
        return key

    def _ip_digest(self, client_host):
        return hmac.new(self._ip_hash_key, (client_host or "unknown").encode("utf-8"), hashlib.sha256).hexdigest()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=5)
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    answer_memory TEXT NOT NULL DEFAULT '',
                    conversations_json TEXT NOT NULL DEFAULT '[]'
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS rate_counters (
                    subject TEXT NOT NULL,
                    action TEXT NOT NULL,
                    window_start INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY (subject, action, window_start)
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS session_storage (
                    session_id TEXT PRIMARY KEY,
                    document_bytes INTEGER NOT NULL DEFAULT 0,
                    history_bytes INTEGER NOT NULL DEFAULT 0
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS shared_conversations (
                    share_id TEXT PRIMARY KEY,
                    snapshot_json TEXT NOT NULL,
                    snapshot_bytes INTEGER NOT NULL,
                    created_at REAL NOT NULL
                )"""
            )
            connection.execute(
                "INSERT OR IGNORE INTO session_storage (session_id) SELECT session_id FROM sessions"
            )
            sessions = connection.execute(
                "SELECT session_id, conversations_json FROM sessions"
            ).fetchall()
        with self._connect() as connection:
            for session_id, conversations_json in sessions:
                history_bytes = len((conversations_json or "[]").encode("utf-8"))
                document_bytes = self._existing_document_bytes(session_id)
                connection.execute(
                    "UPDATE session_storage SET document_bytes = ?, history_bytes = ? WHERE session_id = ?",
                    (document_bytes, history_bytes, session_id),
                )
        try:
            os.chmod(self.database, 0o600)
        except OSError:
            pass

    def _existing_document_bytes(self, session_id):
        try:
            session_dir = self.session_dir(session_id)
            active = json.loads((session_dir / "active.json").read_text(encoding="utf-8"))
            document_id = active.get("document_id", "")
            if not SESSION_ID_PATTERN.fullmatch(document_id):
                return 0
            documents_dir = (session_dir / "documents").resolve()
            document_dir = (documents_dir / document_id).resolve()
            if document_dir.parent != documents_dir or not document_dir.is_dir():
                return 0
            return sum(path.stat().st_size for path in document_dir.iterdir() if path.is_file())
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return 0

    @staticmethod
    def _token_hash(token):
        return hashlib.sha256(token.encode("ascii")).hexdigest()

    def resolve(self, presented_token=None):
        now = time.time()
        self.cleanup_expired(now)

        if presented_token is not None:
            if not isinstance(presented_token, str) or not presented_token.isascii() or not 40 <= len(presented_token) <= 128:
                raise SessionNotFoundError("Session expired. Refresh the page to continue.")
            token_hash = self._token_hash(presented_token)
            expired_id = None
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT session_id, created_at, last_seen FROM sessions WHERE token_hash = ?",
                    (token_hash,),
                ).fetchone()
                if row and now - row[2] < self.ttl_seconds:
                    if now - row[1] >= self.ttl_seconds // 2:
                        replacement_token = secrets.token_urlsafe(32)
                        connection.execute(
                            "UPDATE sessions SET token_hash = ?, created_at = ?, last_seen = ? WHERE session_id = ?",
                            (self._token_hash(replacement_token), now, now, row[0]),
                        )
                        return Session(row[0], replacement_token, False, True)
                    connection.execute(
                        "UPDATE sessions SET last_seen = ? WHERE token_hash = ?",
                        (now, token_hash),
                    )
                    return Session(row[0], presented_token, False)
                if row:
                    expired_id = row[0]
                    connection.execute("DELETE FROM sessions WHERE session_id = ?", (expired_id,))
            if expired_id:
                self._remove_session_files(expired_id)
            raise SessionNotFoundError("Session expired. Refresh the page to continue.")

        token = secrets.token_urlsafe(32)
        session_id = secrets.token_hex(16)
        token_hash = self._token_hash(token)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            if count >= self.max_sessions:
                raise SessionCapacityError("The service has reached its temporary session limit.")
            connection.execute(
                "INSERT INTO sessions (session_id, token_hash, created_at, last_seen) VALUES (?, ?, ?, ?)",
                (session_id, token_hash, now, now),
            )
            connection.execute("INSERT INTO session_storage (session_id) VALUES (?)", (session_id,))
        self.session_dir(session_id).mkdir(mode=0o700, parents=True, exist_ok=True)
        return Session(session_id, token, True)

    def session_dir(self, session_id):
        if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(session_id):
            raise ValueError("Invalid server-side session identifier.")
        path = (self.sessions_dir / session_id).resolve()
        if path.parent != self.sessions_dir.resolve():
            raise ValueError("Session path is outside the storage root.")
        return path

    def lock_for(self, session_id):
        self.session_dir(session_id)
        with self._guard:
            return self._locks.setdefault(session_id, threading.RLock())

    def get_preferences(self, session_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT answer_memory, conversations_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError("Session expired. Refresh the page to continue.")
        try:
            conversations = json.loads(row[1])
        except (TypeError, json.JSONDecodeError):
            conversations = []
        return row[0], conversations if isinstance(conversations, list) else []

    def set_answer_memory(self, session_id, text):
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE sessions SET answer_memory = ? WHERE session_id = ?",
                (text, session_id),
            )
            if cursor.rowcount != 1:
                raise SessionNotFoundError("Session expired. Refresh the page to continue.")

    def set_conversations(self, session_id, conversations):
        serialized = json.dumps(conversations, ensure_ascii=False, separators=(",", ":"))
        history_bytes = len(serialized.encode("utf-8"))
        if history_bytes > self.max_history_bytes:
            raise ValueError("Conversation history exceeds the storage limit.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT document_bytes, history_bytes FROM session_storage WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise SessionNotFoundError("Session expired. Refresh the page to continue.")
            if row[0] + history_bytes > self.max_session_bytes:
                raise SessionStorageLimitError("Session storage limit reached.")
            total = connection.execute(
                "SELECT COALESCE(SUM(document_bytes + history_bytes), 0) FROM session_storage"
            ).fetchone()[0]
            if total - row[1] + history_bytes > self.max_total_bytes:
                raise SessionStorageLimitError("Service storage limit reached. Try again later.")
            cursor = connection.execute(
                "UPDATE sessions SET conversations_json = ? WHERE session_id = ?",
                (serialized, session_id),
            )
            if cursor.rowcount != 1:
                raise SessionNotFoundError("Session expired. Refresh the page to continue.")
            connection.execute(
                "UPDATE session_storage SET history_bytes = ? WHERE session_id = ?",
                (history_bytes, session_id),
            )

    def set_document_bytes(self, session_id, document_bytes):
        document_bytes = max(0, int(document_bytes))
        if document_bytes > self.max_session_bytes:
            raise SessionStorageLimitError("Session storage limit reached.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT document_bytes, history_bytes FROM session_storage WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise SessionNotFoundError("Session expired. Refresh the page to continue.")
            if row[1] + document_bytes > self.max_session_bytes:
                raise SessionStorageLimitError("Session storage limit reached.")
            total = connection.execute(
                "SELECT COALESCE(SUM(document_bytes + history_bytes), 0) FROM session_storage"
            ).fetchone()[0]
            if total - row[0] + document_bytes > self.max_total_bytes:
                raise SessionStorageLimitError("Service storage limit reached. Try again later.")
            connection.execute(
                "UPDATE session_storage SET document_bytes = ? WHERE session_id = ?",
                (document_bytes, session_id),
            )
            return row[0]

    def delete_session(self, session_id):
        self.session_dir(session_id)
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM session_storage WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM rate_counters WHERE subject LIKE ?", ("session:" + session_id,))
        self._remove_session_files(session_id)
        with self._guard:
            self._locks.pop(session_id, None)

    def allow_request(self, session_id, client_host, action, limit, window_seconds=60):
        now = int(time.time())
        window_start = now - now % window_seconds
        ip_digest = self._ip_digest(client_host)
        subjects = (("session:" + session_id, limit), ("ip:" + ip_digest, limit * 3))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for subject, subject_limit in subjects:
                row = connection.execute(
                    "SELECT count FROM rate_counters WHERE subject = ? AND action = ? AND window_start = ?",
                    (subject, action, window_start),
                ).fetchone()
                if row and row[0] >= subject_limit:
                    return False
            for subject, _subject_limit in subjects:
                connection.execute(
                    "INSERT INTO rate_counters (subject, action, window_start, count) VALUES (?, ?, ?, 1) "
                    "ON CONFLICT(subject, action, window_start) DO UPDATE SET count = count + 1",
                    (subject, action, window_start),
                )
            connection.execute("DELETE FROM rate_counters WHERE window_start < ?", (window_start - 3600,))
        return True

    def allow_ip_request(self, client_host, action, limit, window_seconds=60):
        now = int(time.time())
        window_start = now - now % window_seconds
        ip_digest = self._ip_digest(client_host)
        subject = "ip:" + ip_digest
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT count FROM rate_counters WHERE subject = ? AND action = ? AND window_start = ?",
                (subject, action, window_start),
            ).fetchone()
            if row and row[0] >= limit:
                return False
            connection.execute(
                "INSERT INTO rate_counters (subject, action, window_start, count) VALUES (?, ?, ?, 1) "
                "ON CONFLICT(subject, action, window_start) DO UPDATE SET count = count + 1",
                (subject, action, window_start),
            )
            connection.execute("DELETE FROM rate_counters WHERE window_start < ?", (window_start - 3600,))
        return True

    def cleanup_expired(self, now=None):
        now = time.time() if now is None else now
        if now - self._last_cleanup < 60 or not self._cleanup_guard.acquire(blocking=False):
            return
        expired_before = now - self.ttl_seconds
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    "SELECT session_id FROM sessions WHERE last_seen < ?", (expired_before,)
                ).fetchall()
                ids = [row[0] for row in rows]
                connection.executemany("DELETE FROM sessions WHERE session_id = ?", [(sid,) for sid in ids])
                connection.executemany("DELETE FROM session_storage WHERE session_id = ?", [(sid,) for sid in ids])
            for session_id in ids:
                self._remove_session_files(session_id)
                with self._guard:
                    self._locks.pop(session_id, None)
            self._last_cleanup = now
        finally:
            self._cleanup_guard.release()

    def create_shared_conversation(self, share_id, snapshot_json, max_bytes, max_shares):
        snapshot_bytes = len(snapshot_json.encode("utf-8"))
        if snapshot_bytes > max_bytes:
            raise SessionStorageLimitError("Conversation is too large to share.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(snapshot_bytes), 0) FROM shared_conversations"
            ).fetchone()
            if row[0] >= max_shares or row[1] + snapshot_bytes > self.max_total_bytes:
                raise SessionStorageLimitError("Shared conversation storage limit reached.")
            connection.execute(
                "INSERT INTO shared_conversations (share_id, snapshot_json, snapshot_bytes, created_at) "
                "VALUES (?, ?, ?, ?)",
                (share_id, snapshot_json, snapshot_bytes, time.time()),
            )

    def get_shared_conversation(self, share_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM shared_conversations WHERE share_id = ?", (share_id,)
            ).fetchone()
        if row is None:
            return None
        try:
            snapshot = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return None
        return snapshot if isinstance(snapshot, dict) else None

    def _remove_session_files(self, session_id):
        try:
            directory = self.session_dir(session_id)
        except ValueError:
            return
        if directory.exists():
            shutil.rmtree(directory)


class SessionCapacityError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class SessionStorageLimitError(Exception):
    pass
