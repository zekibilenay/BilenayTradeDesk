from tradedesk import calendar_data as cd

RAW = [
    {"title": "Unemployment Claims", "country": "USD", "date": "2026-10-08T08:30:00-04:00", "impact": "Medium",
     "forecast": "200K", "previous": "197K"},
    {"title": "Main Refinancing Rate", "country": "EUR", "date": "2026-10-29T09:15:00+01:00", "impact": "High"},
    {"title": "OPEC", "country": "ALL", "date": "2026-10-04T05:15:00-04:00", "impact": "Holiday"},
    {"title": "broken", "date": "not a date"},
    {"country": "USD"},
]


def test_parse_events():
    ev = cd.parse_events(RAW)
    assert len(ev) == 3
    assert [e["country"] for e in ev] == ["ALL", "USD", "EUR"]          # sorted by time
    assert ev[0]["impact"] == "Low"                                      # holiday -> low
    assert ev[1]["dt"].startswith("2026-10-08T12:30")                    # converted to UTC


def test_cache_roundtrip(tmp_path):
    p = tmp_path / "c.json"
    ev = cd.parse_events(RAW)
    fetched = cd.save_cache(ev, p)
    assert cd.load_cache(p) == (ev, fetched)
    assert cd.load_cache(tmp_path / "missing.json") == ([], None)
