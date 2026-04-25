# Todo: Option to edit/add daily metrics
# Todo: Option to edit/add categories.

from typing import Any

from dash import html
import dash_bootstrap_components as dbc

from src.data_access.settings import (
    fetch_user_categories_sort_order_rows,
    fetch_user_metrics_for_settings,
)
from src.helpers.general import get_category_layout


def create_settings_page(user_id: str | None = None) -> html.Div:
    page = "settings"

    return dbc.Container(
        [
            dbc.Row(dbc.Col(html.H5("Settings"), width=12), className="mb-2"),
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



def edit_categories_content(
    user_id: str,
    draft_rows: list[dict[str, Any]] | None = None,
    edited_rows: dict[str, Any] | None = None,
) -> list[Any]:
    rows = fetch_user_categories_sort_order_rows(user_id)
    draft_rows = draft_rows or []
    edited_rows = edited_rows or {}
    table_header = html.Thead(
        html.Tr(
            [
                html.Th("Category Name"),
                html.Th("Is Active", style={"width": "110px"}, className="text-center align-middle"),
                html.Th("Actions", style={"width": "90px"}, className="text-center align-middle"),
            ]
        )
    )
    table_body = html.Tbody(
        (
            [
            html.Tr(
                [
                    (
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=(edited_rows.get(str(int(r["category_id"])), {}) or {}).get("category_name", r["category_name"]),
                                debounce=True,
                                invalid=bool((edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_duplicate")),
                                id={
                                    "page": "settings-modal",
                                    "name": "category-edit-name",
                                    "type": "input",
                                    "category_id": int(r["category_id"]),
                                },
                            )
                        )
                        if (edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_editing")
                        else html.Td(
                            html.Div(
                                [
                                    html.Span(
                                        (edited_rows.get(str(int(r["category_id"])), {}) or {}).get("category_name", r["category_name"]),
                                        id={
                                            "page": "settings-modal",
                                            "name": "category-name",
                                            "type": "text",
                                            "category_id": int(r["category_id"]),
                                        },
                                        className="d-inline-block py-1 me-2",
                                    ),
                                ],
                                className="d-flex align-items-center",
                            )
                        )
                    ),
                    (
                        html.Td(
                            html.Div(
                                dbc.Button(
                                    html.I(
                                        className=(
                                            "bi bi-check2-circle text-success"
                                            if bool((edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_active", r["is_active"]))
                                            else "bi bi-circle text-muted"
                                        )
                                    ),
                                    id={
                                        "page": "settings-modal",
                                        "name": "category-edit-active-toggle",
                                        "type": "button",
                                        "category_id": int(r["category_id"]),
                                    },
                                    className="icon-action-btn",
                                    title="Toggle active",
                                ),
                                className="d-flex justify-content-center align-items-center h-100",
                            ),
                            className="text-center align-middle",
                            style={"width": "110px"},
                        )
                        if (edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_editing")
                        else html.Td(
                            html.Div(
                                html.I(
                                    className=(
                                        "bi bi-check2-circle text-success"
                                        if bool((edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_active", r["is_active"]))
                                        else "bi bi-circle text-muted"
                                    ),
                                    id={
                                        "page": "settings-modal",
                                        "name": "category-active",
                                        "type": "icon",
                                        "category_id": int(r["category_id"]),
                                    },
                                ),
                                className="d-flex justify-content-center align-items-center h-100",
                            ),
                            className="text-center align-middle",
                            style={"width": "110px"},
                        )
                    ),
                    (
                        html.Td(
                            html.Div(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-check-lg"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "category-edit-save",
                                            "type": "button",
                                            "category_id": int(r["category_id"]),
                                        },
                                        className="icon-action-btn me-1",
                                        title="Save",
                                        n_clicks=0,
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-x-lg"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "category-edit-undo",
                                            "type": "button",
                                            "category_id": int(r["category_id"]),
                                        },
                                        className="icon-action-btn",
                                        title="Undo",
                                        n_clicks=0,
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "90px"},
                        )
                        if (edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_editing")
                        else html.Td(
                            html.Div(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-pencil"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "category-edit",
                                            "type": "button",
                                            "category_id": int(r["category_id"]),
                                        },
                                        className="icon-action-btn settings-row-action me-1",
                                        title="Edit",
                                        n_clicks=0,
                                    ),
                                    (
                                        dbc.Button(
                                            html.I(className="bi bi-x-lg"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "category-edit-undo",
                                                "type": "button",
                                                "category_id": int(r["category_id"]),
                                            },
                                            className="icon-action-btn settings-row-action",
                                            title="Undo staged change",
                                            n_clicks=0,
                                        )
                                        if (edited_rows.get(str(int(r["category_id"])), {}) or {}).get("is_staged")
                                        else None
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "90px"},
                        )
                    ),
                ]
            )
            for r in rows
            ]
            +
            [
                html.Tr(
                    [
                        html.Td(
                            html.Div(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-chevron-up"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-draft-move-up",
                                            "type": "button",
                                            "row_id": d["row_id"],
                                        },
                                        className="icon-action-btn me-1",
                                        title="Move up",
                                        n_clicks=0,
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-chevron-down"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-draft-move-down",
                                            "type": "button",
                                            "row_id": d["row_id"],
                                        },
                                        className="icon-action-btn",
                                        title="Move down",
                                        n_clicks=0,
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "68px"},
                        ),
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=d.get("category_name", ""),
                                placeholder="Category name",
                                debounce=True,
                                disabled=bool(d.get("is_staged")),
                                invalid=bool(d.get("is_duplicate")),
                                id={
                                    "page": "settings-modal",
                                    "name": "category-draft-name",
                                    "type": "input",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Div(
                                [
                                    html.Span(d.get("category_name", ""), className="d-inline-block py-1 me-2"),
                                ],
                                className="d-flex align-items-center",
                            )
                        ),
                        html.Td(
                            html.Div(
                                dbc.Button(
                                    html.I(
                                        className=(
                                            "bi bi-check2-circle text-success"
                                            if bool(d.get("is_active", True))
                                            else "bi bi-circle text-muted"
                                        )
                                    ),
                                    disabled=bool(d.get("is_staged")),
                                    id={
                                        "page": "settings-modal",
                                        "name": "category-draft-active-toggle",
                                        "type": "button",
                                        "row_id": d["row_id"],
                                    },
                                    className="icon-action-btn",
                                    title="Toggle active",
                                ),
                                className="d-flex justify-content-center align-items-center h-100",
                            ),
                            className="text-center align-middle",
                            style={"width": "110px"},
                        ),
                        html.Td(
                            html.Div(
                                [
                                    (
                                        dbc.Button(
                                            html.I(className="bi bi-check-lg"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "category-draft-save",
                                                "type": "button",
                                                "row_id": d["row_id"],
                                            },
                                            className="icon-action-btn me-1",
                                            title="Save",
                                            n_clicks=0,
                                        )
                                        if not d.get("is_staged")
                                        else dbc.Button(
                                            html.I(className="bi bi-pencil"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "category-draft-edit",
                                                "type": "button",
                                                "row_id": d["row_id"],
                                            },
                                            className="icon-action-btn me-1",
                                            title="Re-edit",
                                            n_clicks=0,
                                        )
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-x-lg"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "category-draft-delete",
                                            "type": "button",
                                            "row_id": d["row_id"],
                                        },
                                        className="icon-action-btn",
                                        title="Delete",
                                        n_clicks=0,
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "90px"},
                        ),
                    ]
                )
                for d in draft_rows
            ]
        )
    )

    return [
            dbc.Row(dbc.Col(html.H5("Edit Categories"), width=12), className="mb-2"),
            dbc.Table(
                [table_header, table_body],
                bordered=False,
                hover=True,
                responsive=True,
                striped=False,
                size="sm",
                className="settings-minimal-table mb-1",
            ),
            html.Div(
                [
                    dbc.Button(
                        html.I(
                            className="bi bi-plus-lg",
                            style={"fontSize": "1.2rem"},
                        ),
                        id={
                            "page": "settings-modal",
                            "name": "category-add",
                            "type": "button",
                        },
                        color="light",
                        size="sm",
                        className="rounded-circle",
                        style={
                            "width": "28px",
                            "height": "28px",
                            "padding": "0",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                        n_clicks=0,
                    ),
                    dbc.Tooltip(
                        "Add category",
                        target={
                            "page": "settings-modal",
                            "name": "category-add",
                            "type": "button",
                        },
                        placement="right",
                    ),
                ],
                className="d-flex justify-content-start",
                style={"paddingLeft": "0.75rem", "marginTop": "0.2rem"},
            ),
    ]


def edit_metrics_content(
    user_id: str,
    draft_rows: list[dict[str, Any]] | None = None,
    edited_rows: dict[str, Any] | None = None,
    row_order: list[str] | None = None,
) -> list[Any]:
    rows = fetch_user_metrics_for_settings(user_id)
    draft_rows = draft_rows or []
    edited_rows = edited_rows or {}
    row_order = row_order or []

    row_by_key = {str(r["metric_key"]): r for r in rows}
    ordered_keys = [k for k in row_order if k in row_by_key]
    ordered_keys.extend([k for k in row_by_key.keys() if k not in ordered_keys])
    rows = [row_by_key[k] for k in ordered_keys]
    category_options = [{"label": "Unassigned", "value": ""}] + [
        {"label": str(opt["label"]), "value": str(opt["value"])}
        for opt in get_category_layout(user_id, include_all_option=False)
    ]
    category_label_by_value = {str(opt["value"]): str(opt["label"]) for opt in category_options}

    table_header = html.Thead(
        html.Tr(
            [
                html.Th("", style={"width": "68px"}, className="text-center align-middle"),
                html.Th("Display Name"),
                html.Th("Unit"),
                html.Th("Is Duration", style={"width": "110px"}, className="text-center align-middle"),
                html.Th("Value Type"),
                html.Th("Category"),
                html.Th("Subcategory"),
                html.Th("Activity"),
                html.Th("To Minutes Factor"),
                html.Th("Metric Key"),
                html.Th("Actions", style={"width": "90px"}, className="text-center align-middle"),
            ]
        )
    )
    table_body = html.Tbody(
        (
            [
                html.Tr(
                    [
                        html.Td(
                            html.Div(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-chevron-up"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-move-up",
                                            "type": "button",
                                            "metric_key": r["metric_key"],
                                        },
                                        className="icon-action-btn me-1",
                                        title="Move up",
                                        n_clicks=0,
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-chevron-down"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-move-down",
                                            "type": "button",
                                            "metric_key": r["metric_key"],
                                        },
                                        className="icon-action-btn",
                                        title="Move down",
                                        n_clicks=0,
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "68px"},
                        ),
                        (
                            html.Td(
                                dbc.Input(
                                    type="text",
                                    value=(edited_rows.get(r["metric_key"], {}) or {}).get("display_name", r["display_name"]),
                                    debounce=True,
                                    invalid=bool((edited_rows.get(r["metric_key"], {}) or {}).get("is_invalid")),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-edit-display-name",
                                        "type": "input",
                                        "metric_key": r["metric_key"],
                                    },
                                )
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Span(
                                    (edited_rows.get(r["metric_key"], {}) or {}).get("display_name", r["display_name"]),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-display-name",
                                        "type": "text",
                                        "metric_key": r["metric_key"],
                                    },
                                    className="d-inline-block py-1",
                                )
                            )
                        ),
                        (
                            html.Td(
                                dbc.Input(
                                    type="text",
                                    value=(edited_rows.get(r["metric_key"], {}) or {}).get("unit", r["unit"]),
                                    debounce=True,
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-edit-unit",
                                        "type": "input",
                                        "metric_key": r["metric_key"],
                                    },
                                )
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Span(
                                    (edited_rows.get(r["metric_key"], {}) or {}).get("unit", r["unit"]),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-unit",
                                        "type": "text",
                                        "metric_key": r["metric_key"],
                                    },
                                    className="d-inline-block py-1",
                                )
                            )
                        ),
                        (
                            html.Td(
                                html.Div(
                                    dbc.Button(
                                        html.I(
                                            className=(
                                                "bi bi-check2-circle text-success"
                                                if bool((edited_rows.get(r["metric_key"], {}) or {}).get("is_duration", r["is_duration"]))
                                                else "bi bi-circle text-muted"
                                            )
                                        ),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-edit-is-duration-toggle",
                                            "type": "button",
                                            "metric_key": r["metric_key"],
                                        },
                                        className="icon-action-btn",
                                        title="Toggle duration",
                                    ),
                                    className="d-flex justify-content-center align-items-center h-100",
                                ),
                                className="text-center align-middle",
                                style={"width": "110px"},
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Div(
                                    html.I(
                                        className=(
                                            "bi bi-check2-circle text-success"
                                            if bool((edited_rows.get(r["metric_key"], {}) or {}).get("is_duration", r["is_duration"]))
                                            else "bi bi-circle text-muted"
                                        ),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-is-duration",
                                            "type": "icon",
                                            "metric_key": r["metric_key"],
                                        },
                                    ),
                                    className="d-flex justify-content-center align-items-center h-100",
                                ),
                                className="text-center align-middle",
                                style={"width": "110px"},
                            )
                        ),
                        html.Td(
                            html.Span(
                                (edited_rows.get(r["metric_key"], {}) or {}).get("value_type", r["value_type"]),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-value-type",
                                    "type": "text",
                                    "metric_key": r["metric_key"],
                                },
                                className="d-inline-block py-1",
                            )
                        ),
                        (
                            html.Td(
                                dbc.Select(
                                    options=category_options,
                                    value=(edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "category_id",
                                        "" if r["category_id"] is None else str(r["category_id"]),
                                    ),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-edit-category-id",
                                        "type": "dropdown",
                                        "metric_key": r["metric_key"],
                                    },
                                )
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                [
                                    html.Span(
                                        (edited_rows.get(r["metric_key"], {}) or {}).get(
                                            "category_name",
                                            "" if r["category_name"] is None else r["category_name"],
                                        ),
                                        className="d-inline-block py-1",
                                    ),
                                    html.Span(
                                        (edited_rows.get(r["metric_key"], {}) or {}).get(
                                            "category_id",
                                            "" if r["category_id"] is None else str(r["category_id"]),
                                        ),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-category-id",
                                            "type": "text",
                                            "metric_key": r["metric_key"],
                                        },
                                        className="d-none",
                                    ),
                                ]
                            )
                        ),
                        (
                            html.Td(
                                dbc.Input(
                                    type="text",
                                    value=(edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "subcategory",
                                        "" if r["subcategory"] is None else r["subcategory"],
                                    ),
                                    debounce=True,
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-edit-subcategory",
                                        "type": "input",
                                        "metric_key": r["metric_key"],
                                    },
                                )
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Span(
                                    (edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "subcategory",
                                        "" if r["subcategory"] is None else r["subcategory"],
                                    ),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-subcategory",
                                        "type": "text",
                                        "metric_key": r["metric_key"],
                                    },
                                    className="d-inline-block py-1",
                                )
                            )
                        ),
                        (
                            html.Td(
                                dbc.Input(
                                    type="text",
                                    value=(edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "activity",
                                        "" if r["activity"] is None else r["activity"],
                                    ),
                                    debounce=True,
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-edit-activity",
                                        "type": "input",
                                        "metric_key": r["metric_key"],
                                    },
                                )
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Span(
                                    (edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "activity",
                                        "" if r["activity"] is None else r["activity"],
                                    ),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-activity",
                                        "type": "text",
                                        "metric_key": r["metric_key"],
                                    },
                                    className="d-inline-block py-1",
                                )
                            )
                        ),
                        (
                            html.Td(
                                dbc.Input(
                                    type="text",
                                    value=(edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "to_minutes_factor",
                                        "" if r["to_minutes_factor"] is None else str(r["to_minutes_factor"]),
                                    ),
                                    debounce=True,
                                    invalid=bool((edited_rows.get(r["metric_key"], {}) or {}).get("is_invalid_to_minutes_factor")),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-edit-to-minutes-factor",
                                        "type": "input",
                                        "metric_key": r["metric_key"],
                                    },
                                )
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Span(
                                    (edited_rows.get(r["metric_key"], {}) or {}).get(
                                        "to_minutes_factor",
                                        "" if r["to_minutes_factor"] is None else str(r["to_minutes_factor"]),
                                    ),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-to-minutes-factor",
                                        "type": "text",
                                        "metric_key": r["metric_key"],
                                    },
                                    className="d-inline-block py-1",
                                )
                            )
                        ),
                        html.Td(
                            html.Span(
                                r["metric_key"],
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-key",
                                    "type": "text",
                                    "metric_key": r["metric_key"],
                                },
                                className="d-inline-block py-1 text-muted",
                            )
                        ),
                        (
                            html.Td(
                                html.Div(
                                    [
                                        dbc.Button(
                                            html.I(className="bi bi-check-lg"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "metric-edit-save",
                                                "type": "button",
                                                "metric_key": r["metric_key"],
                                            },
                                            className="icon-action-btn me-1",
                                            title="Save",
                                            n_clicks=0,
                                        ),
                                        dbc.Button(
                                            html.I(className="bi bi-x-lg"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "metric-edit-undo",
                                                "type": "button",
                                                "metric_key": r["metric_key"],
                                            },
                                            className="icon-action-btn",
                                            title="Undo",
                                            n_clicks=0,
                                        ),
                                    ],
                                    className="d-flex justify-content-center align-items-center",
                                ),
                                className="text-center align-middle",
                                style={"width": "90px"},
                            )
                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_editing")
                            else html.Td(
                                html.Div(
                                    [
                                        dbc.Button(
                                            html.I(className="bi bi-pencil"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "metric-edit",
                                                "type": "button",
                                                "metric_key": r["metric_key"],
                                            },
                                            className="icon-action-btn settings-row-action me-1",
                                            title="Edit",
                                            n_clicks=0,
                                        ),
                                        (
                                            dbc.Button(
                                                html.I(className="bi bi-x-lg"),
                                                id={
                                                    "page": "settings-modal",
                                                    "name": "metric-edit-undo",
                                                    "type": "button",
                                                    "metric_key": r["metric_key"],
                                                },
                                                className="icon-action-btn settings-row-action",
                                                title="Undo staged change",
                                                n_clicks=0,
                                            )
                                            if (edited_rows.get(r["metric_key"], {}) or {}).get("is_staged")
                                            else None
                                        ),
                                    ],
                                    className="d-flex justify-content-center align-items-center",
                                ),
                                className="text-center align-middle",
                                style={"width": "90px"},
                            )
                        ),
                    ]
                )
                for r in rows
            ]
            +
            [
                html.Tr(
                    [
                        html.Td(
                            html.Div(
                                [
                                    dbc.Button(
                                        html.I(className="bi bi-chevron-up"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-draft-move-up",
                                            "type": "button",
                                            "row_id": d["row_id"],
                                        },
                                        className="icon-action-btn me-1",
                                        title="Move up",
                                        n_clicks=0,
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-chevron-down"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-draft-move-down",
                                            "type": "button",
                                            "row_id": d["row_id"],
                                        },
                                        className="icon-action-btn",
                                        title="Move down",
                                        n_clicks=0,
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "68px"},
                        ),
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=d.get("display_name", ""),
                                placeholder="Metric display name",
                                debounce=True,
                                disabled=bool(d.get("is_staged")),
                                invalid=bool(d.get("is_invalid")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-display-name",
                                    "type": "input",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Span(d.get("display_name", ""), className="d-inline-block py-1")
                        ),
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=d.get("unit", ""),
                                placeholder="Unit",
                                debounce=True,
                                disabled=bool(d.get("is_staged")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-unit",
                                    "type": "input",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Span(d.get("unit", ""), className="d-inline-block py-1")
                        ),
                        html.Td(
                            html.Div(
                                dbc.Button(
                                    html.I(
                                        className=(
                                            "bi bi-check2-circle text-success"
                                            if bool(d.get("is_duration", False))
                                            else "bi bi-circle text-muted"
                                        )
                                    ),
                                    disabled=bool(d.get("is_staged")),
                                    id={
                                        "page": "settings-modal",
                                        "name": "metric-draft-is-duration-toggle",
                                        "type": "button",
                                        "row_id": d["row_id"],
                                    },
                                    className="icon-action-btn",
                                    title="Toggle duration",
                                ),
                                className="d-flex justify-content-center align-items-center h-100",
                            ),
                            className="text-center align-middle",
                            style={"width": "110px"},
                        ),
                        html.Td(
                            dbc.Select(
                                options=[
                                    {"label": "int", "value": "int"},
                                    {"label": "double", "value": "double"},
                                ],
                                value=d.get("value_type", "double"),
                                disabled=bool(d.get("is_staged")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-value-type",
                                    "type": "dropdown",
                                    "row_id": d["row_id"],
                                },
                            )
                        ),
                        html.Td(
                            dbc.Select(
                                options=category_options,
                                value=d.get("category_id", ""),
                                disabled=bool(d.get("is_staged")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-category-id",
                                    "type": "dropdown",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Span(
                                d.get("category_name", category_label_by_value.get(str(d.get("category_id", "")), "")),
                                className="d-inline-block py-1",
                            )
                        ),
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=d.get("subcategory", ""),
                                placeholder="Subcategory",
                                debounce=True,
                                disabled=bool(d.get("is_staged")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-subcategory",
                                    "type": "input",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Span(d.get("subcategory", ""), className="d-inline-block py-1")
                        ),
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=d.get("activity", ""),
                                placeholder="Activity",
                                debounce=True,
                                disabled=bool(d.get("is_staged")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-activity",
                                    "type": "input",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Span(d.get("activity", ""), className="d-inline-block py-1")
                        ),
                        html.Td(
                            dbc.Input(
                                type="text",
                                value=d.get("to_minutes_factor", ""),
                                placeholder="Optional",
                                debounce=True,
                                disabled=bool(d.get("is_staged")),
                                invalid=bool(d.get("is_invalid_to_minutes_factor")),
                                id={
                                    "page": "settings-modal",
                                    "name": "metric-draft-to-minutes-factor",
                                    "type": "input",
                                    "row_id": d["row_id"],
                                },
                            ) if not d.get("is_staged")
                            else html.Span(d.get("to_minutes_factor", ""), className="d-inline-block py-1")
                        ),
                        html.Td(html.Span("New", className="d-inline-block py-1 text-muted")),
                        html.Td(
                            html.Div(
                                [
                                    (
                                        dbc.Button(
                                            html.I(className="bi bi-check-lg"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "metric-draft-save",
                                                "type": "button",
                                                "row_id": d["row_id"],
                                            },
                                            className="icon-action-btn me-1",
                                            title="Save",
                                            n_clicks=0,
                                        )
                                        if not d.get("is_staged")
                                        else dbc.Button(
                                            html.I(className="bi bi-pencil"),
                                            id={
                                                "page": "settings-modal",
                                                "name": "metric-draft-edit",
                                                "type": "button",
                                                "row_id": d["row_id"],
                                            },
                                            className="icon-action-btn me-1",
                                            title="Re-edit",
                                            n_clicks=0,
                                        )
                                    ),
                                    dbc.Button(
                                        html.I(className="bi bi-x-lg"),
                                        id={
                                            "page": "settings-modal",
                                            "name": "metric-draft-delete",
                                            "type": "button",
                                            "row_id": d["row_id"],
                                        },
                                        className="icon-action-btn",
                                        title="Delete",
                                        n_clicks=0,
                                    ),
                                ],
                                className="d-flex justify-content-center align-items-center",
                            ),
                            className="text-center align-middle",
                            style={"width": "90px"},
                        ),
                    ]
                )
                for d in draft_rows
            ]
        )
    )

    return [
            dbc.Row(dbc.Col(html.H5("Edit Metrics"), width=12), className="mb-2"),
            dbc.Table(
                [table_header, table_body],
                bordered=False,
                hover=True,
                responsive=True,
                striped=False,
                size="sm",
                className="settings-minimal-table mb-1",
            ),
            html.Div(
                [
                    dbc.Button(
                        html.I(
                            className="bi bi-plus-lg",
                            style={"fontSize": "1.2rem"},
                        ),
                        id={
                            "page": "settings-modal",
                            "name": "metric-add",
                            "type": "button",
                        },
                        color="light",
                        size="sm",
                        className="rounded-circle",
                        style={
                            "width": "28px",
                            "height": "28px",
                            "padding": "0",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                        n_clicks=0,
                    ),
                    dbc.Tooltip(
                        "Add metric",
                        target={
                            "page": "settings-modal",
                            "name": "metric-add",
                            "type": "button",
                        },
                        placement="right",
                    ),
                ],
                className="d-flex justify-content-start",
                style={"paddingLeft": "0.75rem", "marginTop": "0.2rem"},
            ),
    ]
