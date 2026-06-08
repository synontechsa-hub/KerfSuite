"""
KerfCut — Optimizer Tests
Run with: python -m pytest tests/
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


from core.models import Job, Sheet, Piece
from core.optimizer import optimize


def make_job(sheets, pieces, kerf=4):
    job = Job(blade_kerf=kerf)
    job.sheets = sheets
    job.pieces = pieces
    return job


# ── Basic placement ───────────────────────────────────────────────────────────

def test_single_piece_fits():
    job = make_job(
        sheets=[Sheet(width=1000, height=1000, active=True, quantity=1)],
        pieces=[Piece(quantity=1, width=500, height=500)],
    )
    result = optimize(job)
    assert result.total_pieces_placed == 1
    assert len(result.unplaced) == 0


def test_all_pieces_placed_when_enough_sheet():
    job = make_job(
        sheets=[Sheet(width=2440, height=1220, active=True, quantity=10)],
        pieces=[
            Piece(quantity=20, width=800, height=500),
            Piece(quantity=10, width=400, height=300),
        ],
    )
    result = optimize(job)
    assert result.total_pieces_placed == 30
    assert len(result.unplaced) == 0


def test_unplaced_when_no_space():
    job = make_job(
        sheets=[Sheet(width=100, height=100, active=True, quantity=1)],
        pieces=[Piece(quantity=1, width=500, height=500)],
    )
    result = optimize(job)
    assert result.total_pieces_placed == 0
    assert len(result.unplaced) == 1


def test_piece_rotation_improves_fit():
    """A tall thin piece should fit via rotation if normal orientation doesn't."""
    job = make_job(
        sheets=[Sheet(width=400, height=100, active=True, quantity=1)],
        pieces=[Piece(quantity=1, width=90, height=380, can_rotate=True)],
    )
    result = optimize(job)
    assert result.total_pieces_placed == 1
    placed = result.layouts[0].placed[0]
    assert placed.rotated is True


def test_rotation_disabled_respects_grain():
    """With rotation disabled, a piece that only fits rotated should be unplaced."""
    job = make_job(
        sheets=[Sheet(width=400, height=100, active=True, quantity=1)],
        pieces=[Piece(quantity=1, width=90, height=380, can_rotate=False)],
    )
    result = optimize(job)
    assert result.total_pieces_placed == 0
    assert len(result.unplaced) == 1


# ── Kerf ─────────────────────────────────────────────────────────────────────

def test_kerf_edge_skip():
    # Sheet 1000x1000, kerf 10.
    # Piece 1: 500x1000 -> takes 510 width (leaves 500).
    # Piece 2: 490x1000 -> takes 500 width. Both should fit.
    job = make_job(
        sheets=[Sheet(width=1000, height=1000, active=True, quantity=1)],
        pieces=[
            Piece(quantity=1, width=500, height=1000),
            Piece(quantity=1, width=490, height=1000),
        ],
        kerf=10
    )
    result = optimize(job)
    assert result.total_pieces_placed == 2
    assert len(result.unplaced) == 0


def test_piece_nearly_as_large_as_sheet():
    """A 998mm piece should fit on a 1000mm sheet even with a 4mm kerf.
    The kerf overflows the sheet edge (saw cuts air), so it must not
    prevent placement."""
    job = make_job(
        sheets=[Sheet(width=1000, height=1000, active=True, quantity=1)],
        pieces=[Piece(quantity=1, width=998, height=998)],
        kerf=4,
    )
    result = optimize(job)
    assert result.total_pieces_placed == 1
    assert len(result.unplaced) == 0


def test_piece_exact_sheet_size():
    """A piece exactly the size of the sheet should always fit (kerf overflows)."""
    job = make_job(
        sheets=[Sheet(width=500, height=500, active=True, quantity=1)],
        pieces=[Piece(quantity=1, width=500, height=500)],
        kerf=4,
    )
    result = optimize(job)
    assert result.total_pieces_placed == 1
    assert len(result.unplaced) == 0


# ── Quantity & Constraints ─────────────────────────────────────────────────────────────────────

def test_kerf_reduces_usable_space():
    """With a large kerf, fewer pieces should fit than without."""
    job_no_kerf = make_job(
        sheets=[Sheet(width=500, height=500, active=True, quantity=1)],
        pieces=[Piece(quantity=4, width=240, height=240)],
        kerf=0,
    )
    job_kerf = make_job(
        sheets=[Sheet(width=500, height=500, active=True, quantity=1)],
        pieces=[Piece(quantity=4, width=240, height=240)],
        kerf=20,
    )
    r_no_kerf = optimize(job_no_kerf)
    r_kerf    = optimize(job_kerf)
    assert r_no_kerf.total_pieces_placed >= r_kerf.total_pieces_placed


# ── Sheet quantity ────────────────────────────────────────────────────────────

def test_sheet_quantity_limits_usage():
    """Should not use more sheets than the stated quantity."""
    job = make_job(
        sheets=[Sheet(width=500, height=500, active=True, quantity=1)],
        pieces=[Piece(quantity=100, width=490, height=490)],
    )
    result = optimize(job)
    assert result.sheets_used <= 1


def test_zero_sheet_quantity_is_unavailable():
    """A sheet with zero stock should not be used."""
    job = make_job(
        sheets=[Sheet(width=1000, height=1000, active=True, quantity=0)],
        pieces=[Piece(quantity=1, width=500, height=500)],
    )
    result = optimize(job)
    assert result.sheets_used == 0
    assert result.total_pieces_placed == 0
    assert len(result.unplaced) == 1


def test_multiple_sheet_types():
    job = make_job(
        sheets=[
            Sheet(width=1000, height=500, active=True, quantity=2),
            Sheet(width=2000, height=1000, active=True, quantity=2),
        ],
        pieces=[Piece(quantity=10, width=900, height=450)],
    )
    result = optimize(job)
    assert result.total_pieces_placed == 10


# ── Inactive sheets ───────────────────────────────────────────────────────────

def test_inactive_sheet_not_used():
    job = make_job(
        sheets=[
            Sheet(width=2000, height=2000, active=False, quantity=5),
        ],
        pieces=[Piece(quantity=1, width=500, height=500)],
    )
    result = optimize(job)
    assert result.sheets_used == 0
    assert len(result.unplaced) == 1


# ── Efficiency ────────────────────────────────────────────────────────────────

def test_efficiency_in_range():
    job = make_job(
        sheets=[Sheet(width=2440, height=1220, active=True, quantity=5)],
        pieces=[Piece(quantity=20, width=600, height=400)],
    )
    result = optimize(job)
    assert 0 <= result.overall_efficiency <= 100


def test_full_sheet_efficiency():
    """Pieces that perfectly tile a sheet should yield ~100% efficiency."""
    job = make_job(
        sheets=[Sheet(width=1000, height=1000, active=True, quantity=1)],
        pieces=[Piece(quantity=4, width=500, height=500)],
        kerf=0,
    )
    result = optimize(job)
    assert result.total_pieces_placed == 4
    assert abs(result.overall_efficiency - 100.0) < 1.0


def test_guillotine_strategy():
    from core.optimizer import GuillotineStrategy
    job = make_job(
        sheets=[Sheet(width=1000, height=1000, active=True, quantity=1)],
        pieces=[
            Piece(quantity=1, width=600, height=400),
            Piece(quantity=1, width=400, height=400),
            Piece(quantity=1, width=1000, height=600),
        ],
        kerf=0,
    )
    result = optimize(job, strategy=GuillotineStrategy())
    assert result.total_pieces_placed == 3
    assert len(result.unplaced) == 0
    assert abs(result.overall_efficiency - 100.0) < 1.0
