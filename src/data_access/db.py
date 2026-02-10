from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, Engine
from dotenv import load_dotenv
from sqlalchemy import text
import os

from functools import lru_cache

load_dotenv()


@lru_cache(maxsize=1)
def load_sql_engine()->Engine:
    # Cacched load of the database from .env
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME')

    engine = create_engine(
        f'postgresql://{user}:{password}@{host}:{port}/{database}',
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    return engine



def fetch_user_categories_rows(user_id: str): #Main source of truth
    engine = load_sql_engine()
    sql = text("""
        SELECT category_id, category_name
        FROM user_categories
        WHERE user_id = :user_id
          AND is_active = TRUE
        ORDER BY sort_order, category_name
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"user_id": user_id}).mappings().all()

def load_category_id_to_name(user_id: str) -> dict[int, str]:
    rows = fetch_user_categories_rows(user_id)
    return {int(r["category_id"]): str(r["category_name"]) for r in rows}

def get_category_from_id(user_id: str, category_id: int) -> str | None:
    """
    Return the category name for a given active category_id owned by the user.
    Returns None if the category_id is not found (e.g., invalid, inactive, or not owned).
    """
    try:
        cid = int(category_id)
    except (TypeError, ValueError):
        return None

    rows = fetch_user_categories_rows(user_id)
    for r in rows:
        if int(r["category_id"]) == cid:
            return str(r["category_name"])
    return None





# Category-level time summaries for view trends
# These queries return (date, category, total_minutes) and are
# combined in pandas to produce unified daily category totals.

def load_category_list(user_id):
    engine = load_sql_engine()
    sql = text("""
              SELECT category_id, category_name
              FROM user_categories
              WHERE user_id = :user_id
                AND is_active = TRUE
              ORDER BY sort_order, category_name
              """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"user_id": user_id}).mappings().all()

    return [{"label": r["category_name"], "value": r["category_id"]} for r in rows]

def load_tasks_base_for_view_trend(user_id):
    engine = load_sql_engine()
    sql = text("""
        SELECT
          date,
          category_id,
          subcategory,
          SUM(duration_min) AS total_minutes
        FROM task_data
        WHERE user_id = :user_id
          AND category_id IS NOT NULL
        GROUP BY date, category_id, subcategory
        ORDER BY date, category_id, subcategory;
    """)
    return pd.read_sql(sql, engine, params={"user_id": user_id})


def load_daily_metrics_base_for_view_trend(user_id):
    engine = load_sql_engine()
    sql = text("""
        SELECT
            dmv.date,
            md.category_id,
            md.subcategory,
            SUM(dmv.value_num * md.to_minutes_factor) AS total_minutes
        FROM daily_metric_values dmv
        JOIN metric_definitions md
          ON dmv.metric_key = md.metric_key
         AND md.user_id = dmv.user_id
        WHERE dmv.user_id = :user_id
          AND md.category_id IS NOT NULL
          AND md.to_minutes_factor IS NOT NULL
        GROUP BY dmv.date, md.category_id, md.subcategory
        ORDER BY dmv.date, md.category_id, md.subcategory
    """)
    return pd.read_sql(sql, engine, params={"user_id": user_id})

# Weekly summary task tables

def load_weekly_summary_table_dailies(user_id):
    engine = load_sql_engine()
    today = date.today()
    start_date = today - timedelta(days=7)
    end_date = today

    sql = text("""
        SELECT 
            dmv.date,
            md.display_name,
            dmv.value_num
        FROM daily_metric_values dmv
        JOIN metric_definitions md
          ON md.metric_key = dmv.metric_key
         AND md.user_id = dmv.user_id
        WHERE dmv.user_id = :user_id
          AND dmv.date >= :start_date
          AND dmv.date < :end_date
          AND md.is_duration = FALSE
        ORDER BY dmv.date, md.sort_order, md.display_name
    """)

    return pd.read_sql(
        sql,
        engine,
        params={"user_id": user_id, "start_date": start_date, "end_date": end_date},
    )


# New functions

def load_task_base_for_daily_summary(user_id):
    engine = load_sql_engine()
    today = date.today()
    sql = text("""
        SELECT
            category_id,
            subcategory,
            SUM(duration_min) AS total_minutes
        FROM task_data
        WHERE user_id = :user_id
          AND date = :today
          AND subcategory IS NOT NULL
          AND category_id IS NOT NULL
        GROUP BY category_id, subcategory
        ORDER BY category_id, subcategory
    """)
    return pd.read_sql(sql, engine, params={"user_id": user_id, "today": today})

def load_metrics_base_for_daily_summary(user_id):
    engine = load_sql_engine()
    today = date.today()
    sql = text("""
               SELECT md.category_id,
                      md.subcategory,
                      SUM(dmv.value_num * md.to_minutes_factor) AS total_minutes
               FROM daily_metric_values dmv
                        JOIN metric_definitions md
                             ON dmv.metric_key = md.metric_key
                                 AND md.user_id = dmv.user_id
               WHERE dmv.user_id = :user_id
                 AND dmv.date = :today
                 AND md.subcategory IS NOT NULL
                 AND md.to_minutes_factor IS NOT NULL
                 AND md.category_id IS NOT NULL
               GROUP BY md.category_id, md.subcategory
               ORDER BY md.category_id, md.subcategory
               """)
    return pd.read_sql(sql, engine, params={"user_id": user_id,"today":today})


def load_recent_task_data(user_id, n=5):
    engine = load_sql_engine()
    query = text("""
        SELECT
            td.task_id,
            td.start_at,
            td.end_at,
            uc.category_name AS category,
            td.subcategory,
            td.activity
        FROM task_data td
        LEFT JOIN user_categories uc
          ON uc.user_id = td.user_id
         AND uc.category_id = td.category_id
        WHERE td.user_id = :user_id
        ORDER BY td.start_at DESC, td.task_id DESC
        LIMIT :n
    """)
    return pd.read_sql(query, con=engine, params={"user_id": user_id, "n": int(n)})


def insert_task(row_dict):
    engine = load_sql_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO task_data (
                    date, subcategory, activity,
                    start_at, end_at, duration_min, notes, user_id, category_id
                )
                VALUES (
                    :date, :subcategory, :activity,
                    :start_at, :end_at, :duration_min, :notes, :user_id, :category_id
                )
            """),
            row_dict,
        )

def update_task(task_id: int, row_dict: dict, user_id:str):
    engine = load_sql_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE task_data
                SET
                    date = :date,
                    category_id = :category_id,
                    subcategory = :subcategory,
                    activity = :activity,
                    start_at = :start_at,
                    end_at = :end_at,
                    duration_min = :duration_min,
                    notes = :notes,
                    updated_at = NOW()
                WHERE task_id = :task_id
            """),
            {
                **row_dict,
                "task_id": task_id,
            },
        )

def load_task_db(task_id: int) -> dict:
    engine = load_sql_engine()

    with engine.begin() as conn:
        result = conn.execute(
            text("""
                SELECT
                    task_id,
                    date,
                    category_id,
                    subcategory,
                    activity,
                    start_at,
                    end_at,
                    duration_min,
                    notes
                FROM task_data
                WHERE task_id = :task_id
            """),
            {"task_id": task_id},
        ).mappings().one()

    return dict(result)

def update_daily_metrics(records):
    """
    records: list[dict] with keys:
      - user_id
      - date
      - metric_key
      - value_num
    """
    if not records:
        return

    engine = load_sql_engine()

    UPSERT_SQL = """
        INSERT INTO daily_metric_values (user_id, date, metric_key, value_num, updated_at)
        VALUES (:user_id, :date, :metric_key, :value_num, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id, date, metric_key) DO UPDATE
        SET value_num = EXCLUDED.value_num,
            updated_at = CURRENT_TIMESTAMP;
    """

    with engine.begin() as conn:
        conn.execute(text(UPSERT_SQL), records)

def get_daily_metrics_definitions(user_id):
    sql = """
        SELECT metric_key, display_name, is_duration
        FROM metric_definitions
        WHERE user_id = :user_id
        ORDER BY sort_order, display_name
    """
    engine = load_sql_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {
                "user_id": user_id,
            },
        ).mappings().fetchall()

    return rows

def get_daily_metrics_for_date(metric_date, user_id):
    sql = """
    SELECT
      dmv.metric_key,
      dmv.value_num
    FROM daily_metric_values dmv
    JOIN metric_definitions md
      ON dmv.metric_key = md.metric_key
    WHERE dmv.date = :metric_date
      AND dmv.user_id = :user_id
    ORDER BY md.sort_order;
    """

    engine = load_sql_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {
                "metric_date": metric_date,
                "user_id": user_id,
            },
        ).mappings().fetchall()

    return {row["metric_key"]: row["value_num"] for row in rows}

def delete_task_sql(task_id: int) -> None:
    engine = load_sql_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM task_data WHERE task_id = :task_id"),
            {"task_id": task_id},
        )

def get_user_id(username: str):
    engine = load_sql_engine()
    sql = """
        SELECT user_id
        FROM users
        WHERE username = :username
          AND is_active = TRUE
    """
    with engine.begin() as conn:
        return str(conn.execute(
            text(sql),
            {"username": username}
        ).scalar_one())


def get_users():
    engine = load_sql_engine()

    sql = """
          SELECT user_id, \
                 display_name
          FROM users
          WHERE is_active = TRUE
          ORDER BY display_name \
          """

    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
        ).mappings().fetchall()

    return {str(row["user_id"]): row["display_name"] for row in rows}

def get_first_user_id():
    users = get_users()
    return next(iter(users), None)


def load_today_summary_minutes(user_id: str, selected_date):
    engine = load_sql_engine()
    sql = text("""
        WITH task_totals AS (
            SELECT td.category_id, SUM(td.duration_min) AS minutes
            FROM task_data td
            WHERE td.user_id = :user_id
              AND td.category_id IS NOT NULL
              AND td.date = :selected_date
            GROUP BY td.category_id
        ),
        metric_totals AS (
            SELECT md.category_id, SUM(dmv.value_num * md.to_minutes_factor) AS minutes
            FROM daily_metric_values dmv
            JOIN metric_definitions md
              ON md.metric_key = dmv.metric_key
             AND md.user_id = dmv.user_id
            WHERE dmv.user_id = :user_id
              AND md.category_id IS NOT NULL
              AND md.to_minutes_factor IS NOT NULL
              AND dmv.date = :selected_date
            GROUP BY md.category_id
        ),
        combined AS (
            SELECT category_id, minutes FROM task_totals
            UNION ALL
            SELECT category_id, minutes FROM metric_totals
        )
        SELECT
            c.category_id,
            uc.category_name,
            uc.sort_order,
            SUM(c.minutes) AS total_minutes
        FROM combined c
        LEFT JOIN user_categories uc
          ON uc.user_id = :user_id
         AND uc.category_id = c.category_id
        GROUP BY c.category_id, uc.category_name, uc.sort_order
        ORDER BY uc.sort_order NULLS LAST, uc.category_name, c.category_id
    """)
    return pd.read_sql(sql, engine, params={"user_id": user_id, "selected_date": selected_date})


def load_weekly_summary_minutes_by_day(user_id: str, selected_date=None, days: int = 7):
    end_date = selected_date or date.today()
    start_date = end_date - timedelta(days=days)

    engine = load_sql_engine()
    sql = text("""
        WITH task_totals AS (
            SELECT td.date, td.category_id, SUM(td.duration_min) AS minutes
            FROM task_data td
            WHERE td.user_id = :user_id
              AND td.category_id IS NOT NULL
              AND td.date >= :start_date
              AND td.date <  :end_date
            GROUP BY td.date, td.category_id
        ),
        metric_totals AS (
            SELECT dmv.date, md.category_id, SUM(dmv.value_num * md.to_minutes_factor) AS minutes
            FROM daily_metric_values dmv
            JOIN metric_definitions md
              ON md.metric_key = dmv.metric_key
             AND md.user_id = dmv.user_id
            WHERE dmv.user_id = :user_id
              AND md.category_id IS NOT NULL
              AND md.to_minutes_factor IS NOT NULL
              AND dmv.date >= :start_date
              AND dmv.date <  :end_date
            GROUP BY dmv.date, md.category_id
        ),
        combined AS (
            SELECT date, category_id, minutes FROM task_totals
            UNION ALL
            SELECT date, category_id, minutes FROM metric_totals
        )
        SELECT
            c.date,
            c.category_id,
            uc.category_name,
            uc.sort_order,
            SUM(c.minutes) AS total_minutes
        FROM combined c
        LEFT JOIN user_categories uc
          ON uc.user_id = :user_id
         AND uc.category_id = c.category_id
        GROUP BY c.date, c.category_id, uc.category_name, uc.sort_order
        ORDER BY c.date, uc.sort_order NULLS LAST, uc.category_name, c.category_id
    """)
    return pd.read_sql(
        sql, engine,
        params={"user_id": user_id, "start_date": start_date, "end_date": end_date},
    )
