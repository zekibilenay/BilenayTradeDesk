import json
from pathlib import Path

from .paths import atomic_write_text

DEFAULTS = {
    "geometry": "1500x900",
    "theme": "Midnight",
    "announcements": True,                  # shared Bilenay announcement box in the calendar (false = off, no request)
    "tz_offset": -5.0,                      # calendar time zone (UTC-5)
    "hidden_suggestions": {},               # journal drop-down values removed with the ✕: {list name: [values]}
    "cal_view": "week",                     # "today" | "week"
    "cal_impacts": ["High", "Medium", "Low"],         # every impact level
    "cal_currencies": ["ALL", "AUD", "CAD", "CHF", "CNY", "EUR", "GBP", "JPY", "NZD", "USD"],   # every currency
}


class Settings:
    def __init__(self, path: Path):
        self.path = path
        self.data = dict(DEFAULTS)
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value, save=True):
        self.data[key] = value
        if save:
            self.save()

    def save(self):
        try:
            atomic_write_text(self.path, json.dumps(self.data, indent=2, ensure_ascii=False))
        except Exception:
            pass
