from datetime import date

from dash import dcc, html
import dash_bootstrap_components as dbc

from src.data_access.db import load_category_id_to_name
from src.data_access.daily_summary import load_timeline_tasks_for_date
from src.helpers.general import fmt_h_m
from src.layout.shared_components.components import date_cycler_row
from src.logic.pages.daily_summary import (
    df_to_daily_html_table,
    get_subcategory_df_for_date,
    make_stacked_subcategory_fig,
)
from src.logic.pages.daily_summary_timeline import build_timeline_figure


def create_daily_summary_page(user_id: str) -> dbc.Container:
    """Create the daily summary page for a given user."""
    page = "daily-summary"
    selected_date = date.today().isoformat()
    combined = get_subcategory_df_for_date(user_id, selected_date)
    task_rows = load_timeline_tasks_for_date(user_id, selected_date)
    category_order = list(load_category_id_to_name(user_id).values())

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Daily Summary")), className="mb-2"),
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
            dbc.Row([dbc.Col(html.Hr(), width=12)], className="mt-2"),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            dcc.Graph(
                                figure=build_timeline_figure(
                                    task_rows,
                                    selected_date,
                                    category_order=category_order,
                                ),
                                config={"displayModeBar": False},
                                className="daily-summary-timeline-graph",
                                id={"page": page, "name": "timeline-graph", "type": "graph"},
                            ),
                            className="daily-summary-timeline-scroll",
                        ),
                        width=12,
                    ),
                ],
            ),
        ],
        fluid=True,
        className="p-0",
    )
