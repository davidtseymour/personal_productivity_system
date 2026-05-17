from datetime import date, datetime, timedelta
from typing import Any

from dash import Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
import pandas as pd

from src.data_access.db import bulk_update_tasks, load_tasks_for_date_range
from src.helpers.general import get_category_id_list
from src.layout.pages.daily_task_log import render_daily_task_log_table


def _to_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _selected_weekdays_from_clicks(
    weekday_clicks: list[int | None],
    weekday_map: list[int],
) -> set[int]:
    return {
        weekday_map[idx]
        for idx, clicks in enumerate(weekday_clicks)
        if (clicks or 0) % 2 == 0
    }


def _filter_task_rows(
    task_rows: pd.DataFrame,
    selected_weekdays: set[int],
    category_value: Any,
    subcategory_filter: str | None,
    activity_filter: str | None,
) -> pd.DataFrame:
    filtered = task_rows.copy()

    weekday_values = pd.to_datetime(filtered["date"], errors="coerce").dt.weekday
    filtered = filtered[weekday_values.isin(selected_weekdays)].copy()
    if filtered.empty:
        return filtered

    selected_category_id = _to_int_or_none(category_value)
    if selected_category_id is not None:
        filtered = filtered[filtered["category_id"] == selected_category_id].copy()
        if filtered.empty:
            return filtered

    subcategory_query = (subcategory_filter or "").strip()
    if subcategory_query:
        filtered = filtered[
            filtered["subcategory"].fillna("").astype(str).str.contains(
                subcategory_query, case=False, regex=False
            )
        ].copy()
        if filtered.empty:
            return filtered

    activity_query = (activity_filter or "").strip()
    if activity_query:
        filtered = filtered[
            filtered["activity"].fillna("").astype(str).str.contains(
                activity_query, case=False, regex=False
            )
        ].copy()

    return filtered


def _rank_case_sensitive_matches_first(
    filtered: pd.DataFrame,
    subcategory_filter: str | None,
    activity_filter: str | None,
) -> pd.DataFrame:
    subcategory_query = (subcategory_filter or "").strip()
    activity_query = (activity_filter or "").strip()
    if not subcategory_query and not activity_query:
        return filtered

    case_rank = 0
    if subcategory_query:
        subcat_case_match = filtered["subcategory"].fillna("").astype(str).str.contains(
            subcategory_query, case=True, regex=False
        )
        case_rank = case_rank + subcat_case_match.astype(int)

    if activity_query:
        activity_case_match = filtered["activity"].fillna("").astype(str).str.contains(
            activity_query, case=True, regex=False
        )
        case_rank = case_rank + activity_case_match.astype(int)

    ranked = filtered.copy()
    ranked["_case_rank"] = case_rank
    ranked["_base_order"] = range(len(ranked))
    ranked = ranked.sort_values(
        by=["_case_rank", "_base_order"],
        ascending=[False, True],
        kind="mergesort",
    ).drop(columns=["_case_rank", "_base_order"])
    return ranked


def _task_snapshot(filtered: pd.DataFrame) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []
    if filtered is None or filtered.empty:
        return snapshot

    columns = ["task_id", "category_id", "subcategory", "activity"]
    for record in filtered[columns].to_dict("records"):
        task_id = _to_int_or_none(record.get("task_id"))
        if task_id is None:
            continue
        category_id = _to_int_or_none(record.get("category_id"))
        snapshot.append(
            {
                "task_id": task_id,
                "category_id": category_id,
                "subcategory": str(record.get("subcategory") or ""),
                "activity": str(record.get("activity") or ""),
            }
        )
    return snapshot


def _apply_exact_case_sensitive_match(
    snapshot: list[dict[str, Any]],
    match_category: Any,
    match_subcategory: str | None,
    match_activity: str | None,
) -> list[int]:
    category_match_id = _to_int_or_none(match_category)
    subcategory_match = (match_subcategory or "").strip()
    activity_match = (match_activity or "").strip()

    matched_ids: list[int] = []
    for row in snapshot:
        row_task_id = _to_int_or_none(row.get("task_id"))
        if row_task_id is None:
            continue

        if category_match_id is not None and _to_int_or_none(row.get("category_id")) != category_match_id:
            continue
        if subcategory_match and str(row.get("subcategory") or "") != subcategory_match:
            continue
        if activity_match and str(row.get("activity") or "") != activity_match:
            continue

        matched_ids.append(row_task_id)

    # Keep stable ordering but remove duplicates.
    deduped: list[int] = []
    seen: set[int] = set()
    for task_id in matched_ids:
        if task_id in seen:
            continue
        seen.add(task_id)
        deduped.append(task_id)
    return deduped


def _build_bulk_confirm_summary(
    *,
    count: int,
    updates: dict[str, Any],
    match_category: Any,
    match_subcategory: str | None,
    match_activity: str | None,
) -> list[Any]:
    update_parts: list[str] = []
    if "category_id" in updates:
        update_parts.append(f"Category ID -> {updates['category_id']}")
    if "subcategory" in updates:
        update_parts.append(f"Subcategory -> {updates['subcategory']}")
    if "activity" in updates:
        update_parts.append(f"Activity -> {updates['activity']}")

    match_parts: list[str] = []
    category_match_id = _to_int_or_none(match_category)
    if category_match_id is not None:
        match_parts.append(f"Category ID = {category_match_id}")

    sub_match = (match_subcategory or "").strip()
    if sub_match:
        match_parts.append(f"Subcategory = '{sub_match}'")

    act_match = (match_activity or "").strip()
    if act_match:
        match_parts.append(f"Activity = '{act_match}'")

    if not match_parts:
        match_parts.append("No exact-match constraints")

    return [
        html.Div(f"This will update {count} task(s).", className="mb-2 fw-semibold"),
        html.Div(f"Set: {', '.join(update_parts)}", className="mb-1"),
        html.Div(f"Match: {', '.join(match_parts)}"),
    ]


def register_task_explorer_callbacks(app: Dash) -> None:
    page = "task-explorer"
    weekday_map = [6, 0, 1, 2, 3, 4, 5]  # S, M, T, W, T, F, S -> Python weekday ints

    @app.callback(
        Output({"page": page, "name": "start-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-start-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-start-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "start-date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_task_explorer_start_date(
        _prev_clicks,
        _next_clicks,
        start_date_value,
    ):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            start_dt = date.fromisoformat(start_date_value) if start_date_value else date.today()
        except (TypeError, ValueError):
            start_dt = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-start-day":
            delta = -1
        elif source_name == "next-start-day":
            delta = 1
        else:
            raise PreventUpdate

        return (start_dt + timedelta(days=delta)).isoformat()

    @app.callback(
        Output({"page": page, "name": "end-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "prev-end-day", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "next-end-day", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "end-date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_task_explorer_end_date(
        _prev_clicks,
        _next_clicks,
        end_date_value,
    ):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        try:
            end_dt = date.fromisoformat(end_date_value) if end_date_value else date.today()
        except (TypeError, ValueError):
            end_dt = date.today()

        source_name = triggered.get("name")
        if source_name == "prev-end-day":
            delta = -1
        elif source_name == "next-end-day":
            delta = 1
        else:
            raise PreventUpdate

        return (end_dt + timedelta(days=delta)).isoformat()

    @app.callback(
        Output({"page": page, "name": "dow-sun", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-mon", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-tue", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-wed", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-thu", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-fri", "type": "button"}, "active"),
        Output({"page": page, "name": "dow-sat", "type": "button"}, "active"),
        Input({"page": page, "name": "dow-sun", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-mon", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-tue", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-wed", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-thu", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-fri", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-sat", "type": "button"}, "n_clicks"),
    )
    def update_weekday_button_state(*weekday_clicks):
        return [((clicks or 0) % 2 == 0) for clicks in weekday_clicks]

    @app.callback(
        Output({"page": page, "name": "task-table", "type": "table"}, "children"),
        Output({"page": page, "name": "filtered-task-snapshot", "type": "store"}, "data"),
        Input({"page": page, "name": "start-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "end-date", "type": "date-input"}, "value"),
        Input({"page": page, "name": "category", "type": "dropdown"}, "value"),
        Input({"page": page, "name": "subcategory", "type": "input"}, "value"),
        Input({"page": page, "name": "activity", "type": "input"}, "value"),
        Input({"page": page, "name": "dow-sun", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-mon", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-tue", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-wed", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-thu", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-fri", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "dow-sat", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "bulk-edit-refresh", "type": "store"}, "data"),
        Input("user-id", "data"),
        Input("task-nav-update-store", "data"),
        Input("last-update", "data"),
    )
    def update_task_explorer_table(
        start_date_value,
        end_date_value,
        category_value,
        subcategory_filter,
        activity_filter,
        n_sun,
        n_mon,
        n_tue,
        n_wed,
        n_thu,
        n_fri,
        n_sat,
        _bulk_refresh,
        user_id,
        _task_reload,
        _last_update,
    ):
        if not user_id or not start_date_value or not end_date_value:
            raise PreventUpdate

        weekday_clicks = [n_sun, n_mon, n_tue, n_wed, n_thu, n_fri, n_sat]
        selected_weekdays = _selected_weekdays_from_clicks(weekday_clicks, weekday_map)
        if not selected_weekdays:
            return render_daily_task_log_table(None, table_page=page, show_date=True), []

        try:
            start_dt = date.fromisoformat(start_date_value)
            end_dt = date.fromisoformat(end_date_value)
        except (TypeError, ValueError):
            raise PreventUpdate

        range_start = min(start_dt, end_dt).isoformat()
        range_end = max(start_dt, end_dt).isoformat()
        task_rows = load_tasks_for_date_range(
            user_id=user_id,
            start_date=range_start,
            end_date=range_end,
        )

        if task_rows is None or task_rows.empty:
            return render_daily_task_log_table(task_rows, table_page=page, show_date=True), []

        filtered = _filter_task_rows(
            task_rows,
            selected_weekdays,
            category_value,
            subcategory_filter,
            activity_filter,
        )
        if filtered.empty:
            return render_daily_task_log_table(filtered, table_page=page, show_date=True), []

        ranked = _rank_case_sensitive_matches_first(
            filtered,
            subcategory_filter,
            activity_filter,
        )
        snapshot = _task_snapshot(ranked)
        return render_daily_task_log_table(ranked, table_page=page, show_date=True), snapshot

    @app.callback(
        Output({"page": page, "name": "bulk-edit-modal", "type": "modal"}, "is_open"),
        Output({"page": page, "name": "bulk-edit-error", "type": "text"}, "children", allow_duplicate=True),
        Output({"page": page, "name": "bulk-match-category", "type": "dropdown"}, "value"),
        Output({"page": page, "name": "bulk-match-subcategory", "type": "input"}, "value"),
        Output({"page": page, "name": "bulk-match-activity", "type": "input"}, "value"),
        Output({"page": page, "name": "bulk-set-category", "type": "dropdown"}, "value"),
        Output({"page": page, "name": "bulk-set-subcategory", "type": "input"}, "value"),
        Output({"page": page, "name": "bulk-set-activity", "type": "input"}, "value"),
        Input({"page": page, "name": "open-bulk-edit", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "cancel-bulk-edit", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "confirm-bulk-edit", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "bulk-edit-modal", "type": "modal"}, "is_open"),
        State({"page": page, "name": "category", "type": "dropdown"}, "value"),
        State({"page": page, "name": "subcategory", "type": "input"}, "value"),
        State({"page": page, "name": "activity", "type": "input"}, "value"),
        prevent_initial_call=True,
    )
    def toggle_bulk_edit_modal(
        _open_clicks,
        _cancel_clicks,
        _confirm_clicks,
        is_open,
        app_category_filter,
        app_subcategory_filter,
        app_activity_filter,
    ):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        name = triggered.get("name")
        if name == "open-bulk-edit":
            category_match = app_category_filter if app_category_filter not in (None, "") else "all"
            return (
                True,
                "",
                category_match,
                (app_subcategory_filter or ""),
                (app_activity_filter or ""),
                None,
                "",
                "",
            )
        if name in {"cancel-bulk-edit", "confirm-bulk-edit"}:
            return False, "", no_update, no_update, no_update, no_update, no_update, no_update
        return is_open, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    @app.callback(
        Output({"page": page, "name": "bulk-edit-modal", "type": "modal"}, "is_open", allow_duplicate=True),
        Output({"page": page, "name": "bulk-edit-confirm-modal", "type": "modal"}, "is_open"),
        Output({"page": page, "name": "bulk-edit-confirm-summary", "type": "text"}, "children"),
        Output({"page": page, "name": "bulk-edit-pending", "type": "store"}, "data"),
        Output({"page": page, "name": "bulk-edit-error", "type": "text"}, "children"),
        Input({"page": page, "name": "review-bulk-edit", "type": "button"}, "n_clicks"),
        Input({"page": page, "name": "cancel-bulk-confirm", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "filtered-task-snapshot", "type": "store"}, "data"),
        State({"page": page, "name": "bulk-match-category", "type": "dropdown"}, "value"),
        State({"page": page, "name": "bulk-match-subcategory", "type": "input"}, "value"),
        State({"page": page, "name": "bulk-match-activity", "type": "input"}, "value"),
        State({"page": page, "name": "bulk-set-category", "type": "dropdown"}, "value"),
        State({"page": page, "name": "bulk-set-subcategory", "type": "input"}, "value"),
        State({"page": page, "name": "bulk-set-activity", "type": "input"}, "value"),
        prevent_initial_call=True,
    )
    def review_bulk_edit(
        _review_clicks,
        _cancel_confirm_clicks,
        filtered_snapshot,
        match_category_value,
        match_subcategory_value,
        match_activity_value,
        set_category_value,
        set_subcategory_value,
        set_activity_value,
    ):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        if triggered.get("name") == "cancel-bulk-confirm":
            return True, False, no_update, no_update, no_update
        if triggered.get("name") != "review-bulk-edit":
            raise PreventUpdate

        updates: dict[str, Any] = {}
        selected_category_id = _to_int_or_none(set_category_value)
        if set_category_value not in (None, "") and selected_category_id is None:
            return no_update, False, no_update, {}, "Select a valid category for update."
        if selected_category_id is not None:
            updates["category_id"] = selected_category_id

        set_subcategory = (set_subcategory_value or "").strip()
        if set_subcategory:
            updates["subcategory"] = set_subcategory

        set_activity = (set_activity_value or "").strip()
        if set_activity:
            updates["activity"] = set_activity

        if not updates:
            return no_update, False, no_update, {}, "Enter at least one new value to apply."

        snapshot_rows = filtered_snapshot if isinstance(filtered_snapshot, list) else []
        matched_task_ids = _apply_exact_case_sensitive_match(
            snapshot_rows,
            match_category_value,
            match_subcategory_value,
            match_activity_value,
        )
        if not matched_task_ids:
            return no_update, False, no_update, {}, "No matching tasks for the exact-match criteria."

        confirm_summary = _build_bulk_confirm_summary(
            count=len(matched_task_ids),
            updates=updates,
            match_category=match_category_value,
            match_subcategory=match_subcategory_value,
            match_activity=match_activity_value,
        )
        pending_payload = {
            "task_ids": matched_task_ids,
            "updates": updates,
            "count": len(matched_task_ids),
        }
        return False, True, confirm_summary, pending_payload, ""

    @app.callback(
        Output({"page": page, "name": "bulk-edit-confirm-modal", "type": "modal"}, "is_open", allow_duplicate=True),
        Output({"page": page, "name": "bulk-edit-refresh", "type": "store"}, "data"),
        Output({"page": page, "name": "bulk-edit", "type": "toast"}, "is_open"),
        Output({"page": page, "name": "bulk-edit", "type": "toast"}, "children"),
        Output({"page": page, "name": "bulk-edit", "type": "toast"}, "icon"),
        Input({"page": page, "name": "confirm-bulk-edit", "type": "button"}, "n_clicks"),
        State({"page": page, "name": "bulk-edit-pending", "type": "store"}, "data"),
        State("user-id", "data"),
        prevent_initial_call=True,
    )
    def apply_bulk_edit(
        _confirm_clicks,
        pending_payload,
        user_id,
    ):
        if not user_id or not isinstance(pending_payload, dict):
            raise PreventUpdate

        raw_task_ids = pending_payload.get("task_ids") or []
        updates = pending_payload.get("updates") or {}
        task_ids = [_to_int_or_none(task_id) for task_id in raw_task_ids]
        task_ids = [task_id for task_id in task_ids if task_id is not None]
        if not task_ids:
            return False, no_update, True, "No tasks were selected for bulk edit.", "warning"
        if not updates:
            return False, no_update, True, "No update fields were provided.", "warning"

        allowed_categories = set(get_category_id_list(user_id))
        category_id = updates.get("category_id")
        if category_id is not None and category_id not in allowed_categories:
            return False, no_update, True, "Invalid category for this user.", "danger"

        if "subcategory" in updates and not str(updates["subcategory"]).strip():
            return False, no_update, True, "Subcategory cannot be blank.", "danger"
        if "activity" in updates and not str(updates["activity"]).strip():
            return False, no_update, True, "Activity cannot be blank.", "danger"

        rows_updated = bulk_update_tasks(user_id, task_ids, updates)
        refresh_token = datetime.now().isoformat()

        if rows_updated <= 0:
            return False, no_update, True, "No tasks were updated.", "warning"
        return (
            False,
            refresh_token,
            True,
            f"Updated {rows_updated} task(s).",
            "success",
        )
