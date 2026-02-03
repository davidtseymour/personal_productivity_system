import dash_bootstrap_components as dbc
from dash import dcc, html

from src.data_access.db import get_first_user_id
from src.layout.navigation import create_left_navigation, create_right_sidebar
from src.layout.overlays import generate_delete_modal, generate_edit_task_offcanvas


def create_layout() -> dbc.Container:
    return dbc.Container(
        [
            dcc.Store(id="edit-task-inputs", data={}),
            dcc.Store(id="log-task-inputs", data={}),
            dcc.Store(id="date-range-store", data="btn-1"),  # TODO: ensure consistent naming
            dcc.Store(id="task-nav-update-store", data={}),
            dcc.Store(id="last-update", data={}),
            # NOTE: This triggers a DB call at layout creation time.
            # Consider setting this via a callback on first load.
            dcc.Store(id="user-id", data=get_first_user_id()),

            generate_delete_modal(),
            generate_edit_task_offcanvas(),
            dcc.Location(id="url"),

            dbc.Row(
                [
                    # LEFT (fixed width)
                    dbc.Col(
                        html.Div(
                            create_left_navigation(),
                            className="h-100 d-flex flex-column",
                            style={"width": "240px"},
                        ),
                        width="auto",
                        className="bg-light border-end h-100",
                    ),

                    # CENTER (fluid)
                    dbc.Col(
                        dbc.Container(
                            html.Div(id="page-content"),
                            className="p-4 h-100",
                            fluid=True,
                        ),
                        className="h-100",
                    ),

                    # RIGHT (fixed width)
                    dbc.Col(
                        html.Div(
                            create_right_sidebar(),
                            className="h-100 d-flex flex-column",
                            style={"width": "320px"},
                        ),
                        width="auto",
                        className="p-2 h-100",
                    ),
                ],
                className="g-0 h-100",
            ),
        ],
        fluid=True,
        className="p-0 vh-100 d-flex flex-column",
        style={"height": "100vh"},
    )
