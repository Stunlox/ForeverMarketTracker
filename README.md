# Forever Market Tracker v1.2.3a — Weekday Overnight Trading

New tab **Suggested Buys (Weekday)**: pairs Monday–Thursday 18:00–23:59 UK evening asking prices with the immediately following Tuesday–Friday 12:00–17:59 UK afternoon asking prices. Saturday and Sunday snapshots are excluded from every strategy input, including supply averages and latest-price proxies. Friday evening is excluded because the following day is Saturday. Default history 30 days, minimum 3 paired days, 100 AH units and 60% positive pairs. Includes existing vendor exclusions, category filters, manual right-click exclusions, and UK DST handling. Historical asking prices do not prove completed sales.

## Installation
Extract this ZIP and upload its contents (including `.github/workflows/windows-exe.yml`) to the root of your GitHub repository. Commit to main and download the `ForeverMarketTracker-Windows-v1.2.3a-Portable` GitHub Actions artifact. Keep both app and collector folders together.

## Verification
Run `python -m unittest discover -p 'test_*.py'`. Windows PySide6 and Task Scheduler behaviour must be tested on Windows.

## v1.2.4a — Professions crafting profits

- New **Professions** tab: choose one of eight crafting professions, view per-craft AH proceeds, reagent costs, net profit after AH cut, ROI, and current output supply; double-click for material breakdown.
- New **Import ForeverDB crafting professions** button in **API & Settings**, with a dedicated progress indicator in **Collector Health**. Existing market history and previous recipe imports are preserved if an import fails.
- Import excludes gathering professions, and excludes recipes without identifiable AH-saleable outputs or reagent IDs. Missing prices are not assumed zero.
- Explicit NPC **purchase** prices can be stored from vendor inventory responses (recognized keys: `buyPrice`, `purchasePrice`, `vendorPrice` and snake-case equivalents). **Re-import vendor inventories** to populate this field when the API supplies it. The old vendor table has no purchase price, and an item's NPC sell value is not an NPC purchase price.
- Profit is an estimate based on latest available AH **median asking prices**, not a verified executable order book or actual completed sales. Crafting cooldowns, deposits, AH supply depth, recipe acquisition, binding restrictions, and proc yields are not fully modeled.
- ForeverDB API recipe shape has **not been verified live** in this environment. If the API uses different field names, the importer may report no usable recipes rather than import bad data. No live import or Windows build was performed here.

### v1.2.4a: crafting import diagnostics
The importer now accepts additional nested output/reagent shapes and reports counts of accepted/rejected recipes in Collector Health. If no recipe is usable, the error reports rejection categories and top-level recipe field names to help diagnose ForeverDB schema differences. It does not log or include your API key. The live ForeverDB response has not been verified; share the exact error text if the retry still fails.

## v1.2.4c — Rarity and vendor price visibility

- WoW rarity colours for crafted output names and reagent names (where the item catalogue has quality metadata).
- Double-click a recipe to see a table of AH price, explicit NPC vendor purchase price, selected cheaper source, and vendor stock classification for every priced reagent.
- Collector Health and the Professions tab show vendor price coverage: priced inventory rows, total rows, and unique priced items.
- Vendor importer recognises additional *explicit copper-denominated purchase price* fields; it never treats vendor sell-to-NPC values as purchase costs or assumes missing prices are free.
- Re-run **Import ForeverDB vendor inventories** in API & Settings to populate any newly recognised price fields; the crafting recipe import need not be repeated.
- Updated GitHub Actions ZIP/artifact names to `ForeverMarketTracker-Windows-v1.2.4c-Portable` and Windows version metadata to `1.2.4c`.
- Vendor limited-stock prices are indicative and may not support bulk crafting; no automatic stock-cap quantity calculation is possible without reliable stock amounts.
- The live authenticated ForeverDB schema and Windows executable have not been verified in this environment.

## v1.2.4d — Robust trading price references
- Isolated hourly 8–9g → ~16g → 8–9g reversals are excluded from timing analysis, but sustained repricing and recurring weekday patterns are retained.
- Target Item and Suggested Buys now estimate conservative resale from the lower quartile of historical **market median** asking prices, rather than assuming the cheapest 10% is the resale market.
- Target Item exposes buy/unit, resale/unit and estimated net profit/unit so calculations are auditable.
- Timing advice needs at least two observations in each proposed buy/sell hour; otherwise it is labelled provisional.
- Windows GitHub Actions build name and app version updated to v1.2.4d.
- Historical SQLite data and ForeverDB imports are untouched. These are asking-price estimates, not evidence of executed sales; deposits and failed auctions are excluded.


## v1.2.4e — live vendor coverage and consistent market pricing
- During vendor import, Collector Health updates vendor progress, downloaded inventory rows, rows with explicit NPC purchase prices, unique priced items, and missing prices after each vendor API response. No additional API requests are made for these counters. Existing vendor database stays unchanged until the full import succeeds.
- Market Timing uses the shared isolated-spike detector for its selected metric, excludes flagged observations from the heatmap and timing advice, and requires repeated observations for precise timing recommendations.
- Target Item adds historical buy and timed net/unit columns, distinct from current buy and net/unit. Historical values are estimates, not guaranteed executable orders.
- Windows Actions artifact and EXE version set to v1.2.4e.


## v1.2.4f — Trade Journal
- New Trade Journal tab: predictive catalogue item entry (rarity-coloured), quantity, per-unit gold/silver/copper purchase and sale prices, sold checkbox, optional notes.
- Save, edit, reopen or delete recorded trades; SQLite persists in the existing local database.
- Shows unsold cost, realised P/L after AH cut, and break-even sell price.
- Historical sell advice uses cleaned AH snapshots and requires repeated hour observations; single spikes are not reliable selling windows.
- Sold checkbox represents **the entire recorded lot**. For partial sales, record separate lots.
- Costs and profits are estimates: no deposit, expired auctions, or realised-sale API verification.
- No additional ForeverDB API calls are required.


## v1.2.4g — Hourly collector status
- Persistent coloured scheduler indicator in the status bar on every tab, refreshed every 60 seconds and clickable to open Collector Health.
- Detects missing, disabled, unknown, and stale executable-path tasks, not just existence.
- Collector Health shows exact scheduler state and the next scheduled run.
- No Blizzard or ForeverDB API calls are used for the status check.
- If the task path is stale after an update, click **Enable Hourly Schedule** to recreate it pointing to the current collector EXE.

### v1.2.4h — Buy Now & Hold
Uses fresh local AH snapshots and repeated historical UK weekday/six-hour windows (at least two distinct dates), conservative competitive asking prices, vendor/manual exclusions, rarity and volume filters, configurable budget, holding horizon and minimum net ROI. Stale snapshots over two hours suppress recommendations. Prepare a journal entry and verify the actual purchase before saving. No extra API calls. Historical asking prices do not guarantee sales.
