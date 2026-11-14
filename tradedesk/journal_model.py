"""Journal helpers that do not need the UI: suggestion lists, the confirmation instrument of a pair, image-type order."""

DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "NQ!"]
DEFAULT_SESSIONS = ["Asia", "London", "New York Open", "New York Close", "Other"]
# image types (labels of the screenshots). The pair-specific ones are DXY (EURUSD, GBPUSD) and ES! (NQ!).
DEFAULT_KINDS = ["HTF", "LTF", "DXY HTF", "DXY LTF", "ES! HTF", "ES! LTF", "Entry", "Result", "Other"]


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


def confirmation_symbol(pair) -> str:
    """The instrument you confirm a pair with: NQ! -> ES!, USD pairs (EURUSD, GBPUSD, ...) -> DXY, else ''."""
    p = str(pair or "").upper().replace(" ", "")
    if p.startswith(("NQ", "MNQ")):
        return "ES!"
    if "USD" in p or "DXY" in p:
        return "DXY"
    return ""


def confirmation_label(pair) -> str:
    sym = confirmation_symbol(pair)
    return f"{sym} confirmation" if sym else "Confirmation"


def kind_sequence(pair):
    """The order screenshots are usually taken in. After pasting one, the next image type is preselected."""
    sym = confirmation_symbol(pair)
    middle = [f"{sym} HTF", f"{sym} LTF"] if sym else []
    return ["HTF", "LTF"] + middle + ["Entry", "Result"]


def next_kind(current, pair):
    seq = kind_sequence(pair)
    if current in seq[:-1]:
        return seq[seq.index(current) + 1]
    return current
