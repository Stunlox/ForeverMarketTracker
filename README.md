# Forever Market Tracker v0.5 — Full ForeverDB Catalogue

This version imports **all** pages from the official ForeverDB item API, not just the first 100. It preserves the existing SQLite price history and saved credentials. The API is queried with `limit=100` and increasing `offset`, with throttling and retries for 429 responses. Catalogue metadata is committed only when the full download succeeds. Categories are derived from item class/subclass IDs when available; unknown classifications remain Uncategorised.

## Update
Upload the extracted files (including `.github/workflows/windows-exe.yml`) to the same GitHub repository, replacing existing files. GitHub Actions builds the standalone Windows EXE. Close v0.4 before launching v0.5. Keep your existing local database in `%USERPROFILE%\AppData\Local\ForeverMarketTracker`.

In **API & Settings**, keep the existing credentials, enter `https://foreverdb.net/api/v1/items` (or leave URL blank), then click **Import FULL ForeverDB catalogue**. The import should retrieve about 23,805 item records (the count changes as ForeverDB updates). This is metadata only: auction snapshots still come from the Blizzard Forever endpoint hourly while the GUI is open.

The importer is manual in v0.5; monthly auto-refresh is not yet implemented. No credentials are embedded in this public source ZIP. Never upload your local settings.json.

ForeverDB item metadata credit: https://foreverdb.net. Their API terms require visible credit and prohibit distributing API keys in applications.

## v0.6 Market Timing tab

New **Market Timing** tab restricts the analysis to Trade Goods from the latest snapshot and lets you select a minimum current supply (default 100 units) and 30–365 day lookback. The 7-by-24 heatmap displays historical median unit listing prices, available quantity and observation count for each weekday/hour in **UK local time** (including daylight saving). Grey cells have fewer than three samples. A preliminary cheapest-versus-highest hourly comparison is only shown after 14 distinct days of snapshots and at least three observations in each compared cell. It is descriptive, not proof of a recurring market opportunity. Values represent *asking prices*, not executed sales; an estimated 5% AH fee is applied to the illustrative spread, without deposits or unsold inventory costs.

No new API calls are made for this tab. Hourly snapshots must continue collecting for patterns to emerge. All existing SQLite history and credentials remain in the same local folder.

## v0.7 Cheapest 10% price tracking

The Market Timing tab now defaults to **Cheapest 10% average**, with selectable Cheapest 20%, Lowest Buyout, and All-units Median. Each snapshot calculates a quantity-weighted average of the cheapest 10% or 20% of **units** on offer, rather than the cheapest fraction of auction listings. Each heatmap cell displays the median of this selected metric across the snapshots for that weekday/hour. Existing snapshots are preserved, but their cheapest-10%/20% values are unavailable and cannot be reconstructed; new metric history starts with the first v0.7 snapshot. Switching back to Lowest Buyout or All-units Median still displays legacy history. The historical price metric is an observed asking price, not an executed sale or guaranteed resale profit.

Upload all files to your existing GitHub repository, replacing prior versions, then download the GitHub Actions build artifact. Keep `%LOCALAPPDATA%\ForeverMarketTracker\market.sqlite3` intact. The hourly collector also uses the upgraded snapshot function.

## v0.8 — Market Timing Simplified

The new **Market Timing Simplified** tab ranks up to 40 trade goods by historical buy/sell time-slot differences, using the **quantity-weighted cheapest 10% average** captured in v0.7+ hourly snapshots. Columns show typical buy and sell prices, UK-local day/hour windows, estimated margin after configurable AH cut, current supply, sample counts and confidence.

To avoid false signals, the ranking requires at least 14 distinct dates, three snapshots in each compared hour, and observations in at least three distinct calendar weeks for both windows. It only includes trade goods meeting the minimum current supply, and suppresses nonpositive estimated margins. The tab will remain empty until sufficient history is collected. A historical asking-price spread does **not** prove actual sales or realizable profit. No existing SQLite database or settings need to be replaced.
