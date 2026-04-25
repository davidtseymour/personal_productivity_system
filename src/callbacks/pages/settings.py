import uuid

from dash import ALL, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate

from src.data_access.settings import (
    persist_category_settings_changes,
    persist_metric_settings_changes,
)
from src.helpers.general import get_category_layout
from src.layout.pages.settings import edit_categories_content, edit_metrics_content


def _normalize_positive_double(value):
    text = "" if value is None else str(value).strip()
    if text == "":
        return True, ""
    try:
        parsed = float(text)
    except (TypeError, ValueError):
        return False, text
    if parsed <= 0:
        return False, text
    return True, text


def register_settings_callbacks(app):
    @app.callback(
        Output("edit-setting-modal", "is_open"),
        Output("settings-modal-mode", "data"),
        Output("edit-setting-modal", "dialog_style"),
        Output("settings-categories-drafts", "data"),
        Output("settings-categories-edits", "data"),
        Output("settings-metrics-drafts", "data"),
        Output("settings-metrics-edits", "data"),
        Output("settings-metrics-order", "data"),
        Input({"page": "settings", "type": "button", "name": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "cancel", "type": "button"}, "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_settings_modal(n_clicks_vec, n_cancel):
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate

        name = triggered_id.get("name")
        if name in {"edit-categories", "edit-metrics"}:
            value = ctx.triggered[0].get("value")
            if not value:  # None or 0
                raise PreventUpdate

            if name == "edit-categories":
                modal_mode = "categories"
                dialog_style = {"maxWidth": "min(92vw, 1000px)", "width": "92vw"}
                category_drafts = []
                category_edits = {}
                metric_drafts = []
                metric_edits = {}
            if name == "edit-metrics":
                modal_mode = "metrics"
                dialog_style = {"maxWidth": "min(96vw, 1600px)", "width": "96vw"}
                category_drafts = []
                category_edits = {}
                metric_drafts = []
                metric_edits = {}
            return True, modal_mode, dialog_style, category_drafts, category_edits, metric_drafts, metric_edits, []
        if name == "cancel":
            return False, None, {"maxWidth": "min(92vw, 1000px)", "width": "92vw"}, [], {}, [], {}, []

        raise PreventUpdate

    @app.callback(
        Output("edit-setting-modal", "is_open", allow_duplicate=True),
        Output("settings-modal-mode", "data", allow_duplicate=True),
        Output("edit-setting-modal", "dialog_style", allow_duplicate=True),
        Output("settings-categories-drafts", "data", allow_duplicate=True),
        Output("settings-categories-edits", "data", allow_duplicate=True),
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Output("settings-metrics-order", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "save-task", "type": "button"}, "n_clicks"),
        State("settings-modal-mode", "data"),
        State("settings-categories-drafts", "data"),
        State("settings-categories-edits", "data"),
        State("settings-metrics-drafts", "data"),
        State("settings-metrics-edits", "data"),
        State("settings-metrics-order", "data"),
        State("user-id", "data"),
        prevent_initial_call=True,
    )
    def save_settings_modal(
        n_save,
        modal_mode,
        category_drafts,
        category_edits,
        metric_drafts,
        metric_edits,
        metric_order,
        user_id,
    ):
        if not n_save or not user_id or modal_mode not in {"categories", "metrics"}:
            raise PreventUpdate

        if modal_mode == "categories":
            persist_category_settings_changes(
                user_id=user_id,
                category_edits=category_edits,
                category_drafts=category_drafts,
            )
        elif modal_mode == "metrics":
            persist_metric_settings_changes(
                user_id=user_id,
                metric_edits=metric_edits,
                metric_drafts=metric_drafts,
                metric_order=metric_order,
            )
        else:
            raise PreventUpdate

        return False, None, {"maxWidth": "min(92vw, 1000px)", "width": "92vw"}, [], {}, [], {}, []

    @app.callback(
        Output("settings-modal-form", "children"),
        Input("settings-modal-mode", "data"),
        Input("settings-categories-drafts", "data"),
        Input("settings-categories-edits", "data"),
        Input("settings-metrics-drafts", "data"),
        Input("settings-metrics-edits", "data"),
        Input("settings-metrics-order", "data"),
        State("user-id", "data"),
    )
    def render_settings_modal_content(
        modal_mode,
        draft_rows,
        edited_rows,
        metric_draft_rows,
        metric_edited_rows,
        metric_order,
        user_id,
    ):
        if not modal_mode or not user_id:
            return []

        if modal_mode == "categories":
            return edit_categories_content(user_id, draft_rows=draft_rows, edited_rows=edited_rows)
        if modal_mode == "metrics":
            return edit_metrics_content(
                user_id,
                draft_rows=metric_draft_rows,
                edited_rows=metric_edited_rows,
                row_order=metric_order,
            )

        return []

    @app.callback(
        Output("settings-metrics-order", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-move-up", "type": "button", "metric_key": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-move-down", "type": "button", "metric_key": ALL}, "n_clicks"),
        State("settings-metrics-order", "data"),
        State({"page": "settings-modal", "name": "metric-key", "type": "text", "metric_key": ALL}, "id"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def reorder_existing_metrics(move_up_clicks, move_down_clicks, row_order, metric_key_ids, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate

        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        value = ctx.triggered[0].get("value")
        if not value:
            raise PreventUpdate

        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        current_order = list(row_order or [])
        if not current_order:
            current_order = [id_obj.get("metric_key") for id_obj in (metric_key_ids or []) if id_obj.get("metric_key")]

        if metric_key not in current_order:
            current_order.append(metric_key)

        idx = current_order.index(metric_key)
        if triggered_id.get("name") == "metric-move-up" and idx > 0:
            current_order[idx - 1], current_order[idx] = current_order[idx], current_order[idx - 1]
        elif triggered_id.get("name") == "metric-move-down" and idx < len(current_order) - 1:
            current_order[idx + 1], current_order[idx] = current_order[idx], current_order[idx + 1]

        return current_order

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-move-up", "type": "button", "row_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-draft-move-down", "type": "button", "row_id": ALL}, "n_clicks"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def reorder_metric_drafts(move_up_clicks, move_down_clicks, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate

        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        value = ctx.triggered[0].get("value")
        if not value:
            raise PreventUpdate

        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        rows = list(draft_rows or [])
        idx = next((i for i, d in enumerate(rows) if d.get("row_id") == row_id), -1)
        if idx < 0:
            raise PreventUpdate

        if triggered_id.get("name") == "metric-draft-move-up" and idx > 0:
            rows[idx - 1], rows[idx] = rows[idx], rows[idx - 1]
        elif triggered_id.get("name") == "metric-draft-move-down" and idx < len(rows) - 1:
            rows[idx + 1], rows[idx] = rows[idx], rows[idx + 1]

        return rows

    @app.callback(
        Output("settings-categories-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "category-add", "type": "button"}, "n_clicks"),
        Input({"page": "settings-modal", "name": "category-draft-save", "type": "button", "row_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "category-draft-edit", "type": "button", "row_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "category-draft-delete", "type": "button", "row_id": ALL}, "n_clicks"),
        State("settings-categories-drafts", "data"),
        State({"page": "settings-modal", "name": "category-draft-name", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "category-draft-name", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "category-name", "type": "text", "category_id": ALL}, "children"),
        State({"page": "settings-modal", "name": "category-name", "type": "text", "category_id": ALL}, "id"),
        State("settings-categories-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def handle_category_draft_rows(
        add_clicks,
        save_clicks,
        edit_clicks,
        delete_clicks,
        draft_rows,
        draft_names,
        draft_name_ids,
        existing_name_children,
        existing_name_ids,
        edited_rows,
        modal_mode,
    ):
        if modal_mode != "categories":
            raise PreventUpdate

        draft_rows = list(draft_rows or [])
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate

        name = triggered_id.get("name")
        if name == "category-add":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            draft_rows.append(
                {
                    "row_id": str(uuid.uuid4()),
                    "category_name": "",
                    "is_active": True,
                    "is_staged": False,
                    "is_duplicate": False,
                }
            )
            return draft_rows

        row_id_to_name = {}
        for i, id_obj in enumerate(draft_name_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_name[rid] = (draft_names[i] or "").strip() if i < len(draft_names or []) else ""

        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        if name == "category-draft-save":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            category_name = row_id_to_name.get(row_id, "").strip()
            if not category_name:
                updated_rows = []
                for d in draft_rows:
                    if d.get("row_id") == row_id:
                        updated_rows.append(
                            {
                                **d,
                                "category_name": "",
                                "is_duplicate": True,
                                "is_staged": False,
                            }
                        )
                    else:
                        updated_rows.append(d)
                return updated_rows
            normalized_name = " ".join(category_name.lower().split())

            taken_names = set()
            for i, _ in enumerate(existing_name_ids or []):
                base_name = (existing_name_children[i] or "").strip() if i < len(existing_name_children or []) else ""
                if base_name:
                    taken_names.add(" ".join(base_name.lower().split()))

            for d in draft_rows:
                if d.get("row_id") != row_id:
                    d_name = row_id_to_name.get(d.get("row_id"), (d.get("category_name") or "").strip())
                    d_name = (d_name or "").strip()
                    if d_name:
                        taken_names.add(" ".join(d_name.lower().split()))

            for _, e in (edited_rows or {}).items():
                if e.get("is_staged"):
                    e_name = (e.get("category_name") or "").strip()
                    if e_name:
                        taken_names.add(" ".join(e_name.lower().split()))

            if normalized_name in taken_names:
                updated_rows = []
                for d in draft_rows:
                    if d.get("row_id") == row_id:
                        updated_rows.append(
                            {
                                **d,
                                "category_name": category_name,
                                "is_duplicate": True,
                                "is_staged": False,
                            }
                        )
                    else:
                        updated_rows.append(d)
                return updated_rows
            updated_rows = []
            for d in draft_rows:
                if d.get("row_id") == row_id:
                    updated_rows.append(
                        {
                            "row_id": row_id,
                            "category_name": category_name,
                            "is_active": bool(d.get("is_active", True)),
                            "is_staged": True,
                            "is_duplicate": False,
                        }
                    )
                else:
                    updated_rows.append(d)
            return updated_rows

        if name == "category-draft-edit":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            updated_rows = []
            for d in draft_rows:
                if d.get("row_id") == row_id:
                    updated_rows.append(
                        {
                            **d,
                            "is_staged": False,
                            "is_duplicate": False,
                        }
                    )
                else:
                    updated_rows.append(d)
            return updated_rows

        if name == "category-draft-delete":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            return [d for d in draft_rows if d.get("row_id") != row_id]

        return no_update

    @app.callback(
        Output("settings-categories-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "category-draft-active-toggle", "type": "button", "row_id": ALL}, "n_clicks"),
        State("settings-categories-drafts", "data"),
        State({"page": "settings-modal", "name": "category-draft-name", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "category-draft-name", "type": "input", "row_id": ALL}, "id"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def toggle_category_draft_active(toggle_clicks, draft_rows, draft_names, draft_name_ids, modal_mode):
        if modal_mode != "categories":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        value = ctx.triggered[0].get("value")
        if not value:
            raise PreventUpdate

        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        row_id_to_name = {}
        for i, id_obj in enumerate(draft_name_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_name[rid] = (draft_names[i] or "") if i < len(draft_names or []) else ""

        updated = []
        for d in list(draft_rows or []):
            draft_row_id = d.get("row_id")
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {
                    **d,
                    "category_name": row_id_to_name.get(draft_row_id, d.get("category_name", "")),
                    "is_active": not bool(d.get("is_active", True)),
                    "is_duplicate": False,
                }
            elif draft_row_id in row_id_to_name and not d.get("is_staged"):
                d = {
                    **d,
                    "category_name": row_id_to_name[draft_row_id],
                }
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-categories-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "category-edit", "type": "button", "category_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "category-edit-save", "type": "button", "category_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "category-edit-undo", "type": "button", "category_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "category-edit-active-toggle", "type": "button", "category_id": ALL}, "n_clicks"),
        State("settings-categories-edits", "data"),
        State({"page": "settings-modal", "name": "category-name", "type": "text", "category_id": ALL}, "children"),
        State({"page": "settings-modal", "name": "category-name", "type": "text", "category_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "category-active", "type": "icon", "category_id": ALL}, "className"),
        State({"page": "settings-modal", "name": "category-edit-name", "type": "input", "category_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "category-edit-name", "type": "input", "category_id": ALL}, "id"),
        State("settings-categories-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def handle_existing_category_rows(
        edit_clicks,
        save_clicks,
        undo_clicks,
        toggle_clicks,
        edited_rows,
        name_children,
        name_ids,
        active_icon_classes,
        edit_name_values,
        edit_name_ids,
        draft_rows,
        modal_mode,
    ):
        if modal_mode != "categories":
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate

        def _base_row_values(category_id_value: int):
            cid_str = str(int(category_id_value))
            base_name = ""
            base_active = True
            for i, id_obj in enumerate(name_ids or []):
                if str(id_obj.get("category_id")) == cid_str:
                    base_name = (name_children[i] or "") if i < len(name_children or []) else ""
                    cls = (active_icon_classes[i] or "") if i < len(active_icon_classes or []) else ""
                    base_active = "check2-circle" in cls
                    break
            if cid_str in edited_rows:
                base_name = edited_rows[cid_str].get("category_name", base_name)
                base_active = bool(edited_rows[cid_str].get("is_active", base_active))
            return base_name, base_active

        name = triggered_id.get("name")
        category_id = triggered_id.get("category_id")
        if category_id is None:
            raise PreventUpdate
        cid_str = str(int(category_id))

        if name == "category-edit":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            base_name, base_active = _base_row_values(category_id)
            edited_rows[cid_str] = {
                "category_name": base_name,
                "is_active": base_active,
                "is_editing": True,
                "is_staged": bool(edited_rows.get(cid_str, {}).get("is_staged")),
                "is_duplicate": False,
            }
            return edited_rows

        if name == "category-edit-save":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            current_name = None
            for i, id_obj in enumerate(edit_name_ids or []):
                if str(id_obj.get("category_id")) == cid_str:
                    current_name = (edit_name_values[i] or "").strip() if i < len(edit_name_values or []) else ""
                    break
            if not current_name:
                current_active = bool(edited_rows.get(cid_str, {}).get("is_active", True))
                edited_rows[cid_str] = {
                    "category_name": "",
                    "is_active": current_active,
                    "is_editing": True,
                    "is_staged": bool(edited_rows.get(cid_str, {}).get("is_staged")),
                    "is_duplicate": True,
                }
                return edited_rows
            normalized_name = " ".join(current_name.lower().split())

            taken_names = set()
            for i, id_obj in enumerate(name_ids or []):
                row_cid = str(id_obj.get("category_id"))
                if row_cid == cid_str:
                    continue
                base_name = (name_children[i] or "") if i < len(name_children or []) else ""
                base_name = (base_name or "").strip()
                if base_name:
                    taken_names.add(" ".join(base_name.lower().split()))

            for row_cid, row_data in (edited_rows or {}).items():
                if row_cid == cid_str:
                    continue
                row_name = (row_data.get("category_name") or "").strip()
                if row_name:
                    taken_names.add(" ".join(row_name.lower().split()))

            for d in list(draft_rows or []):
                d_name = (d.get("category_name") or "").strip()
                if d_name:
                    taken_names.add(" ".join(d_name.lower().split()))

            if normalized_name in taken_names:
                current_active = bool(edited_rows.get(cid_str, {}).get("is_active", True))
                edited_rows[cid_str] = {
                    "category_name": current_name,
                    "is_active": current_active,
                    "is_editing": True,
                    "is_staged": bool(edited_rows.get(cid_str, {}).get("is_staged")),
                    "is_duplicate": True,
                }
                return edited_rows

            current_active = bool(edited_rows.get(cid_str, {}).get("is_active", True))
            edited_rows[cid_str] = {
                "category_name": current_name,
                "is_active": current_active,
                "is_editing": False,
                "is_staged": True,
                "is_duplicate": False,
            }
            return edited_rows

        if name == "category-edit-active-toggle":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            row = edited_rows.get(cid_str)
            if not row or not row.get("is_editing"):
                raise PreventUpdate
            current_name = row.get("category_name", "")
            for i, id_obj in enumerate(edit_name_ids or []):
                if str(id_obj.get("category_id")) == cid_str:
                    current_name = (edit_name_values[i] or "").strip() if i < len(edit_name_values or []) else ""
                    break
            edited_rows[cid_str] = {
                **row,
                "category_name": current_name,
                "is_active": not bool(row.get("is_active", True)),
                "is_duplicate": False,
            }
            return edited_rows

        if name == "category-edit-undo":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            if cid_str in edited_rows:
                edited_rows.pop(cid_str, None)
            return edited_rows

        return no_update

    @app.callback(
        Output("settings-categories-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "category-draft-name", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "category-draft-name", "type": "input", "row_id": ALL}, "id"),
        State("settings-categories-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def clear_draft_name_error_on_change(name_values, name_ids, draft_rows, modal_mode):
        if modal_mode != "categories":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = None
        for i, id_obj in enumerate(name_ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = name_values[i] if i < len(name_values or []) else ""
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {
                    **d,
                    "category_name": "" if current_value is None else str(current_value),
                    "is_duplicate": False,
                }
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-categories-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "category-edit-name", "type": "input", "category_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "category-edit-name", "type": "input", "category_id": ALL}, "id"),
        State("settings-categories-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def clear_existing_name_error_on_change(name_values, name_ids, edited_rows, modal_mode):
        if modal_mode != "categories":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        category_id = triggered_id.get("category_id")
        if category_id is None:
            raise PreventUpdate
        cid_str = str(int(category_id))

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(cid_str)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("category_name", "")
        for i, id_obj in enumerate(name_ids or []):
            if str(id_obj.get("category_id")) == cid_str:
                current_value = name_values[i] if i < len(name_values or []) else ""
                break

        edited_rows[cid_str] = {
            **row,
            "category_name": "" if current_value is None else str(current_value),
            "is_duplicate": False,
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-add", "type": "button"}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-draft-save", "type": "button", "row_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-draft-edit", "type": "button", "row_id": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-draft-delete", "type": "button", "row_id": ALL}, "n_clicks"),
        State("settings-metrics-drafts", "data"),
        State({"page": "settings-modal", "name": "metric-draft-display-name", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-display-name", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-unit", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-unit", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-subcategory", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-subcategory", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-activity", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-activity", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-to-minutes-factor", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-to-minutes-factor", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-value-type", "type": "dropdown", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-value-type", "type": "dropdown", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-category-id", "type": "dropdown", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-category-id", "type": "dropdown", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-display-name", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-display-name", "type": "text", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("user-id", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def handle_metric_draft_rows(
        add_clicks,
        save_clicks,
        edit_clicks,
        delete_clicks,
        draft_rows,
        draft_names,
        draft_name_ids,
        draft_units,
        draft_unit_ids,
        draft_subcategories,
        draft_subcategory_ids,
        draft_activities,
        draft_activity_ids,
        draft_to_minutes_factors,
        draft_to_minutes_factor_ids,
        draft_value_types,
        draft_value_type_ids,
        draft_category_ids,
        draft_category_id_ids,
        existing_name_children,
        existing_name_ids,
        metric_edits,
        user_id,
        modal_mode,
    ):
        if modal_mode != "metrics":
            raise PreventUpdate

        draft_rows = list(draft_rows or [])
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate

        name = triggered_id.get("name")
        if name == "metric-add":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            draft_rows.append(
                {
                    "row_id": str(uuid.uuid4()),
                    "display_name": "",
                    "unit": "",
                    "subcategory": "",
                    "activity": "",
                    "to_minutes_factor": "",
                    "is_duration": False,
                    "value_type": "double",
                    "category_id": "",
                    "category_name": "",
                    "is_staged": False,
                    "is_invalid": False,
                    "is_invalid_to_minutes_factor": False,
                }
            )
            return draft_rows

        row_id_to_name = {}
        for i, id_obj in enumerate(draft_name_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_name[rid] = (draft_names[i] or "").strip() if i < len(draft_names or []) else ""
        row_id_to_unit = {}
        for i, id_obj in enumerate(draft_unit_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_unit[rid] = (draft_units[i] or "").strip() if i < len(draft_units or []) else ""
        row_id_to_subcategory = {}
        for i, id_obj in enumerate(draft_subcategory_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_subcategory[rid] = (draft_subcategories[i] or "").strip() if i < len(draft_subcategories or []) else ""
        row_id_to_activity = {}
        for i, id_obj in enumerate(draft_activity_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_activity[rid] = (draft_activities[i] or "").strip() if i < len(draft_activities or []) else ""
        row_id_to_to_minutes_factor = {}
        for i, id_obj in enumerate(draft_to_minutes_factor_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_to_minutes_factor[rid] = (draft_to_minutes_factors[i] or "").strip() if i < len(draft_to_minutes_factors or []) else ""
        row_id_to_value_type = {}
        for i, id_obj in enumerate(draft_value_type_ids or []):
            rid = id_obj.get("row_id")
            value_type = (draft_value_types[i] if i < len(draft_value_types or []) else None) or "double"
            row_id_to_value_type[rid] = value_type
        row_id_to_category_id = {}
        for i, id_obj in enumerate(draft_category_id_ids or []):
            rid = id_obj.get("row_id")
            value = (draft_category_ids[i] if i < len(draft_category_ids or []) else None)
            row_id_to_category_id[rid] = "" if value in (None, "") else str(value)
        category_label_by_value = {"": ""}
        for opt in get_category_layout(user_id, include_all_option=False):
            category_label_by_value[str(opt["value"])] = str(opt["label"])

        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        if name == "metric-draft-save":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            display_name = row_id_to_name.get(row_id, "").strip()
            ok_to_minutes, normalized_to_minutes = _normalize_positive_double(
                row_id_to_to_minutes_factor.get(row_id, "")
            )
            if not display_name:
                updated = []
                for d in draft_rows:
                    if d.get("row_id") == row_id:
                        updated.append(
                            {
                                **d,
                                "display_name": "",
                                "to_minutes_factor": normalized_to_minutes,
                                "is_invalid": True,
                                "is_invalid_to_minutes_factor": False,
                                "is_staged": False,
                            }
                        )
                    else:
                        updated.append(d)
                return updated
            if not ok_to_minutes:
                updated = []
                for d in draft_rows:
                    if d.get("row_id") == row_id:
                        updated.append(
                            {
                                **d,
                                "display_name": display_name,
                                "to_minutes_factor": normalized_to_minutes,
                                "is_invalid": False,
                                "is_invalid_to_minutes_factor": True,
                                "is_staged": False,
                            }
                        )
                    else:
                        updated.append(d)
                return updated

            normalized_name = " ".join(display_name.lower().split())
            taken_names = set()
            for i, _ in enumerate(existing_name_ids or []):
                base_name = (existing_name_children[i] or "").strip() if i < len(existing_name_children or []) else ""
                if base_name:
                    taken_names.add(" ".join(base_name.lower().split()))

            for d in draft_rows:
                if d.get("row_id") != row_id:
                    d_name = row_id_to_name.get(d.get("row_id"), (d.get("display_name") or "").strip())
                    d_name = (d_name or "").strip()
                    if d_name:
                        taken_names.add(" ".join(d_name.lower().split()))

            for _, e in (metric_edits or {}).items():
                if e.get("is_staged") or e.get("is_editing"):
                    e_name = (e.get("display_name") or "").strip()
                    if e_name:
                        taken_names.add(" ".join(e_name.lower().split()))

            if normalized_name in taken_names:
                updated = []
                for d in draft_rows:
                    if d.get("row_id") == row_id:
                        updated.append(
                            {
                                **d,
                                "display_name": display_name,
                                "unit": row_id_to_unit.get(row_id, d.get("unit", "")),
                                "subcategory": row_id_to_subcategory.get(row_id, d.get("subcategory", "")),
                                "activity": row_id_to_activity.get(row_id, d.get("activity", "")),
                                "to_minutes_factor": normalized_to_minutes,
                                "value_type": row_id_to_value_type.get(row_id, d.get("value_type", "double")),
                                "category_id": row_id_to_category_id.get(row_id, d.get("category_id", "")),
                                "category_name": category_label_by_value.get(
                                    row_id_to_category_id.get(row_id, d.get("category_id", "")),
                                    "",
                                ),
                                "is_invalid": True,
                                "is_invalid_to_minutes_factor": False,
                                "is_staged": False,
                            }
                        )
                    else:
                        updated.append(d)
                return updated

            updated = []
            for d in draft_rows:
                if d.get("row_id") == row_id:
                    updated.append(
                        {
                            **d,
                            "display_name": display_name,
                            "unit": row_id_to_unit.get(row_id, d.get("unit", "")),
                            "subcategory": row_id_to_subcategory.get(row_id, d.get("subcategory", "")),
                            "activity": row_id_to_activity.get(row_id, d.get("activity", "")),
                            "to_minutes_factor": normalized_to_minutes,
                            "value_type": row_id_to_value_type.get(row_id, d.get("value_type", "double")),
                            "category_id": row_id_to_category_id.get(row_id, d.get("category_id", "")),
                            "category_name": category_label_by_value.get(
                                row_id_to_category_id.get(row_id, d.get("category_id", "")),
                                "",
                            ),
                            "is_staged": True,
                            "is_invalid": False,
                            "is_invalid_to_minutes_factor": False,
                        }
                    )
                else:
                    updated.append(d)
            return updated

        if name == "metric-draft-edit":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            updated = []
            for d in draft_rows:
                if d.get("row_id") == row_id:
                    updated.append(
                        {
                            **d,
                            "is_staged": False,
                            "is_invalid": False,
                            "is_invalid_to_minutes_factor": False,
                        }
                    )
                else:
                    updated.append(d)
            return updated

        if name == "metric-draft-delete":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            return [d for d in draft_rows if d.get("row_id") != row_id]

        return no_update

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-is-duration-toggle", "type": "button", "row_id": ALL}, "n_clicks"),
        State("settings-metrics-drafts", "data"),
        State({"page": "settings-modal", "name": "metric-draft-unit", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-unit", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-subcategory", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-subcategory", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-activity", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-activity", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-to-minutes-factor", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-to-minutes-factor", "type": "input", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-value-type", "type": "dropdown", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-value-type", "type": "dropdown", "row_id": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-draft-category-id", "type": "dropdown", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-category-id", "type": "dropdown", "row_id": ALL}, "id"),
        State("user-id", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def toggle_metric_draft_duration(
        toggle_clicks,
        draft_rows,
        draft_units,
        draft_unit_ids,
        draft_subcategories,
        draft_subcategory_ids,
        draft_activities,
        draft_activity_ids,
        draft_to_minutes_factors,
        draft_to_minutes_factor_ids,
        draft_value_types,
        draft_value_type_ids,
        draft_category_ids,
        draft_category_id_ids,
        user_id,
        modal_mode,
    ):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        value = ctx.triggered[0].get("value")
        if not value:
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        row_id_to_value_type = {}
        for i, id_obj in enumerate(draft_value_type_ids or []):
            rid = id_obj.get("row_id")
            value_type = (draft_value_types[i] if i < len(draft_value_types or []) else None) or "double"
            row_id_to_value_type[rid] = value_type
        row_id_to_unit = {}
        for i, id_obj in enumerate(draft_unit_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_unit[rid] = (draft_units[i] or "").strip() if i < len(draft_units or []) else ""
        row_id_to_subcategory = {}
        for i, id_obj in enumerate(draft_subcategory_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_subcategory[rid] = (draft_subcategories[i] or "").strip() if i < len(draft_subcategories or []) else ""
        row_id_to_activity = {}
        for i, id_obj in enumerate(draft_activity_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_activity[rid] = (draft_activities[i] or "").strip() if i < len(draft_activities or []) else ""
        row_id_to_to_minutes_factor = {}
        for i, id_obj in enumerate(draft_to_minutes_factor_ids or []):
            rid = id_obj.get("row_id")
            row_id_to_to_minutes_factor[rid] = (draft_to_minutes_factors[i] or "").strip() if i < len(draft_to_minutes_factors or []) else ""
        row_id_to_category_id = {}
        for i, id_obj in enumerate(draft_category_id_ids or []):
            rid = id_obj.get("row_id")
            value = (draft_category_ids[i] if i < len(draft_category_ids or []) else None)
            row_id_to_category_id[rid] = "" if value in (None, "") else str(value)
        category_label_by_value = {"": ""}
        for opt in get_category_layout(user_id, include_all_option=False):
            category_label_by_value[str(opt["value"])] = str(opt["label"])

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                new_is_duration = not bool(d.get("is_duration", False))
                d = {
                    **d,
                    "unit": row_id_to_unit.get(row_id, d.get("unit", "")),
                    "subcategory": row_id_to_subcategory.get(row_id, d.get("subcategory", "")),
                    "activity": row_id_to_activity.get(row_id, d.get("activity", "")),
                    "to_minutes_factor": row_id_to_to_minutes_factor.get(row_id, d.get("to_minutes_factor", "")),
                    "value_type": "int" if new_is_duration else row_id_to_value_type.get(row_id, d.get("value_type", "double")),
                    "category_id": row_id_to_category_id.get(row_id, d.get("category_id", "")),
                    "category_name": category_label_by_value.get(
                        row_id_to_category_id.get(row_id, d.get("category_id", "")),
                        "",
                    ),
                    "is_duration": new_is_duration,
                    "is_invalid": False,
                    "is_invalid_to_minutes_factor": False,
                }
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit", "type": "button", "metric_key": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-edit-save", "type": "button", "metric_key": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-edit-undo", "type": "button", "metric_key": ALL}, "n_clicks"),
        Input({"page": "settings-modal", "name": "metric-edit-is-duration-toggle", "type": "button", "metric_key": ALL}, "n_clicks"),
        State("settings-metrics-edits", "data"),
        State({"page": "settings-modal", "name": "metric-display-name", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-display-name", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-unit", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-unit", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-subcategory", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-subcategory", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-activity", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-activity", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-to-minutes-factor", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-to-minutes-factor", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-value-type", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-value-type", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-category-id", "type": "text", "metric_key": ALL}, "children"),
        State({"page": "settings-modal", "name": "metric-category-id", "type": "text", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-is-duration", "type": "icon", "metric_key": ALL}, "className"),
        State({"page": "settings-modal", "name": "metric-edit-display-name", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-display-name", "type": "input", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-edit-unit", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-unit", "type": "input", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-edit-subcategory", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-subcategory", "type": "input", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-edit-activity", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-activity", "type": "input", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-edit-to-minutes-factor", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-to-minutes-factor", "type": "input", "metric_key": ALL}, "id"),
        State({"page": "settings-modal", "name": "metric-edit-category-id", "type": "dropdown", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-category-id", "type": "dropdown", "metric_key": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("user-id", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def handle_existing_metric_rows(
        edit_clicks,
        save_clicks,
        undo_clicks,
        toggle_clicks,
        edited_rows,
        name_children,
        name_ids,
        unit_children,
        unit_ids,
        subcategory_children,
        subcategory_ids,
        activity_children,
        activity_ids,
        to_minutes_factor_children,
        to_minutes_factor_ids,
        value_type_children,
        value_type_ids,
        category_id_children,
        category_id_ids,
        duration_icon_classes,
        edit_name_values,
        edit_name_ids,
        edit_unit_values,
        edit_unit_ids,
        edit_subcategory_values,
        edit_subcategory_ids,
        edit_activity_values,
        edit_activity_ids,
        edit_to_minutes_factor_values,
        edit_to_minutes_factor_ids,
        edit_category_id_values,
        edit_category_id_ids,
        metric_drafts,
        user_id,
        modal_mode,
    ):
        if modal_mode != "metrics":
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate

        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        def _base_metric_values(target_key: str):
            base_name = ""
            base_unit = ""
            base_subcategory = ""
            base_activity = ""
            base_to_minutes_factor = ""
            base_value_type = "double"
            base_category_id = ""
            base_category_name = ""
            base_is_duration = False
            for i, id_obj in enumerate(name_ids or []):
                if id_obj.get("metric_key") == target_key:
                    base_name = (name_children[i] or "") if i < len(name_children or []) else ""
                    break
            for i, id_obj in enumerate(unit_ids or []):
                if id_obj.get("metric_key") == target_key:
                    base_unit = (unit_children[i] or "") if i < len(unit_children or []) else ""
                    break
            for i, id_obj in enumerate(subcategory_ids or []):
                if id_obj.get("metric_key") == target_key:
                    base_subcategory = (subcategory_children[i] or "") if i < len(subcategory_children or []) else ""
                    break
            for i, id_obj in enumerate(activity_ids or []):
                if id_obj.get("metric_key") == target_key:
                    base_activity = (activity_children[i] or "") if i < len(activity_children or []) else ""
                    break
            for i, id_obj in enumerate(to_minutes_factor_ids or []):
                if id_obj.get("metric_key") == target_key:
                    raw = to_minutes_factor_children[i] if i < len(to_minutes_factor_children or []) else ""
                    base_to_minutes_factor = "" if raw is None else str(raw).strip()
                    break
            for i, id_obj in enumerate(value_type_ids or []):
                if id_obj.get("metric_key") == target_key:
                    base_value_type = (value_type_children[i] or "double") if i < len(value_type_children or []) else "double"
                    break
            for i, id_obj in enumerate(category_id_ids or []):
                if id_obj.get("metric_key") == target_key:
                    raw = category_id_children[i] if i < len(category_id_children or []) else ""
                    base_category_id = "" if raw in (None, "") else str(raw)
                    break
            for i, id_obj in enumerate(name_ids or []):
                if id_obj.get("metric_key") == target_key:
                    cls = (duration_icon_classes[i] or "") if i < len(duration_icon_classes or []) else ""
                    base_is_duration = "check2-circle" in cls
                    break
            category_label_by_value = {"": ""}
            for opt in get_category_layout(user_id, include_all_option=False):
                category_label_by_value[str(opt["value"])] = str(opt["label"])
            base_category_name = category_label_by_value.get(base_category_id, "")
            if target_key in edited_rows:
                base_name = edited_rows[target_key].get("display_name", base_name)
                base_unit = edited_rows[target_key].get("unit", base_unit)
                base_subcategory = edited_rows[target_key].get("subcategory", base_subcategory)
                base_activity = edited_rows[target_key].get("activity", base_activity)
                base_to_minutes_factor = edited_rows[target_key].get("to_minutes_factor", base_to_minutes_factor)
                base_value_type = edited_rows[target_key].get("value_type", base_value_type)
                base_category_id = edited_rows[target_key].get("category_id", base_category_id)
                base_category_name = edited_rows[target_key].get("category_name", base_category_name)
                base_is_duration = bool(edited_rows[target_key].get("is_duration", base_is_duration))
            return (
                base_name,
                base_unit,
                base_subcategory,
                base_activity,
                base_to_minutes_factor,
                base_value_type,
                base_category_id,
                base_category_name,
                base_is_duration,
            )

        name = triggered_id.get("name")
        if name == "metric-edit":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            (
                base_name,
                base_unit,
                base_subcategory,
                base_activity,
                base_to_minutes_factor,
                base_value_type,
                base_category_id,
                base_category_name,
                base_is_duration,
            ) = _base_metric_values(metric_key)
            edited_rows[metric_key] = {
                "display_name": base_name,
                "unit": base_unit,
                "subcategory": base_subcategory,
                "activity": base_activity,
                "to_minutes_factor": base_to_minutes_factor,
                "value_type": base_value_type,
                "category_id": base_category_id,
                "category_name": base_category_name,
                "is_duration": base_is_duration,
                "is_editing": True,
                "is_staged": bool(edited_rows.get(metric_key, {}).get("is_staged")),
                "is_invalid": False,
                "is_invalid_to_minutes_factor": False,
            }
            return edited_rows

        if name == "metric-edit-save":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            current_name = ""
            for i, id_obj in enumerate(edit_name_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_name = (edit_name_values[i] or "").strip() if i < len(edit_name_values or []) else ""
                    break
            current_unit = (edited_rows.get(metric_key, {}) or {}).get("unit", "")
            for i, id_obj in enumerate(edit_unit_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_unit = (edit_unit_values[i] or "").strip() if i < len(edit_unit_values or []) else ""
                    break
            current_subcategory = (edited_rows.get(metric_key, {}) or {}).get("subcategory", "")
            for i, id_obj in enumerate(edit_subcategory_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_subcategory = (edit_subcategory_values[i] or "").strip() if i < len(edit_subcategory_values or []) else ""
                    break
            current_activity = (edited_rows.get(metric_key, {}) or {}).get("activity", "")
            for i, id_obj in enumerate(edit_activity_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_activity = (edit_activity_values[i] or "").strip() if i < len(edit_activity_values or []) else ""
                    break
            current_to_minutes_factor = (edited_rows.get(metric_key, {}) or {}).get("to_minutes_factor", "")
            for i, id_obj in enumerate(edit_to_minutes_factor_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    raw = edit_to_minutes_factor_values[i] if i < len(edit_to_minutes_factor_values or []) else ""
                    current_to_minutes_factor = "" if raw is None else str(raw).strip()
                    break
            ok_to_minutes, normalized_to_minutes = _normalize_positive_double(current_to_minutes_factor)
            current_category_id = (edited_rows.get(metric_key, {}) or {}).get("category_id", "")
            for i, id_obj in enumerate(edit_category_id_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    raw = edit_category_id_values[i] if i < len(edit_category_id_values or []) else ""
                    current_category_id = "" if raw in (None, "") else str(raw)
                    break
            category_label_by_value = {"": ""}
            for opt in get_category_layout(user_id, include_all_option=False):
                category_label_by_value[str(opt["value"])] = str(opt["label"])
            current_category_name = category_label_by_value.get(current_category_id, "")
            current_value_type = (edited_rows.get(metric_key, {}) or {}).get("value_type", "double")
            if not current_name:
                current_duration = bool(edited_rows.get(metric_key, {}).get("is_duration", False))
                edited_rows[metric_key] = {
                    "display_name": "",
                    "unit": current_unit,
                    "subcategory": current_subcategory,
                    "activity": current_activity,
                    "to_minutes_factor": normalized_to_minutes,
                    "value_type": current_value_type,
                    "category_id": current_category_id,
                    "category_name": current_category_name,
                    "is_duration": current_duration,
                    "is_editing": True,
                    "is_staged": bool(edited_rows.get(metric_key, {}).get("is_staged")),
                    "is_invalid": True,
                    "is_invalid_to_minutes_factor": False,
                }
                return edited_rows
            if not ok_to_minutes:
                current_duration = bool(edited_rows.get(metric_key, {}).get("is_duration", False))
                edited_rows[metric_key] = {
                    "display_name": current_name,
                    "unit": current_unit,
                    "subcategory": current_subcategory,
                    "activity": current_activity,
                    "to_minutes_factor": normalized_to_minutes,
                    "value_type": current_value_type,
                    "category_id": current_category_id,
                    "category_name": current_category_name,
                    "is_duration": current_duration,
                    "is_editing": True,
                    "is_staged": bool(edited_rows.get(metric_key, {}).get("is_staged")),
                    "is_invalid": False,
                    "is_invalid_to_minutes_factor": True,
                }
                return edited_rows

            normalized_name = " ".join(current_name.lower().split())
            taken_names = set()
            for i, id_obj in enumerate(name_ids or []):
                row_key = id_obj.get("metric_key")
                if row_key == metric_key:
                    continue
                base_name = (name_children[i] or "") if i < len(name_children or []) else ""
                base_name = (base_name or "").strip()
                if base_name:
                    taken_names.add(" ".join(base_name.lower().split()))

            for row_key, row_data in (edited_rows or {}).items():
                if row_key == metric_key:
                    continue
                row_name = (row_data.get("display_name") or "").strip()
                if row_name:
                    taken_names.add(" ".join(row_name.lower().split()))

            for d in list(metric_drafts or []):
                d_name = (d.get("display_name") or "").strip()
                if d_name:
                    taken_names.add(" ".join(d_name.lower().split()))

            if normalized_name in taken_names:
                current_duration = bool(edited_rows.get(metric_key, {}).get("is_duration", False))
                edited_rows[metric_key] = {
                    "display_name": current_name,
                    "unit": current_unit,
                    "subcategory": current_subcategory,
                    "activity": current_activity,
                    "to_minutes_factor": normalized_to_minutes,
                    "value_type": current_value_type,
                    "category_id": current_category_id,
                    "category_name": current_category_name,
                    "is_duration": current_duration,
                    "is_editing": True,
                    "is_staged": bool(edited_rows.get(metric_key, {}).get("is_staged")),
                    "is_invalid": True,
                    "is_invalid_to_minutes_factor": False,
                }
                return edited_rows

            current_duration = bool(edited_rows.get(metric_key, {}).get("is_duration", False))
            edited_rows[metric_key] = {
                "display_name": current_name,
                "unit": current_unit,
                "subcategory": current_subcategory,
                "activity": current_activity,
                "to_minutes_factor": normalized_to_minutes,
                "value_type": current_value_type,
                "category_id": current_category_id,
                "category_name": current_category_name,
                "is_duration": current_duration,
                "is_editing": False,
                "is_staged": True,
                "is_invalid": False,
                "is_invalid_to_minutes_factor": False,
            }
            return edited_rows

        if name == "metric-edit-is-duration-toggle":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            row = edited_rows.get(metric_key)
            if not row or not row.get("is_editing"):
                raise PreventUpdate
            current_name = row.get("display_name", "")
            for i, id_obj in enumerate(edit_name_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_name = (edit_name_values[i] or "").strip() if i < len(edit_name_values or []) else ""
                    break
            current_unit = row.get("unit", "")
            for i, id_obj in enumerate(edit_unit_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_unit = (edit_unit_values[i] or "").strip() if i < len(edit_unit_values or []) else ""
                    break
            current_subcategory = row.get("subcategory", "")
            for i, id_obj in enumerate(edit_subcategory_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_subcategory = (edit_subcategory_values[i] or "").strip() if i < len(edit_subcategory_values or []) else ""
                    break
            current_activity = row.get("activity", "")
            for i, id_obj in enumerate(edit_activity_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    current_activity = (edit_activity_values[i] or "").strip() if i < len(edit_activity_values or []) else ""
                    break
            current_to_minutes_factor = row.get("to_minutes_factor", "")
            for i, id_obj in enumerate(edit_to_minutes_factor_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    raw = edit_to_minutes_factor_values[i] if i < len(edit_to_minutes_factor_values or []) else ""
                    current_to_minutes_factor = "" if raw is None else str(raw).strip()
                    break
            ok_to_minutes, normalized_to_minutes = _normalize_positive_double(current_to_minutes_factor)
            current_category_id = row.get("category_id", "")
            for i, id_obj in enumerate(edit_category_id_ids or []):
                if id_obj.get("metric_key") == metric_key:
                    raw = edit_category_id_values[i] if i < len(edit_category_id_values or []) else ""
                    current_category_id = "" if raw in (None, "") else str(raw)
                    break
            category_label_by_value = {"": ""}
            for opt in get_category_layout(user_id, include_all_option=False):
                category_label_by_value[str(opt["value"])] = str(opt["label"])
            current_value_type = row.get("value_type", "double")
            edited_rows[metric_key] = {
                **row,
                "display_name": current_name,
                "unit": current_unit,
                "subcategory": current_subcategory,
                "activity": current_activity,
                "to_minutes_factor": normalized_to_minutes,
                "value_type": current_value_type,
                "category_id": current_category_id,
                "category_name": category_label_by_value.get(current_category_id, ""),
                "is_duration": not bool(row.get("is_duration", False)),
                "is_invalid": False,
                "is_invalid_to_minutes_factor": not ok_to_minutes,
            }
            return edited_rows

        if name == "metric-edit-undo":
            value = ctx.triggered[0].get("value")
            if not value:
                raise PreventUpdate
            if metric_key in edited_rows:
                edited_rows.pop(metric_key, None)
            return edited_rows

        return no_update

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-display-name", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-display-name", "type": "input", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def clear_metric_draft_name_error_on_change(name_values, name_ids, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = ""
        for i, id_obj in enumerate(name_ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = name_values[i] if i < len(name_values or []) else ""
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {
                    **d,
                    "display_name": "" if current_value is None else str(current_value),
                    "is_invalid": False,
                }
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit-display-name", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-display-name", "type": "input", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def clear_existing_metric_name_error_on_change(name_values, name_ids, edited_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(metric_key)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("display_name", "")
        for i, id_obj in enumerate(name_ids or []):
            if id_obj.get("metric_key") == metric_key:
                current_value = name_values[i] if i < len(name_values or []) else ""
                break

        edited_rows[metric_key] = {
            **row,
            "display_name": "" if current_value is None else str(current_value),
            "is_invalid": False,
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-unit", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-unit", "type": "input", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_metric_draft_unit(values, ids, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = ""
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {**d, "unit": str(current_value)}
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-subcategory", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-subcategory", "type": "input", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_metric_draft_subcategory(values, ids, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = ""
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {**d, "subcategory": str(current_value)}
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-activity", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-activity", "type": "input", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_metric_draft_activity(values, ids, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = ""
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {**d, "activity": str(current_value)}
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-to-minutes-factor", "type": "input", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-to-minutes-factor", "type": "input", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_metric_draft_to_minutes_factor(values, ids, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = ""
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {
                    **d,
                    "to_minutes_factor": str(current_value),
                    "is_invalid_to_minutes_factor": False,
                }
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-category-id", "type": "dropdown", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-category-id", "type": "dropdown", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("user-id", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_metric_draft_category(values, ids, draft_rows, user_id, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = ""
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("row_id") == row_id:
                raw = values[i] if i < len(values or []) else ""
                current_value = "" if raw in (None, "") else str(raw)
                break

        category_label_by_value = {"": ""}
        for opt in get_category_layout(user_id, include_all_option=False):
            category_label_by_value[str(opt["value"])] = str(opt["label"])

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {
                    **d,
                    "category_id": current_value,
                    "category_name": category_label_by_value.get(current_value, ""),
                }
            updated.append(d)
        return updated

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit-unit", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-unit", "type": "input", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_existing_metric_unit(values, ids, edited_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(metric_key)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("unit", "")
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("metric_key") == metric_key:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        edited_rows[metric_key] = {
            **row,
            "unit": str(current_value),
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit-subcategory", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-subcategory", "type": "input", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_existing_metric_subcategory(values, ids, edited_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(metric_key)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("subcategory", "")
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("metric_key") == metric_key:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        edited_rows[metric_key] = {
            **row,
            "subcategory": str(current_value),
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit-activity", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-activity", "type": "input", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_existing_metric_activity(values, ids, edited_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(metric_key)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("activity", "")
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("metric_key") == metric_key:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        edited_rows[metric_key] = {
            **row,
            "activity": str(current_value),
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit-to-minutes-factor", "type": "input", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-to-minutes-factor", "type": "input", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_existing_metric_to_minutes_factor(values, ids, edited_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(metric_key)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("to_minutes_factor", "")
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("metric_key") == metric_key:
                current_value = (values[i] if i < len(values or []) else "") or ""
                break

        edited_rows[metric_key] = {
            **row,
            "to_minutes_factor": str(current_value),
            "is_invalid_to_minutes_factor": False,
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-edits", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-edit-category-id", "type": "dropdown", "metric_key": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-edit-category-id", "type": "dropdown", "metric_key": ALL}, "id"),
        State("settings-metrics-edits", "data"),
        State("user-id", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_existing_metric_category(values, ids, edited_rows, user_id, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        metric_key = triggered_id.get("metric_key")
        if not metric_key:
            raise PreventUpdate

        edited_rows = dict(edited_rows or {})
        row = edited_rows.get(metric_key)
        if not row or not row.get("is_editing"):
            raise PreventUpdate

        current_value = row.get("category_id", "")
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("metric_key") == metric_key:
                raw = values[i] if i < len(values or []) else ""
                current_value = "" if raw in (None, "") else str(raw)
                break

        category_label_by_value = {"": ""}
        for opt in get_category_layout(user_id, include_all_option=False):
            category_label_by_value[str(opt["value"])] = str(opt["label"])

        edited_rows[metric_key] = {
            **row,
            "category_id": current_value,
            "category_name": category_label_by_value.get(current_value, ""),
        }
        return edited_rows

    @app.callback(
        Output("settings-metrics-drafts", "data", allow_duplicate=True),
        Input({"page": "settings-modal", "name": "metric-draft-value-type", "type": "dropdown", "row_id": ALL}, "value"),
        State({"page": "settings-modal", "name": "metric-draft-value-type", "type": "dropdown", "row_id": ALL}, "id"),
        State("settings-metrics-drafts", "data"),
        State("settings-modal-mode", "data"),
        prevent_initial_call=True,
    )
    def sync_metric_draft_value_type(values, ids, draft_rows, modal_mode):
        if modal_mode != "metrics":
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            raise PreventUpdate
        row_id = triggered_id.get("row_id")
        if not row_id:
            raise PreventUpdate

        current_value = "double"
        for i, id_obj in enumerate(ids or []):
            if id_obj.get("row_id") == row_id:
                current_value = (values[i] if i < len(values or []) else None) or "double"
                break

        updated = []
        for d in list(draft_rows or []):
            if d.get("row_id") == row_id and not d.get("is_staged"):
                d = {**d, "value_type": current_value}
            updated.append(d)
        return updated
