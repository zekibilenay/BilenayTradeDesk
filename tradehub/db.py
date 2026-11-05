"""SQLite layer: checklist days, trades and trade images."""
import json
import sqlite3
from datetime import datetime

TRADE_FIELDS = (
    "trade_date", "trade_time", "instrument", "direction", "session",
    "entry", "sl", "tp", "exit_price", "outcome", "result_r",
    "setup", "dxy_conf", "mistakes", "why", "review", "cl_verdict", "cl_score", "status",
)


def _trades_sql(name="trades"):
    # entry / sl / tp / exit_price / result_r are free text (liquidity names, levels, "2R", ...)
    return f"""
CREATE TABLE IF NOT EXISTS {name} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date  TEXT NOT NULL,
    trade_time  TEXT NOT NULL DEFAULT '',
    instrument  TEXT NOT NULL DEFAULT 'EURUSD',
    direction   TEXT NOT NULL DEFAULT '',
    session     TEXT NOT NULL DEFAULT '',
    entry       TEXT NOT NULL DEFAULT '',
    sl          TEXT NOT NULL DEFAULT '',
    tp          TEXT NOT NULL DEFAULT '',
    exit_price  TEXT NOT NULL DEFAULT '',
    outcome     TEXT NOT NULL DEFAULT 'Open',
    result_r    TEXT NOT NULL DEFAULT '',
    setup       TEXT NOT NULL DEFAULT '',
    dxy_conf    TEXT NOT NULL DEFAULT '',
    mistakes    TEXT NOT NULL DEFAULT '',
    why         TEXT NOT NULL DEFAULT '',
    review      TEXT NOT NULL DEFAULT '',
    cl_verdict  TEXT NOT NULL DEFAULT '',
    cl_score    REAL,
    status      TEXT NOT NULL DEFAULT 'done',
    created_at  TEXT
);"""


SCHEMA = """
CREATE TABLE IF NOT EXISTS checklist_days (
    date        TEXT PRIMARY KEY,
    answers     TEXT NOT NULL DEFAULT '{}',
    choices     TEXT NOT NULL DEFAULT '{}',
    note        TEXT NOT NULL DEFAULT '',            -- unused since v0.3 (day notes were removed); kept so old data survives
    verdict     TEXT NOT NULL DEFAULT '',
    score       REAL NOT NULL DEFAULT 0,
    required_ok INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS trade_images (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id   INTEGER NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'Other',
    caption    TEXT NOT NULL DEFAULT '',
    filename   TEXT NOT NULL,
    created_at TEXT,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);
"""

# v0.1 stored Turkish labels; translate them once (idempotent).
VALUE_MAP = (
    ("trades", "outcome", {"Açık": "Open", "Kazanç": "Win", "Kayıp": "Loss"}),
    ("trades", "session", {"Asya": "Asia", "Londra": "London", "Londra/NY kesişimi": "London/NY overlap",
                           "Diğer": "Other"}),
    ("trade_images", "kind", {"Giriş": "Entry", "Sonuç": "Result", "Diğer": "Other"}),
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(_trades_sql("trades") + SCHEMA)
        self._migrate()
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(trade_date, trade_time)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_images_trade ON trade_images(trade_id)")
        self.conn.commit()

    def close(self):
        self.conn.close()

    # --------------------------------------------------------- migrations
    def _migrate(self):
        cols = {r["name"]: (r["type"] or "").upper() for r in self.conn.execute("PRAGMA table_info(trades)")}
        if cols.get("entry") == "REAL":                       # v0.1 schema: numeric price columns
            self.conn.commit()
            self.conn.execute("PRAGMA foreign_keys = OFF")
            try:
                def txt(c):
                    return f"CASE WHEN {c} IS NULL THEN '' ELSE CAST({c} AS TEXT) END"
                self.conn.executescript(_trades_sql("trades_new"))
                self.conn.execute(f"""
                    INSERT INTO trades_new (id, trade_date, trade_time, instrument, direction, session,
                        entry, sl, tp, exit_price, outcome, result_r, setup, dxy_conf, mistakes, why, review,
                        cl_verdict, cl_score, created_at)
                    SELECT id, trade_date, trade_time, instrument, direction, session,
                        {txt('entry')}, {txt('sl')}, {txt('tp')}, {txt('exit_price')}, outcome, {txt('result_r')},
                        setup, dxy_conf, mistakes, why, review, cl_verdict, cl_score, created_at
                    FROM trades""")
                self.conn.execute("DROP TABLE trades")
                self.conn.execute("ALTER TABLE trades_new RENAME TO trades")
                self.conn.commit()
            finally:
                self.conn.execute("PRAGMA foreign_keys = ON")
        # v0.3: trades.status ('draft' = still being edited, 'done' = finished) and checklist_days.choices.
        # Existing trades become 'done' (the column default), so old entries show up as completed.
        if "status" not in {r["name"] for r in self.conn.execute("PRAGMA table_info(trades)")}:
            self.conn.execute("ALTER TABLE trades ADD COLUMN status TEXT NOT NULL DEFAULT 'done'")
        if "choices" not in {r["name"] for r in self.conn.execute("PRAGMA table_info(checklist_days)")}:
            self.conn.execute("ALTER TABLE checklist_days ADD COLUMN choices TEXT NOT NULL DEFAULT '{}'")
        for table, column, mapping in VALUE_MAP:
            for old, new in mapping.items():
                self.conn.execute(f"UPDATE {table} SET {column} = ? WHERE {column} = ?", (new, old))
        self.conn.commit()

    # ---------------------------------------------------------- checklist
    def get_checklist_day(self, date_str):
        row = self.conn.execute("SELECT * FROM checklist_days WHERE date = ?", (date_str,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("answers", "choices"):
            try:
                d[key] = json.loads(d.get(key) or "{}")
            except Exception:
                d[key] = {}
        return d

    def save_checklist_day(self, date_str, answers, choices, verdict, score, required_ok):
        self.conn.execute(
            """INSERT INTO checklist_days (date, answers, choices, verdict, score, required_ok, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET answers=excluded.answers, choices=excluded.choices,
                 verdict=excluded.verdict, score=excluded.score,
                 required_ok=excluded.required_ok, updated_at=excluded.updated_at""",
            (date_str, json.dumps(answers, ensure_ascii=False), json.dumps(choices, ensure_ascii=False),
             verdict, float(score), 1 if required_ok else 0, _now()))
        self.conn.commit()

    def delete_checklist_day(self, date_str):
        self.conn.execute("DELETE FROM checklist_days WHERE date = ?", (date_str,))
        self.conn.commit()

    # ------------------------------------------------------------- trades
    def create_trade(self, trade_date, trade_time=""):
        cur = self.conn.execute(
            "INSERT INTO trades (trade_date, trade_time, outcome, status, created_at) VALUES (?, ?, 'Open', 'draft', ?)",
            (trade_date, trade_time, _now()))
        self.conn.commit()
        return cur.lastrowid

    def update_trade(self, trade_id, fields):
        cols = [k for k in fields if k in TRADE_FIELDS]
        if not cols:
            return
        sql = "UPDATE trades SET " + ", ".join(f"{c} = ?" for c in cols) + " WHERE id = ?"
        self.conn.execute(sql, [fields[c] for c in cols] + [trade_id])
        self.conn.commit()

    def get_trade(self, trade_id):
        row = self.conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
        return dict(row) if row else None

    def list_trades(self, outcome=None, search=None):
        sql, params, where = "SELECT * FROM trades", [], []
        if outcome:
            where.append("outcome = ?")
            params.append(outcome)
        if search:
            like = f"%{search}%"
            cols = ("instrument", "setup", "dxy_conf", "mistakes", "why", "review", "direction", "session",
                    "entry", "sl", "tp", "exit_price")
            where.append("(" + " OR ".join(f"{c} LIKE ?" for c in cols) + ")")
            params.extend([like] * len(cols))
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY trade_date DESC, trade_time DESC, id DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def trade_numbers(self) -> dict:
        """{trade id: running number}. With n trades the next new trade is number n + 1; deleting a trade
        closes the gap (numbers are a count, not the internal database id)."""
        ids = [r[0] for r in self.conn.execute("SELECT id FROM trades ORDER BY id")]
        return {tid: i + 1 for i, tid in enumerate(ids)}

    def delete_trade(self, trade_id):
        self.conn.execute("DELETE FROM trade_images WHERE trade_id = ?", (trade_id,))
        self.conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        self.conn.commit()

    def distinct_values(self, column):
        if column not in ("setup", "dxy_conf", "instrument", "entry", "sl", "tp", "exit_price"):
            return []
        rows = self.conn.execute(
            f"SELECT DISTINCT {column} AS v FROM trades WHERE {column} != '' ORDER BY {column}").fetchall()
        return [r["v"] for r in rows]

    # ------------------------------------------------------------- images
    def add_image(self, trade_id, kind, caption, filename):
        cur = self.conn.execute(
            "INSERT INTO trade_images (trade_id, kind, caption, filename, created_at) VALUES (?,?,?,?,?)",
            (trade_id, kind, caption, filename, _now()))
        self.conn.commit()
        return cur.lastrowid

    def list_images(self, trade_id):
        rows = self.conn.execute(
            "SELECT * FROM trade_images WHERE trade_id = ? ORDER BY id", (trade_id,)).fetchall()
        return [dict(r) for r in rows]

    def update_image(self, image_id, **fields):
        cols = [k for k in fields if k in ("kind", "caption")]
        if not cols:
            return
        sql = "UPDATE trade_images SET " + ", ".join(f"{c} = ?" for c in cols) + " WHERE id = ?"
        self.conn.execute(sql, [fields[c] for c in cols] + [image_id])
        self.conn.commit()

    def delete_image(self, image_id):
        row = self.conn.execute("SELECT filename FROM trade_images WHERE id = ?", (image_id,)).fetchone()
        self.conn.execute("DELETE FROM trade_images WHERE id = ?", (image_id,))
        self.conn.commit()
        return row["filename"] if row else None
