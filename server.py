import os
import sys
import shutil
import logging
import tempfile
import threading
import json
import secrets
import time
from pathlib import Path
from typing import List, Optional
import fitz
import numpy as np
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from dotenv import load_dotenv, find_dotenv

# Ensure .env is dynamically located and loaded with override=True
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path, override=False)
else:
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

# Add src to sys.path so backend modules can be imported directly
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import existing Python RAG backend modules
from pdf_loader import extract_text
from chunker import chunk_text
from embedder import create_embeddings
from storage import (
    get_file_hash,
)
from document_search import find_module_headings, get_structural_answer
from citations import parse_sources_line, build_citations, filter_supported_answer
from generator import (
    retrieve,
    generate_answer,
    generate_general_answer,
    generate_suggested_questions,
    is_module_count_question,
    answer_module_count_question,
    build_context,
    get_client,
)
import generator
from session_store import SessionCapacityError, SessionNotFoundError, SessionStorageLimitError, SessionStore

IS_PRODUCTION = os.getenv("CWP_ENV", "development").lower() == "production"
ALLOWED_HOSTS = {
    host.strip().lower()
    for host in os.getenv("ALLOWED_HOSTS", "" if IS_PRODUCTION else "127.0.0.1,localhost,testserver").split(",")
    if host.strip()
}
if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be configured for production.")
app = FastAPI(
    title="CWP - Chat with PDF API",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(_request: Request, _error: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request."})

# Global State Container for loaded document index
DATA_DIR = os.path.abspath(os.getenv("CWP_DATA_DIR", os.path.join(PROJECT_ROOT, "data")))
DEFAULT_PDF_PATH = os.path.abspath(os.getenv("CWP_DEFAULT_PDF_PATH", os.path.join(DATA_DIR, "document.pdf")))
os.makedirs(DATA_DIR, exist_ok=True)
SESSION_COOKIE_NAME = "cwp_session"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "1000"))
MAX_SESSION_STORAGE_BYTES = int(os.getenv("MAX_SESSION_STORAGE_BYTES", str(64 * 1024 * 1024)))
MAX_TOTAL_STORAGE_BYTES = int(os.getenv("MAX_TOTAL_STORAGE_BYTES", str(2 * 1024 * 1024 * 1024)))
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_BYTES", str(20 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))
MAX_PDF_TEXT_CHARS = int(os.getenv("MAX_PDF_TEXT_CHARS", str(2_000_000)))
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "4000"))
MAX_CONVERSATIONS_BYTES = int(os.getenv("MAX_CONVERSATIONS_BYTES", str(2 * 1024 * 1024)))
MODEL_WORK_SEMAPHORE = threading.BoundedSemaphore(max(1, int(os.getenv("MAX_CONCURRENT_MODEL_REQUESTS", "2"))))
PDF_PROCESS_SEMAPHORE = threading.BoundedSemaphore(max(1, int(os.getenv("MAX_CONCURRENT_PDF_PROCESSES", "2"))))
DOCUMENT_LOAD_SEMAPHORE = threading.BoundedSemaphore(max(1, int(os.getenv("MAX_CONCURRENT_DOCUMENT_LOADS", "2"))))
_session_store_instance = None
_session_store_path = None
_session_store_guard = threading.Lock()
_upload_progress = {}
_upload_progress_guard = threading.Lock()


def _set_upload_progress(session_id, stage):
    with _upload_progress_guard:
        if stage is None:
            _upload_progress.pop(session_id, None)
        else:
            _upload_progress[session_id] = stage


def get_session_store():
    global _session_store_instance, _session_store_path
    data_path = str(Path(DATA_DIR).resolve())
    with _session_store_guard:
        if _session_store_instance is None or _session_store_path != data_path:
            _session_store_instance = SessionStore(
                DATA_DIR,
                ttl_seconds=SESSION_TTL_SECONDS,
                max_sessions=MAX_SESSIONS,
                max_session_bytes=MAX_SESSION_STORAGE_BYTES,
                max_total_bytes=MAX_TOTAL_STORAGE_BYTES,
                max_history_bytes=MAX_CONVERSATIONS_BYTES,
            )
            _session_store_path = data_path
    return _session_store_instance


def _safe_json_write(path, payload):
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    descriptor, staged = tempfile.mkstemp(prefix=".cwp-state-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
            file.flush()
            os.fsync(file.fileno())
        os.chmod(staged, 0o600)
        os.replace(staged, path)
    except Exception:
        if os.path.exists(staged):
            os.remove(staged)
        raise


def _load_document_state(session_id):
    with DOCUMENT_LOAD_SEMAPHORE:
        return _load_document_state_impl(session_id)


def _cleanup_session_artifacts(session_id):
    store = get_session_store()
    session_dir = store.session_dir(session_id)
    active_path = session_dir / "active.json"
    active_id = None
    if active_path.exists():
        try:
            active_id = json.loads(active_path.read_text(encoding="utf-8")).get("document_id")
        except (OSError, ValueError, TypeError):
            raise HTTPException(status_code=500, detail="Stored document metadata is unavailable.") from None
        if not isinstance(active_id, str) or len(active_id) != 32 or any(ch not in "0123456789abcdef" for ch in active_id):
            raise HTTPException(status_code=500, detail="Stored document metadata is unavailable.")

    for entry in session_dir.iterdir():
        if entry.is_file() and entry.name.startswith((".cwp-upload-", ".cwp-seed-")):
            try:
                entry.unlink()
            except OSError as error:
                logger.warning("Could not remove abandoned session temp file (%s).", type(error).__name__)

    documents_dir = session_dir / "documents"
    active_dir = None
    if documents_dir.exists():
        for entry in documents_dir.iterdir():
            if entry.name.startswith(".") or entry.name != active_id:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                elif entry.is_file():
                    try:
                        entry.unlink()
                    except OSError:
                        pass
        if active_id:
            active_dir = (documents_dir / active_id).resolve()
            if active_dir.parent != documents_dir.resolve():
                raise HTTPException(status_code=500, detail="Stored document metadata is unavailable.")

    active_bytes = 0
    if active_dir and active_dir.is_dir():
        active_bytes = sum(item.stat().st_size for item in active_dir.iterdir() if item.is_file())
    store.set_document_bytes(session_id, active_bytes)
    return active_id


def _load_document_state_impl(session_id):
    store = get_session_store()
    session_dir = store.session_dir(session_id)
    active_id = _cleanup_session_artifacts(session_id)
    active_path = session_dir / "active.json"
    if active_id is None:
        return None
    try:
        document_id = active_id
        document_dir = (session_dir / "documents" / document_id).resolve()
        if document_dir.parent != (session_dir / "documents").resolve():
            raise ValueError("Document path is outside the session directory.")
        metadata = json.loads((document_dir / "metadata.json").read_text(encoding="utf-8"))
        chunks = json.loads((document_dir / "chunks.json").read_text(encoding="utf-8"))
        page_texts = json.loads((document_dir / "pages.json").read_text(encoding="utf-8"))
        with np.load(document_dir / "embeddings.npz", allow_pickle=False) as vectors:
            embeddings = vectors["embeddings"]
        return DocumentState(
            filename=metadata["filename"],
            pdf_path=str(document_dir / "document.pdf"),
            pdf_hash=metadata["pdf_hash"],
            chunks=chunks,
            embeddings=embeddings,
            pages_count=metadata["pages_count"],
            page_texts=page_texts,
            modules=metadata["modules"],
            suggested_questions=metadata["suggested_questions"],
            document_id=document_id,
            is_ready=True,
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        logger.warning("Could not load session document state (%s).", type(error).__name__)
        raise HTTPException(status_code=500, detail="Stored document state is unavailable.") from None


def _get_active_document_hash(session_id):
    session_dir = get_session_store().session_dir(session_id)
    active_id = _cleanup_session_artifacts(session_id)
    active_path = session_dir / "active.json"
    if active_id is None:
        return None
    try:
        document_id = active_id
        documents_dir = (session_dir / "documents").resolve()
        document_dir = (documents_dir / document_id).resolve()
        if document_dir.parent != documents_dir:
            raise ValueError("Document path is outside the session directory.")
        metadata = json.loads((document_dir / "metadata.json").read_text(encoding="utf-8"))
        return metadata["pdf_hash"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Stored document metadata is unavailable.") from None


def _store_document_state(session_id, candidate):
    store = get_session_store()
    session_dir = store.session_dir(session_id)
    documents_dir = session_dir / "documents"
    documents_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    document_id = secrets.token_hex(16)
    staged_dir = documents_dir / ("." + document_id + ".tmp")
    document_dir = documents_dir / document_id
    staged_dir.mkdir(mode=0o700)
    prior_storage_bytes = None
    try:
        os.replace(candidate.pdf_path, staged_dir / "document.pdf")
        _safe_json_write(str(staged_dir / "metadata.json"), {
            "filename": candidate.filename,
            "pdf_hash": candidate.pdf_hash,
            "pages_count": candidate.pages_count,
            "modules": candidate.modules,
            "suggested_questions": candidate.suggested_questions,
        })
        _safe_json_write(str(staged_dir / "chunks.json"), candidate.chunks)
        _safe_json_write(str(staged_dir / "pages.json"), candidate.page_texts)
        vector_path = staged_dir / "embeddings.npz"
        with open(vector_path, "wb") as vector_file:
            np.savez_compressed(vector_file, embeddings=np.asarray(candidate.embeddings, dtype=np.float32))
            vector_file.flush()
            os.fsync(vector_file.fileno())
        os.chmod(vector_path, 0o600)
        staged_bytes = sum(path.stat().st_size for path in staged_dir.iterdir() if path.is_file())
        prior_storage_bytes = store.set_document_bytes(session_id, staged_bytes)
        os.replace(staged_dir, document_dir)
        previous_id = None
        active_path = session_dir / "active.json"
        if active_path.exists():
            try:
                previous_id = json.loads(active_path.read_text(encoding="utf-8")).get("document_id")
            except (OSError, ValueError, TypeError):
                previous_id = None
        _safe_json_write(str(active_path), {"document_id": document_id})
        if previous_id and previous_id != document_id:
            old_dir = (documents_dir / previous_id).resolve()
            if old_dir.parent == documents_dir.resolve() and old_dir.exists():
                shutil.rmtree(old_dir)
        candidate.pdf_path = str(document_dir / "document.pdf")
        candidate.document_id = document_id
        return candidate
    except Exception:
        if prior_storage_bytes is not None:
            try:
                store.set_document_bytes(session_id, prior_storage_bytes)
            except Exception:
                logger.error("Could not roll back session storage accounting.")
        if staged_dir.exists():
            shutil.rmtree(staged_dir, ignore_errors=True)
        active_path = session_dir / "active.json"
        active_id = None
        if active_path.exists():
            try:
                active_id = json.loads(active_path.read_text(encoding="utf-8")).get("document_id")
            except (OSError, ValueError, TypeError):
                active_id = None
        if document_dir.exists() and active_id != document_id:
            shutil.rmtree(document_dir, ignore_errors=True)
        raise

class DocumentState:
    def __init__(self, filename=None, pdf_path=None, pdf_hash=None, chunks=None, embeddings=None,
                 pages_count=0, page_texts=None, modules=None, suggested_questions=None,
                 document_id=None, is_ready=False):
        self.filename = filename
        self.pdf_path = pdf_path
        self.pdf_hash = pdf_hash
        self.chunks = chunks or []
        self.embeddings = embeddings
        self.pages_count = pages_count
        self.page_texts = page_texts or []
        self.modules = modules or []
        self.suggested_questions = suggested_questions or []
        self.document_id = document_id
        self.is_ready = is_ready

logger = logging.getLogger("cwp")

class PdfLimitError(Exception):
    pass


def _build_document_state(pdf_path: str, filename: str):
    with PDF_PROCESS_SEMAPHORE:
        return _build_document_state_impl(pdf_path, filename)


def _build_document_state_impl(pdf_path: str, filename: str):
    if os.path.getsize(pdf_path) > MAX_PDF_BYTES:
        raise PdfLimitError("PDF exceeds the configured upload size limit.")
    with fitz.open(pdf_path) as pdf:
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")
        if len(pdf) < 1:
            raise ValueError("PDF contains no pages.")
        if len(pdf) > MAX_PDF_PAGES:
            raise PdfLimitError("PDF exceeds the configured page limit.")

    current_hash = get_file_hash(pdf_path)
    pages = extract_text(pdf_path)
    if sum(len(page.get("text", "")) for page in pages) > MAX_PDF_TEXT_CHARS:
        raise PdfLimitError("PDF exceeds the configured extracted-text limit.")
    chunks = chunk_text(pages)
    if not chunks:
        raise ValueError("PDF contains no extractable text.")
    with MODEL_WORK_SEMAPHORE:
        embeddings = create_embeddings(chunks)
    modules = find_module_headings(pdf_path)
    with MODEL_WORK_SEMAPHORE:
        suggested_q = generate_suggested_questions(pages)
    return DocumentState(
        filename=filename,
        pdf_path=pdf_path,
        pdf_hash=current_hash,
        chunks=chunks,
        embeddings=embeddings,
        pages_count=len(pages),
        page_texts=[page["text"] for page in pages],
        modules=modules,
        suggested_questions=suggested_q,
        is_ready=True,
    )


def _get_document_state(session_id, seed_default=True):
    store = get_session_store()
    state = _load_document_state(session_id)
    if state is not None:
        return state
    if not seed_default or IS_PRODUCTION or not os.path.isfile(DEFAULT_PDF_PATH):
        return DocumentState()

    session_dir = store.session_dir(session_id)
    descriptor, staged_pdf = tempfile.mkstemp(prefix=".cwp-seed-", suffix=".pdf", dir=session_dir)
    try:
        with os.fdopen(descriptor, "wb") as staged_file, open(DEFAULT_PDF_PATH, "rb") as default_file:
            shutil.copyfileobj(default_file, staged_file)
        candidate = _build_document_state(staged_pdf, os.path.basename(DEFAULT_PDF_PATH))
        return _store_document_state(session_id, candidate)
    except Exception:
        if os.path.exists(staged_pdf):
            os.remove(staged_pdf)
        raise


def _request_session(request: Request):
    return request.state.cwp_session


def _request_allowed(request, session_id, action, limit, window_seconds=60):
    store = get_session_store()
    host = request.client.host if request.client else "unknown"
    if not store.allow_request(session_id, host, action, limit, window_seconds):
        raise HTTPException(status_code=429, detail="Request limit reached. Please wait and try again.")


@app.middleware("http")
async def session_security_middleware(request: Request, call_next):
    request_host = request.headers.get("host", "").split(":", 1)[0].lower()
    if request_host not in ALLOWED_HOSTS:
        return JSONResponse(status_code=400, content={"detail": "Request host is not allowed."})
    if request.url.path.startswith("/api/") or request.url.path == "/":
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid request size."})
            path_limit = MAX_PDF_BYTES + 1024 * 1024 if request.url.path == "/api/upload" else 8 * 1024 * 1024
            if declared_size < 0 or declared_size > path_limit:
                return JSONResponse(status_code=413, content={"detail": "Request exceeds the configured size limit."})
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if not origin:
                return JSONResponse(status_code=403, content={"detail": "Request origin is required."})
            from urllib.parse import urlsplit
            parsed_origin = urlsplit(origin)
            if parsed_origin.scheme not in {"http", "https"} or parsed_origin.netloc.lower() != request.headers.get("host", "").lower():
                return JSONResponse(status_code=403, content={"detail": "Cross-origin request rejected."})
        try:
            store = get_session_store()
            presented_token = request.cookies.get(SESSION_COOKIE_NAME)
            try:
                session = store.resolve(presented_token)
            except SessionNotFoundError:
                if request.url.path != "/" or request.method != "GET":
                    response = JSONResponse(status_code=401, content={"detail": "Session expired. Refresh the page to continue."})
                    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
                    return response
                session = store.resolve()
            if session.created:
                host = request.client.host if request.client else "unknown"
                if not store.allow_ip_request(host, "new-session", int(os.getenv("MAX_NEW_SESSIONS_PER_MINUTE", "20"))):
                    store.delete_session(session.session_id)
                    return JSONResponse(status_code=429, content={"detail": "Session creation limit reached. Please wait and retry."})
        except SessionCapacityError:
            return JSONResponse(status_code=503, content={"detail": "Temporary session capacity reached."})
        request.state.cwp_session = session
        try:
            response = await call_next(request)
        except Exception as error:
            logger.error("Unhandled request failure (%s).", type(error).__name__)
            return JSONResponse(status_code=500, content={"detail": "The request could not be completed."})
        if session.created or session.rotated:
            secure_cookie = IS_PRODUCTION or request.url.scheme == "https"
            response.set_cookie(
                SESSION_COOKIE_NAME,
                session.token,
                max_age=SESSION_TTL_SECONDS,
                httponly=True,
                secure=secure_cookie,
                samesite="lax",
                path="/",
            )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        elif request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https://*.supabase.co; "
            "connect-src 'self' https://*.supabase.co wss://*.supabase.co; "
            "worker-src 'self' blob: https://cdnjs.cloudflare.com; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    return await call_next(request)

class QuestionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    question: str

class MemoryRequest(BaseModel):
    model_config = {"extra": "forbid"}
    memory: str


class ConversationsRequest(BaseModel):
    model_config = {"extra": "forbid"}
    conversations: List[dict]
    document_hash: Optional[str] = None

@app.get("/api/config")
def get_config():
    """Return runtime configuration including Supabase configuration."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")

    # Verify whether valid (non-placeholder) Supabase configuration is present
    is_configured = bool(
        url and
        "xyzcompany.supabase.co" not in url and
        "your-supabase-url" not in url and
        key and
        "test_key" not in key
    )

    return {
        "supabase_url": url if url else "https://xyzcompany.supabase.co",
        "supabase_anon_key": key if key else "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYwOTQ1OTIwMCwiZXhwIjoyMDA0OTk1MjAwfQ.test_key",
        "supabase_configured": is_configured,
        "local_history_migration_enabled": not IS_PRODUCTION,
    }

@app.get("/api/status")
def get_status(request: Request):
    """Return the current anonymous session's document and preferences."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "status", int(os.getenv("MAX_STATUS_PER_MINUTE", "120")))
    with get_session_store().lock_for(session_id):
        state = _get_document_state(session_id)
        saved_mem, _ = get_session_store().get_preferences(session_id)
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        has_api_key = bool(key and key not in ["dummy_key_for_load", "AIzaSy_placeholder_key_for_load"])
        return {
            "status": "ready" if state.is_ready else "no_document",
            "has_api_key": has_api_key,
            "document": {
                "filename": state.filename,
                "pages_count": state.pages_count,
                "suggested_questions": state.suggested_questions,
                "hash": state.pdf_hash,
            } if state.is_ready else None,
            "answer_memory": {"text": saved_mem, "is_active": bool(saved_mem)},
        }

@app.get("/api/upload/status")
def get_upload_status(request: Request):
    """Expose only this session's upload stage without waiting on its processing lock."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "upload-status", int(os.getenv("MAX_STATUS_PER_MINUTE", "120")))
    with _upload_progress_guard:
        stage = _upload_progress.get(session_id, "idle")
    return {"stage": stage}

@app.get("/api/memory")
def get_memory(request: Request):
    """Retrieve the current session's answer presentation preference."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "memory-read", int(os.getenv("MAX_MEMORY_PER_MINUTE", "30")))
    mem, _ = get_session_store().get_preferences(session_id)
    return {
        "memory": mem,
        "is_active": bool(mem)
    }

@app.post("/api/memory")
def save_memory(req: MemoryRequest, request: Request):
    """Save an answer presentation preference for the current session."""
    if len(req.memory) > 5000:
        raise HTTPException(status_code=413, detail="Answer preference exceeds the configured limit.")
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "memory-write", int(os.getenv("MAX_MEMORY_WRITES_PER_HOUR", "20")), 3600)
    saved_mem = req.memory.strip()
    get_session_store().set_answer_memory(session_id, saved_mem)
    return {
        "success": True,
        "memory": saved_mem,
        "is_active": bool(saved_mem),
        "message": "Personalized Answer Memory saved successfully."
    }

@app.delete("/api/memory")
def delete_memory(request: Request):
    """Clear the current session's answer presentation preference."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "memory-write", int(os.getenv("MAX_MEMORY_WRITES_PER_HOUR", "20")), 3600)
    get_session_store().set_answer_memory(session_id, "")
    return {
        "success": True,
        "memory": "",
        "is_active": False,
        "message": "Personalized Answer Memory cleared."
    }


@app.get("/api/conversations")
def get_conversations(request: Request):
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "conversation-read", int(os.getenv("MAX_CONVERSATION_READS_PER_MINUTE", "60")))
    with get_session_store().lock_for(session_id):
        _, conversations = get_session_store().get_preferences(session_id)
        document_hash = _get_active_document_hash(session_id)
    return {"conversations": conversations, "document_hash": document_hash}


@app.put("/api/conversations")
def save_conversations(req: ConversationsRequest, request: Request):
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "conversation-write", int(os.getenv("MAX_CONVERSATION_WRITES_PER_MINUTE", "60")))
    try:
        with get_session_store().lock_for(session_id):
            active_hash = _get_active_document_hash(session_id)
            if req.document_hash != active_hash:
                raise HTTPException(status_code=409, detail="Conversation document changed. Refresh session history.")
            get_session_store().set_conversations(session_id, req.conversations)
    except HTTPException:
        raise
    except SessionStorageLimitError as error:
        raise HTTPException(status_code=507, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    return {"success": True}


@app.post("/api/session/logout")
def logout_session(request: Request):
    session_id = _request_session(request).session_id
    store = get_session_store()
    with store.lock_for(session_id):
        store.delete_session(session_id)
    response = JSONResponse({"success": True})
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response

@app.get("/api/pdf")
def get_active_pdf(request: Request):
    """Serves raw bytes of the currently active PDF document for viewer rendering with strict no-cache headers."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "pdf-download", int(os.getenv("MAX_PDF_DOWNLOADS_PER_MINUTE", "60")))
    with get_session_store().lock_for(session_id):
        state = _get_document_state(session_id)
        if not state.is_ready or not state.pdf_path or not os.path.exists(state.pdf_path):
            raise HTTPException(status_code=404, detail="No active document loaded.")
        with open(state.pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read(MAX_PDF_BYTES + 1)
        if len(pdf_bytes) > MAX_PDF_BYTES:
            raise HTTPException(status_code=500, detail="Stored document exceeds the configured size limit.")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

@app.post("/api/upload")
def upload_pdf(request: Request, file: UploadFile = File(...)):
    """Upload a new PDF document and process it through the existing RAG pipeline."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "upload", int(os.getenv("MAX_UPLOADS_PER_HOUR", "5")), 3600)
    filename = os.path.basename((file.filename or "").replace("\\", "/"))
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    if getattr(file, "size", None) is not None and file.size > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the configured upload size limit.")

    session_dir = get_session_store().session_dir(session_id)
    staged_path = None
    try:
        with get_session_store().lock_for(session_id):
            _set_upload_progress(session_id, "uploading")
            descriptor, staged_path = tempfile.mkstemp(prefix=".cwp-upload-", suffix=".pdf", dir=session_dir)
            total_bytes = 0
            with os.fdopen(descriptor, "wb") as buffer:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_PDF_BYTES:
                        raise HTTPException(status_code=413, detail="PDF exceeds the configured upload size limit.")
                    buffer.write(chunk)
            _set_upload_progress(session_id, "processing")
            candidate = _build_document_state(staged_path, filename)
            _store_document_state(session_id, candidate)
            get_session_store().set_conversations(session_id, [])

            return {
                "success": True,
                "message": f"Successfully loaded and indexed '{filename}'.",
                "document": {
                    "filename": candidate.filename,
                    "pages_count": candidate.pages_count,
                    "suggested_questions": candidate.suggested_questions,
                    "hash": candidate.pdf_hash,
                }
            }
    except HTTPException:
        raise
    except PdfLimitError as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    except SessionStorageLimitError as error:
        raise HTTPException(status_code=507, detail=str(error)) from None
    except Exception as error:
        logger.error("PDF upload failed (%s).", type(error).__name__)
        raise HTTPException(status_code=400, detail="PDF processing failed. Verify the file is readable and not encrypted.") from None
    finally:
        _set_upload_progress(session_id, None)
        if staged_path:
            try:
                os.unlink(staged_path)
            except FileNotFoundError:
                pass
            except OSError as error:
                logger.error("Could not remove staged PDF upload (%s).", type(error).__name__)

@app.delete("/api/document")
def remove_document(request: Request):
    """Remove only the current session's active PDF and index."""
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "document-remove", int(os.getenv("MAX_DOCUMENT_REMOVALS_PER_HOUR", "10")), 3600)
    store = get_session_store()
    with store.lock_for(session_id):
        session_dir = store.session_dir(session_id)
        active_path = session_dir / "active.json"
        if active_path.exists():
            try:
                document_id = json.loads(active_path.read_text(encoding="utf-8")).get("document_id")
                document_dir = (session_dir / "documents" / document_id).resolve()
                if document_dir.parent == (session_dir / "documents").resolve() and document_dir.exists():
                    shutil.rmtree(document_dir)
                store.set_document_bytes(session_id, 0)
                active_path.unlink(missing_ok=True)
            except (OSError, ValueError, TypeError):
                raise HTTPException(status_code=500, detail="Could not remove the active document.") from None
        store.set_conversations(session_id, [])

    return {
        "success": True,
        "message": "This session's active document and conversation were cleared."
    }

@app.post("/api/remove")
def remove_document_post_alias(request: Request):
    """POST alias for PDF removal endpoint."""
    return remove_document(request)

@app.post("/api/chat")
def chat(req: QuestionRequest, request: Request):
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "chat", int(os.getenv("MAX_CHAT_PER_MINUTE", "30")))
    if len(req.question) > MAX_QUESTION_CHARS:
        raise HTTPException(status_code=413, detail="Question exceeds the configured size limit.")
    with get_session_store().lock_for(session_id):
        return _chat(req, session_id)


def _insufficient_evidence_response(message: Optional[str] = None):
    """Return a conservative no-answer payload requiring explicit user opt-in to Gemini general knowledge."""
    fallback_message = message or (
        "I couldn't find enough relevant information in your PDF to answer this question reliably. "
        "Would you like Gemini to answer using its general knowledge instead?"
    )
    return {
        "answer": None,
        "sources": [],
        "found_in_pdf": False,
        "is_module_question": False,
        "memory_applied": False,
        "retrieved_chunks": [],
        "citations": [],
        "requires_fallback": True,
        "fallback_prompt": fallback_message,
        "message": fallback_message,
    }


def _chat(req: QuestionRequest, session_id):
    """
    Main Chat API Endpoint.
    Uses direct document-structure retrieval for positional/ordinal queries,
    and semantic RAG for conceptual questions with Personalized Answer Memory layer.
    """
    doc_state = _get_document_state(session_id)
    if not doc_state.is_ready or not doc_state.chunks or not doc_state.pdf_path:
        raise HTTPException(
            status_code=400,
            detail="No document loaded. Please upload a PDF before asking questions."
        )

    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    active_memory, _ = get_session_store().get_preferences(session_id)
    active_memory = (active_memory or "").strip()

    # 1. Structural/Positional Query Search (e.g. "What is the fourth question in Module 4?")
    structural_result = get_structural_answer(question, doc_state.pdf_path)
    if structural_result is not None:
        return {
            "answer": structural_result["answer"],
            "sources": structural_result["sources"],
            "found_in_pdf": structural_result["found_in_pdf"],
            "is_module_question": True,
            "memory_applied": False,
            "retrieved_chunks": [],
            "citations": []
        }

    # 2. Module count question check
    if is_module_count_question(question):
        answer = answer_module_count_question(doc_state.pdf_path)
        return {
            "answer": answer,
            "sources": [],
            "found_in_pdf": True,
            "is_module_question": True,
            "memory_applied": False,
            "retrieved_chunks": [],
            "citations": []
        }

    # 3. Normal Semantic RAG retrieval
    results = retrieve(
        question,
        doc_state.chunks,
        doc_state.embeddings
    )

    if not results:
        return _insufficient_evidence_response(
            "No relevant content found in the PDF for this question. Would you like Gemini to answer using its general knowledge instead?"
        )

    context = build_context(results)

    try:
        with MODEL_WORK_SEMAPHORE:
            answer = generate_answer(question, context, answer_memory=active_memory)
        if not answer:
            return _insufficient_evidence_response(
                "I couldn't find enough relevant evidence in your PDF to answer this question reliably. Would you like Gemini to answer using its general knowledge instead?"
            )
    except Exception as error:
        logger.error("PDF answer generation failed (%s).", type(error).__name__)
        err_msg = str(error).lower()
        status_code = 500
        if "429" in err_msg or "quota" in err_msg or "resourceexhausted" in err_msg:
            status_code = 429
            detail = "AI rate limit or quota exceeded. Please wait a moment and try again."
        elif "503" in err_msg or "unavailable" in err_msg:
            status_code = 503
            detail = "AI model is currently experiencing high demand. Please try again in a few moments."
        else:
            detail = "AI generation failed. Please retry shortly."
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "llm_error",
                "detail": detail
            }
        )

    # Validate the model's SOURCES line against the chunks actually supplied (S1..Sn).
    # Citations carry highlight evidence only if the answer demonstrably reproduces
    # that chunk's text; retrieval score is never used as proof of support.
    answer, cited_idx, rejected_ids = parse_sources_line(answer, len(results))
    if rejected_ids:
        print(f"[CWP Citations] Ignored invalid source ids from model: {rejected_ids}")
    fallback_phrase = (answer or "").lower()
    if (
        "does not contain information" in fallback_phrase
        or "does not contain any information" in fallback_phrase
        or "does not contain enough information" in fallback_phrase
        or "not enough information in the pdf" in fallback_phrase
        or "not enough relevant information" in fallback_phrase
        or "cannot be found in the pdf" in fallback_phrase
        or "could not be found in the pdf context" in fallback_phrase
        or "the pdf context excerpt does not contain" in fallback_phrase
    ):
        return _insufficient_evidence_response(
            "I couldn't find enough supporting evidence in your PDF to answer this question reliably. Ask Gemini instead?"
        )

    answer, supported_indexes, has_unsupported_parts = filter_supported_answer(answer, results)
    if not answer:
        return _insufficient_evidence_response(
            "I couldn't verify enough information in your PDF to answer this question. Would you like Gemini to answer using its general knowledge instead?"
        )
    if has_unsupported_parts:
        answer = (
            answer.rstrip()
            + "\n\nSome parts of your question were not supported by the PDF and were omitted."
        )

    citations = build_citations(answer, results, supported_indexes, doc_state.page_texts)

    # Never expose a page badge unless the answer contains verified support from it.
    pages = sorted(set(
        citation["page"]
        for citation in citations
        if citation.get("evidence_verified") and isinstance(citation.get("page"), int)
    ))

    return {
        "answer": answer,
        "sources": pages,
        "found_in_pdf": bool(results),
        "is_module_question": False,
        "memory_applied": bool(active_memory),
        "citations": citations,
        "retrieved_chunks": [
            {
                "page": r["page"],
                "score": float(r.get("score", 0.0)),
                "source_type": r.get("source", "semantic"),
                "text": r["text"]
            }
            for r in results
        ] if results else []
    }

@app.post("/api/chat/image")
async def chat_image(
    request: Request,
    file: UploadFile = File(...),
    question: Optional[str] = Form(None)
):
    """
    Image Chat API Endpoint.
    Processes uploaded image and executes grounded RAG search against active PDF.
    """
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "image", int(os.getenv("MAX_IMAGE_PER_MINUTE", "5")))
    max_image_bytes = MAX_IMAGE_BYTES
    if question and len(question) > MAX_QUESTION_CHARS:
        raise HTTPException(status_code=413, detail="Question exceeds the configured size limit.")
    if getattr(file, "size", None) is not None and file.size > max_image_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds the configured upload size limit.")
    with get_session_store().lock_for(session_id):
        doc_state = _get_document_state(session_id)
    if not doc_state.is_ready or not doc_state.chunks:
        raise HTTPException(
            status_code=400,
            detail="No document loaded. Please upload a PDF before asking questions."
        )

    allowed_extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")
    if file.filename and not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Supported formats: PNG, JPG, JPEG, WEBP, BMP, GIF."
        )

    try:
        image_bytes = await file.read(max_image_bytes + 1)
        if len(image_bytes) > max_image_bytes:
            raise HTTPException(status_code=413, detail="Image exceeds the configured upload size limit.")
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded image file is empty.")

        content_type = file.content_type or "image/png"
        if not content_type.startswith("image/"):
            content_type = "image/png"

        from google.genai import types

        vision_client = get_client()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)

        ocr_prompt = (
            "Analyze this image carefully. Extract all readable text, formulas, diagrams, questions, "
            "answers, and key technical concepts present in the image. "
            "Provide a clear, detailed transcription and key search terms for retrieval."
        )

        extracted_text = ""
        models_to_try = [generator.PRIMARY_MODEL, generator.FALLBACK_MODEL]

        for m_name in models_to_try:
            try:
                with MODEL_WORK_SEMAPHORE:
                    ocr_resp = vision_client.models.generate_content(
                        model=m_name,
                        contents=[image_part, ocr_prompt]
                    )
                if ocr_resp and ocr_resp.text:
                    extracted_text = ocr_resp.text.strip()
                    break
            except Exception as error:
                logger.warning("Image OCR failed (%s).", type(error).__name__)

        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text or readable content from the uploaded image."
            )

        user_q = (question or "").strip()
        if user_q:
            search_query = f"{user_q}\nExtracted Image Content: {extracted_text}"
        else:
            search_query = extracted_text

        results = retrieve(
            search_query,
            doc_state.chunks,
            doc_state.embeddings
        )

        if not results:
            if _get_active_document_hash(session_id) != doc_state.pdf_hash:
                raise HTTPException(status_code=409, detail="The active PDF changed while processing. Please retry.")
            return {
                "answer": None,
                "sources": [],
                "found_in_pdf": False,
                "extracted_image_text": extracted_text,
                "memory_applied": False,
                "retrieved_chunks": [],
                "message": "No relevant content found in the PDF corresponding to this image."
            }

        context = build_context(results)
        active_memory, _ = get_session_store().get_preferences(session_id)
        active_memory = active_memory.strip()

        memory_prompt_section = ""
        if active_memory:
            memory_prompt_section = f"""
CRITICAL ANSWER PRESENTATION INSTRUCTIONS (USER ANSWER MEMORY):
The user has set the following custom answer presentation preference/memory. Format and structure your answer strictly according to these presentation rules while keeping all content strictly grounded in the PDF context below:
---
{active_memory}
---
"""

        grounded_prompt = f"""
The user uploaded an image containing the following extracted content:
---
{extracted_text}
---

User Request / Question:
{user_q if user_q else "Find and explain relevant information in the PDF corresponding to this image content."}

Answer the user's question using ONLY the information provided in the PDF context below.

If the answer cannot be found in the PDF context, respond with exactly this phrase:
PDF_ANSWER_NOT_FOUND

Do not use outside knowledge.
The PDF context blocks are labelled [S1], [S2], and so on. End the response with one line in exactly this form:
SOURCES: S1,S2
List only blocks that directly support the answer. If none support it, use SOURCES: NONE.
{memory_prompt_section}
PDF CONTEXT:
{context}
"""

        answer = None
        for m_name in models_to_try:
            try:
                with MODEL_WORK_SEMAPHORE:
                    resp = vision_client.models.generate_content(
                        model=m_name,
                        contents=grounded_prompt
                    )
                ans = resp.text.strip()
                if "PDF_ANSWER_NOT_FOUND" not in ans:
                    answer, cited_indexes, _ = parse_sources_line(ans, len(results))
                    break
            except Exception as error:
                logger.warning("Image answer generation failed (%s).", type(error).__name__)

        if answer is None:
            if _get_active_document_hash(session_id) != doc_state.pdf_hash:
                raise HTTPException(status_code=409, detail="The active PDF changed while processing. Please retry.")
            return {
                "answer": None,
                "sources": [],
                "found_in_pdf": False,
                "extracted_image_text": extracted_text,
                "memory_applied": False,
                "retrieved_chunks": results,
                "message": "The PDF context does not contain enough information corresponding to this image."
            }

        if _get_active_document_hash(session_id) != doc_state.pdf_hash:
            raise HTTPException(status_code=409, detail="The active PDF changed while processing. Please retry.")
        citations = build_citations(answer, results, cited_indexes, doc_state.page_texts)
        pages = sorted(set(
            citation["page"]
            for citation in citations
            if citation.get("evidence_verified") and isinstance(citation.get("page"), int)
        ))

        return {
            "answer": answer,
            "sources": pages,
            "found_in_pdf": True,
            "extracted_image_text": extracted_text,
            "is_module_question": False,
            "memory_applied": bool(active_memory),
            "citations": citations,
            "retrieved_chunks": [
                {
                    "page": r["page"],
                    "score": float(r.get("score", 0.0)),
                    "source_type": r.get("source", "semantic"),
                    "text": r["text"]
                }
                for r in results
            ]
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.error("Image endpoint failed (%s).", type(error).__name__)
        raise HTTPException(status_code=500, detail="Image processing failed. Please verify the image and retry.") from None

@app.post("/api/chat/fallback")
def chat_fallback(req: QuestionRequest, request: Request):
    """
    General Knowledge Fallback Endpoint.
    Calls Gemini general knowledge when user requests it, with optional Answer Memory.
    """
    session_id = _request_session(request).session_id
    _request_allowed(request, session_id, "fallback", int(os.getenv("MAX_FALLBACK_PER_MINUTE", "10")))
    if len(req.question) > MAX_QUESTION_CHARS:
        raise HTTPException(status_code=413, detail="Question exceeds the configured size limit.")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    active_memory, _ = get_session_store().get_preferences(session_id)
    active_memory = (active_memory or "").strip()

    try:
        with MODEL_WORK_SEMAPHORE:
            answer = generate_general_answer(question, answer_memory=active_memory)
        if answer is None:
            raise HTTPException(status_code=503, detail="Gemini could not generate a response. Please retry shortly.")

        return {
            "answer": answer,
            "source_label": "Gemini general knowledge",
            "found_in_pdf": False,
            "memory_applied": bool(active_memory)
        }
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Gemini fallback failed (%s).", type(error).__name__)
        error_text = str(error).lower()
        if "429" in error_text or "quota" in error_text or "resourceexhausted" in error_text:
            status_code = 429
            detail = "Gemini rate limit or quota reached. Please wait a moment and try again."
        elif "503" in error_text or "unavailable" in error_text or "timeout" in error_text:
            status_code = 503
            detail = "Gemini is temporarily unavailable. Please retry shortly."
        else:
            status_code = 503
            detail = "Gemini fallback is temporarily unavailable. Please retry."
        raise HTTPException(status_code=status_code, detail=detail) from None

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "public")
os.makedirs(FRONTEND_DIR, exist_ok=True)
STATIC_ASSETS = {"style.css", "cwp-mark.svg", "cwp-favicon.svg", "app.js", "highlight.js", "markdown.js"}


@app.get("/static/{asset_path:path}")
def get_static_asset(asset_path: str):
    if asset_path not in STATIC_ASSETS or os.path.basename(asset_path) != asset_path:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(
        os.path.join(FRONTEND_DIR, asset_path),
        headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"},
    )

@app.get("/")
def serve_index():
    index_html = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_html):
        return FileResponse(index_html)
    return {"message": "CWP API Server is running. Frontend static files not found in public/."}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0" if IS_PRODUCTION else "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    trusted_proxies = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=not IS_PRODUCTION,
        workers=1 if IS_PRODUCTION else None,
        proxy_headers=True,
        forwarded_allow_ips=trusted_proxies,
    )
