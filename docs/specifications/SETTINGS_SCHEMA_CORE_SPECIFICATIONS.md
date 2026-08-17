# Settings Schema Core Specifications

## Document Purpose

This document defines a unified, canonical schema for all user-provided settings and derived parameters used across the Braille Card and Cylinder STL Generator. It centralizes field names, types, defaults, validation rules, and normalization behavior used by both the client and server. It complements feature-specific specifications by providing a single source of truth for parameter contracts and API payloads.

## Scope

- Request payloads for STL generation and geometry spec extraction
- Top-level settings structure and category groupings
- Field types, enumerations, and value constraints (high-level)
- Normalization and precedence rules
- Cross-field validation
- Example payloads

## Source Priority (Order of Correctness)
1. `backend.py` — Request validation, geometry generation
2. `geometry_spec.py` — Geometry spec extraction
3. `app/models.py` — Data models and defaults
4. `static/workers/*.js` — Client-side CSG workers (consumers of the spec)
5. Feature specs — Category-specific rules and formulas

---

## Table of Contents
1. Unified Settings Object Overview
2. Top-Level Request Schema (generate endpoints)
3. Category Reference and Field Definitions
   - 3.1 Text & Translation
   - 3.2 Plate Selection & Shape Type
   - 3.3 Spacing & Layout
   - 3.4 Surface Dimensions (Card & Cylinder)
   - 3.5 Braille Dot Shape & Dimensions (Emboss & Counter)
   - 3.6 Recess Indicators
   - 3.7 Export/Generation Options
4. Normalization Rules (Determinism & Caching)
5. Validation & Cross-Field Constraints
6. Example Requests
7. Versioning & Compatibility
8. Related Specifications
9. Document History

---

## 1. Unified Settings Object Overview

All generate requests use a JSON object composed of logical categories. Categories mirror the UI structure and feature specs.

Top-level conceptual shape:

```json
{
  "shape_type": "card | cylinder",
  "plate_type": "positive | negative",
  "placement_mode": "auto | manual",
  "text": { /* see 3.1 */ },
  "spacing": { /* see 3.3 */ },
  "card": { /* see 3.4 (Card) */ },
  "cylinder": { /* see 3.4 (Cylinder) */ },
  "dots": { /* see 3.5 */ },
  "indicators": { /* see 3.6 */ },
  "export": { /* see 3.7 */ }
}
```

Notes:
- Fields irrelevant to a chosen `shape_type` are ignored by validators but may still be present.
- All numeric fields are millimeters unless explicitly stated (angles in degrees).

---

## 2. Top-Level Request Schema (generate endpoints)

Applies to:
- POST `/generate_braille_stl`
- POST `/geometry_spec`
- POST `/generate_counter_plate_stl` (alias of the negative-plate path)

Minimal JSON Schema (high-level; see category sections for details):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://braille-stl/specs/settings.schema.json",
  "type": "object",
  "required": ["shape_type", "plate_type", "text"],
  "properties": {
    "shape_type": {"type": "string", "enum": ["card", "cylinder"]},
    "plate_type": {"type": "string", "enum": ["positive", "negative"]},
    "placement_mode": {"type": "string", "enum": ["auto", "manual"]},

    "text": {"type": "object"},
    "spacing": {"type": "object"},
    "card": {"type": "object"},
    "cylinder": {"type": "object"},
    "dots": {"type": "object"},
    "indicators": {"type": "object"},
    "export": {"type": "object"},

    "schema_version": {"type": "string"}
  },
  "additionalProperties": true
}
```

---

## 3. Category Reference and Field Definitions

This section lists canonical field names, high-level types, and brief rules. See the linked feature specs for formulas, geometry details, and UI mappings.

### 3.1 Text & Translation
- text.lines: array<string>
  - Required. Each entry MUST be Unicode braille (U+2800–U+28FF). See validation pipeline.
  - The frontend fills this either from liblouis or, when the Braille (Unicode) field is
    non-empty, from that field verbatim. Even then `text.original_lines` carries the English
    inputs when they are non-empty (for indicator letters); it is `null` only when braille
    was pasted with the English inputs left empty.
- text.languages: array<string>
  - Optional. Per-line table IDs; falls back to `text.default_language`.
- text.default_language: string
  - Default language table. Defaults to `en-ueb-g2.ctb` (English UEB, contracted / grade 2),
    matching the BANA *Guidelines for Brailling Business Cards* (March 2024), whose worked
    examples are all contracted UEB.
- text.original_lines: array<string>
  - Optional. Original pre-translation lines for indicators and preview context.
- text.auto_wrap: boolean
  - Auto placement uses BANA-aware wrapping.

See: `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md`, `LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md`, `BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md`.

### 3.2 Plate Selection & Shape Type
- shape_type: "card" | "cylinder" (required)
- plate_type: "positive" | "negative" (required)

See: `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md`.

### 3.3 Spacing & Layout
- spacing.grid_columns: integer (>= 1, default: 15) — TOTAL columns per row,
  including reserved marker columns. The UI dial counts text cells only and
  adds `getReservedMarkerColumns()` before sending (visual default: 13 text
  + 2 markers = 15). See section 3.6 for the per-mode reserved counts.
- spacing.grid_rows: integer (>= 1, default: 4)
- spacing.dot_spacing_mm: number (>= 0)
- spacing.cell_spacing_mm: number (>= 0)
- spacing.line_spacing_mm: number (>= 0)
- spacing.braille_x_adjust_mm: number (default: 0)
- spacing.braille_y_adjust_mm: number (default: 0)

Notes:
- Dot numbering and cell layout are fixed by standard; not user-configurable.
- `grid_columns`/`grid_rows` appear flat in the runtime settings payload under
  the same names, matching `CardSettings`.

See: `BRAILLE_SPACING_SPECIFICATIONS.md`.

### 3.4 Surface Dimensions

Card:
- card.plate_width_mm: number (> 0)
- card.plate_height_mm: number (> 0)
- card.plate_thickness_mm: number (> 0)

Cylinder:
- cylinder.cylinder_diameter_mm: number (> 0)
- cylinder.cylinder_height_mm: number (> 0)
- cylinder.polygon_cutout_radius_mm: number (>= 0) — 0 disables cutout
- cylinder.polygon_cutout_points: integer (>= 3 when radius > 0)
- cylinder.seam_offset_degrees: number (0 ≤ value < 360)

See: `SURFACE_DIMENSIONS_SPECIFICATIONS.md`.

### 3.5 Braille Dot Shape & Dimensions

Selection:
- dots.combined_shape: "rounded" | "cone" (controls both emboss and counter selections; default: "rounded")
- dots.dot_shape: "rounded" | "cone" (compatibility alias, optional)
- dots.recess_shape: 1 | 2 (bowl = 1, cone = 2; compatibility alias, optional; default: 1)

Defaults:
- "Rounded" is the default Braille Dot Shape. Both the 0.4mm and 0.3mm Card Thickness
  presets default to Rounded when applied (the presets change dimensions only; the shape
  is set once when a preset is explicitly selected and can then be changed by the user).

Emboss (rounded):
- dots.rounded.base_diameter_mm: number (> 0)
- dots.rounded.base_height_mm: number (>= 0)
- dots.rounded.dome_diameter_mm: number (> 0)
- dots.rounded.dome_height_mm: number (>= 0)

Emboss (cone):
- dots.cone.diameter_mm: number (> 0)
- dots.cone.height_mm: number (>= 0)
- dots.cone.flat_hat_diameter_mm: number (>= 0)

Counter (bowl recess):
- dots.bowl.base_diameter_mm: number (> 0)
- dots.bowl.depth_mm: number (>= 0)

Counter (cone recess):
- dots.recess_cone.base_diameter_mm: number (> 0)
- dots.recess_cone.height_mm: number (>= 0)
- dots.recess_cone.flat_hat_diameter_mm: number (>= 0)

Notes:
- Category selection controls visibility and applicability of parameter groups.

See: `BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md`, `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md`.

### 3.6 Recess Indicators
- indicators.enabled: boolean (gates ONLY the indicator letter on the emboss plate and
  the matching square on the counter plate; the triangle alignment indicators are always
  generated and have no user-facing toggle). Ignored in tactile mode.
- indicators.indicator_mode: "visual" | "tactile" (default: "visual"; cylinder only)
- indicators.type: "triangle" | "rectangle" | "character"
- indicators.depth_mm: number (default: 0.6)
- indicators.character: string (single alphanumeric for character marker)
- indicators.size_scale: number (scales relative to `spacing.dot_spacing_mm`)
- indicators.rotate_180: boolean (applies for counter plate on cylinder)

Tactile mode dimensions (mm). Both Card Thickness presets apply the same five values —
the arrow is sized by the finger that reads it, not by the print layer height — so a change
here must land in `settings.schema.json`, `app/models.py`, the HTML input defaults, and
**both** `THICKNESS_PRESETS` entries:
- indicators.tactile_indicator_width: number, 2–10 (default: 4.0) — width around the cylinder
- indicators.tactile_indicator_length: number, 2–15 (default: 10.0) — length along the axis
- indicators.tactile_indicator_raise: number, 0–2 (default: 0.5) — emboss arrow height above the surface
- indicators.tactile_recess_clearance: number, 0–1 (default: 0.2) — counter recess outline margin
- indicators.tactile_recess_extra_depth: number, 0–1 (default: 0.2) — counter recess depth beyond the raise

All eleven fields appear **flat** in the runtime settings payload under the same names
(`indicator_mode`, `tactile_indicator_width`, …), matching the OpenSCAD parameter names.
`indicators.enabled` is the one exception: its runtime name is `indicator_shapes` (0 or 1).

UI location: `indicator_mode` is a main-form control (**Row Indicator Style**, above Card
Thickness). The five `tactile_*` dials live in the **Tactile Indicator Dimensions** submenu
of Expert Mode, which is hidden entirely unless tactile mode is selected.

Reserved marker columns per row. The UI dial counts TEXT cells only; the payload
`grid_columns` adds the reserved columns on top. What limits the total is the seam gap
it leaves, `π × diameter − (total − 1) × cell_spacing`: at the defaults (30.75 mm
diameter, so a 96.61 mm circumference, and 6.5 mm cell spacing) that is 5.6 mm at 15
total columns and 12.1 mm at 14.
- indicator_mode = "tactile": 0 columns — the indicator sits in the seam gap — 14 text cells recommended at defaults (14 total, leaving 12.1 mm against the 9.0 mm the arrow and its clear zone need; 15 total leaves only 5.6 mm and is still too many for tactile)
- indicator_shapes = 1 (On): 2 marker columns reserved per row (letter + triangle) — 13 text cells at defaults (13 + 2 = 15 total, 5.6 mm gap)
- indicator_shapes = 0 (Off): 1 marker column reserved per row (triangle only) — 13 text cells at defaults (13 + 1 = 14 total, 12.1 mm gap)

Visual mode recommends 13 text cells in both toggle states because a UEB phone number
is exactly 13 cells when written with periods (`206.616.7678` → `⠼⠃⠚⠋⠲⠋⠁⠋⠲⠛⠋⠛⠓`), and
comes to 13 for a hyphenated number once the repeated number signs are edited out in
the Braille (Unicode) field (`⠼⠑⠁⠚⠤⠃⠃⠊⠤⠛⠊⠁⠓`). Either way it has to fit on one row.

Cross-field notes:
- `indicator_mode` is geometry-affecting and column-count-affecting: it changes
  `validate_line_lengths()` availability, the frontend `grid_columns` payload arithmetic,
  and BANA auto-wrap width.
- Every per-row capacity check (auto-wrap width, auto/manual overflow warnings, the
  Braille (Unicode) field validation, and the generate-time gate) derives from the same
  text-cell dial (`getAvailableColumns()` in the UI); there are no independent capacity
  formulas.
- Tactile mode warns (does not reject) when
  `π × diameter − (grid_columns − 1) × cell_spacing < tactile_indicator_width + 5.0`.
  The warning is returned in the geometry spec's `warnings` array and shown live in the UI.
- Visual mode warns (does not reject) when the seam gap no longer clears one cell's dot
  footprint: `π × diameter − (grid_columns − 1) × cell_spacing < dot_spacing +
  max(rounded_dot_base_diameter, emboss_dot_base_diameter)`, which is 4.5 mm at the
  defaults (frontend `checkPhysicalFit()`). The gap only has to keep the last cell's dots
  clear of the first cell's, and a cell's dots span `dot_spacing` plus one dot diameter;
  requiring a full cell spacing instead would have flagged the recommended 13-text-cell
  visual layout, which leaves 5.6 mm and prints without the dots touching. On the default
  cylinder the warning now starts at 16 total columns rather than 15.

See: `RECESS_INDICATOR_SPECIFICATIONS.md`.

### 3.7 Export/Generation Options
- export.use_client_side_csg: boolean (default: true)
- export.use_manifold_repair: boolean (default: true when available)
- export.file_name_prefix: string (sanitized)

See: `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md`.

---

## 4. Normalization Rules (Determinism & Caching)

Applied before cache-key generation and geometry building:
- Convert numeric strings to numbers
- Round floats to 5 decimals
- Convert near-integers to integers (e.g., 1.0 → 1)
- Normalize booleans to JSON booleans; avoid 0/1 in payloads
- Omit non-geometry-affecting UI fields from geometry hashing

See: `CACHING_SYSTEM_CORE_SPECIFICATIONS.md` (Number normalization, canonical JSON).

---

## 5. Validation & Cross-Field Constraints

High-level checks (non-exhaustive):
- shape_type and plate_type must be valid enums
- text.lines are required and must be Braille Unicode (U+2800–U+28FF)
- cylinder.polygon_cutout_points valid only when radius > 0
- seam_offset_degrees normalized to [0, 360)
- For selected dot shape families, only corresponding parameter groups are required
- All mm values must be non-negative; heights/diameters > 0 where noted
- Geometry safety checks: margins, grid centering, cylinder wrap

Double-sided (interpoint) beta — hard gates (`validate_double_sided_settings()` in
`app/validation.py`, called from `validate_settings()` on every request). All three
are skipped when `double_sided.enabled` is off, so single-sided requests validate
exactly as before the beta. This is the first runtime enforcement of these ranges —
the `minimum`/`maximum` values in settings.schema.json are documentation only:
- `double_sided.enabled` = true requires `indicator_mode` = "tactile"; any other
  value (including the absent-key default "visual") is rejected with HTTP 400.
  The soft warn-and-force branch in `geometry_spec.py` remains as defense-in-depth
  for direct callers of `extract_cylinder_geometry_spec()`.
- `double_sided.interpoint_offset_x_mm` and `_y_mm` must stay within
  [1.15, 1.35] mm (`interpoint.INTERPOINT_OFFSET_MIN_MM` / `_MAX_MM`); out-of-range
  values are rejected with the range quoted.
- The same-surface gap — material between a raised dot (`ds_dot_base_diameter_mm`)
  and the nearest back-side recess (`ds_bowl_base_diameter_mm`) sharing one cylinder
  surface, computed by `interpoint.same_surface_min_gap()` with the active offsets
  and grid — must clear 0.34 mm (`SAME_SURFACE_GAP_FLOOR_MM`, what a 0.4 mm nozzle
  can lay down); below that the request is rejected with the gap quoted to three
  decimals. The marginal band 0.34–0.50 mm (`SAME_SURFACE_GAP_RELIABLE_MM`) is NOT
  rejected: geometry_spec returns it as a soft warning in the spec's `warnings`
  array, and the UI recomputes the same gap live (`checkDoubleSidedGap()` in
  public/index.html, status region `#ds-gap-warning`). Reference values at offsets
  1.25/1.25: Option B dot 1.2 + bowl 1.3 → 0.518 mm (clean); dot 1.2 + bowl 1.5 →
  0.418 mm (warn); single-sided dot 1.5 + bowl 1.8 → 0.118 mm (reject).
- The six `ds_*` footprint values must stay inside their schema ranges
  (`ds_dot_base_diameter_mm` 0.5–3.0, `ds_dot_base_height_mm` 0.0–2.0,
  `ds_dot_dome_diameter_mm` 0.5–3.0, `ds_dot_dome_height_mm` 0.1–2.0,
  `ds_bowl_base_diameter_mm` 0.5–5.0, `ds_bowl_depth_mm` 0.0–5.0); out-of-range
  values are rejected with the range quoted. Like the rest of these gates this
  fires only when the beta is on; the range literals in `validate_double_sided_settings()`
  mirror this schema and must change with it in the same commit.

See feature specs for detailed constraints and formulas.

---

## 6. Example Requests

Card, positive (emboss, rounded):

```json
{
  "shape_type": "card",
  "plate_type": "positive",
  "placement_mode": "auto",
  "text": {
    "lines": ["⠓⠑⠇⠇⠕ ⠺⠕⠗⠇⠙"],
    "default_language": "en-ueb-g2.ctb",
    "auto_wrap": true
  },
  "spacing": {
    "dot_spacing_mm": 2.5,
    "cell_spacing_mm": 6.5,
    "line_spacing_mm": 10.0
  },
  "card": {"plate_width_mm": 90, "plate_height_mm": 52, "plate_thickness_mm": 2.0},
  "dots": {
    "combined_shape": "rounded",
    "rounded": {"base_diameter_mm": 1.5, "base_height_mm": 0.6, "dome_diameter_mm": 1.5, "dome_height_mm": 0.4}
  },
  "indicators": {"enabled": true, "type": "triangle", "depth_mm": 0.6},
  "export": {"use_client_side_csg": true, "use_manifold_repair": true}
}
```

Cylinder, negative (counter, bowl recess):

```json
{
  "shape_type": "cylinder",
  "plate_type": "negative",
  "placement_mode": "manual",
  "text": {
    "lines": ["⠠⠁⠃⠉", "⠠⠙⠑⠋"],
    "languages": ["en-ueb-g2", "en-ueb-g2"]
  },
  "spacing": {"dot_spacing_mm": 2.5, "cell_spacing_mm": 6.5, "line_spacing_mm": 10.0},
  "cylinder": {
    "cylinder_diameter_mm": 30.75,
    "cylinder_height_mm": 52,
    "polygon_cutout_radius_mm": 0,
    "polygon_cutout_points": 12,
    "seam_offset_degrees": 355
  },
  "dots": {
    "combined_shape": "rounded",
    "bowl": {"base_diameter_mm": 1.8, "depth_mm": 0.6}
  },
  "indicators": {"enabled": true, "type": "rectangle", "depth_mm": 0.6, "rotate_180": true},
  "export": {"use_client_side_csg": false}
}
```

---

## 7. Versioning & Compatibility

- schema_version: optional string in requests. When present, backend may validate compatibility.
- Cache key may include a cache version field; see caching spec (recommended).

---

## 8. Related Specifications
- Text & Translation: `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md`
- Translation Engine: `LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md`
- Preview: `BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md`
- Spacing & Layout: `BRAILLE_SPACING_SPECIFICATIONS.md`
- Surface Dimensions: `SURFACE_DIMENSIONS_SPECIFICATIONS.md`
- Dot Shapes: `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md`
- Dot Adjustments: `BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md`
- Indicators: `RECESS_INDICATOR_SPECIFICATIONS.md`
- Export & Download: `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md`
- Caching: `CACHING_SYSTEM_CORE_SPECIFICATIONS.md`
- Manifold WASM: `MANIFOLD_CYLINDER_FIX.md` (in docs/development/)

---

## 9. Development Guidelines

This section provides explicit instructions for developers working on this codebase when implementing changes.

### Change Workflow for Developers

When asked to modify settings, defaults, UI controls, or core features:

```
1. CONSULT SPECIFICATIONS FIRST
   └── Read SPECIFICATIONS_INDEX.md to locate relevant spec(s)
   └── Read SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md for settings changes
   └── Read feature-specific spec for domain logic

2. VALIDATE AGAINST SCHEMA
   └── Check settings.schema.json for field constraints
   └── Verify enum values and type definitions
   └── Confirm default values match across schema and models

3. IMPLEMENT CHANGES IN ORDER
   └── settings.schema.json (if schema change)
   └── app/models.py CardSettings (if default change)
   └── backend.py (if API change)
   └── Frontend JS/HTML (if UI change)
   └── Update specification document(s)

4. CROSS-VALIDATE
   └── Verify cache key normalization handles new fields
   └── Confirm UI reflects schema constraints
   └── Update SPECIFICATIONS_INDEX.md if new subsystem
```

### Critical Constants (DO NOT CHANGE without updating all 9+ locations)

| Constant | Value | Locations |
|----------|-------|-----------|
| Braille Unicode Start | `0x2800` | app/utils.py, app/validation.py, backend.py (×2), app/geometry/plates.py (×2), app/geometry/cylinder.py, geometry_spec.py, liblouis-worker.js |
| Braille Unicode End | `0x28FF` | Same 9 locations |
| Dot Position Array | `[[0,0],[1,0],[2,0],[0,1],[1,1],[2,1]]` | BRAILLE_SPACING_SPECIFICATIONS.md, geometry generation modules |

### Settings Change Impact Matrix

| Change Type | Files to Modify | Specs to Update |
|-------------|-----------------|-----------------|
| New parameter | schema.json → models.py → backend.py | SETTINGS_SCHEMA_CORE_SPECIFICATIONS |
| Default value change | models.py → schema.json | SETTINGS_SCHEMA_CORE_SPECIFICATIONS + feature spec |
| New enum value | schema.json → models.py | SETTINGS_SCHEMA_CORE_SPECIFICATIONS |
| Remove parameter | Deprecate first, then remove | Add to Document History |
| Geometry-affecting change | Increment `cache_version` in schema | CACHING_SYSTEM_CORE_SPECIFICATIONS |

### Specification Verification Checklist

Before completing any task involving settings:

- [ ] `settings.schema.json` validates new/changed structure
- [ ] `app/models.py` CardSettings has matching defaults
- [ ] Relevant specification document updated with changes
- [ ] `SPECIFICATIONS_INDEX.md` updated if new system/spec added
- [ ] Cache key normalization handles geometry-affecting fields
- [ ] Document History section updated with date and changes

---

## 10. Document History

- 2025-12-06 — Initial creation. Consolidated settings schema across specs; added high-level JSON Schema, normalization and validation rules, and examples.
- 2025-12-06 — Added Development Guidelines (Section 9); added `cache_version` field to schema; added default values to schema properties.
- 2026-07-29 — Added `indicators.indicator_mode` and the five `indicators.tactile_*` dimensions for the tactile row indicator ported from the OpenSCAD version (Section 3.6), and noted the Braille (Unicode) field's effect on `text.lines` / `text.original_lines` (Section 3.1).
- 2026-07-30 — Changed `indicators.tactile_indicator_length` to 10.0 and `indicators.tactile_indicator_raise` to 0.5; recorded that both Card Thickness presets now carry all five tactile dimensions, and documented where each indicator control lives in the UI (Section 3.6).
- 2026-07-31 — Changed `spacing.grid_columns` default from 14 to 15 and the per-mode text-cell recommendations to 13 visual (either toggle state) and 14 tactile (Sections 3.3 and 3.6); replaced the visual-mode physical-fit warning rule with the dot-footprint threshold `dot_spacing + max(rounded_dot_base_diameter, emboss_dot_base_diameter)` (Section 3.6).
- 2026-08-16 — Added the double-sided (interpoint) beta hard gates to Section 5: tactile indicator lock, interpoint offset range [1.15, 1.35] mm, the six `ds_*` footprint schema ranges, and the 0.34 mm same-surface-gap floor, enforced by `validate_double_sided_settings()` in app/validation.py when the beta is on (the schema's own min/max otherwise remain documentation only); noted the 0.34–0.50 mm marginal band stays a soft warning (geometry_spec `warnings` + live UI region `#ds-gap-warning`). All user-facing message wording signed off by Brennen the same day.
