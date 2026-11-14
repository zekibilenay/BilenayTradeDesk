# Bilenay Trade Desk

A small desktop workspace for a daily EURUSD routine, built with Python + Tkinter. No account, no cloud, no
telemetry: your data stays in the `data/` folder. The only network requests are the economic calendar feed and
the announcement file (see *Announcements & privacy* below).

| Tab | What it does |
|---|---|
| **Pre-Trade Checklist** | Sections hold options (pick one, e.g. market phase); every option holds your own steps. The steps of the options you pick form **Today's checklist** at the top of the page, which you tick off as you trade. Add, edit and delete everything directly on the page. |
| **Economic Calendar** | ForexFactory weekly feed, impact/currency filters, time-zone picker with a live clock, offline cache, rich-text notes. |
| **Trade Journal** | A scrolling feed of trade cards: pair, session and levels (free text, e.g. liquidity names; earlier entries can be picked again from the drop-downs), HTF / LTF / DXY (or ES! for NQ!) screenshots with your own labels, three per row (paste with Ctrl+V), reasoning and review. New trades are edited with autosave; press **Finish** to turn one into a compact read-only card. |

The tabs are independent: the checklist has no calendar widgets. 

## Download (Windows)
Go to **Releases**, download `BilenayTradeDesk-vX.Y.Z-windows.zip`, unzip it anywhere you can write files
(not `Program Files`) and run `BilenayTradeDesk\BilenayTradeDesk.exe`.
Windows SmartScreen may warn because the exe is not code-signed: *More info → Run anyway*.

**Updating:** unzip the new version over the old folder but keep your `data` folder.

## Your data
Everything is stored in the `data/` folder next to the app: `tradedesk.db` (checklist days, trades),
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
`build_exe.bat` (Windows) → `dist\BilenayTradeDesk\BilenayTradeDesk.exe`.

Or on GitHub: **Actions → Build Windows exe → Run workflow** (downloadable artifact), or push a tag:
```bash
git tag v0.7.0 && git push origin v0.7.0      # builds the exe and creates a GitHub Release
```

## Development
```bash
pip install -r requirements-dev.txt
python -m pytest
```
Logic (database, checklist evaluation, calendar parsing) is UI-independent and unit-tested; the Tkinter
tabs live in `tradedesk/*_tab.py`.

## Notes
- Calendar data comes from the public ForexFactory feed; it is rate-limited, so manual refresh is
  limited to once per 2 minutes. This is a personal tool, not financial advice.
- License: MIT.

## Themes

Midnight, Graphite, OLED Black, Nord, Light and Sand. Pick one with the selector at the right end of the tab bar; the choice is remembered.

## Announcements & privacy
The Economic Calendar page shows a one-line **announcement box** next to the *Next:* label. It reads the same shared
announcement file as Next Book and Economic Calendar (`https://zekibilenay.github.io/announcements/feed.json`):
one HTTPS GET at start-up and again every 6 hours while the app stays open (the server only sees
`User-Agent: BilenayTradeDesk/<version>`; nothing about you or your trades is sent). Click the box to open the
announcement board; links open only after you confirm. The box can not be dismissed, but you can turn it off: put
`"announcements": false` into `data/settings.json` (then no request is made at all).
