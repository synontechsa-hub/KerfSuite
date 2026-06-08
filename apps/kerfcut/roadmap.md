# SynCAD — Codebase Review & Development Roadmap
>
> **Based on v1.0.1 snapshot analysis**  
> Sources: Claude Sonnet (Anthropic) + GPT-4o (OpenAI) + Antigravity (Gemini Pro)  
> Status: Pre-Phase 1 — awaiting developer sign-off

---

## 1. Codebase Health (Current State)

**Overall verdict: Excellent MVP. Clean architecture. Ready to build on.**

| Area | Status | Notes |
|---|---|---|
| Architecture | ✅ Solid | Clear `core` / `ui` separation, no cross-contamination |
| Algorithm | ✅ Correct | MaxRects BSSF properly implemented and tested |
| Testing | ✅ 19 passing | Covers optimizer + persistence layers |
| Entry point | ✅ Clean | `main.py` → `ui/app.py` → `MainWindow` — minimal and correct |
| Persistence | ✅ Functional | Save/load `.zcad`, legacy `.ZAD` import working |
| PDF export | ✅ Present | ReportLab-based, functional but has issues (see below) |
| Branding | ⚠️ Leftover | `core/models.py` and `core/optimizer.py` still reference "Z-CAD Python" in docstrings |
| State management | ⚠️ Weak | `_dirty` flag is manual and easy to miss; no undo/redo |

---

## 2. Issues Identified — Full List

### 🔴 Critical (affects trust, usability, and real-world use)

**1. Input validation is silent**
When a piece is too large to fit any available sheet, it silently ends up in `unplaced` with no warning before or after optimization. Users won't think "my input is wrong" — they'll think "your software is broken." This is a trust-killer and a support nightmare.

*Fix:* Pre-optimization pass that checks each piece against all active sheets and surfaces warnings in the UI before the optimizer even runs.

---

**2. No undo / redo**
The UI mutates job state directly. One accidental delete of a piece after entering 30 of them is a rage-quit moment. This is data safety, not UX polish.

*Fix:* A bounded stack (last 20 states) of serialized job snapshots — simple, no complex diffing needed. Triggered on every destructive action (add, delete, edit piece/sheet).

---

**3. Cost model is not trustworthy**
Labour is hardcoded at "2 minutes per cut, ~2 cuts per piece." This is a placeholder. No workshop operator can use this for real quoting. The Costs tab is decorative in its current state.

*Fix (v2, not full rewrite):* User-configurable fields for:

- Cost per cut (machine time)
- Setup / changeover time per sheet
- Labour hourly rate (already exists — just needs to feed a real model)

---

**4. No material / sheet library**
Users re-enter the same sheet sizes, prices, and thicknesses every single job. There is no concept of a reusable material catalogue. This is the difference between "a script someone runs once" and "software a workshop relies on daily."

*Fix:* A persistent library of sheet materials (name, dimensions, thickness, buy price, sell price) that can be pulled into any job. Stored locally, editable from a settings panel.

---

**5. Currency is hardcoded as `€`**
Hardcoded in `core/export_pdf.py` and `ui/costs_tab.py`. For a South African developer targeting local workshops — and eventually international ones — this is a credibility problem on first impression.

*Fix:* Single currency config value in `version.py` or a settings file. `"R"`, `"€"`, `"$"` — one change propagates everywhere.

---

### 🟡 Important (architecture and power-user concerns)

**6. Optimizer heuristic is hardcoded (backend concern, not just UI)**
MaxRects BSSF is the only path. The issue isn't that users need a toggle now — it's that the architecture doesn't support multiple strategies. Adding one later means refactoring code that will have layouts, undo stacks, and persistence all depending on it.

*Fix:* Abstract the heuristic behind a strategy interface now. Expose a UI toggle later. This is a 20-minute refactor at this stage; a painful one in three phases' time.

**GPT-4o note:** "UI toggle = later ✅ — backend abstraction = now ⚠️" — agreed.

---

**7. `main_window.py` is overloaded (14KB)**
CSV import logic, recent jobs, file I/O, tab coordination, and toolbar building all live here. It works, but it's a maintenance liability as features are added.

*Fix:* Extract CSV import to `core/import_csv.py`. Not urgent, but do it before Phase 4 features land.

---

**8. Cut sequence / cut list output is absent**
The visual cut plan is solid. What's missing is a numbered cut list an operator can hand to an apprentice — "Cut 1: rip sheet 1 at 800mm, Cut 2: crosscut at 500mm." The optimizer knows the placements; it doesn't derive a practical cutting sequence.

*Fix:* This is a Phase 4+ feature, especially since it becomes more meaningful once Guillotine Cut Mode is implemented. Don't rush this one.

---

**9. Layout results are not persisted**
`job_to_dict` saves sheets and pieces but not `layouts`. Every file open requires re-running the optimizer.

*Decision: defer.* The optimizer is fast, recomputing avoids stale data and versioning headaches, and this only becomes a real problem with very large jobs. Revisit if optimization time becomes noticeable.

---

### 🟢 Minor (polish and edge cases)

- No edge case tests for zero-dimension pieces or sheets — worth adding before public release
- `version.py` still shows `APP_VERSION = "1.0.0"` while the snapshot is labelled `v1.0.1` — align these
- `core/models.py` and `core/optimizer.py` docstrings still say "Z-CAD Python" — clean up during Phase 1
- No pre-validation warning when a piece's dimensions exceed all active sheet sizes

---

## 3. Recommended Phase Execution Order

> Each phase protects and enables the next. Do not skip ahead.

---

### Phase 1 — Architecture & Clean Code

**Goal:** Solid foundation before complexity arrives.

- [ ] Create `utils/logger.py` — centralized logging, rotating file handler
- [ ] Install PyQt6 exception hook — catch unhandled crashes, log them, show user-friendly dialog instead of silent exit
- [ ] Sweep leftover "Z-CAD Python" branding from docstrings
- [ ] Align `version.py` version string with actual build label
- [ ] Extract CSV import from `main_window.py` → `core/import_csv.py`

**Why first?** Debugging auth failures and compilation issues without logs is exponentially harder. Do this while the codebase is still simple.

---

### Phase 2 — Security & Code Protection

**Goal:** Prove the app can be compiled before sensitive licensing logic exists.

- [ ] Set up **Nuitka** (not PyInstaller — see note below) to compile to machine code
- [ ] Bundle `.qss` stylesheets and assets into the virtual filesystem
- [ ] Verify all 19 tests pass against the compiled binary

> ⚠️ **Use Nuitka, not PyInstaller.**  
> PyInstaller bundles `.pyc` bytecode — trivially reversible with `uncompyle6`. Nuitka compiles to C then to machine code. Since Phase 3 depends on Phase 2 actually hiding the source, PyInstaller does not achieve the goal.

---

### Phase 3 — Monetization, Auth & Licensing

**Goal:** Business logic, protected by Phase 2 compilation.

- [ ] Spin up dedicated **Supabase instance** for SynCAD (separate from SoulLink)
- [ ] Build FastAPI license validation endpoint
- [ ] Implement startup license key / login flow in the UI
- [ ] Add offline grace token (allow N days offline before re-validation)
- [ ] Consider trial mode / feature-limited free tier for workshop demos

**Why after Phase 2?** Without compilation, any `if not has_license: exit()` check is one line deletion away from being bypassed.

---

### Phase 4 — Essential Features (ordered by impact/effort ratio)

#### Tier 1 — Do these first (fast wins, high credibility)

- [ ] **Input validation warnings** — pre-optimization check, surface impossible pieces clearly
- [ ] **Material / sheet library** — persistent catalogue, pull into any job
- [ ] **Currency config** — one setting, propagates to PDF and UI

#### Tier 2 — Stability and real usability

- [ ] **Undo / redo** — bounded snapshot stack, 20 states, triggered on destructive actions
- [ ] **Configurable cost model** — user-defined cut cost, setup time, labour rate

#### Tier 3 — Power features

- [ ] **Optimizer strategy abstraction** (backend already, UI toggle later)
- [ ] **Guillotine Cut Mode** — constrain cuts to guillotine sequences for panel saws
- [ ] **Excel / Clipboard import** — paste piece lists directly from spreadsheets
- [ ] **Cut sequence output** — numbered cut list, printable, pairs with Guillotine Mode
- [ ] **Persistent app settings** — default kerf, default labour rate, last-used directory

---

## 4. Go-To-Market Notes

> Not code — but relevant to development prioritisation.

**Target market (Phase 1):** Local South African workshops, cold outreach + email. Direct feedback loop.

**Competitive positioning:** Z-CAD is the acknowledged incumbent — German, aging, hard to find. SynCAD's pitch writes itself.

**Key differentiator to lead with:** Legacy `.ZAD` import. Any workshop currently on Z-CAD can migrate without re-entering historical job data. This removes the single biggest switching barrier.

**Reddit communities for launch:**

- r/woodworking
- r/cabinetmaking  
- r/DIY
- r/selfhosted

**Pricing framing:** Don't sell features — sell material savings. If SynCAD saves one sheet of 18mm MDF per job, it's paid for itself. Frame the pitch around that.

**Demo advice:** When demoing to a workshop owner, run a real job — their sheet sizes, their piece list. The visual cut plan is immediately legible to anyone who's done manual layout. That's your hook.

---

## 5. Quick Reference — Consensus Priority Table

| # | Issue | Claude | GPT-4o | Consensus Priority |
|---|---|---|---|---|
| 1 | Input validation warnings | Critical | Tier 1 | **🔴 Do first** |
| 2 | Material / sheet library | Critical | Tier 1 | **🔴 Do first** |
| 3 | Currency config | Critical | Tier 1 | **🔴 Do first** |
| 4 | Undo / redo | Critical | Tier 2 | **🟠 Do soon** |
| 5 | Cost model v2 | Critical | Tier 2 | **🟠 Do soon** |
| 6 | Heuristic abstraction (backend) | Nice-to-have | Now (backend) | **🟡 Do in Phase 1–2** |
| 7 | Cut sequence output | Phase 4+ | Phase 4+ | **🟢 Later** |
| 8 | Layout persistence | Defer | Defer | **⚪ Defer** |

---

*Document generated from v1.0.1 snapshot review. Update as phases complete.*
