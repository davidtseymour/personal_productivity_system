from datetime import date as Date, datetime, timezone
from typing import Any

def build_update_event(
    *,
    event_type: str,
    entity: str,
    user_id: str | None = None,
    date: Date | datetime | str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(date, datetime):
        date_str = date.date().isoformat()
    elif isinstance(date, Date):
        date_str = date.isoformat()
    else:
        date_str = date  # str or None

    payload: dict[str, Any] = {}
    if details is not None:
        payload["details"] = details

    return {
        "event_type": event_type,
        "entity": entity,
        "user_id": user_id,
        "date": date_str,  # always present, maybe None
        "payload": payload,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
