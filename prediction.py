from __future__ import annotations
from datetime import datetime, timedelta, timezone
from protocol import new_id, utc_now


def create_presence_prediction(episode_id: str, entity_key: str, current_value: str,
                               horizon_seconds: float, rule: str) -> dict:
    created = datetime.now(timezone.utc)
    due = created + timedelta(seconds=float(horizon_seconds))
    return {
        "prediction_id": new_id("pred"),
        "episode_id": episode_id,
        "entity_key": entity_key,
        "property": "presence",
        "predicted_value": current_value,
        "confidence": 0.70,
        "rule": rule,
        "horizon_seconds": float(horizon_seconds),
        "created_at": created.isoformat(timespec="milliseconds"),
        "due_at": due.isoformat(timespec="milliseconds"),
        "status": "pending",
    }
