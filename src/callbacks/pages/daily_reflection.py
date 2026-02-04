from datetime import datetime

from dash import Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from src.data_access.daily_reflection import load_daily_reflection, upsert_daily_reflection
from src.layout.toasts import hide_toast


def register_daily_reflection_callbacks(app):
    page = "daily-reflection"

    # ---------- SAVE ----------
    @app.callback(
        Output({"page": page, "type": "toast", "name": "save-reflection"}, "is_open"),
        Output({"page": page, "type": "toast", "name": "save-reflection"}, "children"),
        Output({"page": page, "type": "toast", "name": "save-reflection"}, "icon"),
        Input({"page": page, "name": "submit", "type": "button"}, "n_clicks"),
        State("user-id", "data"),
        State({"page": page, "name": "date", "type": "date-input"}, "value"),
        State({"page": page, "name": "intentionality-score", "type": "input"}, "value"),
        State({"page": page, "name": "accomplishments", "type": "textarea"}, "value"),
        State({"page": page, "name": "what-worked", "type": "textarea"}, "value"),
        State({"page": page, "name": "what-didnt-work", "type": "textarea"}, "value"),
        State({"page": page, "name": "intentions-tomorrow", "type": "textarea"}, "value"),
        prevent_initial_call=True,
    )
    def save_form(
        n_clicks,
        user_id,
        reflection_date,
        score_raw,
        accomplishments,
        what_worked,
        what_didnt_work,
        intentions_tomorrow,
    ):
        if not n_clicks:
            raise PreventUpdate

        if not user_id:
            return True, "Error: Missing user id.", "danger"

        # Validate date
        try:
            datetime.strptime(reflection_date or "", "%Y-%m-%d")
        except (TypeError, ValueError):
            return True, f"Error: Invalid date ({reflection_date}). Expected YYYY-MM-DD.", "danger"

        # Validate score
        intentionality_score = None
        if score_raw not in (None, ""):
            try:
                intentionality_score = int(score_raw)
            except (TypeError, ValueError):
                return True, "Error: Intentionality Score must be a number.", "danger"
            if not (1 <= intentionality_score <= 10):
                return True, "Error: Intentionality Score must be between 1 and 10.", "danger"

        try:
            upsert_daily_reflection(
                user_id=user_id,
                reflection_date=reflection_date,
                intentionality_score=intentionality_score,
                accomplishments=accomplishments or "",
                what_worked=what_worked or "",
                what_didnt_work=what_didnt_work or "",
                intentions_tomorrow=intentions_tomorrow or "",
            )
            return True, f"Saved Daily Reflection for {reflection_date}.", "success"
        except Exception:
            return True, "Error: Failed to save Daily Reflection.", "danger"

    # ---------- LOAD ----------
    @app.callback(
        Output({"page": page, "type": "toast", "name": "load-reflection"}, "is_open"),
        Output({"page": page, "type": "toast", "name": "load-reflection"}, "children"),
        Output({"page": page, "type": "toast", "name": "load-reflection"}, "icon"),
        Output({"page": page, "name": "intentionality-score", "type": "input"}, "value"),
        Output({"page": page, "name": "accomplishments", "type": "textarea"}, "value"),
        Output({"page": page, "name": "what-worked", "type": "textarea"}, "value"),
        Output({"page": page, "name": "what-didnt-work", "type": "textarea"}, "value"),
        Output({"page": page, "name": "intentions-tomorrow", "type": "textarea"}, "value"),
        Input({"page": page, "name": "date", "type": "date-input"}, "value"),
        State("user-id", "data"),
    )
    def load_form(selected_date, user_id):
        if not user_id:
            return *hide_toast(), no_update, no_update, no_update, no_update, no_update

        # Validate date first
        try:
            datetime.strptime(selected_date or "", "%Y-%m-%d")
        except (TypeError, ValueError):
            return *hide_toast(), no_update, no_update, no_update, no_update, no_update

        default_score = ""
        default_text = ""

        try:
            data = load_daily_reflection(user_id=user_id, reflection_date=selected_date)
        except Exception:
            data = None

        if not data:
            return *hide_toast(), default_score, default_text, default_text, default_text, default_text

        return (
            *hide_toast(),
            data.get("intentionality_score") or "",
            data.get("accomplishments", ""),
            data.get("what_worked", ""),
            data.get("what_didnt_work", ""),
            data.get("intentions_tomorrow", ""),
        )
