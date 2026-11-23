"""Manual transaction journal: autocomplete, rarity, cost entry and sell guidance."""
import datetime as dt
from PySide6.QtCore import Qt,QStringListModel
from PySide6.QtGui import QColor,QStandardItem,QStandardItemModel
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QCompleter,
    QSpinBox,QCheckBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QGroupBox,QAbstractItemView)
from core import copper,QUALITY_COLORS
from trade_ledger import migrate,lots,save_lot,delete_lot,sell_advice,realised_profit

def amount(g,s,c):return int(g)*10000+int(s)*100+int(c)
def set_amount(spins,value):
    g,rest=divmod(max(0,int(value)),10000);s,c=divmod(rest,100)
    for spin,v in zip(spins,(g,s,c)):spin.setValue(v)

class TradeLedgerTab(QWidget):
    def __init__(self,db,settings):
        super().__init__();self.db=db;self.settings=settings;self.edit_id=None;self.item_id=None
        migrate(db)
        self.catalogue=db.execute('SELECT item_id,name,quality FROM items ORDER BY name COLLATE NOCASE').fetchall()
        self.by_name={name.casefold(): (ident,quality) for ident,name,quality in self.catalogue}
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('TRADE JOURNAL — record your purchases, track unsold inventory and review historical selling windows'))
        form=QGroupBox('Add / edit purchase');lay.addWidget(form);grid=QFormLayout(form)
        self.item=QLineEdit();self.item.setPlaceholderText('Start typing an item name...')
        model=QStandardItemModel(self)
        for ident,name,quality in self.catalogue:
            entry=QStandardItem(name);entry.setData(ident,Qt.ItemDataRole.UserRole)
            if quality in QUALITY_COLORS:entry.setForeground(QColor(QUALITY_COLORS[quality]))
            model.appendRow(entry)
        self.completer=QCompleter(model,self);self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains);self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.item.setCompleter(self.completer);self.completer.activated[str].connect(self._select)
        self.item.textChanged.connect(self._item_changed)
        grid.addRow('Item (autocomplete)',self.item)
        self.quantity=QSpinBox();self.quantity.setRange(1,100000000);self.quantity.setValue(1);grid.addRow('Quantity purchased',self.quantity)
        self.buy_spins=self._money(grid,'Purchase price per item')
        self.sold=QCheckBox('Sold — tick once the full recorded quantity has sold');grid.addRow('Sale status',self.sold)
        self.sell_spins=self._money(grid,'Actual sale price per item')
        self.sold.toggled.connect(self._sold_toggled);self._sold_toggled(False)
        self.note=QLineEdit();self.note.setPlaceholderText('Optional notes');grid.addRow('Notes',self.note)
        buttons=QHBoxLayout();lay.addLayout(buttons)
        self.save=QPushButton('Save trade');self.save.clicked.connect(self.save_trade);buttons.addWidget(self.save)
        reset=QPushButton('New trade / clear');reset.clicked.connect(self.clear);buttons.addWidget(reset)
        self.remove=QPushButton('Delete selected trade');self.remove.clicked.connect(self.delete_selected);buttons.addWidget(self.remove)
        self.summary=QLabel();lay.addWidget(self.summary)
        self.table=QTableWidget(0,9);self.table.setHorizontalHeaderLabels(['Item','Qty','Buy/unit','Status','Sold/unit','Realised P/L','Break-even sell/unit','Suggested sell window (UK)','Confidence'])
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7,QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.load_selected)
        lay.addWidget(self.table,1)
        self.advice=QLabel('Select an unsold trade to see the recommendation.');self.advice.setWordWrap(True);lay.addWidget(self.advice)
        lay.addWidget(QLabel('AH asking prices are not completed sales. Guidance needs repeated observations, excludes detected spikes, and assumes the configured AH cut. Auction deposits and failed sales are excluded.'))
        self.refresh()
    def _money(self,form,title):
        line=QHBoxLayout();spins=[]
        for label,maxval in [('Gold',100000000),('Silver',99),('Copper',99)]:
            sp=QSpinBox();sp.setRange(0,maxval);line.addWidget(QLabel(label));line.addWidget(sp);spins.append(sp)
        form.addRow(title,line);return spins
    def _item_changed(self,text):
        found=self.by_name.get(text.strip().casefold())
        self.item_id=found[0] if found else None
        quality=found[1] if found else None
        self.item.setStyleSheet('color:'+QUALITY_COLORS[quality]+';' if quality in QUALITY_COLORS else '')
    def _select(self,text):self._item_changed(text)
    def _sold_toggled(self,checked):
        for sp in self.sell_spins:sp.setEnabled(checked)
    def clear(self):
        self.edit_id=None;self.item.clear();self.quantity.setValue(1)
        set_amount(self.buy_spins,0);set_amount(self.sell_spins,0)
        self.sold.setChecked(False);self.note.clear();self.save.setText('Save trade')
    def save_trade(self):
        try:
            if self.item_id is None:raise ValueError('Select an exact item from the catalogue suggestions')
            buy=amount(*(s.value() for s in self.buy_spins))
            sell=amount(*(s.value() for s in self.sell_spins)) if self.sold.isChecked() else None
            trade_id=save_lot(self.db,self.item_id,self.quantity.value(),buy,self.sold.isChecked(),sell,self.note.text(),self.edit_id)
            self.clear();self.refresh();self._select_row(trade_id)
        except (ValueError,TypeError) as exc:QMessageBox.warning(self,'Trade not saved',str(exc))
    def _select_row(self,trade_id):
        for row in range(self.table.rowCount()):
            if self.table.item(row,0).data(Qt.ItemDataRole.UserRole)==trade_id:
                self.table.selectRow(row);break
    def load_selected(self):
        selection=self.table.selectedItems()
        if not selection:return
        trade_id=self.table.item(selection[0].row(),0).data(Qt.ItemDataRole.UserRole)
        record=next((r for r in self.records if r[0]==trade_id),None)
        if record is None:return
        ident,item_id,name,quality,qty,buy,bought_at,sold,sell,sold_at,note=record
        self.edit_id=ident;self.item.setText(name or f'Item #{item_id}')
        self.quantity.setValue(qty);set_amount(self.buy_spins,buy)
        self.sold.setChecked(bool(sold));set_amount(self.sell_spins,sell or 0)
        self.note.setText(note);self.save.setText('Update selected trade')
        if sold:
            profit=realised_profit(qty,buy,sell,float(self.settings.get('ah_cut_percent',5)))
            self.advice.setText(f'Sold trade. Estimated realised P/L after AH cut: {"+" if profit>=0 else "-"}{copper(abs(profit))}.')
        else:
            a=sell_advice(self.db,item_id,buy,float(self.settings.get('ah_cut_percent',5)))
            ref=copper(a['reference']) if a['reference'] is not None else 'Unknown'
            self.advice.setText(f'{name}: {a["status"]}. Break-even sale price {copper(a["break_even"])} / unit; historical median {ref}. {a["message"]}')
    def delete_selected(self):
        selection=self.table.selectedItems()
        if not selection:return
        trade_id=self.table.item(selection[0].row(),0).data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self,'Delete trade','Permanently delete this trade record?')!=QMessageBox.StandardButton.Yes:return
        delete_lot(self.db,trade_id);self.clear();self.refresh()
    def refresh(self):
        self.records=lots(self.db);self.table.blockSignals(True);self.table.setRowCount(len(self.records))
        cut=float(self.settings.get('ah_cut_percent',5));cache={};open_spend=0;realised=0
        for row,r in enumerate(self.records):
            ident,item_id,name,quality,qty,buy,bought_at,sold,sell,sold_at,note=r
            if sold:
                profit=realised_profit(qty,buy,sell,cut);realised+=profit
                status='Sold';profit_text=('+' if profit>=0 else '-')+copper(abs(profit));window='—';confidence='Completed'
            else:
                open_spend+=qty*buy;status='To sell';profit_text='—'
                key=(item_id,buy)
                if key not in cache:cache[key]=sell_advice(self.db,item_id,buy,cut)
                advice=cache[key];window=advice['window'] or advice['status'];confidence=advice['status']
            breakeven=__import__('math').floor(buy/(1-cut/100))+1 if cut<100 else 0
            values=[name or f'Item #{item_id}',str(qty),copper(buy),status,copper(sell) if sold else '—',profit_text,copper(breakeven),window,confidence]
            for col,value in enumerate(values):
                cell=QTableWidgetItem(value);cell.setData(Qt.ItemDataRole.UserRole,ident)
                if col==0 and quality in QUALITY_COLORS:cell.setForeground(QColor(QUALITY_COLORS[quality]))
                if col==5 and sold:cell.setForeground(QColor('#40d991' if profit>=0 else '#ff7777'))
                self.table.setItem(row,col,cell)
        self.table.blockSignals(False)
        self.summary.setText(f'{len(self.records)} recorded trades | {sum(not r[7] for r in self.records)} awaiting sale | Unsold purchase cost {copper(open_spend)} | Realised P/L after AH cut {"+" if realised>=0 else "-"}{copper(abs(realised))}')
