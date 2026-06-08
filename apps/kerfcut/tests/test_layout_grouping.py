"""Tests for layout grouping and technical cut plan table math."""
import pytest
from core.models import (
    Sheet, Piece, PlacedPiece, SheetLayout, Job,
    LayoutGroup, group_identical_layouts,
)
from core.optimizer import optimize


def _make_placed(piece, x, y, w, h, rotated=False):
    return PlacedPiece(piece=piece, x=x, y=y, width=w, height=h, rotated=rotated)


class TestGroupIdenticalLayouts:
    """Verify that identical layouts get grouped together."""

    def test_identical_layouts_grouped(self):
        sheet = Sheet(id="s1", width=1000, height=500)
        piece = Piece(id="p1", width=200, height=100, quantity=6)
        pp = _make_placed(piece, 0, 0, 200, 100)

        l1 = SheetLayout(sheet=sheet, placed=[pp])
        l2 = SheetLayout(sheet=sheet, placed=[pp])
        l3 = SheetLayout(sheet=sheet, placed=[pp])

        groups = group_identical_layouts([l1, l2, l3])
        assert len(groups) == 1
        assert groups[0].count == 3

    def test_different_layouts_not_grouped(self):
        sheet = Sheet(id="s1", width=1000, height=500)
        p1 = Piece(id="p1", width=200, height=100, quantity=2)
        p2 = Piece(id="p2", width=300, height=150, quantity=2)

        l1 = SheetLayout(sheet=sheet, placed=[_make_placed(p1, 0, 0, 200, 100)])
        l2 = SheetLayout(sheet=sheet, placed=[_make_placed(p2, 0, 0, 300, 150)])

        groups = group_identical_layouts([l1, l2])
        assert len(groups) == 2
        assert groups[0].count == 1
        assert groups[1].count == 1

    def test_different_sheets_not_grouped(self):
        s1 = Sheet(id="s1", width=1000, height=500, buy_price=10)
        s2 = Sheet(id="s2", width=1000, height=500, buy_price=20)
        p1 = Piece(id="p1", width=200, height=100, quantity=2)
        pp = _make_placed(p1, 0, 0, 200, 100)

        l1 = SheetLayout(sheet=s1, placed=[pp])
        l2 = SheetLayout(sheet=s2, placed=[pp])

        groups = group_identical_layouts([l1, l2])
        assert len(groups) == 2

    def test_empty_layouts_list(self):
        groups = group_identical_layouts([])
        assert groups == []

    def test_single_layout(self):
        sheet = Sheet(id="s1", width=1000, height=500)
        l1 = SheetLayout(sheet=sheet, placed=[])
        groups = group_identical_layouts([l1])
        assert len(groups) == 1
        assert groups[0].count == 1

    def test_mixed_identical_and_different(self):
        sheet = Sheet(id="s1", width=1000, height=500)
        p1 = Piece(id="p1", width=200, height=100, quantity=4)
        p2 = Piece(id="p2", width=300, height=150, quantity=1)

        pp1 = _make_placed(p1, 0, 0, 200, 100)
        pp2 = _make_placed(p2, 0, 0, 300, 150)

        l1 = SheetLayout(sheet=sheet, placed=[pp1])
        l2 = SheetLayout(sheet=sheet, placed=[pp1])
        l3 = SheetLayout(sheet=sheet, placed=[pp2])

        groups = group_identical_layouts([l1, l2, l3])
        assert len(groups) == 2
        assert groups[0].count == 2  # pp1 group
        assert groups[1].count == 1  # pp2 group

    def test_template_returns_first_layout(self):
        sheet = Sheet(id="s1", width=1000, height=500)
        l1 = SheetLayout(sheet=sheet, placed=[])
        l2 = SheetLayout(sheet=sheet, placed=[])
        group = LayoutGroup([l1, l2])
        assert group.template is l1


class TestTableQuantityMath:
    """Verify the Already Cut / On this Plan / Remaining math."""

    def test_quantity_tracking_across_groups(self):
        """Simulate 2 groups and verify the running totals are correct."""
        # Setup: 10 pieces total, placed across 2 different sheet groups
        sheet = Sheet(id="s1", width=2000, height=1000, quantity=10)
        piece = Piece(id="p1", width=400, height=300, quantity=10, label="Panel")

        # Group 1: 3 identical sheets, each placing 2 pieces = 6 total
        pp = _make_placed(piece, 0, 0, 400, 300)
        pp2 = _make_placed(piece, 400, 0, 400, 300)
        layouts_g1 = [SheetLayout(sheet=sheet, placed=[pp, pp2]) for _ in range(3)]

        # Group 2: 2 identical sheets, each placing 2 pieces = 4 total
        pp3 = _make_placed(piece, 0, 0, 400, 300)
        pp4 = _make_placed(piece, 0, 300, 400, 300)
        layouts_g2 = [SheetLayout(sheet=sheet, placed=[pp3, pp4]) for _ in range(2)]

        all_layouts = layouts_g1 + layouts_g2
        groups = group_identical_layouts(all_layouts)

        # Build running stats just like cutplan_tab does
        piece_stats = {"p1": {"total": 10, "cut": 0}}
        results = []

        for group in groups:
            pieces_on_template = {}
            for pp in group.template.placed:
                if pp.piece.id not in pieces_on_template:
                    pieces_on_template[pp.piece.id] = {"count": 0, "piece": pp.piece}
                pieces_on_template[pp.piece.id]["count"] += 1

            for p_id, info in pieces_on_template.items():
                count_per_sheet = info["count"]
                count_in_group = count_per_sheet * group.count
                total_qty = piece_stats[p_id]["total"]
                already_cut = piece_stats[p_id]["cut"]
                remaining = total_qty - already_cut - count_in_group
                piece_stats[p_id]["cut"] += count_in_group

                results.append({
                    "total": total_qty,
                    "already": already_cut,
                    "on_plan": count_in_group,
                    "remaining": remaining,
                })

        # Group 1: 0 already, 6 on plan, 4 remaining
        assert results[0]["already"] == 0
        assert results[0]["on_plan"] == 6
        assert results[0]["remaining"] == 4

        # Group 2: 6 already, 4 on plan, 0 remaining
        assert results[1]["already"] == 6
        assert results[1]["on_plan"] == 4
        assert results[1]["remaining"] == 0

    def test_full_optimizer_grouping_integration(self):
        """Run the real optimizer and verify grouping works on its output."""
        job = Job(name="Test", blade_kerf=0)
        job.sheets = [Sheet(id="s1", width=1000, height=500, quantity=5)]
        job.pieces = [Piece(id="p1", width=500, height=500, quantity=5, label="Full")]

        optimize(job)

        # Optimizer fits 2 pieces per sheet (2×500 = 1000), so 3 sheets: 2+2+1
        assert job.total_pieces_placed == 5
        assert len(job.layouts) == 3

        groups = group_identical_layouts(job.layouts)
        # 2 identical 2-piece sheets, plus 1 different 1-piece sheet = 2 groups
        assert len(groups) == 2
        assert groups[0].count == 2  # the 2-piece sheets
        assert groups[1].count == 1  # the 1-piece sheet
