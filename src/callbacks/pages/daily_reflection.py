from datetime import datetime
from dash import Input, Output, State, no_update
from dash.dependencies import ALL
from pathlib import Path
import json
import os

from src.layout.toasts import hide_toast, toast, update_toast


def _atomic_write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def _read_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def register_daily_reflection_callbacks(app, config):
    reviews_dir = Path(config["daily_review_dir"]).resolve()

    @app.callback(
        Output({"page": "daily-review", "type": "toast", "name": "save_review"}, "is_open"),
        Output({"page": "daily-review", "type": "toast", "name": "save_review"}, "children"),
        Output({"page": "daily-review", "type": "toast", "name": "save_review"}, "icon"),
        Input({"page": "daily-review", "name": "submit", "type": "button"}, "n_clicks"),
        # Grab all input + textarea values, ids, and validity flags
        State({"page": "daily-review", "type": ALL, "name": ALL}, "value"),
        State({"page": "daily-review", "type": ALL, "name": ALL}, "id"),
        State({"page": "daily-review", "type": ALL, "name": ALL}, "invalid"),
        prevent_initial_call=True,
    )
    def save_form(_, values, ids, invalids):
        # --- Validate all fields ---
        # If any component explicitly reports invalid=True, block save
        if any(v is True for v in (invalids or [])):
            return True, "Error: Please correct invalid fields before saving.", "danger"

        # --- Build payload dynamically ---
        payload = {}
        for val, idd in zip(values, ids):
            t = idd.get("type")
            if t in ("input", "textarea"):
                name = idd.get("name")
                payload[name.replace("-", "_")] = val or ""

        # --- Required defaults ---
        raw_date = payload.get("date")
        try:
            # Expect YYYY-MM-DD
            datetime.strptime(raw_date, "%Y-%m-%d")
            day = raw_date
        except (TypeError, ValueError):
            return True, f"Error: Invalid date format ({raw_date}). Expected YYYY-MM-DD.", "danger"

        payload["review_date"] = day
        payload["version"] = 1

        # --- Save JSON file ---
        try:
            target = reviews_dir / f"{day}.json"
            _atomic_write_json(target, payload)
            t = toast("DAILY_REVIEW_SAVED", day=day)
            return update_toast(t)
        except Exception:
            t = toast("DAILY_REVIEW_SAVE_FAILED")
            return update_toast(t)

    # ---------- LOAD (reverse) ----------
    @app.callback(
        Output({"page": "daily-review", "type": "toast", "name": "load_review"}, "is_open"),
        Output({"page": "daily-review", "type": "toast", "name": "load_review"}, "children"),
        Output({"page": "daily-review", "type": "toast", "name": "load_review"}, "icon"),
        # Fill values for all value-bearing components in this page
        Output({"page": "daily-review", "type": ALL, "name": ALL}, "value"),
        # Reset invalid flags
        Output({"page": "daily-review", "type": ALL, "name": ALL}, "invalid"),
        # Trigger: date input (assumes your date field is an input named 'date')
        Input({"page": "daily-review", "name": "date", "type": "input"}, "value"),
        State({"page": "daily-review", "type": ALL, "name": ALL}, "id"),
    )
    def load_form(selected_date, ids):
        # Validate date first (silent failure; keep current values)
        try:
            datetime.strptime(selected_date or "", "%Y-%m-%d")
        except (TypeError, ValueError):
            return *hide_toast(), [no_update] * len(ids), [no_update] * len(ids)

        target = reviews_dir / f"{selected_date}.json"

        # Prepare defaults (clear everything except keep date echo)
        default_values = []
        for idd in ids:
            t = idd.get("type")
            n = idd.get("name")
            if t in ("input", "textarea"):
                # keep the date box showing the selected date; clear others
                if n == "date":
                    default_values.append(selected_date)
                else:
                    default_values.append("")
            else:
                default_values.append(no_update)
        default_invalids = [False] * len(ids)

        # Load file and map keys back to inputs/textareas (silent failure on missing/bad file)
        try:
            data = _read_json(target)
        except Exception:
            return *hide_toast(), default_values, default_invalids

        # Build values list aligned to ids
        filled_values = []
        for idd in ids:
            t = idd.get("type")
            n = idd.get("name")
            if t in ("input", "textarea"):
                key = (n or "").replace("-", "_")
                if n == "date":
                    # Always set date from selected control (source of truth)
                    filled_values.append(selected_date)
                else:
                    filled_values.append(data.get(key, ""))
            else:
                filled_values.append(no_update)

        return *hide_toast(), filled_values, default_invalids
