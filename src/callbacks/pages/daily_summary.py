from dash import Input, Output, html
from dash.exceptions import PreventUpdate

from src.helpers.general import fmt_h_m
from src.logic.pages.daily_summary import (
    df_to_daily_html_table,
    get_subcategory_df_for_date,
    make_stacked_subcategory_fig,
)


def register_daily_summary_callbacks(app):
    page = "daily-summary"

    @app.callback(
        Output({"page": page, "name": "subcategory-graph", "type": "graph"}, "figure"),
        Output({"page": page, "name": "subcategory-table", "type": "table"}, "children"),
        Input({"page": page, "name": "date", "type": "date-input"}, "value"),
        Input("user-id", "data"),
        Input("last-update", "data"),
        prevent_initial_call=True,
    )
    def update_daily_summary(selected_date, user_id, _last_update):
        if not user_id or not selected_date:
            raise PreventUpdate

        combined = get_subcategory_df_for_date(user_id, selected_date)
        table = df_to_daily_html_table(combined, fmt_h_m)

        return make_stacked_subcategory_fig(combined), (table if table is not None else html.Div())
