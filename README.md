# Bilenay Trade Desk

A small desktop workspace for a daily EURUSD routine, built with Python + Tkinter. Runs on Windows, macOS and Linux. No account, no cloud, no
telemetry: your data stays in the `data/` folder. The only network requests are the economic calendar feed and
the announcement file (see *Announcements & privacy* below).

| Tab | What it does |
|---|---|
| **Pre-Trade Checklist** | Sections hold options (pick one, e.g. market phase); every option holds your own steps. The steps of the options you pick form **Today's checklist** at the top of the page, which you tick off as you trade. Add, edit and delete everything directly on the page. |
| **Economic Calendar** | ForexFactory weekly feed, impact/currency filters, time-zone picker with a live clock, offline cache, rich-text notes. |
| **Trade Journal** | A scrolling feed of trade cards: pair, session and levels (free text, e.g. liquidity names; dates are typed as DD-MM-YYYY; a value typed in any drop-down box and confirmed with Enter is saved and offered in every later trade, and can be removed with ✕), risk % and planned R:R, up to two correlated pairs per trade (+ button), HTF / LTF / DXY (or ES! for NQ!) screenshots with your own labels, three per row (paste with Ctrl+V), reasoning and review. New trades are edited with autosave; press **Finish** to turn one into a compact read-only card. |

The tabs are independent: the checklist has no calendar widgets. 

## Download
Go to **Releases** (or the itch.io page) and take the file for your system:

| System | File | Start |
|---|---|---|
| **Windows** 10 / 11 | `BilenayTradeDesk-vX.Y.Z-windows.zip` | Unzip anywhere you can write files (not `Program Files`), run `BilenayTradeDesk\BilenayTradeDesk.exe`. |
| **macOS**, Apple Silicon (M1 and newer) | `BilenayTradeDesk-vX.Y.Z-macos-arm64.zip` | Unzip, drag `BilenayTradeDesk.app` to *Applications*, open it. |
| **macOS**, Intel | `BilenayTradeDesk-vX.Y.Z-macos-intel.zip` | Same. |
| **Linux**, 64-bit | `BilenayTradeDesk-vX.Y.Z-linux.tar.gz` | `tar xzf BilenayTradeDesk-*-linux.tar.gz`, then run `BilenayTradeDesk/BilenayTradeDesk`. Optional: `./install-linux.sh` inside that folder adds an application-menu entry (`--remove` removes it). |

`SHA256SUMS.txt` in every release lets you check a download.

**The apps are not code-signed**, so each system warns once:
- **Windows SmartScreen:** *More info → Run anyway*.
- **macOS:** if it says the app can not be opened, go to *System Settings → Privacy & Security*, scroll down to the
  message about Bilenay Trade Desk and click **Open Anyway** (older macOS: right-click the app → *Open*). Or, in Terminal:
  `xattr -cr /Applications/BilenayTradeDesk.app`.
- **Linux:** built on Ubuntu 22.04, so it runs on Ubuntu 22.04+, Debian 12+, Fedora 36+ and similar. To paste screenshots
  with Ctrl+V install `xclip` (X11) or `wl-clipboard` (Wayland); **Add file…** always works.

**Updating:** Windows / Linux: unzip the new version over the old folder but keep your `data` folder.
macOS: just replace the app (your data is elsewhere, see below).

## Your data
Everything is stored in the `data/` folder next to the app on Windows and Linux; on a **Mac** in
`~/Library/Application Support/BilenayTradeDesk/` (Finder: *Go → Go to Folder…*). It holds `tradedesk.db`
(checklist days, trades), `images/` (screenshots), `checklist_template.json`, `calendar_notes.json`, `settings.json`.
**Back up = copy that folder.** It is git-ignored; never commit it. (If the folder next to the app is not writable, the
app uses `%APPDATA%\BilenayTradeDesk` on Windows or `~/.local/share/BilenayTradeDesk` on Linux instead.)

## Run from source
```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py
```
Python 3.10+ with Tk (the python.org installer includes it on Windows and macOS; on Linux `sudo apt install python3-tk`).

## Build the app yourself
PyInstaller can not cross-compile: build on the system you want the app for.
```bash
pip install -r requirements.txt pyinstaller
python build.py              # -> release/BilenayTradeDesk-v<version>-<system>.zip or .tar.gz
```
(`build_exe.bat` on Windows and `./build.sh` on macOS / Linux do the same, including the pip step.)
Needs Python 3.10+ with Tk 8.6 (Windows / macOS: the python.org installer; Linux: `sudo apt install python3-tk`).

Or on GitHub: **Actions → Build apps → Run workflow** (downloadable artifacts), or push a tag. That builds Windows, macOS
(Apple Silicon and Intel) and Linux on four runners and publishes one release with all files:
```bash
git tag v0.7.3 && git push origin v0.7.3
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
