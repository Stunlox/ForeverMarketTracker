from pathlib import Path
import ast
api=Path('api.py'); core=Path('core.py'); app=Path('app.py')
for f in (api,core,app):
    if not f.exists(): raise SystemExit('Missing '+str(f))
s=api.read_text()
s=s.replace('def fetch_catalogue(settings, progress=None):','def fetch_catalogue(settings, progress=None, on_page=None, start_offset=0, should_cancel=None):')
s=s.replace('    result = []\n    offset = 0','    result = []\n    offset = start_offset')
s=s.replace('    while True:\n        for attempt in range(4):','    while True:\n        if should_cancel and should_cancel(): return {"cancelled":True,"offset":offset}\n        for attempt in range(4):')
s=s.replace('        result.extend(rows)\n        offset += len(rows)','        next_offset = offset + len(rows)\n        if on_page: on_page(rows,next_offset,total)\n        else: result.extend(rows)\n        offset = next_offset')
s=s.replace('        time.sleep(0.12)','        time.sleep(2.4)')
s=s.replace("    if not result: raise ValueError('ForeverDB returned no catalogue items')\n    return result", "    if on_page: return {'cancelled':False,'offset':offset}\n    if not result: raise ValueError('ForeverDB returned no catalogue items')\n    return result")
ast.parse(s);api.write_text(s)
s=core.read_text()
s=s.replace('def import_catalogue(db,items):','def import_catalogue(db,items,complete=True):')
s=s.replace('        db.execute("INSERT OR REPLACE INTO metadata VALUES (\'catalogue_refreshed\',?)",(str(now),))','        if complete: db.execute("INSERT OR REPLACE INTO metadata VALUES (\'catalogue_refreshed\',?)",(str(now),))')
s+='''

def catalogue_checkpoint(db):
    row=db.execute("SELECT value FROM metadata WHERE key='catalogue_offset'").fetchone()
    return int(row[0]) if row else 0

def save_catalogue_page(db,rows,offset,total):
    import_catalogue(db,rows,complete=False)
    with db:
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('catalogue_offset',?)",(str(offset),))
        if total is not None:
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('catalogue_total',?)",(str(total),))

def finish_catalogue(db):
    with db:
        db.execute("DELETE FROM metadata WHERE key IN ('catalogue_offset','catalogue_total')")
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('catalogue_refreshed',?)",(str(int(time.time())),))
'''
ast.parse(s);core.write_text(s)
s=app.read_text()
s=s.replace('import sys, time, traceback','import sys, time, traceback, threading')
s=s.replace('QSplitter)','QSplitter,QProgressBar)')
s=s.replace('copper,import_catalogue','copper,import_catalogue,catalogue_checkpoint,save_catalogue_page,finish_catalogue')
s=s.replace('class Worker(QThread):\n    done=Signal(object); failed=Signal(str)','class Worker(QThread):\n    done=Signal(object); failed=Signal(str); progress=Signal(int,int,float)')
s=s.replace('self.worker=None;self.catalogue_running=False','self.worker=None;self.catalogue_running=False;self.catalogue_cancel=threading.Event()')
s=s.replace('Forever Market Tracker 0.5','Forever Market Tracker 0.6')
s=s.replace("catalog=QPushButton('Import FULL ForeverDB catalogue (~24k items)');catalog.clicked.connect(self.catalogue);form.addRow(catalog)","self.catalog_button=QPushButton('Import / Resume ForeverDB');self.catalog_button.clicked.connect(self.catalogue);form.addRow(self.catalog_button)\n        self.cancel_button=QPushButton('Pause import');self.cancel_button.clicked.connect(self.pause_catalogue);self.cancel_button.setEnabled(False);form.addRow(self.cancel_button)\n        self.catalogue_progress=QProgressBar();form.addRow(self.catalogue_progress)")
start=s.index('    def catalogue(self):')
end=s.index('    def tick(self):',start)
replacement='''    def pause_catalogue(self):
        self.catalogue_cancel.set()
        self.catalogue_status.setText('Pausing after current page...')

    def catalogue(self):
        self.save()
        if self.worker and self.worker.isRunning(): return
        self.catalogue_cancel.clear()
        self.catalogue_running=True
        self.catalog_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        db=connect()
        try: start=catalogue_checkpoint(db)
        finally: db.close()
        started=time.monotonic()
        self.catalogue_status.setText(f'Resuming from item {start:,}...')
        def fn():
            db=connect()
            try:
                def on_page(rows,offset,total):
                    save_catalogue_page(db,rows,offset,total)
                    self.worker.progress.emit(offset,total or 0,time.monotonic()-started)
                result=fetch_catalogue(self.settings,on_page=on_page,start_offset=start,should_cancel=self.catalogue_cancel.is_set)
                if not result['cancelled']: finish_catalogue(db)
                return result
            finally: db.close()
        def progress(offset,total,elapsed):
            if total:
                self.catalogue_progress.setRange(0,100)
                self.catalogue_progress.setValue(min(100,int(offset*100/total)))
                remaining=max(0,total-offset)
                speed=(offset-start)/max(elapsed,1)
                eta=int(remaining/speed) if speed>0 else 0
                self.catalogue_status.setText(f'{offset:,} / {total:,} ({offset*100/total:.1f}%) | {remaining:,} left | ETA {eta//60}m {eta%60}s | Saved')
            else:
                self.catalogue_progress.setRange(0,0)
                self.catalogue_status.setText(f'{offset:,} items saved; total not reported')
        def done(result):
            self.catalogue_running=False
            self.catalog_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            if result['cancelled']:
                self.catalogue_status.setText(f'Paused at {result["offset"]:,} items. Click Resume.')
            else:
                self.catalogue_progress.setRange(0,100)
                self.catalogue_progress.setValue(100)
                self.catalogue_status.setText(f'Complete: {result["offset"]:,} items')
            self.refresh()
        def failed(msg):
            self.catalogue_running=False
            self.catalog_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.catalogue_status.setText('Stopped: '+msg+'; saved batches retained.')
            QMessageBox.warning(self,'ForeverDB import',msg)
        self.worker=Worker(fn)
        self.worker.progress.connect(progress)
        self.worker.done.connect(done)
        self.worker.failed.connect(failed)
        self.worker.start()

    def closeEvent(self,event):
        if self.catalogue_running and self.worker and self.worker.isRunning():
            self.catalogue_cancel.set()
            self.worker.wait()
        super().closeEvent(event)
'''
s=s[:start]+replacement+s[end:]
ast.parse(s);app.write_text(s)
print('v0.6 patch applied')
