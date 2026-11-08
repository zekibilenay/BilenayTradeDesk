# TradeHub

A small desktop workspace for a daily EURUSD routine, built with Python + Tkinter. Local-only: no account,
no cloud, no telemetry.

| Tab | What it does |
|---|---|
| **Pre-Trade Checklist** | Sections hold options (pick one, e.g. market phase); every option holds your own steps. The steps of the options you pick form **Today's checklist** at the bottom, which you tick off as you trade. Add, edit and delete everything directly on the page. |
| **Economic Calendar** | ForexFactory weekly feed, impact/currency filters, time-zone picker with a live clock, offline cache, rich-text notes. |
| **Trade Journal** | A scrolling feed of trade cards: levels (free text, e.g. liquidity names), HTF / LTF / DXY screenshots, three per row (paste with Ctrl+V), reasoning and review. New trades are edited with autosave; press **Finish** to turn one into a compact read-only card. |

The tabs are independent: the checklist has no calendar widgets. A trade card only records which
checklist verdict that day had.

## Download (Windows)
Go to **Releases**, download `TradeHub-vX.Y.Z-windows.zip`, unzip it anywhere you can write files
(not `Program Files`) and run `TradeHub\TradeHub.exe`.
Windows SmartScreen may warn because the exe is not code-signed: *More info → Run anyway*.

**Updating:** unzip the new version over the old folder but keep your `data` folder.

## Your data
Everything is stored in the `data/` folder next to the app: `tradehub.db` (checklist days, trades),
`images/` (screenshots), `checklist_template.json`, `calendar_notes.json`, `settings.json`.
**Back up = copy `data/`.** It is git-ignored; never commit it.

## Run from source
```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py
```
Python 3.10+ with Tk (on Windows the python.org installer includes it).

## Build the exe yourself
`build_exe.bat` (Windows) → `dist\TradeHub\TradeHub.exe`.

Or on GitHub: **Actions → Build Windows exe → Run workflow** (downloadable artifact), or push a tag:
```bash
git tag v0.5.0 && git push origin v0.5.0      # builds the exe and creates a GitHub Release
```

## Development
```bash
pip install -r requirements-dev.txt
python -m pytest
```
Logic (database, checklist evaluation, calendar parsing) is UI-independent and unit-tested; the Tkinter
tabs live in `tradehub/*_tab.py`.

## Notes
- Calendar data comes from the public ForexFactory feed; it is rate-limited, so manual refresh is
  limited to once per 2 minutes. This is a personal tool, not financial advice.
- License: MIT.

## Themes

Midnight, Graphite, OLED Black, Nord, Light and Sand. Pick one with the selector at the right end of the tab bar; the choice is remembered.
