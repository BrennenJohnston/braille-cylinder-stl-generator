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
     workers — watch diameter-vs-radius conversions). Height went 52 → 54 →
     back to 52 on 2026-08-31 (Brennen's deployment verdict): 52 is the
     VERSION 1 STANDARD barrel, the height every previously shipped V1 gear
     model pairs with. The 1 mm card-shelf barrel (54) is Embosser Version 2
     ONLY, applied by V2_PRESET_OVERRIDES when the selector is on Version 2 —
     never by these defaults. Cylinder height stays DECOUPLED from card
     height: the absent-field fallback is 52, owned by
     gears.DEFAULT_CYLINDER_HEIGHT_MM, and updateShapeSettings() no longer
     seeds the dial from card_height. Both thickness presets carry 52.
   - plate/card: 90 × 52 × 2.0 mm — the card stays 52; do not "sync" it to
     the barrel
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
6b. Double-sided (interpoint) — cylinders only, OUT OF BETA since 2026-09-20
   (D-7): the choice is the "Card sides" radio group (`card_sides_single`
   checked / `card_sides_double`) inside the "Embosser setup" menu item at the
   top of the form, read ONLY through isDoubleSidedOn(); the old
   `#double_sided_enabled` checkbox and its accordion are gone; the Back of
   Card fieldset (`#back-entry-fieldset`) is always in the tree and
   native-disabled while single-sided. Single-sided behavior must stay
   byte-identical to before the feature:
   - interpoint offset default (1.25, 1.25) mm diagonal, range 1.15–1.35 each
     (settings double_sided.interpoint_offset_x_mm/_y_mm → flat runtime
     interpoint_offset_x/_y; interpoint.py calls the y number offset_z).
   - Double-sided = 1:1 paired recesses on BOTH cylinders (no universal
     counter grid) + Row Indicator Style locked to tactile. Footprints ship
     FIXED — no UI dials (2026-08-16) — and KEYED to the card-stock preset
     since 2026-08-20: 0.3 preset → Option B dot ⌀1.2 (0.4 base + 0.4 dome,
     dome ⌀0.8) + bowl ⌀1.3 × 0.5 mm (still the schema/models defaults);
     0.4 preset → Q2 dot ⌀1.2 (0.5 base + 0.5 dome, dome ⌀1.0; total 1.0)
     + bowl ⌀1.4 × 0.5 mm (prints ⌀1.48 × 0.74). Source of truth:
     interpoint.DS_FOOTPRINTS_BY_PRESET = index.html DS_FOOTPRINTS (a smoke
     test diffs them). The 0.4 package trips the crowding warning by design
     (nominal gap 0.468; printed ridge 0.428, measured clean 2026-08-20).
     Die heights above 1.0 mm scrape the embosser housing — never raise
     them on your own.
   - csg-worker-manifold.js partitions dots per dot on is_recess (true →
     subtract, false → union, absent → legacy plate-wide rule); CSG order:
     shell → union raised → subtract recesses. Never reorder.
   - Naming in the double-sided flow ONLY: "Cylinder A" = positive plate,
     "Cylinder B" = negative plate, downloads Cylinder_A_/Cylinder_B_*.stl.
     Never rename single-sided labels/filenames (training videos use them).
   - BACK PARITY (2026-09-21, sub-plan D, D-11): the back has its OWN
     placement toggle name="back_placement_mode" (Auto checked), rows
     #back_line{i} + #back_line_lang_{i} (class line-language-select, so
     syncLineLanguageSelects() fills them; rebuilt with the front's on every
     grid_rows change), read through backPlacementMode() /
     getBackDynamicLineValues() / translateBackManualLines(). Manual back
     rows are held to the cell count (S-D1 (signed 2026-09-21), fail closed) and send
     back_per_line_language_tables (schema text.back_languages) - ONLY for a
     manual back; Auto and the back braille field send nothing extra, so
     their request bodies are byte-identical to before. The overflow box
     #ds-back-overflow-warning sits OUTSIDE #back-auto-input-container on
     purpose (manual rows write to it). Persistence
     braille_prefs_back_placement_mode. GenerateBrailleRequest (no callers)
     declares back_lines + back_per_line_language_tables.

6c. Gear-integrated one-piece rollers — cylinders only, OUT OF BETA since
   2026-09-20 (D-7): the choice is the "Gears" radio group
   (`gear_mode_standard` checked / `gear_mode_fixed`) inside the "Embosser
   setup" menu item, read ONLY through isGearRollersOn(); the old
   `#gear_rollers_enabled` checkbox fieldset is gone. Standard (the old OFF)
   must stay byte-identical (proved at three levels: the geometry spec, the
   worker STL, and the request body).
   - Flat name gear_rollers_enabled (schema gear_rollers.enabled), int 0/1.
   - The gears are VENDORED 1:1 replica data at static/assets/gears/
     gears_{a,b}.bin — NEVER hand-edit them, and regenerate ONLY via
     scripts/derive_gear_assets.py (the manifest's sha256s are pinned by a
     test). 24 teeth, tip r 16.1093702290795, 10 mm thick, gears at z -36..-26
     and +26..+36 in the browser frame. The VERSION 2 set lives beside them as
     v2_gears_{a,b}.bin + v2_gears_manifest.json (derived from the v8 Version 2
     gear STLs by scripts/derive_gear_assets_v2.py ONLY, since 2026-09-21;
     same rule, same pin test): same teeth and tip radius, bodies at
     z -37..-27 / +27..+37 with the 15 mm pegs INSIDE the barrel, every axis
     MEASURED per gear (they differ by up to 0.005 mm - recorded, never
     averaged), A set Rz(180), B set identity, every notch/pin on the 180
     column. app/geometry/gears.py owns every gear
     constant, the way app/geometry/interpoint.py owns the DS ones — both
     app/validation.py and app/geometry_spec.py read it, so it is the ONE place
     these numbers live.
   - The cylinder size is FIXED while gears are on: 30.8 x 52.0 mm in
     Version 1 (S7) and 30.8 x 54.0 mm in Version 2 (S-G1 (signed 2026-09-21); the gate
     reads embosser_version and gears.reference_barrel(version)), +/- 0.001,
     or the request is REJECTED. The gears are baked at fixed z and do not
     move with the barrel — a 51 mm barrel exports as THREE loose bodies and
     still reports watertight, and a 62 mm one swallows the teeth. Never
     "relax" this to a warning. The default barrel returned to 52 later on
     2026-08-31 (Brennen's deployment verdict — the one-day 54 default broke
     gears on untouched dials), so gear mode passes S7 on defaults again; the
     54 mm card-shelf barrel is Version 2 only.
   - THE BARREL MUST BE SOLID while gears are on, and emitting
     polygon_points: [] does NOT achieve that — with no polygon the worker
     hollows by wall thickness, which seals an undrainable cavity. The shell
     builder takes an explicit `solid` argument.
   - Weld rings r 8.0-13.0 x 0.1 mm at z +/-height/2 (computed, never
     hardcoded); raised tactile arrows grow by 0.005 mm in gear mode only
     (D-8a). CSG order is unchanged: gears join the RAISED stage, recesses
     still cut last. In FUSED Version 2 mode the gear stage also unions the
     two notch fills (spec gears.notch_fills, see 6d) after the rings.
   - Naming: a `Geared_` segment is inserted ONLY when gears are on
     (Embossing_Cylinder_Geared_{preset}_{name}.stl). Toggle-off names never
     change — training videos use them.
   - There is NO card shape in the UI (one radio, value="cylinder"), so do not
     add UI branches for one; the cylinders-only rule lives in the API.

6d. Embosser Version 2 keyed cutouts - cylinders only, selector default
   Version 1, and Version 1 must stay byte-identical (proved at FIVE levels:
   settings, geometry spec, HTTP, golden fixtures, and a real-browser `fc /b`
   of both the request body and the exported STL). Since 2026-09-20 (D-7,
   D-8) the "(prototype)" tag and the prototype notice are gone and the
   version radios (`embosser_version_1/2`, ids unchanged) are the FIRST of
   three choices inside the "Embosser setup" menu item
   (`#embosser-setup-selection`, the form's first item), whose legend is the
   page's h2 while each choice's legend is an h3.
   - Flat names `embosser_version` (int enum 1|2, schema `embosser_version`)
     and `v2_key_clearance_mm` (schema `version_2.key_clearance_mm`). The
     version is parsed as an EXACT integer - 2.5 is refused, not rounded.
   - app/geometry/version2.py is the ONE place every Version 2 number lives,
     the way gears.py owns the gear ones. Never retype a number from it.
   - Family R14, the only family: four rounded rectangles, corner r 0.500,
     A top 14x14 (the nub end), A bottom 18x10, B top 16x12, B bottom 20x8,
     LONG dimension on 90/270 so a flat always faces the arrow column. The v7
     star, hexagon and 15x15 squares are RETIRED. Grow a key with
     grown_key_outline (sides +2c, corner radius +c) - never by mitering an
     already-rounded outline.
   - Barrel 30.8 x 54.0, tolerance 0.001, but SOFT: off-size warns (S-V5) and
     is ACCEPTED. Unlike the gear gate, never a rejection. Diameter found by
     printing: 30.1 -> 30.5 (2026-08-29, the 30.1 pair embossed with too
     little pressure) -> 30.8 (2026-08-30, the 30.5 double-sided pair felt
     loose and printed shallow, uneven dots - the same symptom weaker, so the
     search stopped at the size Version 1 has always used). Height 54 since
     2026-08-31 (was 52) - the 1 mm card shelf at each end, VERSION 2's ALONE
     since the same day (the project default returned to the 52 mm Version 1
     standard; V2_PRESET_OVERRIDES is what carries a V2 cylinder to 54).
     TRAP (found by a 52 mm V2 print from the live site, 2026-09-20): BOTH
     card-stock presets carry cylinder_height_mm 52, so a preset chosen
     AFTER Version 2 used to put the barrel back to 52 with only the soft
     S-V5 warning; applyThicknessPreset() now re-asserts
     V2_PRESET_OVERRIDES whenever isVersion2() - keep that when the version
     handling is reworked.
     54 print test PASSED (Brennen, 2026-09-01) — both cylinders printed
     from the OpenSCAD V2 file. Version 2 and the gears BETA share ⌀30.8 but the
     HEIGHT now tells them apart (V2 54, gears and the V1 default 52) - and
     so does the version. Version 2 has its own OpenSCAD companion (since
     2026-08-31 also at 30.8 x 54 with 4 text rows per face):
     Braille_Cylinder_STL_Generator_EmbosserV2.scad in the OpenSCAD repo -
     self-contained, interpoint included, and since OpenSCAD v2.8.0
     (2026-09-21) with its own [Integrated Gears] switch for the fused
     Version 2 roller (D-V6 retired); NOT vendored into this repo. The V1
     .scad files stay 52 and untouched.
   - Clearance 0.110 default, range 0.0-0.5, input step 0.005. Applied OUTWARD
     to the four holes ONLY. TWO printed rounds bracketed it on 2026-08-29:
     too loose at 0.15, too tight at 0.075. NOT the midpoint 0.1125 - an
     off-step default renders the input :invalid and kills Generate silently;
     0.110 / 0.005 = 22. Wrong-pair margin is 1.000 - c, so 0.890 here.
   - The NUB DOES NOT FOLLOW THE DIAL, because gear A1's notch is already cut.
     Under the old shared-dial rule, tightening the holes GREW the nub into
     that notch. Never re-couple them. V2_NUB_CLEARANCE_MM is 0.30 since
     2026-08-29 and is DERIVED, never retyped, as V2_GEAR_TRIANGLE_INSET_MM
     (0.15, measured off the gear) + V2_ANTIROT_CLEARANCE_MM (0.15, the signed
     fit). At the old hard 0.15 the nub was line-to-line in the notch - 5 um of
     INTERFERENCE on the base face. Base flare is 0.10, not 0.5: the notch has
     NO mouth relief (half-width constant to full depth), so a 0.5 flare stood
     0.49 mm proud per side and A1 never seated flush across two printed
     rounds.
   - Two halves meet at the mid-plane as ONE through-hole (overlap 0.01), and
     ONE 2.0 x 45 degree rule covers all four mouths. A chamfer hull's slabs
     sit FAR-EDGE-OUT or the taper overshoots. The nub is THREE unioned parts,
     never one hull - a single hull bulges the body 0.2 mm and jams gear A1.
   - BOTH plates carry an anti-rotation NUB above the top face and a SOCKET in
     the bottom one, all four on the 180-degree arrow column (2026-08-29; the
     "positive plate only" rule is RETIRED - every gear has a feature now).
     A gets the triangle, B a square. Nubs are MITRED, sockets are PARALLEL
     CURVES with a corner arc of radius c - backwards puts a sharp internal
     corner in a vertically printed barrel - which is now the WHOLE reason. It
     also costs A 0.15 mm of wall (1.4025 -> 1.2525), but since the 30.8 barrel
     that no longer breaks the 1.2 minimum, so do not argue it from the wall. Socket depth 3.15 (pin + one clearance), no mouth
     chamfer. V2_SOCKET_MAX_RADIUS_MM 14.00 trims 0.0000 today and bites above
     c = 0.1525 - a guard rail, NOT dead code. seam_offset never turns any of
     them.
   - The barrel is SOLID while Version 2 is on; the keyed hole is the bore.
   - FIXED GEARS WORK IN VERSION 2 since 2026-09-21 (sub-plan B; the S-V7
     refusal and the C2 guard/S-M13 are RETIRED). Version 2 + gears = the
     FUSED roller: barrel SOLID, NO keyed_cutouts block (no holes, chamfers,
     nub or socket - D-6), spec['gears'] = {asset v2_gears_a|b, weld_rings,
     notch_fills: [ONE prism]}. The notch fill is the measured top-gear notch
     grown 0.05 as an EXACT parallel_curve (a mitre pushes A's apex 0.10 out),
     z height/2-0.05 .. height/2+depth+0.05, capped at
     V2_NOTCH_FILL_MAX_RADIUS_MM 13.95 < 15.938 (mating tip circle at the V1
     operating distance; the V2 distance is an OPEN item). Without it a
     solid barrel seals an undrainable void; the D-6 acceptance is ONE body
     from mesh.split(only_watertight=False). Golden pair
     tests/fixtures/v2_gear_roller{A,B}_golden.* (regenerate only via
     python -m tests.test_golden). Filenames compose: _Geared_V2_. Ready
     message S-G2 (signed 2026-09-21) replaces S5 + S-V8' for a fused run. The version
     change listener now makes ONE composed DEFERRED announcement (S-V10 +
     gear notes) - keep the deferral: the form-wide change listener bubbles
     after it and re-announces the bare gear note. OpenSCAD counterpart since
     v2.8.0 (2026-09-21): `[Integrated Gears]` in the EmbosserV2 file -
     gear_set_v2 imports assets/v2_gears_{a,b}.stl, the same weld rings and
     notch fill, the same hard 30.8 x 54 gate with the S-G1 sentence; its
     MakerWorld copy hides the switch (no assets there).
   - Naming: a `V2_` segment is inserted ONLY when Version 2 is on
     (Embossing_Cylinder_V2_{preset}_{name}.stl). Version 1 names never change.
   - Version 2 recommends the SAME cell counts as Version 1. The one-fewer
     rule was retired 2026-08-29 with the 30.5 barrel (seam gap 4.8 mm against
     the 4.0 needed) and the 30.8 barrel widens it to 5.76. Restore it only
     below a 30.24 mm barrel.
   - The R14 gear pegs EXIST as of 2026-08-29 and measure exactly nominal
     (14x14, 18x10, 16x12, 20x8, every corner r 0.500). Their STLs are still
     named "v7" - that is the gear body's version, not the peg's. No v7 PEG
     ever enters an R14 hole.

6e. Slicer seam channel (2026-09-20, sub-plan A of the 2026-09-20 programme;
   decisions D-1, D-2, D-13, D-14, D-15) - every cylinder, both plates, ON by
   default, and the only feature whose DEFAULT changes geometry:
   - A V-groove 1.0 wide x 0.5 deep (90 degrees) the full height of the OUTER
     surface, in the seam gap beside the row-indicator column, so a slicer's
     default "aligned" seam mode hides each layer's seam in it instead of in a
     dot. Measured in the 2026-09-20 slicing spike (scripts/seam_spike.py):
     100 % capture on both visual plates and the tactile counter plate, 90.8 %
     on the tactile emboss plate with the rest on the arrow tips, never a dot.
     "Back"/"rear" seam mode is unsafe for the emboss plate by geometry, so
     there is NO export rotation - the guide tells such users to switch to
     Aligned.
   - Size is NOT a dial. app/geometry_spec.py owns SEAM_CHANNEL_WIDTH_MM 1.0,
     DEPTH 0.5, MARGIN 0.25, OVERSHOOT 1.0, LIP 0.5, MIN_WALL 1.2; index.html
     mirrors four of them and both omission sentences (a smoke test diffs
     them). Changing the groove needs Brennen's decision AND a new spike.
   - Flat name seam_channel_enabled (schema seam_channel.enabled, default
     true / 1); absent means ON. The Expert Mode switch #seam_channel_enabled
     (Surface Dimensions) is the ONLY thing that sends seam_channel_enabled: 0,
     and ON adds NOTHING to the request body - an untouched body is
     byte-identical to a pre-channel one (pinned against the captured
     tests/e2e/fixtures/*.request.json). Switch OFF reproduces the pre-channel
     STL byte for byte (tests/e2e/fixtures/*_before_seam_channel.stl).
   - Placement, VISUAL mode: signed arc s from the seam centre toward column
     0; the free window is what the last cell's dots and column 0's triangle
     leave of the gap, groove at its middle; theta = pi -/+ s_c/R
     (positive/negative), so theta_A + theta_B = 2 pi. theta is in the DOT
     convention: the worker negates EVERY theta it places (dots, markers,
     channel alike) - never treat this angle differently from a dot's. In the
     STL the default 15-column visual layout has the groove at 181.67 deg (A)
     / 178.33 (B).
   - Placement, TACTILE mode (D-T6, 2026-09-21, Brennen's call after testing
     the one-day "behind the arrow" placement): the groove runs down the
     ARROW COLUMN itself, theta = pi on BOTH plates, as TWO stretches that
     stop SEAM_CHANNEL_ARROW_MARGIN_MM 0.3 short of the arrow chain (block
     key `segments`: [{z_from, z_to}] about mid-height, each from the end
     face + overshoot to the chain, emitted in tactile mode only; a stretch
     under SEAM_CHANNEL_MIN_SEGMENT_MM 1.0 is dropped). The chain's extent
     comes from tactile_arrow_span(): the outermost row's arrow +/- length/2,
     grown by the recess clearance (counter) or the gear weld (emboss, gear
     mode) - the mitred recess APEX grows by clearance/sin(atan((w/2)/l)) =
     1.02 mm, not by the clearance. 13 cells, 4 rows, 0.4 preset: emboss
     (-27, -20.3) + (20.3, 27), counter (-27, -20.5) + (21.32, 27). There is
     no window to fit, so the gap rule never speaks in tactile mode; when the
     arrows reach both end faces the groove is left out with S-C4 (DRAFT).
     The groove never runs UNDER a raised arrow (a 0.3 mm tunnel and tip
     notches); across the chain the arrows' own corners hold the seam (the
     slicing study: 0 % of layers in a dot).
   - Left out, with a warning (S-C2 / S-C3 (signed 2026-09-21)), when the
     visual free window is under 1.5 mm or the wall under the apex is under
     1.2 mm (polygon circumradius, or wall_thickness - depth for a barrel
     with no cutout; solid barrels - gears, Version 2 - skip the wall rule).
     15 visual fits at 30.8; every tactile layout gets its groove (15 columns
     tactile trips the seam-GAP warning, not the channel's).
   - CSG order: the groove is cut from the BARE outer cylinder before the bore,
     the keyed pockets or anything unioned, in both the worker
     (createSeamChannelManifold - one prism per stretch when `segments` is
     present, else one full-height prism) and tests/test_golden.py
     (_seam_channel_cutter); all six golden pairs regenerated once on
     2026-09-20 (+8 triangles each, bounds unchanged), all eight again on
     2026-09-21 (D-T6).
   - Cards never get one.
   - OpenSCAD parity since v2.8.0 (2026-09-21): `seam_channel` switch in both
     .scad files with the same six constants (a test in that repo diffs them
     against app/geometry_spec.py) and the visual groove at the PHYSICAL
     angle 180 +/- s/R (emboss +, counter -) - the .scad negates nothing, so
     its 181.67 / 178.33 equals this worker's exported STL. The tactile
     stretches on the arrow column follow in the D-T6 pass (6g).

6f. One Generate / one Download (2026-09-21, sub-plan E of the 2026-09-20
   programme; D-8, D-9, D-10). Generate STL builds BOTH cylinders unless
   "Cylinders to Generate" - the FIRST Expert Mode submenu
   (#cylinders-to-generate-submenu / #expert-panel-cylinders) - names one:
   radios name="plate_selection" value both (checked) | positive | negative,
   read ONLY through currentPlateSelection() / currentPlateType() ('both'
   resolves to positive for single-plate wording). There is NO
   input[name="plate_type"] radio, NO #generate-both-btn, NO #pair-downloads
   and NO isPairModeOn()/updatePairModeUI() any more - pair mode is universal.
   The ONE #download-stl-btn saves the combined Cylinder_Pair_[Geared_][V2_]
   file after a both run, Cylinder A then B (pairFallbackQueue) after a failed
   combine, or the single file. Filenames NEVER changed (training videos).
   Persistence key stays braille_prefs_plate_type (old positive/negative
   values honoured). Strings S-E1..S-E7 signed 2026-09-21. e2e: single-plate specs
   choose Cylinder A in openApp() via tests/e2e/helpers/cylinders.ts
   (selectCylinders - the radio is in the collapsed panel, so check() would
   refuse it); pair tests choose 'both'. The submenu toggle focuses its first
   control after 100 ms - wait for it before arrow keys.

6g. Tactile arrow position and card fit (2026-09-21, decisions D-T1..D-T6
   after Brennen's printed 14-cell card ran out of paper at the end of every
   row while its start lay blank; plan 05_TACTILE_LEAD_IN_PLAN.md in the
   2026_09_20 research folder):
   - The arrow sits at the SEAM-GAP MIDPOINT, TACTILE_SEAM_THETA = pi, on
     both plates - equal space either side of it, last cell to arrow and
     arrow to first cell (D-T6). A fixed lead-in before column 0 (D-T1,
     "Option A") was built, pushed and REVERTED the same day: Brennen's test
     of the Vercel build showed the groove beside the arrows and a large
     trailing space after the last cell, and he asked for the groove centred
     on the arrows and the spacing back to even. Never re-shift the arrow on
     your own.
   - The card, not the cylinder, bounds a tactile row. The embosser is loaded
     with the card's leading edge AT the alignment arrow (D-T3), so a row
     needs gap/2 + grid + footprint of card (footprint = dot_spacing/2 + the
     widest dot or bowl radius, the seam channel's number; 2.15 at the 0.4
     preset): 13 cells need 89.5 mm of a 90 mm card, 14 need 92.8 (92.9 with
     the default dot families) and lose their last cell at ANY arrow
     position. app/geometry_spec.py tactile_card_need_mm / tactile_max_cells
     (max = floor((card - pi*D/2 - footprint) * 2 / cell) + 1) own it;
     index.html updateCardFitUI mirrors the arithmetic. Warning S-T1 (DRAFT)
     from card_width in spec warnings and the live #card-fit-warning box;
     tactile recommendation 13 (S-T3, DRAFT); the dial stays free to 14 with
     the warning, never a rejection. Visual mode is NOT checked (different
     alignment procedure). NOTE: a US 3.5 in card (88.9 mm) now warns at 13
     cells (max 12) - reported to Brennen 2026-09-21, not decided.
   - All eight golden pairs regenerated 2026-09-21 (twice: the lead-in, then
     D-T6); the fixture settings declare card_width 100 because the generator
     refuses a spec with warnings and the fixtures are 14-column geometry
     references.
   - interpoint.arrow_zone_margins(arrow_arc_mm=0.0) keeps its parameter
     (negative refused); the arrow is at pi, so callers pass nothing.
   - The seam channel in tactile mode runs down the arrow column in two
     stretches (6e). The slicing study reran on it (scripts/seam_spike.py
     --layouts tactile14,tactile13 --channels none,v10 --no-rear --out
     build/seam_spike_column): 0 % of layers in a dot on every plate, groove
     or not; 60 % (emboss) / 37 % (counter) of layers within 0.8 mm of arc
     of 180 deg, the rest on the arrows' own edges.
   - OpenSCAD: the lead-in parity (T6, a7585cc, pushed) is reworked to D-T6
     on that repo's develop; v2.8.1 and the re-vendor wait for Brennen's
     13-cell tactile print test.

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
    never edit it here. Its home is the GitHub repo
    **braille-cylinder-stl-generator-openscad** (the local clone sits in a folder
    named braille-stl-generator-openscad — the two spellings are the same repo;
    OpenSCAD/VENDORED.json and a test both pin the GitHub name).

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
| Integrated gears, one-piece rollers, gear assets | GEAR_INTEGRATED_ROLLERS_SPECIFICATIONS.md |
| Embosser Version 2, keyed gear pegs, key clearance | EMBOSSER_VERSION_2_KEYED_CUTOUTS_SPECIFICATIONS.md |
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
