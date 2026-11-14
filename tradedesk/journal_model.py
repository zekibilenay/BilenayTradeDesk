"""Journal helpers that do not need the UI: suggestion lists, correlation pairs, image-type order, hidden suggestions."""

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
