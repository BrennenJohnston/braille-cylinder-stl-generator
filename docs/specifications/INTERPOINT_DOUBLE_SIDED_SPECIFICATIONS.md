# Interpoint (Double-Sided) Specifications

## Overview

This document specifies the **Double-Sided Card (BETA)** feature: a toggle that turns the
single cylinder the app generates today into a **paired set** that embosses both faces of a
card in one pass between two counter-rotating cylinders.

| Name in this feature | Repo `plate_type` | Single-sided name | Carries when the beta is ON |
|---|---|---|---|
| **Cylinder A** | `positive` | Embossing Plate | The card FRONT's raised dots, plus one recess for every actual BACK dot, plus raised seam arrows |
| **Cylinder B** | `negative` | Universal Counter Plate | The card BACK's raised dots, plus one recess for every actual FRONT dot, plus recessed seam arrows |

There is **no universal all-position counter grid** in double-sided mode — every recess is
paired 1:1 with a real dot on the other cylinder. When the toggle is OFF the app behaves
exactly as before the feature existed; this is proven, not assumed (see
[Section 8, Regression anchors](#8-regression-anchors)).

**Status: BETA — physically validated 2026-08, per stock thickness.** The geometry is
complete and tested in software. The original two print rounds embossed **0.3 mm card
stock** legibly on both faces — the same pair did NOT emboss 0.4 mm stock (corrected
2026-08-19). A controlled print matrix then found the 0.4 mm answer, and since
2026-08-20 the beta ships **two fixed footprint packages keyed to the card-stock
preset** — 0.3 → Option B, 0.4 → the Q2 matrix winner (see
[Section 10, Physical validation](#10-physical-validation-2026-08)). Still no tuning
dials, and the UI label still carries "(BETA — for testing)" — that label now waits on
broader user testing, not on the embossing test.

**Code is authoritative.** Where this document and the code disagree, the code wins — flag
the mismatch, do not silently edit either side. Authoritative sources in order:
`settings.schema.json` → `app/models.py` (settings), `app/geometry_spec.py` →
`app/geometry/interpoint.py` (geometry), `app/validation.py` (gates).

---

## 1. Why Interpoint — the Interference Problem

A braille dot is a dome pushed into the paper. If a front-side dot and a back-side dot land
on the **same spot** of the card, the second emboss flattens the first: pushing a dome up
from behind destroys the dome already pushed down from the front. US Patent 5,527,117
(Kenneth L. Roy, Impact Devices Inc., 1996) states both the problem and the industry's
solution:

> "Since a dot on one side of the paper cannot be co-located with a dot on the other side
> of the paper (in which a deformed dot at best would be provided), the location of the dots
> on one side of the paper is offset in the x and y directions by approximately 1.25 mm or
> 0.047″ so that the dots on the front of the sheet of paper are 'interpointed' with respect
> to the dots on the back of the sheet of paper."

This diagonal offset is the industry standard called **interpoint**. Duxbury Systems
describes it the same way: "with the embossing done on both sides of each sheet, with a
slight diagonal offset to prevent the dots on the two sides from interfering with each
other."

Two facts from the standards matter for this implementation:

1. **The offset is (1.25, 1.25) mm diagonal** — half the dot pitch in each axis
   (patent, at our 2.5 mm dot pitch). A grid search over every rigid offset of the
   fully-populated 2.5 / 6.5 / 10.0 lattice confirms this diagonal is also the mathematical
   optimum: it maximises the smallest front-to-back dot-centre distance at **1.76777 mm**
   (= 1.25·√2). A horizontal-only or vertical-only offset manages just 1.25 mm.
2. **Interpoint does NOT change the braille grid.** NLS *Specification 800* (October 2014)
   §3.1 mandates interpoint for braille books ("Braille shall be placed on both sides of
   the page, interpoint") and §3.2.4 states one line spacing — 0.400 in = 10.16 mm — with
   no interpoint exception. The repo's 2.5 / 6.5 / 10.0 mm grid therefore stays untouched
   in double-sided mode; only the back grid's position shifts.

---

## 2. The Pairing Mirror and the Back Grid

### 2.1 The mirror: theta → −theta, arrow at 180° as the fixed point

The two cylinders already mirror each other in single-sided mode: the embossing plate
places content at theta = −x/R (`apply_seam` in `app/geometry_spec.py`) and the counter
plate at theta = +x/R (`apply_seam_mirrored`). Double-sided mode reuses exactly this
convention. A raised dot at cylinder angle theta is met by its recess at **−theta** on the
opposing cylinder, at the same height — an exact float negation, no tolerance, no rounding.

The mirror's fixed points are theta = 0 and theta = 180°, and 180° is where the **tactile
seam arrow** sits — so the arrow and its recess line up with no special case, and the
mirror plane is the vertical plane through the arrow midpoint.

### 2.2 The back grid: mirror + interpoint offset

A back-side feature reads normally from behind the card; seen from the front (the frame
both cylinders are laid out in), the back layout is **mirrored** about the seam plane and
then **translated** by the interpoint offset. Implemented as
`interpoint.back_grid_transform(x_mm, z_mm, offset_x, offset_z, direction)`:

```
(x_back, z_back) = (−x + direction · offset_x,  z + direction · offset_z)
```

### 2.3 The D3 sign: `interpoint.BACK_GRID_DIRECTION = +1`

Both signs of the translation give **byte-identical clearances** (the lattice is
symmetric); the sign only chooses which side of the seam arrow the back grid crowds. The
signed-off choice is **+1**: back features crowd the **left of Cylinder A's arrow** for
someone standing outside the cylinder, looking at the arrow with the cylinder top upward.
The back grid slides towards the END of a text line, so the roomier ~3.4 mm of seam land
stays on the start-of-line side, where a finger arrives when locating a row.

The axial step is **coupled to the same sign** — one diagonal step, back rows sitting
1.25 mm higher than front rows.

**The sign is now physically confirmed (2026-08).** No software test or measurement can
catch a wrong sign, because both signs measure the same — so this was the one choice the
suite could not check. Handling the printed Cylinder A/B pairs settled it: the back
features land on the expected side, and the pair registers. `BACK_GRID_DIRECTION = +1`
is confirmed as built; §10 records the test.

**Troubleshooting first stop (retained as history).** If a future printed pair ever comes
out crowded on the unexpected side of the arrow, or will not register, flip
`BACK_GRID_DIRECTION` in `app/geometry/interpoint.py` first (one character), then re-run
the suite — `test_default_direction_crowds_the_left_of_cylinder_a_s_arrow` pins the
constant to its physical meaning and will fail until its expectation is updated to match.

### 2.4 Naming bridge: `interpoint_offset_y_mm` vs `offset_z`

The **settings** call the axial (cylinder-height) offset `interpoint_offset_y_mm`
(runtime `interpoint_offset_y`), matching the y axis of the emitted dot specs. The
**math module** `app/geometry/interpoint.py` calls that same number `offset_z`
(`INTERPOINT_OFFSET_Z_MM`), because its card frame uses z for the cylinder-height axis.
**Same number, two names.** `app/geometry_spec.py` performs the handoff in
`_back_dot_placements` with a comment marking the bridge.

---

## 3. Parameters

Every double-sided field has **two spellings**, following the repo's existing convention
(`spacing.dot_spacing_mm` → `dot_spacing`, `indicators.enabled` → `indicator_shapes`):
the canonical **schema name** lives under the grouped `"double_sided"` object in
`settings.schema.json`, and the **runtime name** is flat with the `_mm` dropped, because
`backend.py` constructs `CardSettings(**settings_data)` from the flat request `settings`
object. **A payload sent with the grouped `_mm` spelling inside `settings` is silently
ignored** — CardSettings keeps its defaults. Send the runtime names.

| Schema name (`double_sided.*`) | Runtime name (flat) | Default | Range | Meaning (mm unless noted) |
|---|---|---|---|---|
| `enabled` | `double_sided_enabled` | `false` / `0` | boolean; runtime 0/1 int | The beta toggle. 0 preserves today's behavior exactly |
| `interpoint_offset_x_mm` | `interpoint_offset_x` | 1.25 | 1.15–1.35 | Back-grid shift around the cylinder (arc length) |
| `interpoint_offset_y_mm` | `interpoint_offset_y` | 1.25 | 1.15–1.35 | Back-grid shift along the cylinder axis (module name `offset_z`, §2.4) |
| `ds_dot_base_diameter_mm` | `ds_dot_base_diameter` | 1.2 | 0.5–3.0 | Double-sided raised dot base diameter |
| `ds_dot_base_height_mm` | `ds_dot_base_height` | 0.4 | 0.0–2.0 | Height of the dot's rounded base below the dome |
| `ds_dot_dome_diameter_mm` | `ds_dot_dome_diameter` | 0.8 | 0.5–3.0 | Diameter where the dome meets the base |
| `ds_dot_dome_height_mm` | `ds_dot_dome_height` | 0.4 | 0.1–2.0 | Dome height (total dot height = 0.4 + 0.4 = 0.8 at defaults) |
| `ds_bowl_base_diameter_mm` | `ds_bowl_base_diameter` | 1.3 | 0.5–5.0 | Paired bowl recess diameter |
| `ds_bowl_depth_mm` | `ds_bowl_depth` | 0.5 | 0.0–5.0 | Paired bowl recess depth |

The runtime toggle is an **int 0/1** like `indicator_shapes`, not a Python bool; read it as
`int(getattr(settings, 'double_sided_enabled', 0))`. JSON `true`/`false` are accepted on
the way in.

**Offset range rationale (1.15–1.35):** the same-surface gap (§5, gate 4) loses roughly
0.18 mm for every 0.125 mm of offset error; below an offset of about 1.125 mm the Option B
gap crosses the 0.34 mm printability floor. The range brackets the published 1.25 value
with room to tune against a real print.

Clearance **peaks at 1.25 mm and falls off symmetrically** — 1.15 and 1.35 give the
identical centre distance — so both ends of the range fail together, and the fix for a
crowding rejection is always to move *back toward* 1.25 mm, never simply to raise or
lower. Since the gate moved onto the printed ridge (v1.6, below) not every value in the
range renders on every package. Measured 2026-08-21, sweeping both offsets in 0.01 mm
steps (441 combinations per package) against the 0.34 mm floor:

| Package | Combinations accepted | Band with both offsets moved together | Worst ridge in range |
|---|---|---|---|
| 0.3 preset (Option B) | 441 of 441 | the whole 1.15–1.35 | 0.354 mm |
| 0.4 preset (Q2, shipped default) | 297 of 441 | **1.19–1.31 mm** | 0.286 mm |

The **range itself did not narrow** (FD-11c, 2026-08-20): 1.15–1.35 stays in
`settings.schema.json`, in `app/validation.py`'s gate 2, and on the OpenSCAD slider,
because the 0.3 package legitimately uses the whole span. What changed is that gate 4
now rejects 132 of the 0.4 package's combinations that the nominal figure used to pass —
the tightest being 1.16/1.16, where 0.3405 mm nominal cleared the floor by 0.0005 mm but
the printed ridge is 0.3005 mm.

**Footprint rationale (two fixed packages keyed to the card-stock preset — Option B
signed off 2026-08-16; the 0.4 package and the keying decided 2026-08-20):** front and
back features share one cylinder surface, so double-sided mode needs smaller dies than
single-sided mode. At the 1.25/1.25 offset the closest front-to-back centre distance is
1.76777 mm; material left between a dot and its neighbouring recess = 1.76777 −
(dot Ø + bowl mouth)/2. Each package has two gap figures because the worker cuts the
bowl as a hemisphere whose mouth is wider than the nominal diameter (§6.4): the
*nominal* figure is what the two warnings compute, the *printed* figure is the ridge on
the physical part and, since 2026-08-21, what the hard gate measures (§5, gate 4).

| Footprints | Gap (nominal) | Gap (printed) | Verdict |
|---|---|---|---|
| 0.3 preset — Option B: dot Ø1.2 × 0.8 tall + bowl Ø1.3 (schema default; prints Ø1.345) | **+0.518 mm** | +0.495 mm | Embossed 0.3 mm stock cleanly (two rounds, 2026-08-17) |
| 0.4 preset — Q2: dot Ø1.2 × 1.0 tall (base 0.5 + dome Ø1.0 × 0.5) + bowl Ø1.4 (prints Ø1.48 × 0.74) | +0.468 mm | +0.428 mm | Only package that embossed 0.4 mm stock cleanly (print matrix 2026-08-20); printed ridge measured clean; trips the live warning by design |
| Option A: dot Ø1.5 + bowl Ø1.3 (documented history) | +0.368 mm | +0.345 mm | Fallback superseded by the keyed 0.4 package |
| Single-sided sizes: dot Ø1.5 + bowl Ø1.8 (prints Ø2.12) | +0.118 mm | **−0.042 mm** | Rejected — the printed footprints overlap outright; the nominal figure read this as 0.118 mm of material |

One footprint cannot serve both stocks — the print matrix showed the Q2 package tears
0.35 mm card while Option B under-forms 0.4 mm card, the same fact that motivates the
single-sided presets — so the UI sends the package for the selected card-stock preset
(§6.1, §7.5) and the schema defaults stay Option B as the absent-field fallback. A
machine-side limit from the same tests: die heights above 1.0 mm scrape the embosser's
cylinder-holder housing (§10), so both packages sit at or below 1.0 mm.

Thresholds (constants in `app/geometry/interpoint.py`): `SAME_SURFACE_GAP_RELIABLE_MM`
= 0.50, `SAME_SURFACE_GAP_FLOOR_MM` = 0.34 (Bambu X1C Arachne wall generator: paths from
0.1 to 0.34 mm are force-widened to 0.34 mm; below 0.1 mm they are dropped).

### 3.1 `back_lines` — one field, three spellings

The back face's braille (Unicode U+2800–U+28FF, one string per row) appears under a
different spelling at each layer. All three are the same data:

| Layer | Spelling | Notes |
|---|---|---|
| Saved settings document / `settings.schema.json` | `text.back_lines` | Same braille-only pattern as `text.lines` |
| `/geometry_spec` request body | top-level `back_lines`, beside `lines` | The request body has **no `text` object** — this mirrors how `text.original_lines` is spelled `original_lines` on the wire |
| `extract_cylinder_geometry_spec(...)` | `back_lines=` keyword parameter | Added last in the signature, so existing positional calls still work |

`back_lines` is **not** a CardSettings field — it is text and never travels inside the
`settings` object.

### 3.2 Schema ranges vs runtime enforcement

The minimum/maximum values in `settings.schema.json` are **documentation only** — no
Python code validates a payload against the JSON schema. Runtime enforcement is
`validate_double_sided_settings()` in `app/validation.py` (§5), which mirrors the schema's
range literals; the two are flagged in code as a change-both-in-one-commit pair.

---

## 4. Behavior Matrix

| | Toggle OFF (default) | Toggle ON |
|---|---|---|
| Cylinder A (`positive`) | Front raised dots + raised seam arrows (today's Embossing Plate, unchanged) | Front raised dots + **one recess per actual back dot** + raised seam arrows |
| Cylinder B (`negative`) | Universal counter grid — a recess at EVERY possible dot position (rows × columns × 6) | Back raised dots + **one recess per actual front dot** + recessed seam arrows. **No universal grid** |
| Row Indicator Style | User's choice (`visual` default) | **Locked to `tactile`** (UI lock + validation gate) |
| Dot/recess footprints | Shipped single-sided sizes | The `ds_*` Option B footprints for ALL dots and paired recesses |
| Capacity per side | tactile: 14 cols × 4 rows = 56 cells | **Unchanged** — 56 cells per side, 112 total (interpoint never re-spaces the grid) |
| `lines` on a Cylinder B request | Empty (counter plate needs no text) | **The front braille** — it places B's 1:1 paired recesses |
| `back_lines` | Absent (byte-identical pre-feature payload) | Present, top-level, padded to `grid_rows` |
| Download filenames | `Embossing_Cylinder_{preset}_{name}.stl` / `Counter_Cylinder_{preset}_{name}.stl` | `Cylinder_A_{preset}_{name}.stl` / `Cylinder_B_{preset}_{name}.stl` (both named from the front text; see STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md v1.8 §7) |
| Shape | Cards and cylinders | **Cylinders only** — the UI never sends the flag for cards |

Example at the test fixture inputs (front "abc" = ⠁⠃⠉ = 5 dots, back "def" = ⠙⠑⠋ =
8 dots): Cylinder A = 5 raised + 8 recessed, Cylinder B = 8 raised + 5 recessed, 4 seam
arrows each — instead of the 336-recess universal grid a single-sided counter plate would
carry at 14 × 4.

---

## 5. Validation Gates (`app/validation.py`)

`validate_double_sided_settings()` is called from inside `validate_settings()`, which
`backend.py` already runs on every `/geometry_spec` request — so a failed gate is an
HTTP 400 with no backend change. **Every gate is skipped when `double_sided_enabled` is
0 / absent / empty**, proven by tests that feed a config failing all gates with the flag
off.

The four hard gates, with their signed-off messages (`<...>` marks interpolated values).
Gates 1–3 were signed off by Brennen on 2026-08-16; gate 4's rewrite for the
printed-mouth switch was signed off **2026-08-21**. Reword only with his sign-off.

1. **Tactile lock.** `indicator_mode` must be `'tactile'` (the absent-key default
   `'visual'` also rejects):
   > "Double-sided mode is a beta that requires the tactile row indicator style: set the
   > Row Indicator Style to 'Tactile seam arrow' (indicator_mode 'tactile') or turn
   > double-sided mode off. Received indicator_mode '`<mode>`'."
2. **Offset range.** Both offsets within [1.15, 1.35], quoting the canonical schema
   spelling:
   > "Setting 'double_sided.interpoint_offset_x_mm' must be between 1.15 and 1.35 mm;
   > received `<value>`."
3. **Footprint ranges.** Each of the six `ds_*` values within its schema range (§3
   table), same message shape:
   > "Setting '`<double_sided.ds_* schema name>`' must be between `<min>` and `<max>` mm;
   > received `<value>`."
4. **Same-surface gap floor.** `interpoint.same_surface_min_gap()` with the active
   footprints, offsets, and grid must clear 0.34 mm — measured on the recess's **printed
   mouth**, `interpoint.printed_bowl_mouth_mm(bowl_diameter, bowl_depth)`, not its
   nominal diameter (below). Message wording rewritten and **signed off 2026-08-21**:
   > "Double-sided crowding: the `<bowl>` mm recess is cut as a hemisphere, so it prints
   > `<mouth>` mm across, and beside a `<dot>` mm dot at the `<x>` / `<y>` mm interpoint
   > offset that leaves `<gap>` mm of material between them — less than the 0.34 mm a
   > 0.4 mm nozzle can lay down, so the ridge between them would not print. Clearance is
   > widest with both interpoint offsets at 1.25 mm and narrows toward either end of the
   > range, so move them back toward 1.25 mm — or use a smaller double-sided dot or
   > recess (the 0.3 mm card stock preset pairs the same dot with a smaller recess)."

   (The gap is quoted to three decimals; the single-sided footprints 1.5 + 1.8 now
   produce "−0.042" against a printed mouth of "2.12" and reject, where the nominal
   figure read "0.118".) The `details` dict carries `gap_mm` (the printed ridge the gate
   compared), `floor_mm`, `dot_diameter_mm`, `bowl_diameter_mm` (still nominal — it is
   the user's input), and since 2026-08-21 `printed_bowl_mouth_mm` and `nominal_gap_mm`,
   so nothing the old message reported was lost. `details` is internal: `backend.py`
   returns only the message text.

   **Why printed here and nominal in the warnings (FD-11b, Brennen 2026-08-20).** The
   assert is what actually stops an unprintable export, so it measures what actually
   prints; the nominal figure overstates the ridge by 0.023 mm on the 0.3 package and
   0.040 mm on the 0.4 one, and that band is exactly where this gate used to pass a ridge
   the printer cannot hold. Switching the two soft warnings as well would have forced
   `SAME_SURFACE_GAP_RELIABLE_MM` to be re-decided, because at the 0.50 mm line the
   printed figure makes the **0.3 package warn about itself** (0.4953 mm) despite its
   embossing clean on 0.3 mm stock. Leaving them nominal also keeps the browser, the
   generator and the OpenSCAD port quoting one number. A test asserts the split at the
   source in both directions, so consolidating onto one formula fails the suite.

   **Non-positive `ds_bowl_depth` — REJECTED since 2026-08-21.** `ds_bowl_depth_mm` is
   documented 0.0–5.0 because a *single-sided* counter plate may legitimately ask for no
   recesses at all (a flat counter plate). Double-sided cannot: the paired bowl is what
   receives the opposing cylinder's dot, so a depthless one leaves the two cylinders
   pressing solid against solid at the nip. `validate_double_sided_settings` now raises
   before any measurement is attempted:

   > Setting 'double_sided.ds_bowl_depth_mm' must be greater than 0 mm in double-sided
   > mode; the paired recess is what receives the opposing cylinder's dot, so a depth of
   > 0 mm would leave the two cylinders pressing solid against solid. Received 0.0.

   This retires the nominal-diameter fallback the gate carried between 2026-08-21's two
   revisions, and keeps `printed_bowl_mouth_mm`'s own `ValueError` unreachable from this
   path rather than merely worked around. A NEGATIVE depth never reaches this check — the
   0.0–5.0 range test above it rejects those first, with its own message.

**The marginal band (0.34–0.50 mm nominal) is NOT rejected.** Validation only logs it,
on the nominal figure; the user-facing channels are the `geometry_spec` soft warning
(§6.3) and the live UI region (§7.3), both quoting the same nominal numbers.

Related, in `backend.py`: when a request carries `back_lines`, it is validated with
`validate_lines` + `validate_braille_lines(back_lines, 'positive')` +
`validate_line_lengths` — **always as braille, on BOTH plate types**. There is no
counter-plate exemption for back text, because back braille is real geometry on both
plates (recesses on A, raised dots on B). Decided by Brennen 2026-08-16.

---

## 6. Data Flow As Built

### 6.1 UI → wire (`public/index.html`, generate handler)

1. `doubleSidedOn` = toggle checked **AND** shape is cylinder. The flag is never sent for
   cards.
2. With the beta on, the front translation branch runs for **both** plate types (single-
   sided negative requests still send empty `lines` — byte-identity preserved).
3. `#back-text` is split on newlines, trimmed, trailing blanks dropped; each non-empty
   line goes through `translateWithLiblouis(applyCapitalizationSetting(line), 'g2',
   tableName)` — **master language table only**, same capitalization path as the front —
   then padded to `grid_rows`. Fails **closed** on too many lines, a failed translation,
   or an over-long translated row (§7.4 strings).
4. The request body gains a top-level `back_lines` and, inside `settings`, the flat
   double-sided fields — `double_sided_enabled` as the NUMBER 1, offsets as strings
   with 1.25 fallbacks, and the six footprints as NUMBERS from `DS_FOOTPRINTS[preset]`
   (`activeDsFootprints()`: the package for the selected card-stock preset; 'custom'
   falls back to the last persisted preset, then '0.4') — **only when the beta is on**.
   Key order is unchanged, so the toggle-off payload is byte-identical to the
   pre-feature payload.

### 6.2 Backend (`backend.py`)

Reads top-level `back_lines`; when present, validates it (§5) and passes
`back_lines=back_lines` to `extract_cylinder_geometry_spec`. Three hunks inside the
`/geometry_spec` handler; the security-header paths are untouched.

### 6.3 Geometry (`app/geometry_spec.py`)

With the flag on, the cylinder builder emits per plate:

- **Cylinder A**: the existing front-dot loop (untouched), then one bowl recess per
  actual back-text dot at the back-grid position.
- **Cylinder B**: one bowl recess per actual front-text dot, then raised dots for the
  back text. The universal all-position grid is **skipped entirely**.

**Ordering is a contract:** both plates emit FRONT features first, then BACK, in the same
order — so `A.dots[i]` and `B.dots[i]` are partners at theta and −theta, and
`zip(interpoint.pairing_map(a['dots']), b['dots'])` compares them index for index (a test
does exactly this, with EXACT theta/y equality).

Emitted footprints reuse the existing shape vocabulary — the workers learn no new words:

- Raised dot: `params.shape = 'rounded'` (defaults: `base_radius` 0.6, `top_radius` 0.4,
  `base_height` 0.4, `dome_height` 0.4, `dome_radius` 0.4 — the Option B dome is an exact
  hemisphere). `is_recess: false`.
- Paired recess: `params.shape = 'bowl'` (defaults: `bowl_radius` 0.65, `bowl_depth`
  0.5). `is_recess: true`.

Two soft warnings can be appended to `spec['warnings']` (wording signed off 2026-08-16):

- Non-tactile indicator forced (defense-in-depth for direct callers; unreachable via HTTP
  because gate 1 rejects first):
  > "Double-sided mode is a beta that locks the row indicator style to the tactile seam
  > arrows; '`<mode>`' was requested and 'tactile' was used instead."
- Marginal same-surface gap (0.34–0.50 mm):
  > "Double-sided crowding: a `<dot>` mm dot next to a `<bowl>` mm recess at the
  > `<x>` / `<y>` mm interpoint offset leaves `<gap>` mm of material between them — less
  > than the 0.50 mm needed to print reliably, so the ridge between them may come out thin
  > or merged. Reduce the double-sided dot or recess diameter, or check the interpoint
  > offsets."

At the Option B defaults the spec is warning-free (gap 0.518 ≥ 0.50).

### 6.4 Worker (`static/workers/csg-worker-manifold.js`)

`processGeometrySpec` partitions dots **per dot** on the spec's `is_recess` flag
(verified in-browser, both plates):

- `dotSpec.is_recess === true` → the subtract batch.
- `dotSpec.is_recess === false` → the union batch.
- Flag **absent** → the legacy plate-wide rule: positive plate unions, negative
  subtracts. Kept because card-style dot specs carry no `is_recess` (see Bug 6 in
  BRAILLE_DOT_SHAPE_SPECIFICATIONS.md), while single-sided CYLINDER specs always did —
  which is why single-sided STLs proved **byte-identical** before/after this change
  (`fc /b` on real browser downloads, both plates).

**CSG order is a contract** — a recess is never filled back in by a later union:

```
shell → union raised dots → union raised markers (arrows)
      → subtract recess dots → subtract recess markers
```

**Bowl-cut convention (authoritative since 2026-08-19):** the worker cuts the bowl from
a sphere centred ON the cylinder surface — a hemisphere of radius (a² + h²)/(2h) — so
the nominal 1.3 × 0.5 mm bowl comes out 0.667–0.672 mm deep (0.6725 predicted) with a
1.345 mm mouth, and `ds_bowl_depth` sets neither directly. This is what has been
printed and embossed, so it is the convention of record: the golden fixtures render it
since 2026-08-20, and the OpenSCAD port was changed to match. The warnings still quote
gaps from the NOMINAL bowl diameter and so understate crowding by (printed mouth −
nominal)/2 — flagged for the warnings phase.

### 6.5 Nip kinematics (why the pair cannot collide)

At the nip, A's raised dot dips `dot height − surface gap` into B's paired bowl. With the
Option B dot (total height 0.8 mm) in its 1.3 × 0.5 mm bowl, clearance stays ≥ 0.1 mm for
surface gaps down to ~0.25 mm (measured 0.151 mm clearance at gap 0.35). A front dot and a
back dot passing the nip together clear each other by 0.666 mm at gap 0.35 (0.572 mm at
metal-to-metal) thanks to the diagonal offset; a circumference-only offset would collide
(0.000 mm). Rotational sync between the cylinders must stay within about ±1.0° — a
mechanical assembly requirement, not software.

---

## 7. User Interface (`public/index.html`)

Full pattern documented in UI_INTERFACE_CORE_SPECIFICATIONS.md v1.16 Section 4.8; summary
here with the signed-off strings. **All wording below was signed off by Brennen
2026-08-16 — reword only with his sign-off** (each string carries that comment in code).

### 7.1 The toggle block

A `.grade-selection` block directly after the front entry fieldset:

- Legend: **"Double-Sided Card (BETA — for testing)"**
- `#double_sided_enabled` — a real checkbox in a 44 px `.ds-toggle-option` label, with
  `aria-expanded` (mirrors the state), `aria-controls="double-sided-section"`, and
  `aria-describedby` pointing at the explanation note. Label text: **"Emboss both sides of
  the card (interpoint)"**
- Explanation note (`#double-sided-note`): "Embosses both sides of the card in one pass:
  **Cylinder A** (the embossing plate) carries the front's raised dots plus recesses for
  the back, and **Cylinder B** (the counter plate) carries the back's raised dots plus
  recesses for the front, offset diagonally by 1.25 mm so the two sides never collide.
  Turning this on shows the Back of Card section below and locks the Row Indicator Style
  to the tactile seam arrow. Generate each cylinder with the same settings. This is a beta
  for testing — proofread both sides and check every braille surface before use."

Toggling ON reveals `#double-sided-section` containing the **Back of Card** fieldset:

- Legend: **"Back of Card — Enter Text for Braille Translation"**
- Label: **"Back of Card Text"** for the `#back-text` textarea, placeholder **signed off by
  Brennen 2026-08-17**: **"Type the text for the back of the card here. It wraps across the
  rows automatically."** This replaces the 2026-08-16 placeholder ("Each line becomes one
  braille row"), which BANA auto-wrap made untrue — one typed line can now produce several
  braille rows. A newline is still a forced row break, which is what the help note says.
- Help note (`#back-text-help`), **signed off by Brennen 2026-08-17**: "Your text is
  translated with the language selected below and wrapped across the braille rows for you,
  keeping whole words together. Press Enter only where you want to force the start of a new
  row. The back has the same number of rows and cells per row as the front." This replaces
  the 2026-08-16 signed-off note, which said "there is no automatic wrapping here yet" —
  false since the back text gained BANA auto-wrap (§7.4).
- Live overflow warning (`#ds-back-overflow-warning` / `#ds-back-overflow-message`,
  `hidden` when clear) directly after the help note. It carries **no** `role="status"` and
  **no** `aria-live` — it announces through the shared `#a11y-status` region instead. See
  §7.4 and §7.6.

While ON, the front legend reads **"Front of Card — Enter Text for Braille
Translation"** and restores its exact original text ("Enter Text for Braille
Translation") when OFF. Since 2026-08-22 that legend contains an `<h2>` — the section's
heading, see UI_INTERFACE_CORE_SPECIFICATIONS.md §4.11 — so `updateDoubleSidedUI()`
writes to **`#front-entry-heading`**, not to `#front-entry-legend`. Assigning
`textContent` to the legend would delete the heading element. The legend keeps its id;
`tests/e2e/doubleSided.spec.ts` reads it, and reads the same text either way.

### 7.2 The tactile lock

Toggling ON force-selects the tactile radio through a real `change` event (so
persistence, the column dial, and the tactile submenu all react), sets **native
`disabled`** on the visual radio (the repo's existing pattern for unavailable controls —
there is no `aria-disabled` anywhere in the codebase), and shows the live lock note
`#indicator-mode-lock-note` (no `role="status"`, no `aria-live` — it announces through
`#a11y-status`; see §7.6):

> "**Locked:** Double-Sided Card is on, so the Row Indicator Style stays on the tactile
> seam arrow — both cylinders of a double-sided pair need it. Turn the beta off to choose
> visual markers."

All reversed on toggle-off; the tactile **selection** is deliberately kept (no surprise
snap-back).

### 7.3 The live gap warning

`#ds-gap-warning` / `#ds-gap-message` (no `role="status"`, no `aria-live` — announced
through `#a11y-status`; see §7.6) live inside `#double-sided-section` — visible only while the beta is on, the only time it can fire.
`checkDoubleSidedGap()` recomputes on every form change via the form's input/change
delegation, using `dsLatticeMinCenterDistance()` (a JS mirror of
`interpoint.lattice_min_center_distance`). Hidden while the gap ≥ 0.50 mm. The message is
a shared prefix plus one of two tails:

> "A `<dot>` mm dot next to a `<bowl>` mm recess at the `<x>` / `<y>` mm interpoint offset
> leaves `<gap>` mm of material between them — "
>
> - marginal (0.34–0.50): "less than the 0.50 mm needed to print reliably, so the ridge
>   between them may come out thin or merged. Reduce the double-sided dot or recess
>   diameter, or check the interpoint offsets."
> - blocked (< 0.34): "less than the 0.34 mm a 0.4 mm nozzle can print, so generation
>   will be blocked. Reduce the double-sided dot or recess diameter, or check the
>   interpoint offsets."

The footprints come from the selected card-stock preset's package
(`activeDsFootprints()`, §7.5), so on the 0.4 preset the warning is visible whenever
the beta is on: the Q2 package's 0.468 mm nominal gap sits below the 0.50 mm line by
design (its printed 0.428 mm ridge was measured printing clean, 2026-08-20).
Reference numbers (asserted by the e2e suite): 0.4 preset at offsets 1.25/1.25 →
"0.468 mm" marginal; 0.3 preset at 1.25/1.25 → hidden (gap 0.518); 0.3 preset,
offset x 1.15 → "0.449 mm" marginal; both offsets 1.15 → "0.376 mm"; 0.4 preset at
both 1.15 → "0.326 mm" blocked.

**This warning REPORTS the nominal gap and keeps doing so** (FD-11b, §5 gate 4), which is
what keeps its numbers identical to the generator's warning and the OpenSCAD port's. Its
visibility test is nominal too — on the printed figure the 0.3 package (0.4953 mm) would
warn about itself.

**But since 2026-08-21 the printed ridge decides which tail the user gets** (Brennen, the
same day he signed off gate 4's message). The two are computed side by side:

| | Figure used | Why |
|---|---|---|
| Gap quoted in the message | nominal | One number across the browser, the generator and the .scad |
| Show / hide at 0.50 mm | nominal | The printed figure would make the 0.3 package warn about itself |
| "thin or merged" vs "will be blocked" | **printed** | This is what `app/validation.py` gate 4 actually compares, so the box agrees with what generate does |

`dsPrintedBowlMouth(bowlDiameter, bowlDepth)` in `public/index.html` mirrors
`interpoint.printed_bowl_mouth_mm`, including its fallback to the nominal diameter for a
non-positive depth — which since 2026-08-21 is doubly unreachable: the UI ships fixed
footprints, and validation now rejects a 0 mm double-sided depth outright. Before this, the box promised "may come out thin or merged" on the
0.4 preset at both offsets 1.16–1.18 or 1.32–1.34 mm and the request was then rejected;
now those six values read "generation will be blocked" while still quoting their nominal
0.340–0.369 mm. Two e2e rows bracket the band edge: 1.17/1.17 quotes "0.355 mm" and says
blocked, 1.19/1.19 quotes "0.383 mm" and says thin or merged.

The OpenSCAD port keeps the simpler two-way split — its DOTS TOO CLOSE warning is nominal
throughout and its assert is printed — because a rendered console warning has no
equivalent of a live box that must predict a later HTTP rejection.

### 7.4 Back-text wrapping, live warning, and error messages (fail closed)

Since 2026-08-17 the Back of Card text has the same treatment as the front's Auto
Placement: the generate handler runs the **shared `banaAutoWrap(src, cols, rows,
tableName)`** over `#back-text` — same language table, same capitalization setting, same
contracted-grade default, newlines still hard row breaks — instead of translating one row
per newline. `banaAutoWrap` always returns exactly `rows` lines, so the wire shape
(`back_lines` padded to `grid_rows`) is unchanged.

**Live warning while typing.** `computeBackOverflow()` runs the same simulation on a 250 ms
debounce behind its own run-id counter (stale async results are dropped), driven by the
form's `input`/`change` delegation through `refreshLiveWarnings()`. It runs only while the
beta toggle is ON and hides `#ds-back-overflow-warning` the moment the toggle goes off or
the text fits. Both sentences were **signed off by Brennen on 2026-08-17**; the per-paragraph
line deliberately mirrors the front's wording so the two overflow boxes read the same way:

> "Back line N (\"...\") needs C cells but A are available." (one per overflowing paragraph)
>
> "Your back text needs N rows but the plate has R."

**Blocking errors.** The generate handler stops — no STL, no `/geometry_spec` request — on
any of three paths. All three were **signed off by Brennen on 2026-08-17**; they replace the
2026-08-16 signed-off strings, which counted input lines rather than wrapped rows:

> "Back text needs N rows but only R rows are available. Please shorten the back text or
> increase Rows."
>
> "Back of card: <banaAutoWrap warning> The STL file was not generated to prevent producing
> incorrect braille." (a word too long to divide per BANA)
>
> "Back text could not be translated to braille. Please check the text and try again. The
> STL file was not generated to prevent producing incorrect braille." (liblouis unavailable)

The 2026-08-16 per-line "exceeds C available braille cells by X cells" error is **retired**:
wrapping guarantees every emitted row fits, and a token that cannot fit at all now takes the
BANA-undividable path above.

### 7.6 How the beta's warnings are announced (`#a11y-status`)

Added 2026-08-18 (Phase 05d/05e). **The four beta-flow boxes do not announce themselves.**
`#ds-back-overflow-warning`, `#ds-gap-warning`, `#indicator-mode-lock-note` and
`#tactile-gap-warning` are hidden between messages, and a live region that is hidden when
its text is written is inserted into the accessibility tree already holding that text — an
insertion is not a change, so nothing is spoken. `role="status"`/`aria-live` were therefore
**removed** from all four: on a box hidden between messages they can never fire, and leaving
them would let some assistive tech speak the warning twice.

They announce through one always-present region instead:

```html
<div id="a11y-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></div>
```

written by `announceStatus(source, message)`:

- **Scoped by source.** The owning box's id is stored in `dataset.source`; an empty message
  clears the region **only if** the caller owns it, so one box clearing cannot wipe
  another's message.
- **Writing does NOT deduplicate.** `announceStatus()` assigns `textContent`
  unconditionally, and assigning an identical string still replaces the text node — a
  real DOM mutation that assistive tech can speak again. Callers that recompute
  frequently must gate themselves; see the three exceptions below.
  *(Corrected 2026-08-21. This bullet previously claimed "an unchanged string is not a
  mutation, which keeps the per-keystroke recomputes from chattering", which
  contradicted the `announceDsGap` bullet further down the same list and was disproved
  by measurement: `#caps-warning`, whose text never changes, announced **11 times over
  11 keystrokes** when wired without a gate.)*
- **Each announcement repeats the box's own `textContent`**, so what is heard matches what
  is shown, "Warning:" included, and no separate wording exists to drift or need sign-off.

Four call sites are deliberately not a plain mirror, each found by listening (or by a
test that listens) rather than by reading the accessibility tree:

- **The lock note is deferred one task** (`setTimeout(..., 0)`). Announced synchronously it
  arrived before the checkbox's own "checked, expanded" — about 30 words before the user
  learned the box they had just pressed was ticked.
- **The back-text overflow warning announces only on hidden → shown.** Its text carries a
  live cell count, so every keystroke was a real change and it talked over the user while
  they typed. Measured 3 announcements before the change, 1 after, over the same typed
  sentence.
- **The gap warning announces only when its message changes** (`announceDsGap`, added
  2026-08-20 with the preset keying). On the 0.4 preset the warning box is visible for
  the whole session, and `announceStatus` rewrites the region even for identical text —
  so its per-keystroke recompute kept re-taking the region and talked over the
  back-overflow warning (caught by the e2e suite). Announcing only on change restores
  one polite announcement per real event; the visible box is unaffected.
- **The physical seam-fit warning is debounced 250 ms and gated hidden → shown**
  (`checkPhysicalFit()`, added 2026-08-22 — found by the first NVDA run of the
  live-warnings walkthrough). It recomputes on every keystroke into the cells,
  diameter and spacing dials, and its text embeds the live numbers, so each digit
  typed was a "different string" and announced mid-typing — measured four
  announcements in 5.3 seconds while a value was typed, reading out intermediate
  arithmetic like "needs 1415 columns … leaves -9094.2 mm". No suite test pins
  this cadence: every input feeding the check is preset-owned, so a dial-typing
  test hits the known dial race — the walkthrough's Part 5 listens for it
  instead.

**Three more sources joined on 2026-08-21, from outside the beta flow.**
`#auto-overflow-warning`, `#cylinder-overflow-warning` and `#caps-warning` had the
identical defect and were the last unwired regions on the page. All three had their
`role="status"`/`aria-live` removed and now announce their own `textContent` through
this channel, each gated hidden → shown. Their sources are their own box ids, so the
scoping rule above covers them unchanged. Full account, including why the
capitalization note needed a gate despite having fixed text, is in
UI_INTERFACE_CORE_SPECIFICATIONS.md §4.10.

**The wired sources are now nine:** `ds-back-overflow-warning`, `ds-gap-warning`,
`indicator-mode-lock-note`, `tactile-gap-warning`, `stl-ready`, `error-message`
(via MutationObserver), `auto-overflow-warning`, `cylinder-overflow-warning` and
`caps-warning`.

The tree proves a region *can* announce; only listening proves it announces usefully.
The single-sided flow's `#error-message` reaches the same region through one
MutationObserver rather than through `announceStatus()` calls — see
STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md §8.

### 7.5 Persistence, reset, and no dials

- Persisted as `braille_prefs_double_sided_enabled` (`'1'`/`'0'`) and
  `braille_prefs_back_text`; restored on load (a restored ON state re-reveals the section
  and re-applies the lock), cleared by Reset and by Clear-all. Also documented in
  BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md v1.4 (Section 8 and the Section 11
  localStorage table).
- **There are no offset or footprint dials, by decision** (Brennen, 2026-08-16; preset
  keying added 2026-08-20): the footprints ship as fixed packages keyed to the
  card-stock preset — 0.3 → Option B, 0.4 → the Q2 print-matrix winner — via
  `DS_FOOTPRINTS` / `activeDsFootprints()` ('custom' falls back to the last persisted
  preset, then '0.4'). The offsets are overridable only via a saved-settings JSON or a
  direct payload; footprint dials stay deliberately absent — the interpoint budget
  leaves no safe adjustment room (§3).

---

## 8. Regression Anchors

Anything touching this feature must keep these green:

1. **Golden fixture pair** — `tests/fixtures/ds_cylinderA_golden.stl` /
   `ds_cylinderB_golden.stl` (+ `.json` metadata siblings): front "abc" / back "def",
   Option B footprints, tactile, 14 × 4, offsets 1.25/1.25, solid shell (no cutout).
   A = 5 raised + 8 bowls, B = 5 bowls + 8 raised, 4 arrows each. Regenerate ONLY via
   `python -m tests.test_golden` from the repo root. Bowls are cut with the **worker's
   centre-on-surface convention** (0.6725 mm deep at the Option B nominals, §6.4) since
   the 2026-08-20 regeneration. The fixtures pin the Option B (0.3-preset) package: the
   generator refuses a spec with warnings, and the 0.4/Q2 package trips the crowding
   warning by design. These are the first
   files that literally match project-facts' "NEVER modify `tests/fixtures/*_golden.stl`"
   glob.
2. **E2E suite** — `tests/e2e/doubleSided.spec.ts` (16 tests; local pass bar Chromium +
   Firefox, decided 2026-08-16 — WebKit stays with CI on Linux): pins the toggle-off
   payload to an embedded pre-feature snapshot, the tactile lock, the wire shape
   (top-level `back_lines`, flat ds settings as the preset-keyed package — Q2 on the
   default 0.4 preset, Option B on 0.3 — B carrying the front braille), the
   5-raised/8-recessed vs 8/5 paired spec split with no universal grid, all three
   download filenames, the live warning numbers (§7.3), the backend 400 gates, and
   keyboard-only operation of the toggle.
3. **Byte-identity and deep-equality proofs** — toggle-off request payloads proved
   byte-identical to the pre-feature baseline (`fc /b` on captured bodies);
   `test_single_sided_specs_are_unchanged_by_the_double_sided_code` holds a pre-change
   spec capture and deep-compares every dot, marker, and polygon point; the four pre-beta
   golden payloads with `double_sided_enabled: 0` added return responses deep-equal to
   their flag-absent baselines.
4. **Unit/validation suites** — `tests/test_interpoint_math.py` reproduces every research
   number exactly (1.76777, 0.518, 0.118, nip clearances);
   `tests/test_double_sided_validation.py` covers the four gates at both the function and
   the HTTP level, and since 2026-08-21 also pins the printed-mouth switch: both shipped
   packages still pass at 1.25/1.25, 1.16/1.16 is newly rejected on the 0.4 package but
   still accepted on the 0.3 one, the 0.4 package's diagonal band edges at 1.19 (accept)
   and 1.18 (reject), and two source-level guards: one fails if the hard gate stops using
   the printed mouth or if `geometry_spec`'s warning starts using it, the other pins the
   browser's three-way split (nominal quoted, nominal visibility, printed tail choice).

**Do not assert `is_watertight` on raised-arrow plates** (single-sided embossing plate
and double-sided Cylinder A): at the default 10 mm arrow length on 10 mm line spacing,
every such export carries exactly 3 pre-existing non-manifold pinch edges at theta 180°
(the arrow tip-to-base tangency, welded by STL float32 rounding). Measured identically on
pre-beta output — product behavior, not a regression. B plates (recess outlines grown
0.2 mm) are watertight.

---

## 9. Known Gaps and Risks

- ~~**The D3 sign is the one unverifiable choice** (§2.3)~~ — **CLOSED 2026-08.**
  Confirmed by handling the printed pair (§10). Still cheap to reverse if a future build
  ever disagrees.
- ~~**Physical dome conformance is unproven**~~ — **CLOSED 2026-08.** The Ø1.2 mm Option B
  die raises a legible dome on real card stock over two print rounds (§10). Option B is
  permanent; the Option A fallback (§3) stays documented as history only. **Amended
  2026-08-20:** that pass was on 0.3 mm stock only; 0.4 mm stock needs the taller Q2
  package, keyed to the card-stock preset (§3, §10).
- **Front lines on a double-sided Cylinder B request bypass the braille-charset check**
  (pre-existing `validate_braille_lines(lines, plate_type)` signature; report-only). They
  only become recesses there, and the paired Cylinder A request does validate them.
- **A card request with the flag on passes the gates if tactile** — the flag is
  meaningless on the card path and the UI never sends it for cards; the gates are
  settings-level only.
- **Worker bowl-depth drift** (§6.4) and the **arrow tangency pinch edges** (§8) are
  documented pre-existing behavior, not bugs introduced by this feature.
- ~~**The live UI warning under-predicts blocking in a narrow band**~~ — **CLOSED
  2026-08-21.** On the 0.4 preset, six diagonal offsets (1.16–1.18 and 1.32–1.34 mm)
  showed "may come out thin or merged" and were then rejected at generate time. Brennen
  chose the middle option: the browser now decides that tail on the printed ridge while
  still quoting the nominal gap (§7.3). Rejected: leaving it (a surprising rejection for
  an assistive-tech user is worse than a three-way split), and switching the browser
  fully to printed (that is the 0.3-package self-warning FD-11b exists to avoid).
- ~~**A 0 mm `ds_bowl_depth` is schema-legal and means two different things**~~ —
  **CLOSED 2026-08-21.** The gap was real and slightly worse than recorded here: the
  worker's 0.8 mm substitution was reachable from the *single-sided* Bowl Recess Dot
  Depth dial (`min="0"`) as well, and on the card counter plate the same 0 mm raised
  `ZeroDivisionError` -> HTTP 500. `app/geometry_spec.py` now emits no bowl at all at
  0 mm depth, which makes the substitution unreachable on every path; double-sided 0 mm
  is rejected by gate 4 (§5). See `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md` §5, "A depth of
  0 mm means no recess, not a default one".
- **Rotational sync** between the two cylinders must stay within about ±1.0° (§6.5) — a
  requirement on the mechanical assembly, outside this codebase.

---

## 10. Physical Validation (2026-08)

The embossing test the beta was waiting on has been run and **passed**.

| Item | Result |
|---|---|
| Test date | 2026-08 (recorded 2026-08-17) |
| Printer / nozzle | Bambu Lab X1C, 0.4 mm nozzle |
| Rounds | Two, each a full Cylinder A + Cylinder B pair |
| Footprints under test | Option B — dot Ø1.2 mm (0.4 mm rounded base + 0.4 mm dome, dome Ø0.8 mm); paired bowl Ø1.3 × 0.5 mm deep |
| Medium | Real card stock, embossed through the paired cylinders — **0.3 mm stock** (corrected 2026-08-19: the same pair did NOT emboss 0.4 mm stock) |
| Outcome | Braille legible on **both** faces of the card |

**What this closes**

1. **Option B is permanent.** The smaller double-sided die raises a readable dome, so the
   shipped footprints stay fixed with no tuning dials. **Option A (dot Ø1.5 + bowl Ø1.3)
   is documented history only** — there is no fallback switch to it, in the UI or in the
   settings. **Amended 2026-08-20: permanent as the 0.3-preset package**; the 0.4 preset
   ships the Q2 package (the 2026-08-20 record below).
2. **`BACK_GRID_DIRECTION = +1` is confirmed** (§2.3). Handling the printed pair showed
   the back features landing where the spec says they should — left of Cylinder A's raised
   arrows, viewed from outside the cylinder with the top upward. The "unverifiable sign"
   caveat is closed; the flip procedure in §2.3 is retained as troubleshooting history.
3. **The §9 physical-conformance risk is closed** for the printed pair as specified.

**What this does NOT close**

- The feature keeps its **BETA** label. The remaining gap is breadth — one builder, one
  printer, one paper stock — not whether the geometry works.
- **Rotational sync** between the two cylinders must still stay within about ±1.0° (§6.5).
  That is a requirement on whoever assembles the machine, not something this codebase can
  enforce.

**The 0.4 mm answer (print matrix, 2026-08-20).** Option B could not emboss 0.4 mm stock
(0.40 mm of usable push against the 0.60 mm the single-sided 0.4 preset gets). A
controlled matrix — Control (= Option B) / Q1 (dot raised to 1.0 mm) / Q2 (Q1 + bowl
Ø1.4) — was printed as paired cylinders and embossed:

| Stock | Control | Q1 | Q2 |
|---|---|---|---|
| 0.35 mm testers | 1.4 × 1.3 mm base, 0.55 tall, clean | 1.45 × 1.3, 0.65, minimal breakthroughs | 1.5 × 1.4, 0.75, many breakthroughs |
| 0.40 mm (one card) | — | — | **1.4 × 1.4, 0.40 tall, clean** |

Findings, all first-hand: embossed height tracks dot push until the paper is pressed to
the bowl floor — **floor contact is the breakthrough mechanism**; embossed width tracks
the bowl mouth (±0.06 mm); 0.4 mm stock is stiffness-limited (it converted only ~⅔ of
the available push); and a 0.05 mm stock change flipped the same Q2 pair from many
breakthroughs to a clean under-formed dot — no single footprint can serve both stocks.
A follow-up (Q3) matrix probing taller and blunter dots was contaminated by a
machine-side discovery: **die heights above 1.0 mm scrape the embosser's
cylinder-holder housing** (Brennen, 2026-08-20), so 1.0 mm is the die-height ceiling on
the current hardware. With no further 0.4 mm stock on hand, Brennen decided 2026-08-20:
**Q2 is the 0.4-stock package** — the only clean 0.4 mm emboss, and its 1.0 mm height
clears the housing — keyed to the card-stock preset. Its printed 0.428 mm same-surface
ridge was inspected on the printed cylinders (row of full cells, both faces): **clean
and separated**. Full record: the research folder's `00_PROJECT_MEMORY.md`, FD-8/FD-9.

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-21 | 1.8 | **Section 7.6 corrected and extended** (post-initiative accessibility hygiene bundle). The bullet claiming "an unchanged string is not a mutation, which keeps the per-keystroke recomputes from chattering" was **wrong and contradicted the `announceDsGap` bullet in the same list**: `announceStatus()` assigns `textContent` unconditionally, and assigning an identical string still replaces the text node. Disproved by measurement - `#caps-warning`, whose text never changes, announced **11 times over 11 keystrokes** when wired without a gate. The bullet now states that writing does not deduplicate and that frequent callers must gate themselves. Also records the three non-beta sources that joined the channel the same day (`auto-overflow-warning`, `cylinder-overflow-warning`, `caps-warning`), bringing the wired total to **nine**. Documentation and one UI file only - no beta behaviour, wire shape, footprint, threshold, or geometry changed, and the toggle-off payload is untouched. |
| 2026-08-21 | 1.8 | **A 0 mm `ds_bowl_depth` is now REJECTED in double-sided mode** (§5 gate 4; the §9 gap is struck as closed). The gap recorded at v1.6/v1.7 turned out to understate the problem: `csg-worker-manifold.js`'s 0.8 mm substitution was reachable from the shipped *single-sided* Bowl Recess Dot Depth dial too, and the card counter plate raised `ZeroDivisionError` -> HTTP 500 on the same input. `app/geometry_spec.py` now declines to emit a depthless bowl on all three paths, so 0 mm single-sided means what it says — a flat counter plate, reported through `spec['warnings']` and the log — while double-sided 0 mm fails with a message naming the nip. The gate's nominal-diameter fallback and its `measured_on_the_print` branch are gone; `dsPrintedBowlMouth()`'s matching fallback is left in place but is now doubly unreachable. Two tests were rewritten from the old contract to the new one; `test_footprint_boundaries_are_accepted` moves `ds_bowl_depth` from 0.0 to the hemisphere 0.25 mm, the value that minimises the printed mouth for a 0.5 mm bowl. **No threshold, range, footprint, geometry, or golden fixture changed** — schema range stays 0.0–5.0 and both shipped depths (0.5 double-sided, 0.8 single-sided) are byte-identical. |
| 2026-08-22 | 1.10 | **§7.1: the front-legend relabel names the right node again.** The five major section legends now each contain an `<h2>` (audit finding F-A, decision D1 — the page went from 1 visible heading to 6 on load), so `updateDoubleSidedUI()` writes the "Front of Card — …" text to `#front-entry-heading`; writing it to `#front-entry-legend` would delete the heading. **The user-facing wording is unchanged in both states and the toggle-off text is byte-identical**, verified by toggling the beta on and off under an accessibility-tree probe. Documentation only — no geometry, no defaults, no wording. |
| 2026-08-22 | 1.9 | **§7.6: the exceptions list grows to four.** `checkPhysicalFit()` (the `tactile-gap-warning` source) gained the 250 ms debounce and hidden→shown gate its siblings had, after the first NVDA listening run (POST15_6) measured **four announcements in 5.3 s** while a value was typed into the cells dial. One UI file; no threshold, footprint, or geometry changed. Verified by probe on Chromium and Firefox: typing 9-9-9-9 now produces one announcement (was three). No suite test can pin the cadence — every input feeding the check is preset-owned (the dial race) — so the live-warnings walkthrough gained Part 5 to listen for it. Approved by Brennen 2026-08-22 (FD-20). |
| 2026-08-21 | 1.7 | **Phase 13b closeout — Brennen's two decisions, taken the same day.** (1) Gate 4's rewritten message is **SIGNED OFF as written**; the `REVIEW-BRENNEN` marker is gone from `app/validation.py` and §5 records the sign-off date. He kept the version that leads with why the recess prints wider than the number the user set, over a shorter fix-first variant and over mirroring the .scad's text — the .scad's names the 0.3 mm preset as *the* fix, which would mislead anyone setting footprints straight over the API. (2) **The live UI warning now chooses its blocked-vs-marginal tail on the PRINTED ridge** while still quoting the nominal gap, closing the §9 gap this phase opened: on the 0.4 preset at both offsets 1.16–1.18 or 1.32–1.34 mm the box said "may come out thin or merged" and generate then failed with a 400. New `dsPrintedBowlMouth()` in `public/index.html` mirrors `interpoint.printed_bowl_mouth_mm`, fallback included. **Visibility and the quoted figure stay nominal** — on the printed figure the 0.3 package would warn about itself, which is the whole of FD-11(b). §7.3 gains the three-way table and the band-edge e2e rows (1.17 → "0.355 mm" blocked, 1.19 → "0.383 mm" thin or merged); §9's entry is struck with the rejected alternatives recorded. The source guard splits into two tests, one per repo half. No threshold, range, geometry, footprint, or golden fixture changed. |
| 2026-08-21 | 1.6 | **The hard printability gate now measures the recess's PRINTED mouth** (FD-11b, approved by Brennen 2026-08-20; the OpenSCAD port made the same switch in its Phase 12, so the two generators now agree on what is exportable). New `interpoint.printed_bowl_mouth_mm(bowl_diameter, bowl_depth)` replaces the sphere-radius expression that was inline in `paired_nip_clearance`; `app/validation.py` gate 4 feeds its result to the same `same_surface_min_gap()` rather than carrying a second formula. **The two soft warnings — `app/geometry_spec.py` and `checkDoubleSidedGap()` in `public/index.html` — deliberately stay on the NOMINAL figure**, and a test pins the split at the source in both directions. Neither threshold moved (floor 0.34, reliable 0.50) and neither did the 1.15–1.35 offset range. Measured consequence, swept in 0.01 mm steps: the 0.3 package keeps all 441 offset combinations, the 0.4 package keeps 297 and loses 132 the nominal figure used to pass; **both shipped defaults are unaffected** (printed 0.495 and 0.428 mm at 1.25/1.25). §3 gains the measured band table and the printed figures for Option A (0.345) and the single-sided sizes (−0.042); §5 gate 4 rewritten with the new message, the extended `details` dict, and the non-positive-depth fallback; §7.3 records that the live warning's "will be blocked" tail under-predicts in a six-value band; §9 gains that band and the 0 mm bowl-depth note. Gate 4's message shipped in this version awaiting Brennen's sign-off (`REVIEW-BRENNEN` in `app/validation.py`) — ***superseded hours later by v1.7 above, which records the sign-off; no marker remains in the repo.*** No geometry, footprint, or golden fixture changed. |
| 2026-08-20 | 1.5 | **Footprints keyed to the card-stock preset** (research memory FD-8/FD-9): 0.3 preset → Option B (unchanged, still the schema/models defaults), 0.4 preset → the Q2 print-matrix winner (dot Ø1.2 × 1.0 mm tall, dome Ø1.0; bowl Ø1.4 nominal → printed Ø1.48 × 0.74). §3 rationale rewritten with both packages and nominal-vs-printed gap figures (Q2: 0.468 nominal / 0.428 printed, measured printing clean); §6.1 wire shape (footprints now numbers from `DS_FOOTPRINTS[preset]`); §6.4 bowl convention now authoritative and used by the regenerated goldens; §7.3 new reference numbers — the 0.4 preset shows the warning at defaults by design; §7.5 keying; §7.6 documents `announceDsGap` (the persistent warning announces only on change, fixing it talking over the back-overflow announcement); §8 anchors updated (16 e2e tests; goldens regenerated 2026-08-20 with the worker bowl convention, still Option B footprints); Overview/§9/§10 corrected — the 2026-08 physical pass was 0.3 mm stock only — and §10 gains the 2026-08-20 print-matrix record, the Q2 decision, and the 1.0 mm die-height housing ceiling. Wire payloads change only with the beta ON; toggle-off stays byte-identical. |
| 2026-08-18 | 1.4 | **Section 7 corrected against the code** (web repo Phase 07 closeout, after Phase 05d/05e changed the announcement mechanism): §7.1, §7.2 and §7.3 no longer claim `role="status"`/`aria-live` on `#ds-back-overflow-warning`, `#indicator-mode-lock-note` and `#ds-gap-warning` — those attributes were removed from the markup because a box hidden between messages can never fire them. New §7.6 documents what replaced them: the always-present `#a11y-status` region, `announceStatus(source, message)` and its source scoping, the lock note's one-task deferral, and the overflow warning's hidden-to-shown gate. Also refreshed stale cross-reference versions: STL_EXPORT_AND_DOWNLOAD is at v1.8 and UI_INTERFACE_CORE at v1.16, not the v1.5 and v1.10 cited. Documentation only — no code, wire shape, or geometry changed by this edit. |
| 2026-08-17 | 1.3 | **Placeholder corrected** (web repo Phase 04 closeout): `#back-text`'s placeholder said "Each line becomes one braille row", which stopped being true when v1.2 added BANA auto-wrap. Replaced with "Type the text for the back of the card here. It wraps across the rows automatically.", **signed off by Brennen on 2026-08-17**; §7.1 updated. This closes the last carried-over wording item from Phase 02. No code behaviour, wire shape, or geometry changed. |
| 2026-08-17 | 1.2 | **Back of Card text reached parity with the front** (web repo Phase 02): the generate handler now runs the shared `banaAutoWrap()` over `#back-text` instead of translating one row per newline, and a live `#ds-back-overflow-warning` status region warns while the user types. §7.4 rewritten (wrapping rule, live-warning wording, three fail-closed blocking paths); the 2026-08-16 per-line "exceeds C available braille cells" error retired; the Back of Card help note replaced. All six new user-facing strings — the help note, the three blocking errors, and the two live-warning sentences — were **signed off by Brennen on 2026-08-17**. Wire shape, persistence keys, the toggle-off payload, and all geometry are unchanged. |
| 2026-08-17 | 1.1 | Recorded the **physical validation** (new §10): two Bambu Lab X1C (0.4 mm nozzle) print rounds of Cylinder A/B pairs embossed real card stock legibly on both faces with the Option B footprints. Consequences written through the document — Option B is permanent (Option A is history, not a fallback switch); `BACK_GRID_DIRECTION = +1` is confirmed by physical handling and the "unverifiable sign" caveat in §2.3/§9 is closed (flip procedure retained as history); the status line in the Overview now says the BETA label waits on broader user testing, not on the embossing test. No code, geometry, or golden fixture changed. |
| 2026-08-16 | 1.0 | Initial specification, written at Phase 10 of the interpoint initiative after the implementation (Phases 01–09) was complete and verified. Documents the as-built feature: schema/runtime naming, the four validation gates, the wire shape, the worker partition, the fixed Option B footprints, all signed-off user-facing strings verbatim, and the regression anchors. Citations: US Patent 5,527,117 (Roy, Impact Devices, 1996); NLS Specification 800, October 2014, §3.1/§3.2.4; Duxbury Systems, "Louis Braille and the Braille System"; Bambu Lab Wiki, "Introduction to wall generator". |

---

## Related Documentation

- `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md` v1.4 §8 — the `back_lines` wire
  field, back translation, persistence keys
- `UI_INTERFACE_CORE_SPECIFICATIONS.md` v1.16 §4.8 — the disclosure toggle pattern,
  accessibility validation results
- `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md` v1.8 §7 — the Cylinder A/B download
  filenames
- `RECESS_INDICATOR_SPECIFICATIONS.md` §4 — the tactile seam arrow the beta locks to
- `SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md` §5 — the validation gates from the schema's
  point of view
- `BRAILLE_SPACING_SPECIFICATIONS.md` §6 — the universal-counter-grid exception
- `app/geometry/interpoint.py` — the math module (constants, transforms, clearance
  functions; docstrings carry the research numbers)
