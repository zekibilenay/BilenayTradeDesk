"""Time-zone labels are pure functions; the calendar module imports tkinter, so skip if it is unavailable."""
import pytest

pytest.importorskip("tkinter")

from tradedesk.calendar_tab import TZ_BY_LABEL, tz_label  # noqa: E402


def test_labels():
    assert tz_label(3) == "UTC+3" and tz_label(-4) == "UTC-4" and tz_label(0) == "UTC+0"
    assert tz_label(5.5) == "UTC+5:30" and tz_label(-3.5) == "UTC-3:30" and tz_label(5.75) == "UTC+5:45"
    assert TZ_BY_LABEL["UTC-4"] == -4.0 and TZ_BY_LABEL["UTC+5:30"] == 5.5
