from src.config.app_defaults import DEFAULT_CATEGORIES
from src.data_access.db_setup_users import create_user, upsert_user_categories


def init_new_user(
    username: str,
    display_name: str,
    categories: list[str] = DEFAULT_CATEGORIES,
) -> dict:
    """
    High-level entry point: creates a new user and inserts their
    initial categories.

    Parameters
    ----------
    username : str
    display_name : str
    categories : list[str]
        Category names to create. Defaults to DEFAULT_CATEGORIES.

    Returns
    -------
    dict with user_id, username, display_name, is_active, created_at
    """

    user = create_user(username, display_name)

    if user is None:
        return None

    upsert_user_categories(user["user_id"], categories)

    return user