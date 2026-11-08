# Changelog

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
  - Window icon: the app window and taskbar now show the TradeHub icon (before, only the .exe file had it).
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
