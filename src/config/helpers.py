# TODO: Multi-user: replace local data/ storage with DB-backed storage + per-user storage

from pathlib import Path

def create_config_dic() -> dict:
    """
    Create and return a config dictionary.
    Ensures the project subdirectory 'data/daily_review' exists.
    """
    review_dir = Path("data") / "daily_review"
    review_dir.mkdir(parents=True, exist_ok=True)

    config_dic = {"daily_review_dir": str(review_dir.resolve())}
    return config_dic



