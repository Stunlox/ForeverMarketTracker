"""Separate short-horizon weekday evening buy / next-day afternoon sell view."""
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QSpinBox,QDoubleSpinBox,QCheckBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QMenu
from core import copper,QUALITY_COLORS
from weekday_strategy import weekday_candidates
from exclusions import exclude

class WeekdayBuysTab(QWidget):
    exclusions_changed=Signal()
    def __init__(self,db):
        super().__init__();self.db=db
        layout=QVBoxLayout(self);bar=QHBoxLayout();layout.addLayout(bar)
        bar.addWidget(QLabel('Category'))
        self.category=QComboBox();self.category.addItems(['Trade Goods','All categories'])
        for (cat,) in db.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND category<>'' ORDER BY category"):
            if cat.casefold() not in ('trade goods','tradegoods'):self.category.addItem(cat)
        bar.addWidget(self.category)
        bar.addWidget(QLabel('History'))
        self.days=QComboBox();self.days.addItems(['14','30','60','90']);self.days.setCurrentText('30');bar.addWidget(self.days)
        bar.addWidget(QLabel('Min AH qty'))
        self.minimum=QSpinBox();self.minimum.setRange(0,10000000);self.minimum.setValue(100);bar.addWidget(self.minimum)
        self.mode=QComboBox();self.mode.addItems(['Latest snapshot','Historical average']);bar.addWidget(self.mode)
        bar.addWidget(QLabel('Min paired days'))
        self.pairs=QSpinBox();self.pairs.setRange(2,100);self.pairs.setValue(3);bar.addWidget(self.pairs)
        bar.addWidget(QLabel('AH cut %'))
        self.cut=QDoubleSpinBox();self.cut.setRange(0,30);self.cut.setValue(5);bar.addWidget(self.cut)
        self.unlimited=QCheckBox('Include unlimited vendor items');bar.addWidget(self.unlimited)
        self.limited=QCheckBox('Include limited-stock vendor items');bar.addWidget(self.limited)
        refresh=QPushButton('Find overnight buys');refresh.clicked.connect(self.refresh);bar.addWidget(refresh)
        self.summary=QLabel();self.summary.setWordWrap(True);layout.addWidget(self.summary)
        self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['Item','AH qty','Latest weekday buy','Evening buy median','Next afternoon median','Est. net/unit','Paired days','Positive pairs','Confidence'])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.exclusion_menu)
        layout.addWidget(self.table,1)
        info=QLabel('Buy window Mon–Thu 18:00–23:59 UK; sell window Tue–Fri 12:00–17:59 UK. Only consecutive weekday pairs; NO weekend data. Asking-price patterns are not confirmed sales. Friday evening is excluded because Saturday is not a valid sell day.')
        info.setWordWrap(True);layout.addWidget(info)
        for widget,signal in [(self.category,'currentIndexChanged'),(self.days,'currentIndexChanged'),(self.minimum,'valueChanged'),(self.mode,'currentIndexChanged'),(self.pairs,'valueChanged'),(self.cut,'valueChanged'),(self.unlimited,'toggled'),(self.limited,'toggled')]:
            getattr(widget,signal).connect(self.refresh)
        self.refresh()
    def refresh(self,*_):
        rows=weekday_candidates(self.db,days=int(self.days.currentText()),category=self.category.currentText(),min_quantity=self.minimum.value(),quantity_mode=self.mode.currentText(),min_pairs=self.pairs.value(),cut_pct=self.cut.value(),include_unlimited=self.unlimited.isChecked(),include_limited=self.limited.isChecked())
        self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[r['name'],f"{r['filter_quantity']:,.0f}",copper(r['current_buy']),copper(r['buy_reference']),copper(r['sell_reference']),copper(r['estimated_net_unit']),str(r['pairs']),f"{r['wins']}/{r['pairs']} ({r['win_rate']:.0%})",r['confidence']]
            for j,value in enumerate(vals):
                cell=QTableWidgetItem(value);cell.setData(Qt.ItemDataRole.UserRole,r['item_id'])
                cell.setToolTip('Paired weekday asking-price observations; not verified sales or executable quotes.')
                if j==0 and r['quality'] in QUALITY_COLORS:cell.setForeground(QColor(QUALITY_COLORS[r['quality']]))
                self.table.setItem(i,j,cell)
        self.summary.setText(f'{len(rows)} weekday overnight opportunities. Historical matched evening-to-next-afternoon pairs only; minimum 60% positive pairs. Latest weekday buy estimate uses latest AH snapshot, which may not be an evening snapshot. Confirm price and stock before buying.')
    def exclusion_menu(self,pos):
        row=self.table.rowAt(pos.y())
        if row<0:return
        cell=self.table.item(row,0)
        if cell is None:return
        item_id=cell.data(Qt.ItemDataRole.UserRole)
        menu=QMenu(self.table);action=menu.addAction('Exclude this item from recommendations')
        if menu.exec(self.table.viewport().mapToGlobal(pos))==action:
            exclude(self.db,item_id);self.exclusions_changed.emit()
