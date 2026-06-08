"""
KerfCut — Data Models
"""
from dataclasses import dataclass, field
import uuid


@dataclass
class Sheet:
    """A stock sheet of material available for cutting."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    width: int = 0          # mm
    height: int = 0         # mm
    active: bool = True
    quantity: int = 1       # how many of this sheet type in stock
    buy_price: float = 0.0  # cost price per sheet (€)
    sell_price: float = 0.0  # sell price per sheet (€)
    thickness: float = 0.0  # mm
    label: str = ""         # optional label e.g. "4100x1200"

    @property
    def area(self) -> int:
        return self.width * self.height

    def display_label(self) -> str:
        if self.label:
            return self.label
        return f"{self.width} × {self.height} mm"


@dataclass
class Piece:
    """A rectangular piece that needs to be cut."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    quantity: int = 0       # how many needed
    width: int = 0          # mm
    height: int = 0         # mm
    can_rotate: bool = True  # allow 90° rotation
    label: str = ""         # e.g. "Side panel left"

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class PlacedPiece:
    """A piece that has been placed onto a sheet layout."""
    piece: Piece
    x: int          # mm from left
    y: int          # mm from top
    width: int      # actual placed width (may be rotated)
    height: int     # actual placed height
    rotated: bool = False
    color: tuple = (100, 149, 237)  # cornflower blue default


@dataclass
class SheetLayout:
    """Result of placing pieces onto one physical sheet."""
    sheet: Sheet
    placed: list = field(default_factory=list)  # list of PlacedPiece
    waste_area: int = 0

    @property
    def used_area(self) -> int:
        return sum(p.width * p.height for p in self.placed)

    @property
    def efficiency(self) -> float:
        if self.sheet.area == 0:
            return 0.0
        return self.used_area / self.sheet.area * 100


@dataclass
class LayoutGroup:
    """A grouping of multiple identical SheetLayouts."""
    layouts: list = field(default_factory=list)  # list of SheetLayout

    @property
    def count(self) -> int:
        return len(self.layouts)

    @property
    def template(self) -> SheetLayout:
        return self.layouts[0] if self.layouts else None


def group_identical_layouts(layouts: list[SheetLayout]) -> list[LayoutGroup]:
    """Group a list of layouts by identical sheet dimensions and placed pieces."""
    groups = []
    groups_map = {}

    def signature(layout: SheetLayout) -> tuple:
        placed_tuple = tuple(sorted(
            (p.piece.id, p.x, p.y, p.width, p.height, p.rotated)
            for p in layout.placed
        ))
        return (layout.sheet.id, layout.sheet.width, layout.sheet.height, placed_tuple)

    for layout in layouts:
        sig = signature(layout)
        if sig not in groups_map:
            group = LayoutGroup([layout])
            groups_map[sig] = group
            groups.append(group)
        else:
            groups_map[sig].layouts.append(layout)
            
    return groups


@dataclass
class Job:
    """A complete cutting job."""
    name: str = "New Job"
    customer: str = ""
    notes: str = ""
    material_name: str = ""
    blade_kerf: int = 4     # mm — saw blade thickness
    markup_percent: float = 0.0
    hourly_rate: float = 0.0
    estimated_labor_cost: float = 0.0
    estimated_labor_minutes: float = 0.0
    cut_mode: str = "nested"  # "nested" or "guillotine"

    sheets: list = field(default_factory=list)   # list of Sheet
    pieces: list = field(default_factory=list)   # list of Piece

    # Results (populated after optimization)
    layouts: list = field(default_factory=list)  # list of SheetLayout
    # list of Piece that didn't fit
    unplaced: list = field(default_factory=list)

    @property
    def total_pieces_needed(self) -> int:
        return sum(p.quantity for p in self.pieces if p.quantity > 0 and p.width > 0 and p.height > 0)

    @property
    def total_pieces_placed(self) -> int:
        return sum(len(layout.placed) for layout in self.layouts)

    @property
    def sheets_used(self) -> int:
        return len(self.layouts)

    @property
    def total_material_cost(self) -> float:
        cost = 0.0
        for layout in self.layouts:
            cost += layout.sheet.buy_price
        return cost

    @property
    def total_sell_price(self) -> float:
        """
        Total quote price for the customer.
        Calculated as (Material Sell Price + Labor Cost) + Markup.
        """
        material_base = sum(layout.sheet.sell_price for layout in self.layouts)
        subtotal = material_base + self.estimated_labor_cost
        if self.markup_percent > 0:
            subtotal *= (1 + self.markup_percent / 100)
        return subtotal

    @property
    def total_job_cost(self) -> float:
        """Internal cost to the business (Material Buy Price + Labor)."""
        material_buy = sum(layout.sheet.buy_price for layout in self.layouts)
        return material_buy + self.estimated_labor_cost



    @property
    def overall_efficiency(self) -> float:
        total_used = sum(layout.used_area for layout in self.layouts)
        total_sheet = sum(layout.sheet.area for layout in self.layouts)
        if total_sheet == 0:
            return 0.0
        return total_used / total_sheet * 100
