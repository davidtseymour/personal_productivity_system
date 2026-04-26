from datetime import datetime

from dash import Dash, Input, Output, ctx, html, no_update
import dash_bootstrap_components as dbc

from src.layout.pages.daily_metrics import create_daily_metrics
from src.layout.pages.daily_task_log import create_daily_task_log_page
from src.layout.pages.daily_reflection import create_daily_reflection
from src.layout.pages.daily_summary import create_daily_summary_page
from src.layout.pages.goals import create_goals
from src.layout.pages.log_time import create_task_form
from src.layout.pages.patterns_trends import create_trends_page
from src.layout.pages.settings import create_settings_page
from src.layout.pages.weekly_summary import create_weekly_summary_page


def register_layout_callbacks(app: Dash) -> None:
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        Input("user-id","data")
    )
    def render_page_content(pathname,user_id):
        # Tracking
        if pathname in ("/", "/log_time"): # default log_time
            return create_task_form(user_id)
        if pathname in ("/daily_task_log", "/daily_tasks"):
            return create_daily_task_log_page(user_id)
        if pathname == "/daily_metrics":
            return html.Div(create_daily_metrics(user_id))  # pass user_id if needed
        if pathname == "/daily_reflection":
            return create_daily_reflection()
        if pathname == "/goals":
            return create_goals(user_id)

        # Analytics
        if pathname == "/daily_summary":
            return create_daily_summary_page(user_id)
        if pathname == "/weekly_summary":
            return create_weekly_summary_page(user_id)
        if pathname == "/patterns_trends":
            return create_trends_page(user_id)

        # Settings
        if pathname == "/settings":
            return create_settings_page(user_id)

        #Page not found
        return dbc.Container(
            html.H4("404: Page not found"),
            className="p-4",
        )

    @app.callback(
        Output("last-update", "data"),
        Output("task-nav-update-store", "data"),
        [
            Input("last-update-edit", "data"),
            Input("last-update-delete", "data"),
            Input("last-update-log-time", "data"),
            Input("last-update-daily-metrics", "data"),
        ],
        prevent_initial_call=True,
    )
    def bump_master_refresh(*_):
        # always change -> guarantees downstream refresh triggers
        refresh_token = datetime.now().isoformat()
        if ctx.triggered_id in {"last-update-edit", "last-update-delete", "last-update-log-time"}:
            return refresh_token, refresh_token
        return refresh_token, no_update
