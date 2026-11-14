from tradedesk import journal_model as jm
from tradedesk.db import Database


def test_default_suggestions():
    assert jm.DEFAULT_PAIRS == ["EURUSD", "GBPUSD", "NQ!"]
    assert jm.DEFAULT_SESSIONS == ["Asia", "London", "New York Open", "New York Close", "Other"]
    assert {"HTF", "LTF", "DXY HTF", "DXY LTF", "ES! HTF", "ES! LTF", "Entry", "Result", "Other"} <= set(jm.DEFAULT_KINDS)


def test_merge_unique_keeps_order_and_drops_blanks_and_duplicates():
    assert jm.merge_unique(["A", "B"], ["B", " ", "C", ""], None, ["A", "D"]) == ["A", "B", "C", "D"]


def test_correlation_pair_suggestions_follow_the_traded_pair():
    assert jm.correlation_symbol("EURUSD") == "DXY" and jm.correlation_symbol("gbpusd") == "DXY"
    assert jm.correlation_symbol("NQ!") == "ES!" and jm.correlation_symbol("nq1!") == "ES!"
    assert jm.correlation_symbol("") == "" and jm.correlation_symbol(None) == ""
    assert jm.correlation_defaults("EURUSD") == ["DXY", "ES!"]
    assert jm.correlation_defaults("NQ!") == ["ES!", "DXY"]
    assert jm.correlation_defaults("XYZ") == ["DXY", "ES!"]


def test_removed_suggestions_are_hidden_and_come_back_when_typed_again():
    h = jm.hide_value({}, "entry", "PDH sweep")
    h = jm.hide_value(h, "entry", "PDH sweep")                                  # twice = once
    h = jm.hide_value(h, "corr_pair", "ES!")
    assert h == {"entry": ["PDH sweep"], "corr_pair": ["ES!"]}
    assert jm.visible(["PDH sweep", "PDL sweep"], h["entry"]) == ["PDL sweep"]
    assert jm.visible(["a"], None) == ["a"]
    back = jm.unhide_value(h, "entry", "PDH sweep")
    assert back == {"corr_pair": ["ES!"]} and h["entry"] == ["PDH sweep"]       # input is not modified
    assert jm.unhide_value(back, "entry", "never hidden") == back


def test_image_type_order_depends_on_the_pair():
    assert jm.kind_sequence("EURUSD") == ["HTF", "LTF", "DXY HTF", "DXY LTF", "Entry", "Result"]
    assert jm.kind_sequence("NQ!") == ["HTF", "LTF", "ES! HTF", "ES! LTF", "Entry", "Result"]
    assert jm.next_kind("LTF", "NQ!") == "ES! HTF" and jm.next_kind("LTF", "EURUSD") == "DXY HTF"
    assert jm.next_kind("Result", "EURUSD") == "Result"          # stays on the last one
    assert jm.next_kind("My own label", "EURUSD") == "My own label"


def test_values_used_before_are_offered_again(tmp_path):
    db = Database(tmp_path / "t.db")
    a, b, c = (db.create_trade("2026-11-01") for _ in range(3))
    db.update_trade(a, {"instrument": "EURUSD", "session": "London", "entry": "PDH sweep", "sl": "Above high"})
    db.update_trade(b, {"instrument": "NQ!", "session": "New York Open", "entry": "PDL sweep"})
    db.update_trade(c, {"instrument": "NQ!", "session": "Lon", "entry": "half typ"})          # being typed right now
    assert db.distinct_values("instrument", exclude_id=c) == ["EURUSD", "NQ!"]
    assert db.distinct_values("session", exclude_id=c) == ["London", "New York Open"]
    assert db.distinct_values("entry", exclude_id=c, recent_first=True) == ["PDL sweep", "PDH sweep"]
    assert db.distinct_values("sl") == ["Above high"]
    db.update_trade(a, {"mistakes": "Moved the stop"})
    db.update_trade(b, {"mistakes": "Early entry"})
    assert db.distinct_values("mistakes", recent_first=True) == ["Early entry", "Moved the stop"]
    assert db.distinct_values("tp") == [] and db.distinct_values("nope") == []


def test_custom_image_types_are_remembered(tmp_path):
    db = Database(tmp_path / "t.db")
    tid = db.create_trade("2026-11-01")
    db.add_image(tid, "HTF", "", "a.png")
    db.add_image(tid, "SMT", "", "b.png")
    db.add_image(tid, "SMT", "", "c.png")
    assert db.distinct_kinds() == ["HTF", "SMT"]
    assert jm.merge_unique(jm.DEFAULT_KINDS, db.distinct_kinds())[-1] == "SMT"


def test_correlation_lists_read_both_slots(tmp_path):
    db = Database(tmp_path / "t.db")
    a, b = db.create_trade("2026-11-01"), db.create_trade("2026-11-02")
    db.update_trade(a, {"corr1_pair": "DXY", "corr1_note": "SMT with EURUSD", "corr2_pair": "ES!", "corr2_note": "swept low"})
    db.update_trade(b, {"corr1_pair": "DXY", "corr1_note": "SMT with EURUSD"})
    assert db.distinct_values("corr_pair") == ["DXY", "ES!"]
    assert db.distinct_values("corr_note", recent_first=True) == ["SMT with EURUSD", "swept low"]
    assert db.distinct_values("corr_pair", exclude_id=b) == ["DXY", "ES!"]
    assert db.list_trades(search="swept")[0]["id"] == a


def test_old_dxy_confirmation_moves_into_the_first_correlation(tmp_path):
    import sqlite3
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.executescript("""
    CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, trade_time TEXT NOT NULL DEFAULT '',
     instrument TEXT NOT NULL DEFAULT 'EURUSD', direction TEXT NOT NULL DEFAULT '', session TEXT NOT NULL DEFAULT '',
     entry TEXT NOT NULL DEFAULT '', sl TEXT NOT NULL DEFAULT '', tp TEXT NOT NULL DEFAULT '', exit_price TEXT NOT NULL DEFAULT '',
     outcome TEXT NOT NULL DEFAULT 'Open', result_r TEXT NOT NULL DEFAULT '', setup TEXT NOT NULL DEFAULT '',
     dxy_conf TEXT NOT NULL DEFAULT '', mistakes TEXT NOT NULL DEFAULT '', why TEXT NOT NULL DEFAULT '',
     review TEXT NOT NULL DEFAULT '', cl_verdict TEXT NOT NULL DEFAULT '', cl_score REAL, status TEXT NOT NULL DEFAULT 'done',
     created_at TEXT);
    INSERT INTO trades (trade_date, instrument, dxy_conf) VALUES ('2026-10-30', 'EURUSD', 'DXY swept the high');
    INSERT INTO trades (trade_date, instrument, dxy_conf) VALUES ('2026-10-31', 'NQ!', 'ES! made a lower high');
    INSERT INTO trades (trade_date, instrument) VALUES ('2026-11-01', 'EURUSD');
    """)
    c.commit()
    c.close()
    db = Database(p)
    t1, t2, t3 = db.get_trade(1), db.get_trade(2), db.get_trade(3)
    assert (t1["corr1_pair"], t1["corr1_note"], t1["dxy_conf"]) == ("DXY", "DXY swept the high", "")
    assert (t2["corr1_pair"], t2["corr1_note"]) == ("ES!", "ES! made a lower high")
    assert (t3["corr1_pair"], t3["corr1_note"], t3["corr2_pair"], t3["corr2_note"]) == ("", "", "", "")
    db.update_trade(1, {"corr1_pair": "", "corr1_note": ""})
    db.close()
    assert Database(p).get_trade(1)["corr1_note"] == ""          # a second start must not move anything again


def test_dates_are_typed_as_dd_mm_yyyy_and_stored_as_iso():
    assert jm.parse_date("14-11-2026") == "2026-11-14"
    assert jm.parse_date("5.1.2026") == "2026-01-05" and jm.parse_date("05/01/2026") == "2026-01-05"
    assert jm.parse_date("2026-11-14") == "2026-11-14"                 # the old way of typing still works
    for bad in ("", "31-02-2026", "2026-13-01", "14-11-26", "tomorrow", None):
        assert jm.parse_date(bad) is None
    assert jm.display_date("2026-11-14") == "14-11-2026"
    assert jm.display_date("") == "" and jm.display_date(None) == "" and jm.display_date("junk") == "junk"
    assert jm.parse_date(jm.display_date("2026-03-09")) == "2026-03-09"


def test_value_typed_with_enter_is_saved_per_group():
    s = jm.remember_value({}, "entry", " PDH sweep ")
    s = jm.remember_value(s, "entry", "PDH sweep")                      # twice = once
    s = jm.remember_value(s, "entry", "PDL sweep")
    s = jm.remember_value(s, "risk_pct", "1")
    s = jm.remember_value(s, "risk_pct", "   ")                          # blank is ignored
    assert s == {"entry": ["PDH sweep", "PDL sweep"], "risk_pct": ["1"]}
    assert jm.saved_values(s, "entry") == ["PDH sweep", "PDL sweep"]
    assert jm.saved_values(s, "entry", newest_first=True) == ["PDL sweep", "PDH sweep"]
    assert jm.saved_values(s, "nothing") == [] and jm.saved_values(None, "entry") == []
    assert jm.remember_value(None, "x", " ") == {}
    before = {"a": ["1"]}
    jm.remember_value(before, "a", "2")
    assert before == {"a": ["1"]}                                        # input is not modified


def test_saved_value_is_offered_even_when_no_trade_uses_it_and_can_be_removed():
    saved = jm.remember_value({}, "setup", "Judas swing")
    offered = jm.visible(jm.merge_unique([], jm.saved_values(saved, "setup"), ["OB retest"]), None)
    assert offered == ["Judas swing", "OB retest"]
    hidden = jm.hide_value({}, "setup", "Judas swing")
    assert jm.visible(offered, hidden["setup"]) == ["OB retest"]
