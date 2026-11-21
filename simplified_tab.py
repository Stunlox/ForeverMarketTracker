"""Top 40 recurring trade-goods timing patterns, using recorded hourly snapshots."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
    QSpinBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView)
from simplified_market import top_deals
from core import copper

class SimplifiedTimingTab(QWidget):
    def __init__(self,db,parent=None):
        super().__init__(parent);self.db=db
        layout=QVBoxLayout(self);controls=QHBoxLayout();layout.addLayout(controls)
        controls.addWidget(QLabel('History'))
        self.days=QComboBox();self.days.addItems(['30 days','60 days','90 days','180 days','365 days']);self.days.setCurrentText('90 days');controls.addWidget(self.days)
        controls.addWidget(QLabel('Min current supply'))
        self.supply=QSpinBox();self.supply.setRange(0,1000000);self.supply.setValue(100);self.supply.setSingleStep(100);controls.addWidget(self.supply)
        controls.addWidget(QLabel('AH cut %'))
        self.cut=QSpinBox();self.cut.setRange(0,30);self.cut.setValue(5);controls.addWidget(self.cut)
        reload=QPushButton('Find top 40 deals');reload.clicked.connect(self.refresh);controls.addWidget(reload)
        controls.addStretch()
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.table=QTableWidget(0,10);self.table.setHorizontalHeaderLabels([
            'Rank','Trade good','Best time to BUY (UK)','Best time to SELL (UK)',
            'Typical buy / unit','Typical sell / unit','Net margin %','Current supply','Buy / Sell samples','Confidence'])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(False)
        header=self.table.horizontalHeader();header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table,1)
        self.note=QLabel('Only Trade Goods. Uses median cheapest-10%-by-quantity asking prices per weekday/hour. '
            'Requires at least 14 distinct dates and 3 separate weeks for each compared time slot. '
            'Times are UK local (Europe/London). Margins subtract the AH cut but exclude deposits, unsold listings and slippage. '
            'Buy and sell windows are historical observations, not guarantees of sales or profit.')
        self.note.setWordWrap(True);layout.addWidget(self.note)
        self.days.currentIndexChanged.connect(self.refresh)
        self.supply.valueChanged.connect(self.refresh)
        self.cut.valueChanged.connect(self.refresh)
        self.refresh()

    def refresh(self,*_):
        days=int(self.days.currentText().split()[0])
        deals,checked=top_deals(self.db,days=days,min_supply=self.supply.value(),cut_pct=self.cut.value())
        self.table.setRowCount(len(deals))
        for i,d in enumerate(deals):
            values=[str(i+1),d['name'],d['buy_time'],d['sell_time'],copper(d['buy_price']),
                    copper(d['sell_price']),f"{d['margin_pct']:+.1f}%",f"{d['current_supply']:,}",
                    f"{d['buy_samples']} / {d['sell_samples']}",d['confidence']]
            for j,value in enumerate(values):
                item=QTableWidgetItem(value)
                item.setToolTip(f"Observed across {d['dates']} dates. Buy slot: {d['buy_weeks']} weeks; sell slot: {d['sell_weeks']} weeks. Estimated net margin excludes deposits and failed sales.")
                if j in (0,6,7):item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i,j,item)
        if deals:
            self.summary.setText(f'{len(deals)} ranked historical timing opportunities from {checked:,} currently high-supply trade goods. '
                'Sorted by estimated margin, adjusted for supply and repeat observations. No actual sale prices are available.')
        else:
            self.summary.setText(f'No statistically eligible opportunities yet among {checked:,} trade goods meeting the current supply filter. '
                'Keep collecting hourly snapshots. The cheapest-10% metric only exists for snapshots collected since v0.7; '
                'several weeks of repeated weekday/hour observations are needed before the top 40 can populate.')
