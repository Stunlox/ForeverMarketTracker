import sys, time, traceback
from pathlib import Path
from PySide6.QtGui import QIcon,QColor
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLineEdit,QComboBox,QTableWidget,QTableWidgetItem,QLabel,QTabWidget,QFormLayout,QSpinBox,QMessageBox,QHeaderView,QAbstractItemView,QSplitter)
from PySide6.QtCharts import QChart,QChartView,QLineSeries,QValueAxis
from core import connect,load_settings,save_settings,store_snapshot,market_rows,history,copper,import_catalogue,quality_for_items,QUALITY_COLORS,QUALITY_NAMES
from api import AuctionClient,fetch_catalogue
from timing_tab import MarketTimingTab
from simplified_tab import SimplifiedTimingTab
from collector_health import CollectorHealthTab
from investment_tab import SuggestedBuysTab,TargetItemTab
from collection_service import collect_once

def resource_path(relative):
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return str(base / relative)

STYLE='''QWidget {background:#101720;color:#e5edf6;font: 12px "Segoe UI";} QLineEdit,QComboBox,QSpinBox {background:#1d2938;border:1px solid #344456;border-radius:5px;padding:7px;} QPushButton {background:#245c72;border:0;border-radius:5px;padding:9px 14px;font-weight:600;} QPushButton:hover {background:#307f96;} QTableWidget {background:#172231;alternate-background-color:#1d2938;gridline-color:#29384a;selection-background-color:#236b75;} QHeaderView::section {background:#253548;color:#b9ccdf;padding:8px;border:0;} QTabWidget::pane {border:1px solid #344456;} QTabBar::tab {padding:11px 20px;background:#1c2a3a;} QTabBar::tab:selected {background:#28677b;}'''
class Worker(QThread):
    done=Signal(object); failed=Signal(str)
    def __init__(self,fn):super().__init__();self.fn=fn
    def run(self):
        try:self.done.emit(self.fn())
        except Exception as e:self.failed.emit(str(e))
class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.db=connect();self.settings=load_settings();self.last_check=0;self.worker=None;self.catalogue_running=False
        self.setWindowTitle('Forever Market Tracker 1.2 | Alliance PvP');self.setWindowIcon(QIcon(resource_path('assets/app_icon.png')));self.resize(1300,820)
        self.tabs=QTabWidget();self.setCentralWidget(self.tabs)
        self.market=QWidget();self.tabs.addTab(self.market,'Market Browser');self.setup_market()
        self.timing=MarketTimingTab(self.db);self.tabs.addTab(self.timing,'Market Timing')
        self.simplified=SimplifiedTimingTab(self.db);self.tabs.addTab(self.simplified,'Market Timing Simplified')
        self.suggested=SuggestedBuysTab(self.db);self.tabs.addTab(self.suggested,'Suggested Buys')
        self.target=TargetItemTab(self.db);self.tabs.addTab(self.target,'Target Item')
        self.health=CollectorHealthTab(self.db);self.tabs.addTab(self.health,'Collector Health');self.health.collect_requested.connect(self.scan)
        self.health.snapshot_saved.connect(self.refresh)
        self.config=QWidget();self.tabs.addTab(self.config,'API & Settings');self.setup_config()
        self.statusBar().showMessage('Local database ready. API not yet validated.')
        self.refresh()
    def setup_market(self):
        lay=QVBoxLayout(self.market);top=QHBoxLayout();lay.addLayout(top)
        self.search=QLineEdit();self.search.setPlaceholderText('Search item names...');self.search.textChanged.connect(self.refresh);top.addWidget(self.search)
        self.category=QComboBox();self.category.currentTextChanged.connect(self.refresh);top.addWidget(self.category)
        self.period=QComboBox();self.period.addItems(['7 days','30 days','90 days','365 days']);self.period.setCurrentText('30 days');self.period.currentTextChanged.connect(self.refresh);top.addWidget(self.period)
        scan=QPushButton('Fetch snapshot');scan.clicked.connect(self.scan);top.addWidget(scan)
        splitter=QSplitter(Qt.Orientation.Vertical);lay.addWidget(splitter)
        self.table=QTableWidget(0,8);self.table.setHorizontalHeaderLabels(['Item','Category','Current','30d median','Below median','Quantity','Listings','Observations']);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);self.table.setAlternatingRowColors(True);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.itemSelectionChanged.connect(self.show_history);splitter.addWidget(self.table)
        self.chart=QChart();self.chart.setTitle('Select an item to view price history');self.chart.setBackgroundBrush(__import__('PySide6').QtGui.QColor('#172231'));self.chart.setTitleBrush(__import__('PySide6').QtGui.QColor('#e5edf6'))
        self.chartview=QChartView(self.chart);splitter.addWidget(self.chartview);splitter.setSizes([470,240])
        self.summary=QLabel('No market snapshots yet');lay.addWidget(self.summary)
    def setup_config(self):
        form=QFormLayout(self.config);self.fields={}
        for key,label in [('house_id','Forever auction house ID (discover below)'),('client_id','Blizzard client ID'),('client_secret','Blizzard client secret'),('foreverdb_url','ForeverDB catalogue URL'),('foreverdb_key','ForeverDB API key')]:
            field=QLineEdit(str(self.settings.get(key,'')))
            if 'secret' in key or 'key' in key:field.setEchoMode(QLineEdit.EchoMode.Password)
            self.fields[key]=field;form.addRow(label,field)
        self.interval=QSpinBox();self.interval.setRange(15,1440);self.interval.setValue(int(self.settings['interval_minutes']));form.addRow('Refresh interval (minutes)',self.interval)
        self.cut=QSpinBox();self.cut.setRange(0,30);self.cut.setValue(int(self.settings['ah_cut_percent']));form.addRow('AH cut % (estimate)',self.cut)
        save=QPushButton('Save settings');save.clicked.connect(self.save);form.addRow(save)
        discover=QPushButton('Discover WoW Forever auction houses');discover.clicked.connect(self.discover);form.addRow(discover)
        validate=QPushButton('Fetch Alliance PvP snapshot (auctions + commodities)');validate.clicked.connect(self.scan);form.addRow(validate)
        catalog=QPushButton('Import FULL ForeverDB catalogue (~24k items)');catalog.clicked.connect(self.catalogue);form.addRow(catalog)
        self.catalogue_status=QLabel('Catalogue not yet refreshed this session');form.addRow(self.catalogue_status)
        form.addRow(QLabel('Credentials stay in local settings.json. This MVP does not encrypt them; protect your Windows account.'))
        form.addRow(QLabel('Select the Alliance PvP house ID from the discovered list. No house ID is assumed.'))
        form.addRow(QLabel('Item metadata: ForeverDB.net — https://foreverdb.net (credit required).'))
    def save(self):
        self.settings.update({k:v.text().strip() for k,v in self.fields.items()});self.settings['interval_minutes']=self.interval.value();self.settings['ah_cut_percent']=self.cut.value();save_settings(self.settings);self.statusBar().showMessage('Settings saved')
    def work(self,fn,on_done):
        if self.worker and self.worker.isRunning():return
        self.worker=Worker(fn);self.worker.done.connect(on_done);self.worker.failed.connect(lambda msg:QMessageBox.warning(self,'API validation / import failed',msg));self.worker.start()
    def discover(self):
        self.save()
        def done(houses):
            lines=[]
            for h in houses:
                if isinstance(h,dict):
                    ident=h.get('id',h.get('auction_house_id','?'))
                    lines.append(f'{ident}: {h.get("name",h.get("type",str(h)))}')
                else:lines.append(str(h))
            QMessageBox.information(self,'WoW Forever auction houses',
                'Choose the Alliance PvP house ID from this list and enter it in settings:\n\n'+'\n'.join(lines[:80]))
        self.work(lambda:AuctionClient(self.settings).discover_houses(),done)

    def scan(self):
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage('Another operation is already running')
            return
        self.save()
        self.health.set_running('Fetching Blizzard auction data...')
        self.statusBar().showMessage('Collecting Blizzard auction snapshot...')
        def done(count):
            self.last_check=time.time()
            self.health.set_finished(f'Completed: {count:,} priced items saved')
            self.statusBar().showMessage(f'Validated snapshot: {count:,} priced items.')
            self.refresh()
        def failed(msg):
            self.health.set_finished('Collection failed: '+msg)
            self.statusBar().showMessage('Collection failed')
            QMessageBox.warning(self,'Collection failed',msg)
        self.worker=Worker(lambda:collect_once('manual'))
        self.worker.done.connect(done);self.worker.failed.connect(failed);self.worker.start()
    def catalogue(self):
        self.save()
        if self.worker and self.worker.isRunning():return
        self.catalogue_status.setText('Importing all pages; this may take a minute...')
        def fn():
            items=fetch_catalogue(self.settings)
            db=connect()
            try:return import_catalogue(db,items)
            finally:db.close()
        def done(count):
            self.catalogue_status.setText(f'Full catalogue imported: {count:,} items')
            self.statusBar().showMessage(f'Imported {count:,} item records from ForeverDB')
            self.refresh()
        self.work(fn,done)
    def refresh(self,*_):
        cats=['All']+[r[0] for r in self.db.execute('SELECT DISTINCT category FROM items ORDER BY category') if r[0]]
        selected=self.category.currentText();self.category.blockSignals(True);self.category.clear();self.category.addItems(cats);self.category.setCurrentText(selected if selected in cats else 'All');self.category.blockSignals(False)
        days=int(self.period.currentText().split()[0]);rows=market_rows(self.db,self.search.text(),self.category.currentText(),days)
        rows.sort(key=lambda r:r[6],reverse=True)
        self.table.setRowCount(len(rows));self.ids=[]
        qualities=quality_for_items(self.db,[r[0] for r in rows])
        for i,r in enumerate(rows):
            item_id,name,cat,sub,current,median,discount,qty,listings,observations=r;self.ids.append(item_id)
            for j,val in enumerate([name,cat+((' / '+sub) if sub else ''),copper(current),copper(median),f'{discount:+.1f}%',str(qty),str(listings),str(observations)]):
                cell=QTableWidgetItem(val);cell.setData(Qt.ItemDataRole.UserRole,item_id)
                if j==0 and qualities.get(item_id) in QUALITY_COLORS:
                    quality=qualities[item_id];cell.setForeground(QColor(QUALITY_COLORS[quality]));cell.setToolTip(f'{QUALITY_NAMES[quality]} quality')
                self.table.setItem(i,j,cell)
        self.summary.setText(f'{len(rows):,} items with latest auction data | Historical comparisons use observed lowest buyouts, not completed sales')
        self.timing.load_items()
        self.simplified.refresh()
        self.suggested.refresh()
        self.target.refresh()
    def show_history(self):
        selection=self.table.selectedItems()
        if not selection:return
        item_id=selection[0].data(Qt.ItemDataRole.UserRole);days=int(self.period.currentText().split()[0]);data=history(self.db,item_id,days)
        self.chart.removeAllSeries()
        for axis in self.chart.axes():self.chart.removeAxis(axis)
        self.chart.setTitle(selection[0].text()+' — minimum buyout (gold)')
        if not data:return
        series=QLineSeries();series.setColor(__import__('PySide6').QtGui.QColor('#55d6b0'))
        for idx,(ts,low,median,qty) in enumerate(data):series.append(idx,low/10000)
        self.chart.addSeries(series)
        x=QValueAxis();x.setTitleText(f'Observation (first {time.strftime("%d %b",time.localtime(data[0][0]))}; last {time.strftime("%d %b",time.localtime(data[-1][0]))})');x.setRange(0,max(1,len(data)-1))
        y=QValueAxis();y.setTitleText('Gold');y.setRange(0,max(1,max(r[1] for r in data)/10000*1.1))
        self.chart.addAxis(x,Qt.AlignmentFlag.AlignBottom);self.chart.addAxis(y,Qt.AlignmentFlag.AlignLeft);series.attachAxis(x);series.attachAxis(y)
if __name__=='__main__':
    app=QApplication(sys.argv);app.setWindowIcon(QIcon(resource_path('assets/app_icon.png')));app.setStyleSheet(STYLE);win=Main();win.show();sys.exit(app.exec())
