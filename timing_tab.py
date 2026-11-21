"""Standalone tab integrated into the existing PySide6 market tracker."""
from zoneinfo import ZoneInfo
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
    QSpinBox,QTableWidget,QTableWidgetItem,QHeaderView,QPushButton,QSplitter)
from market_timing import DAYS, trade_goods, observations, analyse, summarize
from core import copper

class MarketTimingTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db=db
        layout=QVBoxLayout(self)
        controls=QHBoxLayout();layout.addLayout(controls)
        controls.addWidget(QLabel('Trade good'))
        self.item=QComboBox();self.item.setMinimumWidth(320);self.item.currentIndexChanged.connect(self.refresh);controls.addWidget(self.item,1)
        controls.addWidget(QLabel('Price metric'))
        self.metric=QComboBox();self.metric.addItem('Cheapest 10% average','cheap10');self.metric.addItem('Cheapest 20% average','cheap20');self.metric.addItem('Lowest buyout','lowest');self.metric.addItem('All-units median','median');self.metric.currentIndexChanged.connect(self.refresh);controls.addWidget(self.metric)
        controls.addWidget(QLabel('History'))
        self.days=QComboBox();self.days.addItems(['30 days','60 days','90 days','180 days','365 days']);self.days.setCurrentText('90 days');self.days.currentIndexChanged.connect(self.refresh);controls.addWidget(self.days)
        controls.addWidget(QLabel('Min current supply'))
        self.supply=QSpinBox();self.supply.setRange(0,1000000);self.supply.setValue(100);self.supply.setSingleStep(100);self.supply.valueChanged.connect(self.load_items);controls.addWidget(self.supply)
        reload=QPushButton('Refresh analysis');reload.clicked.connect(self.load_items);controls.addWidget(reload)
        self.summary=QLabel('Collect several weeks of hourly snapshots to discover patterns.')
        self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.note=QLabel('UK local time (Europe/London). Each cell: median of selected hourly price metric / median supply / snapshot count.\n'
            'Grey cells have fewer than 3 observations. Asking prices are not confirmed sale prices.')
        self.note.setWordWrap(True);layout.addWidget(self.note)
        self.table=QTableWidget(7,24);self.table.setVerticalHeaderLabels(DAYS)
        self.table.setHorizontalHeaderLabels([f'{hour:02d}:00' for hour in range(24)])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(63)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellClicked.connect(self.selected_cell)
        layout.addWidget(self.table,1)
        self.detail=QLabel('Select a heatmap cell for its statistics.');layout.addWidget(self.detail)
        self.cells={}
        self.load_items()

    def load_items(self,*_):
        previous=self.item.currentData()
        self.item.blockSignals(True);self.item.clear()
        for item_id,name,sub,qty,price in trade_goods(self.db,self.supply.value()):
            self.item.addItem(f'{name}  ({qty:,} available)',item_id)
        if previous is not None:
            idx=self.item.findData(previous)
            if idx>=0:self.item.setCurrentIndex(idx)
        self.item.blockSignals(False)
        self.refresh()

    def refresh(self,*_):
        item_id=self.item.currentData()
        self.table.clearContents();self.cells={}
        if item_id is None:
            self.summary.setText('No trade goods meet the supply threshold in the latest snapshot. Reduce the minimum supply or fetch a new snapshot.')
            return
        days=int(self.days.currentText().split()[0])
        rows=observations(self.db,item_id,days)
        self.cells=analyse(rows,ZoneInfo('Europe/London'),metric=self.metric.currentData())
        valid=[c['median_price'] for c in self.cells.values() if c['eligible']]
        lo=min(valid) if valid else 0;hi=max(valid) if valid else 0
        for weekday in range(7):
            for hour in range(24):
                c=self.cells.get((weekday,hour))
                if not c:continue
                value=f"{copper(c['median_price'])}\nQty {c['median_quantity']:,} · n={c['count']}"
                cell=QTableWidgetItem(value);cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if not c['eligible']:
                    cell.setBackground(QColor('#303744'));cell.setForeground(QColor('#9ca8b5'))
                elif hi>lo:
                    ratio=(c['median_price']-lo)/(hi-lo)
                    # Lower price = teal, higher price = reddish; muted for legibility.
                    cell.setBackground(QColor(int(27+65*ratio),int(92-45*ratio),int(83-36*ratio)))
                else:cell.setBackground(QColor('#235b55'))
                self.table.setItem(weekday,hour,cell)
        repeats=len(rows);days_seen=len({__import__('datetime').datetime.fromtimestamp(r[0],ZoneInfo('Europe/London')).date() for r in rows})
        result=summarize(self.cells)
        metric_label=self.metric.currentText()
        if result and days_seen>=14:
            buy_day,buy_hour=result['buy'];sell_day,sell_hour=result['sell']
            cut=0.05
            potential=(result['sell_price']*(1-cut)-result['buy_price'])/result['buy_price']*100
            self.summary.setText(f"{self.item.currentText().split('  (')[0]}  |  {repeats} snapshots across {days_seen} dates. "
                f"Metric: {metric_label}. Observed cheapest: {DAYS[buy_day]} {buy_hour:02d}:00 ({copper(result['buy_price'])}, n={result['buy_samples']}). "
                f"Highest: {DAYS[sell_day]} {sell_hour:02d}:00 ({copper(result['sell_price'])}, n={result['sell_samples']}). "
                f"Illustrative spread after 5% AH cut: {potential:+.1f}% before deposits/failed sales. Not a trading recommendation.")
        else:
            self.summary.setText(f'{repeats} snapshots across {days_seen} dates. {len([c for c in self.cells.values() if c["eligible"]])} eligible time slots for {metric_label}. Insufficient repeat coverage for a timing signal '
                '(requires at least 14 distinct dates and 3 observations in each compared hour). Keep hourly collection running.')
        self.detail.setText('Select a heatmap cell for its statistics.')

    def selected_cell(self,day,hour):
        c=self.cells.get((day,hour))
        if not c:self.detail.setText(f'{DAYS[day]} {hour:02d}:00 — no snapshots yet.');return
        self.detail.setText(f"{DAYS[day]} {hour:02d}:00 UK time | {c['count']} observations | "
            f"Median {self.metric.currentText()} {copper(c['median_price'])} per unit | "
            f"Median lowest buyout {copper(c['median_lowest'])} per unit | "
            f"Median supply {c['median_quantity']:,} | "
            + ('Repeat coverage sufficient for this cell' if c['eligible'] else 'Not enough repeat observations'))
