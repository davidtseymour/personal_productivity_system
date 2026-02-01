import dash_bootstrap_components as dbc
from dash import dcc, html
from datetime import date

from src.helpers.general import get_category_layout
from src.layout.common_components import create_toast, labeled_control_row


# IF there are values they should be all be validated, but better to assume that there are issues
# Select function --> dictionary of values
# keep same keys but expand start_at and stop_at into their date time components


def get_default_task_values():
    today = date.today().isoformat()
    return {
        "start_date": today,
        "start_time": "",
        "end_date": today,
        "end_time": "",
        "duration_hours": "",
        "duration_minutes": "",
        "category": "",
        "category_id": "",
        "subcategory": "",
        "activity": "",
        "notes": "",
    }


def normalize_task_values(values=None):
    base = get_default_task_values()
    if values:
        base.update({k: v for k, v in values.items() if v is not None})
    return base


def create_task_inputs(page, user_id, store_data=None, values=None):
    group = "task-input"
    values = normalize_task_values(values)

    return [
        # ---------------------- Start/End Time ----------------------
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Start time"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Input(
                                        id={"page": page, "group": group, "name": "start-date", "type": "input"},
                                        type="date",
                                        value=values["start_date"],
                                    ),
                                    width=6,
                                ),
                                dbc.Col(
                                    dbc.Input(
                                        id={"page": page, "group": group, "name": "start-time", "type": "input"},
                                        type="time",
                                        value=values["start_time"],
                                    ),
                                    width=6,
                                ),
                            ],
                            className="g-3",
                        ),
                    ],
                    width=6,
                ),
                dbc.Col(
                    [
                        dbc.Label("End time"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    dbc.Input(
                                        id={"page": page, "group": group, "name": "end-date", "type": "input"},
                                        type="date",
                                        value=values["end_date"],
                                    ),
                                    width=6,
                                ),
                                dbc.Col(
                                    dbc.Input(
                                        id={"page": page, "group": group, "name": "end-time", "type": "input"},
                                        type="time",
                                        value=values["end_time"],
                                    ),
                                    width=6,
                                ),
                            ],
                            className="g-3",
                        ),
                    ],
                    width=6,
                ),
            ],
            className="mb-3",
        ),

        # ---------------------- Duration ----------------------
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Duration"),
                        html.Div(
                            [
                                dbc.InputGroup(
                                    [
                                        dbc.Input(
                                            id={"page": page, "group": group, "name": "duration-hours", "type": "input"},
                                            type="text",
                                            autoComplete="off",
                                            style={"width": "55px", "textAlign": "right"},
                                            value="", #Intentionally blank for edit
                                        ),
                                        dbc.InputGroupText("h"),
                                    ],
                                    style={"display": "inline-flex", "width": "auto", "marginRight": "20px"},
                                ),
                                dbc.InputGroup(
                                    [
                                        dbc.Input(
                                            id={"page": page, "group": group, "name": "duration-minutes", "type": "input"},
                                            type="text",
                                            autoComplete="off",
                                            style={"width": "55px", "textAlign": "right"},
                                            value="", #Intentionally blank for edit
                                        ),
                                        dbc.InputGroupText("m"),
                                    ],
                                    style={"display": "inline-flex", "width": "auto"},
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center"},
                        ),
                        dbc.FormText(
                            id={"page": page, "name": "duration-warning", "type": "text"},
                            className="text-warning",
                            children="",
                        ),
                    ],
                    width=6,
                ),
            ],
            className="mb-3",
        ),

        # ---------------------- Category / Subcategory ----------------------
        dbc.Row(
            [
                labeled_control_row(
                    "Category",
                    dcc.Dropdown(
                        id={"page": page, "group": group, "name": "task-category", "type": "dropdown"},
                        options=get_category_layout(user_id, include_all_option=False),
                        placeholder="Select category...",
                        value=values["category_id"],
                    ),
                    col_width=6,
                    label_px=110,
                ),
            ]
        ),
        dbc.Row(
            [
                labeled_control_row(
                    "Subcategory",
                    [
                        dbc.Input(
                            id={"page": page, "group": group, "name": "task-subcategory", "type": "input"},
                            type="text",
                            placeholder="Enter subcategory...",
                            list="subcategory-suggestions",  # must be a string for HTML datalist
                            value=values["subcategory"],
                        ),
                        # NOTE: datalist needs a plain string id so the 'list' attribute works correctly
                        # Todo: Update datalist based on db
                        html.Datalist(
                            id="subcategory-suggestions",
                            children=[],
                        ),
                    ],
                    col_width=6,
                    label_px=110,
                ),
            ]
        ),

        # ---------------------- Activity ----------------------
        dbc.Row(
            [
                labeled_control_row(
                    "Activity",
                    dbc.Input(
                        id={"page": page, "group": group, "name": "task-activity", "type": "input"},
                        type="text",
                        placeholder="Enter activity...",
                        value=values["activity"],
                    ),
                    col_width=6,
                    label_px=110,
                ),
            ]
        ),

        # ---------------------- Notes ----------------------
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Notes"),
                        dbc.Textarea(
                            id={"page": page, "group": group, "name": "task-notes", "type": "textarea"},
                            placeholder="Add optional notes...",
                            rows=3,
                            className="mb-3",
                            value=values["notes"],
                        ),
                    ],
                    width=12,
                ),
            ]
        ),
    ]


def create_task_form(user_id):
    page = "log-time"

    return dbc.Form(
        [
            html.H5("Log Time"),
            dbc.Row(
                dbc.Col(
                    [
                        *create_task_inputs(page, user_id),
                    ],
                    width=8,
                ),
            ),

            # ---------------------- Buttons ----------------------
            dbc.Button(
                "Save Task",
                id={"page": page, "name": "save-task", "type": "button"},
                color="primary",
                className="me-2 mb-3",
            ),
            dbc.Button(
                "Clear Task",
                id={"page": page, "name": "clear-task", "type": "button"},
                color="secondary",
                className="me-2 mb-3",
            ),

            # ---------------------- Toast ----------------------
            create_toast(page, "save-task", "Log Time", icon="success"),
        ]
    )
