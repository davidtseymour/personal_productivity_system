def task_row_to_form_initial(row: dict) -> dict:
    start_at = row["start_at"]
    end_at = row["end_at"]
    duration_min = int(row["duration_min"])

    return {
        "start_date": start_at.strftime("%Y-%m-%d"),
        "start_time": start_at.strftime("%H:%M"),
        "end_date": end_at.strftime("%Y-%m-%d"),
        "end_time": end_at.strftime("%H:%M"),
        "duration_hours": str(duration_min // 60),
        "duration_minutes": f"{duration_min % 60:02d}",
        "category_id": row["category_id"],
        "subcategory": row.get("subcategory") or "",
        "activity": row.get("activity") or "",
        "notes": row.get("notes") or "",
    }
