# Forever Market Tracker v1.2.3a — Weekday Overnight Trading

New tab **Suggested Buys (Weekday)**: pairs Monday–Thursday 18:00–23:59 UK evening asking prices with the immediately following Tuesday–Friday 12:00–17:59 UK afternoon asking prices. Saturday and Sunday snapshots are excluded from every strategy input, including supply averages and latest-price proxies. Friday evening is excluded because the following day is Saturday. Default history 30 days, minimum 3 paired days, 100 AH units and 60% positive pairs. Includes existing vendor exclusions, category filters, manual right-click exclusions, and UK DST handling. Historical asking prices do not prove completed sales.

## Installation
Extract this ZIP and upload its contents (including `.github/workflows/windows-exe.yml`) to the root of your GitHub repository. Commit to main and download the `ForeverMarketTracker-Windows-v1.2.3a-Portable` GitHub Actions artifact. Keep both app and collector folders together.

## Verification
Run `python -m unittest discover -p 'test_*.py'`. Windows PySide6 and Task Scheduler behaviour must be tested on Windows.
