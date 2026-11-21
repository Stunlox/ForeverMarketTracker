# Forever Market Tracker — Alliance PvP

Windows desktop auction price history application, with SQLite history and a dark PySide6 interface.

## Download the Windows EXE (no Python required)

Go to **Actions → Build Windows executable → latest successful run → Artifacts → ForeverMarketTracker-Windows**.
Download the ZIP, extract it, and double-click `ForeverMarketTracker.exe`.

The executable is unsigned: Windows SmartScreen may prompt before running. Only run binaries from builds you trust.

## Configure on first launch

Go to **API & Settings** and enter the Blizzard Client Secret and your ForeverDB key on your own PC. The Blizzard Client ID is prefilled. The ForeverDB key is not committed into this public GitHub repository. Settings are stored under `%LOCALAPPDATA%\ForeverMarketTracker\settings.json` (unencrypted).

**Important:** The live Forever Alliance PvP auction endpoint and the ForeverDB catalogue API URL are **not verified**. You must configure supported, verified endpoints before collection works. Blizzard official API credentials alone do not establish that a private-server auction house is exposed. Avoid assigning a guessed connected-realm ID. The current catalogue importer supports a single page, not yet full pagination or automatic monthly refresh.

## Automatic tracking

While the desktop application is open, it checks for new snapshots hourly (after successful API configuration). For collection while the GUI is closed, use Windows Task Scheduler to run the included `ForeverMarketCollector.exe` hourly; your PC must be awake and online. The collector stores data in the same local SQLite database.

## Limitations

Auction listings are **asking prices** and not confirmed sales. Market history starts with the first successful collection; this is an early prototype, not a verified live-trading system.

## Local development

```powershell
python -m pip install -r requirements.txt
python app.py
python -m unittest discover -p 'test_*.py' -v
```

Built on Windows by `.github/workflows/windows-exe.yml` using PyInstaller.
