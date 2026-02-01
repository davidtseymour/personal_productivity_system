TOASTS = {
    # LOG TIME TOASTS
    "LOG_TIME_SAVED": {"status": "success", "message": "Saved entry"},
    "TIME_UPDATED": {"status": "info", "message": "Updated entry"},

    # DAILY METRICS
    "METRICS_SAVED": {"status": "success", "message": "Metrics saved"},

    # DAILY REVIEW
    "DAILY_REVIEW_SAVED": {"status": "success", "message": "Saved for {day}."},
    "DAILY_REVIEW_SAVE_FAILED": {"status": "danger", "message": "Save failed."},
    "DAILY_REVIEW_LOAD_FAILED": {"status": "danger", "message": "Cannot load review."},

    # DELETE TIME
    "TIME_ENTRY_DELETED": {"status": "info", "message": "Deleted entry."},

    # GOALS
    "GOAL_THEME_ADDED": {"message":"Goal theme added","status":"success"},
    "GOAL_THEME_EXISTS":{"message":"Goal theme already exists","status":"info"},
    "GOALS_SAVED":{"message": "Goals saved.", "status": "success"},

    # GENERAL
    "VALIDATION_ERROR": {"status": "danger", "message": "Validation error"},
    "TIME_CONSISTENCY_ERROR": {"status": "danger", "message": "Time Consistency Error"},
    "CATEGORY_ERROR": {"status": "danger", "message": "Category Consistency Error"},
}


def toast(key: str, **details) -> dict:
    """
    Returns a standardized toast dict:
      {"status": <bootstrap-status>, "message": <formatted string>}
    """
    spec = TOASTS.get(key) or {}
    status = spec.get("status", "info")
    msg_template = spec.get("message", "Action completed.")

    # Safe formatting: don't crash if caller forgets a format field
    try:
        message = msg_template.format(**details)
    except KeyError:
        message = msg_template

    return {"status": status, "message": message}


def update_toast(t_dict) -> tuple:
    """Returns (is_open, children, icon)."""
    return True, t_dict.get("message"), t_dict.get("status", "info")


def hide_toast() -> tuple:
    """Closes the toast."""
    return False, None, None
