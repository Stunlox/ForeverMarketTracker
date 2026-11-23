"""Up to 300 ranked historical timing opportunities."""
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
    QSpinBox,QCheckBox,QDoubleSpinBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMenu)
from simplified_market import top_deals
from exclusions import exclude
from market_timing import categories
from core import copper,quality_for_items,QUALITY_COLORS,QUALITY_NAMES

class SimplifiedTimingTab(QWidget):
    exclusions_changed=Signal()
    def __init__(self,db,parent=None):
        super().__init__(parent);self.db=db
        layout=QVBoxLayout(self);controls=QHBoxLayout();layout.addLayout(controls)
        controls.addWidget(QLabel('Category'))
        self.category=QComboBox();self.category.addItem('Trade Goods');self.category.addItem('All categories')
        for category in categories(self.db):
            if category.casefold() not in ('trade goods','tradegoods'):self.category.addItem(category)
        controls.addWidget(self.category)
        controls.addWidget(QLabel('History'))
        self.days=QComboBox();self.days.addItems(['30 days','60 days','90 days','180 days','365 days']);self.days.setCurrentText('90 days');controls.addWidget(self.days)
        controls.addWidget(QLabel('Min current supply'))
        self.supply=QSpinBox();self.supply.setRange(0,1000000);self.supply.setValue(100);self.supply.setSingleStep(100);controls.addWidget(self.supply)
        controls.addWidget(QLabel('AH cut %'))
        self.cut=QSpinBox();self.cut.setRange(0,30);self.cut.setValue(5);controls.addWidget(self.cut)
        controls.addWidget(QLabel('Deals'))
        self.limit=QComboBox();self.limit.addItems(['25','50','100','200','300']);self.limit.setCurrentText('100');controls.addWidget(self.limit)
        controls.addWidget(QLabel('Min profit / unit (g)'))
        self.min_profit=QDoubleSpinBox();self.min_profit.setRange(0,100000);self.min_profit.setDecimals(1);controls.addWidget(self.min_profit)
        self.spikes=QCheckBox('Exclude temporary spikes');self.spikes.setChecked(True);controls.addWidget(self.spikes)
        reload=QPushButton('Find deals');reload.clicked.connect(self.refresh);controls.addWidget(reload)
        controls.addStretch()
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels([
            'Rank','Item','Best time to BUY (UK)','Best time to SELL (UK)',
            'Typical buy / unit','Typical sell / unit','Net margin %','Current supply','Buy / Sell samples','Confidence'])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.exclude_menu)
        header=self.table.horizontalHeader();header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table,1)
        self.note=QLabel('Category selectable. Uses median cheapest-10%-by-quantity asking prices per weekday/hour. '
            'Early signals can use 2 dates, but are marked LOW DATA and are provisional. '
            'Times are UK local (Europe/London). Margins subtract the AH cut but exclude deposits, unsold listings and slippage. '
            'Buy and sell windows are historical observations, not guarantees of sales or profit.')
        self.note.setWordWrap(True);layout.addWidget(self.note)
        self.category.currentIndexChanged.connect(self.refresh)
        self.days.currentIndexChanged.connect(self.refresh)
        self.supply.valueChanged.connect(self.refresh)
        self.cut.valueChanged.connect(self.refresh)
        self.limit.currentIndexChanged.connect(self.refresh)
        self.min_profit.valueChanged.connect(self.refresh)
        self.spikes.toggled.connect(self.refresh)
        self.refresh()

    def exclude_menu(self,pos):
        row=self.table.rowAt(pos.y())
        if row<0:return
        cell=self.table.item(row,1)
        if cell is None:return
        ident=cell.data(Qt.ItemDataRole.UserRole)
        if ident is None:return
        menu=QMenu(self.table);action=menu.addAction('Exclude this item from recommendations')
        vendor=menu.addAction('Exclude as vendor item (manual)')
        selected=menu.exec(self.table.viewport().mapToGlobal(pos))
        if selected in (action,vendor):
            exclude(self.db,ident,'Vendor (manual)' if selected==vendor else 'Manual');self.exclusions_changed.emit()
    def refresh(self,*_):
        days=int(self.days.currentText().split()[0])
        deals,checked=top_deals(self.db,days=days,min_supply=self.supply.value(),cut_pct=self.cut.value(),category=self.category.currentText(),limit=int(self.limit.currentText()),min_profit_gold=self.min_profit.value(),exclude_spikes=self.spikes.isChecked())
        self.table.setRowCount(len(deals))
        qualities=quality_for_items(self.db,[d['item_id'] for d in deals])
        for i,d in enumerate(deals):
            values=[str(i+1),d['name'],d['buy_time'],d['sell_time'],copper(d['buy_price']),
                    copper(d['sell_price']),f"{d['margin_pct']:+.1f}%",f"{d['current_supply']:,}",
                    f"{d['buy_samples']} / {d['sell_samples']}",d['confidence']]
            for j,value in enumerate(values):
                item=QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole,d["item_id"])
                item.setToolTip(f"{d['snapshots']} snapshots across {d['dates']} dates. Buy slot: {d['buy_weeks']} weeks; sell slot: {d['sell_weeks']} weeks. Estimated net margin excludes deposits and failed sales.")
                if j==1 and qualities.get(d['item_id']) in QUALITY_COLORS:
                    quality=qualities[d['item_id']];item.setForeground(QColor(QUALITY_COLORS[quality]))
                    item.setToolTip(f'{QUALITY_NAMES[quality]} quality. '+item.toolTip())
                if j==9 and d['confidence']=='Low data':item.setForeground(QColor('#F4BE62'))
                if j in (0,6,7):item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i,j,item)
        if deals:
            self.summary.setText(f'{len(deals)} ranked historical timing opportunities from {checked:,} items matching the selected category and supply filter. '
                'Provisional asking-price signals, ranked by estimated margin, supply and confidence. Low-data signals are speculative; no actual sale prices are available.')
        else:
            self.summary.setText(f'No statistically eligible opportunities yet among {checked:,} items meeting the current supply filter. '
                'Keep collecting hourly snapshots. At least two distinct dates with positive cheap-10% prices are needed for provisional signals.')
