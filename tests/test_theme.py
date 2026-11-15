import pytest

from tradedesk import theme

NAMES = theme.names()


def _c(p, a, b):
    return theme.contrast(p.get(a, a), p.get(b, b))


def test_there_are_several_themes_and_the_default_exists():
    assert len(NAMES) >= 5 and theme.DEFAULT_THEME in NAMES


@pytest.mark.parametrize("name", NAMES)
def test_every_role_has_its_own_colour(name):
    p = theme.palette(name)
    assert set(p) == set(theme.ROLES)
    assert len(set(p.values())) == len(p)                      # needed to map colours back to roles when switching
    assert "#ffffff" not in p.values() and "#000000" not in p.values()


@pytest.mark.parametrize("name", NAMES)
def test_text_is_readable(name):
    p = theme.palette(name)
    for bg in ("BG", "PANEL", "PANEL2"):
        assert _c(p, "FG", bg) >= 7, (name, bg)
        assert _c(p, "MUTED", bg) >= 4.5, (name, bg)
        assert _c(p, "ACCENT", bg) >= 4.5, (name, bg)
        for role in ("GREEN", "YELLOW", "RED", "ORANGE"):
            assert _c(p, role, bg) >= 4.5, (name, role, bg)
    assert _c(p, "FG", "PANEL3") >= 7 and _c(p, "MUTED", "PANEL3") >= 4.5
    assert _c(p, "FG", "SELECT") >= 7
    assert _c(p, "ACCENT", "ACCENT_BG") >= 4.5 and _c(p, "MUTED", "ACCENT_BG") >= 4.5
    assert _c(p, "FG", "INVALID_BG") >= 4.5


@pytest.mark.parametrize("name", NAMES)
def test_buttons_and_calendar_are_readable(name):
    p = theme.palette(name)
    for bg in ("ACCENT_BTN", "ACCENT_HOVER", "RED_BTN"):
        assert _c(p, "#ffffff", bg) >= 4.5, (name, bg)        # white label on a button
    for k in ("HIGH", "MED", "LOW"):
        assert _c(p, f"IMP_{k}", "PANEL") >= 4.5 and _c(p, f"IMP_{k}", "SOON_BG") >= 4.5
        assert _c(p, f"IMP_{k}_DIM", "PANEL") >= 3.0           # past events are dimmed, but still legible
    assert _c(p, "SCROLL", "BG") >= 1.8                         # the scrollbar thumb is visible


def test_unknown_theme_falls_back_to_default():
    try:
        assert theme.set_theme("does not exist")["BG"] == theme.palette(theme.DEFAULT_THEME)["BG"]
        assert theme.current_name() == theme.DEFAULT_THEME
    finally:
        theme.set_theme(theme.DEFAULT_THEME)


def test_module_colours_follow_the_current_theme():
    try:
        theme.set_theme("Light")
        assert theme.BG == theme.palette("Light")["BG"]
        theme.set_theme("Midnight")
        assert theme.BG == theme.palette("Midnight")["BG"]
    finally:
        theme.set_theme(theme.DEFAULT_THEME)
