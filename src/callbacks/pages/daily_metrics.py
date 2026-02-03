from dash import Input, Output, State, ctx, ALL
from dash.exceptions import PreventUpdate

from src.data_access.db import get_daily_metrics_for_date, update_daily_metrics
from src.helpers.general import minutes_to_hmm
from src.helpers.update_events import build_update_event
from src.layout.toasts import toast, update_toast

DURATION_KEYS = {"sleep_minutes", "screen_minutes"}

import re

_HMM_RE = re.compile(r"^\s*(\d+):([0-5]\d)\s*$")   # h:mm with mm = 00–59
_NUM_RE = re.compile(r"^\s*\d+(\.\d+)?\s*$")      # integer or float


def hmm_to_minutes(x):
    """
    Accepts:
      - None / ""            → None
      - int / float          → float(minutes)
      - numeric string       → float(minutes)
      - 'h:mm'               → minutes as int

    Rejects everything else → None
    """

    if x is None:
        return None

    # Already numeric
    if isinstance(x, (int, float)):
        return float(x)

    s = str(x).strip()
    if s == "":
        return None

    # Strict h:mm
    m = _HMM_RE.match(s)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2))
        return h * 60 + mm

    # Strict numeric string
    if _NUM_RE.match(s):
        return float(s)

    # Anything else is invalid
    return None


def register_daily_metrics_callbacks(app):
    @app.callback(
        Output(
            {"page": "daily-metrics", "name": ALL, "type": "input"},
            "value"
        ),
        Input(
            {"page": "daily-metrics", "name": "date", "type": "date-input"},
            "value"
        ),
        Input(
            {"page": "daily-metrics", "name": ALL, "type": "input"},
            "value"
        ),
        Input("user-id", "data"),
    )
    def load_metrics_for_date(selected_date, component_values,uuid):

        if not selected_date:
            raise PreventUpdate

        triggered = ctx.triggered_id
        load_from_db = (
                triggered is None or
                (isinstance(triggered, dict) and triggered.get("type") == "date-input")
                or (isinstance(triggered, str) and triggered == "user-id")
        )

        if load_from_db:
            current = get_daily_metrics_for_date(selected_date,uuid) or {}
        else:
            # component_values is the list of values for ALL inputs, same order as inputs_list[1]
            in_all_specs = ctx.inputs_list[1]
            current = {
                spec["id"]["name"]: component_values[idx]
                for idx, spec in enumerate(in_all_specs)
            }

        # ---- 2) Validate/normalize into canonical numeric values ----
        validated = {}
        for key, raw in current.items():
            if raw in (None, ""):
                validated[key] = None
                continue

            if key in DURATION_KEYS:
                minutes = hmm_to_minutes(raw)
                validated[key] = minutes if (minutes is not None and minutes > 0) else None
            else:
                try:
                    v = float(raw)
                except (TypeError, ValueError):
                    validated[key] = None
                    continue
                validated[key] = v if v >= 0 else None

        # ---- 3) Build output list once, in output order ----
        out_specs = ctx.outputs_list # for single Output(ALL,...), this is the list
        values = []
        for spec in out_specs:
            metric_key = spec["id"]["name"]
            v = validated.get(metric_key)

            if metric_key in DURATION_KEYS:
                values.append(minutes_to_hmm(v) if v is not None else None)
            else:
                values.append(v)

        return values


    @app.callback(
        Output({"page": "daily-metrics", "name": "save-metrics", "type": "toast"}, "is_open"),
        Output({"page": "daily-metrics", "name": "save-metrics", "type": "toast"}, "children"),
        Output({"page": "daily-metrics", "name": "save-metrics", "type": "toast"}, "icon"),
        Output("last-update-daily-metrics", "data"),
        Input({"page": "daily-metrics", "name": "save-metrics", "type": "button"}, "n_clicks"),
        State({"page": "daily-metrics", "name": "date", "type": "date-input"}, "value"),
        State({"page": "daily-metrics", "name": ALL, "type": "input"}, "value"),
        State("user-id","data"),
        prevent_initial_call=True,
    )
    def save_metrics(n_clicks, selected_date, all_values,uuid):
        if not n_clicks:
            raise PreventUpdate
        if not selected_date:
            raise PreventUpdate

        # Get the IDs corresponding to the ALL State values (same order as all_values)
        in_all_specs = ctx.states_list[1]  # second State in decorator is ALL inputs

        # Build {metric_key: raw_value}
        current = {
            spec["id"]["name"]: all_values[idx]
            for idx, spec in enumerate(in_all_specs)
        }

        # Validate/normalize to canonical numeric values
        validated = {}
        for key, raw in current.items():
            if raw in (None, ""):
                validated[key] = None
                continue

            if key in DURATION_KEYS:
                minutes = hmm_to_minutes(raw)  # should return minutes or None
                validated[key] = minutes if (minutes is not None and minutes > 0) else None
            else:
                try:
                    v = float(raw)
                except (TypeError, ValueError):
                    validated[key] = None
                    continue
                validated[key] = v if v >= 0 else None

        # Build df_long to upsert
        records = []
        for metric_key, value_num in validated.items():
            # Decide whether to write NULL rows or skip them:
            # If you want to skip missing values, uncomment the next 2 lines.
            if value_num is None:
                continue


            records.append(
                {"user_id":uuid,"date": selected_date, "metric_key": metric_key, "value_num": value_num}
            )

        # Write to DB
        update_daily_metrics(records)

        # Optional: return n_clicks unchanged; using button n_clicks output is a cheap no-op output.
        update_event = build_update_event(
            event_type="update",
            entity="daily_metrics",
            user_id=uuid,
            date=selected_date,
        )
        return *update_toast(toast("METRICS_SAVED")), update_event
