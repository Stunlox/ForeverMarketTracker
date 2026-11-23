# Forever Market Tracker v1.2.3 — Market Volume Filters

Includes all v1.2.2 functionality and a **minimum AH quantity** filter (default 100 units) in Market Browser, Market Timing Simplified, Suggested Buys and Target Item.

- Choose **Latest snapshot** or **Historical average** in each tab. Historical average uses all observations in the selected lookback window, including only snapshots where the item was listed.
- Set minimum to **0** to disable filtering.
- AH quantity is *listed supply*, **not sales volume**; high supply does not guarantee demand.
- Investment planner affordability still uses its separate 10% of *latest observed supply* conservative cap, even when filtering on historical average.
- Market Timing Simplified shows the chosen filter quantity in its AH qty column.
- Historical auction data and vendor classifications remain untouched. No additional ForeverDB or Blizzard download is required.

## Installation
Extract this ZIP and upload its contents (including `.github/workflows/windows-exe.yml`) to the root of your GitHub repository. Commit to main and download the `ForeverMarketTracker-Windows-v1.2.3-Portable` GitHub Actions artifact. Keep both app and collector folders together.

## Verification
Run `python -m unittest discover -p 'test_*.py'`. Windows PySide6 and Task Scheduler behaviour must be tested on Windows.
