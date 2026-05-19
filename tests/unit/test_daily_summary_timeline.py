import unittest

import pandas as pd

from src.logic.pages.category_colors import ordered_category_color_map
from src.logic.pages.daily_summary_timeline import (
    _build_timeline_category_color_map,
    assign_tracks,
    compute_horizon_window,
    normalize_intervals,
)


class TestDailySummaryTimeline(unittest.TestCase):
    def test_normalize_intervals_clips_cross_midnight(self) -> None:
        rows = pd.DataFrame(
            [
                {
                    "task_id": 1,
                    "category_id": 10,
                    "category": "Work",
                    "subcategory": "Coding",
                    "activity": "Deep work",
                    "start_at": "2026-05-16 23:30:00",
                    "end_at": "2026-05-17 00:30:00",
                },
                {
                    "task_id": 2,
                    "category_id": 20,
                    "category": "Family",
                    "subcategory": "Dinner",
                    "activity": "Cooked",
                    "start_at": "2026-05-17 23:00:00",
                    "end_at": "2026-05-18 01:00:00",
                },
                {
                    "task_id": 3,
                    "category_id": 30,
                    "category": "Exercise",
                    "subcategory": "Run",
                    "activity": "Cardio",
                    "start_at": "2026-05-16 20:00:00",
                    "end_at": "2026-05-16 21:00:00",
                },
            ]
        )

        intervals = normalize_intervals(rows, "2026-05-17")
        self.assertEqual(len(intervals), 2)

        first = intervals.loc[intervals["task_id"] == 1].iloc[0]
        self.assertEqual(first["display_start"], pd.Timestamp("2026-05-17 00:00:00"))
        self.assertEqual(first["display_end"], pd.Timestamp("2026-05-17 00:30:00"))
        self.assertTrue(bool(first["clipped_left"]))
        self.assertFalse(bool(first["clipped_right"]))

        second = intervals.loc[intervals["task_id"] == 2].iloc[0]
        self.assertEqual(second["display_start"], pd.Timestamp("2026-05-17 23:00:00"))
        self.assertEqual(second["display_end"], pd.Timestamp("2026-05-18 00:00:00"))
        self.assertFalse(bool(second["clipped_left"]))
        self.assertTrue(bool(second["clipped_right"]))

    def test_assign_tracks_reuses_tracks(self) -> None:
        intervals = pd.DataFrame(
            [
                {"task_id": 1, "display_start": pd.Timestamp("2026-05-17 08:00:00"), "display_end": pd.Timestamp("2026-05-17 09:00:00")},
                {"task_id": 2, "display_start": pd.Timestamp("2026-05-17 08:30:00"), "display_end": pd.Timestamp("2026-05-17 10:00:00")},
                {"task_id": 3, "display_start": pd.Timestamp("2026-05-17 09:00:00"), "display_end": pd.Timestamp("2026-05-17 09:30:00")},
            ]
        )

        tracked, track_count = assign_tracks(intervals)
        self.assertEqual(track_count, 2)
        self.assertListEqual(tracked["track"].tolist(), [0, 1, 0])

    def test_compute_horizon_window_active_span_clamps_to_day(self) -> None:
        intervals = pd.DataFrame(
            [
                {
                    "display_start": pd.Timestamp("2026-05-17 00:10:00"),
                    "display_end": pd.Timestamp("2026-05-17 23:50:00"),
                }
            ]
        )
        horizon = compute_horizon_window(intervals, "2026-05-17")
        self.assertEqual(horizon["start_at"], pd.Timestamp("2026-05-17 00:00:00"))
        self.assertEqual(horizon["end_at"], pd.Timestamp("2026-05-18 00:00:00"))

    def test_compute_horizon_window_uses_union_of_workday_and_active(self) -> None:
        intervals = pd.DataFrame(
            [
                {
                    "display_start": pd.Timestamp("2026-05-17 05:00:00"),
                    "display_end": pd.Timestamp("2026-05-17 23:00:00"),
                }
            ]
        )
        horizon = compute_horizon_window(intervals, "2026-05-17")
        self.assertEqual(horizon["start_at"], pd.Timestamp("2026-05-17 04:30:00"))
        self.assertEqual(horizon["end_at"], pd.Timestamp("2026-05-17 23:30:00"))

    def test_compute_horizon_window_falls_back_to_workday_when_empty(self) -> None:
        intervals = pd.DataFrame(columns=["display_start", "display_end"])
        horizon = compute_horizon_window(intervals, "2026-05-17")
        self.assertEqual(horizon["start_at"], pd.Timestamp("2026-05-17 06:00:00"))
        self.assertEqual(horizon["end_at"], pd.Timestamp("2026-05-17 22:00:00"))

    def test_timeline_colors_share_same_base_sequence_as_trends(self) -> None:
        canonical_order = ["Exercise", "Family", "Work"]
        trends_colors = ordered_category_color_map(canonical_order, tint=0.0)
        timeline_colors = ordered_category_color_map(canonical_order, tint=0.18)

        self.assertSetEqual(set(trends_colors), set(timeline_colors))
        self.assertNotEqual(trends_colors["Exercise"], timeline_colors["Exercise"])

    def test_timeline_color_map_respects_global_category_order(self) -> None:
        tracked = pd.DataFrame(
            [
                {"category_id": 30, "category": "Work"},
                {"category_id": 10, "category": "Exercise"},
            ]
        )
        color_map = _build_timeline_category_color_map(
            tracked,
            category_order=["Exercise", "Family", "Work"],
        )
        expected = ordered_category_color_map(["Exercise", "Family", "Work"], tint=0.18)

        self.assertEqual(color_map["Exercise"], expected["Exercise"])
        self.assertEqual(color_map["Work"], expected["Work"])


if __name__ == "__main__":
    unittest.main()
