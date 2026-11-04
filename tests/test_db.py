import sqlite3

from tradehub.db import Database


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
