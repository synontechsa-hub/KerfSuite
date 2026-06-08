"""Costs Tab — material cost, labour, quote summary."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from core.settings import get_currency


class CostsTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_win = parent
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        top = QHBoxLayout()

        # ── Summary cards ─────────────────────────────────────────────────────
        cards = QVBoxLayout()

        self.summary_group = QGroupBox("Job Summary")
        self.summary_form = QFormLayout(self.summary_group)
        self.summary_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.summary_form.setSpacing(6)
        cards.addWidget(self.summary_group)

        self.cost_group = QGroupBox("Cost Breakdown")
        self.cost_form = QFormLayout(self.cost_group)
        self.cost_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.cost_form.setSpacing(6)
        cards.addWidget(self.cost_group)

        self.quote_group = QGroupBox("Quote")
        self.quote_form = QFormLayout(self.quote_group)
        self.quote_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.quote_form.setSpacing(6)
        cards.addWidget(self.quote_group)

        cards.addStretch()
        top.addLayout(cards, 1)

        # ── Per-sheet table ────────────────────────────────────────────────────
        sheet_box = QGroupBox("Sheet Usage Detail")
        sheet_vbox = QVBoxLayout(sheet_box)

        self.sheet_table = QTableWidget(0, 5)
        self.refresh_currency_headers()
        self.sheet_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sheet_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.sheet_table.setAlternatingRowColors(True)
        self.sheet_table.verticalHeader().hide()
        sheet_vbox.addWidget(self.sheet_table)
        top.addWidget(sheet_box, 2)

        layout.addLayout(top)

        self.no_results = QLabel("Run optimization first to see cost breakdown.")
        self.no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results.setStyleSheet("color: #888; font-size: 12pt; padding: 40px;")
        layout.addWidget(self.no_results)

    def refresh_currency_headers(self):
        self.sheet_table.setHorizontalHeaderLabels(
            ["Material / Size", "Qty Used", "Total Pieces", "Avg Efficiency", f"Total Cost ({get_currency()})"]
        )

    def _clear_form(self, form: QFormLayout):
        while form.rowCount():
            form.removeRow(0)

    def _row(self, form, label, value, bold=False, color=None):
        lbl = QLabel(value)
        if bold:
            f = lbl.font()
            f.setBold(True)
            lbl.setFont(f)
        if color:
            lbl.setStyleSheet(f"color: {color};")
        form.addRow(label, lbl)

    def load_from_job(self, job):
        self.refresh_currency_headers()
        has_results = bool(job.layouts)
        self.no_results.setVisible(not has_results)
        self.summary_group.setVisible(has_results)
        self.cost_group.setVisible(has_results)
        self.quote_group.setVisible(has_results)

        if not has_results:
            self.sheet_table.setRowCount(0)
            return

        # Summary
        self._clear_form(self.summary_form)
        self._row(self.summary_form, "Sheets used:", str(job.sheets_used))
        self._row(self.summary_form, "Pieces placed:",
                  f"{job.total_pieces_placed} / {job.total_pieces_needed}")
        eff_color = "#1a7a1a" if job.overall_efficiency >= 75 else "#cc6600"
        self._row(self.summary_form, "Overall efficiency:",
                  f"{job.overall_efficiency:.1f}%", bold=True, color=eff_color)
        if job.unplaced:
            self._row(self.summary_form, "⚠ Unplaced pieces:",
                      str(sum(p.quantity for p in job.unplaced)), color="#cc0000")

        # Costs
        self._clear_form(self.cost_form)
        mat = job.total_material_cost
        c = get_currency()
        
        self._row(self.cost_form, "Total material cost:", f"{c} {mat:.2f}", bold=True)

        if job.estimated_labor_minutes > 0:
            self._row(self.cost_form, "Est. labour time:", f"{job.estimated_labor_minutes:.0f} min")
        if job.estimated_labor_cost > 0:
            self._row(self.cost_form, "Est. labour cost:", f"{c} {job.estimated_labor_cost:.2f}")

        # Quote
        self._clear_form(self.quote_form)
        total_quote = job.total_sell_price
        material_base = sum(l.sheet.sell_price for l in job.layouts)
        labor_base = job.estimated_labor_cost
        
        if total_quote > 0:
            self._row(self.quote_form, "Base Material:", f"{c} {material_base:.2f}")
            if labor_base > 0:
                self._row(self.quote_form, "Base Labour:", f"{c} {labor_base:.2f}")
            
            if job.markup_percent > 0:
                markup_val = total_quote - (material_base + labor_base)
                self._row(self.quote_form, f"Project Markup ({job.markup_percent:.1f}%):", 
                          f"{c} {markup_val:.2f}")
            
            self._row(self.quote_form, "Total Quote Price:", f"{c} {total_quote:.2f}",
                      bold=True, color="#2d6a9f")
            
            # Gross Margin calculation (Sale Price - Internal Cost) / Sale Price
            internal_cost = job.total_job_cost
            if total_quote > internal_cost:
                margin = (total_quote - internal_cost) / total_quote * 100
                self._row(self.quote_form, "Est. Gross Margin:", f"{margin:.1f}%",
                          color="#1a7a1a" if margin > 25 else "#cc6600")
        else:
            self._row(self.quote_form, "(Set prices on sheets to see quote)", "")

        # Sheet table
        self.sheet_table.setRowCount(0)
        
        sheet_groups = {}
        for layout in job.layouts:
            sid = layout.sheet.id
            if sid not in sheet_groups:
                sheet_groups[sid] = {
                    "sheet": layout.sheet,
                    "count": 0,
                    "pieces": 0,
                    "total_eff": 0.0,
                    "total_cost": 0.0
                }
            grp = sheet_groups[sid]
            grp["count"] += 1
            grp["pieces"] += len(layout.placed)
            grp["total_eff"] += layout.efficiency
            grp["total_cost"] += layout.sheet.buy_price

        for i, grp in enumerate(sheet_groups.values()):
            r = self.sheet_table.rowCount()
            self.sheet_table.insertRow(r)
            sheet = grp["sheet"]
            avg_eff = grp["total_eff"] / grp["count"]

            items = [
                sheet.display_label(),
                f"{grp['count']}x",
                str(grp['pieces']),
                f"{avg_eff:.1f}%",
                f"{c} {grp['total_cost']:.2f}",
            ]
            for col, txt in enumerate(items):
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.sheet_table.setItem(r, col, item)

            # Colour-code efficiency
            eff_item = self.sheet_table.item(r, 3)
            if avg_eff >= 80:
                eff_item.setForeground(QColor("#1a7a1a"))
            elif avg_eff >= 60:
                eff_item.setForeground(QColor("#cc6600"))
            else:
                eff_item.setForeground(QColor("#cc0000"))
