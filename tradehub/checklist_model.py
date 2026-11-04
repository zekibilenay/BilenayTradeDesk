"""Checklist template + evaluation logic (independent of the UI).

A template is a list of sections; each section has requirements and (optionally) a set of *choices*
("pick one" options, each with a short reminder text, e.g. market phase: Expansion / Retracement / ...).
For every day, each requirement gets an answer: {"note": <your written explanation>, "confirmed": <bool>},
and each section with choices can have one chosen option id.
"""
import copy
import json
import uuid

from .paths import CHECKLIST_TEMPLATE_PATH, atomic_write_text


def new_id() -> str:
    return uuid.uuid4().hex[:8]


# Just examples - delete or rewrite them directly on the checklist page.
DEFAULT_TEMPLATE = {
    "version": 3,
    "threshold_green": 80,      # % confirmed (and all required confirmed) -> CLEAR TO TRADE
    "threshold_yellow": 60,     # % confirmed -> CAUTION, below -> NO TRADE
    "sections": [
        {"id": "ex_phase", "title": "Current market phase (example)", "items": [], "options": [
            {"id": "ex_p1", "title": "Expansion",
             "desc": "Strong, one-directional displacement. Don't fade it; wait for a pullback or stay out."},
            {"id": "ex_p2", "title": "Retracement",
             "desc": "Price is pulling back into a discount / premium zone inside a larger move. Look for continuation."},
            {"id": "ex_p3", "title": "Reversal",
             "desc": "Structure has shifted against the old trend. Needs confirmation before trusting it."},
            {"id": "ex_p4", "title": "Consolidation",
             "desc": "Tight range, no clear intent. Trade the edges only, or skip the day."},
        ]},
        {"id": "ex_market", "title": "Market conditions (example)", "items": [
            {"id": "ex_1", "text": "Higher-timeframe bias is clear and I can state it in one sentence.", "required": True},
            {"id": "ex_2", "text": "Liquidity and volatility are sufficient for my setup.", "required": False},
        ]},
        {"id": "ex_dxy", "title": "DXY (example)", "items": [
            {"id": "ex_3", "text": "DXY gives a confirmation that agrees with my EURUSD idea.", "required": True},
        ]},
        {"id": "ex_me", "title": "Personal state (example)", "items": [
            {"id": "ex_4", "text": "I know my maximum daily loss and I accept it before entering.", "required": True},
        ]},
    ],
}

VERDICT_LABELS = {
    "green": "CLEAR TO TRADE",
    "yellow": "CAUTION",
    "red": "NO TRADE",
    "none": "NO REQUIREMENTS YET",
    "": "NO RECORD",
}


def normalize(t) -> dict:
    out = {"version": 3, "threshold_green": 80, "threshold_yellow": 60, "sections": []}
    if not isinstance(t, dict):
        return copy.deepcopy(DEFAULT_TEMPLATE)
    for key in ("threshold_green", "threshold_yellow"):
        try:
            out[key] = max(0, min(100, int(t.get(key, out[key]))))
        except (TypeError, ValueError):
            pass
    for s in t.get("sections", []) or []:
        if not isinstance(s, dict):
            continue
        sec = {"id": str(s.get("id") or new_id()), "title": str(s.get("title", "")).strip() or "Untitled section",
               "items": [], "options": []}
        for it in s.get("items", []) or []:
            if not isinstance(it, dict):
                continue
            text = str(it.get("text", "")).strip()
            if text:
                sec["items"].append({"id": str(it.get("id") or new_id()), "text": text,
                                     "required": bool(it.get("required", False))})
        for op in s.get("options", []) or []:
            if not isinstance(op, dict):
                continue
            title = str(op.get("title", "")).strip()
            if title:
                sec["options"].append({"id": str(op.get("id") or new_id()), "title": title,
                                       "desc": str(op.get("desc", "")).strip()})
        out["sections"].append(sec)
    return out


def save_template(t, path=CHECKLIST_TEMPLATE_PATH) -> None:
    atomic_write_text(path, json.dumps(normalize(t), indent=2, ensure_ascii=False))


def load_template(path=CHECKLIST_TEMPLATE_PATH) -> dict:
    try:
        return normalize(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        t = copy.deepcopy(DEFAULT_TEMPLATE)
        save_template(t, path)
        return t
    except Exception:
        try:                                   # corrupt file: keep a backup, start from the default
            path.replace(path.with_suffix(".json.bak"))
        except Exception:
            pass
        t = copy.deepcopy(DEFAULT_TEMPLATE)
        save_template(t, path)
        return t


def coerce_answers(raw) -> dict:
    """Accepts the current format and the old v0.1 one ({id: bool})."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        if isinstance(v, dict):
            out[str(k)] = {"note": str(v.get("note", "")), "confirmed": bool(v.get("confirmed", False))}
        else:
            out[str(k)] = {"note": "", "confirmed": bool(v)}
    return out


def coerce_choices(raw, t=None) -> dict:
    """{section_id: option_id}. With a template, choices whose section/option no longer exists are dropped."""
    out = {}
    if not isinstance(raw, dict):
        return out
    valid = None
    if t is not None:
        valid = {sec["id"]: {o["id"] for o in sec.get("options", [])} for sec in t["sections"]}
    for k, v in raw.items():
        k, v = str(k), str(v)
        if valid is None or v in valid.get(k, ()):
            out[k] = v
    return out


def all_items(t):
    for s in t["sections"]:
        for it in s["items"]:
            yield it


def _confirmed(answer) -> bool:
    if isinstance(answer, dict):
        return bool(answer.get("confirmed"))
    return bool(answer)


def evaluate(t, answers) -> dict:
    """A missing required requirement forces NO TRADE regardless of the percentage."""
    items = list(all_items(t))
    total = len(items)
    checked = sum(1 for it in items if _confirmed(answers.get(it["id"])))
    req = [it for it in items if it["required"]]
    req_total = len(req)
    req_checked = sum(1 for it in req if _confirmed(answers.get(it["id"])))
    pct = (checked / total * 100.0) if total else 0.0
    if total == 0:
        verdict = "none"
    elif req_checked < req_total:
        verdict = "red"
    elif pct >= t["threshold_green"]:
        verdict = "green"
    elif pct >= t["threshold_yellow"]:
        verdict = "yellow"
    else:
        verdict = "red"
    return {"total": total, "checked": checked, "req_total": req_total, "req_checked": req_checked,
            "pct": pct, "verdict": verdict, "required_ok": req_checked == req_total}
