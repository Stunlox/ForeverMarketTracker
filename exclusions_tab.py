from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView
from core import QUALITY_COLORS
from PySide6.QtGui import QColor
from exclusions import migrate,restore

class ExclusionsTab(QWidget):
    changed=Signal()
    def __init__(self,db):
        super().__init__();self.db=db;migrate(db)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Excluded items are hidden from Suggested Buys, Target Item and Market Timing Simplified. Market Browser remains searchable. Vendor exclusions require verified vendor-only metadata or a manual exclusion.'))
        row=QHBoxLayout();layout.addLayout(row)
        reload=QPushButton('Refresh exclusions');reload.clicked.connect(self.refresh);row.addWidget(reload)
        restore_btn=QPushButton('Restore selected items');restore_btn.clicked.connect(self.restore_selected);row.addWidget(restore_btn)
        row.addStretch()
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['Item','ID','Reason','Source']);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection);self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);layout.addWidget(self.table)
        self.summary=QLabel();layout.addWidget(self.summary);self.refresh()
    def refresh(self):
        rows=self.db.execute("SELECT i.name,e.item_id,e.reason,'Manual',i.quality FROM item_exclusions e LEFT JOIN items i ON i.item_id=e.item_id UNION ALL SELECT i.name,v.item_id,'Verified vendor-only',v.source,i.quality FROM vendor_items v LEFT JOIN items i ON i.item_id=v.item_id ORDER BY 1").fetchall()
        self.table.setRowCount(len(rows))
        for r,(name,ident,reason,source,quality) in enumerate(rows):
            for c,val in enumerate((name or f'Item #{ident}',ident,reason,source)):
                cell=QTableWidgetItem(str(val));cell.setData(Qt.ItemDataRole.UserRole,ident)
                if c==0 and quality in QUALITY_COLORS:cell.setForeground(QColor(QUALITY_COLORS[quality]))
                self.table.setItem(r,c,cell)
        self.summary.setText(f'{len(rows)} excluded entries. Only manually excluded entries can be restored here; verified vendor-only entries are retained as source data.')
    def restore_selected(self):
        ids={self.table.item(index.row(),1).data(Qt.ItemDataRole.UserRole) for index in self.table.selectionModel().selectedRows()}
        for ident in ids:restore(self.db,ident)
        self.refresh();self.changed.emit()
