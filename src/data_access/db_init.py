
from sqlalchemy import text
from src.data_access.db import load_sql_engine, get_user_id, update_metric_definition  # or get_engine

# *************** MAIN STRUCTURE ***************

# ----- Users-----
def create_users_table(engine):

    statements = [
        """CREATE EXTENSION IF NOT EXISTS pgcrypto;""",
        """
                    CREATE TABLE IF NOT EXISTS users (
                      user_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                      username     TEXT NOT NULL UNIQUE,
                      display_name TEXT NOT NULL,
                      is_active    BOOLEAN NOT NULL DEFAULT TRUE,
                      created_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

# ----- User Categories -----
def create_user_categories(engine) -> None:
    statements: list[str] = [
        """
        CREATE TABLE IF NOT EXISTS user_categories (
          category_id   BIGSERIAL PRIMARY KEY,
          user_id       UUID NOT NULL REFERENCES users(user_id),
          category_name TEXT NOT NULL,

          is_active     BOOLEAN NOT NULL DEFAULT TRUE,
          sort_order    INT NOT NULL DEFAULT 0,

          created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

          CONSTRAINT user_categories_name_nonempty CHECK (btrim(category_name) <> '')
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_user_categories_user_lowername
        ON user_categories (user_id, lower(btrim(category_name)));
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_user_categories_user_active_sort
        ON user_categories (user_id, is_active, sort_order, category_name);
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


# *************** Tasks ***************

# ----- task_data ------
def create_task_data_table(engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS task_data (
            task_id BIGSERIAL PRIMARY KEY,

            user_id UUID NOT NULL REFERENCES users(user_id),

            date DATE,
            start_at TIMESTAMP WITHOUT TIME ZONE,
            end_at TIMESTAMP WITHOUT TIME ZONE,
            duration_min BIGINT,

            category_id BIGINT NOT NULL REFERENCES user_categories(category_id),

            subcategory TEXT,
            activity TEXT,
            notes TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT chk_task_time_order
                CHECK (
                    start_at IS NULL
                    OR end_at IS NULL
                    OR end_at > start_at
                )
        );
        """,
        """
            CREATE INDEX IF NOT EXISTS idx_task_data_user_date
            ON task_data (user_id, date);
        """,
        """
            CREATE INDEX IF NOT EXISTS idx_task_data_user_start_desc
            ON task_data (user_id, start_at DESC);
        """,
        """
            CREATE INDEX IF NOT EXISTS idx_task_data_user_category_date
            ON task_data (user_id, category_id, date);
        """,
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


# *************** Daily Metrics ***************

# ----- metric_definitions -----

# ----- daily_metric_values -----



# *************** GOALS ***************

# ----- GOAL THEMES -----
def create_goal_themes_table(engine) -> None:
    statements = [
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
        for stmt in statements:
            conn.execute(text(stmt))


# ----- GOAL SETS -----
def create_goal_sets_table(engine) -> None:
    statements = [
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
        for stmt in statements:
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

    # Main Structure
    create_users_table(engine)
    create_user_categories(engine)

    # Goals
    create_goal_themes_table(engine)
    create_goal_sets_table(engine)
    create_goal_sets_table(engine)

    # Daily reflections
    create_daily_reflections_table(engine)