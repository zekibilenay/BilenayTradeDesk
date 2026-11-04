# Changelog

## 0.3.0
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
