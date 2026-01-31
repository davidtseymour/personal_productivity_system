from dash import dcc, html
import dash_bootstrap_components as dbc

from src.layout.common_components import create_toast


def generate_delete_modal():
    return html.Div(
        [
            dcc.Store(id="pending-delete-task-id"),
            dbc.Modal(
                [
                    dbc.ModalHeader("Delete task?"),
                    dbc.ModalBody("This action cannot be undone."),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Cancel", id="cancel-delete", color="secondary", outline=True),
                            dbc.Button("Delete", id="confirm-delete", color="danger"),
                        ]
                    ),
                ],
                id="delete-confirm-modal",
                is_open=False,
                centered=True,
            ),
        ]
    )


def generate_edit_task_offcanvas():
    page = "edit-modal"

    return html.Div(
        [
            create_toast(page, "edit-task", "Edit Task", icon="success"),
            dcc.Store(id="edit-task-id"),
            dcc.Store(id="edit-modal-task-data"),
            dbc.Modal(
                [
                    dbc.ModalBody(
                        [
                            html.Div(id="edit-task-form"),
                            html.Div(
                                [
                                    dbc.Button(
                                        "Cancel",
                                        id={"page": page, "name": "cancel", "type": "button"},
                                        color="secondary",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        "Save Task",
                                        id={"page": page, "name": "save-task", "type": "button"},
                                        color="primary",
                                    ),
                                ],
                                className="d-flex justify-content-end",
                            ),
                        ]
                    ),
                ],
                id="edit-task-modal",
                is_open=False,
                size="xl",
                scrollable=True,
                centered=True,
            ),
        ]
    )
