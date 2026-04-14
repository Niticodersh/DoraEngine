"""FastAPI server exposing the decoupled DoraEngine backend.

MVP NOTE: Chat history endpoints are commented out.
         OTP verification endpoints added for mobile/email verification.
"""
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
    generate_and_send_otp,
    generate_password_reset_token,
    verify_user_otp,
    # get_chat_history,   # MVP: history disabled
    get_plans,
    get_public_user,
    get_user_runtime_config,
    reset_password_with_token,
    # save_chat_history,  # MVP: history disabled
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
    # Set by the frontend after Firebase email-link verification completes.
    # TODO (prod): require a Firebase ID token and verify with firebase-admin
    # instead of trusting this boolean from the client.
    email_verified: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    groq_api_key: str | None = None
    # tavily_api_key: str | None = None  # MVP: not exposed to users


class PlanUpdateRequest(BaseModel):
    plan_code: str


class OtpVerifyRequest(BaseModel):
    otp_code: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str

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
        user = create_user(
            request.email,
            request.password,
            request.mobile,
            is_verified=request.email_verified,
        )
        auth = create_auth_response(user)
        # Only generate backend OTP for legacy / unverified signups.
        # Firebase-verified signups skip this path entirely.
        if not request.email_verified:
            otp_result = generate_and_send_otp(user["id"])
            return {**auth, "otp_info": otp_result}
        return auth
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


# ── OTP Endpoints ──────────────────────────────────────────────────────────────

@app.post("/api/auth/send-otp")
def send_otp(authorization: str | None = Header(default=None, alias="Authorization")):
    """
    (Re)generates and sends OTP to user's registered mobile and email.
    Call this on signup (auto-triggered) and when user clicks 'Resend OTP'.

    TODO (Production): Remove 'dev_otp' from the response. Wire actual
    SMS (Twilio/MSG91) and email (SendGrid/SES) delivery inside
    generate_and_send_otp() in user_service.py.
    """
    try:
        user_id = _current_user_id(authorization)
        result = generate_and_send_otp(user_id)
        return result
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/auth/verify-otp")
def verify_otp(
    request: OtpVerifyRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """
    Validates the submitted OTP. Marks user as verified on success.
    Returns updated user object.
    """
    try:
        user_id = _current_user_id(authorization)
        user = verify_user_otp(user_id, request.otp_code)
        return {"user": user}
    except Exception as exc:
        raise _http_error(exc) from exc



# ── Password Reset Endpoints ───────────────────────────────────────────────────

@app.post("/api/auth/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    origin: str | None = Header(default=None, alias="Origin"),
    referer: str | None = Header(default=None, alias="Referer"),
):
    """
    Generates a password-reset token for the given email (if it exists).
    Always returns 200 to prevent email enumeration.

    If GMAIL_USER + GMAIL_APP_PASSWORD are set in .env, sends a real email.
    Otherwise returns dev_reset_url for local click-through testing.
    """
    try:
        # Determine the app's base URL from the request so the reset link
        # in the email goes to the correct frontend (works for any domain).
        base_url = origin or ""
        if not base_url and referer:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
        if not base_url:
            base_url = "http://localhost:5173"  # local dev fallback

        result = generate_password_reset_token(request.email, app_base_url=base_url)
        return result
    except Exception as exc:
        raise _http_error(exc) from exc


@app.post("/api/auth/reset-password")
def reset_password(request: ResetPasswordRequest):
    """
    Validates the reset token and updates the user password.
    """
    try:
        result = reset_password_with_token(request.email, request.token, request.new_password)
        return result
    except Exception as exc:
        raise _http_error(exc) from exc


# ──────────────────────────────────────────────────────────────────────────────


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
            # tavily_api_key not accepted from frontend in MVP
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


# ── MVP: History endpoint DISABLED ─────────────────────────────────────────────
# Re-enable when history feature is included in a release.

# @app.get("/api/history")
# def history(authorization: str | None = Header(default=None, alias="Authorization")):
#     try:
#         user_id = _current_user_id(authorization)
#         return {"items": get_chat_history(user_id)}
#     except Exception as exc:
#         raise _http_error(exc) from exc

# ──────────────────────────────────────────────────────────────────────────────


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
        # MVP: History saving disabled
        # if result.get("success"):
        #     save_chat_history(user_id, request.query, result)
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
            # MVP: History saving disabled
            # if result.get("success"):
            #     save_chat_history(user_id, request.query, result)
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
