import dash_bootstrap_components as dbc
from dash import dcc, html

from src.helpers.general import fmt_h_m
from src.logic.pages.daily_summary import (
    df_to_daily_html_table,
    get_today_subcategory_df,
    make_stacked_subcategory_fig,
)


def create_daily_summary_page(user_id: str) -> dbc.Container:
    """Create the daily summary page for a given user."""
    page = "daily-summary"
    combined = get_today_subcategory_df(user_id)

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Summary"))),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            figure=make_stacked_subcategory_fig(combined),
                            style={"height": "330px"},
                            config={"displayModeBar": False},
                            id={"page": page, "name": "subcategory-graph", "type": "graph"},
                        ),
                        width=True,
                    ),
                    dbc.Col(
                        html.Div(
                            df_to_daily_html_table(combined, fmt_h_m),
                            className="d-flex flex-column",
                            style={"width": "320px", "height": "330px"},
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
