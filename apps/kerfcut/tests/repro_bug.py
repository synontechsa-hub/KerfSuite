import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from core.models import Piece, Sheet, Job
from core.optimizer import optimize, MaxRectsBSSFStrategy

def test_zero_dimension_bug():
    print("Testing 0-dimension piece bug...")
    job = Job(name="Bug Test")
    job.sheets = [Sheet(width=1000, height=1000, quantity=1)]
    # One normal piece, one 0-dimension piece
    job.pieces = [
        Piece(label="Normal", width=100, height=100, quantity=1),
        Piece(label="Zero", width=0, height=100, quantity=1)
    ]
    
    # This should not loop infinitely
    optimize(job, strategy=MaxRectsBSSFStrategy())
    
    print(f"Placed pieces: {len(job.layouts[0].placed) if job.layouts else 0}")
    print(f"Unplaced pieces: {len(job.unplaced)}")
    
    # The bug I suspected: if piece.width == 0, it's skipped in the loop but stays in 'remaining'
    # In core/optimizer.py:
    # 123: if piece.width == 0 or piece.height == 0:
    # 124:     placed_indices.add(i)
    # 125:     continue
    # It continues the loop (over remaining pieces), but doesn't remove the 0-dim piece from 'remaining'.
    # HOWEVER, the 'changed' flag is only set to True if a 'best_i' is found (line 189).
    # Since 0-dim pieces don't update 'best_i', 'changed' will stay False and the 'while changed' loop will exit.
    # SO, it's not an infinite loop, but it is "dead code" (placed_indices is never used).

if __name__ == "__main__":
    test_zero_dimension_bug()
