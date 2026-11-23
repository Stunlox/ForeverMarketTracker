"""Collector health tab: seven-day display, unlimited price history."""
import time
from datetime import datetime
from PySide6.QtCore import QFileSystemWatcher, Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QProgressBar,QTableWidget,QTableWidgetItem,QMessageBox,QHeaderView
from collection_service import recent_events, BACKUP_DIR, LOG_PATH
from scheduler import enable_task,disable_task,task_status

class CollectorHealthTab(QWidget):
    collect_requested=Signal()
    snapshot_saved=Signal()
    def __init__(self,db,parent=None):
        super().__init__(parent);self.db=db;self.running=False
        lay=QVBoxLayout(self)
        title=QLabel('COLLECTOR HEALTH');title.setStyleSheet('font-size:20px;font-weight:bold;');lay.addWidget(title)
        self.next_label=QLabel('Next Blizzard API pull: checking scheduler...');lay.addWidget(self.next_label)
        self.last_label=QLabel('Last successful collection: —');lay.addWidget(self.last_label)
        self.coverage=QLabel('Last 7 days: —');lay.addWidget(self.coverage)
        self.database=QLabel('Historical database: retained indefinitely');lay.addWidget(self.database)
        self.backups=QLabel('Backups: —');lay.addWidget(self.backups)
        self.progress_label=QLabel('Collector idle');lay.addWidget(self.progress_label)
        self.vendor_label=QLabel('ForeverDB vendor import: not started this session');lay.addWidget(self.vendor_label)
        self.vendor_progress=QProgressBar();self.vendor_progress.setRange(0,100);self.vendor_progress.setValue(0);lay.addWidget(self.vendor_progress)
        self.profession_label=QLabel('ForeverDB crafting recipes: not started this session');lay.addWidget(self.profession_label)
        self.profession_progress=QProgressBar();self.profession_progress.setRange(0,100);lay.addWidget(self.profession_progress)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0);lay.addWidget(self.progress)
        buttons=QHBoxLayout();lay.addLayout(buttons)
        self.manual=QPushButton('Collect Now');self.manual.clicked.connect(self.collect_requested.emit);buttons.addWidget(self.manual)
        self.enable=QPushButton('Enable Hourly Schedule');self.enable.clicked.connect(self.enable_schedule);buttons.addWidget(self.enable)
        self.disable=QPushButton('Disable Schedule');self.disable.clicked.connect(self.disable_schedule);buttons.addWidget(self.disable)
        self.update_button=QPushButton('Refresh Status');self.update_button.clicked.connect(self.refresh);buttons.addWidget(self.update_button)
        lay.addWidget(QLabel('Recent collection events (last 7 days shown; market prices are never deleted)'))
        self.events=QTableWidget(0,4);self.events.setHorizontalHeaderLabels(['Time (local)','Result','Items','Details']);self.events.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch);lay.addWidget(self.events)
        # Observe changes to the local event log without polling Windows Task Scheduler.
        # QFileSystemWatcher uses OS file notifications, not periodic API requests.
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.touch(exist_ok=True)
        self.watcher=QFileSystemWatcher([str(LOG_PATH)], self)
        self.watcher.fileChanged.connect(self._event_log_changed)
        self._last_success=None
        self.schedule_status={'enabled':False,'next':'Not checked'}
        self.refresh()
        successes=[e for e in recent_events() if e.get('status')=='success']
        self._last_success=self.db.execute('SELECT MAX(id) FROM snapshots').fetchone()[0]
    def vendor_started(self):
        self.vendor_progress.setRange(0,0)
        self.vendor_label.setText('ForeverDB vendor import: connecting…')
    def vendor_progress_update(self,stage,current,total):
        if total:
            self.vendor_progress.setRange(0,100)
            self.vendor_progress.setValue(min(100,int(100*current/total)))
        else:self.vendor_progress.setRange(0,0)
        self.vendor_label.setText(f'ForeverDB: {stage} — {current:,} / {total:,}' if total else f'ForeverDB: {stage} — {current:,}')
    def vendor_finished(self,message,success=True):
        self.vendor_progress.setRange(0,100)
        self.vendor_progress.setValue(100 if success else 0)
        self.vendor_label.setText('ForeverDB vendor import: '+message)
    def profession_started(self):
        self.profession_progress.setRange(0,0)
        self.profession_label.setText('ForeverDB crafting recipes: connecting…')
    def profession_progress_update(self,stage,current,total):
        if total:
            self.profession_progress.setRange(0,100)
            self.profession_progress.setValue(min(100,int(current*100/total)))
        else:self.profession_progress.setRange(0,0)
        self.profession_label.setText(f'ForeverDB recipes: {stage} — {current:,} / {total:,}' if total else f'ForeverDB recipes: {stage} — {current:,}')
    def profession_finished(self,message,success=True):
        self.profession_progress.setRange(0,100)
        self.profession_progress.setValue(100 if success else 0)
        self.profession_label.setText('ForeverDB crafting recipes: '+message)
    def set_running(self,stage):
        self.running=True;self.manual.setEnabled(False);self.progress.setRange(0,0);self.progress_label.setText(stage)
    def set_finished(self,message):
        self.running=False;self.manual.setEnabled(True);self.progress.setRange(0,100);self.progress.setValue(100);self.progress_label.setText(message);self.refresh_local()
    def enable_schedule(self):
        try:enable_task();self.refresh()
        except Exception as exc:QMessageBox.warning(self,'Scheduler',str(exc))
    def disable_schedule(self):
        try:disable_task();self.refresh()
        except Exception as exc:QMessageBox.warning(self,'Scheduler',str(exc))
    def refresh(self):
        # Only explicit refresh / initial opening / schedule changes query schtasks.
        self.schedule_status=task_status()
        self.refresh_local()

    def _event_log_changed(self, *_):
        # FileSystemWatcher is notification-based; no periodic external process.
        if str(LOG_PATH) not in self.watcher.files() and LOG_PATH.exists():
            self.watcher.addPath(str(LOG_PATH))
        self.refresh_local()
        newest=self.db.execute('SELECT MAX(id) FROM snapshots').fetchone()[0]
        if newest is not None and self._last_success is not None and newest!=self._last_success:
            self.snapshot_saved.emit()
        self._last_success=newest

    def refresh_local(self):
        status=self.schedule_status
        self.next_label.setText('Next Blizzard API pull: '+status['next'] if status['enabled'] else 'Next Blizzard API pull: Not scheduled (enable hourly collection)')
        events=recent_events()
        if events and not self.running:
            latest=events[-1]
            if latest.get('status')=='started':
                self.progress.setRange(0,0)
                self.progress_label.setText('Scheduled Blizzard collection in progress…' if latest.get('origin')=='scheduled' else 'Collection in progress…')
            elif latest.get('status') in ('success','failed'):
                self.progress.setRange(0,100)
                self.progress.setValue(100 if latest['status']=='success' else 0)
                self.progress_label.setText('Last collection: '+latest['status']+' — '+latest.get('detail',''))
        successes=[e for e in events if e.get('status')=='success']
        if successes:
            last=successes[-1];self.last_label.setText('Last successful collection: '+datetime.fromtimestamp(last['timestamp']).strftime('%d %b %Y %H:%M')+f" — {last.get('count',0):,} items")
        since=time.time()-7*86400
        recent=[e for e in events if e.get('timestamp',0)>=since and e.get('status') in ('success','failed')]
        success=sum(e['status']=='success' for e in recent)
        self.coverage.setText(f'Last 7 days: {success} successful / {len(recent)} completed attempts (not a scheduled-slot success rate)')
        count=self.db.execute('SELECT COUNT(*),MIN(captured_at),MAX(captured_at) FROM snapshots').fetchone()
        size=__import__('core').DB_PATH.stat().st_size if __import__('core').DB_PATH.exists() else 0
        self.database.setText(f'Historical database: {count[0]:,} snapshots retained | {size/1048576:.1f} MB | no 7-day purge')
        backups=list(BACKUP_DIR.glob('market-*.sqlite3')) if BACKUP_DIR.exists() else []
        self.backups.setText(f'Daily backups: {len(backups)} retained (maximum 14)')
        recent=recent[-100:][::-1]
        self.events.setRowCount(len(recent))
        for i,e in enumerate(recent):
            values=[datetime.fromtimestamp(e.get('timestamp',0)).strftime('%d %b %H:%M'),e.get('status',''),str(e.get('count') or ''),e.get('detail','')]
            for j,val in enumerate(values):self.events.setItem(i,j,QTableWidgetItem(val))
