"""Cut Plan Tab — visual rendering of the optimized sheet layouts."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QSlider, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QFontMetrics

from core.models import LayoutGroup


class SheetCanvas(QWidget):
    """Renders a single layout group in a technical drawing style."""

    MARGIN = 40  # increased to allow dimensions outside

    def __init__(self, group: LayoutGroup, scale: float = 0.15):
        super().__init__()
        self.group = group
        self.layout_template = group.template
        self._scale = scale
        self._hovered = -1
        # Visually flip if height > width
        self._flip = self.layout_template.sheet.height > self.layout_template.sheet.width
        self.setMouseTracking(True)
        self._update_size()

    def set_scale(self, scale: float):
        self._scale = scale
        self._update_size()
        self.update()

    def _update_size(self):
        m = self.MARGIN
        sw = self.layout_template.sheet.height if self._flip else self.layout_template.sheet.width
        sh = self.layout_template.sheet.width if self._flip else self.layout_template.sheet.height
        w = int(sw * self._scale) + m * 2
        h = int(sh * self._scale) + m * 2
        self.setFixedSize(w, h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        m = self.MARGIN
        
        real_sw = self.layout_template.sheet.width
        real_sh = self.layout_template.sheet.height
        disp_sw = real_sh if self._flip else real_sw
        disp_sh = real_sw if self._flip else real_sh
        
        sw = int(disp_sw * self._scale)
        sh = int(disp_sh * self._scale)
        ox, oy = m, m

        # White background for the widget
        p.fillRect(0, 0, self.width(), self.height(), QColor("#ffffff"))

        # Sheet background (waste) - technical grey
        p.fillRect(ox, oy, sw, sh, QColor("#eaeaea"))
        p.setPen(QPen(QColor("#000000"), 1))
        p.drawRect(ox, oy, sw, sh)

        # Outer Dimension (Width)
        p.setPen(QPen(QColor("#000000"), 1))
        p.drawLine(ox, oy - 15, ox + sw, oy - 15)
        p.drawLine(ox, oy - 20, ox, oy - 10)
        p.drawLine(ox + sw, oy - 20, ox + sw, oy - 10)
        
        font_dim = QFont("Segoe UI", 9)
        p.setFont(font_dim)
        fm_dim = QFontMetrics(font_dim)
        tw = fm_dim.horizontalAdvance(str(disp_sw))
        # background wipe for text
        p.fillRect(ox + sw//2 - tw//2 - 4, oy - 22, tw + 8, 14, QColor("#ffffff"))
        p.drawText(ox + sw//2 - tw//2, oy - 11, str(disp_sw))

        # Outer Dimension (Height)
        p.drawLine(ox + sw + 15, oy, ox + sw + 15, oy + sh)
        p.drawLine(ox + sw + 10, oy, ox + sw + 20, oy)
        p.drawLine(ox + sw + 10, oy + sh, ox + sw + 20, oy + sh)
        
        th = fm_dim.horizontalAdvance(str(disp_sh))
        p.fillRect(ox + sw + 10, oy + sh//2 - th//2 - 4, 12, th + 8, QColor("#ffffff"))
        p.save()
        p.translate(ox + sw + 15 + fm_dim.ascent()//2, oy + sh//2 + th//2)
        p.rotate(-90)
        p.drawText(0, 0, str(disp_sh))
        p.restore()

        # Pieces
        font_piece = QFont("Segoe UI", 7)
        fm_piece = QFontMetrics(font_piece)
        font_piece_lbl = QFont("Segoe UI", 8, QFont.Weight.Bold)
        fm_piece_lbl = QFontMetrics(font_piece_lbl)

        for i, pp in enumerate(self.layout_template.placed):
            pp_x = pp.y if self._flip else pp.x
            pp_y = pp.x if self._flip else pp.y
            pp_w = pp.height if self._flip else pp.width
            pp_h = pp.width if self._flip else pp.height

            px = ox + int(pp_x * self._scale)
            py = oy + int(pp_y * self._scale)
            pw = max(2, int(pp_w * self._scale))
            ph = max(2, int(pp_h * self._scale))

            fill = QColor("#ffffff") if i != self._hovered else QColor("#e6f3ff")
            stroke = QColor("#000000")

            p.fillRect(px, py, pw, ph, fill)
            p.setPen(QPen(stroke, 1))
            p.drawRect(px, py, pw, ph)

            # Draw dimensions inside piece
            p.setPen(QColor("#333333"))
            p.setFont(font_piece)
            
            w_str = str(pp_w)
            w_w = fm_piece.horizontalAdvance(w_str)
            if pw > w_w + 4 and ph > fm_piece.height() + 4:
                p.drawText(px + pw//2 - w_w//2, py + fm_piece.ascent() + 2, w_str)
                
            h_str = str(pp_h)
            h_w = fm_piece.horizontalAdvance(h_str)
            if ph > h_w + 4 and pw > fm_piece.height() * 2 + 4:
                p.save()
                p.translate(px + fm_piece.ascent() + 2, py + ph//2 + h_w//2)
                p.rotate(-90)
                p.drawText(0, 0, h_str)
                p.restore()

            # Label / Position
            lbl = pp.piece.label or f"P{i+1}"
            p.setFont(font_piece_lbl)
            lbl_w = fm_piece_lbl.horizontalAdvance(lbl)
            if pw > lbl_w + 8 and ph > fm_piece_lbl.height() * 2.5:
                p.setPen(QColor("#000000"))
                p.drawText(px + pw//2 - lbl_w//2, py + ph//2 + fm_piece_lbl.ascent()//2, lbl)


    def mouseMoveEvent(self, event):
        ox = self.MARGIN
        oy = self.MARGIN
        for i, pp in enumerate(self.layout_template.placed):
            pp_x = pp.y if self._flip else pp.x
            pp_y = pp.x if self._flip else pp.y
            pp_w = pp.height if self._flip else pp.width
            pp_h = pp.width if self._flip else pp.height

            px = ox + int(pp_x * self._scale)
            py = oy + int(pp_y * self._scale)
            pw = int(pp_w * self._scale)
            ph = int(pp_h * self._scale)
            if QRect(px, py, pw, ph).contains(event.pos()):
                if self._hovered != i:
                    self._hovered = i
                    self.update()
                self.setToolTip(
                    f"{pp.piece.label or 'Piece'}\n"
                    f"{pp.width} × {pp.height} mm\n"
                    f"Position: ({pp.x}, {pp.y})\n"
                    f"{'[Rotated]' if pp.rotated else ''}"
                )
                return
        if self._hovered != -1:
            self._hovered = -1
            self.update()
        self.setToolTip("")


class SheetLayoutWidget(QFrame):
    """A container for the canvas and its piece summary table."""
    def __init__(self, group: LayoutGroup, group_index: int, table_data: list, scale: float):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("SheetLayoutWidget { background-color: #ffffff; border: 1px solid #ddd; border-radius: 4px; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel(f"<b>Sheet {group_index}</b> ({group.count}x) — {group.template.sheet.width} × {group.template.sheet.height} mm")
        title.setStyleSheet("font-size: 14px; color: #333;")
        header_layout.addWidget(title)
        
        eff = group.template.efficiency
        eff_label = QLabel(f"Efficiency: {eff:.1f}%")
        eff_label.setStyleSheet("color: #666;")
        header_layout.addStretch()
        header_layout.addWidget(eff_label)
        
        layout.addLayout(header_layout)
        
        # Canvas
        self.canvas = SheetCanvas(group, scale)
        layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Position", "Length [mm]", "Width [mm]", 
            "Total Qty", "Already Cut", "On this Plan", "Remaining Qty"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { border: 1px solid #ccc; background-color: #fff; }
            QHeaderView::section { background-color: #f5f5f5; border: none; border-bottom: 1px solid #ccc; padding: 4px; font-weight: bold; }
        """)
        
        self.table.setRowCount(len(table_data))
        for r, row in enumerate(table_data):
            self.table.setItem(r, 0, QTableWidgetItem(str(row["pos"])))
            self.table.setItem(r, 1, QTableWidgetItem(str(row["length"])))
            self.table.setItem(r, 2, QTableWidgetItem(str(row["width"])))
            
            t_item = QTableWidgetItem(str(row["total"]))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, t_item)
            
            a_item = QTableWidgetItem(str(row["already"]))
            a_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 4, a_item)
            
            op_item = QTableWidgetItem(str(row["on_plan"]))
            op_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 5, op_item)
            
            rem_item = QTableWidgetItem(str(row["remaining"]))
            rem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 6, rem_item)
            
        # Adjust table height to fit contents
        row_height = 24
        header_height = self.table.horizontalHeader().height() or 24
        table_height = header_height + (len(table_data) * row_height) + 2
        self.table.setFixedHeight(table_height)
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        
        layout.addWidget(self.table)
        
    def set_scale(self, scale: float):
        self.canvas.set_scale(scale)


class CutPlanTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_win = parent
        self._scale = 0.14
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Controls bar
        bar = QHBoxLayout()

        bar.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(5, 40)
        self.zoom_slider.setValue(14)
        self.zoom_slider.setFixedWidth(160)
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        bar.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("14%")
        self.zoom_label.setFixedWidth(36)
        bar.addWidget(self.zoom_label)

        bar.addSpacing(20)
        self.stats_label = QLabel("Run optimization to see results.")
        self.stats_label.setStyleSheet("color: #555;")
        bar.addWidget(self.stats_label)
        bar.addStretch()

        layout.addLayout(bar)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.scroll.setStyleSheet("QScrollArea { background-color: #f0f0f0; }")

        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("background-color: #f0f0f0;")
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.canvas_layout.setSpacing(24)

        self.scroll.setWidget(self.canvas_container)
        layout.addWidget(self.scroll)

        self.no_results_label = QLabel("No results yet — press F5 or use Optimize → Run Optimization.")
        self.no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results_label.setStyleSheet("color: #888; font-size: 13pt; padding: 60px;")
        layout.addWidget(self.no_results_label)

    def _on_zoom(self, val):
        self._scale = val / 100
        self.zoom_label.setText(f"{val}%")
        for i in range(self.canvas_layout.count()):
            w = self.canvas_layout.itemAt(i).widget()
            if isinstance(w, SheetLayoutWidget):
                w.set_scale(self._scale)

    def load_from_job(self, job):
        # Clear existing canvases
        while self.canvas_layout.count():
            item = self.canvas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        has_results = bool(job.layouts)
        self.no_results_label.setVisible(not has_results)
        self.scroll.setVisible(has_results)

        if not has_results:
            self.stats_label.setText("No results yet.")
            return

        from core.models import group_identical_layouts
        groups = group_identical_layouts(job.layouts)
        
        # Compute global stats
        piece_stats = {p.id: {"total": p.quantity, "cut": 0} for p in job.pieces}
        
        for i, group in enumerate(groups):
            table_data = []
            
            pieces_on_template = {}
            for pp in group.template.placed:
                if pp.piece.id not in pieces_on_template:
                    pieces_on_template[pp.piece.id] = {"count": 0, "piece": pp.piece}
                pieces_on_template[pp.piece.id]["count"] += 1
                
            for p_id, info in pieces_on_template.items():
                count_per_sheet = info["count"]
                p = info["piece"]
                count_in_group = count_per_sheet * group.count
                
                if p_id in piece_stats:
                    total_qty = piece_stats[p_id]["total"]
                    already_cut = piece_stats[p_id]["cut"]
                    piece_stats[p_id]["cut"] += count_in_group
                else:
                    total_qty = p.quantity
                    already_cut = 0
                
                # Z-Cad format: 5 (5) -> 5 on this plan, 5 total across group
                if group.count > 1:
                    on_plan_str = f"{count_in_group} ({count_per_sheet})"
                else:
                    on_plan_str = f"{count_in_group}"
                    
                table_data.append({
                    "pos": p.label or "Piece",
                    "length": p.width,
                    "width": p.height,
                    "total": total_qty,
                    "already": already_cut,
                    "on_plan": on_plan_str,
                    "remaining": total_qty - already_cut - count_in_group
                })
                
            # Create widget
            widget = SheetLayoutWidget(group, i + 1, table_data, self._scale)
            self.canvas_layout.addWidget(widget)

        placed = job.total_pieces_placed
        needed = job.total_pieces_needed
        eff = job.overall_efficiency
        unplaced = len(job.unplaced)
        txt = (f"✅ {placed}/{needed} pieces placed on {job.sheets_used} sheet(s)  |  "
               f"Overall efficiency: {eff:.1f}%")
        if unplaced:
            txt += f"  ⚠️  {unplaced} piece(s) unplaced — add more sheets!"
        self.stats_label.setText(txt)
        color = "#cc0000" if unplaced else "#1a7a1a"
        self.stats_label.setStyleSheet(f"color: {color}; font-weight: bold;")
