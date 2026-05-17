from datetime import date, datetime, timedelta

from dash import Dash, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate

from src.data_access.daily_reflection import load_daily_reflection, upsert_daily_reflection
from src.layout.toasts import hide_toast


def _validate_intentionality_score(score_raw, required: bool) -> tuple[int | None, str | None, bool]:
    score_text = str(score_raw).strip() if score_raw is not None else ""

    if score_text == "":
        if required:
            return None, "Error: Intentionality Score is required.", True
        return None, None, False

    if not score_text.isdigit():
        return None, "Error: Intentionality Score must be a whole number.", True

    intentionality_score = int(score_text)
    if not (1 <= intentionality_score <= 10):
        return None, "Error: Intentionality Score must be between 1 and 10.", True

    return intentionality_score, None, False


def register_daily_reflection_callbacks(app: Dash) -> None:
    page = "daily-reflection"

    @app.callback(
        Output({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_daily_reflection_date(_prev_clicks, _next_clicks, selected_date):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            base_date = date.fromisoformat(selected_date) if selected_date else date.today()
        except (TypeError, ValueError):
            base_date = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-day":
            return (base_date - timedelta(days=1)).isoformat()
        if source_name == "next-day":
            return (base_date + timedelta(days=1)).isoformat()

        raise PreventUpdate

    # ---------- SAVE ----------
    @app.callback(
        Output({"page": page, "type": "toast", "name": "save-reflection"}, "is_open"),
        Output({"page": page, "type": "toast", "name": "save-reflection"}, "children"),
        Output({"page": page, "type": "toast", "name": "save-reflection"}, "icon"),
        Output({"page": page, "name": "intentionality-score", "type": "input"}, "invalid"),
        Input({"page": page, "name": "submit", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "intentionality-score", "type": "input"}, "value"),
        State("user-id", "data"),
        State({"page": page, "name": "date", "type": "date-input"}, "value"),
        State({"page": page, "name": "accomplishments", "type": "textarea"}, "value"),
        State({"page": page, "name": "what-worked", "type": "textarea"}, "value"),
        State({"page": page, "name": "what-didnt-work", "type": "textarea"}, "value"),
        State({"page": page, "name": "intentions-tomorrow", "type": "textarea"}, "value"),
        prevent_initial_call=True,
    )
    def save_form(
        n_clicks,
        score_raw,
        user_id,
        reflection_date,
        accomplishments,
        what_worked,
        what_didnt_work,
        intentions_tomorrow,
    ):
        triggered = ctx.triggered_id

        # Debounced input validation: highlight invalid score without saving.
        if isinstance(triggered, dict) and triggered.get("name") == "intentionality-score":
            _, _, is_invalid = _validate_intentionality_score(score_raw, required=False)
            return no_update, no_update, no_update, is_invalid

        if not n_clicks:
            raise PreventUpdate

        if not user_id:
            return True, "Error: Missing user id.", "danger", no_update

        # Validate date
        try:
            datetime.strptime(reflection_date or "", "%Y-%m-%d")
        except (TypeError, ValueError):
            return True, f"Error: Invalid date ({reflection_date}). Expected YYYY-MM-DD.", "danger", no_update

        intentionality_score, score_error, is_invalid = _validate_intentionality_score(score_raw, required=True)
        if score_error:
            return True, score_error, "danger", is_invalid

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
            return True, f"Saved Daily Reflection for {reflection_date}.", "success", False
        except Exception:
            return True, "Error: Failed to save Daily Reflection.", "danger", no_update

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

        score_value = data.get("intentionality_score")

        return (
            *hide_toast(),
            str(score_value) if score_value is not None else "",
            data.get("accomplishments", ""),
            data.get("what_worked", ""),
            data.get("what_didnt_work", ""),
            data.get("intentions_tomorrow", ""),
        )
