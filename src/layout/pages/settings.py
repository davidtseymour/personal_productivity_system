# Todo: Option to edit/add daily metrics
# Todo: Option to edit/add categories.

from dash import html
import dash_bootstrap_components as dbc


def create_settings_page(user_id=None) -> html.Div:
    page = "settings"

    return dbc.Container(
        [
            html.H5("Settings", className="mb-2"),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label("Edit categories and metrics", className="mb-2"),
                        dbc.Button(
                            "Edit Categories",
                            id={"page": page, "name": "edit-categories", "type": "button"},
                            color="primary",
                            className="w-100 mb-2",
                        ),
                        dbc.Button(
                            "Edit Metrics",
                            id={"page": page, "name": "edit-metrics", "type": "button"},
                            color="primary",
                            className="w-100",
                        )
                        ],
                        width=4,
                    ),
                ],
                className="align-items-center",
            ),
        ],
        fluid=True,
        className="p-0",
    )

