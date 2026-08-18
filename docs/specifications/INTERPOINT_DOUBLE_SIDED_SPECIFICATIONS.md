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

**Status: BETA — physically validated 2026-08.** The geometry is complete and tested in
software, and the open physical question is now answered: two printed rounds of Cylinder
A/B pairs embossed real card stock with braille legible on BOTH faces (see
[Section 10, Physical validation](#10-physical-validation-2026-08)). The Option B
footprints are therefore **permanent**. The feature still ships with fixed footprints (no
tuning dials) and still carries "(BETA — for testing)" in its UI label — that label now
waits on broader user testing, not on the embossing test.

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
with room to tune against a real print without ever entering unprintable territory.

**Footprint rationale (Option B, signed off 2026-08-16):** front and back features share
one cylinder surface, so double-sided mode needs smaller dies than single-sided mode. At
the 1.25/1.25 offset the closest front-to-back centre distance is 1.76777 mm; material
left between a dot and its neighbouring recess = 1.76777 − (dot Ø + bowl Ø)/2:

| Footprints | Same-surface gap | Verdict |
|---|---|---|
| Option B: dot Ø1.2 + bowl Ø1.3 (shipped) | **+0.518 mm** | Prints reliably (≥ 0.50) |
| Option A: dot Ø1.5 + bowl Ø1.3 (documented fallback) | +0.368 mm | Marginal band — fallback if Option B domes are too faint on card stock |
| Single-sided sizes: dot Ø1.5 + bowl Ø1.8 | +0.118 mm | Rejected — below the 0.34 mm a 0.4 mm nozzle can print |

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
| Download filenames | `Embossing_Cylinder_{preset}_{name}.stl` / `Counter_Cylinder_{preset}_{name}.stl` | `Cylinder_A_{preset}_{name}.stl` / `Cylinder_B_{preset}_{name}.stl` (both named from the front text; see STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md v1.5 §7) |
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

The four hard gates, with their signed-off messages (wording signed off by Brennen
2026-08-16 — reword only with his sign-off; `<...>` marks interpolated values):

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
   footprints, offsets, and grid must clear 0.34 mm:
   > "Double-sided crowding: a `<dot>` mm dot next to a `<bowl>` mm recess at the
   > `<x>` / `<y>` mm interpoint offset leaves `<gap>` mm of material between them — less
   > than the 0.34 mm a 0.4 mm nozzle can lay down, so the ridge between them would not
   > print. Reduce the double-sided dot or recess diameter, or check the interpoint
   > offsets."
   (The gap is quoted to three decimals; the single-sided footprints 1.5 + 1.8 produce
   "0.118" and reject.)

**The marginal band (0.34–0.50 mm) is NOT rejected.** Validation only logs it; the
user-facing channels are the `geometry_spec` soft warning (§6.3) and the live UI region
(§7.3), both quoting the same numbers.

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
   double-sided fields — `double_sided_enabled` as the NUMBER 1, offsets and footprints
   as strings with Option B fallbacks — **only when the beta is on**. Key order is
   unchanged, so the toggle-off payload is byte-identical to the pre-feature payload.

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

**Measured bowl-depth drift (report-only):** the worker cuts the bowl from a sphere
centred ON the cylinder surface, so the nominal 1.3 × 0.5 mm bowl comes out 0.667–0.672 mm
deep on live worker output (~0.6725 predicted), versus the exact 0.5 mm Python convention
used by the golden fixtures. Deeper is the **safe** direction for nip clearance; left
as-is by decision.

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

Full pattern documented in UI_INTERFACE_CORE_SPECIFICATIONS.md v1.10 Section 4.8; summary
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
- Label: **"Back of Card Text"** for the `#back-text` textarea (one braille row per
  newline), placeholder: **"Type the text for the back of the card here. Each line
  becomes one braille row."**
- Help note (`#back-text-help`), **signed off by Brennen 2026-08-17**: "Your text is
  translated with the language selected below and wrapped across the braille rows for you,
  keeping whole words together. Press Enter only where you want to force the start of a new
  row. The back has the same number of rows and cells per row as the front." This replaces
  the 2026-08-16 signed-off note, which said "there is no automatic wrapping here yet" —
  false since the back text gained BANA auto-wrap (§7.4).
- Live overflow warning (`#ds-back-overflow-warning` / `#ds-back-overflow-message`,
  `role="status"`, `aria-live="polite"`, `hidden` when clear) directly after the help note.
  See §7.4.

While ON, the front legend `#front-entry-legend` reads **"Front of Card — Enter Text for
Braille Translation"** and restores its exact original text ("Enter Text for Braille
Translation") when OFF.

### 7.2 The tactile lock

Toggling ON force-selects the tactile radio through a real `change` event (so
persistence, the column dial, and the tactile submenu all react), sets **native
`disabled`** on the visual radio (the repo's existing pattern for unavailable controls —
there is no `aria-disabled` anywhere in the codebase), and shows the live lock note
`#indicator-mode-lock-note` (`role="status"`, `aria-live="polite"`):

> "**Locked:** Double-Sided Card is on, so the Row Indicator Style stays on the tactile
> seam arrow — both cylinders of a double-sided pair need it. Turn the beta off to choose
> visual markers."

All reversed on toggle-off; the tactile **selection** is deliberately kept (no surprise
snap-back).

### 7.3 The live gap warning

`#ds-gap-warning` / `#ds-gap-message` (`role="status"`, `aria-live="polite"`) live inside
`#double-sided-section` — visible only while the beta is on, the only time it can fire.
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

Reference numbers (asserted by the e2e suite): offsets 1.25/1.25 → hidden (gap 0.518);
offset x 1.15 → "0.449 mm" marginal; both 1.15 → "0.376 mm"; footprints 1.5/1.8 →
"0.118 mm" blocked.

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
the text fits. These two sentences are **still drafts awaiting sign-off** — they were not
among the four strings Brennen signed off on 2026-08-17:

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

### 7.5 Persistence, reset, and no dials

- Persisted as `braille_prefs_double_sided_enabled` (`'1'`/`'0'`) and
  `braille_prefs_back_text`; restored on load (a restored ON state re-reveals the section
  and re-applies the lock), cleared by Reset and by Clear-all. Also documented in
  BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md v1.4 (Section 8 and the Section 11
  localStorage table).
- **There are no offset or footprint dials, by decision** (Brennen, 2026-08-16): the beta
  ships FIXED at Option B. The `ds_*` values and offsets are overridable only via a
  saved-settings JSON or a direct payload; dials come only if the physical embossing test
  calls for tuning.

---

## 8. Regression Anchors

Anything touching this feature must keep these green:

1. **Golden fixture pair** — `tests/fixtures/ds_cylinderA_golden.stl` /
   `ds_cylinderB_golden.stl` (+ `.json` metadata siblings): front "abc" / back "def",
   Option B footprints, tactile, 14 × 4, offsets 1.25/1.25, solid shell (no cutout).
   A = 5 raised + 8 bowls, B = 5 bowls + 8 raised, 4 arrows each. Regenerate ONLY via
   `python -m tests.test_golden` from the repo root. Bowls are cut at the **exact Python
   depth convention (0.5 mm)**, not the worker's deeper drift (§6.4). These are the first
   files that literally match project-facts' "NEVER modify `tests/fixtures/*_golden.stl`"
   glob.
2. **E2E suite** — `tests/e2e/doubleSided.spec.ts` (9 tests; local pass bar Chromium +
   Firefox, decided 2026-08-16 — WebKit stays with CI on Linux): pins the toggle-off
   payload to an embedded pre-feature snapshot, the tactile lock, the wire shape
   (top-level `back_lines`, flat ds settings, B carrying the front braille), the
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
   the HTTP level.

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
  permanent; the Option A fallback (§3) stays documented as history only.
- **Front lines on a double-sided Cylinder B request bypass the braille-charset check**
  (pre-existing `validate_braille_lines(lines, plate_type)` signature; report-only). They
  only become recesses there, and the paired Cylinder A request does validate them.
- **A card request with the flag on passes the gates if tactile** — the flag is
  meaningless on the card path and the UI never sends it for cards; the gates are
  settings-level only.
- **Worker bowl-depth drift** (§6.4) and the **arrow tangency pinch edges** (§8) are
  documented pre-existing behavior, not bugs introduced by this feature.
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
| Medium | Real card stock, embossed through the paired cylinders |
| Outcome | Braille legible on **both** faces of the card |

**What this closes**

1. **Option B is permanent.** The smaller double-sided die raises a readable dome, so the
   shipped footprints stay fixed with no tuning dials. **Option A (dot Ø1.5 + bowl Ø1.3)
   is documented history only** — there is no fallback switch to it, in the UI or in the
   settings.
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

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-17 | 1.2 | **Back of Card text reached parity with the front** (web repo Phase 02): the generate handler now runs the shared `banaAutoWrap()` over `#back-text` instead of translating one row per newline, and a live `#ds-back-overflow-warning` status region warns while the user types. §7.4 rewritten (wrapping rule, live-warning wording, three fail-closed blocking paths); the 2026-08-16 per-line "exceeds C available braille cells" error retired; the Back of Card help note replaced. The four replacement strings (help note plus the three blocking errors) were **signed off by Brennen on 2026-08-17**; the two live-warning sentences remain drafts awaiting sign-off. Wire shape, persistence keys, the toggle-off payload, and all geometry are unchanged. |
| 2026-08-17 | 1.1 | Recorded the **physical validation** (new §10): two Bambu Lab X1C (0.4 mm nozzle) print rounds of Cylinder A/B pairs embossed real card stock legibly on both faces with the Option B footprints. Consequences written through the document — Option B is permanent (Option A is history, not a fallback switch); `BACK_GRID_DIRECTION = +1` is confirmed by physical handling and the "unverifiable sign" caveat in §2.3/§9 is closed (flip procedure retained as history); the status line in the Overview now says the BETA label waits on broader user testing, not on the embossing test. No code, geometry, or golden fixture changed. |
| 2026-08-16 | 1.0 | Initial specification, written at Phase 10 of the interpoint initiative after the implementation (Phases 01–09) was complete and verified. Documents the as-built feature: schema/runtime naming, the four validation gates, the wire shape, the worker partition, the fixed Option B footprints, all signed-off user-facing strings verbatim, and the regression anchors. Citations: US Patent 5,527,117 (Roy, Impact Devices, 1996); NLS Specification 800, October 2014, §3.1/§3.2.4; Duxbury Systems, "Louis Braille and the Braille System"; Bambu Lab Wiki, "Introduction to wall generator". |

---

## Related Documentation

- `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md` v1.4 §8 — the `back_lines` wire
  field, back translation, persistence keys
- `UI_INTERFACE_CORE_SPECIFICATIONS.md` v1.10 §4.8 — the disclosure toggle pattern,
  accessibility validation results
- `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md` v1.5 §7 — the Cylinder A/B download
  filenames
- `RECESS_INDICATOR_SPECIFICATIONS.md` §4 — the tactile seam arrow the beta locks to
- `SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md` §5 — the validation gates from the schema's
  point of view
- `BRAILLE_SPACING_SPECIFICATIONS.md` §6 — the universal-counter-grid exception
- `app/geometry/interpoint.py` — the math module (constants, transforms, clearance
  functions; docstrings carry the research numbers)
