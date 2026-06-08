"""Job Info Tab — customer, material, kerf, rates."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox
)
from PyQt6.QtCore import Qt
from core.settings import get_currency, set_currency, CURRENCIES


class JobTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_win = parent
        self._loading = False
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        # ── Job Details ───────────────────────────────────────────────────────
        job_group = QGroupBox("Job Details")
        form = QFormLayout(job_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Kitchen Cabinet Order #42")
        self.customer_edit = QLineEdit()
        self.customer_edit.setPlaceholderText("e.g. Smith & Sons Workshop")
        self.material_edit = QLineEdit()
        self.material_edit.setPlaceholderText("e.g. Acrylic Cast 10mm White")
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Any extra notes about this job…")
        self.notes_edit.setMaximumHeight(90)

        form.addRow("Job Name:", self.name_edit)
        form.addRow("Customer:", self.customer_edit)
        form.addRow("Material:", self.material_edit)
        form.addRow("Notes:", self.notes_edit)
        layout.addWidget(job_group)

        # ── Cutting Settings ──────────────────────────────────────────────────
        cut_group = QGroupBox("Cutting Settings")
        cut_form = QFormLayout(cut_group)
        cut_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        cut_form.setSpacing(8)

        self.kerf_spin = QSpinBox()
        self.kerf_spin.setRange(0, 20)
        self.kerf_spin.setSuffix(" mm")
        self.kerf_spin.setToolTip("Saw blade thickness — deducted from each cut edge.")

        self.cut_mode_combo = QComboBox()
        self.cut_mode_combo.addItem("Nested (CNC Router)", "nested")
        self.cut_mode_combo.addItem("Guillotine (Manual Saw)", "guillotine")
        self.cut_mode_combo.setToolTip("Nested for CNC nesting. Guillotine for edge-to-edge manual saw cuts.")

        cut_form.addRow("Blade Kerf:", self.kerf_spin)
        cut_form.addRow("Cut Mode:", self.cut_mode_combo)
        layout.addWidget(cut_group)

        # ── Pricing ───────────────────────────────────────────────────────────
        price_group = QGroupBox("Pricing (optional)")
        price_form = QFormLayout(price_group)
        price_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        price_form.setSpacing(8)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(CURRENCIES)
        self.currency_combo.setCurrentText(get_currency())
        self.currency_combo.currentTextChanged.connect(self._on_currency_changed)



        self.markup_spin = QDoubleSpinBox()
        self.markup_spin.setRange(0, 500)
        self.markup_spin.setDecimals(1)
        self.markup_spin.setSuffix(" %")
        self.markup_spin.setToolTip("Markup applied on top of sheet sell prices for quoting.")

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 1000)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setPrefix(f"{get_currency()} ")
        self.rate_spin.setSuffix(" / hr")
        self.rate_spin.setToolTip("Hourly labor rate for cost estimation.")

        price_form.addRow("Currency:", self.currency_combo)
        price_form.addRow("Hourly Rate:", self.rate_spin)
        price_form.addRow("Markup %:", self.markup_spin)
        layout.addWidget(price_group)

        layout.addStretch()

        # Wire change signals
        for w in [self.name_edit, self.customer_edit, self.material_edit]:
            w.textChanged.connect(self._on_changed)
        self.notes_edit.textChanged.connect(self._on_changed)
        for w in [self.kerf_spin, self.markup_spin, self.rate_spin]:
            w.valueChanged.connect(self._on_changed)
        self.cut_mode_combo.currentIndexChanged.connect(self._on_changed)

    def _on_changed(self):
        if not self._loading:
            self.main_win.mark_dirty()

    def _on_currency_changed(self, symbol):
        set_currency(symbol)
        self.refresh_currency()
        self.main_win.refresh_currency_views()
        self.main_win.set_status("Currency changed.")

    def refresh_currency(self):
        c = get_currency()
        self.rate_spin.setPrefix(f"{c} ")

    def load_from_job(self, job):
        self._loading = True
        try:
            self.name_edit.setText(job.name)
            self.customer_edit.setText(job.customer)
            self.material_edit.setText(job.material_name)
            self.notes_edit.setPlainText(job.notes)
            self.kerf_spin.setValue(job.blade_kerf)
            self.markup_spin.setValue(job.markup_percent)
            self.rate_spin.setValue(job.hourly_rate)
            idx = self.cut_mode_combo.findData(job.cut_mode)
            if idx >= 0:
                self.cut_mode_combo.setCurrentIndex(idx)
        finally:
            self._loading = False

    def save_to_job(self, job):
        job.name = self.name_edit.text().strip() or "New Job"
        job.customer = self.customer_edit.text().strip()
        job.material_name = self.material_edit.text().strip()
        job.notes = self.notes_edit.toPlainText().strip()
        job.blade_kerf = self.kerf_spin.value()
        job.markup_percent = self.markup_spin.value()
        job.hourly_rate = self.rate_spin.value()
        job.cut_mode = self.cut_mode_combo.currentData()
