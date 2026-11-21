"""Shared, locked auction collection and persistent collector event log."""
import json, os, sqlite3, time, traceback
from pathlib import Path
from core import APP_DIR, DB_PATH, connect, load_settings, store_snapshot
from api import AuctionClient

LOG_PATH = APP_DIR / 'collector_events.jsonl'
LOCK_PATH = APP_DIR / 'collector.lock'
BACKUP_DIR = APP_DIR / 'backups'

def record_event(status, detail='', count=None, origin='scheduled'):
    event = {'timestamp': int(time.time()), 'status': status, 'detail': str(detail)[:600], 'count': count, 'origin': origin}
    with LOG_PATH.open('a', encoding='utf8') as f: f.write(json.dumps(event) + '\n')
    return event

def recent_events(limit=500):
    if not LOG_PATH.exists(): return []
    from collections import deque
    with LOG_PATH.open(encoding='utf8') as f: lines=list(deque(f,maxlen=limit))
    events=[]
    for line in lines:
        try: events.append(json.loads(line))
        except (ValueError,TypeError): continue
    return events

class CollectorLock:
    def __enter__(self):
        self.file = LOCK_PATH.open('a+b')
        try:
            if os.name=='nt':
                import msvcrt
                self.file.seek(0); self.file.write(b'0'); self.file.flush(); self.file.seek(0)
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError):
            self.file.close()
            raise RuntimeError('Another auction collection is already running')
        return self
    def __exit__(self,*args):
        try:
            if os.name=='nt':
                import msvcrt
                self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
        finally:self.file.close()

def backup_database(keep=14):
    BACKUP_DIR.mkdir(parents=True,exist_ok=True)
    day=time.strftime('%Y-%m-%d',time.localtime())
    dest=BACKUP_DIR / f'market-{day}.sqlite3'
    if not dest.exists():
        source=sqlite3.connect(DB_PATH)
        try:
            target=sqlite3.connect(dest)
            try:source.backup(target)
            finally:target.close()
        finally:source.close()
    backups=sorted(BACKUP_DIR.glob('market-????-??-??.sqlite3'),reverse=True)
    for old in backups[keep:]:old.unlink()
    return dest

def collect_once(origin='scheduled',progress=None):
    def report(stage):
        if progress:progress(stage)
    try:
        with CollectorLock():
            record_event('started',origin=origin)
            report('Authenticating and downloading Blizzard auctions...')
            payload=AuctionClient(load_settings()).fetch()
            report('Saving auction prices to SQLite...')
            db=connect()
            try:count=store_snapshot(db,payload)
            finally:db.close()
            report('Checking daily database backup...')
            backup_database()
            record_event('success',f'{count:,} items',count,origin)
            report('Collection complete')
            return count
    except Exception as exc:
        record_event('failed',str(exc),origin=origin)
        raise
