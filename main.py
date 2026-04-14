"""

uvicorn main:app --reload --host 0.0.0.0 --port 8000

"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import start_http_server

from agent.react_agent import ReactAgent
from config.database import ENABLE_METRICS, METRICS_AUTH_TOKEN, METRICS_PORT
from tasks.celery_tasks import celery_app as task_celery_app
from utils.auth_service import (
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SECURE,
    AUTH_TOKEN_TTL_SECONDS,
    AuthService,
    AuthUser,
)
from utils.logger_handler import get_logger
from utils.metrics import (
    CONTENT_TYPE_LATEST,
    record_model_response,
    record_request_metrics,
    registry as metrics_registry,
    render_metrics,
    session_created,
    session_storage_errors,
    set_active_sessions_count,
)
from utils.session_storage import get_storage_backend

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    on_startup()
    yield


app = FastAPI(title="机器人智能客服", version="1.0.0", lifespan=lifespan)
app.celery_app = task_celery_app

_default_origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", ",".join(_default_origins)).split(",")
    if origin.strip()
] or _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent: ReactAgent | None = None
_sessions: dict[str, list[dict]] = {}
_session_owners: dict[str, str] = {}
_storage_backend = None
_auth_service: AuthService | None = None
_metrics_server_started = False


def _get_auth_service() -> AuthService:
    """Lazily initialize AuthService with error handling."""
    global _auth_service
    if _auth_service is None:
        try:
            _auth_service = AuthService()
        except Exception as exc:
            logger.error("Failed to initialize AuthService: %s", exc)
            raise
    return _auth_service

_DEBUG_LOG_PATH = Path("/Users/zhuangbohan/资料/AIPython/AgentProject/.cursor/debug-7a89fb.log")


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": "7a89fb",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def get_agent() -> ReactAgent:
    global _agent
    if _agent is None:
        _agent = ReactAgent()
    return _agent


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入")
    session_id: Optional[str] = Field(None, description="会话 ID，不传则新建会话")


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class StreamChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入")
    session_id: Optional[str] = Field(None, description="会话 ID，不传则新建会话")


class SessionResponse(BaseModel):
    session_id: str
    history: list[dict]


class SessionSummary(BaseModel):
    session_id: str
    title: str
    preview: str
    message_count: int


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthUserResponse(BaseModel):
    user_id: str
    username: str


class AuthResponse(BaseModel):
    user: AuthUserResponse | None


def _sync_active_session_metric() -> None:
    if ENABLE_METRICS:
        set_active_sessions_count(len(_sessions))


def on_startup() -> None:
    global _storage_backend, _sessions, _session_owners, _metrics_server_started
    _debug_log("H1", "main.py:on_startup", "backend startup", {"ok": True})

    try:
        _storage_backend = get_storage_backend(use_db=True)
        loaded = _storage_backend.load_all_active_with_users(max_days=7)
        _sessions = {session_id: item["messages"] for session_id, item in loaded.items()}
        _session_owners = {session_id: item["user_id"] for session_id, item in loaded.items()}
        logger.info("Loaded %s sessions from database", len(loaded))
    except Exception as exc:
        logger.error("Failed to initialize storage backend: %s", exc)
        _storage_backend = get_storage_backend(use_db=False)
        _sessions = {}
        _session_owners = {}

    _sync_active_session_metric()

    if ENABLE_METRICS and not _metrics_server_started:
        try:
            start_http_server(METRICS_PORT, addr="0.0.0.0", registry=metrics_registry)
            _metrics_server_started = True
            logger.info("Prometheus metrics server started on port %s", METRICS_PORT)
        except OSError as exc:
            logger.warning("Failed to start Prometheus metrics server on port %s: %s", METRICS_PORT, exc)

    celery_app = getattr(app, "celery_app", None)
    if celery_app is None:
        logger.warning("Celery app not attached; async task queue may be unavailable")
    else:
        logger.info("Celery app attached to FastAPI application")


def _serialize_session_history(session_id: str) -> list[dict]:
    history = _sessions.get(session_id, [])
    result: list[dict] = []
    for item in history:
        role = item.get("role")
        content = item.get("content", "")
        if role in {"user", "assistant"} and isinstance(content, str):
            result.append({"role": role, "content": content})
    return result


def _build_session_summary(session_id: str, history: list[dict]) -> SessionSummary:
    title = "New Chat"
    preview = ""
    message_count = len(history)

    for item in history:
        if item.get("role") == "user":
            content = item.get("content", "")
            title = content[:50] if content else "New Chat"
            break

    for item in reversed(history):
        if item.get("role") == "user":
            content = item.get("content", "")
            preview = content[:100] if content else ""
            break

    return SessionSummary(
        session_id=session_id,
        title=title,
        preview=preview,
        message_count=message_count,
    )


def _sanitize_assistant_reply(user_message: str, reply: str) -> str:
    text = (reply or "").strip()
    if not text:
        return text

    normalized_user = " ".join((user_message or "").split())
    normalized_text = " ".join(text.split())
    if normalized_user and normalized_text.startswith(normalized_user):
        text = text[len(user_message):].lstrip("：:，,。.!！?？- ")

    prefixes = [
        user_message.strip(),
        f"用户问题：{user_message.strip()}",
        f"你问的是：{user_message.strip()}",
        f"根据你的问题，{user_message.strip()}",
    ]
    for prefix in prefixes:
        if prefix and text.startswith(prefix):
            text = text[len(prefix):].lstrip("：:，,。.!！?？- ")

    sensitive_markers = [
        "用户id",
        "用户ID",
        "user_id",
        "session_id",
        "token",
        "内部标识",
    ]
    normalized_lower = text.lower()
    if any(marker.lower() in normalized_lower for marker in sensitive_markers):
        return "这类内部标识仅用于系统内部处理，不能对外提供。"

    return text.strip()


def _to_auth_response(user: AuthUser) -> AuthResponse:
    return AuthResponse(user=AuthUserResponse(user_id=user.user_id, username=user.username))


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=AUTH_TOKEN_TTL_SECONDS,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", samesite="lax")


def get_current_user(request: Request) -> AuthUser:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    user = _get_auth_service().verify_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录")
    return user


def get_optional_current_user(request: Request) -> AuthUser | None:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None

    return _get_auth_service().verify_token(token)


def _require_session_access(session_id: str, user_id: str) -> None:
    owner = _session_owners.get(session_id)
    if owner != user_id:
        raise HTTPException(status_code=404, detail="session not found")


def _persist_session(session_id: str, user_id: str) -> None:
    if _storage_backend:
        success = _storage_backend.save_session(session_id, _sessions[session_id], user_id)
        if not success and ENABLE_METRICS:
            session_storage_errors.labels(error_type="save_session").inc()


def _run_chat_side_effects(
    *,
    agent: ReactAgent,
    user_id: str,
    user_query: str,
    assistant_answer: str,
    session_id: str,
) -> None:
    try:
        agent.save_long_term_memory(
            user_id=user_id,
            user_query=user_query,
            assistant_answer=assistant_answer,
        )
    except Exception as exc:
        _debug_log(
            "H5",
            "main.py:_run_chat_side_effects",
            "save_long_term_memory failed",
            {"error_type": type(exc).__name__, "error": str(exc)[:100]},
        )

    try:
        from tasks.celery_tasks import save_session_async

        save_session_async.delay(session_id, _sessions[session_id], user_id)
    except Exception as exc:
        logger.warning("Failed to queue session save: %s", exc)
        if ENABLE_METRICS:
            session_storage_errors.labels(error_type="queue_session_save").inc()
        _persist_session(session_id, user_id)


def _chat_non_stream(req: ChatRequest, current_user: AuthUser) -> ChatResponse:
    agent = get_agent()
    sid = req.session_id or str(uuid4())
    if req.session_id:
        _require_session_access(req.session_id, current_user.user_id)
    if sid not in _sessions:
        _sessions[sid] = []
        _session_owners[sid] = current_user.user_id
        if ENABLE_METRICS:
            session_created.inc()
        _sync_active_session_metric()

    _sessions[sid].append({"role": "user", "content": req.message})
    history = list(_sessions[sid])

    parts: list[str] = []
    started_at = time.perf_counter()
    for chunk in agent.execute_stream(req.message, history, user_id=current_user.user_id):
        parts.append(chunk)
    if ENABLE_METRICS:
        record_model_response("react_agent", time.perf_counter() - started_at)
    full_answer = _sanitize_assistant_reply(req.message, "".join(parts).strip())

    _sessions[sid].append({"role": "assistant", "content": full_answer})

    _run_chat_side_effects(
        agent=agent,
        user_id=current_user.user_id,
        user_query=req.message,
        assistant_answer=full_answer,
        session_id=sid,
    )

    return ChatResponse(reply=full_answer, session_id=sid)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if not ENABLE_METRICS:
        return await call_next(request)

    started_at = time.perf_counter()
    status_label = "500"
    try:
        response = await call_next(request)
        status_label = str(response.status_code)
        return response
    except HTTPException as exc:
        status_label = str(exc.status_code)
        raise
    finally:
        record_request_metrics(request.url.path, status_label, time.perf_counter() - started_at)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request) -> Response:
    if not ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="metrics disabled")

    if METRICS_AUTH_TOKEN:
        request_token = request.headers.get("x-metrics-token", "")
        if not hmac.compare_digest(request_token, METRICS_AUTH_TOKEN):
            raise HTTPException(status_code=403, detail="forbidden")
    else:
        client_host = (request.client.host if request.client else "") or ""
        if client_host.startswith("::ffff:"):
            client_host = client_host[7:]
        if client_host not in {"127.0.0.1", "::1", "localhost"}:
            raise HTTPException(status_code=403, detail="forbidden")

    return Response(content=render_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: AuthRequest, response: Response) -> AuthResponse:
    try:
        user = _get_auth_service().register_user(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = _get_auth_service().create_token(user)
    _set_auth_cookie(response, token)
    return _to_auth_response(user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest, response: Response) -> AuthResponse:
    user = _get_auth_service().authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = _get_auth_service().create_token(user)
    _set_auth_cookie(response, token)
    return _to_auth_response(user)


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    _clear_auth_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=AuthResponse)
def me(current_user: AuthUser | None = Depends(get_optional_current_user)) -> AuthResponse:
    if current_user is None:
        return AuthResponse(user=None)
    return _to_auth_response(current_user)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, current_user: AuthUser = Depends(get_current_user)) -> ChatResponse:
    return _chat_non_stream(req, current_user)


@app.post("/api/chat/stream")
async def chat_stream(
    payload: StreamChatRequest,
    request: Request,
    current_user: AuthUser = Depends(get_current_user),
):
    message = payload.message
    session_id = payload.session_id
    _debug_log(
        "H2",
        "main.py:chat_stream",
        "stream request entry",
        {"message_len": len(message or ""), "has_session_id": bool(session_id)},
    )

    agent = get_agent()
    sid = session_id or str(uuid4())
    if session_id:
        _require_session_access(session_id, current_user.user_id)
    if sid not in _sessions:
        _sessions[sid] = []
        _session_owners[sid] = current_user.user_id
        if ENABLE_METRICS:
            session_created.inc()
        _sync_active_session_metric()

    _sessions[sid].append({"role": "user", "content": message})
    history = list(_sessions[sid])

    async def gen():
        buf: list[str] = []
        error_occurred = False
        client_disconnected = False
        emitted_text = ""
        started_at = time.perf_counter()
        try:
            for chunk in agent.execute_stream(message, history, user_id=current_user.user_id):
                if await request.is_disconnected():
                    client_disconnected = True
                    break
                buf.append(chunk)

                partial_answer = _sanitize_assistant_reply(message, "".join(buf).strip())
                if not partial_answer or partial_answer == emitted_text:
                    continue

                if partial_answer.startswith(emitted_text):
                    delta = partial_answer[len(emitted_text):]
                else:
                    delta = partial_answer

                emitted_text = partial_answer
                if delta:
                    yield f"data: {json.dumps({'chunk': delta}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            _debug_log(
                "H3",
                "main.py:chat_stream.gen",
                "stream generator exception",
                {"error_type": type(exc).__name__, "error": str(exc)},
            )
            error_occurred = True
        finally:
            if ENABLE_METRICS:
                record_model_response("react_agent", time.perf_counter() - started_at)

        full_answer = emitted_text or _sanitize_assistant_reply(message, "".join(buf).strip())
        if not full_answer and error_occurred:
            full_answer = "生成回复时出错：请稍后重试。"
        elif client_disconnected and not full_answer:
            full_answer = "已停止生成"

        if full_answer and full_answer != emitted_text:
            if full_answer.startswith(emitted_text):
                delta = full_answer[len(emitted_text):]
            else:
                delta = full_answer
            if delta:
                yield f"data: {json.dumps({'chunk': delta}, ensure_ascii=False)}\n\n"

        _sessions[sid].append({"role": "assistant", "content": full_answer})

        asyncio.create_task(
            asyncio.to_thread(
                _run_chat_side_effects,
                agent=agent,
                user_id=current_user.user_id,
                user_query=message,
                assistant_answer=full_answer,
                session_id=sid,
            )
        )

        _debug_log("H4", "main.py:chat_stream.gen", "stream done", {"answer_len": len(full_answer), "client_disconnected": client_disconnected})
        if not client_disconnected:
            yield f"data: {json.dumps({'session_id': sid, 'done': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.delete("/api/session/{session_id}")
def clear_session(session_id: str, current_user: AuthUser = Depends(get_current_user)):
    _require_session_access(session_id, current_user.user_id)
    if session_id in _sessions:
        del _sessions[session_id]
        _session_owners.pop(session_id, None)
        _sync_active_session_metric()
        if _storage_backend:
            success = _storage_backend.delete_session(session_id)
            if not success and ENABLE_METRICS:
                session_storage_errors.labels(error_type="delete_session").inc()
        return {"ok": True, "session_id": session_id}
    raise HTTPException(status_code=404, detail="session not found")


@app.get("/api/session/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, current_user: AuthUser = Depends(get_current_user)) -> SessionResponse:
    _require_session_access(session_id, current_user.user_id)
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="session not found")
    return SessionResponse(session_id=session_id, history=_serialize_session_history(session_id))


@app.get("/api/sessions", response_model=SessionListResponse)
def list_sessions(current_user: AuthUser = Depends(get_current_user)) -> SessionListResponse:
    sessions = [
        _build_session_summary(session_id, history)
        for session_id, history in reversed(list(_sessions.items()))
        if _session_owners.get(session_id) == current_user.user_id
    ]
    return SessionListResponse(sessions=sessions)
