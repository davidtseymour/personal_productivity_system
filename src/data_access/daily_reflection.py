

from sqlalchemy import text
from src.data_access.db import load_sql_engine


def upsert_daily_reflection(
    *,
    user_id: str,
    reflection_date: str,
    intentionality_score: int | None,
    accomplishments: str,
    what_worked: str,
    what_didnt_work: str,
    intentions_tomorrow: str,
) -> None:
    engine = load_sql_engine()

    sql = text(
        """
        INSERT INTO daily_reflections (
            user_id,
            reflection_date,
            intentionality_score,
            accomplishments,
            what_worked,
            what_didnt_work,
            intentions_tomorrow,
            updated_at
        )
        VALUES (
            :user_id,
            :reflection_date,
            :intentionality_score,
            :accomplishments,
            :what_worked,
            :what_didnt_work,
            :intentions_tomorrow,
            now()
        )
        ON CONFLICT (user_id, reflection_date)
        DO UPDATE SET
            intentionality_score = EXCLUDED.intentionality_score,
            accomplishments       = EXCLUDED.accomplishments,
            what_worked           = EXCLUDED.what_worked,
            what_didnt_work       = EXCLUDED.what_didnt_work,
            intentions_tomorrow   = EXCLUDED.intentions_tomorrow,
            updated_at            = now();
        """
    )

    params = {
        "user_id": user_id,
        "reflection_date": reflection_date,
        "intentionality_score": intentionality_score,
        "accomplishments": accomplishments or "",
        "what_worked": what_worked or "",
        "what_didnt_work": what_didnt_work or "",
        "intentions_tomorrow": intentions_tomorrow or "",
    }

    with engine.begin() as conn:
        conn.execute(sql, params)


def load_daily_reflection(user_id: str, reflection_date: str) -> dict | None:
    engine = load_sql_engine()

    sql = text(
        """
        SELECT
            reflection_date,
            intentionality_score,
            accomplishments,
            what_worked,
            what_didnt_work,
            intentions_tomorrow
        FROM daily_reflections
        WHERE user_id = :user_id
          AND reflection_date = :reflection_date;
        """
    )

    with engine.connect() as conn:
        row = conn.execute(
            sql,
            {"user_id": user_id, "reflection_date": reflection_date},
        ).mappings().first()

    return dict(row) if row else None