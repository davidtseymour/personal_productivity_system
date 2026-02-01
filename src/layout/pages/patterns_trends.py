import dash_bootstrap_components as dbc
from dash import dcc, html

from src.data_access.db import get_category_id_to_name
from src.helpers.general import get_category_layout
from src.logic.pages.patterns_trends import get_task_summary_data, plot_cat_from_store, plot_ts


def create_trends_page(user_id):
    # NOTE: These data fetches/figures are computed at layout creation time.
    # If load time becomes an issue, move into callbacks and/or cache results.
    category_dict = get_category_id_to_name(user_id)
    task_summary_agg, category_ts = get_task_summary_data(user_id)

    fig_ts = plot_ts(category_ts, category_dict)

    day_nums = 1  # TODO: wire this as a preset and then as an option
    fig_cat = plot_cat_from_store(task_summary_agg, category_dict, day_nums)

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Patterns & Trends"))),

            # NOTE: dcc.Store is client-side storage (visible in browser DevTools).
            dcc.Store(id="task-summary-store", data=task_summary_agg),
            dcc.Store(id="trends-category-dict-store", data=category_dict),

            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button("Yesterday", id="btn-1", color="primary", outline=True),
                                        dbc.Button("Last 7 Days", id="btn-7", color="primary", outline=True),
                                        dbc.Button("Last 14 Days", id="btn-14", color="primary", outline=True),
                                        dbc.Button("Last 30 Days", id="btn-30", color="primary", outline=True),
                                        dbc.Button("All Time", id="btn-inf", color="primary", outline=True),
                                    ]
                                ),
                                className="mb-3",
                            )
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        dbc.Row(
                            [
                                dbc.Col(dbc.Label("Category", className="mb-0"), width="auto"),
                                dbc.Col(
                                    dbc.Select(
                                        id="category-dropdown",
                                        options=get_category_layout(user_id, include_all_option=True),
                                        value="all",
                                    )
                                ),
                            ],
                            className="align-items-center",
                        ),
                        width=6,
                    ),
                ],
                className="mb-3",
            ),

            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            id="productivity-graph",
                            figure=fig_cat,
                            style={"height": "330px"},
                            config={"staticPlot": True},
                        ),
                        width=12,
                    )
                ]
            ),

            dbc.Row([dbc.Col(html.Hr(), width=12)]),

            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            id="ts-graph",
                            figure=fig_ts,
                            style={"height": "330px"},
                        ),
                        width=12,
                    )
                ]
            ),
        ],
        fluid=True,
        className="p-0",
    )
