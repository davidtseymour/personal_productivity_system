from datetime import date, datetime, timezone
import re
from typing import Any, Literal

from sqlalchemy import text

from src.data_access.db import load_sql_engine

GoalHorizon = Literal["WEEK", "MONTH", "QTR"]
GoalItemStatus = Literal["ACTIVE", "COMPLETED", "DROPPED"]
GoalProgressMode = Literal["MANUAL", "AUTO_STATUS", "AUTO_TIME"]
GoalCalcSource = Literal["TASKS", "METRICS", "TASKS_AND_METRICS"]
GoalTargetScope = Literal["PERIOD", "DAY"]
GoalTargetOperator = Literal["GTE", "LTE"]


def _normalize_progress_mode(value: object) -> GoalProgressMode:
    mode = str(value or "MANUAL").strip().upper()
    if mode in {"MANUAL", "AUTO_STATUS", "AUTO_TIME"}:
        return mode  # type: ignore[return-value]
    return "MANUAL"


def _normalize_calc_source(value: object) -> GoalCalcSource:
    source = str(value or "TASKS").strip().upper()
    if source in {"TASKS", "METRICS", "TASKS_AND_METRICS"}:
        return source  # type: ignore[return-value]
    return "TASKS"


def _normalize_target_scope(value: object) -> GoalTargetScope:
    scope = str(value or "PERIOD").strip().upper()
    if scope in {"PERIOD", "DAY"}:
        return scope  # type: ignore[return-value]
    return "PERIOD"


def _normalize_target_operator(value: object) -> GoalTargetOperator:
    operator = str(value or "GTE").strip().upper()
    if operator in {"GTE", "LTE"}:
        return operator  # type: ignore[return-value]
    return "GTE"


def _table_exists(conn: Any, table_name: str) -> bool:
    sql = """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = :table_name
        LIMIT 1;
    """
    return conn.execute(text(sql), {"table_name": table_name}).scalar() is not None


def _column_exists(conn: Any, table_name: str, column_name: str) -> bool:
    sql = """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = :table_name
          AND column_name = :column_name
        LIMIT 1;
    """
    return conn.execute(
        text(sql),
        {"table_name": table_name, "column_name": column_name},
    ).scalar() is not None


def _goal_set_items_has_user_id(conn: Any) -> bool:
    return _column_exists(conn, "goal_set_items", "user_id")


def _goal_items_table_exists(conn: Any) -> bool:
    return _table_exists(conn, "goal_items")


def _goal_items_column_set(conn: Any) -> set[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'goal_items';
    """
    rows = conn.execute(text(sql)).mappings().all()
    return {str(row["column_name"]) for row in rows}


def _ensure_user_goal_preferences_table(conn: Any) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_goal_preferences (
                user_id UUID PRIMARY KEY
                    REFERENCES users(user_id) ON DELETE CASCADE,
                auto_calculate_progress BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
    )


def _parse_legacy_goal_lines(detail_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in (detail_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        status: GoalItemStatus = "ACTIVE"
        progress_percent: float | None = None

        checkbox_match = re.match(r"^\s*(?:[-*]\s*)?\[(x|X|\s)\]\s*(.+)\s*$", line)
        if checkbox_match:
            mark = checkbox_match.group(1).strip().lower()
            title = checkbox_match.group(2).strip()
            if mark == "x":
                status = "COMPLETED"
                progress_percent = 100.0
            else:
                status = "ACTIVE"
                progress_percent = 0.0
        else:
            title = re.sub(r"^\s*[-*]\s*", "", line).strip()

        if not title:
            continue

        rows.append(
            {
                "title": title,
                "status": status,
                "progress_percent": progress_percent,
            }
        )
    return rows


def _goal_items_to_legacy_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    lines: list[str] = []
    for row in rows:
        status = str(row.get("status") or "ACTIVE")
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        prefix = "- [x]" if status == "COMPLETED" else "- [ ]"
        lines.append(f"{prefix} {title}")

    return "\n".join(lines)

# ----- GOAL THEMES -----

def get_or_create_goal_theme(name: str, user_id: str) -> tuple[int, bool]:
    """
    Insert a goal theme if it doesn't exist (active), otherwise return the existing theme_id.

    Returns:
        (goal_theme_id, created_new)
    """

    user_id = str(user_id)
    name_clean = (name or "").strip()
    if not name_clean:
        raise ValueError("Theme name cannot be empty.")

    sql = """
    WITH ins AS (
      INSERT INTO goal_themes (user_id, name)
      VALUES (:user_id, :name)
      ON CONFLICT (user_id, name_norm) WHERE archived_at IS NULL
      DO NOTHING
      RETURNING goal_theme_id
    )
    SELECT goal_theme_id, TRUE AS created_new FROM ins
    UNION ALL
    SELECT goal_theme_id, FALSE AS created_new
    FROM goal_themes
    WHERE user_id = :user_id
      AND name_norm = lower(trim(:name))
      AND archived_at IS NULL
    LIMIT 1;
    """

    engine = load_sql_engine()
    with engine.begin() as conn:
        row = conn.execute(text(sql), {"user_id": user_id, "name": name_clean}).one()

    return int(row.goal_theme_id), bool(row.created_new)

def get_goals_themes(user_id: str) -> list[dict[str, Any]]:
    """
       Returns dropdown options for goal themes for a given user.
       Each option is: {"label": <theme name>, "value": <goal_theme_id>}
       """
    if not user_id:
        return []
    user_id = str(user_id)

    engine = load_sql_engine()  # use your existing helper

    sql = """
          SELECT goal_theme_id, name
          FROM goal_themes
          WHERE user_id = :user_id
            AND archived_at IS NULL
          ORDER BY lower(name), goal_theme_id; 
          """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"user_id": user_id}).mappings().all()

    return [{"label": r["name"], "value": int(r["goal_theme_id"])} for r in rows]


def get_goals_auto_calculate_enabled(user_id: str) -> bool:
    if not user_id:
        return False

    engine = load_sql_engine()
    with engine.begin() as conn:
        _ensure_user_goal_preferences_table(conn)
        row = conn.execute(
            text(
                """
                SELECT auto_calculate_progress
                FROM user_goal_preferences
                WHERE user_id = :user_id
                LIMIT 1;
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().first()

    if row is None:
        return False
    return bool(row["auto_calculate_progress"])


def set_goals_auto_calculate_enabled(user_id: str, enabled: bool) -> bool:
    if not user_id:
        return False

    enabled_bool = bool(enabled)
    engine = load_sql_engine()
    with engine.begin() as conn:
        _ensure_user_goal_preferences_table(conn)
        conn.execute(
            text(
                """
                INSERT INTO user_goal_preferences (user_id, auto_calculate_progress)
                VALUES (:user_id, :enabled)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    auto_calculate_progress = EXCLUDED.auto_calculate_progress,
                    updated_at = now();
                """
            ),
            {"user_id": str(user_id), "enabled": enabled_bool},
        )
    return enabled_bool






# ----- GOAL SETS -----

def get_goal_set_id(user_id: str, horizon: GoalHorizon, period_start: date) -> int | None:
    sql = """
        SELECT goal_set_id
        FROM goal_sets
        WHERE user_id = :user_id
          AND horizon = :horizon
          AND period_start = :period_start
        LIMIT 1;
    """
    engine = load_sql_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(sql),
            {"user_id": user_id, "horizon": horizon, "period_start": period_start},
        ).mappings().first()

    return int(row["goal_set_id"]) if row else None

def create_and_get_goal_set_id(
    user_id: str,
    horizon: GoalHorizon,
    period_start: date,
) -> int:
    sql = """
        INSERT INTO goal_sets (user_id, horizon, period_start)
        VALUES (:user_id, :horizon, :period_start)
        ON CONFLICT (user_id, horizon, period_start)
        DO UPDATE SET period_start = EXCLUDED.period_start
        RETURNING goal_set_id;
    """
    engine = load_sql_engine()
    with engine.begin() as conn:
        goal_set_id = conn.execute(
            text(sql),
            {"user_id": user_id, "horizon": horizon, "period_start": period_start},
        ).scalar_one()
    return int(goal_set_id)


# ----- GOAL SET ITEMS -----

def get_goal_set_item_text(
    *,
    user_id: str,
    goal_set_id: int | None,
    goal_theme_id: int | None,
) -> str | None:
    """
    Returns the latest revision text for this (goal_set_id, goal_theme_id).
    Returns:
      - None when no row exists
      - "" when latest row exists and is intentionally empty
      - non-empty text otherwise
    """
    if goal_set_id is None or goal_theme_id is None:
        return None

    engine = load_sql_engine()
    with engine.connect() as conn:
        if _goal_set_items_has_user_id(conn):
            sql = """
                SELECT detail_text
                FROM goal_set_items
                WHERE user_id = :user_id
                  AND goal_set_id = :goal_set_id
                  AND goal_theme_id = :goal_theme_id
                ORDER BY revision_no DESC
                LIMIT 1;
            """
            params = {
                "user_id": user_id,
                "goal_set_id": int(goal_set_id),
                "goal_theme_id": int(goal_theme_id),
            }
        else:
            sql = """
                SELECT detail_text
                FROM goal_set_items
                WHERE goal_set_id = :goal_set_id
                  AND goal_theme_id = :goal_theme_id
                ORDER BY revision_no DESC
                LIMIT 1;
            """
            params = {
                "goal_set_id": int(goal_set_id),
                "goal_theme_id": int(goal_theme_id),
            }

        row = conn.execute(
            text(sql),
            params,
        ).mappings().first()

    if row is None:
        return None
    return str(row["detail_text"] or "")


def get_goal_items_fallback_text(
    *,
    user_id: str,
    goal_set_id: int | None,
    goal_theme_id: int | None,
) -> str:
    """
    Build display text from active structured goal items.
    Used as fallback when no legacy blob exists.
    """
    if goal_set_id is None or goal_theme_id is None:
        return ""

    sql = """
        SELECT title, status, order_index, goal_item_id
        FROM goal_items
        WHERE user_id = :user_id
          AND goal_set_id = :goal_set_id
          AND goal_theme_id = :goal_theme_id
          AND status <> 'DROPPED'
          AND archived_at IS NULL
        ORDER BY order_index, goal_item_id;
    """

    engine = load_sql_engine()
    with engine.connect() as conn:
        if not _goal_items_table_exists(conn):
            return ""
        rows = conn.execute(
            text(sql),
            {
                "user_id": user_id,
                "goal_set_id": int(goal_set_id),
                "goal_theme_id": int(goal_theme_id),
            },
        ).mappings().all()

    return _goal_items_to_legacy_text(list(rows))


def _save_goal_set_item_text_with_conn(
    conn: Any,
    *,
    user_id: str,
    goal_set_id: int,
    goal_theme_id: int,
    detail_text: str,
) -> bool:
    detail_text = detail_text or ""

    if _goal_set_items_has_user_id(conn):
        sql = """
        WITH cur AS (
          SELECT detail_text, revision_no
          FROM goal_set_items
          WHERE user_id = :user_id
            AND goal_set_id = :goal_set_id
            AND goal_theme_id = :goal_theme_id
          ORDER BY revision_no DESC
          LIMIT 1
        ),
        next_rev AS (
          SELECT COALESCE((SELECT revision_no FROM cur), 0) + 1 AS revision_no
        )
        INSERT INTO goal_set_items (goal_set_id, goal_theme_id, user_id, revision_no, detail_text)
        SELECT
          :goal_set_id,
          :goal_theme_id,
          :user_id,
          (SELECT revision_no FROM next_rev),
          :detail_text
        WHERE (SELECT detail_text FROM cur) IS DISTINCT FROM :detail_text
        ON CONFLICT DO NOTHING
        RETURNING 1;
        """
        params = {
            "user_id": user_id,
            "goal_set_id": int(goal_set_id),
            "goal_theme_id": int(goal_theme_id),
            "detail_text": detail_text,
        }
    else:
        sql = """
        WITH cur AS (
          SELECT detail_text, revision_no
          FROM goal_set_items
          WHERE goal_set_id = :goal_set_id
            AND goal_theme_id = :goal_theme_id
          ORDER BY revision_no DESC
          LIMIT 1
        ),
        next_rev AS (
          SELECT COALESCE((SELECT revision_no FROM cur), 0) + 1 AS revision_no
        )
        INSERT INTO goal_set_items (goal_set_id, goal_theme_id, revision_no, detail_text)
        SELECT
          :goal_set_id,
          :goal_theme_id,
          (SELECT revision_no FROM next_rev),
          :detail_text
        WHERE (SELECT detail_text FROM cur) IS DISTINCT FROM :detail_text
        ON CONFLICT DO NOTHING
        RETURNING 1;
        """
        params = {
            "goal_set_id": int(goal_set_id),
            "goal_theme_id": int(goal_theme_id),
            "detail_text": detail_text,
        }

    inserted = conn.execute(text(sql), params).scalar()
    return bool(inserted)


def save_goal_set_item_text(
    *,
    user_id: str,
    goal_set_id: int,
    goal_theme_id: int,
    detail_text: str,
) -> bool:
    """
    Inserts a new revision row ONLY if the text changed.
    Returns True if inserted, False if no change.
    """
    engine = load_sql_engine()
    with engine.begin() as conn:
        return _save_goal_set_item_text_with_conn(
            conn,
            user_id=user_id,
            goal_set_id=goal_set_id,
            goal_theme_id=goal_theme_id,
            detail_text=detail_text,
        )


def _replace_legacy_goal_items_from_text_with_conn(
    conn: Any,
    *,
    user_id: str,
    goal_set_id: int,
    goal_theme_id: int,
    detail_text: str,
) -> bool:
    """
    Keep structured goal_items in sync with the legacy textarea representation.
    This is intentionally full-replace for rows created from legacy textarea content.
    Returns True if rows were updated.
    """
    if not _goal_items_table_exists(conn):
        return False

    parsed = _parse_legacy_goal_lines(detail_text or "")

    select_sql = """
        SELECT title, status, progress_percent, order_index
        FROM goal_items
        WHERE user_id = :user_id
          AND goal_set_id = :goal_set_id
          AND goal_theme_id = :goal_theme_id
          AND source = 'LEGACY_TEXTAREA'
          AND archived_at IS NULL
        ORDER BY order_index, goal_item_id;
    """

    archive_sql = """
        UPDATE goal_items
        SET archived_at = now()
        WHERE user_id = :user_id
          AND goal_set_id = :goal_set_id
          AND goal_theme_id = :goal_theme_id
          AND source = 'LEGACY_TEXTAREA'
          AND archived_at IS NULL;
    """

    insert_sql = """
        INSERT INTO goal_items (
            user_id,
            goal_set_id,
            goal_theme_id,
            title,
            notes,
            status,
            progress_percent,
            weight,
            source,
            order_index,
            completed_at,
            dropped_at
        )
        VALUES (
            :user_id,
            :goal_set_id,
            :goal_theme_id,
            :title,
            '',
            :status,
            :progress_percent,
            1,
            'LEGACY_TEXTAREA',
            :order_index,
            :completed_at,
            :dropped_at
        );
    """

    desired = [
        (
            row["title"],
            row["status"],
            None if row["progress_percent"] is None else float(row["progress_percent"]),
            idx,
        )
        for idx, row in enumerate(parsed)
    ]

    existing_rows = conn.execute(
        text(select_sql),
        {
            "user_id": user_id,
            "goal_set_id": int(goal_set_id),
            "goal_theme_id": int(goal_theme_id),
        },
    ).mappings().all()

    existing = [
        (
            str(row["title"]),
            str(row["status"]),
            None if row["progress_percent"] is None else float(row["progress_percent"]),
            int(row["order_index"]),
        )
        for row in existing_rows
    ]

    if existing == desired:
        return False

    conn.execute(
        text(archive_sql),
        {
            "user_id": user_id,
            "goal_set_id": int(goal_set_id),
            "goal_theme_id": int(goal_theme_id),
        },
    )

    insert_rows = []
    now_utc = datetime.now(timezone.utc)
    for idx, row in enumerate(parsed):
        status = str(row["status"])
        insert_rows.append(
            {
                "user_id": user_id,
                "goal_set_id": int(goal_set_id),
                "goal_theme_id": int(goal_theme_id),
                "title": str(row["title"]),
                "status": status,
                "progress_percent": row["progress_percent"],
                "order_index": idx,
                "completed_at": None,
                "dropped_at": None,
            }
        )
        if status == "COMPLETED":
            insert_rows[-1]["completed_at"] = now_utc
        if status == "DROPPED":
            insert_rows[-1]["dropped_at"] = now_utc

    if insert_rows:
        conn.execute(text(insert_sql), insert_rows)

    return True


def replace_legacy_goal_items_from_text(
    *,
    user_id: str,
    goal_set_id: int,
    goal_theme_id: int,
    detail_text: str,
) -> bool:
    engine = load_sql_engine()
    with engine.begin() as conn:
        return _replace_legacy_goal_items_from_text_with_conn(
            conn,
            user_id=user_id,
            goal_set_id=goal_set_id,
            goal_theme_id=goal_theme_id,
            detail_text=detail_text,
        )


def _normalize_goal_item_row(row: dict[str, Any], order_index: int) -> dict[str, Any] | None:
    title = str(row.get("title") or "").strip()
    if not title:
        return None

    status_raw = str(row.get("status") or "ACTIVE").strip().upper()
    status = status_raw if status_raw in {"ACTIVE", "COMPLETED", "DROPPED"} else "ACTIVE"

    progress_raw = row.get("progress_percent")
    progress_percent: float | None = None
    if progress_raw not in (None, ""):
        try:
            progress_percent = float(progress_raw)
        except (TypeError, ValueError):
            progress_percent = None
    if progress_percent is not None:
        progress_percent = min(100.0, max(0.0, progress_percent))

    if status == "COMPLETED" and progress_percent is None:
        progress_percent = 100.0

    weight_raw = row.get("weight")
    try:
        weight = float(weight_raw)
    except (TypeError, ValueError):
        weight = 1.0
    if weight <= 0:
        weight = 1.0

    category_raw = row.get("category_id")
    category_id: int | None = None
    if category_raw not in (None, ""):
        try:
            category_id = int(category_raw)
        except (TypeError, ValueError):
            category_id = None

    subcategory = str(row.get("subcategory") or "").strip() or None
    activity = str(row.get("activity") or "").strip() or None
    notes = str(row.get("notes") or "").strip()
    progress_mode = _normalize_progress_mode(row.get("progress_mode"))
    calc_source = _normalize_calc_source(row.get("calc_source"))
    target_scope = _normalize_target_scope(row.get("target_scope"))
    target_operator = _normalize_target_operator(row.get("target_operator"))

    target_minutes_raw = row.get("target_minutes")
    target_minutes: float | None = None
    if target_minutes_raw not in (None, ""):
        try:
            target_minutes = float(target_minutes_raw)
        except (TypeError, ValueError):
            target_minutes = None
    if target_minutes is not None and target_minutes < 0:
        target_minutes = 0.0

    return {
        "title": title,
        "status": status,
        "progress_percent": progress_percent,
        "progress_mode": progress_mode,
        "calc_source": calc_source,
        "target_scope": target_scope,
        "target_operator": target_operator,
        "target_minutes": target_minutes,
        "weight": weight,
        "category_id": category_id,
        "subcategory": subcategory,
        "activity": activity,
        "notes": notes,
        "order_index": order_index,
    }


def load_goal_items_for_set(
    *,
    user_id: str,
    goal_set_id: int | None,
    goal_theme_id: int | None,
) -> list[dict[str, Any]]:
    if goal_set_id is None or goal_theme_id is None:
        return []

    engine = load_sql_engine()
    with engine.connect() as conn:
        if _goal_items_table_exists(conn):
            goal_items_columns = _goal_items_column_set(conn)
            has_progress_mode = "progress_mode" in goal_items_columns
            has_calc_source = "calc_source" in goal_items_columns
            has_target_scope = "target_scope" in goal_items_columns
            has_target_operator = "target_operator" in goal_items_columns
            has_target_minutes = "target_minutes" in goal_items_columns

            sql = """
                SELECT
                    goal_item_id,
                    title,
                    notes,
                    status,
                    progress_percent,
                    {progress_mode_expr},
                    {calc_source_expr},
                    {target_scope_expr},
                    {target_operator_expr},
                    {target_minutes_expr},
                    weight,
                    category_id,
                    subcategory,
                    activity,
                    source,
                    order_index
                FROM goal_items
                WHERE user_id = :user_id
                  AND goal_set_id = :goal_set_id
                  AND goal_theme_id = :goal_theme_id
                  AND archived_at IS NULL
                ORDER BY order_index, goal_item_id;
            """.format(
                progress_mode_expr=(
                    "progress_mode AS progress_mode"
                    if has_progress_mode
                    else "'MANUAL' AS progress_mode"
                ),
                calc_source_expr=(
                    "calc_source AS calc_source"
                    if has_calc_source
                    else "'TASKS' AS calc_source"
                ),
                target_scope_expr=(
                    "target_scope AS target_scope"
                    if has_target_scope
                    else "'PERIOD' AS target_scope"
                ),
                target_operator_expr=(
                    "target_operator AS target_operator"
                    if has_target_operator
                    else "'GTE' AS target_operator"
                ),
                target_minutes_expr=(
                    "target_minutes AS target_minutes"
                    if has_target_minutes
                    else "NULL::numeric AS target_minutes"
                ),
            )
            rows = conn.execute(
                text(sql),
                {
                    "user_id": user_id,
                    "goal_set_id": int(goal_set_id),
                    "goal_theme_id": int(goal_theme_id),
                },
            ).mappings().all()
            if rows:
                return [
                    {
                        "goal_item_id": int(row["goal_item_id"]),
                        "title": str(row["title"] or ""),
                        "notes": str(row["notes"] or ""),
                        "status": str(row["status"] or "ACTIVE"),
                        "progress_percent": None if row["progress_percent"] is None else float(row["progress_percent"]),
                        "progress_mode": _normalize_progress_mode(row.get("progress_mode")),
                        "calc_source": _normalize_calc_source(row.get("calc_source")),
                        "target_scope": _normalize_target_scope(row.get("target_scope")),
                        "target_operator": _normalize_target_operator(row.get("target_operator")),
                        "target_minutes": None if row["target_minutes"] is None else float(row["target_minutes"]),
                        "weight": float(row["weight"] or 1),
                        "category_id": None if row["category_id"] is None else int(row["category_id"]),
                        "subcategory": str(row["subcategory"] or ""),
                        "activity": str(row["activity"] or ""),
                        "source": str(row["source"] or "MANUAL"),
                        "order_index": int(row["order_index"] or 0),
                    }
                    for row in rows
                ]

    legacy_text = get_goal_set_item_text(
        user_id=user_id,
        goal_set_id=goal_set_id,
        goal_theme_id=goal_theme_id,
    )
    if legacy_text is None:
        return []

    parsed = _parse_legacy_goal_lines(legacy_text)
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(parsed):
        out.append(
            {
                "goal_item_id": None,
                "title": str(row["title"]),
                "notes": "",
                "status": str(row["status"]),
                "progress_percent": row["progress_percent"],
                "progress_mode": "MANUAL",
                "calc_source": "TASKS",
                "target_scope": "PERIOD",
                "target_operator": "GTE",
                "target_minutes": None,
                "weight": 1.0,
                "category_id": None,
                "subcategory": "",
                "activity": "",
                "source": "LEGACY_TEXTAREA",
                "order_index": idx,
            }
        )
    return out


def replace_goal_items_for_set(
    *,
    user_id: str,
    goal_set_id: int,
    goal_theme_id: int,
    items: list[dict[str, Any]],
) -> int:
    normalized_items: list[dict[str, Any]] = []
    for idx, item in enumerate(items or []):
        normalized = _normalize_goal_item_row(item, idx)
        if normalized is not None:
            normalized_items.append(normalized)

    legacy_text = _goal_items_to_legacy_text(
        [
            {"title": item["title"], "status": item["status"]}
            for item in normalized_items
            if item["status"] != "DROPPED"
        ]
    )

    engine = load_sql_engine()
    with engine.begin() as conn:
        if _goal_items_table_exists(conn):
            goal_items_columns = _goal_items_column_set(conn)
            has_progress_mode = "progress_mode" in goal_items_columns
            has_calc_source = "calc_source" in goal_items_columns
            has_target_scope = "target_scope" in goal_items_columns
            has_target_operator = "target_operator" in goal_items_columns
            has_target_minutes = "target_minutes" in goal_items_columns

            conn.execute(
                text(
                    """
                    UPDATE goal_items
                    SET archived_at = now()
                    WHERE user_id = :user_id
                      AND goal_set_id = :goal_set_id
                      AND goal_theme_id = :goal_theme_id
                      AND archived_at IS NULL;
                    """
                ),
                {
                    "user_id": user_id,
                    "goal_set_id": int(goal_set_id),
                    "goal_theme_id": int(goal_theme_id),
                },
            )

            if normalized_items:
                insert_rows: list[dict[str, Any]] = []
                now_utc = datetime.now(timezone.utc)
                for row in normalized_items:
                    status = str(row["status"])
                    row_payload: dict[str, Any] = {
                        "user_id": user_id,
                        "goal_set_id": int(goal_set_id),
                        "goal_theme_id": int(goal_theme_id),
                        "title": row["title"],
                        "notes": row["notes"],
                        "status": status,
                        "progress_percent": row["progress_percent"],
                        "weight": row["weight"],
                        "category_id": row["category_id"],
                        "subcategory": row["subcategory"],
                        "activity": row["activity"],
                        "source": "MANUAL",
                        "order_index": int(row["order_index"]),
                        "completed_at": now_utc if status == "COMPLETED" else None,
                        "dropped_at": now_utc if status == "DROPPED" else None,
                    }
                    if has_progress_mode:
                        row_payload["progress_mode"] = row["progress_mode"]
                    if has_calc_source:
                        row_payload["calc_source"] = row["calc_source"]
                    if has_target_scope:
                        row_payload["target_scope"] = row["target_scope"]
                    if has_target_operator:
                        row_payload["target_operator"] = row["target_operator"]
                    if has_target_minutes:
                        row_payload["target_minutes"] = row["target_minutes"]
                    insert_rows.append(row_payload)

                columns = [
                    "user_id",
                    "goal_set_id",
                    "goal_theme_id",
                    "title",
                    "notes",
                    "status",
                    "progress_percent",
                ]
                if has_progress_mode:
                    columns.append("progress_mode")
                if has_calc_source:
                    columns.append("calc_source")
                if has_target_scope:
                    columns.append("target_scope")
                if has_target_operator:
                    columns.append("target_operator")
                if has_target_minutes:
                    columns.append("target_minutes")
                columns.extend(
                    [
                        "weight",
                        "category_id",
                        "subcategory",
                        "activity",
                        "source",
                        "order_index",
                        "completed_at",
                        "dropped_at",
                    ]
                )
                values_clause = ",\n                            ".join(f":{col}" for col in columns)
                columns_clause = ",\n                            ".join(columns)

                conn.execute(
                    text(
                        f"""
                        INSERT INTO goal_items (
                            {columns_clause}
                        )
                        VALUES (
                            {values_clause}
                        );
                        """
                    ),
                    insert_rows,
                )

        _save_goal_set_item_text_with_conn(
            conn,
            user_id=user_id,
            goal_set_id=goal_set_id,
            goal_theme_id=goal_theme_id,
            detail_text=legacy_text,
        )

    return len(normalized_items)


def compute_goal_actual_minutes(
    *,
    user_id: str,
    start_date: date,
    end_date_exclusive: date,
    category_id: int | None,
    subcategory: str | None,
    activity: str | None,
    calc_source: GoalCalcSource | str = "TASKS",
) -> float:
    """
    Compute actual minutes for a goal configuration over [start_date, end_date_exclusive).
    Supports tasks, metrics, or combined sources.
    """
    source = _normalize_calc_source(calc_source)
    if end_date_exclusive <= start_date:
        return 0.0

    sub_norm = (subcategory or "").strip().lower() or None
    act_norm = (activity or "").strip().lower() or None

    # Subcategory/activity filters are meaningful only when a category filter is present.
    if category_id is None:
        sub_norm = None
        act_norm = None

    params = {
        "user_id": user_id,
        "start_date": start_date,
        "end_date": end_date_exclusive,
        "category_id": category_id,
        "subcategory_norm": sub_norm,
        "activity_norm": act_norm,
    }

    task_sql = text(
        """
        SELECT COALESCE(SUM(td.duration_min), 0) AS minutes
        FROM task_data td
        WHERE td.user_id = :user_id
          AND td.date >= :start_date
          AND td.date < :end_date
          AND (:category_id IS NULL OR td.category_id = :category_id)
          AND (
            :subcategory_norm IS NULL
            OR lower(btrim(COALESCE(td.subcategory, ''))) = :subcategory_norm
          )
          AND (
            :activity_norm IS NULL
            OR lower(btrim(COALESCE(td.activity, ''))) = :activity_norm
          );
        """
    )
    metric_sql = text(
        """
        SELECT COALESCE(SUM(dmv.value_num * md.to_minutes_factor), 0) AS minutes
        FROM daily_metric_values dmv
        JOIN metric_definitions md
          ON md.user_id = dmv.user_id
         AND md.metric_key = dmv.metric_key
        WHERE dmv.user_id = :user_id
          AND dmv.date >= :start_date
          AND dmv.date < :end_date
          AND md.to_minutes_factor IS NOT NULL
          AND (:category_id IS NULL OR md.category_id = :category_id)
          AND (
            :subcategory_norm IS NULL
            OR lower(btrim(COALESCE(md.subcategory, ''))) = :subcategory_norm
          )
          AND (
            :activity_norm IS NULL
            OR lower(btrim(COALESCE(md.activity, ''))) = :activity_norm
          );
        """
    )

    engine = load_sql_engine()
    with engine.connect() as conn:
        task_minutes = 0.0
        metric_minutes = 0.0
        if source in {"TASKS", "TASKS_AND_METRICS"}:
            task_minutes = float(conn.execute(task_sql, params).scalar() or 0.0)
        if source in {"METRICS", "TASKS_AND_METRICS"}:
            metric_minutes = float(conn.execute(metric_sql, params).scalar() or 0.0)

    return float(task_minutes + metric_minutes)


def save_goal_text_dual_write(
    *,
    user_id: str,
    goal_set_id: int,
    goal_theme_id: int,
    detail_text: str,
) -> bool:
    """
    Dual-write for migration safety:
      1) append legacy revision row
      2) replace corresponding structured legacy rows
    Returns True if either path changed data.
    """
    engine = load_sql_engine()
    with engine.begin() as conn:
        legacy_changed = _save_goal_set_item_text_with_conn(
            conn,
            user_id=user_id,
            goal_set_id=goal_set_id,
            goal_theme_id=goal_theme_id,
            detail_text=detail_text,
        )
        structured_changed = _replace_legacy_goal_items_from_text_with_conn(
            conn,
            user_id=user_id,
            goal_set_id=goal_set_id,
            goal_theme_id=goal_theme_id,
            detail_text=detail_text,
        )
        return legacy_changed or structured_changed


def get_goal_completion_summary(
    *,
    user_id: str,
    goal_set_id: int | None,
    goal_theme_id: int | None,
) -> dict[str, float]:
    if goal_set_id is None or goal_theme_id is None:
        return {
            "total_count": 0.0,
            "completed_count": 0.0,
            "weighted_completion_percent": 0.0,
        }

    sql = """
        SELECT
            COUNT(*)::numeric AS total_count,
            COUNT(*) FILTER (WHERE status = 'COMPLETED')::numeric AS completed_count,
            COALESCE(SUM(weight), 0)::numeric AS total_weight,
            COALESCE(
                SUM(
                    CASE
                        WHEN status = 'COMPLETED' THEN weight
                        WHEN progress_percent IS NOT NULL THEN weight * (progress_percent / 100.0)
                        ELSE 0
                    END
                ),
                0
            )::numeric AS earned_weight
        FROM goal_items
        WHERE user_id = :user_id
          AND goal_set_id = :goal_set_id
          AND goal_theme_id = :goal_theme_id
          AND archived_at IS NULL;
    """

    engine = load_sql_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(sql),
            {
                "user_id": user_id,
                "goal_set_id": int(goal_set_id),
                "goal_theme_id": int(goal_theme_id),
            },
        ).mappings().one()

    total_weight = float(row["total_weight"] or 0)
    earned_weight = float(row["earned_weight"] or 0)
    pct = (earned_weight / total_weight * 100.0) if total_weight > 0 else 0.0

    return {
        "total_count": float(row["total_count"] or 0),
        "completed_count": float(row["completed_count"] or 0),
        "weighted_completion_percent": pct,
    }


def backfill_goal_items_from_latest_legacy_rows(user_id: str | None = None) -> int:
    """
    Populate goal_items from the latest legacy goal_set_items snapshot.
    Safe to re-run; each set/theme is fully replaced for source='LEGACY_TEXTAREA'.
    Returns number of (goal_set, goal_theme) pairs processed.
    """
    sql = """
        WITH latest AS (
            SELECT
                gsi.goal_set_id,
                gsi.goal_theme_id,
                MAX(gsi.revision_no) AS revision_no
            FROM goal_set_items gsi
            GROUP BY gsi.goal_set_id, gsi.goal_theme_id
        )
        SELECT
            gs.user_id,
            l.goal_set_id,
            l.goal_theme_id,
            gsi.detail_text
        FROM latest l
        JOIN goal_set_items gsi
          ON gsi.goal_set_id = l.goal_set_id
         AND gsi.goal_theme_id = l.goal_theme_id
         AND gsi.revision_no = l.revision_no
        JOIN goal_sets gs
          ON gs.goal_set_id = l.goal_set_id
        WHERE (:user_id IS NULL OR gs.user_id = :user_id);
    """

    engine = load_sql_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"user_id": user_id}).mappings().all()

    processed = 0
    for row in rows:
        replace_legacy_goal_items_from_text(
            user_id=str(row["user_id"]),
            goal_set_id=int(row["goal_set_id"]),
            goal_theme_id=int(row["goal_theme_id"]),
            detail_text=str(row["detail_text"] or ""),
        )
        processed += 1

    return processed
