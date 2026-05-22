from sqlalchemy import Engine, text
from src.data_access.db import load_sql_engine

# *************** MAIN STRUCTURE ***************

def create_row_audit_trigger_function(engine: Engine) -> None:
    statements = [
        """
        CREATE OR REPLACE FUNCTION set_updated_at_and_lock_version()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = now();
          NEW.lock_version = COALESCE(OLD.lock_version, 1) + 1;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

# ----- Users-----
def create_users_table(engine: Engine) -> None:

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
def create_user_categories(engine: Engine) -> None:
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
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_user_categories_user_category_id
        ON user_categories (user_id, category_id);
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


# *************** Tasks ***************

# ----- task_data ------
def create_task_data_table(engine: Engine) -> None:
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

def create_metric_definitions_table(engine: Engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS metric_definitions (

            user_id UUID NOT NULL REFERENCES users(user_id),
            metric_key TEXT NOT NULL,
            display_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            value_type TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_duration BOOLEAN NOT NULL DEFAULT FALSE,
            category_id BIGINT NULL
                REFERENCES user_categories(category_id),
            subcategory TEXT NULL,
            activity TEXT NULL,
            to_minutes_factor DOUBLE PRECISION NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT metric_definitions_pkey
                PRIMARY KEY (user_id, metric_key),

            CONSTRAINT to_minutes_factor_positive
                CHECK (to_minutes_factor IS NULL OR to_minutes_factor >= 0),

            CONSTRAINT subcategory_requires_category
                CHECK (subcategory IS NULL OR category_id IS NOT NULL),

            CONSTRAINT activity_requires_subcategory
                CHECK (activity IS NULL OR subcategory IS NOT NULL),

            CONSTRAINT ck_metric_defs_ignore_when_category_null
                CHECK (
                    category_id IS NOT NULL
                    OR (subcategory IS NULL AND activity IS NULL)
                )
        );
        """,
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


# ----- daily_metric_values -----

def create_daily_metric_values_table(engine: Engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS daily_metric_values (
            user_id    UUID NOT NULL
                REFERENCES users(user_id),

            date       DATE NOT NULL,
            metric_key TEXT NOT NULL,

            value_num  DOUBLE PRECISION NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT daily_metric_values_pkey
                PRIMARY KEY (user_id, date, metric_key),

            -- FK to metric definitions (composite, since metric_definitions PK is (user_id, metric_key))
            CONSTRAINT fk_daily_metric_values_metric_def
                FOREIGN KEY (user_id, metric_key)
                REFERENCES metric_definitions(user_id, metric_key)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_daily_metric_values_user_day
        ON daily_metric_values (user_id, date);
        """
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))

# *************** GOALS ***************

# ----- GOAL THEMES -----
def create_goal_themes_table(engine: Engine) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS goal_themes (
            goal_theme_id BIGSERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id),
            name TEXT NOT NULL,
            name_norm TEXT GENERATED ALWAYS AS (lower(trim(name))) STORED,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            lock_version INT NOT NULL DEFAULT 1,
            archived_at TIMESTAMPTZ NULL
        );
        """,
        """
        ALTER TABLE goal_themes
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
        """,
        """
        ALTER TABLE goal_themes
        ADD COLUMN IF NOT EXISTS lock_version INT NOT NULL DEFAULT 1;
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_themes_user_active
        ON goal_themes (user_id, name_norm)
        WHERE archived_at IS NULL;
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_themes_theme_user
        ON goal_themes (goal_theme_id, user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_themes_user
        ON goal_themes (user_id);
        """,
        """
        DROP TRIGGER IF EXISTS trg_goal_themes_audit ON goal_themes;
        """,
        """
        CREATE TRIGGER trg_goal_themes_audit
        BEFORE UPDATE ON goal_themes
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at_and_lock_version();
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


# ----- GOAL SETS -----
def create_goal_sets_table(engine: Engine) -> None:
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
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            lock_version INT NOT NULL DEFAULT 1
        );
        """,
        """
        ALTER TABLE goal_sets
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
        """,
        """
        ALTER TABLE goal_sets
        ADD COLUMN IF NOT EXISTS lock_version INT NOT NULL DEFAULT 1;
        """,
        # One set per user/horizon/period_start
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_sets_user_period
        ON goal_sets (user_id, horizon, period_start);
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_sets_set_user
        ON goal_sets (goal_set_id, user_id);
        """,
        """
        DROP TRIGGER IF EXISTS trg_goal_sets_audit ON goal_sets;
        """,
        """
        CREATE TRIGGER trg_goal_sets_audit
        BEFORE UPDATE ON goal_sets
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at_and_lock_version();
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


# ----- GOAL SET ITEMS (item-level revisions) -----
def create_goal_set_items_table(engine: Engine) -> None:
    stmts = [
        """
        CREATE TABLE IF NOT EXISTS goal_set_items (
            goal_set_id   BIGINT NOT NULL
                REFERENCES goal_sets(goal_set_id) ON DELETE CASCADE,

            goal_theme_id BIGINT NOT NULL
                REFERENCES goal_themes(goal_theme_id),

            user_id UUID NULL,

            revision_no   INT NOT NULL DEFAULT 1,
            detail_text   TEXT NOT NULL DEFAULT '',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            lock_version  INT NOT NULL DEFAULT 1,

            PRIMARY KEY (goal_set_id, goal_theme_id, revision_no),
            CONSTRAINT ck_goal_set_items_revision_pos CHECK (revision_no >= 1)
        );
        """,
        """
        ALTER TABLE goal_set_items
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
        """,
        """
        ALTER TABLE goal_set_items
        ADD COLUMN IF NOT EXISTS lock_version INT NOT NULL DEFAULT 1;
        """,
        """
        ALTER TABLE goal_set_items
        ADD COLUMN IF NOT EXISTS user_id UUID;
        """,
        """
        UPDATE goal_set_items gsi
        SET user_id = gs.user_id
        FROM goal_sets gs
        WHERE gsi.goal_set_id = gs.goal_set_id
          AND gsi.user_id IS NULL;
        """,
        """
        ALTER TABLE goal_set_items
        ALTER COLUMN user_id SET NOT NULL;
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_set_items_user
        ON goal_set_items (user_id, goal_set_id, goal_theme_id, revision_no DESC);
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_goal_set_items_goal_set_user'
          ) THEN
            ALTER TABLE goal_set_items
            ADD CONSTRAINT fk_goal_set_items_goal_set_user
            FOREIGN KEY (goal_set_id, user_id)
            REFERENCES goal_sets (goal_set_id, user_id)
            ON DELETE CASCADE
            NOT VALID;
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_goal_set_items_goal_theme_user'
          ) THEN
            ALTER TABLE goal_set_items
            ADD CONSTRAINT fk_goal_set_items_goal_theme_user
            FOREIGN KEY (goal_theme_id, user_id)
            REFERENCES goal_themes (goal_theme_id, user_id)
            NOT VALID;
          END IF;
        END $$;
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_set_items_latest
        ON goal_set_items (goal_set_id, goal_theme_id, revision_no DESC);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_set_items_by_set
        ON goal_set_items (goal_set_id, revision_no DESC);
        """,
        """
        DROP TRIGGER IF EXISTS trg_goal_set_items_audit ON goal_set_items;
        """,
        """
        CREATE TRIGGER trg_goal_set_items_audit
        BEFORE UPDATE ON goal_set_items
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at_and_lock_version();
        """,
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


def create_goal_items_table(engine: Engine) -> None:
    statements = [
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_item_status') THEN
            CREATE TYPE goal_item_status AS ENUM ('ACTIVE', 'COMPLETED', 'DROPPED');
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_item_source') THEN
            CREATE TYPE goal_item_source AS ENUM ('MANUAL', 'LEGACY_TEXTAREA');
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_progress_mode') THEN
            CREATE TYPE goal_progress_mode AS ENUM ('MANUAL', 'AUTO_STATUS', 'AUTO_TIME');
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_calc_source') THEN
            CREATE TYPE goal_calc_source AS ENUM ('TASKS', 'METRICS', 'TASKS_AND_METRICS');
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_target_scope') THEN
            CREATE TYPE goal_target_scope AS ENUM ('PERIOD', 'DAY');
          END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_target_operator') THEN
            CREATE TYPE goal_target_operator AS ENUM ('GTE', 'LTE');
          END IF;
        END $$;
        """,
        """
        CREATE TABLE IF NOT EXISTS goal_items (
            goal_item_id BIGSERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id),

            goal_set_id BIGINT NOT NULL,
            goal_theme_id BIGINT NOT NULL,

            title TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',

            status goal_item_status NOT NULL DEFAULT 'ACTIVE',
            progress_percent NUMERIC NULL,
            progress_mode goal_progress_mode NOT NULL DEFAULT 'MANUAL',
            calc_source goal_calc_source NOT NULL DEFAULT 'TASKS',
            target_scope goal_target_scope NOT NULL DEFAULT 'PERIOD',
            target_operator goal_target_operator NOT NULL DEFAULT 'GTE',
            target_minutes NUMERIC NULL,
            weight NUMERIC NOT NULL DEFAULT 1,

            category_id BIGINT NULL,
            subcategory TEXT NULL,
            subcategory_norm TEXT GENERATED ALWAYS AS (
                CASE
                    WHEN subcategory IS NULL OR btrim(subcategory) = '' THEN NULL
                    ELSE lower(btrim(subcategory))
                END
            ) STORED,

            activity TEXT NULL,
            activity_norm TEXT GENERATED ALWAYS AS (
                CASE
                    WHEN activity IS NULL OR btrim(activity) = '' THEN NULL
                    ELSE lower(btrim(activity))
                END
            ) STORED,

            source goal_item_source NOT NULL DEFAULT 'MANUAL',
            order_index INT NOT NULL DEFAULT 0,

            completed_at TIMESTAMPTZ NULL,
            dropped_at TIMESTAMPTZ NULL,
            archived_at TIMESTAMPTZ NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            lock_version INT NOT NULL DEFAULT 1,

            CONSTRAINT ck_goal_items_title_nonempty CHECK (btrim(title) <> ''),
            CONSTRAINT ck_goal_items_progress_range CHECK (
                progress_percent IS NULL OR (progress_percent >= 0 AND progress_percent <= 100)
            ),
            CONSTRAINT ck_goal_items_target_minutes_nonnegative CHECK (
                target_minutes IS NULL OR target_minutes >= 0
            ),
            CONSTRAINT ck_goal_items_weight_positive CHECK (weight > 0),
            CONSTRAINT ck_goal_items_status_timestamps CHECK (
                (status = 'ACTIVE' AND completed_at IS NULL AND dropped_at IS NULL)
                OR (status = 'COMPLETED' AND completed_at IS NOT NULL AND dropped_at IS NULL)
                OR (status = 'DROPPED' AND dropped_at IS NOT NULL AND completed_at IS NULL)
            ),
            CONSTRAINT fk_goal_items_goal_set_user
                FOREIGN KEY (goal_set_id, user_id)
                REFERENCES goal_sets (goal_set_id, user_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_goal_items_goal_theme_user
                FOREIGN KEY (goal_theme_id, user_id)
                REFERENCES goal_themes (goal_theme_id, user_id),
            CONSTRAINT fk_goal_items_user_category
                FOREIGN KEY (user_id, category_id)
                REFERENCES user_categories (user_id, category_id)
                ON DELETE SET NULL
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_goal_items_item_user
        ON goal_items (goal_item_id, user_id);
        """,
        """
        ALTER TABLE goal_items
        ADD COLUMN IF NOT EXISTS progress_mode goal_progress_mode NOT NULL DEFAULT 'MANUAL';
        """,
        """
        ALTER TABLE goal_items
        ADD COLUMN IF NOT EXISTS calc_source goal_calc_source NOT NULL DEFAULT 'TASKS';
        """,
        """
        ALTER TABLE goal_items
        ADD COLUMN IF NOT EXISTS target_scope goal_target_scope NOT NULL DEFAULT 'PERIOD';
        """,
        """
        ALTER TABLE goal_items
        ADD COLUMN IF NOT EXISTS target_operator goal_target_operator NOT NULL DEFAULT 'GTE';
        """,
        """
        ALTER TABLE goal_items
        ADD COLUMN IF NOT EXISTS target_minutes NUMERIC NULL;
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_items_active_by_scope
        ON goal_items (user_id, goal_set_id, goal_theme_id, archived_at, order_index, goal_item_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_items_status
        ON goal_items (user_id, status, archived_at);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_items_category_match
        ON goal_items (user_id, category_id, subcategory_norm, activity_norm)
        WHERE archived_at IS NULL;
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_items_progress_config
        ON goal_items (user_id, progress_mode, calc_source, target_scope, target_operator)
        WHERE archived_at IS NULL;
        """,
        """
        DROP TRIGGER IF EXISTS trg_goal_items_audit ON goal_items;
        """,
        """
        CREATE TRIGGER trg_goal_items_audit
        BEFORE UPDATE ON goal_items
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at_and_lock_version();
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def create_user_goal_preferences_table(engine: Engine) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS user_goal_preferences (
            user_id UUID PRIMARY KEY
                REFERENCES users(user_id) ON DELETE CASCADE,
            auto_calculate_progress BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_user_goal_preferences_auto_calc
        ON user_goal_preferences (auto_calculate_progress);
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def create_goal_item_targets_table(engine: Engine) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS goal_item_targets (
            goal_item_target_id BIGSERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id),
            goal_item_id BIGINT NOT NULL,

            label TEXT NOT NULL DEFAULT 'Target',
            metric_key TEXT NULL,
            target_value NUMERIC NOT NULL,
            current_value NUMERIC NULL,
            unit TEXT NULL,
            due_date DATE NULL,
            archived_at TIMESTAMPTZ NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            lock_version INT NOT NULL DEFAULT 1,

            CONSTRAINT ck_goal_item_targets_label_nonempty CHECK (btrim(label) <> ''),
            CONSTRAINT fk_goal_item_targets_goal_item
                FOREIGN KEY (goal_item_id, user_id)
                REFERENCES goal_items(goal_item_id, user_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_goal_item_targets_metric
                FOREIGN KEY (user_id, metric_key)
                REFERENCES metric_definitions(user_id, metric_key)
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_item_targets_goal_item
        ON goal_item_targets (goal_item_id, archived_at, due_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_item_targets_user_due
        ON goal_item_targets (user_id, due_date, archived_at);
        """,
        """
        DROP TRIGGER IF EXISTS trg_goal_item_targets_audit ON goal_item_targets;
        """,
        """
        CREATE TRIGGER trg_goal_item_targets_audit
        BEFORE UPDATE ON goal_item_targets
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at_and_lock_version();
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def create_goal_item_events_table(engine: Engine) -> None:
    statements = [
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goal_item_event_type') THEN
            CREATE TYPE goal_item_event_type AS ENUM (
                'CREATED',
                'UPDATED',
                'STATUS_CHANGED',
                'PROGRESS_CHANGED',
                'TARGET_CHANGED',
                'NOTE_ADDED',
                'ARCHIVED',
                'MIGRATED'
            );
          END IF;
        END $$;
        """,
        """
        CREATE TABLE IF NOT EXISTS goal_item_events (
            goal_item_event_id BIGSERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id),
            goal_item_id BIGINT NOT NULL,

            event_type goal_item_event_type NOT NULL,
            event_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            actor_user_id UUID NULL REFERENCES users(user_id),
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            note TEXT NOT NULL DEFAULT '',

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT fk_goal_item_events_goal_item
                FOREIGN KEY (goal_item_id, user_id)
                REFERENCES goal_items(goal_item_id, user_id)
                ON DELETE CASCADE
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_item_events_goal_item
        ON goal_item_events (goal_item_id, event_at DESC);
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_goal_item_events_user_event
        ON goal_item_events (user_id, event_at DESC);
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


# *************** DAILY REFLECTION ***************

# ----- CREATE DAILY REFLECTION TABLE -----
def create_daily_reflections_table(engine: Engine) -> None:
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


def init_db() -> None:
    engine = load_sql_engine()
    create_row_audit_trigger_function(engine)

    # Main Structure
    create_users_table(engine)
    create_user_categories(engine)

    # Tasks
    create_task_data_table(engine)

    # Daily Metrics
    create_metric_definitions_table(engine)
    create_daily_metric_values_table(engine)

    # Goals
    create_goal_themes_table(engine)
    create_goal_sets_table(engine)
    create_goal_set_items_table(engine)
    create_goal_items_table(engine)
    create_user_goal_preferences_table(engine)
    create_goal_item_targets_table(engine)
    create_goal_item_events_table(engine)

    # Daily reflections
    create_daily_reflections_table(engine)
