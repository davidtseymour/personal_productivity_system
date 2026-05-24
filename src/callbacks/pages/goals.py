from copy import deepcopy
from datetime import date, datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

from dash import ALL, Dash, Input, Output, State, ctx, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.helpers.general import get_category_layout
from src.data_access.goals import (
    compute_goal_actual_minutes,
    get_goals_themes,
    get_or_create_goal_theme,
    load_goal_items_for_set,
    replace_goal_items_for_set,
)
from src.layout.toasts import hide_toast, toast, update_toast
from src.logic.pages.goals import (
    compute_period_start,
    ensure_goal_set_id_for_save,
    get_goal_set_id_for_offset,
    get_goals_timezone,
)


logger = logging.getLogger(__name__)

EDITABLE_HORIZONS = ("QTR", "MONTH", "WEEK")
ALL_HORIZONS = ("QTR", "MONTH", "WEEK", "WEEK_MINUS_1")
HORIZON_OFFSETS = {"QTR": ("QTR", 0), "MONTH": ("MONTH", 0), "WEEK": ("WEEK", 0), "WEEK_MINUS_1": ("WEEK", -1)}
HORIZON_GOAL_COLUMN_LABELS = {
    "QTR": "This quarter's goals",
    "MONTH": "This month's goals",
    "WEEK": "Selected week's goals",
    "WEEK_MINUS_1": "Previous week's goals",
}
STATUS_OPTIONS = [
    {"label": "Active", "value": "ACTIVE"},
    {"label": "Completed", "value": "COMPLETED"},
    {"label": "Dropped", "value": "DROPPED"},
]
STATUS_LABELS = {str(opt["value"]): str(opt["label"]) for opt in STATUS_OPTIONS}
PROGRESS_MODE_OPTIONS = [
    {"label": "Manual", "value": "MANUAL"},
    {"label": "Auto from Time", "value": "AUTO_TIME"},
]
CALC_SOURCE_OPTIONS = [
    {"label": "Tasks", "value": "TASKS"},
    {"label": "Metrics", "value": "METRICS"},
    {"label": "Tasks + Metrics", "value": "TASKS_AND_METRICS"},
]
TARGET_SCOPE_OPTIONS = [
    {"label": "Per Day", "value": "DAY"},
    {"label": "Per Period", "value": "PERIOD"},
]
TARGET_OPERATOR_OPTIONS = [
    {"label": "At Least", "value": "GTE"},
    {"label": "At Most", "value": "LTE"},
]
ROW_EDIT_FIELDS = ("title", "status", "progress_percent")
GOALS_ACTION_COL_WIDTH = "132px"
GOALS_STATUS_COL_WIDTH = "8rem"
GOALS_PROGRESS_COL_WIDTH = "6.5rem"
GOALS_TITLE_COL_MIN_WIDTH = "14rem"


def _empty_goal_row(row_id: str) -> dict:
    return {
        "row_id": row_id,
        "goal_item_id": None,
        "title": "",
        "notes": "",
        "status": "ACTIVE",
        "progress_percent": None,
        "progress_mode": "MANUAL",
        "calc_source": "TASKS_AND_METRICS",
        "target_scope": "PERIOD",
        "target_operator": "GTE",
        "target_minutes": None,
        "weight": 1.0,
        "category_id": None,
        "subcategory": "",
        "activity": "",
        "source": "MANUAL",
        "is_editing": True,
        "is_new": True,
        "edit_backup": None,
    }


def _empty_store() -> dict:
    return {
        "next_row_seq": 1,
        "items": {h: [] for h in ALL_HORIZONS},
    }


def _ensure_store_shape(store: dict | None) -> dict:
    base = _empty_store()
    if not isinstance(store, dict):
        return base

    next_seq = store.get("next_row_seq", 1)
    try:
        base["next_row_seq"] = max(1, int(next_seq))
    except (TypeError, ValueError):
        base["next_row_seq"] = 1

    items = store.get("items")
    if not isinstance(items, dict):
        return base

    for horizon in ALL_HORIZONS:
        rows = items.get(horizon)
        if isinstance(rows, list):
            base["items"][horizon] = rows
    return base


def _has_selected_goal_theme(goal_theme_id: object) -> bool:
    if goal_theme_id in (None, ""):
        return False
    try:
        return int(goal_theme_id) > 0
    except (TypeError, ValueError):
        return bool(goal_theme_id)


def _anchor_now_for_date(selected_date: str | None, tz: str | None = None) -> datetime:
    tz_name = tz or get_goals_timezone()
    tzinfo = ZoneInfo(tz_name)
    default_date = datetime.now(tzinfo).date()
    try:
        selected = date.fromisoformat(selected_date) if selected_date else default_date
    except (TypeError, ValueError):
        selected = default_date
    return datetime.combine(selected, time(hour=12), tzinfo=tzinfo)


def _load_store_for_theme_and_date(user_id: str, goal_theme_id: int, anchor_now_dt: datetime) -> dict:
    store = _empty_store()
    row_seq = 1

    for store_horizon in ALL_HORIZONS:
        horizon, offset = HORIZON_OFFSETS[store_horizon]
        goal_set_id, _ = get_goal_set_id_for_offset(
            user_id,
            horizon,
            offset=offset,
            now_dt=anchor_now_dt,
        )
        loaded_rows = load_goal_items_for_set(
            user_id=user_id,
            goal_set_id=goal_set_id,
            goal_theme_id=goal_theme_id,
        )

        rows_for_horizon: list[dict] = []
        for loaded in loaded_rows:
            goal_item_id = loaded.get("goal_item_id")
            if goal_item_id is None:
                row_id = f"{store_horizon}-legacy-{row_seq}"
            else:
                row_id = f"{store_horizon}-db-{goal_item_id}"
            row_seq += 1
            rows_for_horizon.append(
                {
                    "row_id": row_id,
                    "goal_item_id": goal_item_id,
                    "title": str(loaded.get("title") or ""),
                    "notes": str(loaded.get("notes") or ""),
                    "status": str(loaded.get("status") or "ACTIVE"),
                    "progress_percent": loaded.get("progress_percent"),
                    "progress_mode": str(loaded.get("progress_mode") or "MANUAL"),
                    "calc_source": str(loaded.get("calc_source") or "TASKS"),
                    "target_scope": str(loaded.get("target_scope") or "PERIOD"),
                    "target_operator": str(loaded.get("target_operator") or "GTE"),
                    "target_minutes": loaded.get("target_minutes"),
                    "weight": float(loaded.get("weight") or 1.0),
                    "category_id": loaded.get("category_id"),
                    "subcategory": str(loaded.get("subcategory") or ""),
                    "activity": str(loaded.get("activity") or ""),
                    "source": str(loaded.get("source") or "MANUAL"),
                    "is_editing": False,
                    "is_new": False,
                    "edit_backup": None,
                }
            )
        store["items"][store_horizon] = rows_for_horizon

    store["next_row_seq"] = max(1, row_seq)
    return store


def _merge_ui_fields_into_store(
    store: dict | None,
    field_values: list | None,
    field_ids: list | None,
) -> dict:
    merged = _ensure_store_shape(store)
    if not field_values or not field_ids:
        return merged

    row_lookup: dict[tuple[str, str], dict] = {}
    for horizon in EDITABLE_HORIZONS:
        for row in merged["items"].get(horizon, []):
            row_lookup[(horizon, str(row.get("row_id")))] = row

    for item_id, value in zip(field_ids, field_values):
        if not isinstance(item_id, dict):
            continue
        horizon = item_id.get("horizon")
        field = item_id.get("field")
        row_id = str(item_id.get("row_id"))
        if horizon not in EDITABLE_HORIZONS:
            continue
        row = row_lookup.get((horizon, row_id))
        if row is None:
            continue
        row[field] = value

    return merged


def _add_row(store: dict, horizon: str) -> dict:
    if horizon not in EDITABLE_HORIZONS:
        return store

    new_store = deepcopy(store)
    seq = int(new_store.get("next_row_seq", 1))
    new_store["items"][horizon].append(_empty_goal_row(f"{horizon}-new-{seq}"))
    new_store["next_row_seq"] = seq + 1
    return new_store


def _delete_row(store: dict, horizon: str, row_id: str) -> dict:
    if horizon not in EDITABLE_HORIZONS:
        return store
    new_store = deepcopy(store)
    new_store["items"][horizon] = [
        row for row in new_store["items"].get(horizon, []) if str(row.get("row_id")) != str(row_id)
    ]
    return new_store


def _set_row_editing(store: dict, horizon: str, row_id: str, editing: bool) -> dict:
    if horizon not in EDITABLE_HORIZONS:
        return store
    new_store = deepcopy(store)
    rows = new_store["items"].get(horizon, [])
    for row in rows:
        if str(row.get("row_id")) != str(row_id):
            continue
        if editing and not bool(row.get("is_editing")):
            row["edit_backup"] = {field: row.get(field) for field in ROW_EDIT_FIELDS}
            row["is_editing"] = True
        if not editing:
            row["is_editing"] = False
            row["edit_backup"] = None
        break
    return new_store


def _auto_progress_for_status(status: object) -> float:
    return 100.0 if str(status or "ACTIVE").strip().upper() == "COMPLETED" else 0.0


def _normalize_progress_mode(value: object) -> str:
    mode = str(value or "MANUAL").strip().upper()
    return mode if mode in {"MANUAL", "AUTO_STATUS", "AUTO_TIME"} else "MANUAL"


def _normalize_calc_source(value: object) -> str:
    source = str(value or "TASKS_AND_METRICS").strip().upper()
    return source if source in {"TASKS", "METRICS", "TASKS_AND_METRICS"} else "TASKS_AND_METRICS"


def _normalize_target_scope(value: object) -> str:
    scope = str(value or "PERIOD").strip().upper()
    return scope if scope in {"PERIOD", "DAY"} else "PERIOD"


def _normalize_target_operator(value: object) -> str:
    operator = str(value or "GTE").strip().upper()
    return operator if operator in {"GTE", "LTE"} else "GTE"


def _effective_progress_for_display(row: dict) -> float | None:
    mode = _normalize_progress_mode(row.get("progress_mode"))
    if mode == "AUTO_STATUS":
        return _auto_progress_for_status(row.get("status"))

    value = row.get("progress_percent")
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percent_display(value: object) -> str:
    if value in (None, ""):
        return ""
    try:
        pct = round(float(value), 1)
        pct_text = f"{pct:.1f}".rstrip("0").rstrip(".")
        return f"{pct_text}%"
    except (TypeError, ValueError):
        return ""


def _time_goal_assessment_for_row(
    *,
    user_id: str,
    row: dict,
    horizon: str,
    anchor_now_dt: datetime,
) -> dict[str, object]:
    if horizon not in EDITABLE_HORIZONS:
        return {
            "actual_minutes": 0.0,
            "period_days": 0,
            "elapsed_days": 0,
            "target_total_minutes": None,
            "target_to_date_minutes": None,
            "meets_standard": None,
            "progress_percent": None,
            "result_text": "Unavailable for this horizon.",
        }

    start_date = compute_period_start(horizon, offset=0, now_dt=anchor_now_dt)
    end_date = compute_period_start(horizon, offset=1, now_dt=anchor_now_dt)
    period_days = max(1, (end_date - start_date).days)
    as_of = anchor_now_dt.date()
    elapsed_days = (min(as_of, end_date - timedelta(days=1)) - start_date).days + 1
    if as_of < start_date:
        elapsed_days = 0
    elapsed_days = max(0, min(period_days, elapsed_days))

    category_id = row.get("category_id")
    if category_id in ("", None):
        category_id = None
    else:
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            category_id = None

    calc_source = _normalize_calc_source(row.get("calc_source"))
    target_scope = _normalize_target_scope(row.get("target_scope"))
    target_operator = _normalize_target_operator(row.get("target_operator"))
    target_minutes_raw = row.get("target_minutes")
    try:
        target_minutes = float(target_minutes_raw) if target_minutes_raw not in (None, "") else None
    except (TypeError, ValueError):
        target_minutes = None
    if target_minutes is not None and target_minutes < 0:
        target_minutes = 0.0

    actual_minutes = compute_goal_actual_minutes(
        user_id=user_id,
        start_date=start_date,
        end_date_exclusive=end_date,
        category_id=category_id,
        subcategory=str(row.get("subcategory") or "").strip() or None,
        activity=str(row.get("activity") or "").strip() or None,
        calc_source=calc_source,
    )

    if target_scope == "DAY":
        target_period_total = None if target_minutes is None else target_minutes * period_days
        target_to_date = None if target_minutes is None else target_minutes * elapsed_days
    else:
        target_period_total = target_minutes
        target_to_date = None if target_minutes is None else (target_minutes * elapsed_days / period_days)

    if target_period_total in (None, 0):
        progress_percent = None
    else:
        progress_percent = min(100.0, max(0.0, (actual_minutes / float(target_period_total)) * 100.0))

    meets_standard: bool | None = None
    if target_to_date is not None:
        if target_operator == "GTE":
            meets_standard = actual_minutes >= target_to_date
        else:
            meets_standard = actual_minutes <= target_to_date

    if target_to_date is None:
        result_text = "Set a target to enable standard checking."
    else:
        delta = actual_minutes - float(target_to_date)
        if target_operator == "GTE":
            if meets_standard:
                result_text = f"Meets standard by {delta:.0f} min."
            else:
                result_text = f"Short by {abs(delta):.0f} min."
        else:
            if meets_standard:
                result_text = f"Within cap by {abs(delta):.0f} min."
            else:
                result_text = f"Over cap by {delta:.0f} min."

    return {
        "actual_minutes": float(actual_minutes),
        "period_days": int(period_days),
        "elapsed_days": int(elapsed_days),
        "target_total_minutes": target_period_total,
        "target_to_date_minutes": target_to_date,
        "meets_standard": meets_standard,
        "progress_percent": progress_percent,
        "result_text": result_text,
    }


def _recalculate_auto_time_rows(
    store: dict | None,
    *,
    user_id: str,
    anchor_now_dt: datetime,
    target_horizon: str | None = None,
    target_row_id: str | None = None,
) -> dict:
    shaped = deepcopy(_ensure_store_shape(store))
    for horizon in EDITABLE_HORIZONS:
        if target_horizon is not None and horizon != target_horizon:
            continue
        rows = shaped["items"].get(horizon, [])
        for row in rows:
            if target_row_id is not None and str(row.get("row_id")) != str(target_row_id):
                continue
            if _normalize_progress_mode(row.get("progress_mode")) != "AUTO_TIME":
                continue
            assessment = _time_goal_assessment_for_row(
                user_id=user_id,
                row=row,
                horizon=horizon,
                anchor_now_dt=anchor_now_dt,
            )
            row["progress_percent"] = assessment.get("progress_percent")
    return shaped


def _save_row_edit(store: dict, horizon: str, row_id: str) -> dict:
    if horizon not in EDITABLE_HORIZONS:
        return store
    new_store = deepcopy(store)
    rows = new_store["items"].get(horizon, [])
    for idx, row in enumerate(rows):
        if str(row.get("row_id")) != str(row_id):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            if row.get("is_new"):
                del rows[idx]
                return new_store
            backup = row.get("edit_backup") or {}
            for field in ROW_EDIT_FIELDS:
                if field in backup:
                    row[field] = backup[field]
            row["is_editing"] = False
            row["edit_backup"] = None
            return new_store

        status = str(row.get("status") or "ACTIVE").strip().upper()
        if status not in {"ACTIVE", "COMPLETED", "DROPPED"}:
            status = "ACTIVE"

        mode = _normalize_progress_mode(row.get("progress_mode"))
        if mode == "AUTO_STATUS":
            progress_val = _auto_progress_for_status(status)
        else:
            progress = row.get("progress_percent")
            if progress in ("", None):
                progress_val = None
            else:
                try:
                    progress_val = float(progress)
                except (TypeError, ValueError):
                    progress_val = None
            if progress_val is not None:
                progress_val = max(0.0, min(100.0, progress_val))

        row["title"] = title
        row["status"] = status
        row["progress_percent"] = progress_val
        row["is_editing"] = False
        row["is_new"] = False
        row["edit_backup"] = None
        return new_store
    return new_store


def _undo_row_edit(store: dict, horizon: str, row_id: str) -> dict:
    if horizon not in EDITABLE_HORIZONS:
        return store
    new_store = deepcopy(store)
    rows = new_store["items"].get(horizon, [])
    for idx, row in enumerate(rows):
        if str(row.get("row_id")) != str(row_id):
            continue
        if row.get("is_new"):
            del rows[idx]
            return new_store
        backup = row.get("edit_backup") or {}
        for field in ROW_EDIT_FIELDS:
            if field in backup:
                row[field] = backup[field]
        row["is_editing"] = False
        row["edit_backup"] = None
        return new_store
    return new_store


def _display_status(status: object) -> str:
    status_key = str(status or "").strip().upper()
    if not status_key:
        return ""
    return STATUS_LABELS.get(status_key, status_key.title())


def _display_source(source: object) -> str:
    source_key = str(source or "").strip().upper()
    if source_key == "LEGACY_TEXTAREA":
        return "Legacy Textarea"
    if source_key == "MANUAL":
        return "Manual"
    return source_key.title() if source_key else "Manual"


def _goal_category_options(user_id: str | None) -> list[dict[str, str]]:
    base = [{"label": "Unassigned", "value": ""}]
    if not user_id:
        return base
    loaded = get_category_layout(str(user_id), include_all_option=False)
    for opt in loaded:
        base.append({"label": str(opt.get("label") or ""), "value": str(opt.get("value") or "")})
    return base


def _get_row(store: dict | None, horizon: str, row_id: str) -> dict | None:
    shaped = _ensure_store_shape(store)
    for row in shaped["items"].get(horizon, []):
        if str(row.get("row_id")) == str(row_id):
            return row
    return None


def _apply_goal_item_settings(
    store: dict | None,
    *,
    horizon: str,
    row_id: str,
    category_id_raw: object,
    subcategory: object,
    activity: object,
    progress_mode_raw: object,
    calc_source_raw: object,
    target_scope_raw: object,
    target_operator_raw: object,
    target_minutes_raw: object,
    weight_raw: object,
    notes: object,
) -> dict:
    shaped = deepcopy(_ensure_store_shape(store))
    if horizon not in EDITABLE_HORIZONS:
        return shaped

    try:
        category_id = int(category_id_raw) if category_id_raw not in (None, "", "all") else None
    except (TypeError, ValueError):
        category_id = None

    subcategory_value = str(subcategory or "").strip()
    activity_value = str(activity or "").strip()
    notes_value = str(notes or "").strip()
    progress_mode = _normalize_progress_mode(progress_mode_raw)
    calc_source = _normalize_calc_source(calc_source_raw)
    target_scope = _normalize_target_scope(target_scope_raw)
    target_operator = _normalize_target_operator(target_operator_raw)
    try:
        target_minutes = float(target_minutes_raw) if target_minutes_raw not in (None, "") else None
    except (TypeError, ValueError):
        target_minutes = None
    if target_minutes is not None and target_minutes < 0:
        target_minutes = 0.0

    try:
        weight_value = float(weight_raw)
    except (TypeError, ValueError):
        weight_value = 1.0
    if weight_value <= 0:
        weight_value = 1.0

    if category_id is None:
        subcategory_value = ""
        activity_value = ""

    for row in shaped["items"].get(horizon, []):
        if str(row.get("row_id")) != str(row_id):
            continue
        row["category_id"] = category_id
        row["subcategory"] = subcategory_value
        row["activity"] = activity_value
        row["progress_mode"] = progress_mode
        row["calc_source"] = calc_source
        row["target_scope"] = target_scope
        row["target_operator"] = target_operator
        row["target_minutes"] = target_minutes
        if progress_mode == "AUTO_STATUS":
            row["progress_percent"] = _auto_progress_for_status(row.get("status"))
        row["weight"] = weight_value
        row["notes"] = notes_value
        break

    return shaped


def _goal_column_heading(horizon: str) -> str:
    return HORIZON_GOAL_COLUMN_LABELS.get(horizon, "Goals")


def _render_editable_goals_table(horizon: str, rows: list[dict]) -> html.Div | html.Small:
    add_button_id = {"page": "goals", "name": "add-goal-item", "type": "button", "horizon": horizon}
    header = html.Thead(
        html.Tr(
            [
                html.Th(
                    _goal_column_heading(horizon),
                    style={"minWidth": GOALS_TITLE_COL_MIN_WIDTH, "width": "auto"},
                ),
                html.Th(
                    "Status",
                    style={
                        "width": GOALS_STATUS_COL_WIDTH,
                        "minWidth": GOALS_STATUS_COL_WIDTH,
                        "maxWidth": GOALS_STATUS_COL_WIDTH,
                    },
                ),
                html.Th(
                    "Progress",
                    style={
                        "width": GOALS_PROGRESS_COL_WIDTH,
                        "minWidth": GOALS_PROGRESS_COL_WIDTH,
                        "maxWidth": GOALS_PROGRESS_COL_WIDTH,
                    },
                ),
                html.Th(
                    "Actions",
                    style={
                        "width": GOALS_ACTION_COL_WIDTH,
                        "minWidth": GOALS_ACTION_COL_WIDTH,
                        "maxWidth": GOALS_ACTION_COL_WIDTH,
                    },
                    className="text-center align-middle",
                ),
            ]
        )
    )

    body_rows = []
    for row in rows:
        row_id = str(row.get("row_id"))
        base_id = {"page": "goals", "type": "goal-item-input", "horizon": horizon, "row_id": row_id}
        is_editing = bool(row.get("is_editing"))

        display_progress = _effective_progress_for_display(row)
        progress_mode = _normalize_progress_mode(row.get("progress_mode"))

        body_rows.append(
            html.Tr(
                [
                    (
                        html.Td(
                            dbc.Input(
                                id={**base_id, "field": "title"},
                                type="text",
                                value=row.get("title") or "",
                                placeholder="Goal title",
                                debounce=True,
                                size="sm",
                                style={"width": "100%"},
                            )
                        , style={"minWidth": GOALS_TITLE_COL_MIN_WIDTH})
                        if is_editing
                        else html.Td(
                            html.Span(str(row.get("title") or ""), className="d-inline-block py-1"),
                            style={"minWidth": GOALS_TITLE_COL_MIN_WIDTH},
                        )
                    ),
                    (
                        html.Td(
                            dbc.Select(
                                id={**base_id, "field": "status"},
                                options=STATUS_OPTIONS,
                                value=row.get("status") or "ACTIVE",
                                size="sm",
                                style={"width": "100%"},
                            )
                        ,
                            style={
                                "width": GOALS_STATUS_COL_WIDTH,
                                "minWidth": GOALS_STATUS_COL_WIDTH,
                                "maxWidth": GOALS_STATUS_COL_WIDTH,
                            },
                        )
                        if is_editing
                        else html.Td(
                            html.Span(_display_status(row.get("status")), className="d-inline-block py-1"),
                            style={
                                "width": GOALS_STATUS_COL_WIDTH,
                                "minWidth": GOALS_STATUS_COL_WIDTH,
                                "maxWidth": GOALS_STATUS_COL_WIDTH,
                            },
                        )
                    ),
                    (
                        html.Td(
                            dbc.Input(
                                id={**base_id, "field": "progress_percent"},
                                type="text",
                                inputMode="decimal",
                                pattern="^(100(?:\\.0+)?|[0-9]?[0-9](?:\\.\\d+)?)$",
                                value=display_progress,
                                size="sm",
                                placeholder="%",
                                disabled=progress_mode != "MANUAL",
                                style={"width": "100%"},
                            )
                        , style={
                                "width": GOALS_PROGRESS_COL_WIDTH,
                                "minWidth": GOALS_PROGRESS_COL_WIDTH,
                                "maxWidth": GOALS_PROGRESS_COL_WIDTH,
                            })
                        if is_editing
                        else html.Td(
                            html.Span(
                                _format_percent_display(display_progress),
                                className="d-inline-block py-1",
                            )
                            ,
                            style={
                                "width": GOALS_PROGRESS_COL_WIDTH,
                                "minWidth": GOALS_PROGRESS_COL_WIDTH,
                                "maxWidth": GOALS_PROGRESS_COL_WIDTH,
                            },
                        )
                    ),
                    html.Td(
                        html.Div(
                            [
                                (
                                    dbc.Button(
                                        html.I(className="bi bi-check-lg"),
                                        id={
                                            "page": "goals",
                                            "type": "goal-item-action",
                                            "name": "goal-item-edit-save",
                                            "horizon": horizon,
                                            "row_id": row_id,
                                        },
                                        className="icon-action-btn me-1",
                                        title="Save",
                                        n_clicks=0,
                                    )
                                    if is_editing
                                    else dbc.Button(
                                        html.I(className="bi bi-pencil"),
                                        id={
                                            "page": "goals",
                                            "type": "goal-item-action",
                                            "name": "goal-item-edit",
                                            "horizon": horizon,
                                            "row_id": row_id,
                                        },
                                        className="icon-action-btn table-row-action me-1",
                                        title="Edit",
                                        n_clicks=0,
                                    )
                                ),
                                (
                                    dbc.Button(
                                        html.I(className="bi bi-sliders"),
                                        id={
                                            "page": "goals",
                                            "type": "goal-item-action",
                                            "name": "goal-item-settings",
                                            "horizon": horizon,
                                            "row_id": row_id,
                                        },
                                        className="icon-action-btn table-row-action me-1",
                                        title="Settings",
                                        n_clicks=0,
                                    )
                                    if not is_editing
                                    else None
                                ),
                                (
                                    dbc.Button(
                                        html.I(className="bi bi-trash"),
                                        id={
                                            "page": "goals",
                                            "type": "goal-item-action",
                                            "name": "goal-item-delete",
                                            "horizon": horizon,
                                            "row_id": row_id,
                                        },
                                        className="icon-action-btn table-row-action",
                                        title="Delete",
                                        n_clicks=0,
                                    )
                                    if not is_editing
                                    else None
                                ),
                                (
                                    dbc.Button(
                                        html.I(className="bi bi-x-lg"),
                                        id={
                                            "page": "goals",
                                            "type": "goal-item-action",
                                            "name": "goal-item-edit-undo",
                                            "horizon": horizon,
                                            "row_id": row_id,
                                        },
                                        className="icon-action-btn",
                                        title="Undo",
                                        n_clicks=0,
                                    )
                                    if is_editing
                                    else None
                                ),
                            ],
                            className="d-flex justify-content-center align-items-center",
                        ),
                        className="text-center",
                        style={
                            "width": GOALS_ACTION_COL_WIDTH,
                            "minWidth": GOALS_ACTION_COL_WIDTH,
                            "maxWidth": GOALS_ACTION_COL_WIDTH,
                        },
                    ),
                ]
            )
        )

    if not body_rows:
        body_rows = [
            html.Tr(
                [
                    html.Td(
                        html.Small("No goal items yet.", className="text-muted"),
                        colSpan=4,
                        className="px-2 py-2",
                    )
                ]
            )
        ]

    body_rows.append(
        html.Tr(
            [
                html.Td(
                    html.Div(
                        dbc.Button(
                            html.I(className="bi bi-plus-lg"),
                            id=add_button_id,
                            className="icon-action-btn",
                            title="Add goal item",
                            n_clicks=0,
                        ),
                        className="d-flex justify-content-start",
                    ),
                    colSpan=4,
                    className="py-2 px-2",
                )
            ]
        )
    )

    table = dbc.Table(
        [header, html.Tbody(body_rows)],
        bordered=False,
        hover=True,
        size="sm",
        className="settings-minimal-table mb-1 align-middle",
        responsive=True,
        style={"width": "100%"},
    )
    return table


def _render_readonly_goals_table(horizon: str, rows: list[dict]) -> html.Div | html.Small:
    if not rows:
        return html.Small("No goals from previous week.", className="text-muted px-2")

    header = html.Thead(
        html.Tr(
            [
                html.Th(
                    _goal_column_heading(horizon),
                    style={"minWidth": GOALS_TITLE_COL_MIN_WIDTH, "width": "auto"},
                ),
                html.Th(
                    "Status",
                    style={
                        "width": GOALS_STATUS_COL_WIDTH,
                        "minWidth": GOALS_STATUS_COL_WIDTH,
                        "maxWidth": GOALS_STATUS_COL_WIDTH,
                    },
                ),
                html.Th(
                    "Progress",
                    style={
                        "width": GOALS_PROGRESS_COL_WIDTH,
                        "minWidth": GOALS_PROGRESS_COL_WIDTH,
                        "maxWidth": GOALS_PROGRESS_COL_WIDTH,
                    },
                ),
                html.Th(
                    "",
                    style={
                        "width": GOALS_ACTION_COL_WIDTH,
                        "minWidth": GOALS_ACTION_COL_WIDTH,
                        "maxWidth": GOALS_ACTION_COL_WIDTH,
                    },
                ),
            ]
        )
    )

    body = html.Tbody(
        [
            html.Tr(
                [
                    html.Td(
                        html.Span(str(row.get("title") or ""), className="d-inline-block py-1"),
                        style={"minWidth": GOALS_TITLE_COL_MIN_WIDTH},
                    ),
                    html.Td(
                        html.Span(_display_status(row.get("status")), className="d-inline-block py-1"),
                        style={
                            "width": GOALS_STATUS_COL_WIDTH,
                            "minWidth": GOALS_STATUS_COL_WIDTH,
                            "maxWidth": GOALS_STATUS_COL_WIDTH,
                        },
                    ),
                    html.Td(
                        html.Span(_format_percent_display(row.get("progress_percent")), className="d-inline-block py-1"),
                        style={
                            "width": GOALS_PROGRESS_COL_WIDTH,
                            "minWidth": GOALS_PROGRESS_COL_WIDTH,
                            "maxWidth": GOALS_PROGRESS_COL_WIDTH,
                        },
                    ),
                    html.Td(
                        "",
                        style={
                            "width": GOALS_ACTION_COL_WIDTH,
                            "minWidth": GOALS_ACTION_COL_WIDTH,
                            "maxWidth": GOALS_ACTION_COL_WIDTH,
                        },
                    ),
                ]
            )
            for row in rows
        ]
    )

    table = dbc.Table(
        [header, body],
        bordered=False,
        hover=True,
        size="sm",
        className="settings-minimal-table mb-1 align-middle",
        responsive=True,
        style={"width": "100%"},
    )
    return table


def register_goals_callbacks(app: Dash) -> None:
    @app.callback(
        Output({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        Input({"page": "goals", "name": "prev-week", "type": "button"}, "n_clicks"),
        Input({"page": "goals", "name": "next-week", "type": "button"}, "n_clicks"),
        State({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def cycle_goals_date(_prev_clicks, _next_clicks, selected_date):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate

        base_date = _anchor_now_for_date(selected_date).date()

        source_name = triggered.get("name")
        if source_name == "prev-week":
            return (base_date - timedelta(days=7)).isoformat()
        if source_name == "next-week":
            return (base_date + timedelta(days=7)).isoformat()

        raise PreventUpdate

    @app.callback(
        Output({"page": "goals", "name": "add-theme-modal", "type": "modal"}, "is_open"),
        Output({"page": "goals", "name": "new-theme-name", "type": "input"}, "value"),
        Output({"page": "goals", "name": "new-theme-error", "type": "alert"}, "is_open"),
        Output({"page": "goals", "name": "new-theme-error", "type": "alert"}, "children"),
        Output({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "options"),
        Output({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "value"),
        Output({"page": "goals", "name": "goals", "type": "toast"}, "is_open"),
        Output({"page": "goals", "name": "goals", "type": "toast"}, "children"),
        Output({"page": "goals", "name": "goals", "type": "toast"}, "icon"),
        [
            Input({"page": "goals", "name": "open-add-goal-theme", "type": "button"}, "n_clicks"),
            Input({"page": "goals", "name": "cancel-add-theme", "type": "button"}, "n_clicks"),
            Input({"page": "goals", "name": "save-add-theme", "type": "button"}, "n_clicks"),
        ],
        [
            State({"page": "goals", "name": "add-theme-modal", "type": "modal"}, "is_open"),
            State({"page": "goals", "name": "new-theme-name", "type": "input"}, "value"),
            State("user-id", "data"),
        ],
        prevent_initial_call=True,
    )
    def handle_add_goal_theme(_n_open, _n_cancel, _n_save, _is_open, theme_name, user_id):
        triggered_id = ctx.triggered_id
        if triggered_id is None:
            raise PreventUpdate

        if isinstance(triggered_id, dict) and triggered_id.get("name") == "open-add-goal-theme":
            return True, "", False, "", no_update, no_update, False, no_update, no_update

        if isinstance(triggered_id, dict) and triggered_id.get("name") == "cancel-add-theme":
            return False, "", False, "", no_update, no_update, False, no_update, no_update

        if isinstance(triggered_id, dict) and triggered_id.get("name") == "save-add-theme":
            if not user_id:
                return (
                    True,
                    theme_name or "",
                    True,
                    "No user selected. Cannot save theme.",
                    no_update,
                    no_update,
                    False,
                    no_update,
                    no_update,
                )

            name = (theme_name or "").strip()
            if not name:
                return True, "", True, "Theme name is required.", no_update, no_update, False, no_update, no_update

            try:
                theme_id, created_new = get_or_create_goal_theme(name, user_id)
                options = get_goals_themes(user_id)
                t = toast("GOAL_THEME_ADDED") if created_new else toast("GOAL_THEME_EXISTS")
                return False, "", False, "", options, theme_id, *update_toast(t)
            except Exception as e:
                return True, name, True, f"Could not add theme: {e}", no_update, no_update, False, no_update, no_update

        raise PreventUpdate

    @app.callback(
        Output({"page": "goals", "name": "goal-item-settings-modal", "type": "modal"}, "is_open"),
        Output("goal-item-settings-target-store", "data"),
        Output({"page": "goals", "name": "goal-item-settings-title", "type": "text"}, "children"),
        Output({"page": "goals", "name": "goal-item-settings-progress-mode", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-calc-source", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-target-scope", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-target-operator", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-target-minutes", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-category", "type": "input"}, "options"),
        Output({"page": "goals", "name": "goal-item-settings-category", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-subcategory", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-activity", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-weight", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-notes", "type": "input"}, "value"),
        Output({"page": "goals", "name": "goal-item-settings-assessment", "type": "alert"}, "children"),
        Output({"page": "goals", "name": "goal-item-settings-assessment", "type": "alert"}, "color"),
        Input({"page": "goals", "type": "goal-item-action", "name": ALL, "horizon": ALL, "row_id": ALL}, "n_clicks"),
        Input({"page": "goals", "name": "cancel-goal-item-settings", "type": "button"}, "n_clicks"),
        Input({"page": "goals", "name": "save-goal-item-settings", "type": "button"}, "n_clicks"),
        Input("user-id", "data"),
        State("goals-items-store", "data"),
        State("goal-item-settings-target-store", "data"),
        State({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        prevent_initial_call=True,
    )
    def manage_goal_item_settings_modal(
        _row_actions,
        _n_cancel,
        _n_save,
        user_id,
        items_store,
        target_store,
        selected_date,
    ):
        triggered = ctx.triggered_id
        category_options = _goal_category_options(str(user_id) if user_id else None)
        anchor_now_dt = _anchor_now_for_date(selected_date)

        if not user_id:
            return (
                False,
                {},
                "Goal Settings",
                "MANUAL",
                "TASKS_AND_METRICS",
                "PERIOD",
                "GTE",
                None,
                category_options,
                "",
                "",
                "",
                1.0,
                "",
                "Set a goal target to enable standard checking.",
                "secondary",
            )

        if triggered == "user-id":
            return (
                False,
                {},
                "Goal Settings",
                "MANUAL",
                "TASKS_AND_METRICS",
                "PERIOD",
                "GTE",
                None,
                category_options,
                "",
                "",
                "",
                1.0,
                "",
                "Set a goal target to enable standard checking.",
                "secondary",
            )

        if isinstance(triggered, dict) and triggered.get("type") == "goal-item-action":
            if str(triggered.get("name") or "") != "goal-item-settings":
                raise PreventUpdate

            horizon = str(triggered.get("horizon") or "")
            row_id = str(triggered.get("row_id") or "")
            row = _get_row(items_store, horizon, row_id)
            if row is None:
                raise PreventUpdate

            title = str(row.get("title") or "").strip() or "Goal"
            category_value = row.get("category_id")
            category_value = "" if category_value in (None, "") else str(category_value)
            progress_mode = _normalize_progress_mode(row.get("progress_mode"))
            if progress_mode == "AUTO_STATUS":
                progress_mode = "MANUAL"
            calc_source = _normalize_calc_source(row.get("calc_source"))
            target_scope = _normalize_target_scope(row.get("target_scope"))
            target_operator = _normalize_target_operator(row.get("target_operator"))
            target_minutes = row.get("target_minutes")
            assessment = _time_goal_assessment_for_row(
                user_id=str(user_id),
                row=row,
                horizon=horizon,
                anchor_now_dt=anchor_now_dt,
            )
            target_to_date = assessment.get("target_to_date_minutes")
            if target_to_date is None:
                target_to_date_text = "—"
            else:
                target_to_date_text = f"{float(target_to_date):.0f} min"
            assessment_text = (
                f"Actual: {assessment.get('actual_minutes', 0):.0f} min | "
                f"To Date Target: {target_to_date_text} | "
                f"{assessment.get('result_text', '')}"
            )
            assessment_color = "success" if assessment.get("meets_standard") is True else (
                "danger" if assessment.get("meets_standard") is False else "secondary"
            )

            return (
                True,
                {"horizon": horizon, "row_id": row_id},
                f"Goal Settings: {title}",
                progress_mode,
                calc_source,
                target_scope,
                target_operator,
                target_minutes,
                category_options,
                category_value,
                str(row.get("subcategory") or ""),
                str(row.get("activity") or ""),
                float(row.get("weight") or 1.0),
                str(row.get("notes") or ""),
                assessment_text,
                assessment_color,
            )

        if isinstance(triggered, dict) and triggered.get("name") in {
            "cancel-goal-item-settings",
            "save-goal-item-settings",
        }:
            return (
                False,
                target_store if isinstance(target_store, dict) else {},
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                category_options,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
            )

        raise PreventUpdate

    @app.callback(
        Output("goals-items-store", "data"),
        Output({"page": "goals", "name": "save-goals", "type": "toast"}, "is_open"),
        Output({"page": "goals", "name": "save-goals", "type": "toast"}, "children"),
        Output({"page": "goals", "name": "save-goals", "type": "toast"}, "icon"),
        Input({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "value"),
        Input({"page": "goals", "name": "date", "type": "date-input"}, "value"),
        Input({"page": "goals", "name": "update-goals", "type": "button"}, "n_clicks"),
        Input({"page": "goals", "name": "add-goal-item", "type": "button", "horizon": ALL}, "n_clicks"),
        Input({"page": "goals", "type": "goal-item-action", "name": ALL, "horizon": ALL, "row_id": ALL}, "n_clicks"),
        Input({"page": "goals", "name": "save-goal-item-settings", "type": "button"}, "n_clicks"),
        Input("user-id", "data"),
        State("goals-items-store", "data"),
        State({"page": "goals", "type": "goal-item-input", "horizon": ALL, "field": ALL, "row_id": ALL}, "value"),
        State({"page": "goals", "type": "goal-item-input", "horizon": ALL, "field": ALL, "row_id": ALL}, "id"),
        State("goal-item-settings-target-store", "data"),
        State({"page": "goals", "name": "goal-item-settings-progress-mode", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-calc-source", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-target-scope", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-target-operator", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-target-minutes", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-category", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-subcategory", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-activity", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-weight", "type": "input"}, "value"),
        State({"page": "goals", "name": "goal-item-settings-notes", "type": "input"}, "value"),
        prevent_initial_call=True,
    )
    def goals_store_controller(
        goal_theme_id,
        selected_date,
        _n_update,
        _n_add_goal_items,
        _n_row_actions,
        _n_save_row_settings,
        user_id,
        current_store,
        field_values,
        field_ids,
        settings_target_store,
        settings_progress_mode,
        settings_calc_source,
        settings_target_scope,
        settings_target_operator,
        settings_target_minutes,
        settings_category,
        settings_subcategory,
        settings_activity,
        settings_weight,
        settings_notes,
    ):
        triggered = ctx.triggered_id
        if triggered is None:
            raise PreventUpdate

        if not user_id:
            return _empty_store(), *hide_toast()

        if not _has_selected_goal_theme(goal_theme_id):
            return _empty_store(), *hide_toast()

        anchor_now_dt = _anchor_now_for_date(selected_date)

        if isinstance(triggered, dict) and (
            triggered.get("name") == "goal-theme" or triggered.get("type") == "date-input"
        ):
            loaded = _load_store_for_theme_and_date(str(user_id), int(goal_theme_id), anchor_now_dt)
            loaded = _recalculate_auto_time_rows(loaded, user_id=str(user_id), anchor_now_dt=anchor_now_dt)
            return loaded, *hide_toast()

        merged_store = _merge_ui_fields_into_store(current_store, field_values, field_ids)

        if isinstance(triggered, dict) and triggered.get("name") == "add-goal-item":
            horizon = str(triggered.get("horizon") or "")
            return _add_row(merged_store, horizon), *hide_toast()

        if isinstance(triggered, dict) and triggered.get("name") == "save-goal-item-settings":
            target = settings_target_store if isinstance(settings_target_store, dict) else {}
            horizon = str(target.get("horizon") or "")
            row_id = str(target.get("row_id") or "")
            if not horizon or not row_id:
                raise PreventUpdate
            updated = _apply_goal_item_settings(
                merged_store,
                horizon=horizon,
                row_id=row_id,
                category_id_raw=settings_category,
                subcategory=settings_subcategory,
                activity=settings_activity,
                progress_mode_raw=settings_progress_mode,
                calc_source_raw=settings_calc_source,
                target_scope_raw=settings_target_scope,
                target_operator_raw=settings_target_operator,
                target_minutes_raw=settings_target_minutes,
                weight_raw=settings_weight,
                notes=settings_notes,
            )
            updated = _recalculate_auto_time_rows(
                updated,
                user_id=str(user_id),
                anchor_now_dt=anchor_now_dt,
                target_horizon=horizon,
                target_row_id=row_id,
            )
            return updated, *hide_toast()

        if isinstance(triggered, dict) and triggered.get("type") == "goal-item-action":
            action = str(triggered.get("name") or "")
            horizon = str(triggered.get("horizon") or "")
            row_id = str(triggered.get("row_id") or "")
            if action == "goal-item-edit":
                return _set_row_editing(merged_store, horizon, row_id, True), *hide_toast()
            if action == "goal-item-edit-save":
                saved_store = _save_row_edit(merged_store, horizon, row_id)
                saved_store = _recalculate_auto_time_rows(
                    saved_store,
                    user_id=str(user_id),
                    anchor_now_dt=anchor_now_dt,
                    target_horizon=horizon,
                    target_row_id=row_id,
                )
                return saved_store, *hide_toast()
            if action == "goal-item-edit-undo":
                return _undo_row_edit(merged_store, horizon, row_id), *hide_toast()
            if action == "goal-item-delete":
                return _delete_row(merged_store, horizon, row_id), *hide_toast()
            raise PreventUpdate

        if isinstance(triggered, dict) and triggered.get("name") == "update-goals":
            try:
                merged_store = _recalculate_auto_time_rows(
                    merged_store,
                    user_id=str(user_id),
                    anchor_now_dt=anchor_now_dt,
                )
                for horizon in EDITABLE_HORIZONS:
                    save_id = ensure_goal_set_id_for_save(
                        user_id=str(user_id),
                        horizon=horizon,
                        now_dt=anchor_now_dt,
                    )
                    replace_goal_items_for_set(
                        user_id=str(user_id),
                        goal_set_id=int(save_id),
                        goal_theme_id=int(goal_theme_id),
                        items=merged_store["items"].get(horizon, []),
                    )

                reloaded = _load_store_for_theme_and_date(str(user_id), int(goal_theme_id), anchor_now_dt)
                return reloaded, *update_toast(toast("GOALS_SAVED"))
            except Exception:
                logger.exception("Failed saving goals for user_id=%s theme_id=%s", user_id, goal_theme_id)
                return merged_store, *update_toast(toast("GOALS_SAVE_FAILED"))

        if triggered == "user-id":
            loaded = _load_store_for_theme_and_date(str(user_id), int(goal_theme_id), anchor_now_dt)
            loaded = _recalculate_auto_time_rows(loaded, user_id=str(user_id), anchor_now_dt=anchor_now_dt)
            return loaded, *hide_toast()

        raise PreventUpdate

    @app.callback(
        Output({"page": "goals", "name": "goal-items-container", "type": "container", "horizon": "QTR"}, "children"),
        Output({"page": "goals", "name": "goal-items-container", "type": "container", "horizon": "MONTH"}, "children"),
        Output({"page": "goals", "name": "goal-items-container", "type": "container", "horizon": "WEEK"}, "children"),
        Output({"page": "goals", "name": "goal-items-container", "type": "container", "horizon": "WEEK_MINUS_1"}, "children"),
        Input("goals-items-store", "data"),
        Input("user-id", "data"),
        Input({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "value"),
    )
    def render_goal_sections(store, user_id, goal_theme_id):
        if not user_id:
            empty = html.Div()
            return empty, empty, empty, empty

        if not _has_selected_goal_theme(goal_theme_id):
            empty_msg = html.Small("Select a goal theme to view items.", className="text-muted px-2")
            empty = html.Div()
            return empty_msg, empty, empty, empty

        shaped = _ensure_store_shape(store)
        quarter = _render_editable_goals_table("QTR", shaped["items"].get("QTR", []))
        month = _render_editable_goals_table("MONTH", shaped["items"].get("MONTH", []))
        week = _render_editable_goals_table("WEEK", shaped["items"].get("WEEK", []))
        previous_week = _render_readonly_goals_table("WEEK_MINUS_1", shaped["items"].get("WEEK_MINUS_1", []))
        return quarter, month, week, previous_week

    @app.callback(
        Output({"page": "goals", "name": "update-goals", "type": "button"}, "style"),
        Input("user-id", "data"),
        Input({"page": "goals", "name": "goal-theme", "type": "dropdown"}, "value"),
    )
    def toggle_update_goals_button(user_id, goal_theme_id):
        controls_visible = bool(user_id) and _has_selected_goal_theme(goal_theme_id)
        return {} if controls_visible else {"display": "none"}
