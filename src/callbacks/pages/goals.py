from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dash import Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate

from src.data_access.goals import (
    get_or_create_goal_theme, get_goals_themes, get_goal_set_item_text, save_goal_set_item_text
)
from src.layout.toasts import toast, update_toast, hide_toast
from src.logic.pages.goals import compute_period_start, get_goal_set_id_for_offset, ensure_goal_set_id_for_save


def _anchor_now_for_date(selected_date: str | None, tz: str = "America/New_York") -> datetime:
    try:
        selected = date.fromisoformat(selected_date) if selected_date else date.today()
    except (TypeError, ValueError):
        selected = date.today()
    # Midday avoids edge cases around timezone/day rollover.
    return datetime.combine(selected, time(hour=12), tzinfo=ZoneInfo(tz))


def _goal_progress_labels(selected_date: str | None) -> tuple[str, str, str]:
    anchor_now_dt = _anchor_now_for_date(selected_date)
    selected = anchor_now_dt.date()

    qtr_start = compute_period_start("QTR", offset=0, now_dt=anchor_now_dt)
    next_qtr_start = compute_period_start("QTR", offset=1, now_dt=anchor_now_dt)
    qtr_day = (selected - qtr_start).days + 1
    qtr_total = (next_qtr_start - qtr_start).days

    month_start = compute_period_start("MONTH", offset=0, now_dt=anchor_now_dt)
    next_month_start = compute_period_start("MONTH", offset=1, now_dt=anchor_now_dt)
    month_day = (selected - month_start).days + 1
    month_total = (next_month_start - month_start).days

    week_start = compute_period_start("WEEK", offset=0, now_dt=anchor_now_dt)
    next_week_start = compute_period_start("WEEK", offset=1, now_dt=anchor_now_dt)
    week_day = (selected - week_start).days + 1
    week_total = (next_week_start - week_start).days

    def _with_progress(label_text: str, day_index: int, day_total: int):
        return [
            html.Span(label_text),
            html.Span(
                f"day {day_index}/{day_total}",
                className="text-muted",
                style={"fontWeight": "400"},
            ),
        ]

    return (
        _with_progress("This quarter's goals", qtr_day, qtr_total),
        _with_progress("This month's goals", month_day, month_total),
        _with_progress("Selected week's goals", week_day, week_total),
    )


def register_goals_callbacks(app: Dash) -> None:
    @app.callback(
        Output({"page": "goals", "name": "quarter-goals-label", "type": "label"}, "children"),
        Output({"page": "goals", "name": "month-goals-label", "type": "label"}, "children"),
        Output({"page": "goals", "name": "week-goals-label", "type": "label"}, "children"),
        Input({"page": "goals", "name": "date", "type": "date-input"}, "value"),
    )
    def update_goal_progress_labels(selected_date):
        return _goal_progress_labels(selected_date)

    @app.callback(
        Output({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        Input({"page": "goals", "name": "prev-week", "type": "button"}, "n_clicks"),
        Input({"page": "goals", "name": "next-week", "type": "button"}, "n_clicks"),
        State({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_goals_date(_prev_clicks, _next_clicks, selected_date):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            base_date = date.fromisoformat(selected_date) if selected_date else date.today()
        except (TypeError, ValueError):
            base_date = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-week":
            return (base_date - timedelta(days=7)).isoformat()
        if source_name == "next-week":
            return (base_date + timedelta(days=7)).isoformat()

        raise PreventUpdate

    @app.callback(
        Output({"page": "goals", "name": "add-theme-modal", "type": "modal"}, "is_open"),
        Output({"page": "goals", "name": "new-theme-name", "type": "input"}, "value"),
        Output({"page": "goals", "name": "new-theme-error", "type": "alert"}, "is_open"),
        Output({"page": "goals", "name": "new-theme-error", "type": "alert"}, "children"),
        Output({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "options"),
        Output({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "value"),
        Output({"page": "goals", "name": "goals", "type": "toast"}, "is_open"),
        Output({"page": "goals", "name": "goals", "type": "toast"}, "children"),
        Output({"page": "goals", "name": "goals", "type": "toast"}, "icon"),
        [
            Input({"page": "goals", "name": "open-add-goal-theme", "type": "button"}, "n_clicks"),
            Input({"page": "goals", "name": "cancel-add-theme", "type": "button"}, "n_clicks"),
            Input({"page": "goals", "name": "save-add-theme", "type": "button"}, "n_clicks"),
        ],
        [
            State({"page": "goals", "name": "add-theme-modal", "type": "modal"}, "is_open"),
            State({"page": "goals", "name": "new-theme-name", "type": "input"}, "value"),
            State("user-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_add_goal_theme(n_open, n_cancel, n_save, is_open, theme_name, user_id):
        triggered_id = ctx.triggered_id
        if triggered_id is None:
            raise PreventUpdate

        # --- OPEN ---
        if isinstance(triggered_id, dict) and triggered_id.get("name") == "open-add-goal-theme":
            # open modal, clear input + error, no dropdown change yet
            return True, "", False, "", no_update, no_update, False, no_update, no_update

        # --- CANCEL ---
        if isinstance(triggered_id, dict) and triggered_id.get("name") == "cancel-add-theme":
            # close modal, clear input + error
            return False, "", False, "", no_update, no_update, False, no_update, no_update

        # --- SAVE ---
        if isinstance(triggered_id, dict) and triggered_id.get("name") == "save-add-theme":
            if not user_id:
                # should never happen, but keep modal open and show error
                return (
                    True,
                    theme_name or "",
                    True,
                    "No user selected. Cannot save theme.",
                    no_update,
                    no_update,
                    False,
                    no_update,
                    no_update,
                )

            name = (theme_name or "").strip()
            if not name:
                return True, "", True, "Theme name is required.", no_update, no_update, False, no_update, no_update

            try:
                theme_id, created_new = get_or_create_goal_theme(name, user_id)

                # refresh dropdown options and select the new/existing theme
                options = get_goals_themes(user_id)

                # toast text/icon (match your toast system if you want)
                if created_new:
                    t = toast("GOAL_THEME_ADDED")
                else:
                    t = toast("GOAL_THEME_EXISTS")

                return (
                    False,  # close modal
                    "",  # clear input
                    False, "",  # hide error
                    options,  # refresh dropdown
                    theme_id,  # set selection
                    *update_toast(t)  # open toast + children + icon
                )

            except Exception as e:
                # keep modal open and show error
                return True, name, True, f"Could not add theme: {e}", no_update, no_update, False, no_update, no_update

        raise PreventUpdate

    @app.callback(
        Output("goals-last-saved-store", "data"),
        Output({"page": "goals", "name": "three-month-goals", "type": "textarea"}, "value"),
        Output({"page": "goals", "name": "one-month-goals", "type": "textarea"}, "value"),
        Output({"page": "goals", "name": "this-weeks-goals", "type": "textarea"}, "value"),
        Output({"page": "goals", "name": "last-weeks-goals", "type": "textarea"},"value"),
        Output({"page": "goals", "name": "save-goals", "type": "toast"}, "is_open"),
        Output({"page": "goals", "name": "save-goals", "type": "toast"}, "children"),
        Output({"page": "goals", "name": "save-goals", "type": "toast"}, "icon"),
        Input({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "value"),
        Input({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        Input({"page": "goals", "name": "update-goals", "type": "button"}, "n_clicks"),
        State("user-id", "data"),
        State("goals-last-saved-store", "data"),
        State({"page": "goals", "name": "three-month-goals", "type": "textarea"},"value"),
        State({"page": "goals", "name": "one-month-goals", "type": "textarea"},'value'),
        State({"page": "goals", "name": "this-weeks-goals", "type": "textarea"}, "value"),
        prevent_initial_call=True,
    )
    def goals_load_save(
        goal_theme_id,
        selected_date,
        n_clicks,
        user_id,
        goals_last_saved,
        current_quarter_text,
        current_month_text,
        current_week_text,
    ):
        if not user_id:
            raise PreventUpdate

        triggered = ctx.triggered_id
        goals_last_saved = goals_last_saved or {}
        anchor_now_dt = _anchor_now_for_date(selected_date)

        # Clear if no theme selected
        if goal_theme_id is None:
            return {}, "", "", "", "", *hide_toast()

        # -------------------------
        # LOAD (theme dropdown changed)
        # -------------------------
        if isinstance(triggered, dict) and (
            triggered.get("name") == "goal-theme" or triggered.get("type") == "date-input"
        ):
            week_goal_set_id, week_start = get_goal_set_id_for_offset(
                str(user_id),
                "WEEK",
                offset=0,
                now_dt=anchor_now_dt,
            )
            week_text = get_goal_set_item_text(goal_set_id=week_goal_set_id, goal_theme_id=int(goal_theme_id))

            last_week_goal_set_id, last_week_start = get_goal_set_id_for_offset(
                str(user_id),
                "WEEK",
                offset=-1,
                now_dt=anchor_now_dt,
            )
            last_week_text = get_goal_set_item_text(goal_set_id=last_week_goal_set_id, goal_theme_id=int(goal_theme_id))

            month_goal_set_id, month_start = get_goal_set_id_for_offset(
                str(user_id),
                "MONTH",
                offset=0,
                now_dt=anchor_now_dt,
            )
            month_text = get_goal_set_item_text(goal_set_id=month_goal_set_id, goal_theme_id=int(goal_theme_id))

            quarter_goal_set_id, quarter_start = get_goal_set_id_for_offset(
                str(user_id),
                "QTR",
                offset=0,
                now_dt=anchor_now_dt,
            )
            quarter_text = get_goal_set_item_text(goal_set_id=quarter_goal_set_id, goal_theme_id=int(goal_theme_id))

            store = {
                "week": {
                    "horizon": "WEEK",
                    "offset":0,
                    "text": week_text or "",
                },

                "week_minus_1": {
                    "horizon": "WEEK",
                    "offset": -1,
                    "text": last_week_text or "",
                },

                "month": {
                    "horizon": "MONTH",
                    "offset": 0,
                    "text": month_text or "",
                },

                "quarter": {
                    "horizon": "QTR",
                    "offset": 0,
                    "text": quarter_text or "",
                },
            }

            return store, (quarter_text or ""),(month_text or ""),(week_text or ""), (last_week_text or ""), *hide_toast()

        # -------------------------
        # SAVE (update-goals clicked)
        # -------------------------
        if isinstance(triggered, dict) and triggered.get("name") == "update-goals":


            quarter_text = current_quarter_text or ""
            saved_quarter_text = (goals_last_saved.get("quarter") or {}).get("text") or ""
            if quarter_text != saved_quarter_text:
                save_id_qtr = ensure_goal_set_id_for_save(
                    user_id= user_id,
                    horizon='QTR',
                    now_dt=anchor_now_dt,
                )

                save_goal_set_item_text(
                    goal_set_id=int(save_id_qtr),
                    goal_theme_id=int(goal_theme_id),
                    detail_text=quarter_text,
                )

            month_text = current_month_text or ""
            saved_month_text = (goals_last_saved.get("month") or {}).get("text") or ""
            if month_text != saved_month_text:
                save_id_month = ensure_goal_set_id_for_save(
                    user_id=user_id,
                    horizon='MONTH',
                    now_dt=anchor_now_dt,
                )
                save_goal_set_item_text(
                    goal_set_id=int(save_id_month),
                    goal_theme_id=int(goal_theme_id),
                    detail_text=month_text,
                )


            week_text = current_week_text or ""
            saved_week_text = (goals_last_saved.get("week") or {}).get("text") or ""
            if week_text != saved_week_text:
                save_id_week = ensure_goal_set_id_for_save(
                    user_id=user_id,
                    horizon="WEEK",
                    offset=0,
                    now_dt=anchor_now_dt,
                )
                save_goal_set_item_text(
                    goal_set_id=save_id_week,
                    goal_theme_id=int(goal_theme_id),
                    detail_text=week_text,
                )
            saved_last_week_text = (goals_last_saved.get("week_minus_1") or {}).get("text") or ""

            # Update store baseline to what we just saved
            store = {
                "week": {
                    "horizon": "WEEK",
                    "offset": 0,
                    "text": week_text or "",
                },

                "week_minus_1": {
                    "horizon": "WEEK",
                    "offset": -1,
                    "text": saved_last_week_text,
                },

                "month": {
                    "horizon": "MONTH",
                    "offset": 0,
                    "text": month_text or "",
                },

                "quarter": {
                    "horizon": "QTR",
                    "offset": 0,
                    "text": quarter_text or "",
                },
            }

            return store, no_update, no_update, no_update, no_update, *update_toast(toast("GOALS_SAVED"))

        raise PreventUpdate
