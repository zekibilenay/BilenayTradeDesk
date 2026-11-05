"""Checklist template + evaluation logic (independent of the UI).

A template is a list of sections. Every section holds *options* ("pick one", e.g. market phase:
Expansion / Retracement / ...) and every option holds *steps* (what you do on the chart when that option
applies). For every day you pick one option per section; the steps of the picked options form the day's
checklist, and you tick each step as you do it.
"""
import copy
import json
import uuid

from .paths import CHECKLIST_TEMPLATE_PATH, atomic_write_text

GREEN_AT = 80       # % of steps done -> green (shown next to a trade in the journal)
YELLOW_AT = 60      # % of steps done -> yellow, below -> red


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def _steps(*texts):
    return [{"id": new_id(), "text": t} for t in texts]


def default_template() -> dict:
    """Just examples - rewrite them directly on the checklist page."""
    return {"version": 4, "sections": [
        {"id": "ex_phase", "title": "Current market phase (example)", "options": [
            {"id": "ex_p1", "title": "Expansion", "steps": _steps(
                "Mark the HTF zone", "Find the optimal entry zone for the next move",
                "Wait for price to reach it", "Wait for a confirmation", "Enter with the LTF zone")},
            {"id": "ex_p2", "title": "Retracement", "steps": _steps(
                "Mark the HTF zone and the internal liquidity", "Wait for the liquidity to be taken")},
            {"id": "ex_p3", "title": "Reversal", "steps": _steps(
                "Wait for a structure shift", "Confirm before trusting it")},
            {"id": "ex_p4", "title": "Consolidation", "steps": _steps("No trade: skip the day")},
        ]},
        {"id": "ex_time", "title": "What time is it? (example)", "options": [
            {"id": "ex_t1", "title": "London open", "steps": _steps("Determine the current market phase")},
            {"id": "ex_t2", "title": "New York open", "steps": _steps("Wait for a liquidity sweep")},
            {"id": "ex_t3", "title": "Outside my hours", "steps": _steps("Do not trade")},
        ]},
    ]}


def _clean_steps(raw, id_prefix=None) -> list:
    """id_prefix gives upgraded (id-less) steps stable ids, so ticks saved for them survive a restart."""
    out = []
    for k, st in enumerate(raw or []):
        if isinstance(st, dict):
            text, sid = str(st.get("text", "")).strip(), st.get("id")
        else:
            text, sid = str(st).strip(), None
        if text:
            out.append({"id": str(sid or (f"{id_prefix}-s{k}" if id_prefix else new_id())), "text": text})
    return out


def normalize(t) -> dict:
    """Cleans a template and upgrades older files:
       * v0.3 options had one free-text reminder ("desc") -> every line becomes a step
       * v0.2 sections had requirements ("items") -> they are kept as an option called "Checklist"."""
    if not isinstance(t, dict):
        return default_template()
    out = {"version": 4, "sections": []}
    for s in t.get("sections", []) or []:
        if not isinstance(s, dict):
            continue
        sec = {"id": str(s.get("id") or new_id()), "title": str(s.get("title", "")).strip() or "Untitled section",
               "options": []}
        for op in s.get("options", []) or []:
            if not isinstance(op, dict):
                continue
            title = str(op.get("title", "")).strip()
            if not title:
                continue
            oid = str(op.get("id") or new_id())
            if "steps" in op:
                steps = _clean_steps(op.get("steps"), oid)
            else:
                steps = _clean_steps(str(op.get("desc", "")).splitlines(), oid)
            sec["options"].append({"id": oid, "title": title, "steps": steps})
        legacy = _clean_steps(s.get("items"))
        if legacy:
            sec["options"].append({"id": f"{sec['id']}-legacy", "title": "Checklist", "steps": legacy})
        out["sections"].append(sec)
    return out


def save_template(t, path=CHECKLIST_TEMPLATE_PATH) -> None:
    atomic_write_text(path, json.dumps(normalize(t), indent=2, ensure_ascii=False))


def load_template(path=CHECKLIST_TEMPLATE_PATH) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        t = normalize(raw)
        if t != raw:                           # upgraded an older file: write it back once (stable ids)
            save_template(t, path)
        return t
    except FileNotFoundError:
        t = default_template()
        save_template(t, path)
        return t
    except Exception:
        try:                                   # corrupt file: keep a backup, start from the default
            path.replace(path.with_suffix(".json.bak"))
        except Exception:
            pass
        t = default_template()
        save_template(t, path)
        return t


def coerce_answers(raw) -> dict:
    """{step_id: {"note": str, "confirmed": bool}}; also accepts older formats ({id: bool})."""
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


def selected_steps(t, choices):
    """[(section, option, step)] for the options picked in `choices`, in page order."""
    out = []
    for sec in t["sections"]:
        oid = choices.get(sec["id"])
        for opt in sec.get("options", []):
            if opt["id"] == oid:
                out.extend((sec, opt, st) for st in opt["steps"])
    return out


def _confirmed(answer) -> bool:
    if isinstance(answer, dict):
        return bool(answer.get("confirmed"))
    return bool(answer)


def evaluate(t, answers, choices) -> dict:
    """Progress of the day's checklist: how many of the picked options' steps are ticked."""
    steps = selected_steps(t, choices)
    total = len(steps)
    checked = sum(1 for _s, _o, st in steps if _confirmed(answers.get(st["id"])))
    pct = (checked / total * 100.0) if total else 0.0
    if total == 0:
        verdict = "none"
    elif pct >= GREEN_AT:
        verdict = "green"
    elif pct >= YELLOW_AT:
        verdict = "yellow"
    else:
        verdict = "red"
    return {"total": total, "checked": checked, "pct": pct, "verdict": verdict, "required_ok": True}
