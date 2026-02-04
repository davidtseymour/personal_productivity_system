import pandas as pd
from sqlalchemy import text
from src.data_access.db import load_sql_engine, get_user_id, update_metric_definition  # or get_engine

# *************** GOALS ***************

# ----- GOAL THEMES -----
def create_goal_themes_table(engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS goal_themes (
            goal_theme_id BIGSERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id),
            name TEXT NOT NULL,
            name_norm TEXT GENERATED ALWAYS AS (lower(trim(name))) STORED,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            archived_at TIMESTAMPTZ NULL
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_themes_user_active
        ON goal_themes (user_id, name_norm)
        WHERE archived_at IS NULL;
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_themes_user
        ON goal_themes (user_id);
        """,
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))

# ----- GOAL SETS -----
def create_goal_sets_table(engine) -> None:
    stmts = [
        # Enum for horizon (idempotent)
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_horizon') THEN
            CREATE TYPE goal_horizon AS ENUM ('WEEK', 'MONTH', 'QTR');
          END IF;
        END $$;
        """,
        """
        CREATE TABLE IF NOT EXISTS goal_sets (
            goal_set_id  BIGSERIAL PRIMARY KEY,
            user_id      UUID NOT NULL REFERENCES users(user_id),
            horizon      goal_horizon NOT NULL,
            period_start DATE NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        # One set per user/horizon/period_start
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_sets_user_period
        ON goal_sets (user_id, horizon, period_start);
        """,

    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))

# ----- GOAL SET ITEMS (item-level revisions) -----
def create_goal_set_items_table(engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS goal_set_items (
            goal_set_id   BIGINT NOT NULL
                REFERENCES goal_sets(goal_set_id) ON DELETE CASCADE,

            goal_theme_id BIGINT NOT NULL
                REFERENCES goal_themes(goal_theme_id),

            revision_no   INT NOT NULL DEFAULT 1,
            detail_text   TEXT NOT NULL DEFAULT '',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

            PRIMARY KEY (goal_set_id, goal_theme_id, revision_no),
            CONSTRAINT ck_goal_set_items_revision_pos CHECK (revision_no >= 1)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_set_items_latest
        ON goal_set_items (goal_set_id, goal_theme_id, revision_no DESC);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_set_items_by_set
        ON goal_set_items (goal_set_id, revision_no DESC);
        """,
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))

# *************** DAILY REFLECTION ***************

# ----- CREATE DAILY REFLECTION TABLE -----
def create_daily_reflections_table(engine):
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS daily_reflections (
            daily_reflection_id BIGSERIAL PRIMARY KEY,

            user_id UUID NOT NULL REFERENCES users(user_id),
            reflection_date DATE NOT NULL,

            intentionality_score SMALLINT NULL
                CHECK (intentionality_score BETWEEN 1 AND 10),

            accomplishments TEXT NOT NULL DEFAULT '',
            what_worked TEXT NOT NULL DEFAULT '',
            what_didnt_work TEXT NOT NULL DEFAULT '',
            intentions_tomorrow TEXT NOT NULL DEFAULT '',

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_daily_reflections_user_date
                UNIQUE (user_id, reflection_date)
        );
        """
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


def init_db():
    engine = load_sql_engine()

    # Goals
    create_goal_themes_table(engine)
    create_goal_sets_table(engine)
    create_goal_sets_table(engine)

    # Daily reflections
    create_daily_reflections_table(engine)