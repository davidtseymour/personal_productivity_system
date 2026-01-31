import dash_bootstrap_components as dbc
from dash import dcc, html

from src.data_access.db import get_users
from src.helpers.general import fmt_h_m
from src.layout.common_components import create_toast


def get_dcc_options():
    users = get_users()  # {user_id: display_name}
    return [{"label": name, "value": user_id} for user_id, name in users.items()]


def create_left_navigation():
    """Left sidebar navigation (vertical)"""
    return html.Div(
        [
            # TOP
            html.Div(
                [
                    html.Div("Tracking", className="text-muted fw-semibold"),
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="bi bi-clock me-2"), "Log Time"],
                                href="/log_time",
                                active="exact",
                                className="py-2",
                            ),
                            dbc.NavLink(
                                [html.I(className="bi bi-activity me-2"), "Daily Metrics"],
                                href="/daily_metrics",
                                active="exact",
                                className="py-2",
                            ),
                            dbc.NavLink(
                                [html.I(className="bi bi-clipboard-check me-2"), "Daily Reflection"],
                                href="/daily_reflection",
                                active="exact",
                                className="py-2",
                            ),
                            dbc.NavLink(
                                [html.I(className="bi bi-signpost-2 me-2"), "Goals"],
                                href="/goals",
                                active="exact",
                                className="py-2",
                            ),
                        ],
                        vertical=True,
                        className="flex-column",
                    ),
                    html.Div("Analytics", className="text-muted fw-semibold mt-3"),
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="bi bi-sun me-2"), "Daily Summary"],
                                href="/daily_summary",
                                active="exact",
                                className="py-2",
                            ),
                            dbc.NavLink(
                                [html.I(className="bi bi-calendar-week me-2"), "Weekly Summary"],
                                href="/weekly_summary",
                                active="exact",
                                className="py-2",
                            ),
                            dbc.NavLink(
                                [html.I(className="bi bi-graph-up me-2"), "Patterns & Trends"],
                                href="/patterns_trends",
                                active="exact",
                                className="py-2",
                            ),
                        ],
                        vertical=True,
                        className="flex-column",
                    ),
                ]
            ),

            # BOTTOM (push down)
            html.Div(
                [
                    dcc.Dropdown(
                        id={"page": "nav", "name": "users", "type": "dropdown"},
                        options=get_dcc_options(),
                        placeholder="Select user...",
                        value=None,  # set via callback on first load
                        className="mb-2 sidebar-dropup",
                    ),
                    dbc.NavLink(
                        [html.I(className="bi bi-gear-fill me-2"), "Settings"],
                        href="/settings",
                        active="exact",
                        className="py-2",
                    ),
                ],
                className="mt-auto",
            ),
        ],
        className="h-100 d-flex flex-column p-3",
    )


def create_right_sidebar():
    return html.Div(
        [
            dbc.Card(
                dbc.CardBody(create_daily_summary_component()),
                id="card-daily-summary",
                className="mb-2 rounded-3 shadow-sm",
                style={"display": "none"},
            ),
            dbc.Card(
                dbc.CardBody(create_recent_tasks_component()),
                id="card-recent-tasks",
                className="rounded-3 shadow-sm",
                style={"display": "none"},
            ),
        ],
        className="h-100",
    )


def create_daily_summary_component():
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        "Today's Summary",
                        className="fw-semibold fs-5 text-center mb-2",
                    ),
                    dbc.Button(
                        html.I(className="bi bi-arrow-repeat fs-5"),
                        id="update-summary-tasks",
                        color="secondary",
                        outline=True,
                        size="sm",
                        className=(
                            "btn-icon text-body "
                            "btn-icon position-absolute top-50 end-0 translate-middle-y"
                        ),
                        title="Refresh summary",
                    ),
                ],
                className="position-relative",
            ),
            html.Div(id="today-summary-sidebar"),
        ]
    )


def create_recent_tasks_component():
    return html.Div(
        [
            html.Div("Recent Tasks", className="fw-semibold fs-5 text-center mb-2"),
            html.Div(id="today-recent-tasks-sidebar"),
            create_toast("nav", "delete-task", "Delete Task", icon="success"),
            create_toast("nav", "edit-task", "Edit Task", icon="success"),
        ]
    )


def render_today_summary_table(payload):
    if payload is None:
        return html.Small("No user id.", className="text-muted")

    status = payload.get("status")
    if status in {"empty", "no_productive"}:
        return html.Small("No productive time logged today.", className="text-muted")

    rows = payload.get("rows", [])
    total = payload.get("total", 0)
    screen_minutes = payload.get("screen_minutes")

    body_rows = [
        html.Tr([html.Td(r["category"]), html.Td(fmt_h_m(r["minutes"]))]) for r in rows
    ]
    body_rows.append(
        html.Tr(
            [html.Td(html.Strong("Total")), html.Td(html.Strong(fmt_h_m(total)))],
            style={"borderTop": "1px solid #ddd"},
        )
    )

    if screen_minutes is not None:
        body_rows.append(
            html.Tr(
                [html.Td(html.Strong(" ")), html.Td(html.Strong(" "))],
                style={"borderTop": "1px solid #ddd", "color": "red"},
            )
        )
        body_rows.append(
            html.Tr(
                [
                    html.Td(html.Strong("Screen"), style={"color": "#b00020"}),
                    html.Td(html.Strong(fmt_h_m(screen_minutes)), style={"color": "#b00020"}),
                ],
                style={"borderTop": "1px solid #ddd"},
            )
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Category"), html.Th("Time")])),
            html.Tbody(body_rows),
        ],
        bordered=False,
        striped=False,
        size="sm",
        className="mt-2",
    )
