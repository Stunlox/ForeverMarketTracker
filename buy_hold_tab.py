from PySide6.QtWidgets import QHBoxLayout,QLabel,QComboBox,QDoubleSpinBox,QPushButton
from core import copper,QUALITY_NAMES
from investment_tab import BaseInvestmentTab
from buy_hold import opportunities
from trade_ledger_tab import set_amount
import time

class BuyHoldTab(BaseInvestmentTab):
    def __init__(self,db,journal,open_journal):
        super().__init__(db);self.journal=journal;self.open_journal=open_journal
        bar=QHBoxLayout();self.layout.addLayout(bar)
        bar.addWidget(QLabel('Rarity'));self.rarity=QComboBox();self.rarity.addItem('All rarities',None)
        for k,v in QUALITY_NAMES.items():self.rarity.addItem(v,k)
        bar.addWidget(self.rarity);bar.addWidget(QLabel('Max hold'))
        self.hold=QComboBox()
        for h in (24,48,72,168):self.hold.addItem(f'{h} hours',h)
        self.hold.setCurrentIndex(2);bar.addWidget(self.hold)
        bar.addWidget(QLabel('Minimum net ROI %'));self.roi=QDoubleSpinBox();self.roi.setRange(0,1000);self.roi.setValue(5);bar.addWidget(self.roi)
        self.table=self.create_table(['Item','Rarity','AH qty','Buy/unit','Target/unit','Qty','Spend','Net profit','ROI','Sell window (UK)','Confidence'])
        button=QPushButton('Prepare selected purchase in Trade Journal');button.clicked.connect(self.prepare);self.layout.addWidget(button)
        note=QLabel('Uses recurring weekday windows when available, otherwise daily six-hour patterns across at least two dates. Low confidence = limited daily evidence. Uses competitive asking prices, not completed sales. Max 35% of budget per item, 10% of latest supply. Verify live prices; deposits excluded.');note.setWordWrap(True);self.layout.addWidget(note)
        self.rarity.currentIndexChanged.connect(self.refresh);self.hold.currentIndexChanged.connect(self.refresh);self.roi.valueChanged.connect(self.refresh)
        self.refresh()
    def refresh(self,*_):
        if not hasattr(self,'table'):return
        self.records,stamp=opportunities(self.db,self.budget_copper(),**self.options(),quality=self.rarity.currentData(),hours=self.hold.currentData(),min_roi=self.roi.value())
        self.render(self.table,[(r,[r['name'],QUALITY_NAMES.get(r['quality'],'Unknown'),r['supply'],copper(r['buy']),copper(r['resale']),r['quantity'],copper(r['cost']),copper(r['profit']),f"{r['margin']:.1f}%",r['window'],f"{r['confidence']} ({r['dates']} dates)"]) for r in self.records])
        age=(time.time()-stamp)/60 if stamp else None
        if age is None or age>120:self.summary.setText('No fresh AH snapshot — collect data before buying.');return
        self.summary.setText(f'{len(self.records)} opportunities | Snapshot {max(0,age):.0f} min old | Spend {copper(sum(r["cost"] for r in self.records))} | Estimated profit {copper(sum(r["profit"] for r in self.records))}. If empty: try a longer hold/history, lower ROI or quantity threshold; at least two dates in a selling window are required.')
    def prepare(self):
        row=self.table.currentRow()
        if row<0 or row>=len(self.records):return
        r=self.records[row];self.journal.clear();self.journal.item.setText(r['name']);self.journal.quantity.setValue(r['quantity']);set_amount(self.journal.buy_spins,r['buy']);self.journal.note.setText('Buy Now & Hold estimate — verify actual purchase before saving.');self.open_journal()
