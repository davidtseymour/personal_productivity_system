import unittest

from src.callbacks.pages.daily_summary import _should_skip_last_update


class TestDailySummaryCallbacks(unittest.TestCase):
    def test_skip_last_update_when_date_does_not_match_selected_day(self) -> None:
        should_skip = _should_skip_last_update(
            last_update={"event_type": "create", "date": "2026-05-16", "user_id": "u1"},
            selected_date="2026-05-17",
            user_id="u1",
            triggered_id="last-update",
        )
        self.assertTrue(should_skip)

    def test_skip_last_update_when_user_does_not_match(self) -> None:
        should_skip = _should_skip_last_update(
            last_update={"event_type": "create", "date": "2026-05-17", "user_id": "u2"},
            selected_date="2026-05-17",
            user_id="u1",
            triggered_id="last-update",
        )
        self.assertTrue(should_skip)

    def test_do_not_skip_when_trigger_is_not_last_update(self) -> None:
        should_skip = _should_skip_last_update(
            last_update={"event_type": "create", "date": "2026-05-16", "user_id": "u1"},
            selected_date="2026-05-17",
            user_id="u1",
            triggered_id={"page": "daily-summary", "name": "date", "type": "date-input"},
        )
        self.assertFalse(should_skip)

    def test_do_not_skip_when_event_has_no_date(self) -> None:
        should_skip = _should_skip_last_update(
            last_update={"event_type": "update", "user_id": "u1"},
            selected_date="2026-05-17",
            user_id="u1",
            triggered_id="last-update",
        )
        self.assertFalse(should_skip)


if __name__ == "__main__":
    unittest.main()
