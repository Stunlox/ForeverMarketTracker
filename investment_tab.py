"""Two budget planner screens using local snapshot aggregates."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,
    QDoubleSpinBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QLineEdit)
from core import copper,QUALITY_COLORS
from investment import candidates,estimate,allocate

class BaseInvestmentTab(QWidget):
    def __init__(self,db):
        super().__init__();self.db=db
        self.layout=QVBoxLayout(self);row=QHBoxLayout();self.layout.addLayout(row)
        row.addWidget(QLabel('Budget (gold)'))
        self.budget=QDoubleSpinBox();self.budget.setRange(0,100000000);self.budget.setDecimals(2);self.budget.setValue(500);row.addWidget(self.budget)
        row.addWidget(QLabel('Category'))
        self.category=QComboBox();self.category.addItem('Trade Goods');self.category.addItem('All categories')
        for (cat,) in db.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND category<>'' ORDER BY category"):
            if cat.lower() not in ('trade goods','tradegoods'):self.category.addItem(cat)
        row.addWidget(self.category)
        row.addWidget(QLabel('History'))
        self.days=QComboBox();self.days.addItems(['7','14','30','90']);self.days.setCurrentText('30');row.addWidget(self.days)
        row.addWidget(QLabel('AH cut %'))
        self.cut=QDoubleSpinBox();self.cut.setRange(0,30);self.cut.setValue(5);row.addWidget(self.cut)
        refresh=QPushButton('Recalculate');refresh.clicked.connect(self.refresh);row.addWidget(refresh)
        self.budget.valueChanged.connect(self.refresh)
        self.category.currentIndexChanged.connect(self.refresh)
        self.days.currentIndexChanged.connect(self.refresh)
        self.cut.valueChanged.connect(self.refresh)
        self.summary=QLabel();self.summary.setWordWrap(True);self.layout.addWidget(self.summary)
    def options(self):return {'days':int(self.days.currentText()),'category':self.category.currentText(),'cut_pct':self.cut.value()}
    def budget_copper(self):return int(round(self.budget.value()*10000))
    def create_table(self,headings):
        table=QTableWidget(0,len(headings));table.setHorizontalHeaderLabels(headings)
        table.setAlternatingRowColors(True);table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(table,1)
        return table
    def render(self,table,records):
        table.setRowCount(len(records))
        for row,(data,values) in enumerate(records):
            for col,value in enumerate(values):
                cell=QTableWidgetItem(str(value))
                if col==0 and data.get('quality') in QUALITY_COLORS:cell.setForeground(QColor(QUALITY_COLORS[data['quality']]))
                cell.setToolTip(f"{data.get('snapshots',0)} observations across {data.get('dates',0)} dates. Estimates use aggregated asking prices, not individual executable auction tiers.")
                table.setItem(row,col,cell)

class SuggestedBuysTab(BaseInvestmentTab):
    def __init__(self,db):
        super().__init__(db)
        self.table=self.create_table(['Item','Qty','Est. spend','Est. net proceeds','Est. profit','Confidence'])
        self.layout.addWidget(QLabel('Budget is shared across suggestions. Max 35% per item; purchase quantities capped at 10% of observed supply. Verify live listings.'))
        self.refresh()
    def refresh(self,*_):
        options=self.options();items=candidates(self.db,**options)
        proposed=allocate(self.budget_copper(),items,options['cut_pct'])
        self.render(self.table,[(d,[d['name'],f"{d['quantity']:,}",copper(d['cost']),copper(d['net_proceeds']),
            ('+' if d['profit']>=0 else '-')+copper(abs(d['profit'])),d['confidence']]) for d in proposed])
        spend=sum(d['cost'] for d in proposed);profit=sum(d['profit'] for d in proposed)
        self.summary.setText(f'{len(proposed)} suggested purchases | Estimated spend {copper(spend)} / {copper(self.budget_copper())} budget | '
            f'Estimated net profit {"+" if profit>=0 else "-"}{copper(abs(profit))} | Unspent {copper(self.budget_copper()-spend)}. '
            'Assumes all suggested purchases and resales fill at estimated prices; actual execution may differ.')

class TargetItemTab(BaseInvestmentTab):
    def __init__(self,db):
        super().__init__(db)
        search=QHBoxLayout();self.layout.addLayout(search);search.addWidget(QLabel('Search item'))
        self.search=QLineEdit();self.search.setPlaceholderText('Search any material or item...');search.addWidget(self.search)
        self.search.textChanged.connect(self.refresh)
        self.table=self.create_table(['Item','Available units','Affordable qty','Estimated spend','Est. profit','Data confidence'])
        self.layout.addWidget(QLabel('Affordable quantity uses cheapest-10%-of-units price as an estimate and caps at approximately 10% of observed supply. It is NOT an exact AH buy list.'))
        self.refresh()
    def refresh(self,*_):
        options=self.options();query=self.search.text().strip().casefold()
        matches=candidates(self.db,**options,include_all=True,search=query,limit=300)
        records=[]
        for d in matches:
            e=estimate(self.budget_copper(),d['buy'],d['resale'],d['affordable_supply'],options['cut_pct'])
            records.append((d,[d['name'],f"{d['supply']:,}",f"{e['quantity']:,}",copper(e['cost']),
                ('+' if e['profit']>=0 else '-')+copper(abs(e['profit'])),d['confidence']]))
        self.render(self.table,records)
        self.summary.setText(f'{len(matches)} estimated profitable item matches (maximum 300 displayed). '
            'Items with insufficient history use a provisional reference price; negative estimates are shown, not hidden. '
            'Each row independently uses your full budget.')
