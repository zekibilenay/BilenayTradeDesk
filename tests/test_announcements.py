import datetime
import io
import json
import urllib.error
import urllib.request

import pytest

from tradedesk import announcements as an
from tradedesk import theme

D = datetime.date


def _feed():
    """Shaped like the live shared feed (https://github.com/zekibilenay/announcements)."""
    return {"schema": 1, "apps": {}, "announcements": [
        {"id": "nextbook-update", "apps": ["nextbook"], "max_version": "1.8.1", "type": "update", "priority": 5,
         "text": {"tr": "Yeni sürüm!", "en": "A new version of Next Book is out!"},
         "url": "https://github.com/zekibilenay/nextbook/releases/latest"},
        {"id": "ec-update", "apps": ["economiccalendar"], "max_version": "1.0.0", "type": "update", "priority": 5,
         "text": {"en": "A new version of Economic Calendar is out!"}},
        {"id": "reader", "apps": ["nextbook"], "type": "recommended", "priority": 4,
         "text": {"en": "A cozy place to read"}, "url": "https://bilenay.itch.io/bilenay-reader"},
        {"id": "itch", "apps": ["*"], "type": "info", "priority": 3,
         "text": {"tr": "Bizi itch.io'da bulabilirsin", "en": "Find us on itch.io: drop by, follow us and leave a comment."}},
    ]}


def _ids(feed, **kw):
    return [a["id"] for a in an.select_announcements(feed, **kw)]


def test_tradedesk_gets_only_the_announcements_for_everyone_and_for_itself():
    assert _ids(_feed(), app_id="tradedesk", version="0.6.0", today=D(2026, 11, 20)) == ["itch"]
    f = _feed()
    f["announcements"].append({"id": "td", "apps": ["tradedesk"], "priority": 9, "type": "new_app",
                               "text": {"en": "Hello Trade Desk"}})
    got = an.select_announcements(f, app_id="tradedesk", version="0.6.0")
    assert [a["id"] for a in got] == ["td", "itch"] and got[0]["type"] == "new_app"


def test_default_app_id_is_the_one_documented():
    assert an.APP_ID == "tradedesk"


def test_version_window_and_dates():
    f = {"announcements": [
        {"id": "old", "max_version": "0.5.1", "text": "only old versions"},
        {"id": "new", "min_version": "0.6.0", "text": "only new versions"},
        {"id": "later", "starts": "2026-12-01", "text": "starts later"},
        {"id": "gone", "expires": "2026-11-01", "text": "expired"},
        {"id": "now", "starts": "2026-11-01", "expires": "2026-11-30", "text": "in window"}]}
    today = D(2026, 11, 20)
    assert _ids(f, version="0.5.1", today=today) == ["old", "now"]
    assert _ids(f, version="0.6.0", today=today) == ["new", "now"]
    assert _ids(f, version="0.6.0", today=D(2026, 12, 1)) == ["new", "later"]


def test_priority_order_is_stable():
    f = {"announcements": [{"id": c, "priority": p, "text": c} for c, p in (("a", 1), ("b", 5), ("c", 1), ("d", 5))]}
    assert _ids(f) == ["b", "d", "a", "c"]


def test_latest_version_announcement():
    f = {"apps": {"tradedesk": {"latest": "0.7.0", "url": "https://example.com/get"}}, "announcements": []}
    got = an.select_announcements(f, version="0.6.0")
    assert got[0]["type"] == "update" and "0.7.0" in got[0]["text"] and got[0]["url"] == "https://example.com/get"
    assert an.select_announcements(f, version="0.7.0") == []                # already up to date
    f["apps"]["tradedesk"].pop("url")
    assert an.select_announcements(f, version="0.6.0")[0]["url"] == an.FALLBACK_URL


def test_languages():
    t = {"tr": "merhaba", "en": "hello", "zh-CN": "你好"}
    assert an._loc(t, "tr") == "merhaba" and an._loc(t, "en") == "hello"
    assert an._loc(t, "zh") == "你好"                                          # 'zh-CN' key matches language 'zh'
    assert an._loc(t, "fr") == "hello"                                        # unknown language -> English
    assert an._loc({"de": "hallo"}, "en") == "hallo" and an._loc(5, "en") == "" and an._loc("plain", "tr") == "plain"


def test_broken_data_never_raises():
    for bad in (None, [], "x", 5, {}, {"announcements": "x"}, {"announcements": [None, 1, "x", {}, {"id": ""}]},
                {"apps": [], "announcements": []}):
        assert an.select_announcements(bad) == []
    f = {"announcements": [
        {"id": "x", "text": "bad date", "starts": "not-a-date"},
        {"id": "y", "text": "bad prio", "priority": "high"},
        {"id": "ok", "text": "fine", "type": "weird", "url": "http://insecure.example"}]}
    got = an.select_announcements(f)
    assert [a["id"] for a in got] == ["ok"] and got[0]["type"] == "info" and got[0]["url"] == ""


def test_text_is_shortened_and_whitespace_collapsed():
    f = {"announcements": [{"id": "a", "text": "word " * 400}, {"id": "b", "text": "  many \n spaces\t here "}]}
    got = an.select_announcements(f)
    assert len(got[0]["text"]) <= an.MAX_TEXT and got[1]["text"] == "many spaces here"


def test_only_https_links():
    assert an.safe_url("https://a.b/c") and not an.safe_url("http://a.b") and not an.safe_url("javascript:alert(1)")
    assert not an.safe_url("") and not an.safe_url(None) and not an.safe_url("https://" + "a" * 600)


def test_parse_version():
    assert an.parse_version("0.6.0") == (0, 6, 0) and an.parse_version("v1.10") == (1, 10)
    assert an.parse_version("1.10.0") > an.parse_version("1.9.9") and an.parse_version("junk") == (0,)


class _Font:
    def measure(self, s):
        return len(s) * 7


def test_fit_text():
    f = _Font()
    assert an.fit_text(f, "short", 200) == "short"
    cut = an.fit_text(f, "a very long announcement text that does not fit", 100)
    assert cut.endswith("…") and f.measure(cut) <= 100
    assert an.fit_text(f, "anything", 5) == "anything"                         # not laid out yet: leave it alone


def test_fetch_rejects_plain_http():
    with pytest.raises(ValueError):
        an.fetch_feed("http://example.com/feed.json")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(monkeypatch, payload):
    class Op:
        def open(self, req, timeout=0):
            self.req = req
            return _Resp(payload)
    op = Op()
    monkeypatch.setattr(urllib.request, "build_opener", lambda *h: op)
    return op


def test_fetch_parses_json_and_sends_only_a_user_agent(monkeypatch):
    op = _opener(monkeypatch, json.dumps(_feed()).encode())
    assert an.fetch_feed("https://example.com/feed.json")["schema"] == 1
    assert op.req.get_header("User-agent").startswith("BilenayTradeDesk/")
    assert set(k.lower() for k in op.req.headers) <= {"user-agent", "accept"}


def test_fetch_limits_the_size(monkeypatch):
    _opener(monkeypatch, b" " * (an.MAX_FEED_BYTES + 10))
    with pytest.raises(ValueError):
        an.fetch_feed("https://example.com/feed.json")


def test_redirect_to_http_is_blocked():
    h = an._HttpsOnlyRedirect()
    req = urllib.request.Request("https://example.com/feed.json")
    with pytest.raises(urllib.error.URLError):
        h.redirect_request(req, None, 302, "Found", {}, "http://example.com/feed.json")
    assert h.redirect_request(req, None, 302, "Found", {}, "https://example.org/feed.json") is not None


@pytest.mark.parametrize("kind", an.ANN_TYPES)
def test_icon_is_a_round_badge(kind):
    rows = an.icon_rows(kind, 20, "#336699", "#ffffff", "#101010")
    assert len(rows) == 20 and all(len(r) == 20 for r in rows)
    assert rows[0][0] == "#101010" and rows[19][19] == "#101010"              # corners = background
    flat = {c for r in rows for c in r}
    assert all(len(c) == 7 and c[0] == "#" for c in flat)
    assert "#336699" in flat and "#ffffff" in flat                             # circle and symbol are both drawn
    assert len(flat) > 3                                                       # smooth (anti-aliased) edge


@pytest.mark.parametrize("name", theme.names())
def test_box_and_icons_are_readable_in_every_theme(name):
    try:
        theme.set_theme(name)
        p = theme.palette(name)
        for bg in (theme.PANEL2, an.hover_bg()):
            assert theme.contrast(theme.FG, bg) >= 7, (name, "text")
            assert theme.contrast(theme.MUTED, bg) >= 4.5, (name, "counter")
            assert theme.contrast(theme.ACCENT, bg) >= 1.8, (name, "edge")
        for kind in an.ANN_TYPES:
            fill, glyph = an.icon_colors(kind)
            assert theme.contrast(fill, glyph) >= 3.0, (name, kind, "symbol on circle")
            assert theme.contrast(fill, theme.PANEL2) >= 1.8, (name, kind, "circle on box")
    finally:
        theme.set_theme(theme.DEFAULT_THEME)
