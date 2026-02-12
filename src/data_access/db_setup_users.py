from sqlalchemy import text
from src.data_access.db import load_sql_engine

def create_user(
    username: str,
    display_name: str,
) -> dict | None:
    """
    Insert a new user and return the created record,
    or None if the username already exists.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    username : str – unique login / handle
    display_name : str – human-readable name

    Returns
    -------
    dict with user_id, username, display_name, is_active, created_at
    or None if username already exists
    """
    engine = load_sql_engine()
    stmt = text("""
        INSERT INTO users (username, display_name)
        VALUES (:username, :display_name)
        ON CONFLICT (username) DO NOTHING
        RETURNING user_id, username, display_name, is_active, created_at;
    """)

    with engine.begin() as conn:
        row = conn.execute(
            stmt,
            {"username": username, "display_name": display_name},
        ).mappings().one_or_none()

    if row is None:
        return None

    return dict(row)


def upsert_user_categories(
    user_id: str,
    category_names: list[str],
) -> None:
    """
    Insert new categories or update sort_order on existing ones.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    user_id : str – UUID as string
    category_names : list[str] – ordered list; index becomes sort_order
    """
    engine = load_sql_engine()

    if not category_names:
        return

    rows = [
        {"uid": user_id, "name": name.strip(), "sort": i}
        for i, name in enumerate(category_names)
    ]

    stmt = text("""
        INSERT INTO user_categories (user_id, category_name, sort_order)
        VALUES (:uid, :name, :sort)
        ON CONFLICT (user_id, lower(btrim(category_name)))
        DO UPDATE SET sort_order  = EXCLUDED.sort_order,
                      updated_at  = now();
    """)

    with engine.begin() as conn:
        conn.execute(stmt, rows)