# SynCAD v1.0.3 — Logic Deep-Dive Audit

> **37/37 tests passing** · All core source files reviewed line-by-line  
> Focus: correctness, edge cases, robustness — frontend excluded per request

---

## Executive Summary

The codebase is **well-architected and surprisingly mature for an MVP**. The `core/` ↔ `ui/` separation is clean, the optimizer implements MaxRects BSSF correctly, and persistence round-trips faithfully. That said, I found **16 concrete logic issues** ranging from correctness bugs to robustness gaps that should be resolved before you consider the logic "final." None are showstoppers, but several would cause incorrect results or silent failures in real workshop use.

---

## 1. Optimizer — [optimizer.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py)

### 1.1 ✅ What's Solid

- **MaxRects BSSF** is correctly implemented (split → prune → score cycle)
- **Guillotine strategy** is a proper separate implementation with MAXAS heuristic
- **Strategy pattern** is well-abstracted via `PackingStrategy` ABC — adding new strategies is clean
- **Best-fit sheet selection** (L362–L403) tries all sheet types per round and picks the one that fits most pieces — smart approach
- **Color assignment** works correctly per piece ID

### 1.2 🔴 Kerf Edge-Skip Logic is Fragile

[Lines 134–136](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py#L134-L136) and duplicated at [Lines 149–150](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py#L149-L150), [253–254](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py#L253-L254), [269–270](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py#L269-L270):

```python
pw = piece.width if piece.width == sheet.width and free.x == 0 else piece.width + kerf
ph = piece.height if piece.height == sheet.height and free.y == 0 else piece.height + kerf
```

**The problem:** This only skips kerf when a piece perfectly matches the **full sheet dimension** AND is placed at the sheet edge (x==0 or y==0). But there's a second scenario it misses: a piece placed at position `x` where `x + piece.width == sheet.width` (touching the **right** edge) should also skip the right-side kerf. Same for the bottom edge.

Currently, a piece touching the right or bottom edge still has kerf added, which means:
- The optimizer may reject placements that would physically fit
- Slight material waste overestimation on edge-adjacent pieces

**Additionally**, the condition checks `piece.width == sheet.width`, but after a split, the `free` rect is a sub-rectangle of the original sheet. The check should really be about whether the piece is flush against the **sheet boundary**, not against the free rect's origin. A piece at `free.x == 0` with `piece.width == sheet.width` does work, but a piece at `free.x > 0` touching the right edge of the **sheet** at `free.x + piece.width == sheet.width` does not benefit.

> [!IMPORTANT]
> This is the most significant algorithmic correctness issue. It won't cause wrong results, but it causes sub-optimal packing — the optimizer will sometimes fail to place a piece that would physically fit at a sheet edge. For workshop use, this directly translates to wasted material.

### 1.3 🟡 `Piece.can_rotate` vs `Piece.grain_locked` — Redundant Fields

[models.py L38–40](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py#L38-L40):
```python
can_rotate: bool = True   # allow 90° rotation
grain_locked: bool = False  # if True, cannot rotate
```

These are **logically inverse duplicates**. The optimizer checks both at [L148](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py#L148):
```python
if piece.can_rotate and not piece.grain_locked:
```

If a user sets `can_rotate=True` but `grain_locked=True`, the piece won't rotate — `grain_locked` wins. But there's no enforcement that these stay in sync. If one is set independently of the other (e.g., via CSV import or a persistence edge case), you could get confusing behavior.

**Recommendation:** Pick one. `can_rotate` is cleaner. Add a migration path that sets `can_rotate = not grain_locked` for existing files, then deprecate `grain_locked`.

### 1.4 🟡 Optimizer `O(n² × m)` Complexity — No Issue Today, But Worth Noting

Each iteration of the main loop (L121–L197) scans all remaining pieces × all free rects. With large jobs (hundreds of pieces, many sheets), this could become slow. The current threaded approach in `OptimizerThread` prevents UI freezing, which is good — but there's no progress indication or cancellation mechanism.

### 1.5 🟢 Layout Waste Area Never Computed

[SheetLayout.waste_area](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py#L64) defaults to `0` and is never populated by the optimizer. The `efficiency` property computes from `used_area / sheet.area`, which works, but `waste_area` is misleadingly always `0` — and it gets serialized to saved files as `0`.

Either compute it (`waste_area = sheet.area - used_area`) after optimization, or remove the field.

---

## 2. Data Models — [models.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py)

### 2.1 ✅ What's Solid

- Clean dataclass design, good use of computed properties
- `LayoutGroup` + `group_identical_layouts` is well-designed for the PDF grouping feature
- Cost model properties (`total_sell_price`, `total_job_cost`) are mathematically correct

### 2.2 🔴 `group_identical_layouts` Uses `piece.id` in Signature — Fragile

[Line 98](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py#L98):
```python
placed_tuple = tuple(sorted(
    (p.piece.id, p.x, p.y, p.width, p.height, p.rotated)
    for p in layout.placed
))
```

The grouping signature uses `p.piece.id`. But multiple placed instances of the same `Piece` share the **same** `piece.id` (because the optimizer stores a reference to the original Piece object). This actually works for grouping — two identical sheets will have the same piece IDs at the same positions.

**However**, the signature does NOT include the **sheet ID**. [Line 101](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py#L101):
```python
return (layout.sheet.width, layout.sheet.height, placed_tuple)
```

It compares by `sheet.width` and `sheet.height` — so two different sheet types with the same dimensions but different prices/labels would be grouped together. This could cause incorrect costing in the PDF where the "2x" count on a grouped sheet misrepresents mixed pricing.

> [!WARNING]
> If you add two sheets with identical dimensions but different buy/sell prices (e.g., "MDF 18mm" at R500 and "Plywood 18mm" at R700, both 2440×1220), the grouping will merge their layouts. The PDF table would show incorrect cost data.

**Fix:** Include `layout.sheet.id` (or at minimum `layout.sheet.buy_price, layout.sheet.sell_price`) in the signature tuple.

### 2.3 🟡 `Sheet.width` and `Sheet.height` are `int` — No Sub-mm Precision

Both are declared as `int`. For most workshop use this is fine, but some materials and some international standards use half-mm increments (e.g., 2440.5mm). Not a blocker, but worth being aware of if you expand to European markets.

### 2.4 🟢 `Job.total_pieces_needed` Counts Only `quantity > 0`

[Line 138–139](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py#L138-L139):
```python
return sum(p.quantity for p in self.pieces if p.quantity > 0)
```

This is correct, but the optimizer also filters on `width > 0 and height > 0`. A piece with `quantity=5, width=0, height=100` would be counted in `total_pieces_needed` but would never be placed — resulting in "5/5 pieces placed" never being achievable. Not likely in practice (the UI validates dimensions), but a defensive guard would be:

```python
return sum(p.quantity for p in self.pieces if p.quantity > 0 and p.width > 0 and p.height > 0)
```

---

## 3. Persistence — [persistence.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/persistence.py)

### 3.1 ✅ What's Solid

- Full round-trip for all fields, including layouts, placed pieces, and colors
- Legacy `.ZAD` import handles Latin-1 encoding, tab-delimited parsing, and optional fields
- `_id_or_new()` ensures missing IDs are regenerated on load — good forward compatibility

### 3.2 🔴 `job_to_dict` Persists Layouts but with Independent Sheet Copies

[Lines 72–108](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/persistence.py#L72-L108): Each layout serializes its own copy of the sheet object. On reload, each layout gets an **independent** Sheet instance. This means:

1. If you modify a sheet's price in the `sheets_tab` after loading, the **layout** still references the old sheet data
2. After re-optimizing, the layouts get new sheet references from the pool — but saved files with stale layouts will have disconnected sheet data

This is actually **fine architecturally** (layouts snapshot the sheet state at optimization time), but it can lead to confusion: the Costs tab might show different prices depending on whether it reads from `job.sheets` or `job.layouts[].sheet`.

### 3.3 🟡 `load_zad_file` Overwrites `blade_kerf` Per Sheet Line

[Line 236](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/persistence.py#L236):
```python
job.blade_kerf = int(parts[10])
```

This is inside the `for line in lines` loop — every `Mat.` line overwrites the global `blade_kerf`. If a `.ZAD` file has multiple sheet definitions with different kerfs (unlikely but possible), only the last one wins. The original Z-CAD format stored kerf per-sheet, but SynCAD treats it as a job-level setting. Not a real bug, but worth documenting.

### 3.4 🟡 No File Version Migration Logic

`job_to_dict` writes `"version": "1.0"` but `job_from_dict` never reads or validates it. If you change the schema in a future version (e.g., rename a field, add a required field), there's no mechanism to detect the old format and migrate. Adding a version check now would be cheap insurance.

---

## 4. Authentication & Licensing — [auth.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/auth.py)

### 4.1 ✅ What's Solid

- Fernet encryption for offline tokens — proper choice
- Machine ID binding via MAC + SHA256
- Clock rollback detection with 1-hour tolerance
- Atomic trial increment via Supabase RPC — prevents race conditions
- Dev bypass only works in unfrozen (source) mode — good guard
- Offline fallback with cached trial state

### 4.2 🔴 License Table Allows Anon PATCH — Critical Security Gap

The [supabase_schema.sql](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/supabase_schema.sql) only defines a SELECT policy:
```sql
CREATE POLICY "Allow anon read for verification" ON public.licenses
    FOR SELECT USING (is_active = true);
```

But [auth.py L384–389](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/auth.py#L384-L389) does a PATCH to bind the machine ID:
```python
patch_response = client.patch(
    url, headers=headers,
    params={"id": f"eq.{license_record['id']}"},
    json={"machine_id": current_mid}
)
```

This would be **blocked by RLS** unless you've added an UPDATE policy separately. If the patch silently fails (200 but no rows affected), the license appears valid (the GET succeeded) but the machine binding never persists.

> [!CAUTION]
> Either the PATCH is silently failing in production (meaning machine binding doesn't work), or you've added an UPDATE policy that isn't in the committed SQL — which means anyone with the anon key could unbind/rebind licenses.

**You need** a narrow UPDATE policy:
```sql
CREATE POLICY "Allow anon bind machine" ON public.licenses
    FOR UPDATE USING (machine_id IS NULL OR machine_id = '')
    WITH CHECK (true);
```

### 4.3 🔴 `verify_license` Returns `True` on Force-Trial

[Line 341–343](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/auth.py#L341-L343):
```python
if force_trial_mode_enabled():
    logger.info("Trial mode forced via KERFCUT_FORCE_TRIAL; skipping license verification.")
    return True
```

When `KERFCUT_FORCE_TRIAL` is set, `verify_license()` returns `True` for **any** key, including garbage strings. This bypasses all validation. The intended behavior is probably to skip the license dialog entirely — not to validate fake keys. If the UI calls `verify_license("anything")` in trial mode and gets `True`, it would also call `save_offline_token("anything")` at the call site, potentially creating a fake offline token.

**This only applies when the env var is set**, so it's a dev concern, not a user-facing bug.

### 4.4 🟡 Machine ID Based Only on MAC Address

[Line 76–79](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/auth.py#L76-L79):
```python
mac = str(uuid.getnode())
return hashlib.sha256(mac.encode()).hexdigest()[:16].upper()
```

`uuid.getnode()` can return a random MAC on some systems (VMs, certain Linux configs) and changes if a user swaps network adapters. A workshop PC with a USB Wi-Fi adapter that gets unplugged would generate a different machine ID, potentially locking the user out. Consider also incorporating disk serial or OS-level machine GUID for more stability.

### 4.5 🟡 `increment_trial_run` Called Synchronously After Optimization

[main_window.py L596–598](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/ui/main_window.py#L596-L598): `increment_trial_run()` makes a synchronous HTTP call on the main thread after the optimizer finishes. If the network is slow, the UI freezes for up to 10 seconds (the httpx timeout). This should be done in a background thread.

---

## 5. Cost Model — [models.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py) + [optimizer.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py)

### 5.1 🟡 Labour Estimation is a Placeholder

[optimizer.py L415–423](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/optimizer.py#L415-L423):
```python
job.estimated_labor_minutes = (sheets_count * 5.0) + (pieces_count * 1.0)
```

This is documented as a placeholder in the roadmap. The formula is:
- 5 minutes per sheet (setup/changeover)  
- 1 minute per placed piece (cutting)

For a real workshop, this is roughly in the right ballpark for simple panel saws, but:
- No adjustment for piece size (a 50×50mm cut is not the same as a 2400×1200mm rip)
- No adjustment for material type (acrylic requires slower feeds than MDF)
- The constants are hardcoded in the optimizer, not configurable

**This is acknowledged in the roadmap. Flagging it here for completeness.**

### 5.2 🟢 Markup Applied to Subtotal (Material Sell + Labour) — Correct

The formula in [total_sell_price](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/models.py#L157-L166) is:
```
(sum of sell_prices + labour_cost) × (1 + markup%)
```

This is standard workshop quoting practice. ✅

---

## 6. Material Library — [library.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/library.py)

### 6.1 🟡 UI Dependency in Core Module

`library.py` imports `PyQt6.QtCore.QSettings` — this means it can't be used without PyQt6 installed. Since it's in the `core/` package (which is supposed to be UI-independent), this breaks the architectural separation.

**Fix:** Pass a storage path or use a plain JSON file instead of QSettings.

### 6.2 🟢 Deduplication is Basic But Functional

[add_to_library](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/library.py#L71-L83) checks width × height × thickness × label. This is reasonable. Price changes alone won't trigger a duplicate — that's a design choice, not a bug.

---

## 7. CSV Import/Export — [csv_io.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/csv_io.py)

### 7.1 ✅ Excellent Fuzzy Header Matching

The `normalized_fieldnames` approach (strip all non-alphanumeric, lowercase) means "Width (mm)", "width_mm", "WIDTH", and "Width" all map to the same field. This is genuinely well done.

### 7.2 🟡 Export Format Uses `Area (mm²)` Column — Import Ignores It

[export L60](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/csv_io.py#L60): The export writes an `Area (mm²)` column with comma-formatted numbers (e.g., `"120,000"`). If someone edits this CSV and re-imports it, the area column is harmlessly ignored — but the comma-formatted number could confuse Excel in European locales where commas are decimal separators.

Minor, but worth using a locale-safe format or dropping the area column from export.

### 7.3 🟡 `grain_locked` Field Not Exported or Imported

`export_pieces_to_csv` exports `can_rotate` but not `grain_locked`. Since these are two independent fields (see §1.3), a CSV round-trip would lose grain lock state. Another reason to consolidate these two fields.

---

## 8. PDF Export — [export_pdf.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/export_pdf.py)

### 8.1 ✅ What's Solid

- Professional layout with dimensioned drawings, piece labels, and tables
- Uses `group_identical_layouts` to avoid duplicate pages — smart
- Running piece quantity tracker (`piece_stats`) across groups — the "Already Cut / On This Plan / Remaining" math is correct

### 8.2 🟡 `from core.models import group_identical_layouts` — Relative vs Absolute

[Line 211](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/export_pdf.py#L211):
```python
from core.models import group_identical_layouts
```

This uses an **absolute** import from within the `core` package. It should be:
```python
from .models import group_identical_layouts
```

Same issue at [Line 180](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/export_pdf.py#L180):
```python
from core.settings import get_currency
```

These work because the project root is on `sys.path`, but they break the package encapsulation and would fail if the package were imported from elsewhere.

### 8.3 🟢 Orientation Flip Logic is Correct

[Lines 231–233](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/export_pdf.py#L231-L233): The PDF flips tall sheets to display landscape. The piece coordinate transformation at [L272–276](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/export_pdf.py#L272-L276) correctly swaps x↔y and w↔h. This is the kind of thing that's easy to get wrong — well done.

---

## 9. Settings & Configuration

### 9.1 🟡 `settings.py` and `library.py` Both Import PyQt6 — Core Contamination

Both [settings.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/settings.py) and [library.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/library.py) import `QSettings`. This means running tests that touch these modules requires PyQt6 to be installed. Currently the tests avoid these modules, but it constrains future test expansion.

### 9.2 🟢 Currency Default is `€` — Should Be `R`

[settings.py L11](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/core/settings.py#L11):
```python
return QSettings(APP_AUTHOR, APP_NAME).value("app/currency", "€")
```

Your target market is South African workshops. The default currency should be `R` (Rand), not `€`. A new install will show Euro signs until the user manually changes it.

---

## 10. Undo/Redo — [main_window.py](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/ui/main_window.py)

### 10.1 ✅ Correctly Implemented

- Debounced (500ms timer) to batch rapid changes
- JSON snapshot-based (simple, no diffing) — max 50 states
- `_saved_history_index` tracking means dirty state survives undo/redo cycles
- `_is_undoing` flag prevents history pushes during restore

### 10.2 🟡 `collect_from_ui()` Called in `_push_history` — Subtle Side Effect

[Line 310](file:///d:/Coding/SynonTech/_Development/SynCAD/SynCAD_v1.0.3/ui/main_window.py#L310-L311):
```python
def _push_history(self):
    ...
    self.collect_from_ui()
    self.costs_tab.load_from_job(self.job)
```

This pulls data from the UI into `self.job` and then refreshes the costs tab **every time history is pushed** (which happens on every dirty event after the 500ms debounce). This means the costs tab gets refreshed on every keystroke-batch, which could cause flickering if the costs tab is visible during editing.

---

## 11. Test Coverage

### Current State: 37 tests, all passing

| Module | Tests | Coverage |
|---|---|---|
| Optimizer | 13 | Good — covers rotation, kerf, quantity limits, both strategies |
| Persistence | 9 | Good — round-trip, ZAD import, edge cases |
| Models | 4 | Adequate — cost properties, efficiency |
| CSV I/O | 3 | Good — fuzzy headers, export round-trip |
| Layout Grouping | 8 | Excellent — thorough edge cases |
| Auth | 0 | ❌ No tests |
| Library | 0 | ❌ No tests (requires QSettings mock) |
| PDF Export | 0 | ❌ No tests |

### Missing Test Cases

> [!IMPORTANT]
> These are the gaps most likely to hide bugs:

1. **Optimizer with identical-dimension different-priced sheets** — would expose the grouping signature issue (§2.2)
2. **Kerf edge-skip behavior** — no test validates that pieces at sheet boundaries get correct kerf handling
3. **Persistence version migration** — what happens if you load a v2.0 file in v1.0?
4. **Piece with `can_rotate=True, grain_locked=True`** — behavior is defined but not tested
5. **Optimizer with a single piece that perfectly matches sheet dimensions** — edge case for kerf skip logic
6. **CSV import with BOM markers** — `utf-8-sig` is handled, but what about UTF-16 or Excel-generated CSVs?

---

## 12. Priority-Ranked Summary of All Issues

| # | Severity | Module | Issue | Section |
|---|---|---|---|---|
| 1 | 🔴 Critical | optimizer.py | Kerf edge-skip only handles left/top edges, misses right/bottom | §1.2 |
| 2 | 🔴 Critical | auth.py / SQL | License PATCH requires UPDATE policy not in schema | §4.2 |
| 3 | 🔴 Critical | models.py | Layout grouping signature ignores sheet ID/price — merges different materials | §2.2 |
| 4 | 🔴 Important | auth.py | `verify_license` returns True for any key when force-trial enabled | §4.3 |
| 5 | 🟡 Medium | models.py | `can_rotate` and `grain_locked` are redundant inverse fields | §1.3 |
| 6 | 🟡 Medium | models.py | `waste_area` is never computed, always serialized as 0 | §1.5 |
| 7 | 🟡 Medium | models.py | `total_pieces_needed` counts 0-dimension pieces the optimizer skips | §2.4 |
| 8 | 🟡 Medium | persistence.py | No file version migration/validation logic | §3.4 |
| 9 | 🟡 Medium | auth.py | Machine ID relies solely on MAC address — unstable on VMs/adapter changes | §4.4 |
| 10 | 🟡 Medium | main_window.py | `increment_trial_run` blocks UI thread with synchronous HTTP call | §4.5 |
| 11 | 🟡 Medium | library.py, settings.py | PyQt6 dependency in core package breaks architectural separation | §6.1, §9.1 |
| 12 | 🟡 Medium | export_pdf.py | Absolute imports in core package (`from core.x`) instead of relative | §8.2 |
| 13 | 🟡 Medium | csv_io.py | `grain_locked` field not exported/imported | §7.3 |
| 14 | 🟡 Low | settings.py | Default currency is `€`, should be `R` for SA market | §9.2 |
| 15 | 🟢 Minor | persistence.py | ZAD import overwrites blade_kerf per sheet line | §3.3 |
| 16 | 🟢 Minor | csv_io.py | Comma-formatted area column could confuse European Excel | §7.2 |

---

## 13. What's NOT Wrong

I want to explicitly call out things that are **well done** and shouldn't be changed:

- ✅ **Strategy pattern** for optimizer — clean ABC, easy to extend
- ✅ **Best-fit sheet selection** — trying all sheet types per round is smart
- ✅ **Undo/redo** — snapshot-based approach is simple and correct
- ✅ **Legacy .ZAD import** — handles encoding, optional fields, inactive sheets gracefully
- ✅ **CSV fuzzy header matching** — genuinely clever normalization
- ✅ **Threaded optimization** — prevents UI freezing
- ✅ **Offline grace period** — Fernet encryption with machine binding is a solid approach
- ✅ **Layout grouping for PDF** — the "Already Cut / On Plan / Remaining" tracking is mathematically correct
- ✅ **PDF orientation flip** — coordinate transform for tall sheets is correct
- ✅ **Color palette** — 12 distinct colors, wraps cleanly on large piece lists
