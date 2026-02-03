# callbacks/today_summary.py

import dash_bootstrap_components as dbc
from dash import html, Input, Output, State, ctx, no_update, ALL
from dash.exceptions import PreventUpdate

from src.callbacks.overlays import populate_edit_task_modal
from src.data_access.db import delete_task_sql, load_task_db, update_task
from src.helpers.update_events import build_update_event
from src.helpers.task_adapters import task_row_to_form_initial
from src.layout.navigation import render_today_summary_table
from src.layout.toasts import toast, update_toast, hide_toast
from src.logic.navigation import get_recent_tasks, get_today_summary_payload


def _triggered_all_value(input_index: int, triggered_id: dict) -> int:
    """
    Returns the value of the ALL Input corresponding to triggered_id.
    input_index: which Input in the callback decorator is the ALL one (0 here).
    """
    items = ctx.inputs_list[input_index]  # list of {id, property, value} dicts
    for item in items:
        if item.get("id") == triggered_id:
            return item.get("value") or 0
    return 0


def render_recent_task(df_recent):

    if df_recent is None or df_recent.empty:
        return html.Div(html.Small("No tasks to display.", className="text-muted"))

    items = []
    for _, row in df_recent.iterrows():
        items.append(
            dbc.ListGroupItem(
                html.Div(
                    [
                        # Left content
                        html.Div(
                            [
                                html.Div(
                                    f"{row['start_at'].strftime('%I:%M %p')} – {row['end_at'].strftime('%I:%M %p')}",
                                    className="small text-muted",
                                ),
                                html.Div(
                                    f"{row['category']} / {row['subcategory']}",
                                    className="fw-semibold small",
                                ),
                                html.Div(
                                    row["activity"],
                                    className="small",
                                ),
                            ],
                            className="flex-grow-1",
                        ),

                        # Right actions (hidden by default)
                        html.Div(
                            [
                                dbc.Button(
                                    html.I(className="bi bi-pencil"),
                                    id={"page":"nav","type": "edit-task", "task_id": row["task_id"]},
                                    className="icon-action-btn row-action",
                                    title="Edit",
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-trash"),
                                    id={"page":"nav","type": "delete-task", "task_id": row["task_id"]},
                                    className="icon-action-btn row-action",
                                    title="Delete",
                                ),
                            ],
                            className="d-flex flex-column align-items-center gap-1",
                        ),
                    ],
                    className="d-flex align-items-center justify-content-between task-row",
                )
            )

        )

    return dbc.ListGroup(items, flush=True)


def register_navigation_callbacks(app):
    @app.callback(
        Output("today-summary-sidebar", "children"),
        Output("today-recent-tasks-sidebar", "children"),
        Output("card-daily-summary", "style"),
        Output("card-recent-tasks", "style"),
        Input("update-summary-tasks", "n_clicks"),
        Input("task-nav-update-store", "data"),
        Input("last-update", "data"),
        Input("user-id", "data"),
    )
    def update_today_summary(n_clicks_update, nav_version, last_update, user_id):
        if not user_id:
            raise PreventUpdate

        # Always rebuild recent tasks when something changes
        recent_tasks_df = get_recent_tasks(user_id=user_id)
        recent_tasks_layout = render_recent_task(recent_tasks_df)

        payload = get_today_summary_payload(user_id)
        summary = render_today_summary_table(payload)

        return summary, recent_tasks_layout, {"display": "block"}, {"display": "block"}


    @app.callback(
        Output({"page": "edit-modal", "name": "edit-task", "type": "toast"}, "is_open"),
        Output({"page": "edit-modal", "name": "edit-task", "type": "toast"}, "children"),
        Output({"page": "edit-modal", "name": "edit-task", "type": "toast"}, "icon"),
        Output("edit-task-modal", "is_open"),
        Output("edit-task-form", "children"),
        Output("edit-task-id", "data"),
        Output("last-update", "data"),
        [
            Input({"page": "nav", "type": "edit-task", "task_id": ALL}, "n_clicks"),
            Input({"page": "edit-modal", "name": "cancel", "type": "button"}, "n_clicks"),
            Input({"page": "edit-modal", "name": "save-task", "type": "button"}, "n_clicks"),
        ],
        [
            State("edit-task-inputs", "data"),  # your {ready_to_save, entries}
            State("edit-task-id", "data"),
            State("user-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_edit_task(n_clicks, n_cancel, n_save, edit_task_inputs, edit_task_id, user_id):
        triggered_id = ctx.triggered_id
        if triggered_id is None:
            raise PreventUpdate

        # Open edit modal from row button
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "edit-task":
            this_clicks = _triggered_all_value(0, triggered_id)
            if this_clicks <= 0:
                raise PreventUpdate

            task_id = triggered_id["task_id"]
            task_db = load_task_db(task_id)
            initial = task_row_to_form_initial(task_db)
            edit_task_layout = populate_edit_task_modal(user_id,initial)

            return *hide_toast(), True, edit_task_layout, task_id, no_update

        # Cancel
        if isinstance(triggered_id, dict) and triggered_id.get("name") == "cancel":
            return *hide_toast(), False, [], None, no_update

        # Save
        if isinstance(triggered_id, dict) and triggered_id.get("name") == "save-task":
            if not edit_task_inputs:
                # draft/validation store missing; keep modal open
                validation_error_t = toast("VALIDATION_ERROR")
                return *update_toast(validation_error_t), no_update, no_update, no_update, no_update

            if edit_task_inputs.get("ready_to_save") and edit_task_id is not None:
                update_task(edit_task_id, edit_task_inputs.get("entries"), user_id)
                updated_t = toast("TIME_UPDATED")
                update_event = build_update_event(
                    event_type="update",
                    entity="task",
                    user_id=user_id,
                    details={"task_id": edit_task_id},
                )
                return *update_toast(updated_t), False, [], None, update_event

            validation_error_t = toast("VALIDATION_ERROR")
            return *update_toast(validation_error_t), no_update, no_update, no_update, no_update

        raise PreventUpdate


    @app.callback(
        Output({"page": "nav", "name": "delete-task", "type": "toast"}, "is_open"),
        Output({"page": "nav", "name": "delete-task", "type": "toast"}, "children"),
        Output({"page": "nav", "name": "delete-task", "type": "toast"}, "icon"),

        Output("delete-confirm-modal", "is_open"),
        Output("pending-delete-task-id", "data"),
        Output("last-update", "data"),
        [
            Input({"page": "nav", "type": "delete-task", "task_id": ALL}, "n_clicks"),
            Input("confirm-delete", "n_clicks"),
            Input("cancel-delete", "n_clicks"),
        ],
        State("pending-delete-task-id", "data"),
        prevent_initial_call=True,
    )
    def delete_modal_controller(delete_clicks, confirm_clicks, cancel_clicks, pending_task_id):
        triggered = ctx.triggered_id
        if triggered is None:
            raise PreventUpdate

        # 1) Trash icon clicked -> open modal and store task_id
        if isinstance(triggered, dict) and triggered.get("type") == "delete-task":
            this_clicks = _triggered_all_value(0, triggered)
            if this_clicks <= 0:
                raise PreventUpdate

            task_id = triggered["task_id"]
            return *hide_toast(), True, task_id, no_update

        # 2) Cancel clicked -> close modal, keep pending id (or clear it)
        if triggered == "cancel-delete":
            return *hide_toast(), False, pending_task_id, no_update  # or: (False, None) to clear

        # 3) Confirm clicked -> delete, close modal, clear pending id
        if triggered == "confirm-delete":
            if pending_task_id is None:
                raise PreventUpdate
            delete_task_sql(pending_task_id)
            t = toast("TIME_ENTRY_DELETED")
            update_event = build_update_event(
                event_type="delete",
                entity="task",
                details={"task_id": pending_task_id},
            )
            return *update_toast(t), False, None, update_event

        raise PreventUpdate


    @app.callback(
        Output("user-id", "data"),
        Input({"page": "nav", "name": "users", "type": "dropdown"},"value")
    )
    def update_user_id_data_store(user_id_value):
        if user_id_value is None:
            raise PreventUpdate
        return user_id_value
