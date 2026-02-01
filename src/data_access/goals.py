from src.data_access.db import load_sql_engine
from sqlalchemy import text
from datetime import date
from typing import Literal

GoalHorizon = Literal["WEEK", "MONTH", "QTR"]

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

def get_goals_themes(user_id):
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

def get_goal_set_item_text(goal_set_id: int | None, goal_theme_id: int | None) -> str:
    """
    Returns the latest revision text for this (goal_set_id, goal_theme_id).
    Returns "" if either id is missing or no row exists.
    """
    if goal_set_id is None or goal_theme_id is None:
        return ""

    sql = """
        SELECT detail_text
        FROM goal_set_items
        WHERE goal_set_id = :goal_set_id
          AND goal_theme_id = :goal_theme_id
        ORDER BY revision_no DESC
        LIMIT 1;
    """
    engine = load_sql_engine()
    with engine.connect() as conn:
        val = conn.execute(
            text(sql),
            {"goal_set_id": goal_set_id, "goal_theme_id": goal_theme_id},
        ).scalar()

    return val or ""


def save_goal_set_item_text(*, goal_set_id: int, goal_theme_id: int, detail_text: str) -> bool:
    """
    Inserts a new revision row ONLY if the text changed.
    Returns True if inserted, False if no change.
    """
    engine = load_sql_engine()
    detail_text = detail_text or ""

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
    WHERE COALESCE((SELECT detail_text FROM cur), '') <> :detail_text
    ON CONFLICT DO NOTHING
    RETURNING 1;
    """

    with engine.begin() as conn:
        inserted = conn.execute(
            text(sql),
            {
                "goal_set_id": int(goal_set_id),
                "goal_theme_id": int(goal_theme_id),
                "detail_text": detail_text,
            },
        ).scalar()

    return bool(inserted)

