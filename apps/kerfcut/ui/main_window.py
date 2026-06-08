"""
KerfCut — Main Application Window
"""
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QLabel,
    QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import QSettings, QSize, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from utils.logger import logger

from version import APP_NAME, APP_VERSION, WINDOW_TITLE, APP_AUTHOR, APP_DESCRIPTION
from core import Job, save_job, load_job, load_zad_file, get_recent_jobs
from core.persistence import DEFAULT_JOBS_DIR
from ui.job_tab import JobTab
from ui.sheets_tab import SheetsTab
from ui.pieces_tab import PiecesTab
from ui.cutplan_tab import CutPlanTab
from ui.costs_tab import CostsTab

JOBS_DIR = str(DEFAULT_JOBS_DIR)


class OptimizerThread(QThread):
    done = pyqtSignal()  # custom signal, emitted after optimize() returns
    
    def __init__(self, job, strategy, parent=None):
        super().__init__(parent)
        self.job = job
        self.strategy = strategy
        
    def run(self):
        from core import optimize
        optimize(self.job, strategy=self.strategy)
        self.done.emit()


class TrialIncrementThread(QThread):
    done = pyqtSignal()
    
    def run(self):
        from core.auth import increment_trial_run
        increment_trial_run()
        self.done.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file: str | None = None
        self.job = Job()
        self._dirty = False

        os.makedirs(JOBS_DIR, exist_ok=True)

        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(1100, 750)
        self._restore_geometry()

        self._history = []
        self._history_index = -1
        self._saved_history_index = -1
        self._is_undoing = False
        self._history_timer = QTimer()
        self._history_timer.setSingleShot(True)
        self._history_timer.setInterval(500)
        self._history_timer.timeout.connect(self._push_history)
        self._pending_trial_increment = False

        self._build_menu()
        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()
        self._dirty = False # Initial state is clean
        self._refresh_all()
        self._push_history() # Initial state

    # ── Geometry ──────────────────────────────────────────────────────────────
    def _restore_geometry(self):
        settings = QSettings(APP_AUTHOR, APP_NAME)
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1240, 820)

    def closeEvent(self, event):
        if self._dirty:
            r = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if r == QMessageBox.StandardButton.Save:
                if not self._save():
                    event.ignore()
                    return
            elif r == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        settings = QSettings(APP_AUTHOR, APP_NAME)
        settings.setValue("geometry", self.saveGeometry())
        event.accept()

    # ── Menu ──────────────────────────────────────────────────────────────────
    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._action(file_menu, "&New Job",
                     self._new_job,    "Ctrl+N")
        self._action(file_menu, "&Open…",
                     self._open,       "Ctrl+O")
        file_menu.addSeparator()
        self._action(file_menu, "&Save",
                     self._save,       "Ctrl+S")
        self._action(file_menu, "Save &As…",
                     self._save_as,    "Ctrl+Shift+S")
        file_menu.addSeparator()
        self._action(file_menu, "Import Legacy .ZAD…", self._import_zad)
        file_menu.addSeparator()
        self.recent_menu = file_menu.addMenu("Recent Jobs")
        self._rebuild_recent_menu()
        file_menu.addSeparator()
        self._action(file_menu, "Export &PDF…",
                     self._export_pdf, "Ctrl+E")
        self._action(file_menu, "Export &CSV…",        self._export_csv)
        file_menu.addSeparator()
        self._action(file_menu, "E&xit",
                     self.close,       "Ctrl+Q")

        # Edit
        edit_menu = mb.addMenu("&Edit")
        self.undo_act = self._action(edit_menu, "&Undo", self._undo, "Ctrl+Z")
        self.redo_act = self._action(edit_menu, "&Redo", self._redo, "Ctrl+Y")
        self.undo_act.setEnabled(False)
        self.redo_act.setEnabled(False)

        # View
        view_menu = mb.addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        self.theme_light_act = QAction("Light", self, checkable=True)
        self.theme_dark_act = QAction("Dark", self, checkable=True)
        
        settings = QSettings(APP_AUTHOR, APP_NAME)
        current_theme = settings.value("theme", "light")
        self.theme_light_act.setChecked(current_theme == "light")
        self.theme_dark_act.setChecked(current_theme == "dark")
        
        self.theme_light_act.triggered.connect(lambda: self._set_theme("light"))
        self.theme_dark_act.triggered.connect(lambda: self._set_theme("dark"))
        
        theme_menu.addAction(self.theme_light_act)
        theme_menu.addAction(self.theme_dark_act)

        # Optimise
        opt_menu = mb.addMenu("&Optimise")
        self.optimize_act = self._action(opt_menu, "▶  Run Optimisation",
                                         self._run_optimize, "F5")
        self._action(opt_menu, "Clear Results",         self._clear_results)

        # Help
        help_menu = mb.addMenu("&Help")
        self._action(help_menu, f"About {APP_NAME}", self._about)

    def _action(self, menu, label, slot, shortcut=None):
        act = QAction(label, self)
        if shortcut:
            act.setShortcut(shortcut)
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _set_theme(self, theme: str):
        self.theme_light_act.setChecked(theme == "light")
        self.theme_dark_act.setChecked(theme == "dark")
        settings = QSettings(APP_AUTHOR, APP_NAME)
        settings.setValue("theme", theme)
        
        # Apply instantly
        from ui.app import load_stylesheet
        QApplication.instance().setStyleSheet(load_stylesheet())

    def _rebuild_recent_menu(self):
        self.recent_menu.clear()
        recent = get_recent_jobs(JOBS_DIR)
        if not recent:
            self.recent_menu.addAction("(no recent files)").setEnabled(False)
            return
        for item in recent:
            act = QAction(f"{item['name']}  ({item['modified']})", self)
            act.triggered.connect(
                lambda checked, p=item["path"]: self._open_file(p))
            self.recent_menu.addAction(act)

    # ── Toolbar ───────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))

        def btn(label, slot, tip=""):
            act = QAction(label, self)
            act.setToolTip(tip)
            act.triggered.connect(slot)
            tb.addAction(act)

        btn("🆕  New",      self._new_job,      "New Job  (Ctrl+N)")
        btn("📂  Open",     self._open,         "Open Job  (Ctrl+O)")
        btn("💾  Save",     self._save,         "Save Job  (Ctrl+S)")
        tb.addSeparator()
        self.undo_btn = QAction("↩️ Undo", self)
        self.undo_btn.setToolTip("Undo  (Ctrl+Z)")
        self.undo_btn.triggered.connect(self._undo)
        self.undo_btn.setEnabled(False)
        tb.addAction(self.undo_btn)
        self.redo_btn = QAction("↪️ Redo", self)
        self.redo_btn.setToolTip("Redo  (Ctrl+Y)")
        self.redo_btn.triggered.connect(self._redo)
        self.redo_btn.setEnabled(False)
        tb.addAction(self.redo_btn)
        tb.addSeparator()
        btn("▶  Optimise", self._run_optimize, "Run Optimisation  (F5)")
        tb.addSeparator()
        btn("📄  PDF",      self._export_pdf,   "Export PDF  (Ctrl+E)")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.job_tab = JobTab(self)
        self.sheets_tab = SheetsTab(self)
        self.pieces_tab = PiecesTab(self)
        self.cutplan_tab = CutPlanTab(self)
        self.costs_tab = CostsTab(self)

        self.tabs.addTab(self.job_tab,     "📋  Job Info")
        self.tabs.addTab(self.sheets_tab,  "📐  Stock Sheets")
        self.tabs.addTab(self.pieces_tab,  "✂️   Pieces")
        self.tabs.addTab(self.cutplan_tab, "🗺️   Cut Plan")
        self.tabs.addTab(self.costs_tab,   "📊  Costs")

        self.setCentralWidget(self.tabs)

    # ── Status Bar ────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label, 1)
        
        self.license_label = QLabel("")
        self.license_label.setObjectName("licenseStatus")
        self.license_label.setContentsMargins(0, 0, 10, 0)
        self.statusBar().addPermanentWidget(self.license_label)
        self._refresh_license_status()

    def set_status(self, msg: str):
        self.status_label.setText(msg)

    def _refresh_license_status(self):
        from core.auth import get_license_info
        info = get_license_info()
        status = info["status"]
        days = info["days_left"]
        tier = info.get("tier", "free")
        
        self.license_label.setStyleSheet("") # Reset
        
        if status == "Developer":
            self.license_label.setText("🛠️ Dev Mode")
        elif status == "Activated":
            if days <= 5:
                self.license_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.license_label.setText(f"⚠️ License: {days} days left")
            else:
                self.license_label.setText(f"✅ Licensed ({days} days offline)")
        elif status == "Trial":
            runs = info.get("runs_left", 0)
            runs_used = info.get("runs_used", 0)
            runs_total = info.get("runs_total", 20)
            self.license_label.setStyleSheet("color: #2d6a9f; font-weight: bold;")
            self.license_label.setText(
                f"⏳ Trial: {runs_used}/{runs_total} used ({runs} left), {days} days left"
            )
        else:
            self.license_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            self.license_label.setText("🆓 Free Tier (Limited)")

    def refresh_currency_views(self):
        self.job_tab.refresh_currency()
        self.sheets_tab.refresh_currency_headers()
        self.costs_tab.refresh_currency_headers()
        self.costs_tab.load_from_job(self.job)

    # ── Data Flow & History ───────────────────────────────────────────────────
    def mark_dirty(self):
        if self._is_undoing:
            return
        self._dirty = True
        self._update_title(dirty=True)
        # Invalidate stale optimization results whenever inputs change
        if self.job.layouts:
            self.job.layouts = []
            self.job.unplaced = []
            self.cutplan_tab.load_from_job(self.job)
            self.costs_tab.load_from_job(self.job)
            self.set_status("Inputs changed — press F5 to re-optimise.")
        self._history_timer.start()

    def _push_history(self):
        if self._is_undoing:
            return
        self.collect_from_ui()
        self.costs_tab.load_from_job(self.job)
        import json
        from core.persistence import job_to_dict
        snapshot = json.dumps(job_to_dict(self.job))
        
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]
            
        if self._history and self._history[-1] == snapshot:
            return
            
        self._history.append(snapshot)
        self._history_index = len(self._history) - 1
        
        if len(self._history) > 50:
            self._history.pop(0)
            self._history_index -= 1
            self._saved_history_index -= 1
            
        self._update_undo_actions()

    def _undo(self):
        if self._history_index > 0:
            self._history_index -= 1
            self._restore_history_state()
            
    def _redo(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self._restore_history_state()
            
    def _restore_history_state(self):
        self._is_undoing = True
        try:
            import json
            from core.persistence import job_from_dict
            snapshot = self._history[self._history_index]
            self.job = job_from_dict(json.loads(snapshot))
            self._refresh_all()
            self._dirty = (self._history_index != self._saved_history_index)
            self._update_title(dirty=self._dirty)
        finally:
            self._is_undoing = False
        self._update_undo_actions()

    def _update_undo_actions(self):
        can_undo = self._history_index > 0
        can_redo = self._history_index < len(self._history) - 1
        self.undo_act.setEnabled(can_undo)
        self.redo_act.setEnabled(can_redo)
        self.undo_btn.setEnabled(can_undo)
        self.redo_btn.setEnabled(can_redo)

    def _update_title(self, dirty: bool | None = None):
        if dirty is None:
            dirty = self._dirty
        base = f"{APP_NAME} — {self.job.name}"
        if self.current_file:
            base += f"  [{Path(self.current_file).name}]"
        self.setWindowTitle(base + (" *" if dirty else ""))

    def _refresh_all(self):
        """Push job data to all UI tabs."""
        self.job_tab.load_from_job(self.job)
        self.sheets_tab.load_from_job(self.job)
        self.pieces_tab.load_from_job(self.job)
        self.cutplan_tab.load_from_job(self.job)
        self.costs_tab.load_from_job(self.job)
        self._update_title()

    def collect_from_ui(self):
        """Pull current UI state into self.job before saving / optimising."""
        self.job_tab.save_to_job(self.job)
        self.sheets_tab.save_to_job(self.job)
        self.pieces_tab.save_to_job(self.job)

    # ── File Actions ──────────────────────────────────────────────────────────
    def _new_job(self):
        if self._dirty:
            r = QMessageBox.question(
                self, "Unsaved Changes",
                "Discard unsaved changes and start a new job?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        self.job = Job()
        self.current_file = None
        self._history.clear()
        self._history_index = -1
        self._saved_history_index = -1
        self._dirty = False
        self._refresh_all()
        self._push_history()
        self.set_status("New job created.")

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Job", JOBS_DIR,
            "KerfCut jobs (*.kcut);;Legacy files (*.zcad);;All files (*)",
        )
        if path:
            self._open_file(path)

    def _open_file(self, path: str):
        try:
            self.job = load_job(path)
            self.current_file = path
            self._history.clear()
            self._history_index = -1
            self._saved_history_index = -1
            self._dirty = False
            self._refresh_all()
            self._push_history()
            self._rebuild_recent_menu()
            self.set_status(f"Opened: {Path(path).name}")
        except Exception as e:
            logger.error("Failed to open job file", exc_info=True)
            QMessageBox.critical(self, "Error opening file", str(e))

    def _save(self) -> bool:
        if not self.current_file:
            return self._save_as()
        self.collect_from_ui()
        try:
            save_job(self.job, self.current_file)
            self._saved_history_index = self._history_index
            self._dirty = False
            self._update_title()
            self._rebuild_recent_menu()
            self.set_status(f"Saved — {Path(self.current_file).name}")
            return True
        except Exception as e:
            logger.error("Failed to save job file", exc_info=True)
            QMessageBox.critical(self, "Save Error", str(e))
            return False

    def _save_as(self) -> bool:
        self.collect_from_ui()
        default = str(Path(JOBS_DIR) / (self.job.name or "job"))
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Job As", default,
            "KerfCut jobs (*.kcut)",
        )
        if path:
            if not path.endswith(".kcut"):
                path += ".kcut"
            self.current_file = path
            return self._save()
        return False

    def _import_zad(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Legacy Z-CAD Job", "",
            "Z-CAD files (*.ZAD *.zad);;All files (*)",
        )
        if path:
            try:
                self.job = load_zad_file(path)
                self.current_file = None
                self._history.clear()
                self._history_index = -1
                self._saved_history_index = -1
                self._refresh_all()
                self.mark_dirty()
                self._push_history()
                self.set_status(
                    f"Imported: {Path(path).name} — save as .kcut to keep changes."
                )
            except Exception as e:
                logger.error("Failed to import legacy ZAD file", exc_info=True)
                QMessageBox.critical(self, "Import Error", str(e))

    # ── Optimise ──────────────────────────────────────────────────────────────
    def _run_optimize(self):
        self.collect_from_ui()
        self._pending_trial_increment = False

        from core.auth import get_license_info, FREE_MAX_SHEETS, FREE_MAX_PIECES
        info = get_license_info()
        tier = info.get("tier", "free")

        active_sheets = [s for s in self.job.sheets if s.active and s.width > 0 and s.height > 0 and s.quantity > 0]
        active_pieces = [p for p in self.job.pieces if p.quantity > 0 and p.width > 0 and p.height > 0]

        if tier == "free":
            if sum(max(0, s.quantity) for s in active_sheets) > FREE_MAX_SHEETS or sum(p.quantity for p in active_pieces) > FREE_MAX_PIECES:
                QMessageBox.warning(
                    self, "Free Tier Limit Reached",
                    f"The Free Tier is limited to {FREE_MAX_SHEETS} active sheets and {FREE_MAX_PIECES} pieces per job.\n\n"
                    "Please upgrade to KerfCut Pro to unlock unlimited optimisations!"
                )
                return

        if not active_sheets:
            QMessageBox.warning(self, "No Sheets",
                                "Add at least one active stock sheet with Qty > 0 before optimising.")
            return
            
        if not active_pieces:
            QMessageBox.warning(self, "No Pieces",
                                "Add at least one piece with a quantity > 0 before optimising.")
            return

        # Pre-optimization validation: check for impossible pieces
        impossible_pieces = []
        for p in active_pieces:
            can_fit = False
            for s in active_sheets:
                # A piece fits if its physical dimensions fit on the sheet.
                # Kerf overflows the edge (the saw blade cuts air) so it
                # does not make the piece itself larger.
                if p.width <= s.width and p.height <= s.height:
                    can_fit = True
                    break
                if p.can_rotate:
                    if p.height <= s.width and p.width <= s.height:
                        can_fit = True
                        break
            if not can_fit:
                impossible_pieces.append(p)

        if impossible_pieces:
            names = ", ".join([f"{p.label or 'Unnamed'} ({p.width}x{p.height})" for p in impossible_pieces[:3]])
            if len(impossible_pieces) > 3:
                names += f" and {len(impossible_pieces)-3} more"
            
            reply = QMessageBox.warning(self, "Impossible Pieces Detected",
                f"Some pieces are physically larger than any active stock sheet (including kerf).\n\n"
                f"Examples: {names}\n\n"
                "These pieces will be skipped by the optimizer. Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        self.set_status("⏳ Optimising… please wait.")
        # Disable input tabs and optimize action to prevent race conditions
        if hasattr(self, 'optimize_act'):
            self.optimize_act.setEnabled(False)
        self.job_tab.setEnabled(False)
        self.sheets_tab.setEnabled(False)
        self.pieces_tab.setEnabled(False)
        QApplication.processEvents()

        from core.optimizer import MaxRectsBSSFStrategy, GuillotineStrategy
        if getattr(self.job, "cut_mode", "nested") == "guillotine":
            strategy = GuillotineStrategy()
        else:
            strategy = MaxRectsBSSFStrategy()

        import copy
        self._opt_job = copy.deepcopy(self.job)
        self.optimizer_thread = OptimizerThread(self._opt_job, strategy, parent=self)
        self._pending_trial_increment = (tier == "trial")
        self.optimizer_thread.done.connect(self._on_optimize_finished)
        self.optimizer_thread.start()

    def _on_optimize_finished(self):
        self.job = self._opt_job
        from core.auth import increment_trial_run
        # Wait for the thread to fully exit before touching shared job data
        if hasattr(self, 'optimizer_thread') and self.optimizer_thread.isRunning():
            self.optimizer_thread.wait(5000)  # max 5 seconds

        # Re-enable inputs and optimize action
        if hasattr(self, 'optimize_act'):
            self.optimize_act.setEnabled(True)
        self.job_tab.setEnabled(True)
        self.sheets_tab.setEnabled(True)
        self.pieces_tab.setEnabled(True)

        self.cutplan_tab.load_from_job(self.job)
        self.costs_tab.load_from_job(self.job)
        self.tabs.setCurrentWidget(self.cutplan_tab)

        placed = self.job.total_pieces_placed
        needed = self.job.total_pieces_needed
        eff = self.job.overall_efficiency
        unplaced = len(self.job.unplaced)

        msg = (f"✅ Done — {placed}/{needed} pieces placed on "
               f"{self.job.sheets_used} sheet(s)  |  "
               f"Efficiency: {eff:.1f}%")
        if unplaced:
            msg += f"  ⚠  {unplaced} piece(s) unplaced — add more sheets."
        self.set_status(msg)

        if self._pending_trial_increment:
            self._trial_thread = TrialIncrementThread(parent=self)
            self._trial_thread.done.connect(self._on_trial_incremented)
            self._trial_thread.start()
            self._pending_trial_increment = False

    def _on_trial_incremented(self):
        self._refresh_license_status()

    def _clear_results(self):
        self.job.layouts = []
        self.job.unplaced = []
        self.cutplan_tab.load_from_job(self.job)
        self.costs_tab.load_from_job(self.job)
        self.set_status("Results cleared.")

    # ── Export ────────────────────────────────────────────────────────────────
    def _export_pdf(self):
        from core.auth import get_license_info
        if get_license_info().get("tier", "free") == "free":
            QMessageBox.warning(
                self, "Free Tier Restriction",
                "PDF Export is disabled in the Free Tier.\n\n"
                "Please upgrade to KerfCut Pro to unlock printing and sharing."
            )
            return

        if not self.job.layouts:
            QMessageBox.information(self, "No Results",
                                    "Run optimisation first, then export.")
            return
        default = str(Path(JOBS_DIR) / f"{self.job.name or 'job'}_cutplan.pdf")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF", default, "PDF files (*.pdf)"
        )
        if path:
            try:
                from core.settings import get_currency
                from core.export_pdf import export_pdf
                export_pdf(self.job, path, get_currency())
                self.set_status(f"PDF saved — {Path(path).name}")
                QMessageBox.information(
                    self, "PDF Exported", f"Saved to:\n{path}")
            except ImportError:
                QMessageBox.critical(self, "Missing Library",
                                     "PDF export requires 'reportlab'.\n\n"
                                     "Install it with:\n    pip install reportlab")
            except Exception as e:
                logger.error("Failed to export PDF", exc_info=True)
                QMessageBox.critical(self, "Export Error", str(e))

    def _export_csv(self):
        if not self.job.pieces:
            return
        self.collect_from_ui()
        default = str(Path(JOBS_DIR) / f"{self.job.name or 'job'}_pieces.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Piece List CSV", default, "CSV files (*.csv)"
        )
        if path:
            try:
                from core.csv_io import export_pieces_to_csv
                export_pieces_to_csv(self.job.pieces, path)
                self.set_status(f"CSV saved — {Path(path).name}")
            except Exception as e:
                logger.error("Failed to export pieces CSV", exc_info=True)
                QMessageBox.critical(self, "Export Error", str(e))

    # ── About ─────────────────────────────────────────────────────────────────
    def _about(self):
        from core.auth import get_machine_id_display
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>{APP_DESCRIPTION}</p>"
            "<p>Uses the <b>MaxRects BSSF</b> bin-packing algorithm "
            "for optimal material yield.</p>"
            "<p>Supports import of legacy <b>Z-CAD 2.1d</b> (.ZAD) files.</p>"
            f"<hr><p style='color: #7f8c8d; font-size: 11px;'>"
            f"Machine ID: <code>{get_machine_id_display()}</code></p>",
        )
