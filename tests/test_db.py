import sqlite3

from tradedesk.db import Database


def test_trade_crud_and_free_text(tmp_path):
    db = Database(tmp_path / "t.db")
    tid = db.create_trade("2026-10-30", "09:45")
    db.update_trade(tid, {"entry": "PDH sweep", "sl": "above session high", "tp": "Weekly low",
                          "result_r": "+2R", "outcome": "Win", "evil_column": "ignored"})
    t = db.get_trade(tid)
    assert (t["entry"], t["sl"], t["tp"], t["outcome"]) == ("PDH sweep", "above session high", "Weekly low", "Win")
    assert db.list_trades(search="sweep")[0]["id"] == tid
    assert db.list_trades(outcome="Loss") == []
    db.delete_trade(tid)
    assert db.get_trade(tid) is None


def test_images(tmp_path):
    db = Database(tmp_path / "t.db")
    tid = db.create_trade("2026-10-30")
    a = db.add_image(tid, "HTF", "", "trade_1/a.png")
    db.add_image(tid, "LTF", "x", "trade_1/b.png")
    db.update_image(a, caption="htf structure")
    assert [i["caption"] for i in db.list_images(tid)] == ["htf structure", "x"]
    assert db.delete_image(a) == "trade_1/a.png"
    db.delete_trade(tid)
    assert db.list_images(tid) == []


def test_checklist_day_upsert(tmp_path):
    db = Database(tmp_path / "t.db")
    db.save_checklist_day("2026-10-30", {"a": {"note": "n", "confirmed": True}}, {"s1": "o1"}, "green", 90.0, True)
    d = db.get_checklist_day("2026-10-30")
    assert d["choices"] == {"s1": "o1"} and d["verdict"] == "green"
    db.save_checklist_day("2026-10-30", {}, {}, "red", 10.0, False)
    d = db.get_checklist_day("2026-10-30")
    assert d["choices"] == {} and d["verdict"] == "red" and d["answers"] == {}


def test_migration_from_v01(tmp_path):
    """v0.1 stored numeric price columns and Turkish labels."""
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.executescript("""
    CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, trade_time TEXT NOT NULL DEFAULT '',
     instrument TEXT NOT NULL DEFAULT 'EURUSD', direction TEXT NOT NULL DEFAULT '', session TEXT NOT NULL DEFAULT '',
     entry REAL, sl REAL, tp REAL, exit_price REAL, outcome TEXT NOT NULL DEFAULT 'Açık', result_r REAL,
     setup TEXT NOT NULL DEFAULT '', dxy_conf TEXT NOT NULL DEFAULT '', mistakes TEXT NOT NULL DEFAULT '',
     why TEXT NOT NULL DEFAULT '', review TEXT NOT NULL DEFAULT '', cl_verdict TEXT NOT NULL DEFAULT '', cl_score REAL, created_at TEXT);
    CREATE TABLE trade_images (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_id INTEGER NOT NULL, kind TEXT NOT NULL DEFAULT 'Diğer',
     caption TEXT NOT NULL DEFAULT '', filename TEXT NOT NULL, created_at TEXT, FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE);
    INSERT INTO trades (trade_date, session, entry, sl, outcome, result_r) VALUES ('2026-10-29','Londra',1.0850,1.0830,'Kazanç',2.0);
    INSERT INTO trade_images (trade_id, kind, filename) VALUES (1,'Giriş','trade_1/a.png');
    """)
    c.commit()
    c.close()
    db = Database(p)
    t = db.get_trade(1)
    assert (t["entry"], t["tp"], t["outcome"], t["session"]) == ("1.085", "", "Win", "London")
    assert db.list_images(1)[0]["kind"] == "Entry"
    db.close()
    assert Database(p).get_trade(1)["entry"] == "1.085"      # second open must not migrate again


def test_new_trade_is_a_draft_and_can_be_finished(tmp_path):
    db = Database(tmp_path / "t.db")
    tid = db.create_trade("2026-11-02", "10:00")
    assert db.get_trade(tid)["status"] == "draft"
    db.update_trade(tid, {"status": "done"})
    assert db.get_trade(tid)["status"] == "done"
    assert db.list_trades()[0]["status"] == "done"


def test_migration_from_v02(tmp_path):
    """v0.2 had no trades.status / checklist_days.choices: old trades must come out as finished ('done'),
    old day notes stay untouched in the database."""
    p = tmp_path / "v02.db"
    c = sqlite3.connect(p)
    c.executescript("""
    CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, trade_time TEXT NOT NULL DEFAULT '',
     instrument TEXT NOT NULL DEFAULT 'EURUSD', direction TEXT NOT NULL DEFAULT '', session TEXT NOT NULL DEFAULT '',
     entry TEXT NOT NULL DEFAULT '', sl TEXT NOT NULL DEFAULT '', tp TEXT NOT NULL DEFAULT '', exit_price TEXT NOT NULL DEFAULT '',
     outcome TEXT NOT NULL DEFAULT 'Open', result_r TEXT NOT NULL DEFAULT '', setup TEXT NOT NULL DEFAULT '',
     dxy_conf TEXT NOT NULL DEFAULT '', mistakes TEXT NOT NULL DEFAULT '', why TEXT NOT NULL DEFAULT '',
     review TEXT NOT NULL DEFAULT '', cl_verdict TEXT NOT NULL DEFAULT '', cl_score REAL, created_at TEXT);
    CREATE TABLE checklist_days (date TEXT PRIMARY KEY, answers TEXT NOT NULL DEFAULT '{}', note TEXT NOT NULL DEFAULT '',
     verdict TEXT NOT NULL DEFAULT '', score REAL NOT NULL DEFAULT 0, required_ok INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
    INSERT INTO trades (trade_date, entry, outcome, result_r) VALUES ('2026-10-30', 'PDH sweep', 'Win', '+2R');
    INSERT INTO checklist_days (date, answers, note, verdict, score, required_ok) VALUES ('2026-10-30', '{}', 'old note', 'green', 90, 1);
    """)
    c.commit()
    c.close()
    db = Database(p)
    assert db.get_trade(1)["status"] == "done" and db.get_trade(1)["entry"] == "PDH sweep"
    d = db.get_checklist_day("2026-10-30")
    assert d["choices"] == {} and d["note"] == "old note"
    db.save_checklist_day("2026-10-30", {}, {"s": "o"}, "red", 10.0, False)       # saving must not wipe the old note
    assert db.get_checklist_day("2026-10-30")["note"] == "old note"
    db.close()
    Database(p).close()                                                           # second open: no migration error


def test_trade_numbers_are_a_running_count(tmp_path):
    """With n trades the next one is n + 1, even after trades were deleted (the internal id keeps growing)."""
    db = Database(tmp_path / "t.db")
    ids = [db.create_trade("2026-11-0%d" % d, "10:00") for d in (1, 2, 3)]
    assert db.trade_numbers() == {ids[0]: 1, ids[1]: 2, ids[2]: 3}
    db.delete_trade(ids[1])
    assert db.trade_numbers() == {ids[0]: 1, ids[2]: 2}
    new = db.create_trade("2026-11-04", "10:00")
    assert new > ids[2] and db.trade_numbers()[new] == 3


def test_risk_and_planned_rr_are_stored_searched_and_offered(tmp_path):
    db = Database(tmp_path / "t.db")
    a = db.create_trade("2026-11-14", "20:05")
    b = db.create_trade("2026-11-15", "09:00")
    db.update_trade(a, {"risk_pct": "0.5", "planned_rr": "1:3"})
    db.update_trade(b, {"risk_pct": "1", "planned_rr": "1:3"})
    t = db.get_trade(a)
    assert (t["risk_pct"], t["planned_rr"]) == ("0.5", "1:3")
    assert db.distinct_values("planned_rr") == ["1:3"]
    assert db.distinct_values("risk_pct", exclude_id=b) == ["0.5"]
    assert db.list_trades(search="1:3")[0]["id"] == b                   # newest first; both match
    assert len(db.list_trades(search="1:3")) == 2


def test_database_from_0_7_1_gets_the_new_columns_once(tmp_path):
    import sqlite3
    p = tmp_path / "old.db"
    c = sqlite3.connect(p)
    c.executescript("""
    CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, trade_time TEXT NOT NULL DEFAULT '',
     instrument TEXT NOT NULL DEFAULT 'EURUSD', direction TEXT NOT NULL DEFAULT '', session TEXT NOT NULL DEFAULT '',
     entry TEXT NOT NULL DEFAULT '', sl TEXT NOT NULL DEFAULT '', tp TEXT NOT NULL DEFAULT '', exit_price TEXT NOT NULL DEFAULT '',
     outcome TEXT NOT NULL DEFAULT 'Open', result_r TEXT NOT NULL DEFAULT '', setup TEXT NOT NULL DEFAULT '',
     dxy_conf TEXT NOT NULL DEFAULT '', corr1_pair TEXT NOT NULL DEFAULT '', corr1_note TEXT NOT NULL DEFAULT '',
     corr2_pair TEXT NOT NULL DEFAULT '', corr2_note TEXT NOT NULL DEFAULT '',
     mistakes TEXT NOT NULL DEFAULT '', why TEXT NOT NULL DEFAULT '',
     review TEXT NOT NULL DEFAULT '', cl_verdict TEXT NOT NULL DEFAULT '', cl_score REAL, status TEXT NOT NULL DEFAULT 'done',
     created_at TEXT);
    INSERT INTO trades (trade_date, mistakes) VALUES ('2026-10-30', 'moved stop');
    """)
    c.commit()
    c.close()
    db = Database(p)
    t = db.get_trade(1)
    assert (t["trade_date"], t["mistakes"], t["risk_pct"], t["planned_rr"]) == ("2026-10-30", "moved stop", "", "")
    db.update_trade(1, {"risk_pct": "1"})
    db.close()
    assert Database(p).get_trade(1)["risk_pct"] == "1"                  # opening again keeps the value
