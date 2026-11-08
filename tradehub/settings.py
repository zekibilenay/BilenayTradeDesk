import json
from pathlib import Path

from .paths import atomic_write_text

DEFAULTS = {
    "geometry": "1500x900",
    "theme": "Midnight",
    "psychology_example_added": False,      # the example Psychology section is offered once (0.5.0)
    "tz_offset": 3.0,                       # calendar time zone (UTC+3 = Turkey)
    "cal_view": "week",                     # "today" | "week"
    "cal_impacts": ["High", "Medium"],
    "cal_currencies": ["EUR", "USD"],       # EURUSD-focused default
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
