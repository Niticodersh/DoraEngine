"""Authentication, profile, plans, and chat history services."""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from utils.db import get_db
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _users():
    return get_db().users


def _history():
    return get_db().chat_history


def _serialize_user(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "mobile": doc["mobile"],
        "plan_code": doc.get("plan_code", "free"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "has_groq_api_key": bool(doc.get("groq_api_key")),
        "has_tavily_api_key": bool(doc.get("tavily_api_key")),
    }


def get_plans() -> list[dict]:
    return PLANS


def get_plan(code: str) -> dict:
    for plan in PLANS:
        if plan["code"] == code:
            return plan
    raise ValueError("Unknown plan")


def create_user(email: str, password: str, mobile: str) -> dict:
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
        "groq_api_key": "",
        "tavily_api_key": "",
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
    return doc


def get_public_user(user_id: str) -> dict:
    return _serialize_user(get_user_by_id(user_id))


def update_user_profile(user_id: str, groq_api_key: str | None = None, tavily_api_key: str | None = None) -> dict:
    updates = {}
    if groq_api_key is not None:
        updates["groq_api_key"] = groq_api_key.strip()
    if tavily_api_key is not None:
        updates["tavily_api_key"] = tavily_api_key.strip()
    if updates:
        _users().update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    return get_public_user(user_id)


def update_plan(user_id: str, plan_code: str) -> dict:
    get_plan(plan_code)
    _users().update_one({"_id": ObjectId(user_id)}, {"$set": {"plan_code": plan_code}})
    return get_public_user(user_id)


def get_user_runtime_config(user_id: str) -> dict:
    user = get_user_by_id(user_id)
    plan = get_plan(user.get("plan_code", "free"))

    return {
        "user": _serialize_user(user),
        "plan": plan,
        "groq_api_key": user.get("groq_api_key", ""),
        "tavily_api_key": user.get("tavily_api_key", ""),
        "requires_user_api_key": plan["requires_user_api_key"],
        "watermark_exports": plan["watermark_exports"],
    }


def save_chat_history(user_id: str, query: str, result: dict) -> str:
    answer = ((result.get("final_answer") or {}).get("summary") or "")[:500]
    doc = {
        "user_id": user_id,
        "query": query,
        "answer_summary": answer,
        "result": result,
        "created_at": _utcnow(),
    }
    inserted = _history().insert_one(doc)
    return str(inserted.inserted_id)


def get_chat_history(user_id: str) -> list[dict]:
    items = _history().find({"user_id": user_id}).sort("created_at", -1)
    history = []
    for item in items:
        history.append(
            {
                "id": str(item["_id"]),
                "query": item.get("query", ""),
                "answer_summary": item.get("answer_summary", ""),
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
                "result": item.get("result"),
            }
        )
    return history
