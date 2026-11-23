"""Crafting profits with WoW rarity colours and transparent vendor/AH price comparison."""
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QLabel,QSpinBox,QCheckBox,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPushButton,QDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from core import copper,QUALITY_COLORS,QUALITY_NAMES
from professions_data import CRAFTING,profitability
from vendor_catalogue import vendor_price_coverage


def rarity_item(value,quality=None):
    item=QTableWidgetItem(str(value))
    if quality in QUALITY_COLORS:
        item.setForeground(QColor(QUALITY_COLORS[quality]))
        item.setToolTip(f'{QUALITY_NAMES[quality]} quality')
    return item


class ProfessionsTab(QWidget):
    def __init__(self,db,settings):
        super().__init__();self.db=db;self.settings=settings;self.rows=[]
        lay=QVBoxLayout(self);lay.addWidget(QLabel('CRAFTING PROFIT ANALYSER — AH vs explicit NPC vendor purchase costs'))
        bar=QHBoxLayout();lay.addLayout(bar)
        self.prof=QComboBox();self.prof.addItems([s.replace('-',' ').title() for s in CRAFTING]);self.prof.currentIndexChanged.connect(self.refresh);bar.addWidget(self.prof)
        bar.addWidget(QLabel('Minimum profit (silver)'))
        self.minimum=QSpinBox();self.minimum.setRange(0,10000000);self.minimum.valueChanged.connect(self.refresh);bar.addWidget(self.minimum)
        self.only=QCheckBox('Profitable only');self.only.setChecked(True);self.only.toggled.connect(self.refresh);bar.addWidget(self.only)
        self.refresh_button=QPushButton('Refresh');self.refresh_button.clicked.connect(self.refresh);bar.addWidget(self.refresh_button)
        self.status=QLabel('Import crafting recipes in API & Settings first.');lay.addWidget(self.status)
        self.coverage=QLabel('Vendor price coverage: —');lay.addWidget(self.coverage)
        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(['Craft','Skill','Reagent cost','AH sell/unit','Net profit/craft','ROI %','Output AH qty'])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True);lay.addWidget(self.table)
        self.table.itemDoubleClicked.connect(self.details)
        lay.addWidget(QLabel('Double-click a craft to compare reagent AH prices, vendor purchase prices, stock type and selected source. '
            'Unknown vendor prices are never assumed free. Limited-stock vendor prices may not support bulk crafting. '
            'AH asking prices are not confirmed sales.'))
        self.refresh()

    def refresh(self,*_):
        profession=CRAFTING[self.prof.currentIndex()] if self.prof.currentIndex()>=0 else CRAFTING[0]
        self.rows=profitability(self.db,profession,int(self.settings.get('ah_cut_percent',5)))
        show=[r for r in self.rows if (r['profit'] is None and not self.only.isChecked()) or
            (r['profit'] is not None and r['profit']>=self.minimum.value()*100 and (not self.only.isChecked() or r['profit']>0))]
        show.sort(key=lambda r:r['profit'] if r['profit'] is not None else -10**20,reverse=True)
        self.table.setSortingEnabled(False);self.table.setRowCount(len(show))
        for i,r in enumerate(show):
            profit=r['profit']
            vals=[r['name'],str(r['skill'] or '—'),copper(r['cost']) if r['cost'] is not None else 'Missing prices',
                copper(r['price']) if r['price'] is not None else '—',
                ('+' if profit>0 else '')+copper(profit) if profit is not None and profit>=0 else ('-'+copper(-profit) if profit is not None else 'Unknown'),
                f"{r['roi']:.1f}" if r['roi'] is not None else '—',str(r['supply'])]
            for j,v in enumerate(vals):
                item=rarity_item(v,r.get('quality')) if j==0 else QTableWidgetItem(v)
                item.setData(Qt.ItemDataRole.UserRole,r['recipe_id']);self.table.setItem(i,j,item)
        self.table.setSortingEnabled(True)
        coverage=vendor_price_coverage(self.db)
        self.coverage.setText(f"Vendor purchase prices: {coverage['priced']:,} of {coverage['total']:,} inventory rows | "
            f"{coverage['items']:,} unique items with prices | {coverage['missing']:,} missing")
        self.status.setText(f'{len(show):,} displayed / {len(self.rows):,} imported {profession} recipes | '
            'AH/vendor quotes used when available; unknown prices are not zero')

    def details(self,item):
        rid=item.data(Qt.ItemDataRole.UserRole)
        r=next((r for r in self.rows if r['recipe_id']==rid),None)
        if not r:return
        dialog=QDialog(self);dialog.setWindowTitle('Craft reagents — '+r['name']);dialog.resize(970,420)
        layout=QVBoxLayout(dialog)
        heading=QLabel(r['name']);heading.setStyleSheet('font-size:16px;font-weight:bold;')
        if r.get('quality') in QUALITY_COLORS:heading.setStyleSheet(heading.styleSheet()+f"color:{QUALITY_COLORS[r['quality']]};")
        layout.addWidget(heading)
        table=QTableWidget(len(r['materials']),7)
        table.setHorizontalHeaderLabels(['Reagent','Needed','AH / unit','NPC / unit','Best / unit','Chosen source','Vendor stock'])
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row,part in enumerate(r['materials']):
            vals=[part.name,str(part.count),copper(part.ah) if part.ah is not None else 'Unknown',
                copper(part.vendor) if part.vendor is not None else 'Unknown',copper(part.unit),
                part.source,part.stock if part.vendor is not None else '—']
            for col,val in enumerate(vals):table.setItem(row,col,rarity_item(val,part.quality) if col==0 else QTableWidgetItem(val))
        layout.addWidget(table)
        if r['missing']:layout.addWidget(QLabel('Missing price data: '+', '.join(r['missing'])))
        layout.addWidget(QLabel('NPC costs only count when an explicit purchase price exists. Limited stock may not be available in quantity.'))
        close=QPushButton('Close');close.clicked.connect(dialog.accept);layout.addWidget(close)
        dialog.exec()
