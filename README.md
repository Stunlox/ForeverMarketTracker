# Forever Market Tracker v0.5 — Full ForeverDB Catalogue

This version imports **all** pages from the official ForeverDB item API, not just the first 100. It preserves the existing SQLite price history and saved credentials. The API is queried with `limit=100` and increasing `offset`, with throttling and retries for 429 responses. Catalogue metadata is committed only when the full download succeeds. Categories are derived from item class/subclass IDs when available; unknown classifications remain Uncategorised.

## Update
Upload the extracted files (including `.github/workflows/windows-exe.yml`) to the same GitHub repository, replacing existing files. GitHub Actions builds the standalone Windows EXE. Close v0.4 before launching v0.5. Keep your existing local database in `%USERPROFILE%\AppData\Local\ForeverMarketTracker`.

In **API & Settings**, keep the existing credentials, enter `https://foreverdb.net/api/v1/items` (or leave URL blank), then click **Import FULL ForeverDB catalogue**. The import should retrieve about 23,805 item records (the count changes as ForeverDB updates). This is metadata only: auction snapshots still come from the Blizzard Forever endpoint hourly while the GUI is open.

The importer is manual in v0.5; monthly auto-refresh is not yet implemented. No credentials are embedded in this public source ZIP. Never upload your local settings.json.

ForeverDB item metadata credit: https://foreverdb.net. Their API terms require visible credit and prohibit distributing API keys in applications.
