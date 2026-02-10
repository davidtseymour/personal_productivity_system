from sqlalchemy import text
from src.data_access.db import load_sql_engine

def legacy_add_user_db(username: str, display_name: str):
    engine = load_sql_engine()

    with engine.begin() as conn:
        conn.execute(
            text("""
                 INSERT INTO users (username, display_name)
                 VALUES (:username, :display_name) ON CONFLICT (username) DO
                 UPDATE SET
                     display_name = EXCLUDED.display_name,
                     is_active = TRUE;
                 """),
            {"username": username, "display_name": display_name},
        )
