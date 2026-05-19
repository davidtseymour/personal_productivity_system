from datetime import date, timedelta

from dash import Dash, Input, Output, State, ctx, html
from dash.exceptions import PreventUpdate

from src.data_access.db import load_category_id_to_name
from src.data_access.daily_summary import load_timeline_tasks_for_date
from src.helpers.general import fmt_h_m
from src.logic.pages.daily_summary import (
    df_to_daily_html_table,
    get_subcategory_df_for_date,
    make_stacked_subcategory_fig,
)
from src.logic.pages.daily_summary_timeline import build_timeline_figure


def _should_skip_last_update(
    last_update: dict | None,
    selected_date: str,
    user_id: str,
    triggered_id: dict | str | None,
) -> bool:
    if triggered_id != "last-update":
        return False
    if not isinstance(last_update, dict):
        return False

    event_user = last_update.get("user_id")
    event_date = last_update.get("date")

    if event_user and event_user != user_id:
        return True
    if event_date and event_date != selected_date:
        return True
    return False


def register_daily_summary_callbacks(app: Dash) -> None:
    page = "daily-summary"

    @app.callback(
        Output({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_daily_summary_date(_prev_clicks, _next_clicks, selected_date):
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

    @app.callback(
        Output({"page": page, "name": "subcategory-graph", "type": "graph"}, "figure"),
        Output({"page": page, "name": "subcategory-table", "type": "table"}, "children"),
        Output({"page": page, "name": "timeline-graph", "type": "graph"}, "figure"),
        Input({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input("user-id", "data"),
        Input("last-update", "data"),
        prevent_initial_call=True,
    )
    def update_daily_summary(selected_date, user_id, last_update):
        if not user_id or not selected_date:
            raise PreventUpdate
        if _should_skip_last_update(last_update, selected_date, user_id, ctx.triggered_id):
            raise PreventUpdate

        combined = get_subcategory_df_for_date(user_id, selected_date)
        task_rows = load_timeline_tasks_for_date(user_id, selected_date)
        category_order = list(load_category_id_to_name(user_id).values())
        table = df_to_daily_html_table(combined, fmt_h_m)

        return (
            make_stacked_subcategory_fig(combined),
            (table if table is not None else html.Div()),
            build_timeline_figure(task_rows, selected_date, category_order=category_order),
        )
