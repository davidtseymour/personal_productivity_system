from src.data_access.db import load_recent_task_data, load_today_summary_minutes
import pandas as pd
import datetime as dt



def get_today_summary_payload(user_id) -> dict:
    today = dt.date.today()
    df = load_today_summary_minutes(user_id, today)

    if df is None or df.empty:
        return {"status": "empty", "rows": [], "total": 0, "screen_minutes": None}

    df = df.copy()
    df["minutes"] = df["total_minutes"].fillna(0).round().astype(int)
    df["category"] = df["category_name"]

    #Todo: This should not be hard coded but the framework needs to be adjusted for this to happen
    df_productive = df[~df["category"].isin(["Screen", "Sleep"]) ]
    df_screen = df[df["category"] == "Screen"]

    if df_productive.empty:
        return {
            "status": "no_productive",
            "rows": [],
            "total": 0,
            "screen_minutes": int(df_screen["minutes"].sum()) if not df_screen.empty else None,
        }

    rows = df_productive[["category", "minutes"]].to_dict("records")
    total = int(df_productive["minutes"].sum())
    screen_minutes = int(df_screen["minutes"].sum()) if not df_screen.empty else None

    return {"status": "ok", "rows": rows, "total": total, "screen_minutes": screen_minutes}



def get_recent_tasks(n=5,user_id=None) ->  pd.DataFrame | None:
    if user_id is None:
        return None

    df = load_recent_task_data(user_id,n=n)

    return df

