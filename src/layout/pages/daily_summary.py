from datetime import date

from dash import dcc, html
import dash_bootstrap_components as dbc

from src.helpers.general import fmt_h_m
from src.layout.shared_components.components import date_cycler_row
from src.logic.pages.daily_summary import (
    df_to_daily_html_table,
    get_subcategory_df_for_date,
    make_stacked_subcategory_fig,
)


def create_daily_summary_page(user_id: str) -> dbc.Container:
    """Create the daily summary page for a given user."""
    page = "daily-summary"
    selected_date = date.today().isoformat()
    combined = get_subcategory_df_for_date(user_id, selected_date)

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Summary"), className="mb-2")),
            date_cycler_row(
                page,
                selected_date,
                prev_name="prev-day",
                next_name="next-day",
                prev_tooltip="Go to previous day",
                next_tooltip="Go to next day",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            figure=make_stacked_subcategory_fig(combined),
                            style={"height": "20.625rem"},
                            config={"displayModeBar": False},
                            id={"page": page, "name": "subcategory-graph", "type": "graph"},
                        ),
                        width=True,
                    ),
                    dbc.Col(
                        html.Div(
                            df_to_daily_html_table(combined, fmt_h_m),
                            className="d-flex flex-column",
                            style={"width": "20rem", "height": "20.625rem"},
                            id={"page": page, "name": "subcategory-table", "type": "table"},
                        ),
                        width="auto",
                    ),
                ]
            ),
            # TODO: add the timeline bar when ready
        ],
        fluid=True,
        className="p-0",
    )
