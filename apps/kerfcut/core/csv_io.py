"""
KerfCut — CSV Input/Output
Handles parsing of pieces from CSV, and exporting pieces to CSV.
"""
import csv
from core.models import Piece
import re

def _safe_int(val) -> int:
    """Safely convert string/float inputs to int, handling whitespace and decimals."""
    if not val: return 0
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return 0

def parse_pieces_from_csv(filepath: str) -> list[Piece]:
    """
    Parse a CSV file and return a list of Piece objects.
    Raises Exception if parsing fails.
    """
    pieces = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        
        normalized_fieldnames = {}
        if reader.fieldnames:
            for fn in reader.fieldnames:
                if fn:
                    norm = re.sub(r'[^a-zA-Z0-9]', '', fn).lower()
                    normalized_fieldnames[norm] = fn

        for row in reader:
            def get_val(*keys, default=""):
                for k in keys:
                    if k in normalized_fieldnames:
                        val = row.get(normalized_fieldnames[k])
                        if val is not None and str(val).strip() != "":
                            return val
                return default

            qty = _safe_int(get_val("qty", "quantity", default=1))
            w = _safe_int(get_val("width", "w", "widthmm", default=0))
            h = _safe_int(get_val("height", "h", "heightmm", default=0))
            label = get_val("label", "name", default="")
            
            rot_val = str(get_val("canrotate", "rotate", default="yes")).lower()
            rotate = rot_val not in ("no", "0", "false")
            
            if w > 0 and h > 0:
                pieces.append(Piece(quantity=max(qty, 1), width=w, height=h, label=label, can_rotate=rotate))
    return pieces

def export_pieces_to_csv(pieces: list[Piece], filepath: str) -> None:
    """
    Export a list of pieces to a CSV file.
    """
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["#", "Label", "Qty", "Width (mm)", "Height (mm)", "Area (mm²)", "Can Rotate"])
        for i, p in enumerate(pieces):
            if p.quantity > 0:
                w.writerow([
                    i + 1, 
                    p.label, 
                    p.quantity,
                    p.width, 
                    p.height, 
                    str(p.area),
                    "Yes" if p.can_rotate else "No"
                ])
