from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.helpers.general import fmt_h_m
from src.layout.shared_components.components import date_controlled_row
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
            dbc.Row(
                [
                    date_controlled_row(page, selected_date, className="mb-0"),
                    dbc.Col(
                        [
                            dbc.Button(
                                html.I(className="bi bi-chevron-left", style={"fontSize": "1.2rem"}),
                                id={"page": page, "name": "prev-day", "type": "button"},
                                color="light",
                                size="sm",
                                className="rounded-circle me-2",
                                style={
                                    "width": "32px",
                                    "height": "32px",
                                    "padding": "0",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                },
                                n_clicks=0,
                            ),
                            dbc.Button(
                                html.I(className="bi bi-chevron-right", style={"fontSize": "1.2rem"}),
                                id={"page": page, "name": "next-day", "type": "button"},
                                color="light",
                                size="sm",
                                className="rounded-circle",
                                style={
                                    "width": "32px",
                                    "height": "32px",
                                    "padding": "0",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                },
                                n_clicks=0,
                            ),
                            dbc.Tooltip(
                                "Go to previous day",
                                target={"page": page, "name": "prev-day", "type": "button"},
                                placement="top",
                            ),
                            dbc.Tooltip(
                                "Go to next day",
                                target={"page": page, "name": "next-day", "type": "button"},
                                placement="top",
                            ),
                        ],
                        width="auto",
                        className="d-flex align-items-center",
                    ),
                ],
                className="g-2 align-items-center mb-2",
            ),
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
