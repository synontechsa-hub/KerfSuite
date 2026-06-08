"""
KerfCut — Models Tests
Run with: python -m pytest tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import Job, Sheet, Piece, SheetLayout, PlacedPiece

def test_job_computed_properties():
    job = Job(markup_percent=10.0, hourly_rate=50.0, estimated_labor_minutes=60.0, estimated_labor_cost=50.0)

    sheet1 = Sheet(width=1000, height=1000, buy_price=10.0, sell_price=20.0)
    sheet2 = Sheet(width=1000, height=1000, buy_price=15.0, sell_price=25.0)

    l1 = SheetLayout(sheet=sheet1)
    l2 = SheetLayout(sheet=sheet2)
    job.layouts = [l1, l2]

    # total_material_cost = sum(buy_price) = 10 + 15 = 25
    assert job.total_material_cost == 25.0

    # total_job_cost = material_buy (25) + labor (50) = 75.0
    assert job.total_job_cost == 75.0

    # total_sell_price:
    # material_sell = 20 + 25 = 45
    # subtotal = 45 + 50 = 95
    # markup = 10% of 95 = 9.5
    # total = 95 + 9.5 = 104.5
    assert abs(job.total_sell_price - 104.5) < 0.01


def test_job_overall_efficiency():
    job = Job()
    
    # 0 sheets -> 0% efficiency (no divide by zero)
    assert job.overall_efficiency == 0.0

    sheet1 = Sheet(width=100, height=100) # Area 10,000
    l1 = SheetLayout(sheet=sheet1)
    l1.placed.append(PlacedPiece(piece=Piece(), x=0, y=0, width=50, height=100)) # Area 5,000
    
    job.layouts.append(l1)
    
    # 5,000 / 10,000 = 50%
    assert job.overall_efficiency == 50.0


def test_piece_area():
    p = Piece(width=300, height=400)
    assert p.area == 120000


def test_sheet_display_label():
    s1 = Sheet(width=2440, height=1220, label="Plywood")
    assert s1.display_label() == "Plywood"

    s2 = Sheet(width=2440, height=1220)
    assert s2.display_label() == "2440 × 1220 mm"
