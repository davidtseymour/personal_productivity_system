from dash import Input, Output, State
from dash import html

from src.helpers.validate_tasks import validate_process_time_inputs, calculate_hh_mm_placeholders, \
    validate_category_complete
from src.layout.pages.log_time import create_task_inputs

def populate_edit_task_modal(user_id,task_list):
    page = "edit-modal"
    return (
            html.H5("Edit Task"),
            *create_task_inputs(page,user_id,values=task_list),
        )


def register_overlays_callbacks(app):

    TWO_HOURS_MIN = 120
    page = "edit-modal"
    group = "task-input"

    @app.callback(
        [
            # your existing 6 invalid flags
            Output({"page": page, "group": group, "name": "start-date", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "start-time", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "end-date", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "end-time", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "invalid"),

            # NEW: purely cosmetic warning surfaces
            Output({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "className"),
            Output({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "className"),
            Output({"page": page, "name": "duration-warning", "type": "text"}, "children"),

            Output({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "placeholder"),
            Output({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "placeholder"),
        ],
        [
            Input({"page": page, "group": group, "name": "start-date", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "start-time", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "end-date", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "end-time", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "value"),
        ],
    )
    def validate_edit_task_fields(start_date, start_time, end_date, end_time, hours, minutes, include_placeholders=True):
        form_values = {'start_date': start_date, 'start_time': start_time, 'end_date': end_date, 'end_time': end_time,
                       'hours': hours, 'minutes': minutes}

        invalid_dt, time_output = validate_process_time_inputs(form_values, return_time_value=True)

        duration_min = time_output['duration_min']

        placeholder_hours, placeholder_mins = calculate_hh_mm_placeholders(form_values)

        # 3) Warning only if VALID and > 2 hours
        any_invalid = any(invalid_dt.values())
        warn = (duration_min is not None) and (duration_min > TWO_HOURS_MIN) and (not any_invalid)

        warn_class = "warning" if warn else ""
        warn_text = "Warning: entry exceeds 2 hours." if warn else ""

        if include_placeholders:
            return (
                invalid_dt['start_date'],invalid_dt['start_time'],invalid_dt['end_date'],invalid_dt['end_time'],
                invalid_dt['hours'],invalid_dt['minutes'],
                warn_class, warn_class, warn_text, placeholder_hours, placeholder_mins,
            )
        else:
            return (
                invalid_dt['start_date'], invalid_dt['start_time'], invalid_dt['end_date'], invalid_dt['end_time'],
                invalid_dt['hours'], invalid_dt['minutes'],
            )

    @app.callback(
        Output("edit-task-inputs", "data"),
        [
            Input({"page": page, "group": group, "name": "start-date", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "start-time", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "end-date", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "end-time", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "task-category", "type": "dropdown"}, "value"),
            Input({"page": page, "group": group, "name": "task-subcategory", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "task-activity", "type": "input"}, "value"),
            Input({"page": page, "group": group, "name": "task-notes", "type": "textarea"}, "value"),
        ],
        State("user-id", "data"),
        prevent_initial_call=True,
    )
    def handle_form_submission(
            start_date,
            start_time,
            end_date,
            end_time,
            hours,
            minutes,
            category_id,
            subcategory,
            activity,
            notes,
            user_id
    ):




        # Build form_values dict (UI-level)
        form_values = {
            "start_date": start_date,
            "start_time": start_time,
            "end_date": end_date,
            "end_time": end_time,
            "hours": hours,
            "minutes": minutes,
            "category_id": category_id,
            "subcategory": subcategory,
            "activity": activity,
            "notes": notes,
        }

        # ---- Time validation / inference (DB-level time fields) ----
        # returns: (invalid_flags_dict, time_output_dict)
        _, time_output = validate_process_time_inputs(form_values, return_time_value=True)

        required_time_keys = ("start_at", "end_at", "duration_min","date")
        has_required_time = all(time_output.get(k) is not None for k in required_time_keys)

        # ---- Category completeness / normalization ----
        category_error, category_output = validate_category_complete(user_id,form_values)
        has_required_category = not category_error

        # ---- Merge DB-ready entries ----
        entries = {**time_output, **category_output}


        # ---- Final readiness signal ----
        ready_to_save = has_required_time and has_required_category
        return {"ready_to_save": ready_to_save, "entries": entries}