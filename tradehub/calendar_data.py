"""Calendar data: ForexFactory weekly feed, parsing and cache (independent of the UI)."""
import json
import urllib.request
from datetime import datetime, timezone

from .paths import CALENDAR_CACHE_PATH, atomic_write_text

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
USER_AGENT = "TradeHub/0.1"
IMPACT_MAP = {"high": "High", "medium": "Medium", "low": "Low", "holiday": "Low", "non-economic": "Low"}


def fetch_feed(timeout=15):
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_events(raw):
    events = []
    for it in raw or []:
        try:
            d = datetime.fromisoformat(str(it["date"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        impact = IMPACT_MAP.get(str(it.get("impact", "")).strip().lower(), "Low")
        events.append({
            "title": str(it.get("title", "")).strip(),
            "country": (str(it.get("country", "")).strip().upper() or "ALL"),
            "impact": impact,
            "dt": d.astimezone(timezone.utc).isoformat(),
            "forecast": str(it.get("forecast") or "").strip(),
            "previous": str(it.get("previous") or "").strip(),
            "actual": str(it.get("actual") or "").strip(),
        })
    events.sort(key=lambda e=None: e["dt"])
    return events


def save_cache(events, path=CALENDAR_CACHE_PATH):
    payload = {"fetched_at": datetime.now(timezone.utc).isoformat(), "events": events}
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False))
    return payload["fetched_at"]


def load_cache(path=CALENDAR_CACHE_PATH):
    """-> (events, fetched_at_iso | None)"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("events", []), data.get("fetched_at")
    except Exception:
        return [], None
