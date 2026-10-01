from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def ok(data: Any = None) -> dict:
    return {"status": "PASS", "data": data, "error": None}


def fail(code: str, message: str, data: Any = None) -> dict:
    return {"status": "FAIL", "data": data, "error": {"code": code, "message": message}}


def event(event_type: str, episode_id: str, module: str, payload: dict | None = None) -> dict:
    return {
        "type": event_type,
        "episode_id": episode_id,
        "timestamp": utc_now(),
        "module": module,
        "payload": payload or {},
    }
