"""Crafting profitability at a glance; never substitutes unknown vendor prices."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QLabel,QSpinBox,QCheckBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPushButton,QMessageBox
from PySide6.QtCore import Qt
from core import copper
from professions_data import CRAFTING,profitability

class ProfessionsTab(QWidget):
    def __init__(self,db,settings):
        super().__init__();self.db=db;self.settings=settings;self.rows=[]
        lay=QVBoxLayout(self);lay.addWidget(QLabel('CRAFTING PROFIT ANALYSER — AH reagent costs vs AH output value'))
        bar=QHBoxLayout();lay.addLayout(bar)
        self.prof=QComboBox();self.prof.addItems([s.replace('-',' ').title() for s in CRAFTING]);self.prof.currentIndexChanged.connect(self.refresh);bar.addWidget(self.prof)
        bar.addWidget(QLabel('Minimum profit (silver)'))
        self.minimum=QSpinBox();self.minimum.setRange(0,10000000);self.minimum.valueChanged.connect(self.refresh);bar.addWidget(self.minimum)
        self.only=QCheckBox('Profitable only');self.only.setChecked(True);self.only.toggled.connect(self.refresh);bar.addWidget(self.only)
        self.refresh_button=QPushButton('Refresh');self.refresh_button.clicked.connect(self.refresh);bar.addWidget(self.refresh_button)
        self.status=QLabel('Import crafting recipes in API & Settings first.');lay.addWidget(self.status)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['Craft','Skill','Reagent cost','AH sell/unit','Net profit/craft','ROI %','Output AH qty']);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setSortingEnabled(True);lay.addWidget(self.table)
        self.table.itemDoubleClicked.connect(self.details)
        lay.addWidget(QLabel('Double-click a recipe for reagent quantities. Estimates use current AH median asking prices and the configured AH cut; actual sales are unverified. Vendor prices are used when the ForeverDB vendor import explicitly supplies purchase prices; otherwise unknown costs remain missing.'))
        self.refresh()
    def refresh(self,*_):
        profession=CRAFTING[self.prof.currentIndex()] if self.prof.currentIndex()>=0 else CRAFTING[0]
        self.rows=profitability(self.db,profession,int(self.settings.get('ah_cut_percent',5)))
        show=[r for r in self.rows if (r['profit'] is None and not self.only.isChecked()) or (r['profit'] is not None and r['profit']>=self.minimum.value()*100 and (not self.only.isChecked() or r['profit']>0))]
        show.sort(key=lambda r:r['profit'] if r['profit'] is not None else -10**20,reverse=True)
        self.table.setSortingEnabled(False);self.table.setRowCount(len(show))
        for i,r in enumerate(show):
            vals=[r['name'],str(r['skill'] or '—'),copper(r['cost']) if r['cost'] is not None else 'Missing prices',copper(r['price']) if r['price'] is not None else '—',('+' if r['profit']>0 else '')+copper(r['profit']) if r['profit'] is not None and r['profit']>=0 else ('-'+copper(-r['profit']) if r['profit'] is not None else 'Unknown'),f"{r['roi']:.1f}" if r['roi'] is not None else '—',str(r['supply'])]
            for j,v in enumerate(vals):
                item=QTableWidgetItem(v);item.setData(Qt.ItemDataRole.UserRole,r['recipe_id']);self.table.setItem(i,j,item)
        self.table.setSortingEnabled(True)
        self.status.setText(f'{len(show):,} displayed / {len(self.rows):,} imported {profession} recipes | AH prices only; missing prices are never treated as zero')
    def details(self,item):
        rid=item.data(Qt.ItemDataRole.UserRole)
        r=next((r for r in self.rows if r['recipe_id']==rid),None)
        if not r:return
        lines=[f"{name}: {qty} × {copper(price)} ({source})" for name,qty,price,source in r['materials']]
        if r['missing']:lines+=['Missing AH quotes: '+', '.join(r['missing'])]
        QMessageBox.information(self,'Craft reagents — '+r['name'],'\n'.join(lines) or 'No priced reagents')
