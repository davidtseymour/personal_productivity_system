from dash import Input, Output, html
import dash_bootstrap_components as dbc

from src.layout.pages.log_time import create_task_form
from src.layout.pages.daily_metrics import create_daily_metrics
from src.layout.pages.daily_review import create_daily_review
from src.layout.pages.goals import create_goals

from src.layout.pages.daily_summary import create_daily_summary_page
from src.layout.pages.weekly_summary import create_weekly_summary_page
from src.layout.pages.patterns_trends import create_trends_page


def register_layout_callbacks(app):
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        Input("user-id","data")
    )
    def render_page_content(pathname,user_id):
        # Tracking
        if pathname in ("/", "/log_time"): # default log_time
            return create_task_form(user_id)
        if pathname == "/daily_metrics":
            return html.Div(create_daily_metrics())  # pass user_id if needed
        if pathname == "/daily_reflection":
            return create_daily_review()
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
            return html.H2("Placeholder")

        #Page not found
        return dbc.Container(
            html.H4("404: Page not found"),
            className="p-4",
        )