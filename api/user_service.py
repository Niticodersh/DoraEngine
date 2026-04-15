"""Authentication, profile, plans, and OTP verification services.

MVP NOTE: Chat history is intentionally disabled for this release.
         All history-related functions are commented out below.
         Re-enable by uncommenting when history feature is planned.
"""
from __future__ import annotations

import hmac
import random
import secrets
import string
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from utils.db import get_db
from utils.email_sender import send_password_reset_email
from utils.security import create_token, hash_password, verify_password


PLANS = [
    {
        "code": "free",
        "name": "Free",
        "price_inr": 0,
        "billing": "forever",
        "requires_user_api_key": True,
        "watermark_exports": True,
    },
    {
        "code": "standard_daily",
        "name": "Standard Daily",
        "price_inr": 39,
        "billing": "day",
        "requires_user_api_key": False,
        "watermark_exports": False,
    },
    {
        "code": "standard_monthly",
        "name": "Standard Monthly",
        "price_inr": 299,
        "billing": "month",
        "requires_user_api_key": False,
        "watermark_exports": False,
    },
]

OTP_EXPIRY_MINUTES = 10


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _users():
    return get_db().users


def _pending_signups():
    return get_db().pending_signups


# ── MVP: Chat history collection disabled ──────────────────────────────────────
# def _history():
#     return get_db().chat_history
# ──────────────────────────────────────────────────────────────────────────────


def _serialize_user(doc: dict) -> dict:
    def _iso_utc(dt):
        if not dt: return None
        return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).isoformat()

    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "mobile": doc["mobile"],
        "plan_code": doc.get("plan_code", "free"),
        "is_verified": bool(doc.get("is_verified", False)),
        "created_at": _iso_utc(doc.get("created_at")),
        "plan_expiry_date": _iso_utc(doc.get("plan_expiry_date")),
        "has_groq_api_key": bool(doc.get("groq_api_key")),
        # MVP: Tavily key hidden from serialized user — backend still reads it internally
        # "has_tavily_api_key": bool(doc.get("tavily_api_key")),
    }


def get_plans() -> list[dict]:
    return PLANS


def get_plan(code: str) -> dict:
    for plan in PLANS:
        if plan["code"] == code:
            return plan
    raise ValueError("Unknown plan")


def create_user(email: str, password: str, mobile: str, is_verified: bool = False) -> dict:
    email = email.strip().lower()
    mobile = "".join(char for char in mobile if char.isdigit() or char == "+").strip()

    if not email or not password or not mobile:
        raise ValueError("Email, password, and mobile number are required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    doc = {
        "email": email,
        "mobile": mobile,
        "password_hash": hash_password(password),
        "plan_code": "free",
        "is_verified": is_verified,    # Email may already be verified via Firebase link
        "groq_api_key": "",
        "tavily_api_key": "",          # Internal use only — not exposed to frontend
        "otp_code": "",
        "otp_expiry": None,
        "created_at": _utcnow(),
    }

    try:
        result = _users().insert_one(doc)
    except Exception as exc:
        message = str(exc)
        if "mobile" in message.lower():
            raise ValueError("An account with this mobile number already exists") from exc
        if "email" in message.lower():
            raise ValueError("An account with this email already exists") from exc
        raise

    doc["_id"] = result.inserted_id
    return _serialize_user(doc)


def initiate_signup_with_otp(email: str, password: str, mobile: str) -> dict:
    email = email.strip().lower()
    mobile = "".join(char for char in mobile if char.isdigit() or char == "+").strip()

    if not email or not password or not mobile:
        raise ValueError("Email, password, and mobile number are required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    # Ensure user does not already exist
    if _users().find_one({"email": email}):
        raise ValueError("An account with this email already exists")
    if _users().find_one({"mobile": mobile}):
        raise ValueError("An account with this mobile number already exists")

    otp = "".join(random.choices(string.digits, k=6))
    expiry = _utcnow() + timedelta(minutes=10) # 10 minute expiry

    from utils.email_sender import send_signup_otp_email
    email_sent = send_signup_otp_email(email, otp)

    payload = {
        "email": email,
        "mobile": mobile,
        "password_hash": hash_password(password),
        "otp_code": otp,
        "otp_expiry": expiry,
        "created_at": _utcnow()
    }
    
    # Upsert the pending signup draft
    _pending_signups().update_one({"email": email}, {"$set": payload}, upsert=True)

    if email_sent:
        return {"message": "OTP sent to email address successfully."}
    else:
        return {"message": "OTP recorded locally.", "dev_otp": otp}


def complete_signup_with_otp(email: str, otp_code: str) -> dict:
    email = email.strip().lower()
    pending = _pending_signups().find_one({"email": email})
    
    if not pending:
        raise ValueError("No pending sign up found. Please start over.")
        
    expiry = pending.get("otp_expiry")
    if expiry and _utcnow() > (expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry):
        raise ValueError("OTP has expired. Please sign up again.")
        
    if pending.get("otp_code") != otp_code.strip():
        raise ValueError("Invalid OTP. Please check your email and try again.")
        
    # Validation passed. Transfer them to the main `users` dataset securely.
    try:
        user = create_user(
            email=pending["email"],
            password="", # Irrelevant, we'll manually inject their preserved hash
            mobile=pending["mobile"],
            is_verified=True
        )
    except Exception as e:
        # Overwrite the hash since create_user expects raw text but we only cached the hash
        pass
        
    # The better way: just create it directly here to bypass double-hashing
    doc = {
        "email": pending["email"],
        "mobile": pending["mobile"],
        "password_hash": pending["password_hash"], # Use the original hash they created earlier
        "plan_code": "free",
        "is_verified": True, 
        "groq_api_key": "",
        "tavily_api_key": "",
        "otp_code": "",
        "otp_expiry": None,
        "created_at": _utcnow(),
    }
    try:
        result = _users().insert_one(doc)
    except Exception as exc:
        raise ValueError("Failed to finalize account. User may already exist.") from exc
    
    _pending_signups().delete_one({"email": email})
    doc["_id"] = result.inserted_id
    return _serialize_user(doc)


def authenticate_user(email: str, password: str) -> dict:
    user = _users().find_one({"email": email.strip().lower()})
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise ValueError("Invalid email or password")
    return _serialize_user(user)


def create_auth_response(user: dict) -> dict:
    token = create_token({"sub": user["id"], "email": user["email"]})
    return {"token": token, "user": user}


def get_user_by_id(user_id: str) -> dict:
    try:
        doc = _users().find_one({"_id": ObjectId(user_id)})
    except Exception as exc:
        raise ValueError("Invalid user id") from exc
    if not doc:
        raise ValueError("User not found")
        
    # Lazy Evaluation: Automatically downgrade expired subscription plans
    expiry = doc.get("plan_expiry_date")
    if expiry and _utcnow() > (expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry):
        _users().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"plan_code": "free", "plan_expiry_date": None}}
        )
        doc["plan_code"] = "free"
        doc["plan_expiry_date"] = None
        
    return doc


def get_public_user(user_id: str) -> dict:
    return _serialize_user(get_user_by_id(user_id))


def update_user_profile(user_id: str, groq_api_key: str | None = None) -> dict:
    """Update editable profile fields. Tavily key is backend-only; not updatable via this endpoint."""
    updates = {}
    if groq_api_key is not None:
        updates["groq_api_key"] = groq_api_key.strip()
    if updates:
        _users().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    return get_public_user(user_id)


def update_plan(user_id: str, plan_code: str) -> dict:
    get_plan(plan_code)
    
    # Calculate expiry based on plan
    plan_expiry_date = None
    if plan_code == "standard_daily":
        plan_expiry_date = _utcnow() + timedelta(days=1)
    elif plan_code == "standard_monthly":
        plan_expiry_date = _utcnow() + timedelta(days=30)
        
    _users().update_one(
        {"_id": ObjectId(user_id)}, 
        {"$set": {"plan_code": plan_code, "plan_expiry_date": plan_expiry_date}}
    )
    return get_public_user(user_id)


def get_user_runtime_config(user_id: str) -> dict:
    user = get_user_by_id(user_id)
    plan = get_plan(user.get("plan_code", "free"))

    return {
        "user": _serialize_user(user),
        "plan": plan,
        "groq_api_key": user.get("groq_api_key", ""),
        "tavily_api_key": user.get("tavily_api_key", ""),   # Internal — loaded from env/admin
        "requires_user_api_key": plan["requires_user_api_key"],
        "watermark_exports": plan["watermark_exports"],
    }


# ── OTP Verification ───────────────────────────────────────────────────────────

def generate_and_send_otp(user_id: str) -> dict:
    """
    Generates a 6-digit OTP, stores it in the user document with expiry,
    and returns it for MVP development purposes.

    TODO (Production): Replace return of raw OTP with actual delivery:
        - SMS: Integrate Twilio / MSG91 / AWS SNS to user.mobile
        - Email: Integrate SendGrid / SES / SMTP to user.email
        - Remove 'dev_otp' from the response payload in production.
    """
    otp = "".join(random.choices(string.digits, k=6))
    expiry = _utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    _users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"otp_code": otp, "otp_expiry": expiry}},
    )

    # TODO: Remove dev_otp from production response
    return {"message": f"OTP sent to registered mobile and email (expires in {OTP_EXPIRY_MINUTES}m)", "dev_otp": otp}


def verify_user_otp(user_id: str, otp_code: str) -> dict:
    """
    Validates the OTP against stored value and expiry.
    Marks the user as verified and clears the OTP on success.
    """
    user = get_user_by_id(user_id)
    stored_otp = user.get("otp_code", "")
    expiry = user.get("otp_expiry")

    if not stored_otp:
        raise ValueError("No OTP was generated. Please request a new one.")

    if expiry:
        if _utcnow() > expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry:
            raise ValueError("OTP has expired. Please request a new one.")

    if stored_otp != otp_code.strip():
        raise ValueError("Invalid OTP. Please check and try again.")

    # Mark verified, clear OTP
    _users().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_verified": True, "otp_code": "", "otp_expiry": None}},
    )
    return get_public_user(user_id)


# ── Password Reset ───────────────────────────────────────────────────────────────

PASSWORD_RESET_EXPIRY_MINUTES = 30


def generate_password_reset_token(email: str, app_base_url: str = "") -> dict:
    """
    Generates a secure reset token, stores it on the user doc, and sends a
    password-reset email via Gmail SMTP.

    If GMAIL_USER + GMAIL_APP_PASSWORD are set in .env, a real email is sent
    and 'dev_reset_url' is NOT included in the response.

    If those env vars are absent (local dev), the reset URL is returned as
    'dev_reset_url' so you can click it directly from the frontend banner.
    """
    user = _users().find_one({"email": email.strip().lower()})
    # Always respond the same way to avoid email enumeration
    generic = {"message": "If an account with that email exists, a reset link has been sent."}
    if not user:
        return generic

    token = secrets.token_urlsafe(32)
    expiry = _utcnow() + timedelta(minutes=PASSWORD_RESET_EXPIRY_MINUTES)
    _users().update_one(
        {"_id": user["_id"]},
        {"$set": {"reset_token": token, "reset_token_expiry": expiry}},
    )

    query_string = f"?reset_email={email.strip().lower()}&reset_token={token}"
    reset_url = f"{app_base_url.rstrip('/')}{query_string}"

    # Try sending a real email; fail loudly if creds are missing (Production behavior)
    email_sent = send_password_reset_email(email.strip().lower(), reset_url)

    if not email_sent:
        raise ValueError("Server configuration error: Email delivery is not configured.")

    return generic


def reset_password_with_token(email: str, token: str, new_password: str) -> dict:
    """
    Validates the reset token and updates the user's password hash.
    Clears the token on success to prevent replay.
    """
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    user = _users().find_one({"email": email.strip().lower()})
    if not user:
        raise ValueError("Invalid or expired reset link. Please request a new one.")

    stored_token = user.get("reset_token", "")
    expiry = user.get("reset_token_expiry")

    if not stored_token or not secrets.compare_digest(stored_token, token.strip()):
        raise ValueError("Invalid or expired reset link. Please request a new one.")

    if expiry:
        exp_aware = expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry
        if _utcnow() > exp_aware:
            raise ValueError("Reset link has expired. Please request a new one.")

    _users().update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": hash_password(new_password),
            "reset_token": "",
            "reset_token_expiry": None,
        }},
    )
    return {"message": "Password reset successfully."}


# ── MVP: Chat History — DISABLED ───────────────────────────────────────────────
# These functions are preserved for future re-enablement.
# Do NOT delete — re-enable when history feature is included in a release.

# def save_chat_history(user_id: str, query: str, result: dict) -> str:
#     answer = ((result.get("final_answer") or {}).get("summary") or "")[:500]
#     doc = {
#         "user_id": user_id,
#         "query": query,
#         "answer_summary": answer,
#         "result": result,
#         "created_at": _utcnow(),
#     }
#     inserted = _history().insert_one(doc)
#     return str(inserted.inserted_id)


# def get_chat_history(user_id: str) -> list[dict]:
#     items = _history().find({"user_id": user_id}).sort("created_at", -1)
#     history = []
#     for item in items:
#         history.append(
#             {
#                 "id": str(item["_id"]),
#                 "query": item.get("query", ""),
#                 "answer_summary": item.get("answer_summary", ""),
#                 "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
#                 "result": item.get("result"),
#             }
#         )
#     return history
# ──────────────────────────────────────────────────────────────────────────────
