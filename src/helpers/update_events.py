from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_update_event(
    *,
    event_type: str,
    entity: str,
    user_id: str | None = None,
    date: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if date is not None:
        payload["date"] = date
    if details:
        payload["details"] = details

    return {
        "event_type": event_type,
        "entity": entity,
        "user_id": user_id,
        "payload": payload,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
