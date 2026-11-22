"""Standalone tab integrated into the existing PySide6 market tracker."""
from zoneinfo import ZoneInfo
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
    QSpinBox,QTableWidget,QTableWidgetItem,QHeaderView,QPushButton,QSplitter)
from market_timing import DAYS, market_items, categories, observations, analyse, summarize, price_ratio
from core import copper,quality_for_items,QUALITY_COLORS,QUALITY_NAMES

class MarketTimingTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db=db
        layout=QVBoxLayout(self)
        controls=QHBoxLayout();layout.addLayout(controls)
        controls.addWidget(QLabel('Category'))
        self.category=QComboBox();self.category.addItem('Trade Goods');self.category.addItem('All categories')
        for category in categories(self.db):
            if category.casefold() not in ('trade goods','tradegoods'):self.category.addItem(category)
        self.category.currentIndexChanged.connect(self.load_items);controls.addWidget(self.category)
        controls.addWidget(QLabel('Item'))
        self.item=QComboBox();self.item.setMinimumWidth(320);self.item.currentIndexChanged.connect(self.refresh);controls.addWidget(self.item,1)
        controls.addWidget(QLabel('Price metric'))
        self.metric=QComboBox();self.metric.addItem('Cheapest 10% average','cheap10');self.metric.addItem('Cheapest 20% average','cheap20');self.metric.addItem('Lowest buyout','lowest');self.metric.addItem('All-units median','median');self.metric.currentIndexChanged.connect(self.refresh);controls.addWidget(self.metric)
        controls.addWidget(QLabel('History'))
        self.days=QComboBox();self.days.addItems(['30 days','60 days','90 days','180 days','365 days']);self.days.setCurrentText('90 days');self.days.currentIndexChanged.connect(self.refresh);controls.addWidget(self.days)
        controls.addWidget(QLabel('Min current supply'))
        self.supply=QSpinBox();self.supply.setRange(0,1000000);self.supply.setValue(100);self.supply.setSingleStep(100);self.supply.valueChanged.connect(self.load_items);controls.addWidget(self.supply)
        reload=QPushButton('Refresh analysis');reload.clicked.connect(self.load_items);controls.addWidget(reload)
        self.summary=QLabel('Early signals appear with limited data and are provisional.')
        self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.note=QLabel('UK local time (Europe/London). Each cell: median of selected hourly price metric / median supply / snapshot count.\n'
            'Green = lowest observed item price; red = highest; grey = missing or identical prices. Even a single observation per slot is coloured when prices vary. Asking prices are not confirmed sales.')
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
        items=market_items(self.db,self.category.currentText(),self.supply.value())
        qualities=quality_for_items(self.db,[r[0] for r in items])
        for item_id,name,sub,qty,price in items:
            self.item.addItem(f'{name}  ({qty:,} available)',item_id)
            quality=qualities.get(item_id)
            if quality in QUALITY_COLORS:
                index=self.item.count()-1
                self.item.setItemData(index,QColor(QUALITY_COLORS[quality]),Qt.ItemDataRole.ForegroundRole)
                self.item.setItemData(index,f'{QUALITY_NAMES[quality]} quality',Qt.ItemDataRole.ToolTipRole)
        if previous is not None:
            idx=self.item.findData(previous)
            if idx>=0:self.item.setCurrentIndex(idx)
        self.item.blockSignals(False)
        self.refresh()

    def refresh(self,*_):
        item_id=self.item.currentData()
        self.table.clearContents();self.cells={}
        if item_id is None:
            self.summary.setText('No items in this category meet the supply threshold in the latest snapshot. Reduce the threshold or change category.')
            return
        days=int(self.days.currentText().split()[0])
        rows=observations(self.db,item_id,days)
        self.cells=analyse(rows,ZoneInfo('Europe/London'),metric=self.metric.currentData(),min_samples=1)
        valid=[c['median_price'] for c in self.cells.values()]
        lo=min(valid) if valid else 0;hi=max(valid) if valid else 0
        for weekday in range(7):
            for hour in range(24):
                c=self.cells.get((weekday,hour))
                if not c:continue
                value=f"{copper(c['median_price'])}\nQty {c['median_quantity']:,} · n={c['count']}"
                cell=QTableWidgetItem(value);cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                ratio=price_ratio(c['median_price'],lo,hi)
                if ratio is None:
                    cell.setBackground(QColor('#303744'))
                else:
                    # Green -> yellow -> red; item rarity affects names only.
                    hue=int((1-ratio)*120)
                    cell.setBackground(QColor.fromHsv(hue,185,155))
                    cell.setForeground(QColor('#ffffff'))
                self.table.setItem(weekday,hour,cell)
        repeats=len(rows);days_seen=len({__import__('datetime').datetime.fromtimestamp(r[0],ZoneInfo('Europe/London')).date() for r in rows})
        result=summarize(self.cells,min_samples=1)
        metric_label=self.metric.currentText()
        if result and days_seen>=2:
            buy_day,buy_hour=result['buy'];sell_day,sell_hour=result['sell']
            cut=0.05
            potential=(result['sell_price']*(1-cut)-result['buy_price'])/result['buy_price']*100
            self.summary.setText(f"{self.item.currentText().split('  (')[0]}  |  {repeats} snapshots across {days_seen} dates. "
                f"Metric: {metric_label}. Observed cheapest: {DAYS[buy_day]} {buy_hour:02d}:00 ({copper(result['buy_price'])}, n={result['buy_samples']}). "
                f"Highest: {DAYS[sell_day]} {sell_hour:02d}:00 ({copper(result['sell_price'])}, n={result['sell_samples']}). "
                f"Illustrative spread after 5% AH cut: {potential:+.1f}% before deposits/failed sales. "
                f"{'LOW DATA — provisional only.' if days_seen<7 else 'Observed pattern, not a guaranteed trade.'}")
        else:
            self.summary.setText(f'{repeats} snapshots across {days_seen} dates. '
                f'{len(self.cells)} observed time slots for {metric_label}. '
                'At least two dates and two different observed prices are needed for a provisional buy/sell signal. '
                'Heatmap colouring does not require repeat observations.')
        self.detail.setText('Select a heatmap cell for its statistics.')

    def selected_cell(self,day,hour):
        c=self.cells.get((day,hour))
        if not c:self.detail.setText(f'{DAYS[day]} {hour:02d}:00 — no snapshots yet.');return
        self.detail.setText(f"{DAYS[day]} {hour:02d}:00 UK time | {c['count']} observations | "
            f"Median {self.metric.currentText()} {copper(c['median_price'])} per unit | "
            f"Median lowest buyout {copper(c['median_lowest'])} per unit | "
            f"Median supply {c['median_quantity']:,} | "
            + ('Provisional observation; n='+str(c['count'])))
