from datetime import datetime

import pandas as pd
from dash import Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate

from src.data_access.db import insert_task
from src.helpers.general import is_valid_date, determine_missing_times, get_category_from_id, get_category_id_list
from src.helpers.update_events import build_update_event
from src.layout.toasts import toast, update_toast, hide_toast
from src.logic.pages.log_time import validate_task_fields

def register_log_time_callbacks(app):
    page = "log-time"
    group = "task-input"

    # ---------- Update subcategory suggestions ----------
    @app.callback(
        Output("subcategory-suggestions", "children"),
        Input({"page": page, "name": "task-category", "type": "dropdown"}, "value"),
    )
    def update_subcategories(selected_category):
        if not selected_category:
            raise PreventUpdate

        # Todo: Add subcategory filled text based on and db
        return []


    # ---------- Handle form submission: update toast + clear fields ----------
    @app.callback(
        [
            # Toast outputs
            Output({"page": page, "name": "save-task", "type": "toast"}, "is_open"),
            Output({"page": page, "name": "save-task", "type": "toast"}, "children"),
            Output({"page": page, "name": "save-task", "type": "toast"}, "icon"),

            # Form field outputs
            Output({"page": page, "group": group, "name": "end-date", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "end-time", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "start-date", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "start-time", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "task-category", "type": "dropdown"}, "value"),
            Output({"page": page, "group": group, "name": "task-subcategory", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "task-activity", "type": "input"}, "value"),
            Output({"page": page, "group": group, "name": "task-notes", "type": "textarea"}, "value"),
            Output("task-nav-update-store", "data"),
            Output("last-update", "data"),
        ],
        [
            Input({"page": page, "name": "save-task", "type": "button"}, "n_clicks"),
            Input({"page": page, "name": "clear-task", "type": "button"}, "n_clicks"),
            State({"page": page, "group": group, "name": "start-date", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "start-time", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "end-date", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "end-time", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "task-category", "type": "dropdown"}, "value"),
            State({"page": page, "group": group, "name": "task-subcategory", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "task-activity", "type": "input"}, "value"),
            State({"page": page, "group": group, "name": "task-notes", "type": "textarea"}, "value"),
            State("user-id","data")
        ],
        prevent_initial_call=True,
    )
    def handle_form_submission(
        nclicks_save,
        nclicks_clear,
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
        user_id,
    ):
        if not (nclicks_save or 0) and not (nclicks_clear or 0):
            raise PreventUpdate

        # Todo: Implement convert to dictionary as passthrough
        # form_values = {'start_date': start_date, 'start_time': start_time, 'end_date': end_date, 'end_time': end_time,
        #               'hours': hours, 'minutes': minutes, 'category_id': category_id, 'subcategory': subcategory,
        #               'activity': activity, 'notes': notes}


        # Identify which button was clicked
        triggered = ctx.triggered_id
        if not triggered:
            raise PreventUpdate

        if isinstance(triggered, dict):
            source_name = triggered.get("name")
        else:
            source_name = str(triggered)

        # Default toast values
        toast_type = "LOG_TIME_SAVED"
        toast_return = update_toast(toast(toast_type))
        update_event = no_update

        if source_name == "save-task":

            # --- 1. Run field-level validation ---
            invalid_flags = validate_task_fields(
                start_date, start_time, end_date, end_time, hours, minutes,include_placeholders=False
            )
            has_field_error = any(invalid_flags)

            # --- 2. Time / inference checks (only if basic validation passed) ---
            has_time_error = False
            if not has_field_error:
                duration_min, start_at, end_at = determine_missing_times(
                    start_date, start_time, end_date, end_time, hours, minutes
                )

                # Guard against None before numeric comparison
                if (
                        duration_min is None
                        or duration_min <= 0
                        or start_at is None
                        or end_at is None
                ):
                    has_time_error = True

            try:
                category_id_int = int(category_id) if category_id is not None else None
            except (TypeError, ValueError):
                category_id_int = None

            # Validate cateogory error
            category_id_list = get_category_id_list(user_id)

            has_category_error = (
                    category_id_int is None
                    or category_id_int not in category_id_list
                    or not subcategory or not subcategory.strip()
                    or not activity or not activity.strip()
            )

            # --- 3. Handle error cases (separate branches for future customization) ---
            if has_field_error or has_time_error or has_category_error:
                if has_field_error:
                    toast_type = "VALIDATION_ERROR"
                elif has_time_error:
                    toast_type = "TIME_CONSISTENCY_ERROR"
                elif has_category_error:
                    toast_type = "CATEGORY_ERROR"

                display_t = toast(toast_type)

                return *update_toast(display_t), *(no_update,) * 10, no_update, no_update

            category = get_category_from_id(user_id, category_id_int)

            row_dict = {

                "date": pd.to_datetime(start_at).date(),
                "category": category,
                "category_id": category_id_int,
                "subcategory": subcategory,
                "activity": activity,
                "start_at": start_at,
                "end_at": end_at,
                "duration_min": int(duration_min),
                "notes": notes,
                "user_id":user_id,
            }

            insert_task(row_dict)
            update_event = build_update_event(
                event_type="create",
                entity="task",
                user_id=user_id,
                date=row_dict["date"].isoformat(),
            )


        elif source_name == "clear-task":
            toast_return = hide_toast()

        if is_valid_date(end_date) and source_name == "save-task":
            new_date = end_date
        else:
            new_date = datetime.now().strftime("%Y-%m-%d")

        cleared_values = (
            new_date,  # end-date
            "",  # end-time
            "",  # duration-hours
            "",  # duration-minutes
            new_date,  # start-date
            "",  # start-time
            "",  # category
            "",  # subcategory
            "",  # activity
            "",  # notes
        )

        return (*toast_return, *cleared_values, "data_changed", update_event)

    # ---------- Validation callback ----------
    @app.callback(
        [
            # invalid flags
            Output({"page": page, "group": group, "name": "start-date", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "start-time", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "end-date", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "end-time", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "duration-hours", "type": "input"}, "invalid"),
            Output({"page": page, "group": group, "name": "duration-minutes", "type": "input"}, "invalid"),

            # purely cosmetic warning surfaces
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

    def check_valid_times(start_date, start_time, end_date, end_time, hours, minutes):
        return validate_task_fields(start_date, start_time, end_date, end_time, hours, minutes, include_placeholders=True)
