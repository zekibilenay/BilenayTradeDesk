from tradedesk import journal_model as jm
from tradedesk.db import Database


def test_default_suggestions():
    assert jm.DEFAULT_PAIRS == ["EURUSD", "GBPUSD", "NQ!"]
    assert jm.DEFAULT_SESSIONS == ["Asia", "London", "New York Open", "New York Close", "Other"]
    assert {"HTF", "LTF", "DXY HTF", "DXY LTF", "ES! HTF", "ES! LTF", "Entry", "Result", "Other"} <= set(jm.DEFAULT_KINDS)


def test_merge_unique_keeps_order_and_drops_blanks_and_duplicates():
    assert jm.merge_unique(["A", "B"], ["B", " ", "C", ""], None, ["A", "D"]) == ["A", "B", "C", "D"]


def test_confirmation_follows_the_pair():
    assert jm.confirmation_label("EURUSD") == "DXY confirmation"
    assert jm.confirmation_label("gbpusd") == "DXY confirmation"
    assert jm.confirmation_label("NQ!") == "ES! confirmation"
    assert jm.confirmation_label("nq1!") == "ES! confirmation"
    assert jm.confirmation_label("") == "Confirmation" and jm.confirmation_label(None) == "Confirmation"


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
    assert db.distinct_values("tp") == [] and db.distinct_values("nope") == []


def test_custom_image_types_are_remembered(tmp_path):
    db = Database(tmp_path / "t.db")
    tid = db.create_trade("2026-11-01")
    db.add_image(tid, "HTF", "", "a.png")
    db.add_image(tid, "SMT", "", "b.png")
    db.add_image(tid, "SMT", "", "c.png")
    assert db.distinct_kinds() == ["HTF", "SMT"]
    assert jm.merge_unique(jm.DEFAULT_KINDS, db.distinct_kinds())[-1] == "SMT"
