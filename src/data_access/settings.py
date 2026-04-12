import re

from sqlalchemy import text
from src.data_access.db import load_sql_engine


def fetch_user_categories_sort_order_rows(user_id: str): #Main source of truth
    engine = load_sql_engine()
    sql = text("""
        SELECT category_id, category_name, is_active
        FROM user_categories
        WHERE user_id = :user_id
        ORDER BY sort_order, category_name
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"user_id": user_id}).mappings().all()

def fetch_user_metrics_for_settings(user_id: str):
    engine = load_sql_engine()
    sql = text("""
        SELECT
            md.metric_key,
            md.display_name,
            md.unit,
            md.value_type,
            md.sort_order,
            md.is_duration,
            md.subcategory,
            md.to_minutes_factor,
            md.activity,
            md.category_id,
            uc.category_name
        FROM metric_definitions md
        LEFT JOIN user_categories uc
          ON uc.category_id = md.category_id
         AND uc.user_id = md.user_id
        WHERE md.user_id = :user_id
        ORDER BY md.sort_order, md.display_name
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"user_id": user_id}).mappings().all()


def create_user_category_for_settings(user_id: str, category_name: str, is_active: bool) -> None:
    engine = load_sql_engine()
    sql = text(
        """
        INSERT INTO user_categories (user_id, category_name, is_active, sort_order)
        VALUES (
            :user_id,
            :category_name,
            :is_active,
            COALESCE(
                (SELECT MAX(sort_order) + 1 FROM user_categories WHERE user_id = :user_id),
                0
            )
        )
        ON CONFLICT (user_id, lower(btrim(category_name)))
        DO UPDATE
        SET is_active = EXCLUDED.is_active,
            updated_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "user_id": user_id,
                "category_name": category_name,
                "is_active": bool(is_active),
            },
        )


def _slugify_metric_key(display_name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", (display_name or "").strip().lower())
    key = key.strip("_")
    return key or "metric"


def _ensure_metric_key_unique(conn, user_id: str, base_key: str) -> str:
    probe = base_key
    suffix = 1
    while True:
        exists = conn.execute(
            text(
                """
                SELECT 1
                FROM metric_definitions
                WHERE user_id = :user_id
                  AND metric_key = :metric_key
                LIMIT 1
                """
            ),
            {"user_id": user_id, "metric_key": probe},
        ).scalar()
        if not exists:
            return probe
        suffix += 1
        probe = f"{base_key}_{suffix}"


def _normalize_category_fields(category_id, subcategory, activity):
    cid = None if category_id in (None, "") else int(category_id)
    sub = (subcategory or "").strip() or None
    act = (activity or "").strip() or None
    if cid is None:
        return None, None, None
    if sub is None:
        return cid, None, None
    return cid, sub, act


def _normalize_to_minutes_factor(value):
    txt = "" if value is None else str(value).strip()
    if txt == "":
        return None
    return float(txt)


def persist_category_settings_changes(
    *,
    user_id: str,
    category_edits: dict | None,
    category_drafts: list | None,
) -> None:
    category_edits = category_edits or {}
    category_drafts = category_drafts or []

    engine = load_sql_engine()
    with engine.begin() as conn:
        for category_id_str, row in category_edits.items():
            if not row.get("is_staged"):
                continue
            category_name = (row.get("category_name") or "").strip()
            if not category_name:
                continue
            conn.execute(
                text(
                    """
                    UPDATE user_categories
                    SET category_name = :category_name,
                        is_active = :is_active,
                        updated_at = now()
                    WHERE user_id = :user_id
                      AND category_id = :category_id
                    """
                ),
                {
                    "user_id": user_id,
                    "category_id": int(category_id_str),
                    "category_name": category_name,
                    "is_active": bool(row.get("is_active", True)),
                },
            )

        for row in category_drafts:
            if not row.get("is_staged"):
                continue
            category_name = (row.get("category_name") or "").strip()
            if not category_name:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO user_categories (user_id, category_name, is_active, sort_order)
                    VALUES (
                        :user_id,
                        :category_name,
                        :is_active,
                        COALESCE(
                            (SELECT MAX(sort_order) + 1 FROM user_categories WHERE user_id = :user_id),
                            0
                        )
                    )
                    ON CONFLICT (user_id, lower(btrim(category_name)))
                    DO UPDATE
                    SET is_active = EXCLUDED.is_active,
                        updated_at = now()
                    """
                ),
                {
                    "user_id": user_id,
                    "category_name": category_name,
                    "is_active": bool(row.get("is_active", True)),
                },
            )


def persist_metric_settings_changes(
    *,
    user_id: str,
    metric_edits: dict | None,
    metric_drafts: list | None,
    metric_order: list | None,
) -> None:
    metric_edits = metric_edits or {}
    metric_drafts = metric_drafts or []
    metric_order = metric_order or []

    engine = load_sql_engine()
    with engine.begin() as conn:
        current_metric_keys = [
            str(r["metric_key"])
            for r in conn.execute(
                text(
                    """
                    SELECT metric_key
                    FROM metric_definitions
                    WHERE user_id = :user_id
                    ORDER BY sort_order, display_name
                    """
                ),
                {"user_id": user_id},
            ).mappings()
        ]
        ordered_existing = [k for k in metric_order if k in current_metric_keys]
        ordered_existing.extend([k for k in current_metric_keys if k not in ordered_existing])

        for idx, metric_key in enumerate(ordered_existing):
            conn.execute(
                text(
                    """
                    UPDATE metric_definitions
                    SET sort_order = :sort_order
                    WHERE user_id = :user_id
                      AND metric_key = :metric_key
                    """
                ),
                {"user_id": user_id, "metric_key": metric_key, "sort_order": idx},
            )

        for metric_key, row in metric_edits.items():
            if not row.get("is_staged"):
                continue
            display_name = (row.get("display_name") or "").strip()
            unit = (row.get("unit") or "").strip()
            if not display_name:
                continue

            category_id, subcategory, activity = _normalize_category_fields(
                row.get("category_id"),
                row.get("subcategory"),
                row.get("activity"),
            )

            conn.execute(
                text(
                    """
                    UPDATE metric_definitions
                    SET display_name = :display_name,
                        unit = :unit,
                        is_duration = :is_duration,
                        category_id = :category_id,
                        subcategory = :subcategory,
                        activity = :activity,
                        to_minutes_factor = :to_minutes_factor
                    WHERE user_id = :user_id
                      AND metric_key = :metric_key
                    """
                ),
                {
                    "user_id": user_id,
                    "metric_key": metric_key,
                    "display_name": display_name,
                    "unit": unit,
                    "is_duration": bool(row.get("is_duration", False)),
                    "category_id": category_id,
                    "subcategory": subcategory,
                    "activity": activity,
                    "to_minutes_factor": _normalize_to_minutes_factor(row.get("to_minutes_factor")),
                },
            )

        next_sort = len(ordered_existing)
        for row in metric_drafts:
            if not row.get("is_staged"):
                continue
            display_name = (row.get("display_name") or "").strip()
            unit = (row.get("unit") or "").strip()
            if not display_name:
                continue

            category_id, subcategory, activity = _normalize_category_fields(
                row.get("category_id"),
                row.get("subcategory"),
                row.get("activity"),
            )

            base_key = _slugify_metric_key(display_name)
            metric_key = _ensure_metric_key_unique(conn, user_id, base_key)

            conn.execute(
                text(
                    """
                    INSERT INTO metric_definitions (
                        user_id,
                        metric_key,
                        display_name,
                        unit,
                        value_type,
                        sort_order,
                        is_duration,
                        category_id,
                        subcategory,
                        activity,
                        to_minutes_factor
                    )
                    VALUES (
                        :user_id,
                        :metric_key,
                        :display_name,
                        :unit,
                        :value_type,
                        :sort_order,
                        :is_duration,
                        :category_id,
                        :subcategory,
                        :activity,
                        :to_minutes_factor
                    )
                    """
                ),
                {
                    "user_id": user_id,
                    "metric_key": metric_key,
                    "display_name": display_name,
                    "unit": unit,
                    "value_type": (row.get("value_type") or "double"),
                    "sort_order": next_sort,
                    "is_duration": bool(row.get("is_duration", False)),
                    "category_id": category_id,
                    "subcategory": subcategory,
                    "activity": activity,
                    "to_minutes_factor": _normalize_to_minutes_factor(row.get("to_minutes_factor")),
                },
            )
            next_sort += 1


def persist_settings_changes(
    *,
    user_id: str,
    category_edits: dict | None,
    category_drafts: list | None,
    metric_edits: dict | None,
    metric_drafts: list | None,
    metric_order: list | None,
) -> None:
    """
    Backward-compatible wrapper that persists both sections.
    """
    persist_category_settings_changes(
        user_id=user_id,
        category_edits=category_edits,
        category_drafts=category_drafts,
    )
    persist_metric_settings_changes(
        user_id=user_id,
        metric_edits=metric_edits,
        metric_drafts=metric_drafts,
        metric_order=metric_order,
    )
