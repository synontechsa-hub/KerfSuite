"""
KerfCut — MaxRects Bin-Packing Algorithm

Implements the MAXRECTS algorithm (Jukka Jylänki, 2010).
This is significantly better than simple guillotine cuts.

Heuristic used: Best Short Side Fit (BSSF) — places each piece
into the free rectangle that minimises the shorter leftover side.
"""
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass
from .models import Sheet, Piece, PlacedPiece, Job


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self):
        return self.w * self.h

    def contains(self, other: "Rect") -> bool:
        return (self.x <= other.x and self.y <= other.y and
                self.x + self.w >= other.x + other.w and
                self.y + self.h >= other.y + other.h)




class PackingStrategy(ABC):
    """Abstract base class for all cut optimization strategies."""
    
    @abstractmethod
    def pack_sheet(self, sheet: Sheet, pieces_flat: list[tuple["Piece", int]], kerf: int) -> tuple[list[PlacedPiece], list[tuple["Piece", int]]]:
        """
        Pack as many pieces as possible onto one sheet.
        Returns (placed_pieces, remaining_pieces)
        """
        pass


class MaxRectsBSSFStrategy(PackingStrategy):
    """
    MaxRects algorithm using Best Short Side Fit (BSSF) heuristic.
    Places each piece into the free rectangle that minimises the shorter leftover side.
    """
    
    def _split_rect(self, free: Rect, placed: Rect) -> list[Rect]:
        """Split a free rectangle around a placed rectangle — guillotine split."""
        result = []
        # Right of placed
        if placed.x + placed.w < free.x + free.w:
            result.append(Rect(
                placed.x + placed.w, free.y,
                free.x + free.w - (placed.x + placed.w), free.h
            ))
        # Above placed (top remainder)
        if placed.y + placed.h < free.y + free.h:
            result.append(Rect(
                free.x, placed.y + placed.h,
                free.w, free.y + free.h - (placed.y + placed.h)
            ))
        # Left of placed
        if free.x < placed.x:
            result.append(Rect(
                free.x, free.y,
                placed.x - free.x, free.h
            ))
        # Below placed
        if free.y < placed.y:
            result.append(Rect(
                free.x, free.y,
                free.w, placed.y - free.y
            ))
        return result

    def _prune_free_rects(self, free_rects: list[Rect]) -> list[Rect]:
        """Remove any free rectangle fully contained within another."""
        to_remove = set()
        n = len(free_rects)
        for i in range(n):
            if i in to_remove:
                continue
            a = free_rects[i]
            for j in range(i + 1, n):
                if j in to_remove:
                    continue
                b = free_rects[j]
                if a.contains(b):
                    to_remove.add(j)
                elif b.contains(a):
                    to_remove.add(i)
                    break
        return [r for i, r in enumerate(free_rects) if i not in to_remove]

    def _score_bssf(self, free: Rect, pw: int, ph: int) -> tuple[int, int]:
        """Best Short Side Fit score — lower is better."""
        leftover_x = free.w - pw
        leftover_y = free.h - ph
        short = min(leftover_x, leftover_y)
        long_ = max(leftover_x, leftover_y)
        return (short, long_)

    def pack_sheet(self, sheet: Sheet, pieces_flat: list[tuple["Piece", int]], kerf: int) -> tuple[list[PlacedPiece], list[tuple["Piece", int]]]:
        """
        Pack as many pieces as possible onto one sheet using MaxRects BSSF.
        """
        # Inflate the virtual sheet by kerf so that pieces at the edges
        # naturally "overflow" — the kerf beyond the sheet boundary is
        # just the saw blade cutting air, which is physically correct.
        free_rects = [Rect(0, 0, sheet.width + kerf, sheet.height + kerf)]
        placed_pieces: list[PlacedPiece] = []
        # Filter out invalid pieces upfront
        remaining = [p for p in pieces_flat if p[0].width > 0 and p[0].height > 0]

        # Sort by area descending for better packing
        remaining.sort(key=lambda x: x[0].width * x[0].height, reverse=True)

        changed = True
        while changed and remaining:
            changed = False
            best_score = (float('inf'), float('inf'))
            best_i = -1
            best_rect_i = -1
            best_pw = 0
            best_ph = 0
            best_rotated = False

            for i, (piece, _) in enumerate(remaining):

                for ri, free in enumerate(free_rects):
                    # Every piece reserves piece_dim + kerf in the virtual sheet
                    pw = piece.width + kerf
                    ph = piece.height + kerf
                    
                    if pw <= free.w and ph <= free.h:
                        score = self._score_bssf(free, pw, ph)
                        if score < best_score:
                            best_score = score
                            best_i = i
                            best_rect_i = ri
                            best_pw = pw
                            best_ph = ph
                            best_rotated = False

                    # Try rotated
                    if piece.can_rotate:
                        pw2 = piece.height + kerf
                        ph2 = piece.width + kerf
                        if pw2 != pw or ph2 != ph:  # skip if same dimensions
                            if pw2 <= free.w and ph2 <= free.h:
                                score = self._score_bssf(free, pw2, ph2)
                                if score < best_score:
                                    best_score = score
                                    best_i = i
                                    best_rect_i = ri
                                    best_pw = pw2
                                    best_ph = ph2
                                    best_rotated = True

            if best_i == -1:
                break  # Nothing more fits

            piece, _ = remaining[best_i]
            free = free_rects[best_rect_i]
            placed = Rect(free.x, free.y, best_pw, best_ph)

            # Actual piece dimensions (without kerf for drawing)
            draw_w = piece.height if best_rotated else piece.width
            draw_h = piece.width if best_rotated else piece.height

            placed_pieces.append(PlacedPiece(
                piece=piece,
                x=free.x,
                y=free.y,
                width=draw_w,
                height=draw_h,
                rotated=best_rotated,
            ))

            # Split free rectangles
            new_free = []
            for ri, fr in enumerate(free_rects):
                # Check overlap with placed rect
                if not (placed.x >= fr.x + fr.w or
                        placed.x + placed.w <= fr.x or
                        placed.y >= fr.y + fr.h or
                        placed.y + placed.h <= fr.y):
                    new_free.extend(self._split_rect(fr, placed))
                else:
                    new_free.append(fr)

            free_rects = self._prune_free_rects(new_free)

            remaining.pop(best_i)
            changed = True

        return placed_pieces, remaining


class GuillotineStrategy(PackingStrategy):
    """
    Guillotine algorithm using MAXAS (Maximize Area of Split) heuristic.
    Enforces edge-to-edge cuts.
    """
    def _split_rect_guillotine(self, free: Rect, pw: int, ph: int) -> list[Rect]:
        """Split a free rectangle around a placed rectangle located at bottom-left (free.x, free.y) into exactly two non-overlapping rectangles."""
        w = free.w - pw
        h = free.h - ph
        
        area_horiz = max(w * ph, free.w * h)
        area_vert = max(pw * h, w * free.h)
        
        result = []
        if area_horiz > area_vert:
            # Horizontal split produces a larger single remaining chunk
            if w > 0 and ph > 0:
                result.append(Rect(free.x + pw, free.y, w, ph))
            if free.w > 0 and h > 0:
                result.append(Rect(free.x, free.y + ph, free.w, h))
        else:
            # Vertical split
            if pw > 0 and h > 0:
                result.append(Rect(free.x, free.y + ph, pw, h))
            if w > 0 and free.h > 0:
                result.append(Rect(free.x + pw, free.y, w, free.h))
                
        return result

    def pack_sheet(self, sheet: Sheet, pieces_flat: list[tuple["Piece", int]], kerf: int) -> tuple[list[PlacedPiece], list[tuple["Piece", int]]]:
        # Inflate the virtual sheet by kerf (same approach as MaxRects)
        free_rects = [Rect(0, 0, sheet.width + kerf, sheet.height + kerf)]
        placed_pieces: list[PlacedPiece] = []
        remaining = [p for p in pieces_flat if p[0].width > 0 and p[0].height > 0]

        # Sort by area descending for better packing
        remaining.sort(key=lambda x: x[0].width * x[0].height, reverse=True)

        changed = True
        while changed and remaining:
            changed = False
            best_score = (float('inf'), float('inf'))
            best_i = -1
            best_rect_i = -1
            best_pw = 0
            best_ph = 0
            best_rotated = False

            for i, (piece, _) in enumerate(remaining):

                for ri, free in enumerate(free_rects):
                    # Every piece reserves piece_dim + kerf in the virtual sheet
                    pw = piece.width + kerf
                    ph = piece.height + kerf
                    if pw <= free.w and ph <= free.h:
                        leftover_x = free.w - pw
                        leftover_y = free.h - ph
                        score = (min(leftover_x, leftover_y), max(leftover_x, leftover_y))
                        if score < best_score:
                            best_score = score
                            best_i = i
                            best_rect_i = ri
                            best_pw = pw
                            best_ph = ph
                            best_rotated = False

                    # Try rotated
                    if piece.can_rotate:
                        pw2 = piece.height + kerf
                        ph2 = piece.width + kerf
                        if pw2 != pw or ph2 != ph:
                            if pw2 <= free.w and ph2 <= free.h:
                                leftover_x = free.w - pw2
                                leftover_y = free.h - ph2
                                score = (min(leftover_x, leftover_y), max(leftover_x, leftover_y))
                                if score < best_score:
                                    best_score = score
                                    best_i = i
                                    best_rect_i = ri
                                    best_pw = pw2
                                    best_ph = ph2
                                    best_rotated = True

            if best_i == -1:
                break

            piece, _ = remaining[best_i]
            free = free_rects[best_rect_i]

            draw_w = piece.height if best_rotated else piece.width
            draw_h = piece.width if best_rotated else piece.height

            placed_pieces.append(PlacedPiece(
                piece=piece,
                x=free.x,
                y=free.y,
                width=draw_w,
                height=draw_h,
                rotated=best_rotated,
            ))

            new_free = self._split_rect_guillotine(free, best_pw, best_ph)
            free_rects.pop(best_rect_i)
            free_rects.extend(new_free)

            remaining.pop(best_i)
            changed = True

        return placed_pieces, remaining

# Distinct colors for pieces
PIECE_COLORS = [
    (100, 149, 237),  # cornflower blue
    (144, 238, 144),  # light green
    (255, 182, 193),  # light pink
    (255, 218, 185),  # peach
    (221, 160, 221),  # plum
    (135, 206, 235),  # sky blue
    (255, 255, 153),  # light yellow
    (188, 143, 143),  # rosy brown
    (152, 251, 152),  # pale green
    (173, 216, 230),  # light blue
    (255, 160, 122),  # light salmon
    (240, 230, 140),  # khaki
]


def optimize(job: "Job", strategy: PackingStrategy | None = None) -> "Job":
    """
    Run the optimization on a job using the provided strategy.
    Populates job.layouts and job.unplaced.
    Returns the modified job.
    """
    from .models import SheetLayout
    
    if strategy is None:
        strategy = MaxRectsBSSFStrategy()

    job.layouts = []
    job.unplaced = []

    # Collect active sheets (respecting quantity) — track available counts per sheet type
    sheet_pool: dict[str, tuple[Sheet, int]] = {}
    for sheet in job.sheets:
        if sheet.active and sheet.width > 0 and sheet.height > 0:
            qty = max(sheet.quantity, 0)
            if qty > 0:
                sheet_pool[sheet.id] = (sheet, qty)

    # Expand pieces by quantity
    pieces_flat: list[tuple[Piece, int]] = []
    color_map: dict[str, tuple] = {}
    for idx, piece in enumerate(job.pieces):
        if piece.quantity > 0 and piece.width > 0 and piece.height > 0:
            color = PIECE_COLORS[idx % len(PIECE_COLORS)]
            color_map[piece.id] = color
            for _ in range(piece.quantity):
                pieces_flat.append((piece, idx))

    remaining = pieces_flat

    # Best-fit sheet selection: try all sheet types each round, pick the best
    while remaining and sheet_pool:
        best_layout = None
        best_sheet_id = None
        best_remaining = remaining
        best_placed_count = 0
        best_efficiency = -1.0

        for sid, (sheet, qty) in sheet_pool.items():
            if qty <= 0:
                continue
            placed, leftover = strategy.pack_sheet(sheet, list(remaining), job.blade_kerf)
            if not placed:
                continue
            # Score: prefer more pieces placed; tie-break by efficiency
            used_area = sum(p.width * p.height for p in placed)
            eff = used_area / sheet.area if sheet.area > 0 else 0
            if (len(placed) > best_placed_count or
                    (len(placed) == best_placed_count and eff > best_efficiency)):
                best_layout = SheetLayout(sheet=sheet, placed=placed)
                best_sheet_id = sid
                best_remaining = leftover
                best_placed_count = len(placed)
                best_efficiency = eff

        if best_layout is None:
            break  # No sheet type could fit any remaining piece

        # Assign colors and record the layout
        for pp in best_layout.placed:
            pp.color = color_map.get(pp.piece.id, (180, 180, 180))
        
        best_layout.waste_area = best_layout.sheet.area - best_layout.used_area
        job.layouts.append(best_layout)

        remaining = best_remaining

        # Consume one sheet from the pool
        sheet_obj, qty = sheet_pool[best_sheet_id]
        qty -= 1
        if qty <= 0:
            del sheet_pool[best_sheet_id]
        else:
            sheet_pool[best_sheet_id] = (sheet_obj, qty)

    unplaced_dict = {}

    for p, _ in remaining:
        if p.id not in unplaced_dict:
            p_copy = copy.copy(p)
            p_copy.quantity = 0
            unplaced_dict[p.id] = p_copy
        unplaced_dict[p.id].quantity += 1
    job.unplaced = list(unplaced_dict.values())

    # Simple labor estimation: 5 min per sheet + 1 min per placed piece
    sheets_count = len(job.layouts)
    pieces_count = sum(len(l.placed) for l in job.layouts)
    job.estimated_labor_minutes = (sheets_count * 5.0) + (pieces_count * 1.0)
    
    if job.hourly_rate > 0:
        job.estimated_labor_cost = (job.estimated_labor_minutes / 60.0) * job.hourly_rate
    else:
        job.estimated_labor_cost = 0.0

    return job
