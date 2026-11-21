"""Headless hourly collector, invoked by Windows Task Scheduler."""
import sys
from collection_service import collect_once
if __name__=='__main__':
    try:print(f'Stored {collect_once("scheduled"):,} items')
    except Exception as exc:print(f'Collection failed: {exc}',file=sys.stderr);sys.exit(1)
