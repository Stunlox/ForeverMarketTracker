# Forever Market Tracker v1.2.2 — Vendor Inventory Import

Includes v1.2.1 features and a separate ForeverDB vendor inventory import.

1. Extract and upload **all files** to GitHub, including `.github/workflows/windows-exe.yml`.
2. Build via GitHub Actions and extract both Windows application folders together.
3. Enter/save your ForeverDB API key in API & Settings.
4. Click **Import ForeverDB vendor inventories (separate pull)**. It does NOT require re-downloading the full item catalogue or Blizzard auctions.
5. Watch **Collector Health** for stage, progress, and final counts.
6. Suggested Buys, Target Item and Market Timing Simplified have independent Include unlimited/limited vendor checkboxes (both off by default).
7. Manage Exclusions shows imported vendor inventory and manual exclusions.

**Important:** ForeverDB documents vendor inventory endpoints, but does not publish a complete example JSON schema. The importer only classifies limited/unlimited stock where an explicit field is present; otherwise stock is **unknown**, which remains visible by default. Do not infer stock from NPC buy/sell prices. Vendor imports are atomic: a failed pull does not delete previous vendor data. Manual exclusions always override checkbox choices. Vendor status may originate from Classic reference data, not necessarily verified in Forever.

**API limits:** Free ForeverDB tier 5,000 calls/day, 30/min. Vendor detail requests can take several minutes. Each successful inventory import uses approximately one request per vendor plus pagination.

**Verification:** Unit tests exercise classification and exclusion logic. Live authenticated vendor JSON and compiled Windows build still require user testing.

Credit: https://foreverdb.net
