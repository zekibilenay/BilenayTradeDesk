"""Journal helpers that do not need the UI: dates, suggestion lists, correlation pairs, image-type order, saved and hidden suggestions."""
import re
from datetime import date


DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "NQ!"]
DEFAULT_SESSIONS = ["Asia", "London", "New York Open", "New York Close", "Other"]
# image types (labels of the screenshots). The pair-specific ones are DXY (EURUSD, GBPUSD) and ES! (NQ!).
DEFAULT_KINDS = ["HTF", "LTF", "DXY HTF", "DXY LTF", "ES! HTF", "ES! LTF", "Entry", "Result", "Other"]
DEFAULT_CORR_PAIRS = ["DXY", "ES!"]


def merge_unique(*lists):
    """Joins several lists, keeps the first occurrence of every (non-empty) value and the original order."""
    seen, out = set(), []
    for lst in lists:
        for v in lst or []:
            v = str(v).strip()
            if v and v not in seen:
                seen.add(v)
                out.append(v)
    return out


def correlation_symbol(pair) -> str:
    """The instrument a pair is usually correlated with: NQ! -> ES!, USD pairs (EURUSD, GBPUSD, ...) -> DXY."""
    p = str(pair or "").upper().replace(" ", "")
    if p.startswith(("NQ", "MNQ")):
        return "ES!"
    if "USD" in p or "DXY" in p:
        return "DXY"
    return ""


def correlation_defaults(pair):
    """Example correlation pairs for the drop-down; the one that fits the traded pair comes first."""
    sym = correlation_symbol(pair)
    return merge_unique([sym] if sym else [], DEFAULT_CORR_PAIRS)


def kind_sequence(pair):
    """The order screenshots are usually taken in. After pasting one, the next image type is preselected."""
    sym = correlation_symbol(pair)
    middle = [f"{sym} HTF", f"{sym} LTF"] if sym else []
    return ["HTF", "LTF"] + middle + ["Entry", "Result"]


def next_kind(current, pair):
    seq = kind_sequence(pair)
    if current in seq[:-1]:
        return seq[seq.index(current) + 1]
    return current


# ---- suggestions the user removed with the ✕ in a drop-down -------------------------------------------------
# Removing only hides a value from the lists (earlier trades keep it). {group: [values]}; typing it again brings it back.

def visible(values, hidden):
    gone = set(hidden or [])
    return [v for v in values if v not in gone]


def hide_value(hidden, group, value):
    """-> new dict with `value` hidden in `group`."""
    out = {k: list(v) for k, v in (hidden or {}).items()}
    value = str(value).strip()
    if value and value not in out.setdefault(group, []):
        out[group].append(value)
    return out


def unhide_value(hidden, group, value):
    """-> new dict where `value` is shown again in `group` (same dict content if it was not hidden)."""
    out = {k: list(v) for k, v in (hidden or {}).items()}
    value = str(value).strip()
    if value in out.get(group, []):
        out[group].remove(value)
        if not out[group]:
            del out[group]
    return out


# ---- values saved with Enter ----------------------------------------------------------------------------------
# Typing a value in a drop-down box and pressing Enter saves it for good, so it is offered in every later trade
# (even when no other trade uses it yet). {group: [values]}, oldest first.

def remember_value(saved, group, value):
    """-> new dict with `value` saved in `group` (same content if it was already there or is blank)."""
    out = {k: list(v) for k, v in (saved or {}).items()}
    value = str(value or "").strip()
    if value and value not in out.setdefault(group, []):
        out[group].append(value)
    if not out.get(group):
        out.pop(group, None)
    return out


def saved_values(saved, group, newest_first=False):
    vals = list((saved or {}).get(group, []))
    return vals[::-1] if newest_first else vals


# ---- dates: shown as DD-MM-YYYY, stored as YYYY-MM-DD (so sorting and filtering keep working) ---------------

_DMY = re.compile(r"^\s*(\d{1,2})[-./](\d{1,2})[-./](\d{4})\s*$")
_YMD = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$")


def parse_date(text):
    """What the person typed (DD-MM-YYYY; also DD.MM.YYYY, DD/MM/YYYY or the old YYYY-MM-DD) -> 'YYYY-MM-DD',
    or None when it is not a real date."""
    text = str(text or "")
    m = _DMY.match(text)
    if m:
        d, mo, y = (int(x) for x in m.groups())
    else:
        m = _YMD.match(text)
        if not m:
            return None
        y, mo, d = (int(x) for x in m.groups())
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def display_date(iso):
    """'YYYY-MM-DD' (as stored) -> 'DD-MM-YYYY' (as shown). Anything that is not a stored date is returned as it is."""
    m = _YMD.match(str(iso or ""))
    if not m:
        return str(iso or "")
    y, mo, d = m.groups()
    return f"{int(d):02d}-{int(mo):02d}-{y}"
