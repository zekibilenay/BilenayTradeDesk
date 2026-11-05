# Changelog

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
