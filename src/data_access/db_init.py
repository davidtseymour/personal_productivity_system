import pandas as pd
from sqlalchemy import text
from src.data_access.db import load_sql_engine, get_user_id, update_metric_definition  # or get_engine




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
    create_daily_reflections_table(engine)