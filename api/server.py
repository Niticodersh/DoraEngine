"""FastAPI server exposing the decoupled DoraEngine backend."""
from __future__ import annotations

import asyncio
import json
import threading
from queue import Queue

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from api.constants import AGENT_STAGES, SUGGESTIONS
from api.service import generate_followup_questions, run_research_payload, stage_payload
from api.user_service import (
    create_auth_response,
    create_user,
    authenticate_user,
    get_chat_history,
    get_plans,
    get_public_user,
    get_user_runtime_config,
    save_chat_history,
    update_plan,
    update_user_profile,
)
from utils.docx_export import generate_docx
from utils.paper_pdf_export import generate_pdf
from utils.security import decode_token


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)


class SignupRequest(BaseModel):
    email: str
    password: str
    mobile: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    groq_api_key: str | None = None
    tavily_api_key: str | None = None


class PlanUpdateRequest(BaseModel):
    plan_code: str


class FollowupRequest(BaseModel):
    query: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    count: int = Field(default=6, ge=1, le=10)


class PdfExportRequest(BaseModel):
    query: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    timestamp: str | None = None


class DocxExportRequest(PdfExportRequest):
    pass


app = FastAPI(title="DoraEngine API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    message = str(exc)
    status = 400 if isinstance(exc, ValueError) else 500
    return HTTPException(status_code=status, detail=message)


def _current_user_id(authorization: str | None = None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return payload["sub"]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "message": "DoraEngine API is running"}


@app.get("/api/config")
def config() -> dict:
    return {"suggestions": SUGGESTIONS, "agent_stages": AGENT_STAGES}


@app.get("/api/plans")
def plans() -> dict:
    return {"plans": get_plans()}


@app.post("/api/auth/signup")
def signup(request: SignupRequest):
    try:
        user = create_user(request.email, request.password, request.mobile)
        return create_auth_response(user)
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/auth/login")
def login(request: LoginRequest):
    try:
        user = authenticate_user(request.email, request.password)
        return create_auth_response(user)
    except Exception as exc:
        raise _http_error(exc) from exc


@app.get("/api/auth/me")
def me(authorization: str | None = Header(default=None, alias="Authorization")):
    try:
        user_id = _current_user_id(authorization)
        return {"user": get_public_user(user_id)}
    except Exception as exc:
        raise _http_error(exc) from exc


@app.put("/api/profile")
def profile_update(
    request: ProfileUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    try:
        user_id = _current_user_id(authorization)
        user = update_user_profile(
            user_id,
            groq_api_key=request.groq_api_key,
            tavily_api_key=request.tavily_api_key,
        )
        return {"user": user}
    except Exception as exc:
        raise _http_error(exc) from exc


@app.put("/api/profile/plan")
def profile_plan(
    request: PlanUpdateRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    try:
        user_id = _current_user_id(authorization)
        user = update_plan(user_id, request.plan_code)
        return {"user": user}
    except Exception as exc:
        raise _http_error(exc) from exc


@app.get("/api/history")
def history(authorization: str | None = Header(default=None, alias="Authorization")):
    try:
        user_id = _current_user_id(authorization)
        return {"items": get_chat_history(user_id)}
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/research")
def research(request: ResearchRequest, authorization: str | None = Header(default=None, alias="Authorization")):
    try:
        user_id = _current_user_id(authorization)
        runtime = get_user_runtime_config(user_id)
        result = run_research_payload(
            request.query,
            groq_api_key=runtime["groq_api_key"],
            tavily_api_key=runtime["tavily_api_key"],
            requires_user_key=runtime["requires_user_api_key"],
        )
        if result.get("success"):
            save_chat_history(user_id, request.query, result)
        return result
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/followups")
def followups(request: FollowupRequest) -> dict:
    try:
        return {
            "followups": generate_followup_questions(request.query, request.answer, request.count)
        }
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/export/pdf")
def export_pdf(request: PdfExportRequest, authorization: str | None = Header(default=None, alias="Authorization")):
    try:
        user_id = _current_user_id(authorization)
        runtime = get_user_runtime_config(user_id)
        pdf_bytes = generate_pdf(
            query=request.query,
            answer=request.answer,
            sources=request.sources,
            confidence=request.confidence,
            timestamp=request.timestamp,
            watermark_text="DoraEngine Free Plan" if runtime["watermark_exports"] else None,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="doraengine-paper.pdf"'},
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/export/docx")
def export_docx(request: DocxExportRequest, authorization: str | None = Header(default=None, alias="Authorization")):
    try:
        user_id = _current_user_id(authorization)
        runtime = get_user_runtime_config(user_id)
        docx_bytes = generate_docx(
            query=request.query,
            answer=request.answer,
            sources=request.sources,
            confidence=request.confidence,
            timestamp=request.timestamp,
            watermark_text="DoraEngine Free Plan" if runtime["watermark_exports"] else None,
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="doraengine-paper.docx"'},
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/research/stream")
async def research_stream(
    request: ResearchRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    queue: Queue = Queue()
    completion = threading.Event()
    user_id = _current_user_id(authorization)
    runtime = get_user_runtime_config(user_id)

    def progress(agent: str, action: str) -> None:
        queue.put(
            {
                "type": "stage",
                "agent": agent,
                "action": action,
                "stage": stage_payload(agent),
            }
        )

    def worker() -> None:
        try:
            result = run_research_payload(
                request.query,
                progress_callback=progress,
                groq_api_key=runtime["groq_api_key"],
                tavily_api_key=runtime["tavily_api_key"],
                requires_user_key=runtime["requires_user_api_key"],
            )
            if result.get("success"):
                save_chat_history(user_id, request.query, result)
            queue.put({"type": "complete", "result": result})
        except Exception as exc:
            queue.put({"type": "error", "error": str(exc)})
        finally:
            completion.set()

    threading.Thread(target=worker, daemon=True).start()

    async def event_stream():
        loop = asyncio.get_running_loop()
        while not (completion.is_set() and queue.empty()):
            item = await loop.run_in_executor(None, queue.get)
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
