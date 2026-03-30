from src.data_access.db import load_sql_engine
from sqlalchemy import text

def add_metric_definition(
    *,
    user_id,
    metric_key,
    display_name,
    unit,
    value_type,
    sort_order,
    is_duration=False,
    subcategory=None,
    to_minutes_factor=None,
    activity=None,
    category_id=None,
):
    """
    Insert a new metric definition.

    Raises:
        Exception if constraint violations occur.
    """

    query = text("""
        INSERT INTO public.metric_definitions (
            user_id,
            metric_key,
            display_name,
            unit,
            value_type,
            sort_order,
            is_duration,
            subcategory,
            to_minutes_factor,
            activity,
            category_id
        )
        VALUES (
            :user_id,
            :metric_key,
            :display_name,
            :unit,
            :value_type,
            :sort_order,
            :is_duration,
            :subcategory,
            :to_minutes_factor,
            :activity,
            :category_id
        )
    """)

    params = {
        "user_id": user_id,
        "metric_key": metric_key,
        "display_name": display_name,
        "unit": unit,
        "value_type": value_type,
        "sort_order": sort_order,
        "is_duration": is_duration,
        "subcategory": subcategory,
        "to_minutes_factor": to_minutes_factor,
        "activity": activity,
        "category_id": category_id,
    }
    engine = load_sql_engine()
    with engine.begin() as conn:
        conn.execute(query, params)

#Todo: Edit daily metric




