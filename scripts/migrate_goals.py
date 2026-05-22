#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.data_access.db import load_sql_engine
from src.data_access.goals import backfill_goal_items_from_latest_legacy_rows


def _table_exists(conn, table_name: str) -> bool:
    sql = text(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = :table_name
        LIMIT 1;
        """
    )
    return conn.execute(sql, {"table_name": table_name}).scalar() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    sql = text(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = :table_name
          AND column_name = :column_name
        LIMIT 1;
        """
    )
    return conn.execute(
        sql,
        {"table_name": table_name, "column_name": column_name},
    ).scalar() is not None


def _constraint_exists(conn, constraint_name: str) -> bool:
    sql = text(
        """
        SELECT 1
        FROM pg_constraint
        WHERE conname = :constraint_name
        LIMIT 1;
        """
    )
    return conn.execute(sql, {"constraint_name": constraint_name}).scalar() is not None


def _count(conn, sql_text: str, params: dict | None = None) -> int:
    value = conn.execute(text(sql_text), params or {}).scalar_one()
    return int(value or 0)


def _print_check(name: str, passed: bool, detail: str) -> None:
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {name}: {detail}")


def run_preflight_checks(conn) -> tuple[bool, dict[str, int]]:
    required_tables = ["goal_set_items", "goal_sets", "goal_themes", "goal_items"]
    ok = True

    for table_name in required_tables:
        exists = _table_exists(conn, table_name)
        _print_check(
            f"table {table_name}",
            exists,
            "exists" if exists else "missing",
        )
        ok = ok and exists

    has_user_id = _column_exists(conn, "goal_set_items", "user_id")
    _print_check(
        "column goal_set_items.user_id",
        has_user_id,
        "exists" if has_user_id else "missing",
    )
    ok = ok and has_user_id

    if not ok:
        return False, {}

    null_user_count = _count(
        conn,
        "SELECT COUNT(*) FROM goal_set_items WHERE user_id IS NULL;",
    )
    _print_check(
        "null user_id rows",
        null_user_count == 0,
        f"count={null_user_count}",
    )

    set_mismatch_count = _count(
        conn,
        """
        SELECT COUNT(*)
        FROM goal_set_items gsi
        JOIN goal_sets gs ON gs.goal_set_id = gsi.goal_set_id
        WHERE gsi.user_id <> gs.user_id;
        """,
    )
    _print_check(
        "goal_set_items vs goal_sets user_id match",
        set_mismatch_count == 0,
        f"mismatch_count={set_mismatch_count}",
    )

    theme_mismatch_count = _count(
        conn,
        """
        SELECT COUNT(*)
        FROM goal_set_items gsi
        JOIN goal_themes gt ON gt.goal_theme_id = gsi.goal_theme_id
        WHERE gsi.user_id <> gt.user_id;
        """,
    )
    _print_check(
        "goal_set_items vs goal_themes user_id match",
        theme_mismatch_count == 0,
        f"mismatch_count={theme_mismatch_count}",
    )

    snapshot_count = _count(
        conn,
        """
        SELECT COUNT(*)
        FROM (
            SELECT goal_set_id, goal_theme_id
            FROM goal_set_items
            GROUP BY goal_set_id, goal_theme_id
        ) s;
        """,
    )
    print(f"[INFO] distinct legacy snapshots: {snapshot_count}")

    checks_ok = (
        null_user_count == 0
        and set_mismatch_count == 0
        and theme_mismatch_count == 0
    )

    return checks_ok, {
        "distinct_snapshots": snapshot_count,
    }


def validate_constraints(conn) -> bool:
    constraints = [
        "fk_goal_set_items_goal_set_user",
        "fk_goal_set_items_goal_theme_user",
    ]

    for name in constraints:
        exists = _constraint_exists(conn, name)
        _print_check(
            f"constraint {name}",
            exists,
            "exists" if exists else "missing",
        )
        if not exists:
            return False

    for name in constraints:
        conn.execute(
            text(f"ALTER TABLE goal_set_items VALIDATE CONSTRAINT {name};")
        )
        print(f"[PASS] validated constraint: {name}")

    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill and validate goals migration (legacy -> goal_items)."
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Optional user UUID to scope backfill to one user.",
    )
    parser.add_argument(
        "--skip-backfill",
        action="store_true",
        help="Run checks/validation only; do not backfill.",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip ALTER TABLE ... VALIDATE CONSTRAINT.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    engine = load_sql_engine()

    print("== Goals Migration ==")
    print("1) preflight checks")

    try:
        with engine.connect() as conn:
            preflight_ok, stats = run_preflight_checks(conn)
    except SQLAlchemyError as exc:
        print(f"[FAIL] database error during preflight: {exc}")
        return 1

    if not preflight_ok:
        print("[FAIL] preflight checks failed. Resolve issues before backfill.")
        return 1

    if args.skip_backfill:
        print("2) backfill skipped")
    else:
        print("2) running backfill")
        try:
            processed = backfill_goal_items_from_latest_legacy_rows(args.user_id)
            print(f"[PASS] backfill processed snapshots: {processed}")
            if stats.get("distinct_snapshots", 0) and args.user_id is None:
                expected = stats["distinct_snapshots"]
                if processed != expected:
                    print(
                        "[WARN] processed snapshot count differs from distinct legacy snapshot count: "
                        f"processed={processed}, distinct={expected}"
                    )
        except SQLAlchemyError as exc:
            print(f"[FAIL] backfill failed: {exc}")
            return 1

    if args.skip_validate:
        print("3) constraint validation skipped")
        print("[PASS] migration script completed")
        return 0

    print("3) validating constraints")
    try:
        with engine.begin() as conn:
            ok = validate_constraints(conn)
    except SQLAlchemyError as exc:
        print(f"[FAIL] constraint validation failed: {exc}")
        return 1

    if not ok:
        print("[FAIL] required constraints missing. Run schema migration first.")
        return 1

    print("[PASS] migration script completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
