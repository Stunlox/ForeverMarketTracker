"""Headless collector for Windows Task Scheduler. Run hourly when PC is awake."""
import sys
from core import connect,load_settings,store_snapshot
from api import AuctionClient

def main():
    settings=load_settings();payload=AuctionClient(settings).fetch();db=connect()
    try: print(f'Stored {store_snapshot(db,payload)} items')
    finally:db.close()
if __name__=='__main__':
    try:main()
    except Exception as exc:print(f'Collection failed: {exc}',file=sys.stderr);sys.exit(1)
