# Changelog

## 0.7.2
- **Trade Journal: date as DD-MM-YYYY.** The date box is typed and shown as DD-MM-YYYY (14-11-2026). `5.1.2026`,
  `05/01/2026` and the old `2026-11-14` are accepted too and are tidied up when you leave the box. Behind the scenes
  the date is still stored as YYYY-MM-DD, so sorting is unchanged and no existing trade is touched.
- **Enter saves a value for good.** Type something in Pair, Session, Setup, Correlation (pair and setup), Entry, Stop,
  Target, Exit, Risk %, Planned R:R, Mistakes or an image label and press **Enter**: it is saved and offered in the
  drop-down of every later trade, even if no other trade uses it yet. The ✕ in the list still removes it.
- **Direction** has no empty entry any more: only Long and Short.
- **Setup and correlations share the row equally.** Only Setup: it takes the whole row. With one correlation Setup and
  Correlation are half each; with two correlations a third each (the **+** moves to the right edge).
- **Mistakes is as wide as Entry** and sits on a new line under Entry / Stop / Target / Exit, after two new boxes:
  **Risk %** and **Planned R:R** (free text, e.g. `1` and `1:3`). Both are shown on finished trades and are searchable.
- Existing databases get the two new columns automatically on first start.

## 0.7.1
- **Example steps in the checklist:** the first-start template now has two example steps for every option
  (Expansion, Retracement, Reversal, Consolidation, Asia, London open, New York open, New York close and the five
  Psychology options), and the three sections are labelled *(example)*. Edit or delete them freely.
- **Trade Journal: correlation instead of confirmation.**
    - *DXY / ES! confirmation* is now **Correlation**. Next to Setup there is a **+**: press it, choose the correlated
      pair (DXY and ES! are offered, the one that fits the traded pair first, or type any pair) and write what the
      setup was in the box next to it. After the first correlation a second **+** appears on its right for a second
      one. The small ✕ removes a correlation again.
    - Trades from older versions keep their text: the old *DXY confirmation* becomes the first correlation (pair DXY,
      or ES! for NQ! trades). This happens once, automatically.
    - On a finished trade the correlations are shown as their own tiles.
- **Mistakes** moved to its own line under Entry / Stop / Target / Exit, and earlier mistakes can be picked again from
  the drop-down like the other boxes.
- **Remove old values with ✕:** every value in a drop-down list (pair, session, entry, stop, target, exit, setup,
  correlation, mistakes and screenshot labels, the built-in examples too) has a ✕ on its right. It only removes the
  value from the suggestions: your earlier trades keep it, and typing it again brings it back.
- The drop-downs of these boxes are now an own list (type in the box, press the ▾ or the Down key to open it).

## 0.7.0
- **Name cleanup:** every remaining old name was removed from the code, tests, workflows and docs (the source folder is
  now `tradedesk/`). The database file is now `data/tradedesk.db`; an existing database from an older version is
  renamed automatically on first start, so no trade is lost.
- **New first-start layout** (only for a fresh `data/` folder; your existing checklist and settings are not touched):
    - Pre-Trade Checklist: **Today's checklist is now at the top**, above the sections.
    - *Current market phase*: Expansion, Retracement, Reversal, Consolidation.
    - *What time is it?*: Asia, London open, New York open, New York close.
    - *Psychology*: Calm & focused, Tired / slept badly, Losing streak, Overconfidence after a win,
      Anxious / afraid to miss out.
    - None of these options has steps: press **Edit** on an option card and write your own. (The old example
      steps and the "Angry / want revenge" option are gone from the defaults.)
    - Economic Calendar: all impact levels (High, Medium, Low) and all currencies are shown, and the time zone starts
      at **UTC-5**.
- **Trade Journal: reuse what you wrote before.** Pair, Session, Entry, Stop, Target and Exit are now drop-downs like
  Setup: open the list to pick something from an earlier trade, or just type a new value (it is offered next time).
    - Pair examples: EURUSD, GBPUSD, NQ!. Session examples: Asia, London, New York Open, New York Close, Other.
      Entry / Stop / Target / Exit have no examples, only your own earlier values (newest first).
    - **Confirmation follows the pair:** the field is *DXY confirmation* for EURUSD / GBPUSD (any USD pair) and
      *ES! confirmation* for NQ!. Screenshot types got **ES! HTF** and **ES! LTF** next to DXY HTF / DXY LTF, and after
      pasting a screenshot the next type is preselected in the right order (NQ!: HTF, LTF, ES! HTF, ES! LTF, Entry,
      Result).
    - **Screenshot labels can be new:** the "type of next image" box and the label under each screenshot are
      editable: pick HTF / LTF / ... or type your own label (e.g. SMT). Labels you used before appear in the list.
    - Half-typed text of the trade you are editing is never offered as a suggestion.

## 0.6.0
- **New name: Bilenay Trade Desk** The window title, taskbar identity, exe (`BilenayTradeDesk.exe`)
  and release zip (`BilenayTradeDesk-vX.Y.Z-windows.zip`) carry the new name. Your `data/` folder is unchanged: copy it
  next to the new exe.
- **Announcement box** on the Economic Calendar page, between *Next: ...* and *Refresh*: the shared Bilenay announcement
  feed (the one Next Book and Economic Calendar read). It rotates through the announcements, a click opens the board,
  links ask before opening, it is invisible when there is nothing to show, and `"announcements": false` in
  `data/settings.json` turns it off completely.

## 0.5.1
- Checklist: option cards now start **collapsed** (name, number of steps, Select / Edit), so Today's checklist sits much
  higher on the page. Press **Edit** on a card to open its steps for editing and **Done** to close it again. Clicking an
  option's name selects it. A new option opens by itself so you can add its steps right away.

## 0.5.0
- **Psychology section** (example, added once to your checklist): pick how you feel today - Calm & focused, Tired /
  slept badly, Losing streak, Angry / want revenge, Overconfident after a win, Anxious / afraid to miss out. Each option
  has its own reminder steps, which show up in Today's checklist. Nothing is counted automatically: it is only your own
  check. Edit, reorder (little arrows) or delete it like any other section; once deleted it does not come back.
- Checklist: typing no longer redraws anything. Today's checklist is updated when you leave the box (click elsewhere,
  press Enter or Tab). Saving to disk still happens in the background.
- Trade Journal: slower, smoother mouse-wheel scrolling (about 50 px per notch instead of a third of the window);
  touchpads scroll smoothly too. Other pages keep their speed.

## 0.4.0
- **Themes:** Midnight (default), Graphite, OLED Black, Nord, Light and Sand. The selector sits at the right end
  of the tab bar; the theme changes instantly (no restart) and is remembered. Text and background colours of every
  theme were checked for readable contrast.
- The window now starts maximized.
- Clicking an empty spot takes the text cursor out of the box you were typing in (the box saves itself).
- Trade numbers are a running count: with n trades the next new trade is #n+1 (deleting a trade closes the gap).
- Today's checklist: ticking a step no longer throws the page back to the top; the page stays where it is.
- Trade Journal: the checklist record ("% of steps done", "Checklist that day") is no longer shown on trades.
- Fixed an error dialog that could appear when pasting with a drop-down list open.

## 0.3.2
- Checklist redesigned around options and steps:
    - every option now holds its own **steps**; add, edit and delete them right inside the option card
      (Enter in a step opens the next one)
    - pick one option per section; the steps of the picked options appear at the bottom as
      **Today's checklist** - tick each step as you do it on the chart (with a progress bar)
    - removed: the verdict banner (CLEAR / CAUTION / NO TRADE), the star (required) marks and the separate
      section requirements
    - "+ Choice", "+ Add step" and "+ New section" are quiet links that open a one-line input
    - sections are reordered with the small arrows next to "Delete section"
- Your option reminder texts from 0.3.x become steps (one step per line); old section requirements are kept
  as an option called "Checklist". Ticks are saved per day.
- Journal: the checklist chip of a trade now reads "% of steps done".
- Fixed a crash when adding a new section, and a rare error dialog when the screen redrew under the mouse.

## 0.3.1
- Release workflow: release notes now come from this file instead of GitHub's note generator (which failed with a server error).
- Includes everything from 0.3.0 (it was never published as a release):
  - Fixed the jumping tab: the selected tab no longer changes size/position when you switch tabs.
  - New theme pass: deeper background, flat buttons, consistent tabs, slim scrollbars with a solid thumb.
  - Window icon: the app window and taskbar now show the app icon (before, only the .exe file had it).
    `assets/` is now bundled into the exe build.
  - Checklist: **Day notes removed** (existing notes stay in the database, they are just no longer shown).
  - Checklist: sections can have **choices** (pick one per day, e.g. Current market phase -> Retracement).
    Every choice has its own short reminder text. Add them with "+ Add choices" on a section.
  - Journal: a new trade is in **editing** mode (blue banner, "Finish ✓" button); finished trades show as a
    compact read-only card with the result, levels, screenshots and notes, and an "Edit" button.
    Trades from 0.2.0 appear as finished.
  - Journal: screenshots are shown **three per row** (sized to the window) and the description box is gone.
    Old descriptions stay in the database.
  - Economic Calendar: the scrollbar was pushed out of view and its thumb looked hollow - fixed; columns and
    day headings fit, the table gets ~62 % of the width.
  - Database migrates v0.2 data automatically (new `status` and `choices` columns).

## 0.3.0
- Not released; see 0.3.1.

## 0.2.0
- Whole UI in English.
- Checklist: items are now written *requirements* — explain in writing, then confirm (confirm needs an
  explanation). Add requirements and sections directly on the page, drag ⠿ to reorder (also across
  sections), inline two-step delete, thresholds editable in the banner.
- Calendar: time-zone picker fixed; the live clock (HH:MM:SS) now follows the selected zone instantly;
  half-hour zones added.
- Journal: one scrolling feed of trade cards with large annotated screenshots; Entry / Stop / Target /
  Exit / Result are free text (liquidity names etc.); autosave; pagination; thumbnail cache.
- Database migrates v0.1 data automatically.
- Repo: tests, CI, Windows exe build + release workflow, app icon.

## 0.1.0
- First prototype.
