"""
KerfCut — PDF Export
Generates a professional cut plan + cost summary PDF.
Requires: reportlab
"""


def _add_page_header(story, job, normal_style):
    """Adds the standard job header to the top of a page."""
    import datetime
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    
    date_str = datetime.date.today().strftime("%d.%m.%Y")
    
    left_data = []
    left_data.append([Paragraph("Job:", normal_style), Paragraph(job.name, normal_style)])
    if job.customer:
        left_data.append([Paragraph("Customer:", normal_style), Paragraph(job.customer, normal_style)])
    if job.material_name:
        left_data.append([Paragraph("Material:", normal_style), Paragraph(job.material_name, normal_style)])
    if job.notes:
        left_data.append([Paragraph("Notes:", normal_style), Paragraph(job.notes, normal_style)])
        
    left_table = Table(left_data, colWidths=[20*mm, 100*mm])
    left_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (1, 0), (1, -1), 0.5, colors.black),
    ]))
    
    right_data = [[Paragraph(f"Date: {date_str}", normal_style)]]
    right_table = Table(right_data, colWidths=[40*mm])
    right_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
    ]))
    
    header_table = Table([[left_table, right_table]], colWidths=[130*mm, 50*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 8*mm))


def export_pdf(job, filepath: str, currency: str = "R") -> None:
    """Export job results to a PDF report."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer, HRFlowable, PageBreak)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.graphics.shapes import Drawing, Rect as RLRect, String, Line, Group
        from reportlab.pdfbase.pdfmetrics import stringWidth
    except ImportError:
        raise ImportError("reportlab is required for PDF export. Install with: pip install reportlab")

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceAfter=2)
    normal = styles["Normal"]
    warn_style = ParagraphStyle("warn", parent=normal, textColor=colors.red)

    story = []

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    story.append(Paragraph("Cut Plan Instructions", title_style))
    story.append(Spacer(1, 4*mm))
    _add_page_header(story, job, normal)

    # Stock Sheets Table
    story.append(Paragraph("Stock Sheets Available", h2))
    stock_data = [["Dimensions (mm)", "Available Qty", "Active"]]
    for s in job.sheets:
        stock_data.append([
            f"{s.width} x {s.height}",
            str(s.quantity),
            "Yes" if s.active else "No"
        ])
    
    st_table = Table(stock_data, colWidths=[60*mm, 30*mm, 20*mm])
    st_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fcfcfc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(st_table)
    story.append(Spacer(1, 6*mm))

    # Overall Piece List
    story.append(Paragraph("Pieces Required", h2))
    global_piece_data = [["#", "Label", "Qty", "Width (mm)", "Height (mm)", "Rotate"]]
    for i, p in enumerate(job.pieces):
        if p.quantity > 0:
            global_piece_data.append([
                str(i + 1),
                p.label or "—",
                str(p.quantity),
                str(p.width),
                str(p.height),
                "Yes" if p.can_rotate else "No",
            ])

    pt = Table(global_piece_data, colWidths=[10*mm, 60*mm, 15*mm, 30*mm, 30*mm, 15*mm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a9f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ]))
    story.append(pt)

    if job.unplaced:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(
            f"⚠ {len(job.unplaced)} piece(s) could not be placed — add more sheets.",
            warn_style
        ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: SUMMARY & STATISTICS
    # =========================================================================
    story.append(Paragraph("Job Statistics & Costs", title_style))
    story.append(Spacer(1, 4*mm))
    _add_page_header(story, job, normal)

    story.append(Paragraph("Statistics", h2))
    summary_data = [
        ["Sheets used", str(job.sheets_used)],
        ["Pieces placed", f"{job.total_pieces_placed} / {job.total_pieces_needed}"],
        ["Overall efficiency", f"{job.overall_efficiency:.1f}%"],
        ["Blade kerf", f"{job.blade_kerf} mm"],
    ]
    
    t = Table(summary_data, colWidths=[60*mm, 60*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8f8f8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    if job.total_material_cost > 0 or job.hourly_rate > 0:
        story.append(Paragraph("Costs", h2))
        cost_data = []
        if job.total_material_cost > 0:
            cost_data.append(["Material cost", f"{currency} {job.total_material_cost:.2f}"])
        if job.hourly_rate > 0:
            cost_data.append(["Labour cost", f"{currency} {job.estimated_labor_cost:.2f}"])
            cost_data.append(["Est. labour time", f"{job.estimated_labor_minutes:.0f} min"])
        if job.total_sell_price > 0:
            cost_data.append(["Sell price (incl. markup)", f"{currency} {job.total_sell_price:.2f}"])
            
        tc = Table(cost_data, colWidths=[60*mm, 60*mm])
        tc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e6ffe6")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f7fdf7")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tc)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3+: CUT PLANS
    # =========================================================================
    from .models import group_identical_layouts
    groups = group_identical_layouts(job.layouts)
    piece_stats = {p.id: {"total": p.quantity, "cut": 0} for p in job.pieces}

    page_w = 175 * mm  # usable width slightly reduced for margins
    
    for idx, group in enumerate(groups):
        _add_page_header(story, job, normal)
        
        layout = group.template
        
        eff = layout.efficiency
        story.append(Paragraph(
            f"Sheet {idx+1} ({group.count}x): {layout.sheet.width} × {layout.sheet.height} mm "
            f"— {len(layout.placed)} pieces per sheet — Efficiency: {eff:.1f}%",
            h2
        ))
        story.append(Spacer(1, 2*mm))

        # Determine if we should visually flip it so the long edge is horizontal
        flip = layout.sheet.height > layout.sheet.width
        disp_sw = layout.sheet.height if flip else layout.sheet.width
        disp_sh = layout.sheet.width if flip else layout.sheet.height

        # Scale to fit page width
        scale = min(page_w / disp_sw, 100*mm / disp_sh)
        dw = disp_sw * scale
        dh = disp_sh * scale
        
        m_left = 0 * mm
        m_bottom = 0 * mm
        m_top = 8 * mm
        m_right = 10 * mm

        d = Drawing(dw + m_left + m_right, dh + m_bottom + m_top)

        # Sheet background (waste)
        d.add(RLRect(m_left, m_bottom, dw, dh, fillColor=colors.HexColor("#eaeaea"), strokeColor=colors.black, strokeWidth=1))

        # Outer Dimension (Width at top)
        d.add(Line(m_left, m_bottom + dh + 3*mm, m_left + dw, m_bottom + dh + 3*mm, strokeColor=colors.black, strokeWidth=0.5))
        d.add(Line(m_left, m_bottom + dh + 1*mm, m_left, m_bottom + dh + 5*mm, strokeColor=colors.black, strokeWidth=0.5))
        d.add(Line(m_left + dw, m_bottom + dh + 1*mm, m_left + dw, m_bottom + dh + 5*mm, strokeColor=colors.black, strokeWidth=0.5))
        w_str = str(disp_sw)
        tw = stringWidth(w_str, "Helvetica", 7)
        d.add(RLRect(m_left + dw/2 - tw/2 - 1*mm, m_bottom + dh + 2*mm, tw + 2*mm, 3*mm, fillColor=colors.white, strokeWidth=0))
        d.add(String(m_left + dw/2 - tw/2, m_bottom + dh + 2.5*mm, w_str, fontSize=7, fontName="Helvetica", fillColor=colors.black))

        # Outer Dimension (Height at right)
        d.add(Line(m_left + dw + 3*mm, m_bottom, m_left + dw + 3*mm, m_bottom + dh, strokeColor=colors.black, strokeWidth=0.5))
        d.add(Line(m_left + dw + 1*mm, m_bottom, m_left + dw + 5*mm, m_bottom, strokeColor=colors.black, strokeWidth=0.5))
        d.add(Line(m_left + dw + 1*mm, m_bottom + dh, m_left + dw + 5*mm, m_bottom + dh, strokeColor=colors.black, strokeWidth=0.5))
        h_str = str(disp_sh)
        th = stringWidth(h_str, "Helvetica", 7)
        d.add(RLRect(m_left + dw + 2*mm, m_bottom + dh/2 - th/2 - 1*mm, 3*mm, th + 2*mm, fillColor=colors.white, strokeWidth=0))
        # rotate string
        g = Group(String(0, 0, h_str, fontSize=7, fontName="Helvetica", fillColor=colors.black))
        g.translate(m_left + dw + 2.5*mm, m_bottom + dh/2 + th/2)
        g.rotate(-90)
        d.add(g)

        for i, pp in enumerate(layout.placed):
            pp_x = pp.y if flip else pp.x
            pp_y = pp.x if flip else pp.y
            pp_w = pp.height if flip else pp.width
            pp_h = pp.width if flip else pp.height

            x = m_left + pp_x * scale
            # Flip Y: PDF coords start bottom-left
            y = m_bottom + dh - (pp_y + pp_h) * scale
            w = pp_w * scale
            h = pp_h * scale

            # Pieces are white with black borders
            d.add(RLRect(x, y, w, h, fillColor=colors.white, strokeColor=colors.black, strokeWidth=0.5))

            # Dimensions inside piece
            if w > 8*mm and h > 4*mm:
                pw_str = str(pp_w)
                pw_w = stringWidth(pw_str, "Helvetica", 5)
                if w > pw_w + 2*mm:
                    d.add(String(x + w/2 - pw_w/2, y + h - 2*mm, pw_str, fontSize=5, fontName="Helvetica", fillColor=colors.HexColor("#333333")))
                
                ph_str = str(pp_h)
                ph_w = stringWidth(ph_str, "Helvetica", 5)
                if h > ph_w + 2*mm and w > 4*mm:
                    g2 = Group(String(0, 0, ph_str, fontSize=5, fontName="Helvetica", fillColor=colors.HexColor("#333333")))
                    g2.translate(x + 1.5*mm, y + h/2 + ph_w/2)
                    g2.rotate(-90)
                    d.add(g2)

            # Label
            lbl = pp.piece.label or f"P{i+1}"
            font_size = max(5, min(7, int(h * 0.25)))
            lbl_w = stringWidth(lbl, "Helvetica-Bold", font_size)
            if w > lbl_w + 1*mm and h > font_size + 2*mm:
                d.add(String(x + w/2 - lbl_w/2, y + h/2 - font_size/2.5, lbl,
                             fontSize=font_size, fontName="Helvetica-Bold", fillColor=colors.black))

        story.append(d)
        story.append(Spacer(1, 4*mm))
        
        # Create Summary Table for this sheet layout
        table_data = [["Position", "Length [mm]", "Width [mm]", "Total Qty", "Already Cut", "On this Plan", "Remaining"]]
        
        pieces_on_template = {}
        for pp in layout.placed:
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
            
            if group.count > 1:
                on_plan_str = f"{count_in_group} ({count_per_sheet})"
            else:
                on_plan_str = f"{count_in_group}"
                
            table_data.append([
                p.label or "Piece",
                str(p.width),
                str(p.height),
                str(total_qty),
                str(already_cut),
                on_plan_str,
                str(total_qty - already_cut - count_in_group)
            ])
            
        st = Table(table_data, colWidths=[40*mm, 20*mm, 20*mm, 18*mm, 22*mm, 25*mm, 20*mm])
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fcfcfc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(st)
        story.append(PageBreak())

    doc.build(story)
