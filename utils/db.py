"""MongoDB access helpers."""
from __future__ import annotations

import ssl

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from utils.config import get_secret

_client: MongoClient | None = None


def get_db() -> Database:
    global _client
    uri = get_secret("MONGODB_URI")
    db_name = get_secret("MONGODB_DB_NAME", "doraengine")
    if not uri:
        raise RuntimeError("MONGODB_URI not set")

    if _client is None:
        _client = MongoClient(
            uri,
            tls=True,
            tlsAllowInvalidCertificates=True,   # Dev-only: bypasses cert validation
            serverSelectionTimeoutMS=15000,
        )
        database = _client[db_name]
        database.users.create_index([("mobile", ASCENDING)], unique=True)
        database.users.create_index([("email", ASCENDING)], unique=True)
        database.chat_history.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)])
        return database

    return _client[db_name]
