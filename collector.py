"""Silent hourly collector; progress and failures are written to local event logs."""
import sys
from collection_service import collect_once

if __name__ == '__main__':
    try:
        collect_once('scheduled')
    except Exception:
        # collection_service records failures in collector_events.jsonl.
        sys.exit(1)
