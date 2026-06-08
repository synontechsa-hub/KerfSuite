"""
KerfCut — CSV IO Tests
Run with: python -m pytest tests/
"""
import sys
import tempfile
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import Piece
from core.csv_io import parse_pieces_from_csv, export_pieces_to_csv

def test_parse_exact_match():
    """Verify standard lowercase exact headers work."""
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", newline="", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(["qty", "width", "height", "label", "canrotate"])
        writer.writerow(["5", "100", "200", "Side A", "yes"])
        path = f.name
        
    pieces = parse_pieces_from_csv(path)
    assert len(pieces) == 1
    assert pieces[0].quantity == 5
    assert pieces[0].width == 100
    assert pieces[0].height == 200
    assert pieces[0].label == "Side A"
    assert pieces[0].can_rotate is True


def test_parse_syncad_export_format():
    """Verify that SynCAD can parse the exact file format it exports."""
    # Write using SynCAD's own exporter
    pieces_to_export = [
        Piece(quantity=10, width=500, height=500, label="Box Bottom", can_rotate=False)
    ]
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", newline="", delete=False) as f:
        path = f.name
        
    export_pieces_to_csv(pieces_to_export, path)
    
    # Now import it back
    imported = parse_pieces_from_csv(path)
    
    assert len(imported) == 1
    assert imported[0].quantity == 10
    assert imported[0].width == 500
    assert imported[0].height == 500
    assert imported[0].label == "Box Bottom"
    assert imported[0].can_rotate is False


def test_parse_messy_headers_and_defaults():
    """Verify capitalization, spaces, and punctuation are ignored, and defaults apply."""
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", newline="", delete=False) as f:
        writer = csv.writer(f)
        # Random formatting and missing some columns
        writer.writerow([" Width (mm) ", " Height_mm ", " Name "])
        writer.writerow(["300", "400", "Door"]) # Missing qty and rotate
        writer.writerow(["50", "50", ""]) # Missing label too
        writer.writerow(["", "", "Bad Row"]) # Should be ignored because w,h=0
        path = f.name
        
    pieces = parse_pieces_from_csv(path)
    
    assert len(pieces) == 2
    assert pieces[0].width == 300
    assert pieces[0].height == 400
    assert pieces[0].label == "Door"
    assert pieces[0].quantity == 1 # Default
    assert pieces[0].can_rotate is True # Default

    assert pieces[1].width == 50
    assert pieces[1].height == 50
    assert pieces[1].label == ""
