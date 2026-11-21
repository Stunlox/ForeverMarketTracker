# Forever Market Tracker v0.4 — WoW Forever EU Alliance PvP

This version reuses the **working API endpoints from Forever Gold Companion** (`data_sources.py`): `https://oauth.battle.net/token`, `dynamic-forever-eu`, `/data/wow/ruleset/1/auctions/`, and the separate `/commodities` endpoint. ForeverDB uses the `X-API-Key` header.

## Install
Upload these files to your GitHub repository, replacing the existing source. Keep `.github/workflows/windows-exe.yml` at that exact path. GitHub Actions will build `ForeverMarketTracker.exe` on Windows. Download the artifact from Actions, extract and run.

## Configure
Your previously saved credentials remain in `%LOCALAPPDATA%\ForeverMarketTracker\settings.json`. In API & Settings click **Discover WoW Forever auction houses**. Confirm which returned house is **Alliance PvP**, enter its numeric ID, save, then click **Fetch Alliance PvP snapshot**. Do not assume 110 without confirming its market grouping.

The collector fetches normal auctions and commodities together, then stores one combined snapshot. Collection repeats hourly while the GUI is open; background collection while closed requires scheduling the collector executable using Windows Task Scheduler.

**Limitations:** This code has unit tests but has not been validated against your live API credentials. The catalogue importer is single-page and needs a confirmed ForeverDB catalogue endpoint; automatic monthly catalogue updates and exact WoW category hierarchy remain future work. Historical prices are asking prices, not sales. Credentials are stored locally in plain text and must not be committed to public GitHub.
