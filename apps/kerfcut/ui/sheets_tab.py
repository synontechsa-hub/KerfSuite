"""Stock Sheets Tab — add/edit/remove stock sheet sizes."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView,
    QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from core.models import Sheet
from core.library import get_library, add_to_library
from core.settings import get_currency

COLUMNS = ["Active", "Width (mm)", "Height (mm)", "Qty in Stock",
           "Buy Price", "Sell Price", "Thickness (mm)", "Label"]
COL_ACTIVE, COL_W, COL_H, COL_QTY, COL_BUY, COL_SELL, COL_THICK, COL_LABEL = range(8)


class SheetsTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_win = parent
        self._loading = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Toolbar
        bar = QHBoxLayout()
        self.add_btn = QPushButton("➕  Add Sheet")
        self.add_btn.clicked.connect(self._add_sheet)
        self.remove_btn = QPushButton("🗑  Remove Selected")
        self.remove_btn.clicked.connect(self._remove_selected)
        self.dup_btn = QPushButton("⧉  Duplicate")
        self.dup_btn.clicked.connect(self._duplicate)

        # Material Library
        self.lib_combo = QComboBox()
        self.lib_combo.setMinimumWidth(200)
        self._refresh_library_combo()
        
        self.add_lib_btn = QPushButton("⬇️ Add")
        self.add_lib_btn.setToolTip("Add selected material from library to job")
        self.add_lib_btn.clicked.connect(self._add_from_library)
        
        self.save_lib_btn = QPushButton("💾 Save to Library")
        self.save_lib_btn.setToolTip("Save the selected row to your material library")
        self.save_lib_btn.clicked.connect(self._save_selected_to_library)

        bar.addWidget(self.add_btn)
        bar.addWidget(self.dup_btn)
        bar.addWidget(self.remove_btn)
        bar.addSpacing(20)
        bar.addWidget(QLabel("Library:"))
        bar.addWidget(self.lib_combo)
        bar.addWidget(self.add_lib_btn)
        bar.addWidget(self.save_lib_btn)
        bar.addStretch()
        layout.addLayout(bar)

        # Table
        self.table = QTableWidget(0, len(COLUMNS))
        self.refresh_currency_headers()
        self.table.horizontalHeader().setSectionResizeMode(COL_LABEL, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        hint = QLabel("💡 Tip: Set Qty in Stock to control how many sheets the optimizer may use.")
        hint.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(hint)

    def refresh_currency_headers(self):
        c = get_currency()
        columns = COLUMNS.copy()
        columns[COL_BUY] = f"Buy Price ({c})"
        columns[COL_SELL] = f"Sell Price ({c})"
        if hasattr(self, "table"):
            self.table.setHorizontalHeaderLabels(columns)

    def _add_sheet(self, sheet=None):
        if not isinstance(sheet, Sheet):
            sheet = Sheet(width=2440, height=1220, active=True, quantity=10)
        self._append_row(sheet)
        self.main_win.mark_dirty()

    def _refresh_library_combo(self):
        self.lib_combo.clear()
        self._library_cache = get_library()
        for sheet in self._library_cache:
            name = f"{sheet.width}x{sheet.height}"
            if sheet.thickness:
                name += f"x{sheet.thickness}mm"
            if sheet.label:
                name += f" - {sheet.label}"
            self.lib_combo.addItem(name)

    def _add_from_library(self):
        idx = self.lib_combo.currentIndex()
        if 0 <= idx < len(self._library_cache):
            sheet = self._library_cache[idx]
            # Create a copy so we don't modify the library object directly
            import copy
            self._add_sheet(copy.deepcopy(sheet))
            
    def _save_selected_to_library(self):
        rows = {i.row() for i in self.table.selectedItems()}
        if not rows:
            QMessageBox.information(self, "No Selection", "Please select a sheet row to save to the library.")
            return
            
        added = 0
        for r in rows:
            sheet = self._read_row(r)
            if sheet.width > 0 and sheet.height > 0:
                add_to_library(sheet)
                added += 1
                
        if added > 0:
            self._refresh_library_combo()
            QMessageBox.information(self, "Library Saved", f"Added {added} material(s) to your library.")

    def _remove_selected(self):
        rows = sorted({i.row() for i in self.table.selectedItems()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self.main_win.mark_dirty()

    def _duplicate(self):
        rows = {i.row() for i in self.table.selectedItems()}
        for r in rows:
            sheet = self._read_row(r)
            self._append_row(sheet)
        self.main_win.mark_dirty()

    def _append_row(self, sheet: Sheet):
        self._loading = True
        r = self.table.rowCount()
        self.table.insertRow(r)

        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        chk.setCheckState(Qt.CheckState.Checked if sheet.active else Qt.CheckState.Unchecked)
        chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(r, COL_ACTIVE, chk)

        self.table.setItem(r, COL_W, self._num_item(sheet.width))
        self.table.setItem(r, COL_H, self._num_item(sheet.height))
        self.table.setItem(r, COL_QTY, self._num_item(sheet.quantity))
        self.table.setItem(r, COL_BUY, self._float_item(sheet.buy_price))
        self.table.setItem(r, COL_SELL, self._float_item(sheet.sell_price))
        self.table.setItem(r, COL_THICK, self._float_item(sheet.thickness))
        self.table.setItem(r, COL_LABEL, QTableWidgetItem(sheet.label))

        self._loading = False

    def _num_item(self, val):
        item = QTableWidgetItem(str(val))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _float_item(self, val):
        item = QTableWidgetItem(f"{val:.2f}" if val is not None else "0.00")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def _on_item_changed(self, item):
        if not self._loading:
            self.main_win.mark_dirty()

    def _read_row(self, r: int) -> Sheet:
        def safe_int(col):
            try:
                item = self.table.item(r, col)
                return int(item.text()) if item else 0
            except (ValueError, AttributeError):
                return 0

        def safe_float(col):
            try:
                item = self.table.item(r, col)
                return float(item.text()) if item else 0.0
            except (ValueError, AttributeError):
                return 0.0

        active_item = self.table.item(r, COL_ACTIVE)
        active = active_item.checkState() == Qt.CheckState.Checked if active_item else True
        label_item = self.table.item(r, COL_LABEL)
        
        return Sheet(
            width=safe_int(COL_W),
            height=safe_int(COL_H),
            active=active,
            quantity=max(0, safe_int(COL_QTY)),
            buy_price=safe_float(COL_BUY),
            sell_price=safe_float(COL_SELL),
            thickness=safe_float(COL_THICK),
            label=label_item.text() if label_item else "",
        )

    def load_from_job(self, job):
        self._loading = True
        self.table.setRowCount(0)
        self._loading = False
        for sheet in job.sheets:
            self._append_row(sheet)

    def save_to_job(self, job):
        job.sheets = [self._read_row(r) for r in range(self.table.rowCount())]
