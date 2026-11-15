from tradedesk import paths
from tradedesk.settings import DEFAULTS, Settings


def test_first_start_calendar_defaults(tmp_path):
    s = Settings(tmp_path / "settings.json")
    assert s.get("tz_offset") == -5.0
    assert set(s.get("cal_impacts")) == {"High", "Medium", "Low"}
    assert set(s.get("cal_currencies")) == {"ALL", "AUD", "CAD", "CHF", "CNY", "EUR", "GBP", "JPY", "NZD", "USD"}
    assert "psychology_example_added" not in DEFAULTS
    assert s.get("hidden_suggestions") == {}


def test_saved_settings_still_win(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text('{"tz_offset": 3.0, "cal_impacts": ["High"]}', encoding="utf-8")
    s = Settings(p)
    assert s.get("tz_offset") == 3.0 and s.get("cal_impacts") == ["High"]


def test_old_database_is_renamed_once(tmp_path):
    new = tmp_path / "tradedesk.db"
    old = tmp_path / paths._OLD_DB_NAME
    old.write_bytes(b"trades")
    assert paths.migrate_old_db(tmp_path, new) is True
    assert new.read_bytes() == b"trades" and not old.exists()
    assert paths.migrate_old_db(tmp_path, new) is False
    old.write_bytes(b"other")                                   # never overwrites an existing database
    assert paths.migrate_old_db(tmp_path, new) is False and new.read_bytes() == b"trades"
