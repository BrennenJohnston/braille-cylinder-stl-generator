# Project Facts — braille-cylinder-stl-generator (always active)

Browser-based braille STL generator: client-side geometry, liblouis WASM
translation, Three.js preview. Working branch: develop — never commit to main.

## Invariants — use as given, never re-derive
1. Edit public/index.html (the deprecated templates/ folder is empty — never
   recreate it).
2. Worker routing: cards → csg-worker.js (three-bvh-csg); cylinders →
   csg-worker-manifold.js (Manifold WASM). Never reroute.
3. Coordinates: Python/trimesh, Manifold, and STL are Z-up; Three.js inside
   csg-worker.js is Y-up — cylinder geometry there needs rotateX(PI/2) before
   STL export. Coordinate mixups are the #1 cause of orientation bugs.
4. All braille text is Unicode U+2800–U+28FF, everywhere in the pipeline —
   with ONE exception: the word separator on the wire is the ASCII space
   U+0020, not the braille blank U+2800. `braille_to_dots()` in app/utils.py
   handles `' '` explicitly as an empty cell, so a space occupies exactly one
   cell just as U+2800 would, and every OTHER non-braille character raises
   ValueError (fail closed). This is deliberate and physically validated —
   never "fix" a space to U+2800, and never widen the exception to any other
   character. Measured on both `lines` and `back_lines` and confirmed by
   Brennen 2026-08-18.
5. Dot position map is fixed: [[0,0],[1,0],[2,0],[0,1],[1,1],[2,1]] = dots 1–6
   as [row, col]. Never reorder it. Shape types: card|cylinder. Plate types:
   positive|negative. Placement modes: auto|manual.
6. Canonical defaults — TWO layers, both true, and they differ. Verified
   2026-08-17. Each layer must stay internally consistent across
   public/index.html (UI), app/models.py, app/geometry_spec.py, and
   csg-worker.js (csg-worker-manifold.js takes radius from the incoming spec
   rather than storing its own default; the drift risk is in the other four
   files). Always say WHICH layer you mean when you quote one of these.

   Layer 1 — SCHEMA/BACKEND defaults. settings.schema.json and app/models.py
   agree, and these are also the raw value= attributes in public/index.html:
   - cylinder: ⌀30.75 mm × height 52 mm, seam offset 355° (radius 15.375 in
     workers — watch diameter-vs-radius conversions)
   - plate/card: 90 × 52 × 2.0 mm
   - spacing: dot 2.5 / cell 6.5 / line 10.0 mm
   - emboss dot family is ROUNDED, not cone (schema dots.combined_shape
     "rounded"; models.py use_rounded_dots 1; both index.html radios checked
     on rounded): base ⌀2.0 × 0.2 high + dome ⌀1.5 × 0.6 high. The cone
     family exists beside it at base ⌀1.8, height 1.0, flat hat ⌀0.4 mm —
     selectable, never the default.
   - recess (bowl): ⌀1.8 × 0.8 mm deep (recess_shape 1)

   Layer 2 — LIVE UI on the wire. restoreThicknessPreset() in
   public/index.html runs on every page load and applies the 0.4 mm Card
   Thickness preset whenever nothing is saved, overwriting Layer 1 before the
   user touches anything. What the dials and the request body actually carry:
   - cylinder: ⌀30.8 mm (radius 15.4 in workers), seam offset 0°
   - rounded emboss dot: base ⌀1.5 × 0.5 high + dome ⌀1.0 × 0.5 high
     (cone family if selected: base ⌀1.5, height 0.8, flat hat ⌀0.4 mm)
   - recess (bowl): ⌀1.8 × 0.8 mm deep — the preset sets the same numbers
   - card, spacing, and tactile-arrow values: unchanged from Layer 1
   The 0.3 mm preset is a third set again (see
   docs/specifications/BRAILLE_DOT_SHAPE_SPECIFICATIONS.md §9).

   Never "fix" one layer to match the other on your own — the preset numbers
   are print-tuned and the schema numbers are the absent-field fallback.
6b. Double-sided (interpoint) BETA — cylinders only, toggle default OFF, and
   toggle-off behavior must stay byte-identical to single-sided:
   - interpoint offset default (1.25, 1.25) mm diagonal, range 1.15–1.35 each
     (settings double_sided.interpoint_offset_x_mm/_y_mm → flat runtime
     interpoint_offset_x/_y; interpoint.py calls the y number offset_z).
   - Double-sided = 1:1 paired recesses on BOTH cylinders (no universal
     counter grid) + Row Indicator Style locked to tactile. Footprints ship
     FIXED at Option B: dot ⌀1.2 (0.4 base + 0.4 dome, dome ⌀0.8) + bowl
     ⌀1.3 × 0.5 mm — no UI dials, by decision (2026-08-16).
   - csg-worker-manifold.js partitions dots per dot on is_recess (true →
     subtract, false → union, absent → legacy plate-wide rule); CSG order:
     shell → union raised → subtract recesses. Never reorder.
   - Naming in the double-sided flow ONLY: "Cylinder A" = positive plate,
     "Cylinder B" = negative plate, downloads Cylinder_A_/Cylinder_B_*.stl.
     Never rename single-sided labels/filenames (training videos use them).

## Settings changes — order of operations
7. settings.schema.json is the single source of truth. When adding or changing
   any parameter/default: update settings.schema.json FIRST, then
   app/models.py, then the UI, then the matching spec document (and
   SPECIFICATIONS_INDEX.md if adding a new system).
8. Source priority when implementations disagree — Settings/Validation:
   settings.schema.json > app/models.py > backend.py. Translation: backend.py >
   static/liblouis-worker.js. Geometry: app/geometry_spec.py > app/geometry/*.

## High-risk files — tests must pass before AND after touching these
9. CRITICAL (browser-tested, all users break if wrong): static/workers/
   csg-worker.js, static/workers/csg-worker-manifold.js,
   static/liblouis-worker.js, app/geometry/braille_layout.py,
   app/geometry/cylinder.py, app/geometry_spec.py.
   HIGH: app/geometry/{dot_shapes,plates,booleans}.py, app/validation.py,
   backend.py (security headers!), public/index.html.
10. NEVER modify tests/fixtures/*_golden.stl unless intentionally changing
    geometry output — and say why in the commit message. That glob literally
    names ds_cylinderA_golden.stl / ds_cylinderB_golden.stl (the double-sided
    pair; regenerate only via `python -m tests.test_golden`); the pre-beta
    fixtures are *_small.stl.

## Named checks
11. python -m ruff check .  and  python -m pytest tests/ -v
    (fast: python -m pytest tests/test_smoke.py -q; geometry:
    tests/test_golden.py must match golden fixtures).
12. Pre-commit hooks auto-fix files; if a commit fails with "files were
    modified by this hook", run git add -A and commit again — the second
    attempt succeeds.
13. After UI changes, follow docs/development/ADA_ACCESSIBILITY_VALIDATION_SOP.md
    (W3C validator 0 errors; Lighthouse accessibility 100; contrast ≥4.5:1
    text / 3:1 UI; accordions need aria-expanded + aria-controls kept updated).
14. Consistency-audit file list for the verify.md workflow Tier 3:
    public/index.html, app/models.py, app/geometry_spec.py,
    static/workers/csg-worker.js, static/workers/csg-worker-manifold.js.
15. OpenSCAD/Braille_Cylinder_STL_Generator.scad is a VENDORED offline copy —
    never edit it here; its home is the braille-stl-generator-openscad repo.

## Spec map — load exactly ONE file, only when the task matches
Specs live in docs/specifications/.

| Task involves | Read this spec |
|---|---|
| Unsure which spec applies | SPECIFICATIONS_INDEX.md |
| Cylinder/plate size, cutout, seam offset, margins | SURFACE_DIMENSIONS_SPECIFICATIONS.md |
| Dot/cell/line spacing, positions, cylinder angles | BRAILLE_SPACING_SPECIFICATIONS.md |
| Dot shapes: dome/cone/bowl formulas, recess geometry | BRAILLE_DOT_SHAPE_SPECIFICATIONS.md |
| Dot-dimension UI controls, defaults, validation | BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md |
| Row markers, seam arrow, indicator_mode | RECESS_INDICATOR_SPECIFICATIONS.md |
| Double-sided beta, interpoint offset, paired recesses | INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md |
| Settings JSON schema, field validation | SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md |
| STL generation pipeline, workers, download button | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md |
| Text input, placement modes, BANA wrap, languages | BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md |
| liblouis translation, table chains, dots conversion | LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md |
| Braille preview panel, shorthand decoding | BRAILLE_TRANSLATION_PREVIEW_SPECIFICATIONS.md |
| Themes, fonts, 3D preview, UI accessibility | UI_INTERFACE_CORE_SPECIFICATIONS.md |
| Card thickness presets (0.3 / 0.4 mm) | CARD_THICKNESS_PRESET_SPECIFICATIONS.md |
| Old caching / lookup_stl (feature REMOVED — history only) | CACHING_SYSTEM_CORE_SPECIFICATIONS.md |
| End-to-end app verification steps | VERIFICATION_GUIDE.md |

After changing documented behavior (an algorithm, parameter, or default):
update the matching spec section and its Document History, then follow the
verify.md workflow checklist.
