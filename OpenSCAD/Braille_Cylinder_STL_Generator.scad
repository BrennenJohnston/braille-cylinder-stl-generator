// Braille Cylinder STL Generator (OpenSCAD) — MakerWorld Single-File Build
// Generates embossing plates and counter plates for cylindrical objects
//
// =============================================================================
// MAKERWORLD SINGLE-FILE BUILD
// =============================================================================
//  This file is the flattened, single-file build used to upload the generator
//  to MakerWorld's Parametric Model Maker, which accepts exactly one `.scad`
//  file and does not support local `include <...>` directives.
//
//  The canonical, dual-file DESKTOP version lives in the repository root:
//    ../Braille_Cylinder_STL_Generator.scad
//    ../presets.scad
//
//  This file is identical to the desktop main file from the
//  `BACKWARD COMPATIBILITY` marker to EOF (the geometry body); the only
//  difference is above that marker: the `include <presets.scad>;` line is
//  replaced inline with the body of `presets.scad` (wrapped in BEGIN/END
//  sentinel comments). Both files default `dot_shape` to "Rounded". See
//  ./README.md for the maintainer re-flatten procedure.
//  tests/test_makerworld_sync.py guards byte-identity of the geometry body
//  against the canonical file, AND compares every parameter declaration above
//  the marker - defaults, slider ranges and the DOUBLE-SIDED (INTERPOINT) MATH
//  constants - so a value can no longer drift on one side unnoticed. Comments
//  above the marker may still differ where this build needs its own wording.
//
// =============================================================================
// WHAT THIS MAKES
// =============================================================================
//  • Cylinder Emboss Plate (Raised Dots) — dots on outer cylinder surface
//  • Cylinder Counter Plate (Hemispherical Recesses) — recesses on outer surface
//
//  DOUBLE-SIDED CARD (BETA) — set double_sided = On to emboss BOTH faces of one
//  card in a single pass between the two cylinders. The same two plates take on
//  paired jobs, and each one then carries raised dots AND recesses:
//  • Cylinder A = the Embossing Plate. The FRONT text as raised dots, plus one
//    recessed seat for every BACK dot the other cylinder raises.
//  • Cylinder B = the Counter Plate. The BACK text as raised dots, plus one
//    recessed seat for every FRONT dot Cylinder A raises.
//  Two things change in this mode. There is NO universal recess grid — every
//  recess is the 1:1 partner of an actual dot, so a seat can never sit under
//  this plate's own raised dot. And the row indicators are always TACTILE (the
//  raised seam arrows), because the paired seats occupy the ground the Visual
//  marker columns would stand on, and a blind user needs the arrow to tell the
//  two cylinders apart. Choosing Visual while double_sided is On is overridden,
//  and the model says so on the console and in red text above the cylinder.
//  Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
//
// =============================================================================
// BEFORE YOU START
// =============================================================================
//  • Install OpenSCAD and open this .scad file
//  • In OpenSCAD, open View → Customizer to access all parameters
//  • This version requires pre-translated Unicode braille (no automatic translation)
//  • All parameters match the web-based generator UI for consistency
//
// =============================================================================
// TRANSLATE YOUR TEXT (REQUIRED) — BRANAH WORKFLOW
// =============================================================================
//  This OpenSCAD version does NOT include automatic translation. You must:
//  
//  1. Go to https://www.branah.com/braille-translator
//  2. In the options, select your desired braille grade:
//     - Grade 2 (contracted): Recommended for most uses
//     - Grade 1 (uncontracted): For names, emails, or when contractions cause confusion
//  3. Select Unicode Braille output (NOT ASCII Braille)
//  4. Type your English text in the left box
//  5. Copy the braille output (right box showing characters like ⠓⠑⠇⠇⠕)
//  6. In OpenSCAD's Customizer, paste into the Line_1, Line_2, etc. fields
//  7. DOUBLE-SIDED (BETA) only — the back of the card is translated exactly the
//     same way: same site, same grade, Unicode Braille output. Paste that
//     output into the Back_Line_1, Back_Line_2, … fields under the
//     [Double-Sided Card (BETA)] tab. Back lines obey the same rules as the
//     front — pre-translated Unicode braille only, same cell capacity per row,
//     same row limit — and the same warnings cover them.
//
//  IMPORTANT: If you paste ordinary English letters or see "INVALID CHARACTERS"
//  warning, re-translate on Branah and ensure Unicode Braille is selected.
//  Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
//
// =============================================================================
// QUICK START GUIDE
// =============================================================================
//  1. Translate your text at https://www.branah.com/braille-translator
//  2. Paste pre-translated braille into Line_1, Line_2, etc.
//  3. Raise grid_rows to at least the number of lines you filled in — only the
//     first grid_rows lines are rendered, and a "TOO MANY LINES" warning tells
//     you when text is being left off. Lines 9 and 10 live under the
//     [More Braille Lines (Advanced)] tab.
//  4. Choose plate_type: Embossing Plate or Counter Plate
//  5. Choose dot_shape: Rounded or Cone (affects both plates)
//  6. Adjust dimensions in Expert Mode if needed
//  7. Render (F6) → File → Export → STL
//  8. DOUBLE-SIDED (BETA): turn double_sided On, fill the Back_Line fields,
//     then render each plate_type once — export the Embossing Plate as
//     Cylinder_A_<your name>.stl and the Counter Plate as
//     Cylinder_B_<your name>.stl. The console prints the suggested name for
//     whichever plate you are rendering.
//     Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
//
// =============================================================================
// PARAMETER ORGANIZATION
// =============================================================================
//  Parameters are organized to match the web-based generator:
//
//  MAIN CONTROLS (always visible):
//  • Text Input - Pre-Translated Braille (Line_1 - Line_8)
//  • More Braille Lines (Advanced) (Line_9 - Line_10, the grid_rows maximum)
//  • Double-Sided Card (BETA) (the double_sided gate, Back_Line_1 -
//    Back_Line_10, and the two interpoint offsets)
//  • Plate Selection
//
//  EXPERT MODE (expandable submenus matching web UI):
//  • Expert Mode - Shape Selection (dot shapes, indicators)
//  • Expert Mode - Cylinder Dimensions
//  • Expert Mode - Braille Spacing (grid layout + positioning)
//  • Expert Mode - Braille Dot Adjustments (emboss/counter dimensions)
//
//  OPENSCAD-SPECIFIC:
//  • Rendering Quality
//
// =============================================================================
// REFERENCES
// =============================================================================
//  [1] Web-based Generator (with automatic translation): 
//      https://github.com/BrennenJohnston/braille-cylinder-stl-generator
//      https://braille-cylinder-stl-generator.vercel.app
//  [2] Branah Braille Translator: https://www.branah.com/braille-translator
//  [3] BANA — Size and Spacing: https://brailleauthority.org/size-and-spacing-braille-characters
//  [4] NLS — Specification 800: https://www.loc.gov/nls/
//  [5] 2010 ADA Standards: https://archive.ada.gov/
//
// =============================================================================
// ACKNOWLEDGMENTS
// =============================================================================
//  This OpenSCAD version is based on the web-based generator by Brennen Johnston.
//  Special thanks to Tobi Weinberg for the substantial time and effort volunteered
//  to help start the original project.
//
//  Original web app powered by Liblouis, an open-source professional braille
//  translator: https://liblouis.io/
// =============================================================================

/* [Text Input - Pre-Translated Braille] */
// Paste Unicode braille characters from https://www.branah.com/braille-translator
Line_1 = "⠓⠑⠇⠇⠕"; // First line of braille text
Line_2 = "⠺⠕⠗⠇⠙"; // Second line of braille text
Line_3 = ""; // Third line of braille text
Line_4 = ""; // Fourth line of braille text
Line_5 = ""; // Fifth line of braille text
Line_6 = ""; // Sixth line of braille text
Line_7 = ""; // Seventh line of braille text
Line_8 = ""; // Eighth line of braille text
// Show TEXT TOO LONG warning and clip rows to the cell capacity. Off = render every pasted character (rows may crowd the seam).
text_limit_check = "On"; // [On, Off]

/* [More Braille Lines (Advanced)] */
// Lines 9 and 10 reach the grid_rows maximum of 10. The Customizer cannot add
// fields on demand, so these live in their own tab rather than lengthening the
// text input above. Raise grid_rows under [Expert Mode - Braille Spacing] to
// match, and give the cylinder the height to hold them: 10 rows at the default
// 10 mm line_spacing needs about 100 mm.
Line_9 = ""; // Ninth line of braille text
Line_10 = ""; // Tenth line of braille text

/* [Double-Sided Card (BETA)] */
// BETA - emboss BOTH faces of one card in a single pass. On turns the two
// plates into a matched pair: the Embossing Plate becomes Cylinder A (front
// text raised, one seat per back dot) and the Counter Plate becomes Cylinder B
// (back text raised, one seat per front dot). Row indicators are forced to
// Tactile and the counter plate's universal recess grid is replaced by 1:1
// paired seats. Off is the normal single-sided workflow, unchanged.
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
double_sided = "Off"; // [Off, On]

// The BACK face's braille, one field per row, in the same row order as
// Line_1..Line_10 above. Pre-translated Unicode braille, translated exactly the
// way the front is (see BRANAH WORKFLOW at the top of this file). Read only
// while double_sided is On, so filling these changes nothing until you do.
//
// All ten rows live in this tab, unlike the front's 8 + 2 split. That split
// exists to keep the always-visible main text tab at eight fields; this tab is
// opt-in, so splitting it would only send a double-sided user to a second tab -
// one that also holds single-sided fields - to finish one job.
Back_Line_1 = ""; // First line of back-of-card braille text
Back_Line_2 = ""; // Second line of back-of-card braille text
Back_Line_3 = ""; // Third line of back-of-card braille text
Back_Line_4 = ""; // Fourth line of back-of-card braille text
Back_Line_5 = ""; // Fifth line of back-of-card braille text
Back_Line_6 = ""; // Sixth line of back-of-card braille text
Back_Line_7 = ""; // Seventh line of back-of-card braille text
Back_Line_8 = ""; // Eighth line of back-of-card braille text
Back_Line_9 = ""; // Ninth line of back-of-card braille text
Back_Line_10 = ""; // Tenth line of back-of-card braille text

// How far the back grid is shifted from the front grid, so a front dot and a
// back dot never land on the same patch of paper and flatten each other. The
// shift is diagonal: this is the part measured AROUND the cylinder (mm). The
// 1.25 / 1.25 default is the industry interpoint offset and the value the
// printed pairs were validated at; the 1.15-1.35 range is enforced, and a
// value outside it stops the render.
interpoint_offset_x_mm = 1.25; // [1.15:0.01:1.35]
// The other half of the same diagonal shift, measured ALONG the cylinder axis
// (mm) - back rows sit this far above the front rows.
interpoint_offset_y_mm = 1.25; // [1.15:0.01:1.35]

/* [Plate Selection] */
// Choose which plate to generate. In DOUBLE-SIDED (BETA) mode the two names
// take on the paired roles the web app uses: "Embossing Plate" IS Cylinder A
// and "Counter Plate" IS Cylinder B, exported as Cylinder_A_*.stl and
// Cylinder_B_*.stl. Single-sided keeps these names exactly as they are.
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
plate_type = "Embossing Plate"; // [Embossing Plate, Counter Plate]

/* [Indicator Mode] */
// How each row is marked for alignment. Visual = today's recessed triangle (plus the optional letter square) in marker cells at the start of every row. Tactile = a raised arrow on the embossing plate and a matching recess on the counter plate, centred in the seam gap and pointing at the cylinder top, so a blind user can find the alignment point and tell which end is up by touch. Tactile removes the marker cells (freeing them for text) and ignores the Indicator Letters toggle.
indicator_mode = "Visual"; // [Visual, Tactile]
// Tactile only: indicator width measured around the cylinder (mm)
tactile_indicator_width = 4.0; // [2:0.1:10]
// Tactile only: indicator length measured along the cylinder axis (mm). The default is long enough for a fingertip to read the direction of the point in one pass; at the 10 mm default line_spacing it also means each row's arrow meets the base of the one above.
tactile_indicator_length = 10.0; // [2:0.1:15]
// Tactile only: how far the embossing plate's arrow stands proud of the surface (mm). Keep this BELOW the braille dot height so the dots — not the indicator — carry the rolling pressure. It also sets the wall: a deeper raise means a deeper counter-plate recess, and the material left between that recess floor and the polygonal cutout gets thinner. 1.2 mm is the printable floor, and the model warns on the console and in red 3D text below it. Wording signed off by Brennen 2026-08-20.
tactile_indicator_raise = 0.5; // [0:0.1:2]
// Tactile only: outline margin added around the counter plate's recess (mm), so the arrow still enters the recess when the two cylinders are slightly misaligned.
tactile_recess_clearance = 0.2; // [0:0.05:1]
// Tactile only: counter recess depth added on top of the arrow raise (mm). 0 = exact same-depth nesting. Large values thin the wall between the recess and the polygonal cutout.
tactile_recess_extra_depth = 0.2; // [0:0.05:1]

/* [Paper Thickness Preset] */
// Preset optimized for paper thickness (sets multiple parameters below)
paper_thickness_preset = "0.4mm"; // [0.4mm, 0.3mm, Custom]

/* [Expert Mode - Shape Selection] */
// Braille Dot Shape (Emboss and Counter) - affects both plate types
// Defaults to "Rounded" (matching the canonical desktop file and the 0.4mm/0.3mm
// presets). The dropdown still offers both shapes.
dot_shape = "Rounded"; // [Rounded, Cone]
// Indicator Letters (Emboss and Counter) - VISUAL INDICATOR MODE ONLY (Tactile mode has no marker cells and ignores this). Square marker cutout next to the alignment triangle. Off frees 1 cell per row for braille text; the triangle alignment indicators are always included (they are critical to the mechanical device the cylinder mounts into).
indicators = "On"; // [On, Off]

/* [Expert Mode - Cylinder Dimensions] */
cylinder_diameter_mm = 30.8; // [10:0.1:100] Cylinder outer diameter in mm
cylinder_height_mm = 52; // [20:1:150] Cylinder height in mm
polygon_cutout_radius_mm = 13.0; // [0:0.1:50] Polygonal cutout circumscribed radius (0 = no cutout)
polygon_cutout_points = 12; // [3:1:24] Number of sides/points for polygonal cutout
seam_offset_degrees = 0.0; // [0:1:360] Seam offset (degrees) — Rotates starting position around cylinder

/* [Expert Mode - Braille Spacing] */
// --- Braille Dimensions ---
grid_columns = 13; // [1:1:20] Text capacity in braille cells per row (matches the web app default of 13 text cells; in Visual indicator mode, 2 extra marker cells are added when Indicator Letters are On, or 1 extra cell for the always-present alignment triangle when Off — up to 14 text cells fit the default cylinder with Indicator Letters Off. Tactile indicator mode adds no marker cells, so up to 14 text cells fit the default cylinder; 15 leaves too little seam gap for the indicator)
grid_rows = 4; // [1:1:10] Number of lines of braille
cell_spacing = 6.5; // [2:0.1:15] Horizontal spacing between cells (mm)
line_spacing = 10.0; // [5:0.1:25] Vertical spacing between lines (mm)
dot_spacing = 2.5; // [1:0.1:5] Spacing between dots within a cell (mm)

// --- Braille Positioning ---
// Note: on a cylinder, X = angular wrap around the seam — a linear "X adjust"
// has no useful meaning, so only the vertical adjust is exposed. Use
// `seam_offset_degrees` (Expert Mode - Cylinder Dimensions) to rotate the
// braille pattern around the cylinder axis.
braille_y_adjust = 0.0; // [-10:0.1:10] Vertical adjustment of braille pattern (mm)

/* [Expert Mode - Braille Dot Adjustments] */
// --- Embossing Braille Dot Dimensions (Rounded Shape) ---
rounded_dot_base_diameter = 1.5; // [0.5:0.1:3] Rounded dot base diameter (cone base) (mm)
rounded_dot_base_height = 0.5; // [0:0.1:2] Rounded dot base height (cone height) (mm)
rounded_dot_dome_diameter = 1.0; // [0.5:0.1:3] Rounded dome diameter (linked to cone flat top) (mm)
rounded_dot_dome_height = 0.5; // [0.1:0.1:2] Rounded dot dome height (mm)

// --- Embossing Braille Dot Dimensions (Cone Shape) ---
emboss_dot_base_diameter = 1.5; // [0.5:0.1:3] Cone dot base diameter (mm)
emboss_dot_height = 0.8; // [0.3:0.1:2] Cone dot height (mm)
emboss_dot_flat_hat = 0.4; // [0.1:0.1:2] Cone dot flat hat diameter (mm)

// --- Counter Braille Recessed Dot Dimensions (Rounded Shape / Bowl) ---
bowl_counter_dot_base_diameter = 1.8; // [0.5:0.1:5] Bowl recess base diameter (mm)
counter_dot_depth = 0.8; // [0.1:0.1:2] Bowl recess depth (mm)

// --- Counter Braille Recessed Dot Dimensions (Cone Shape) ---
cone_counter_dot_base_diameter = 1.9; // [0.5:0.1:3] Cone recess base diameter (mm)
cone_counter_dot_height = 0.7; // [0.3:0.1:2] Cone recess height (mm)
cone_counter_dot_flat_hat = 1.0; // [0.1:0.1:2] Cone recess flat hat diameter (mm)

/* [Rendering Quality] */
// Sphere quality for rounded shapes
render_quality = "Medium"; // [Low, Medium, High]
// Cone segments for cone shapes (8-32 range recommended)
cone_segments = 16; // [8:1:64] Number of segments for cone shapes

/* [Hidden] */
$fn = 32; // Resolution for curved surfaces

// Mathematical constants
PI = 3.14159265359;

// Preset value tables (PRESET_04, PRESET_03) and the preset_value() lookup
// helper are inlined below from presets.scad (MakerWorld's Parametric Model
// Maker accepts only one .scad file). For the dual-file desktop version see
// ../Braille_Cylinder_STL_Generator.scad + ../presets.scad. To re-flatten
// after updating upstream presets.scad, replace everything between the
// BEGIN/END sentinel comments with the new presets.scad body (the
// `/* [Hidden] */` marker, both preset tables, and both helper functions).

// ==== BEGIN inlined from presets.scad (MakerWorld single-file requirement) ====
/* [Hidden] */

// --------- 0.4mm Preset (Thicker Paper, Larger Dots) ---------
// NOTE: grid_columns and grid_rows are deliberately ABSENT from the preset
// tables. preset_value() falls back to the user's slider when a key is
// missing, so the sliders always govern text capacity — matching the web
// app, where thickness presets never override the columns/rows dials.
PRESET_04 = [
    // Spacing
    ["cell_spacing",                    6.5],
    ["line_spacing",                    10.0],
    ["dot_spacing",                     2.5],
    ["braille_y_adjust",                0.0],

    // Emboss Rounded
    ["rounded_dot_base_diameter",       1.5],
    ["rounded_dot_base_height",         0.5],
    ["rounded_dot_dome_diameter",       1.0],
    ["rounded_dot_dome_height",         0.5],

    // Emboss Cone
    ["emboss_dot_base_diameter",        1.5],
    ["emboss_dot_height",               0.8],
    ["emboss_dot_flat_hat",             0.4],

    // Counter Bowl
    ["bowl_counter_dot_base_diameter",  1.8],
    ["counter_dot_depth",               0.8],

    // Counter Cone
    ["cone_counter_dot_base_diameter",  1.9],
    ["cone_counter_dot_height",         0.7],
    ["cone_counter_dot_flat_hat",       1.0],

    // Cylinder
    ["cylinder_diameter_mm",            30.8],
    ["cylinder_height_mm",              52],
    ["polygon_cutout_radius_mm",        13],
    ["polygon_cutout_points",           12],
    ["seam_offset_degrees",             0.0],
];

// --------- 0.3mm Preset (Thinner Paper, Smaller Dots) ---------
PRESET_03 = [
    // Spacing (same as 0.4mm; grid_columns/grid_rows intentionally absent —
    // the sliders always govern text capacity)
    ["cell_spacing",                    6.5],
    ["line_spacing",                    10.0],
    ["dot_spacing",                     2.5],
    ["braille_y_adjust",                0.0],

    // Emboss Rounded (smaller)
    ["rounded_dot_base_diameter",       1.2],
    ["rounded_dot_base_height",         0.4],
    ["rounded_dot_dome_diameter",       0.8],
    ["rounded_dot_dome_height",         0.4],

    // Emboss Cone (smaller)
    ["emboss_dot_base_diameter",        1.2],
    ["emboss_dot_height",               0.6],
    ["emboss_dot_flat_hat",             0.2],

    // Counter Bowl (smaller)
    ["bowl_counter_dot_base_diameter",  1.5],
    ["counter_dot_depth",               0.5],

    // Counter Cone (smaller)
    ["cone_counter_dot_base_diameter",  1.5],
    ["cone_counter_dot_height",         0.5],
    ["cone_counter_dot_flat_hat",       0.8],

    // Cylinder (same as 0.4mm)
    ["cylinder_diameter_mm",            30.8],
    ["cylinder_height_mm",              52],
    ["polygon_cutout_radius_mm",        13],
    ["polygon_cutout_points",           12],
    ["seam_offset_degrees",             0.0],
];

// Low-level table lookup. Returns the value for `key` in `preset_list`, or
// `undef` if not found. Uses OpenSCAD's built-in `search()` against the
// first column of the `[key, value]` pair list.
//
// IMPORTANT OpenSCAD quirks (verified on OpenSCAD 2026.01.03):
//   - `search(key, list)`     — treats `key` as a SEQUENCE OF CHARACTERS
//                                and matches each char individually. Useless
//                                for multi-character keys like our preset
//                                names; produces wrong matches silently.
//   - `search([key], list)`   — treats `[key]` as a one-element vector of
//                                needles and does whole-string matching.
//                                Returns `[idx]` on a hit but `[[]]` on a
//                                miss — the return shape is INCONSISTENT
//                                between hit and miss.
//
// We use the wrapped form for whole-string matching and discriminate
// hit-vs-miss with `is_num(m[0])`: a hit means `m[0]` is the integer row
// index; a miss means `m[0]` is the empty list `[]`.
function preset_lookup(preset_list, key) =
    let (m = search([key], preset_list))
    is_num(m[0]) ? preset_list[m[0]][1] : undef;

// Public helper. Selects between the 0.4mm/0.3mm preset tables and the user's
// fallback value (typically a slider variable) based on `preset`. Returns
// `fallback` for "Custom", unrecognized preset names, or keys not present in
// the matched table.
function preset_value(preset, key, fallback) =
    let (val =
        preset == "0.4mm" ? preset_lookup(PRESET_04, key) :
        preset == "0.3mm" ? preset_lookup(PRESET_03, key) :
        undef)
    val == undef ? fallback : val;
// ==== END inlined from presets.scad ====

// =============================================================================
// DOUBLE-SIDED (INTERPOINT) MATH  -  BETA
// =============================================================================
//
// Double-sided ("interpoint") mode embosses BOTH faces of one card in a single
// pass between two counter-rotating cylinders. Each cylinder then carries raised
// dots (its own face's braille) AND recesses (to receive the other cylinder's
// dots) on the same surface. The back grid is shifted diagonally - the industry
// "interpoint" offset - so a front dot and a back dot never land on the same
// patch of paper and flatten each other.
//
// This section is the MATH: constants, pure functions, self-checks and range
// guards. The geometry that reads them lives further down, in
// ds_back_placements() and the two plate modules. The user-facing controls -
// `double_sided`, `Back_Line_1..10` and the two interpoint offsets - are in the
// [Double-Sided Card (BETA)] Customizer tab near the top of this file; the gate
// defaults to "Off", and with it Off nothing here changes a single byte of the
// rendered model.
//
// Ported from the web generator's app/geometry/interpoint.py, which stays the
// authoritative implementation. The numbers are the approved 2026-08-16
// interpoint research decisions D1/D2/D3, recorded next to each constant.
//
// PLACEMENT: this block sits ABOVE the BACKWARD COMPATIBILITY marker on purpose.
// Everything from that marker to EOF must stay byte-identical to the MakerWorld
// flattened build (tests/test_makerworld_sync.py), and that build is re-flattened
// in its own phase. Anything added below the marker breaks that guard - which is
// also why the Customizer tab above holds the parameters, and this block holds
// only what derives from them.

/* [Hidden] */
// Print the self-check echoes below. Off in normal renders so scripts\scad-check.ps1
// stays quiet; tests/test_interpoint_math_scad.py renders with this On. A test
// hook, not a user control, so it stays out of the Customizer.
ds_self_check = false;

// Normalized gate for the `double_sided` dropdown declared in the
// [Double-Sided Card (BETA)] tab. Accepts the Customizer's "On"/"Off" and the
// lowercase "on"/"off" the test system passes with -D, the same way plate_type
// and dot_shape accept both the label and a lowercase form. Declared here rather
// than beside is_emboss_plate / tactile_on in CALCULATED VALUES because that
// section lives past the MakerWorld sync marker.
ds_on = (double_sided == "On") || (double_sided == "on");

// Back-face counterpart of _all_lines, under the same contract: the single
// source of truth for the back content, so no geometry ever names a Back_Line_N.
_all_back_lines = [Back_Line_1, Back_Line_2, Back_Line_3, Back_Line_4, Back_Line_5,
                   Back_Line_6, Back_Line_7, Back_Line_8, Back_Line_9, Back_Line_10];

// -----------------------------------------------------------------------------
// D1 - THE INTERPOINT OFFSET (signed off 2026-08-16)
// -----------------------------------------------------------------------------
// The back grid sits 1.25 mm diagonally from the front grid. Source: US Patent
// 5,527,117 (Roy, Impact Devices, 1996). Sweeping the fully-populated
// 2.5 / 6.5 / 10.0 lattice confirms the diagonal is the optimum: it maximises the
// smallest front-to-back centre distance, at 1.767767 mm.
DS_OFFSET_MIN_MM = 1.15;  // smallest offset the guards below accept, mm
DS_OFFSET_MAX_MM = 1.35;  // largest offset the guards below accept, mm
// The peak of that sweep, and the default both offset sliders ship at. Clearance
// falls off SYMMETRICALLY either side of it - 1.15 and 1.35 measure the same
// 1.626 mm - so "move back toward this number" is the fix whichever end of the
// range a user has strayed to. Named here so the guard message below cannot
// drift from the value the sliders actually default to.
DS_OFFSET_OPTIMUM_MM = 1.25;

// -----------------------------------------------------------------------------
// D3 - WHICH WAY THE BACK GRID SHIFTS (signed off 2026-08-16)
// -----------------------------------------------------------------------------
// +1 = the back grid slides toward the END of the line; its features land LEFT
// of Cylinder A's raised arrows, seen from outside the cylinder with the top up.
// Physically confirmed 2026-08. If a printed pair ever crowds the unexpected
// side of the arrow, FLIP THIS SIGN FIRST - no clearance number can catch a
// wrong choice, because both signs measure exactly the same distances (the set
// of front-minus-back difference vectors already holds every vector and its
// negative).
DS_BACK_DIRECTION = 1;

// -----------------------------------------------------------------------------
// D2 - DOUBLE-SIDED FOOTPRINTS, "OPTION B" (signed off 2026-08-16)
// -----------------------------------------------------------------------------
// Double-sided needs smaller dots than single-sided, because raised dots and
// recesses now share one surface. At the shipped single-sided sizes only
// 0.118 mm of material is left between neighbours - below the 0.34 mm a 0.4 mm
// nozzle can print. Single-sided keeps today's sizes.
//
// These ship FIXED - no Customizer dials (2026-08-16) - as TWO packages keyed
// to paper_thickness_preset (Brennen 2026-08-20, research memory FD-8/FD-9):
// the print matrix showed one footprint cannot serve both card stocks. "0.3mm"
// is Option B, validated on 0.3 mm stock 2026-08-17 (nominal gap 0.518);
// anything else - the "0.4mm" default, and "Custom", which has no
// double-sided meaning - is Q2, the matrix winner validated on 0.4 mm stock
// 2026-08-20 (nominal gap 0.468, below the 0.50 reliable line BY DESIGN: the
// printed 0.428 mm ridge was measured printing clean). Keep in lockstep with
// the web repo's app/geometry/interpoint.py DS_FOOTPRINTS_BY_PRESET; the
// tests here pin both packages. Die heights above 1.0 mm scrape the
// embosser's cylinder-holder housing - never raise them without Brennen.
//
// There is deliberately NO dial and NO fallback switch. The rejected
// alternative, "Option A" (dot base dia 1.5 with the 1.3 bowl), leaves a
// 0.368 mm ridge - under the 0.50 mm reliable line and close to the 0.34 mm
// floor - and survives only as documented history in the web repo's
// docs/specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md. Reviving it
// would be a new decision, not a setting.
ds_use_03_package = (paper_thickness_preset == "0.3mm");
DS_DOT_BASE_DIA = 1.2;                            // both packages, mm
DS_DOT_BASE_H   = ds_use_03_package ? 0.4 : 0.5;  // raised dot base height, mm
DS_DOT_DOME_DIA = ds_use_03_package ? 0.8 : 1.0;  // dome diameter at the base, mm
DS_DOT_DOME_H   = ds_use_03_package ? 0.4 : 0.5;  // dome height, mm - total dot 0.8 / 1.0
DS_BOWL_DIA     = ds_use_03_package ? 1.3 : 1.4;  // paired recess opening diameter, mm
DS_BOWL_DEPTH   = 0.5;                            // both packages, mm

// Derived from the six numbers above, so editing one of them moves the geometry
// with it and no size is ever written twice.
DS_DOT_HEIGHT = DS_DOT_BASE_H + DS_DOT_DOME_H;   // total raised dot height, mm

// Dome and bowl are both spherical caps: R = (a^2 + h^2) / (2h) for an opening
// radius a and a height/depth h. Same formula the single-sided dot and the
// counter plate's bowl already use.
DS_DOT_DOME_R = ((DS_DOT_DOME_DIA / 2) * (DS_DOT_DOME_DIA / 2) + DS_DOT_DOME_H * DS_DOT_DOME_H)
                / (2 * DS_DOT_DOME_H);
DS_BOWL_R     = ((DS_BOWL_DIA / 2) * (DS_BOWL_DIA / 2) + DS_BOWL_DEPTH * DS_BOWL_DEPTH)
                / (2 * DS_BOWL_DEPTH);

// WHAT THE BOWL ACTUALLY IS, and why DS_BOWL_DEPTH is not its depth.
//
// The bowl's sphere is centred ON the shell surface, not outside it, so the cut
// is a HEMISPHERE of radius DS_BOWL_R:
//
//     printed depth = DS_BOWL_R          (NOT DS_BOWL_DEPTH)
//     printed mouth = 2 * DS_BOWL_R      (NOT DS_BOWL_DIA)
//
// At the 0.3 package's 1.3 / 0.5 that is 0.6725 mm deep and 1.345 mm across; at
// the 0.4 package's 1.4 / 0.5 it is 0.7400 mm deep and 1.480 mm across. DS_BOWL_DIA
// and DS_BOWL_DEPTH are shape inputs to DS_BOWL_R above and nothing more; any sum
// computed from them directly is wrong. Note DS_BOWL_R is MINIMISED at
// DS_BOWL_DEPTH = DS_BOWL_DIA / 2, so over part of the range raising the depth
// makes the printed bowl SHALLOWER (0.5 -> 0.70 goes 0.6725 -> 0.6518 mm).
//
// This matches static/workers/csg-worker-manifold.js in the web repo
// (radialOffset = cylRadius), which is the authoritative convention by Brennen's
// decision of 2026-08-19: it is the geometry that has actually been printed and
// embossed. The web app's own Python renderer, and the SINGLE-SIDED
// counter_recess() below, both use the other convention - centre (R - depth)
// outside the surface, cut exactly the nominal depth. Single-sided is
// deliberately left alone: changing it would move every counter plate in use.

// Printability thresholds for the material left between a raised dot and a
// neighbouring recess on the same surface (Bambu X1C, 0.4 mm nozzle: Arachne
// widens anything from 0.1 to 0.34 mm up to 0.34 mm, and drops anything below
// 0.1 mm entirely).
DS_GAP_RELIABLE = 0.50;   // comfortably printable, mm
DS_GAP_FLOOR    = 0.34;   // hard minimum, enforced by the guard below, mm

// The crowding line the PHYSICAL "DOTS TOO CLOSE" text (past the sync marker)
// fires at. The 0.3 package was validated ABOVE the reliable line, so falling
// below it there is a real regression. The 0.4 package sits below the reliable
// line BY DESIGN (0.468 nominal; printed ridge 0.428, measured clean
// 2026-08-20), so for it the physical warning would only apply below the
// floor - where the guard assert already stops the render first. In effect the
// 0.4 package never renders the text; the self-check echoes still report the
// gap. This threshold split was RATIFIED by Brennen 2026-08-20, together with
// the decision that the assert - and only the assert - measures the printed
// ridge instead of the nominal one. The warning stays on the nominal figure so
// it keeps reporting the same number as the web app's checkDoubleSidedGap.
DS_GAP_ACCEPTED = ds_use_03_package ? DS_GAP_RELIABLE : DS_GAP_FLOOR;

// Axial step between the front rows and the back rows: back rows sit 1.25 mm
// higher than front rows. Same number as the interpoint_offset_y_mm default, and
// unused by the maths in this phase - it is the nominal the row placement in a
// later phase builds on.
DS_AXIAL_STEP = 1.25;

// -----------------------------------------------------------------------------
// THE REFERENCE LATTICE THE CLEARANCE SWEEP RUNS ON
// -----------------------------------------------------------------------------
// Mirrors of the canonical grid defaults, not a new source: the same
// 2.5 / 6.5 / 10.0 mm the braille spacing sliders default to. Interpoint offsets
// the back grid; it never re-spaces braille. These are deliberately constants
// rather than reads of active_dot_spacing and friends, so the reported clearance
// is always the documented worst case - the same number interpoint.py reports.
DS_DOT_PITCH  = 2.5;      // dot-to-dot inside one cell, mm
DS_CELL_PITCH = 6.5;      // cell-to-cell along a row, mm
DS_LINE_PITCH = 10.0;     // row-to-row, mm

// Sweep bounds, matching interpoint.py's TACTILE_COLUMNS and GRID_ROWS. The
// answer does not actually depend on them - the closest pair is always inside a
// single cell - but they are pinned so this file and the web repo report the
// same number from the same sweep.
DS_LATTICE_COLS = 14;
DS_LATTICE_ROWS = 4;

// The fixed dot map, [row, col] for dots 1-6. Identical to `dot_positions` in
// the geometry section; declared separately only because that one lives past the
// MakerWorld sync marker. Never reorder either copy.
DS_DOT_MAP = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]];

// -----------------------------------------------------------------------------
// PURE FUNCTIONS
// -----------------------------------------------------------------------------

// Every dot position of a fully-populated grid: all six dots of every cell of
// every row, as [x, y] in mm, x along the row and y up the cylinder. This is the
// worst case for same-surface crowding - real text never fills every position,
// but a counter plate's recesses may, and a user can type text that does.
function ds_lattice_points(cols       = DS_LATTICE_COLS,
                           rows       = DS_LATTICE_ROWS,
                           dot_pitch  = DS_DOT_PITCH,
                           cell_pitch = DS_CELL_PITCH,
                           line_pitch = DS_LINE_PITCH) =
    let (col_offsets = [-dot_pitch / 2, dot_pitch / 2],
         row_offsets = [dot_pitch, 0, -dot_pitch])
    [ for (col = [0 : cols - 1])
        for (row = [0 : rows - 1])
          for (d = DS_DOT_MAP)
            [ col * cell_pitch + col_offsets[d[1]],
              -row * line_pitch + row_offsets[d[0]] ] ];

// Smallest centre-to-centre distance, in mm, between a front feature and a back
// one. The back lattice is the front lattice mirrored and then translated, but a
// fully-populated grid is symmetric about its own centre, so the mirror maps it
// onto itself and the worst case reduces to a pure translation by the interpoint
// offset. DS_BACK_DIRECTION is applied so the code says which way the back grid
// goes; it provably cannot change the answer (see D3 above).
function ds_lattice_min_center_distance(offx, offy,
                                        cols       = DS_LATTICE_COLS,
                                        rows       = DS_LATTICE_ROWS,
                                        dot_pitch  = DS_DOT_PITCH,
                                        cell_pitch = DS_CELL_PITCH,
                                        line_pitch = DS_LINE_PITCH) =
    let (pts     = ds_lattice_points(cols, rows, dot_pitch, cell_pitch, line_pitch),
         shift_x = DS_BACK_DIRECTION * offx,
         shift_y = DS_BACK_DIRECTION * offy)
    sqrt(min([ for (b = pts)
                 min([ for (f = pts)
                         let (dx = f[0] - (b[0] + shift_x),
                              dy = f[1] - (b[1] + shift_y))
                         dx * dx + dy * dy ]) ]));

// Material left between a raised dot and its nearest neighbouring recess, in mm.
// Both live on the same cylinder surface: one face's raised dots and the recesses
// that receive the other face's dots. NEGATIVE means the two footprints overlap
// and the printed ridge between them does not exist. Compare against
// DS_GAP_RELIABLE (0.50 mm) and DS_GAP_FLOOR (0.34 mm).
function ds_same_surface_min_gap(dot_dia, recess_dia, offx, offy,
                                 cols       = DS_LATTICE_COLS,
                                 rows       = DS_LATTICE_ROWS,
                                 dot_pitch  = DS_DOT_PITCH,
                                 cell_pitch = DS_CELL_PITCH,
                                 line_pitch = DS_LINE_PITCH) =
    ds_lattice_min_center_distance(offx, offy, cols, rows, dot_pitch, cell_pitch, line_pitch)
    - (dot_dia + recess_dia) / 2;

// -----------------------------------------------------------------------------
// SELF-CHECKS
// -----------------------------------------------------------------------------
// Values with known answers, so a change to the maths above is caught at
// once instead of silently shifting every clearance. Printed only when
// ds_self_check is true, and independent of double_sided - the functions are
// pure, so they can be checked with the feature Off.
// tests/test_interpoint_math_scad.py renders with -D ds_self_check=true and
// asserts every expected key to +/-0.001 mm.
//   gap_package_03    Option B (dot 1.2, bowl 1.3) - above the reliable line
//   gap_package_04    Q2 (dot 1.2, bowl 1.4) - marginal BY DESIGN; the printed
//                     0.428 mm ridge was measured clean 2026-08-20
//   gap_active        the same gap for the ACTIVE preset's package
//   gap_active_printed  the SAME gap measured on the bowl's PRINTED mouth
//                     (2 * DS_BOWL_R) instead of its nominal diameter. The bowl
//                     is cut as a hemisphere centred on the surface, so its
//                     mouth is wider than DS_BOWL_DIA and the real ridge is
//                     narrower than every gap above it: 0.495 mm for the 0.3
//                     package where the nominal says 0.518, and 0.428 mm for
//                     the 0.4 package where the nominal says 0.468. The
//                     printability ASSERT measures this number (Brennen's
//                     decision 2026-08-20); the DOTS TOO CLOSE text keeps
//                     reporting the nominal, so it stays the same figure the
//                     web app's checkDoubleSidedGap and app/geometry_spec.py
//                     show. Echoed at the fixed 1.25 / 1.25 reference offsets,
//                     like every gap above it - the guard's own live value is
//                     ds_printed_ridge_mm, further down.
//   gap_single_sided  the web app's single-sided sizes - the documented failure
//                     case, below the 0.34 mm floor
//   gap_legacy_cone   the legacy cone footprints - negative, i.e. overlapping
// The four values after them are the derived footprint geometry the paired dot
// and recess are actually built from, echoed so the cut depth this file produces
// can be cited without opening a mesh.
if (ds_self_check) {
    echo("DS_SELFCHECK: every value below is mm");
    echo(str("DS_SELFCHECK lattice_1_25_1_25=", ds_lattice_min_center_distance(1.25, 1.25)));
    echo(str("DS_SELFCHECK lattice_1_25_0=",    ds_lattice_min_center_distance(1.25, 0)));
    echo(str("DS_SELFCHECK gap_package_03=",    ds_same_surface_min_gap(1.2, 1.3, 1.25, 1.25)));
    echo(str("DS_SELFCHECK gap_package_04=",    ds_same_surface_min_gap(1.2, 1.4, 1.25, 1.25)));
    echo(str("DS_SELFCHECK gap_active=",        ds_same_surface_min_gap(DS_DOT_BASE_DIA, DS_BOWL_DIA, 1.25, 1.25)));
    echo(str("DS_SELFCHECK gap_active_printed=", ds_same_surface_min_gap(DS_DOT_BASE_DIA, 2 * DS_BOWL_R, 1.25, 1.25)));
    echo(str("DS_SELFCHECK gap_single_sided=",  ds_same_surface_min_gap(1.5, 1.8, 1.25, 1.25)));
    echo(str("DS_SELFCHECK gap_legacy_cone=",   ds_same_surface_min_gap(1.8, 1.8, 1.25, 1.25)));
    echo(str("DS_SELFCHECK dot_height=",         DS_DOT_HEIGHT));
    echo(str("DS_SELFCHECK dot_dome_r=",         DS_DOT_DOME_R));
    echo(str("DS_SELFCHECK bowl_sphere_r=",      DS_BOWL_R));
    echo(str("DS_SELFCHECK bowl_printed_mouth=",  2 * DS_BOWL_R));
}

// The ridge the printability guard measures, at the user's ACTUAL offsets: the
// material left between a raised dot and its neighbouring recess, using the
// bowl's PRINTED mouth (2 * DS_BOWL_R) rather than its nominal diameter.
//
// Brennen's decision, 2026-08-20: the hard guard measures what actually prints.
// The bowl is cut as a hemisphere centred on the shell surface, so its mouth is
// wider than DS_BOWL_DIA and the nominal figure OVERSTATES the ridge - by
// 0.023 mm for the 0.3 package and 0.040 mm for the 0.4 package. That gap is
// exactly the band where the old nominal guard let through a ridge the printer
// cannot hold. The DOTS TOO CLOSE warning below deliberately still reports the
// nominal, matching the web app's checkDoubleSidedGap and app/geometry_spec.py;
// only the assert moved, so no warning threshold had to be re-decided.
//
// Consequence, measured: with the shipped 0.4 package the renderable offset band
// is 1.19-1.31 mm rather than the slider's full 1.15-1.35. The 0.3 package keeps
// the whole range (its worst case is 0.354 mm, still above the floor). Clearance
// peaks at DS_OFFSET_OPTIMUM_MM and falls off symmetrically, so both ends fail
// together and moving back toward the middle is always the fix.
ds_printed_ridge_mm = ds_on
    ? ds_same_surface_min_gap(DS_DOT_BASE_DIA, 2 * DS_BOWL_R,
                              interpoint_offset_x_mm, interpoint_offset_y_mm)
    : 0;

// -----------------------------------------------------------------------------
// GUARDS
// -----------------------------------------------------------------------------
// Active only when double_sided is On. A failed assert stops the render and
// fails scripts\scad-check.ps1 - that is the point. A pair printed outside these
// ranges will not register, and nothing in a rendered preview would show it.
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
if (ds_on) {
    assert(interpoint_offset_x_mm >= DS_OFFSET_MIN_MM &&
           interpoint_offset_x_mm <= DS_OFFSET_MAX_MM,
           "interpoint_offset_x_mm outside 1.15-1.35 range");
    assert(interpoint_offset_y_mm >= DS_OFFSET_MIN_MM &&
           interpoint_offset_y_mm <= DS_OFFSET_MAX_MM,
           "interpoint_offset_y_mm outside 1.15-1.35 range");
    assert(ds_printed_ridge_mm >= DS_GAP_FLOOR,
           str("double-sided dots and recesses too close to print: this offset ",
               "leaves only ", round(ds_printed_ridge_mm * 1000) / 1000,
               " mm of material between a raised dot and the recess beside it, ",
               "and ", DS_GAP_FLOOR, " mm is the printable minimum. Clearance is ",
               "widest with both interpoint offsets at ", DS_OFFSET_OPTIMUM_MM,
               " mm and narrows toward either end of the range, so move them ",
               "back toward ", DS_OFFSET_OPTIMUM_MM,
               " mm - or select the 0.3mm card stock preset, which pairs the ",
               "same dot with a smaller bowl and accepts the whole range."));
}

// =============================================================================
// BACKWARD COMPATIBILITY - Test System Parameters
// =============================================================================
// The automated test system passes parameters via -D flags using these names.
// These hidden parameters allow the test system to work without modification.
//
// Usage: openscad -D 'combined_shape="rounded"' -D 'indicator_shapes="on"' ...
//
// IMPORTANT: keep this `/* [Hidden] */` marker so OpenSCAD's Customizer
// never renders these four vars as orphan, uncategorized sliders even if
// a new `/* [Section] */` heading gets inserted above this block later.
/* [Hidden] */
combined_shape = "";         // "rounded" or "cone" (from test system)
indicator_shapes = "";       // "on" or "off" (from test system)
hemisphere_quality = "";     // "low", "medium", "high" (from test system)
shape_type = "";             // "cylinder" (from test system, ignored - cylinder only)

// =============================================================================
// CALCULATED VALUES (Do not modify)
// =============================================================================

// Normalize dropdown selections to internal values
// Support both UI dropdowns (human-friendly) and test system parameters (lowercase)
is_emboss_plate = (plate_type == "positive") ? true :
                  (plate_type == "negative") ? false :
                  (plate_type == "Embossing Plate");

use_rounded_dots = (combined_shape == "rounded") ? true :
                   (combined_shape == "cone") ? false :
                   (dot_shape == "Rounded");

indicator_on = (indicator_shapes == "on") ? true :
               (indicator_shapes == "off") ? false :
               (indicators == "On");

// Tactile indicator mode replaces the recessed marker columns with a raised
// arrow (emboss) / matching recess (counter) in the seam gap. It supersedes
// `indicator_on`, which only ever gates the Visual letter square.
//
// Double-sided mode is always tactile. Its two cylinders carry 1:1 paired
// recesses across the whole surface, which is exactly where the Visual marker
// columns would sit, and a blind user working a double-sided pair needs the
// seam arrow to tell the two cylinders apart. The web app refuses the
// combination outright; here it is forced, and warned about below.
tactile_on = (indicator_mode == "Tactile") || ds_on;

// Set when that forcing actually overrode a user's choice, so it can be both
// echoed and rendered as 3D warning text.
ds_forced_tactile = ds_on && (indicator_mode != "Tactile");

if (ds_forced_tactile)
    echo(str("WARNING: double_sided is On, so indicator_mode \"", indicator_mode,
             "\" has been overridden and this plate renders with tactile seam ",
             "arrows. Set indicator_mode = Tactile to clear this."));

// Double-sided renders come in pairs, and the two STLs have to be told apart
// after export. The names match the web app's double-sided flow, whose downloads
// are Cylinder_A_*.stl and Cylinder_B_*.stl; single-sided filenames are never
// renamed. Deliberately not a WARNING: it is a hint, and scripts\scad-check.ps1
// treats that token as a failure.
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
if (ds_on)
    echo(str("Double-sided: this render is Cylinder ", is_emboss_plate ? "A" : "B",
             " (the ", is_emboss_plate ? "Embossing Plate" : "Counter Plate",
             "). Suggested export filename: Cylinder_", is_emboss_plate ? "A" : "B",
             "_<your name>.stl"));

// Material left between a raised dot and its nearest neighbouring recess, both
// of which share this surface in double-sided mode. The 336-point lattice sweep
// behind it is only paid for when the mode is on.
ds_same_surface_gap = ds_on
    ? ds_same_surface_min_gap(DS_DOT_BASE_DIA, DS_BOWL_DIA,
                              interpoint_offset_x_mm, interpoint_offset_y_mm)
    : 0;
// Below DS_GAP_FLOOR the guard in the DOUBLE-SIDED MATH section has already
// stopped the render. DS_GAP_ACCEPTED is the reliable line for the 0.3 package
// but only the floor for the 0.4 package, whose marginal gap is design-accepted
// (see the DOUBLE-SIDED MATH section) - so with the 0.4 package this text is
// effectively retired: below the floor the assert fires first.
ds_dots_too_close = ds_on && (ds_same_surface_gap < DS_GAP_ACCEPTED);

// Map render quality to segment counts (support both UI and test system)
quality_fn = (hemisphere_quality == "low" || render_quality == "Low") ? 24 :
             (hemisphere_quality == "medium" || render_quality == "Medium") ? 32 :
             (hemisphere_quality == "high" || render_quality == "High") ? 64 : 32;

// =============================================================================
// PRESET ROUTING - Select preset vs. custom values
// =============================================================================
// Each `_preset_*` variable routes between the matching preset table entry
// (see presets.scad) and the user's slider value. If `paper_thickness_preset`
// is "0.4mm" or "0.3mm", the table value wins; otherwise the slider value
// (third argument) is used.

// Spacing parameters
_preset_grid_columns                   = preset_value(paper_thickness_preset, "grid_columns",                   grid_columns);
_preset_grid_rows                      = preset_value(paper_thickness_preset, "grid_rows",                      grid_rows);
_preset_cell_spacing                   = preset_value(paper_thickness_preset, "cell_spacing",                   cell_spacing);
_preset_line_spacing                   = preset_value(paper_thickness_preset, "line_spacing",                   line_spacing);
_preset_dot_spacing                    = preset_value(paper_thickness_preset, "dot_spacing",                    dot_spacing);
_preset_braille_y_adjust               = preset_value(paper_thickness_preset, "braille_y_adjust",               braille_y_adjust);

// Emboss Rounded parameters
_preset_rounded_dot_base_diameter      = preset_value(paper_thickness_preset, "rounded_dot_base_diameter",      rounded_dot_base_diameter);
_preset_rounded_dot_base_height        = preset_value(paper_thickness_preset, "rounded_dot_base_height",        rounded_dot_base_height);
_preset_rounded_dot_dome_diameter      = preset_value(paper_thickness_preset, "rounded_dot_dome_diameter",      rounded_dot_dome_diameter);
_preset_rounded_dot_dome_height        = preset_value(paper_thickness_preset, "rounded_dot_dome_height",        rounded_dot_dome_height);

// Emboss Cone parameters
_preset_emboss_dot_base_diameter       = preset_value(paper_thickness_preset, "emboss_dot_base_diameter",       emboss_dot_base_diameter);
_preset_emboss_dot_height              = preset_value(paper_thickness_preset, "emboss_dot_height",              emboss_dot_height);
_preset_emboss_dot_flat_hat            = preset_value(paper_thickness_preset, "emboss_dot_flat_hat",            emboss_dot_flat_hat);

// Counter Bowl parameters
_preset_bowl_counter_dot_base_diameter = preset_value(paper_thickness_preset, "bowl_counter_dot_base_diameter", bowl_counter_dot_base_diameter);
_preset_counter_dot_depth              = preset_value(paper_thickness_preset, "counter_dot_depth",              counter_dot_depth);

// Counter Cone parameters
_preset_cone_counter_dot_base_diameter = preset_value(paper_thickness_preset, "cone_counter_dot_base_diameter", cone_counter_dot_base_diameter);
_preset_cone_counter_dot_height        = preset_value(paper_thickness_preset, "cone_counter_dot_height",        cone_counter_dot_height);
_preset_cone_counter_dot_flat_hat      = preset_value(paper_thickness_preset, "cone_counter_dot_flat_hat",      cone_counter_dot_flat_hat);

// Cylinder parameters
_preset_cylinder_diameter_mm           = preset_value(paper_thickness_preset, "cylinder_diameter_mm",           cylinder_diameter_mm);
_preset_cylinder_height_mm             = preset_value(paper_thickness_preset, "cylinder_height_mm",             cylinder_height_mm);
_preset_polygon_cutout_radius_mm       = preset_value(paper_thickness_preset, "polygon_cutout_radius_mm",       polygon_cutout_radius_mm);
_preset_polygon_cutout_points          = preset_value(paper_thickness_preset, "polygon_cutout_points",          polygon_cutout_points);
_preset_seam_offset_degrees            = preset_value(paper_thickness_preset, "seam_offset_degrees",            seam_offset_degrees);

// =============================================================================
// ACTIVE PARAMETERS - Final values used by geometry
// =============================================================================
// These variables provide the final parameter values used by the geometry code.
// They incorporate both preset routing (above) and shape-based routing (rounded vs cone).

// Active emboss dot parameters (based on shape selection, using preset-routed values)
// Note: cone/rounded emboss modules consume the underlying _preset_* constants
// directly; only the composite height is needed at this layer.
// Double-sided ships its own FIXED footprint (Option B, signed off 2026-08-16):
// raised dots and recesses now share one surface, and at the single-sided sizes
// only 0.118 mm of material would be left between neighbours. So the ds gate
// wins over both the shape selection and the paper-thickness preset, and no
// dial reaches it. `braille_dot_for_plate` below routes the matching solid.
active_emboss_height = ds_on ? DS_DOT_HEIGHT :
                       use_rounded_dots ? (_preset_rounded_dot_base_height + _preset_rounded_dot_dome_height) : _preset_emboss_dot_height;

// Active counter dot parameters (based on shape selection, using preset-routed values)
active_counter_height = use_rounded_dots ? _preset_counter_dot_depth : _preset_cone_counter_dot_height;

// Active spacing parameters (pass through from preset routing)
active_grid_columns = _preset_grid_columns;
active_grid_rows = _preset_grid_rows;
active_cell_spacing = _preset_cell_spacing;
active_line_spacing = _preset_line_spacing;
active_dot_spacing = _preset_dot_spacing;
active_braille_y_adjust = _preset_braille_y_adjust;

// Active cylinder parameters (pass through from preset routing)
active_cylinder_diameter_mm = _preset_cylinder_diameter_mm;
active_cylinder_height_mm = _preset_cylinder_height_mm;
active_polygon_cutout_radius_mm = _preset_polygon_cutout_radius_mm;
active_polygon_cutout_points = _preset_polygon_cutout_points;
active_seam_offset_degrees = _preset_seam_offset_degrees;

// -----------------------------------------------------------------------------
// TACTILE INDICATOR CONSTANTS
// -----------------------------------------------------------------------------
// Declared here, ahead of the grid maths, because OpenSCAD evaluates top-level
// assignments strictly in source order — a constant used by a calculated value
// must already exist at that point. (Constants consumed only inside modules,
// like INDICATOR_OVERCUT below, can be declared later.)

// Clear zone required either side of the indicator, on top of its own width,
// before the seam gap is considered too tight (2 mm dot zone per neighbouring
// cell plus 1 mm of margin).
TACTILE_MIN_GAP_MARGIN = 5.0;

// Radial thickness of the working prism the arrow is extruded into. Must exceed
// raise + recess depth + base embed so the prism always straddles the shell
// surface; the shell band intersection is what sets the actual raise/depth.
TACTILE_PRISM_SPAN = 6;

// How far the raised arrow's base sinks below the shell surface, so the union
// with the shell is a solid overlap rather than a coplanar touch.
TACTILE_BASE_EMBED = 0.2;

// How far the recess cutter projects past the shell surface, so the cut opening
// never leaves coplanar faces behind.
TACTILE_RECESS_OVERCUT = 1;

// Grid dimensions. In Visual indicator mode the triangle alignment marker column
// is ALWAYS present (it has no user-facing toggle) and the indicator letter/square
// column is added only when Indicator Letters are On. Tactile mode has no marker
// columns at all — its indicator lives in the seam gap — so the grid is exactly
// the text cells and the freed space widens the gap.
actual_grid_columns = tactile_on ? active_grid_columns :
                      indicator_on ? (active_grid_columns + 2) : (active_grid_columns + 1);
grid_width = (actual_grid_columns - 1) * active_cell_spacing;

// Seam gap: the arc between the last and first cell centers, measured the long
// way around through the seam. The grid is centered on angle 0, so the middle of
// this gap is always exactly 180° — where the tactile indicator sits. Warn when
// the gap can no longer hold the indicator plus a clear zone either side of it.
seam_gap_mm = PI * active_cylinder_diameter_mm - grid_width;
tactile_gap_too_small = tactile_on && (seam_gap_mm < tactile_indicator_width + TACTILE_MIN_GAP_MARGIN);

if (tactile_gap_too_small)
    echo(str("WARNING: Tactile indicator needs a seam gap of at least ",
             tactile_indicator_width + TACTILE_MIN_GAP_MARGIN, " mm; the current layout leaves ",
             seam_gap_mm, " mm. Lower grid_columns or raise cylinder_diameter_mm."));

// The braille text, in row order. This list is the single source of truth for
// the content: every capacity check, warning, and geometry loop reads it, never
// a Line_N name. Adding a row means declaring Line_N in the text input section
// above, appending it here, and raising the grid_rows slider max to match.
_all_lines = [Line_1, Line_2, Line_3, Line_4, Line_5,
              Line_6, Line_7, Line_8, Line_9, Line_10];

// Text-capacity check. Text capacity is always active_grid_columns; in Visual mode
// the grid is widened by 2 marker cells when Indicator Letters are On, or by 1 (the
// alignment triangle) when Off, and Tactile mode adds none, so text capacity is
// unchanged in every case. The check (and row clipping) can be bypassed with
// text_limit_check = "Off", which renders every pasted cell — rows may then crowd
// the seam.
//
// Double-sided: ds_back_placements() clips back columns to active_grid_columns
// and back rows to active_grid_rows exactly as the front walk does, so the back
// lines are measured by the same two checks and the WIDEST row on either face
// decides. With the gate Off the back lines are never read and both numbers are
// the front's, unchanged.
_front_max_line_len = max([for (l = _all_lines) len(l)]);
_back_max_line_len  = ds_on ? max([for (l = _all_back_lines) len(l)]) : 0;
max_line_len = max(_front_max_line_len, _back_max_line_len);
text_too_long = (text_limit_check == "On") && (max_line_len > active_grid_columns);

// Row-capacity check. Only the first active_grid_rows rows are ever rendered, so
// text pasted into a line past that limit vanishes with nothing to show for it.
// rows_used is the index of the last non-empty line + 1, which preserves blank
// rows deliberately left between filled ones. Unlike the cell-capacity check this
// is not gated on text_limit_check: extra rows cannot be rendered anyway, there is
// no "draw it regardless" option to opt into. The DEEPEST row on either face wins.
_filled_row_idx = [for (i = [0 : len(_all_lines) - 1]) if (len(_all_lines[i]) > 0) i];
_front_rows_used = len(_filled_row_idx) == 0 ? 0 : _filled_row_idx[len(_filled_row_idx) - 1] + 1;
_filled_back_row_idx = ds_on
    ? [for (i = [0 : len(_all_back_lines) - 1]) if (len(_all_back_lines[i]) > 0) i]
    : [];
_back_rows_used = len(_filled_back_row_idx) == 0
    ? 0
    : _filled_back_row_idx[len(_filled_back_row_idx) - 1] + 1;
rows_used = max(_front_rows_used, _back_rows_used);
too_many_rows = rows_used > active_grid_rows;

// Console diagnostics for desktop users (the MakerWorld customizer preview
// cannot show console output — it relies on the extruded 3D warning text). Each
// message names the field that actually overflowed, so a double-sided user is
// never sent hunting through the front text for a back-line problem.
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
if (text_limit_check == "On") {
    for (i = [0 : len(_all_lines) - 1])
        if (len(_all_lines[i]) > active_grid_columns)
            echo(str("WARNING: Line_", i + 1, " uses ", len(_all_lines[i]), " cells; capacity is ", active_grid_columns, ". Raise grid_columns, split across rows, or set text_limit_check = Off."));
    if (ds_on)
        for (i = [0 : len(_all_back_lines) - 1])
            if (len(_all_back_lines[i]) > active_grid_columns)
                echo(str("WARNING: Back_Line_", i + 1, " uses ", len(_all_back_lines[i]), " cells; capacity is ", active_grid_columns, ". Raise grid_columns, split across rows, or set text_limit_check = Off."));
}
if (too_many_rows) {
    if (_front_rows_used > active_grid_rows)
        echo(str("WARNING: text reaches Line_", _front_rows_used, " but grid_rows is ", active_grid_rows,
                 ", so Line_", active_grid_rows + 1, " onward will not be rendered. Raise grid_rows to ",
                 _front_rows_used, " (the cylinder needs roughly ", _front_rows_used * active_line_spacing,
                 " mm of height to hold that many rows)."));
    if (_back_rows_used > active_grid_rows)
        echo(str("WARNING: back text reaches Back_Line_", _back_rows_used, " but grid_rows is ", active_grid_rows,
                 ", so Back_Line_", active_grid_rows + 1, " onward will not be rendered. Raise grid_rows to ",
                 _back_rows_used, " (the cylinder needs roughly ", _back_rows_used * active_line_spacing,
                 " mm of height to hold that many rows)."));
}
grid_height = (active_grid_rows - 1) * active_line_spacing;
top_margin = (active_cylinder_height_mm - grid_height) / 2;

// Cylinder grid geometry — shared by cylinder_emboss_plate and
// cylinder_counter_plate. Both modules used to recompute these identically
// inline; hoisting them keeps the two plates in lockstep so any spacing
// change automatically applies to both. Names mirror the prior local names
// so the module bodies need no changes beyond removing the duplicates.
radius                = active_cylinder_diameter_mm / 2;
grid_angle            = grid_width / radius;
start_angle           = -grid_angle / 2;
cell_spacing_angle    = active_cell_spacing / radius;
dot_spacing_angle     = active_dot_spacing / radius;
dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2];
dot_row_offsets       = [active_dot_spacing, 0, -active_dot_spacing];
dot_positions         = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]];

// Counter plate recess radii (spherical cap formula to match web generator)
// For a bowl recess: R = (a² + h²) / (2h) where a = opening radius, h = depth
// This ensures the opening diameter = bowl_counter_dot_base_diameter and depth = counter_dot_depth
_bowl_a = _preset_bowl_counter_dot_base_diameter / 2;
_bowl_h = _preset_counter_dot_depth;
bowl_recess_radius = (_bowl_a * _bowl_a + _bowl_h * _bowl_h) / (2 * _bowl_h);
bowl_center_offset = bowl_recess_radius - _bowl_h;

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

// Check if a character is valid Unicode braille (U+2800 to U+28FF)
function is_braille_char(c) = (c >= 10240 && c <= 10495);

// Check if string contains invalid characters
function has_invalid_chars(str) = 
    len(str) == 0 ? false : 
    len([for (i = [0:len(str)-1]) if (!is_braille_char(ord(str[i]))) i]) > 0;

// Get the 6-dot pattern from a Unicode braille character
function get_dot_pattern(char) =
    let(code = ord(char))
    (code >= 10240 && code <= 10495) ?
        let(pattern = code - 10240)
        [
            (pattern % 2) >= 1 ? 1 : 0,              // Dot 1
            floor(pattern / 2) % 2 >= 1 ? 1 : 0,     // Dot 2
            floor(pattern / 4) % 2 >= 1 ? 1 : 0,     // Dot 3
            floor(pattern / 8) % 2 >= 1 ? 1 : 0,     // Dot 4
            floor(pattern / 16) % 2 >= 1 ? 1 : 0,    // Dot 5
            floor(pattern / 32) % 2 >= 1 ? 1 : 0     // Dot 6
        ]
    : [0,0,0,0,0,0]; // Empty pattern for non-braille

// =============================================================================
// $fn TESSELLATION POLICY
// =============================================================================
//
// Every curved-surface primitive below picks its $fn from exactly one source
// based on what kind of surface it is. The five sources are intentionally
// segregated (not competing) — pick whichever matches your geometry class:
//
//   1. CYLINDER_SHELL_FN = 64   — the outer cylinder shell, and any band
//      concentric with it (the tactile indicator's shell_band). Hardcoded so
//      the visual roundness of the printable face matches the web preview's
//      three.js mesh exactly. Fixture STLs depend on this; never make it
//      user-tweakable. Sharing the constant is also what keeps the tactile
//      raise/recess radially uniform: band and shell tessellate identically,
//      so their radial difference is constant across the whole arrow.
//
//   2. cone_segments  (slider)  — every cone/frustum primitive (emboss dot
//      base/sides, cone counter recess). User-controllable 8..64; default 16.
//      Cones are the cheapest primitive, so a low default keeps render time
//      low while still allowing the user to crank it up for final exports.
//
//   3. quality_fn  (derived)    — every SPHERE primitive (the rounded dome
//      on top of an emboss dot, and the spherical-cap bowl counter recess).
//      Spheres cost O(n²) facets so we route them through a 3-step quality
//      dropdown: Low/24, Medium/32, High/64. The hemisphere_quality test
//      override also flows in here for cross-platform fixtures.
//
//   4. active_polygon_cutout_points (slider)  — the optional polygonal
//      cutout subtracted from the cylinder shell. $fn here is SEMANTIC: it
//      directly controls how many sides the cutout has (e.g. 6 for a hex
//      hole), so the value is the cutout's purpose, not its quality.
//
//   5. global $fn = 32 (default) — anything not in cases 1–4 (mainly 2D
//      shapes inside linear_extrude, where curvature isn't expressed).
//
// If you add a new curved primitive, pick the case that matches and pass
// its constant explicitly. Do not rely on the global $fn for any visible
// curved surface or you will silently desync from the web preview.
//
// =============================================================================
// INDICATOR SHAPE MODULES
// =============================================================================
//
// Reference: braille-cylinder-stl-generator/docs/specifications/
//   RECESS_INDICATOR_SPECIFICATIONS.md
//
// CRITICAL SEMANTICS:
// - Indicators are ALWAYS RECESSED (subtracted) for BOTH emboss and counter plates.
// - Cylinder layout:
//     Column 0: Triangle alignment marker — ALWAYS present, no user-facing toggle
//               (counter plate triangle rotated 180°)
//     Column 1: Rectangle (square) placeholder — only when Indicator Letters are On
//               (counter ALWAYS rectangle; emboss uses rect for braille input)
//
INDICATOR_TRIANGLE_DEPTH_EMBOSS = 0.6;
INDICATOR_RECT_DEPTH_EMBOSS     = 0.5;

// Radial epsilon pushed into the cylinder shell so recessed indicator
// markers and cone-counter recesses break coplanar boolean faces cleanly
// (without this, CGAL/Manifold can produce zero-area facets at the contact
// patch and STL exporters complain about non-manifold edges).
INDICATOR_OVERCUT = 0.05;

// Cylinder shell tessellation count. The cylinder is rendered as a regular
// prism; 64 segments gives near-cylindrical appearance at modest cost.
// Keep in sync with the web preview's three.js shell segments.
CYLINDER_SHELL_FN = 64;

// -----------------------------------------------------------------------------
// RAISED-DOT BASE EMBED
// -----------------------------------------------------------------------------
// Because the shell is a 64-sided prism, each facet dips SHELL_FACET_DIP inside
// the ideal radius at its centre. A raised dot whose flat base sits at exactly
// `radius` therefore spans that void and exports as a SEPARATE connected body:
// measured 2026-08-21, 32 bodies on the single-sided default and 6 / 9 on the
// double-sided pair, which is where the negative Genus readings came from.
// Sinking the base deeper than the dip fuses dot to shell.
//
// DERIVED, not a constant, because the dip scales with radius: 0.0186 mm at the
// shipped 30.8 mm but 0.0602 mm at the 100 mm ceiling, so any fixed figure small
// enough to be tidy leaves large cylinders floating (0.05 mm still splits a
// 100 mm cylinder into 7 bodies). The factor of two is the overlap margin - the
// same "overlap, never touch" rule INDICATOR_OVERCUT follows.
//
// This does NOT change how far a dot stands proud of the shell. The base frustum
// is LENGTHENED downward along its own taper, so its radius at `radius` is still
// the full base diameter and every surface at or above the shell is untouched -
// see braille_dot_centered(). Declared after CYLINDER_SHELL_FN for the same
// source-order reason as TACTILE_SEAM_WALL_MIN below.
SHELL_FACET_DIP = radius * (1 - cos(180 / CYLINDER_SHELL_FN));
DOT_BASE_EMBED  = SHELL_FACET_DIP * 2;

// "INVALID CHARACTERS" warning text placement (rendered above the cylinder
// when get_dot_pattern() returns the bad-pattern marker for an untranslated
// English glyph).
INVALID_TEXT_Z_OFFSET   = 5;   // mm above the cylinder top
INVALID_TEXT_SIZE       = 5;   // text() font size in mm
INVALID_TEXT_DEPTH      = 2;   // linear_extrude height in mm
// Pitch of the warning stack above INVALID CHARACTERS, one step per warning:
// TEXT TOO LONG, TACTILE GAP TOO SMALL, TOO MANY LINES, the two double-sided
// ones - DOUBLE-SIDED REQUIRES TACTILE and DOTS TOO CLOSE - then TACTILE WALL
// TOO THIN.
INVALID_TEXT_STACK_GAP  = 8;   // mm

// -----------------------------------------------------------------------------
// TACTILE SEAM-RECESS WALL GUARD
// -----------------------------------------------------------------------------
// The counter plate's arrow recess cuts inward toward the polygonal cutout, and
// nothing else stops a user thinning the wall between them below the 1.2 mm FDM
// printable minimum. The measured facts (Phase 08, taken off real STLs): the
// recess floor is the shell band's inner prism, whose faces dip to
// (radius - raise - extra depth) * cos(180 / CYLINDER_SHELL_FN); the cutout's
// VERTICES reach polygon_cutout_radius_mm / cos(180 / polygon_cutout_points),
// because the code treats that parameter as the INSCRIBED radius (see
// cylinder_shell). At the shipped defaults the wall is 14.682 - 13.459 =
// 1.224 mm - just clear; the pre-2026-08-18 raise of 0.8 mm left 0.924 mm,
// already under spec. Declared here, after CYLINDER_SHELL_FN: top-level
// assignments evaluate in source order, and an earlier reference would be
// undef and the guard would silently never fire.
TACTILE_SEAM_WALL_MIN = 1.2;   // FDM minimum printable wall, mm

tactile_seam_wall_mm =
    (radius - tactile_indicator_raise - tactile_recess_extra_depth)
        * cos(180 / CYLINDER_SHELL_FN)
    - (active_polygon_cutout_radius_mm / cos(180 / active_polygon_cutout_points));

tactile_seam_wall_too_thin = tactile_on && (active_polygon_cutout_radius_mm > 0)
    && (tactile_seam_wall_mm < TACTILE_SEAM_WALL_MIN);

// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
if (tactile_seam_wall_too_thin)
    echo(str("WARNING: only ", round(tactile_seam_wall_mm * 1000) / 1000,
             " mm of wall is left between the tactile arrow recess and the ",
             "polygonal cutout; the printable minimum is ", TACTILE_SEAM_WALL_MIN,
             " mm. Lower tactile_indicator_raise or tactile_recess_extra_depth, ",
             "or reduce polygon_cutout_radius_mm."));

module indicator_triangle_2d(rotate_180 = false) {
    // Isosceles triangle with vertical base on LEFT, apex RIGHT (default).
    // When rotate_180=true, triangle is rotated 180° about its center.
    polygon(points = rotate_180 ?
        [
            [+active_dot_spacing/2, +active_dot_spacing],
            [+active_dot_spacing/2, -active_dot_spacing],
            [-active_dot_spacing/2, 0]
        ] :
        [
            [-active_dot_spacing/2, -active_dot_spacing],
            [-active_dot_spacing/2, +active_dot_spacing],
            [+active_dot_spacing/2, 0]
        ]
    );
}

module indicator_rectangle_2d() {
    // Rectangle is NOT centered on the cell center; it is centered at (x + dot_spacing/2, y).
    translate([active_dot_spacing/2, 0])
        square([active_dot_spacing, 2 * active_dot_spacing], center = true);
}

module indicator_triangle_prism_centered(depth, rotate_180 = false) {
    translate([0, 0, -depth/2])
        linear_extrude(height = depth)
            indicator_triangle_2d(rotate_180 = rotate_180);
}

module indicator_rectangle_prism_centered(depth) {
    translate([0, 0, -depth/2])
        linear_extrude(height = depth)
            indicator_rectangle_2d();
}

// Cylinder marker placement helper
module place_cylinder_marker(theta_deg, y_pos, cyl_radius, depth, overcut = INDICATOR_OVERCUT) {
    radial_offset = cyl_radius - depth/2 + overcut;
    x = radial_offset * cos(theta_deg);
    y = radial_offset * sin(theta_deg);
    translate([x, y, y_pos])
        rotate([90, 0, theta_deg - 90])
            children();
}

// One row's indicator markers in EMBOSS orientation (positive angles).
// The counter plate renders these via mirror([0,1,0]) so it is an exact
// mirror of the emboss plate: triangle->rectangle center spacing is identical
// on both plates (mirrored pair) and the triangles point opposite ways.
module place_row_indicators(y_pos, tri_depth, rect_depth) {
    // Col 0: triangle alignment marker — ALWAYS placed (no user-facing toggle;
    // the triangles are critical to the mechanical device the cylinder mounts into).
    tri_theta_deg = start_angle * 180 / PI;
    place_cylinder_marker(tri_theta_deg, y_pos, radius, tri_depth)
        indicator_triangle_prism_centered(tri_depth, rotate_180 = true);

    // Col 1: rectangle (square) placeholder — only when Indicator Letters are On.
    if (indicator_on) {
        rect_theta_deg = (start_angle + cell_spacing_angle) * 180 / PI;
        place_cylinder_marker(rect_theta_deg, y_pos, radius, rect_depth)
            indicator_rectangle_prism_centered(rect_depth);
    }
}

// =============================================================================
// TACTILE INDICATOR MODULES
// =============================================================================
//
// Tactile mode drops the marker columns entirely and puts one indicator per row
// in the seam gap instead: RAISED on the embossing plate, RECESSED on the
// counter plate. Two properties make the pair work:
//
//   - Position. The grid is centred on angle 0, so the midpoint of the gap
//     between the last and first cells is always exactly 180°. The counter
//     plate is built by mirroring about the XZ plane / negating angles, and
//     180° is the fixed point of that transform — so the arrow and its recess
//     line up radially by construction, at any rotation of the paired
//     cylinders, with no extra bookkeeping.
//
//   - Shape. An isosceles triangle symmetric in the rolling direction, with its
//     apex toward the cylinder TOP. Circumferential symmetry means the mirrored
//     recess has exactly the same outline as the arrow, so the two nest instead
//     of colliding. Axial asymmetry means a blind user feels the point and knows
//     which end is up — on both plates — while raised-vs-recessed tells them
//     which cylinder they are holding.
//
// The raise is deliberately less than the braille dot height so the dots, never
// the indicator, carry the rolling pressure.

// Indicator outline in the local frame used by place_cylinder_marker children:
// +X runs circumferentially, +Y points at the cylinder TOP. Symmetric in X,
// apex at +Y.
module tactile_arrow_2d(w, l) {
    polygon(points = [[-w/2, -l/2], [w/2, -l/2], [0, l/2]]);
}

// A band concentric with the cylinder shell (see $fn TESSELLATION POLICY case 1).
// Intersecting the extruded outline with this band is what makes the raise and
// the recess depth radially uniform: a flat prism 4 mm wide on a 15.4 mm radius
// would lose ~0.13 mm at its edges to the chord sagitta, which is large next to
// a 0.2 mm nesting margin.
module tactile_shell_band(r_in, r_out) {
    difference() {
        cylinder(h = active_cylinder_height_mm,     r = r_out, center = true, $fn = CYLINDER_SHELL_FN);
        cylinder(h = active_cylinder_height_mm + 2, r = r_in,  center = true, $fn = CYLINDER_SHELL_FN);
    }
}

// Radial prism straddling the shell surface at 180° (the seam-gap centre).
// Passing cyl_radius = radius + span/2 with no overcut makes place_cylinder_marker
// put the child's origin exactly on the surface, so the prism reaches span/2 both
// outward and inward from it.
module tactile_surface_prism(y_pos, span) {
    place_cylinder_marker(180, y_pos, radius + span / 2, span, 0)
        translate([0, 0, -span / 2])
            linear_extrude(height = span)
                children();
}

// Raised arrow — union into the EMBOSS plate.
module tactile_raised(y_pos) {
    intersection() {
        tactile_surface_prism(y_pos, TACTILE_PRISM_SPAN)
            tactile_arrow_2d(tactile_indicator_width, tactile_indicator_length);
        tactile_shell_band(radius - TACTILE_BASE_EMBED, radius + tactile_indicator_raise);
    }
}

// Matching recess — subtract from the COUNTER plate. Grown by
// tactile_recess_clearance in the plane and tactile_recess_extra_depth radially
// so the arrow still enters when the two cylinders are slightly out of register.
module tactile_recess_cut(y_pos) {
    intersection() {
        tactile_surface_prism(y_pos, TACTILE_PRISM_SPAN)
            offset(delta = tactile_recess_clearance)
                tactile_arrow_2d(tactile_indicator_width, tactile_indicator_length);
        tactile_shell_band(radius - tactile_indicator_raise - tactile_recess_extra_depth,
                           radius + TACTILE_RECESS_OVERCUT);
    }
}

// Anything that is not Unicode braille renders NOTHING for that cell -
// get_dot_pattern() returns an all-zero pattern - so without this warning the
// plate comes out silently blank exactly where the text should be.
//
// Both plates show it, for the same reason tactile_gap_warning() does: the pair
// is generated from one set of settings, and a MakerWorld user may render either
// plate alone. In double-sided mode it also has to be on both, because the BACK
// text is what the COUNTER plate raises - a bad Back_Line blanks that plate, not
// this one. Back lines are checked with the same is_braille_char /
// has_invalid_chars machinery as the front, and only while the gate is On.
module invalid_characters_warning() {
    invalid_front = len([for (l = _all_lines) if (has_invalid_chars(l)) 1]) > 0;
    invalid_back  = ds_on && (len([for (l = _all_back_lines) if (has_invalid_chars(l)) 1]) > 0);

    if (invalid_front || invalid_back) {
        translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET])
        color("red")
        linear_extrude(height = INVALID_TEXT_DEPTH)
        text("INVALID CHARACTERS", size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
    }
}

// Seam gap too tight for the indicator: warn in 3D, because the MakerWorld
// customizer preview cannot show console output. Stacked one step above the
// TEXT TOO LONG warning, reusing the same placement constants.
module tactile_gap_warning() {
    if (tactile_gap_too_small) {
        translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET + 2 * INVALID_TEXT_STACK_GAP])
        color("red")
        linear_extrude(height = INVALID_TEXT_DEPTH)
        text(str("TACTILE GAP TOO SMALL: ", round(seam_gap_mm * 10) / 10, "mm"),
             size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
    }
}

// Wall between the arrow recess floor and the polygonal cutout too thin to
// print: warn in 3D, same reasons and same pattern as tactile_gap_warning
// above. The counter plate is the one that cuts the recess, but both plates
// call this - the pair is printed from one set of settings.
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
module tactile_seam_wall_warning() {
    if (tactile_seam_wall_too_thin) {
        translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET + 6 * INVALID_TEXT_STACK_GAP])
        color("red")
        linear_extrude(height = INVALID_TEXT_DEPTH)
        text(str("TACTILE WALL TOO THIN: ", round(tactile_seam_wall_mm * 1000) / 1000, " mm"),
             size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
    }
}

// The two double-sided warnings, in 3D for the same reason as the ones above:
// the MakerWorld customizer preview cannot show console output. Stacked one and
// two steps above TOO MANY LINES, reusing the same placement constants.
//
// Wording SIGNED OFF by Brennen 2026-08-20 - reword only with his sign-off.
module ds_mode_warnings() {
    if (ds_forced_tactile) {
        translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET + 4 * INVALID_TEXT_STACK_GAP])
        color("red")
        linear_extrude(height = INVALID_TEXT_DEPTH)
        text("DOUBLE-SIDED REQUIRES TACTILE",
             size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
    }

    if (ds_dots_too_close) {
        translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET + 5 * INVALID_TEXT_STACK_GAP])
        color("red")
        linear_extrude(height = INVALID_TEXT_DEPTH)
        text(str("DOTS TOO CLOSE: ", round(ds_same_surface_gap * 1000) / 1000, " mm"),
             size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
    }
}

// One tactile indicator per braille row, at the same row pitch the Visual
// marker columns use.
module tactile_rows_raised() {
    for (row = [0 : active_grid_rows - 1]) {
        y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;
        tactile_raised(y_pos);
    }
}

module tactile_rows_recessed() {
    for (row = [0 : active_grid_rows - 1]) {
        y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;
        tactile_recess_cut(y_pos);
    }
}

// =============================================================================
// DOT CREATION MODULES
// =============================================================================

// Create an embossing braille dot CENTERED at origin for CYLINDER surface
// Geometry spans from -totalHeight/2 to +totalHeight/2 along Z axis
module braille_dot_centered() {
    _total_height = use_rounded_dots ? 
                    (_preset_rounded_dot_base_height + _preset_rounded_dot_dome_height) : 
                    _preset_emboss_dot_height;
    
    if (use_rounded_dots) {
        // Spherical cap formula: R = (r² + h²) / (2h)
        _dome_r = _preset_rounded_dot_dome_diameter / 2;
        _R_sphere = (_dome_r * _dome_r + _preset_rounded_dot_dome_height * _preset_rounded_dot_dome_height) / (2 * _preset_rounded_dot_dome_height);
        _center_z = _preset_rounded_dot_base_height + _preset_rounded_dot_dome_height - _R_sphere;
        
        // Skirt: the frustum continues DOT_BASE_EMBED below the shell surface on
        // its own taper, so its radius AT the surface is still the full base
        // diameter and the dot's standing height is unchanged.
        _base_r  = _preset_rounded_dot_base_diameter / 2;
        _top_r   = _preset_rounded_dot_dome_diameter / 2;
        _skirt_r = _preset_rounded_dot_base_height > 0
                   ? _base_r + (_base_r - _top_r) * DOT_BASE_EMBED / _preset_rounded_dot_base_height
                   : _base_r;
        _frustum_h = _preset_rounded_dot_base_height + DOT_BASE_EMBED;

        // Center the combined geometry at Z=0
        translate([0, 0, -_total_height / 2]) {
            union() {
                // Frustum base
                translate([0, 0, _frustum_h / 2 - DOT_BASE_EMBED])
                cylinder(
                    h = _frustum_h,
                    r1 = _skirt_r,
                    r2 = _top_r,
                    center = true,
                    $fn = cone_segments
                );
                // Dome: proper spherical cap
                intersection() {
                    translate([0, 0, _center_z])
                    sphere(r = _R_sphere, $fn = quality_fn);
                    translate([0, 0, _preset_rounded_dot_base_height + _R_sphere])
                    cube([_R_sphere * 4, _R_sphere * 4, _R_sphere * 2], center = true);
                }
            }
        }
    } else {
        // Cone frustum, centered on the ORIGINAL height so the caller's radial
        // placement still puts the flat hat at radius + height; the skirt hangs
        // below on the same taper.
        _cone_base_r  = _preset_emboss_dot_base_diameter / 2;
        _cone_top_r   = _preset_emboss_dot_flat_hat / 2;
        _cone_skirt_r = _cone_base_r
                        + (_cone_base_r - _cone_top_r) * DOT_BASE_EMBED / _preset_emboss_dot_height;

        translate([0, 0, -DOT_BASE_EMBED / 2])
        cylinder(
            h = _preset_emboss_dot_height + DOT_BASE_EMBED,
            r1 = _cone_skirt_r,
            r2 = _cone_top_r,
            center = true,
            $fn = cone_segments
        );
    }
}

// Double-sided raised dot, CENTERED at origin like braille_dot_centered().
// Same frustum-plus-spherical-cap construction; only the sizes differ, and they
// come from the fixed Option B constants rather than any slider or preset.
module ds_braille_dot_centered() {
    _center_z = DS_DOT_BASE_H + DS_DOT_DOME_H - DS_DOT_DOME_R;

    // Same DOT_BASE_EMBED skirt as the single-sided dot; DS_DOT_BASE_H is fixed
    // by the package so it is never zero.
    _ds_skirt_r = DS_DOT_BASE_DIA / 2
                  + (DS_DOT_BASE_DIA / 2 - DS_DOT_DOME_DIA / 2) * DOT_BASE_EMBED / DS_DOT_BASE_H;
    _ds_frustum_h = DS_DOT_BASE_H + DOT_BASE_EMBED;

    translate([0, 0, -DS_DOT_HEIGHT / 2]) {
        union() {
            translate([0, 0, _ds_frustum_h / 2 - DOT_BASE_EMBED])
            cylinder(
                h = _ds_frustum_h,
                r1 = _ds_skirt_r,
                r2 = DS_DOT_DOME_DIA / 2,
                center = true,
                $fn = cone_segments
            );
            intersection() {
                translate([0, 0, _center_z])
                sphere(r = DS_DOT_DOME_R, $fn = quality_fn);
                translate([0, 0, DS_DOT_BASE_H + DS_DOT_DOME_R])
                cube([DS_DOT_DOME_R * 4, DS_DOT_DOME_R * 4, DS_DOT_DOME_R * 2], center = true);
            }
        }
    }
}

// Which raised dot this plate draws. Double-sided overrides the shape selection
// entirely; single-sided is untouched.
module braille_dot_for_plate() {
    if (ds_on) {
        ds_braille_dot_centered();
    } else {
        braille_dot_centered();
    }
}

// Double-sided paired recess: the bowl that receives the opposing cylinder's
// raised dot. Called with its origin ON the shell surface, and the sphere sits
// at that origin - so the cut is a hemisphere DS_BOWL_R deep and 2 * DS_BOWL_R
// across, NOT DS_BOWL_DEPTH deep. See the constants block for why, and do not
// "fix" this to the nominal-depth convention: it deliberately matches the web
// app's browser worker, which is the geometry that has been printed and
// embossed. Always a spherical cap - the cone family has no ds variant.
module ds_counter_recess() {
    sphere(r = DS_BOWL_R, $fn = quality_fn);
}

// Create a recess for counter plate (bowl or cone shape)
module counter_recess() {
    if (use_rounded_dots) {
        // Bowl recess (spherical cap)
        translate([0, 0, bowl_center_offset])
        sphere(r = bowl_recess_radius, $fn = quality_fn);
    } else {
        // Cone frustum recess
        translate([0, 0, -_preset_cone_counter_dot_height / 2])
        cylinder(
            h = _preset_cone_counter_dot_height,
            r1 = _preset_cone_counter_dot_flat_hat / 2,
            r2 = _preset_cone_counter_dot_base_diameter / 2,
            center = true,
            $fn = cone_segments
        );
    }
}

// =============================================================================
// CYLINDER MODULES
// =============================================================================

module cylinder_shell(cutout_rotate_deg = 0) {
    difference() {
        // Outer cylinder (see $fn TESSELLATION POLICY: case 1)
        cylinder(h = active_cylinder_height_mm, r = active_cylinder_diameter_mm / 2, center = true, $fn = CYLINDER_SHELL_FN);
        
        // Polygonal cutout if specified
        if (active_polygon_cutout_radius_mm > 0) {
            // Web UI: "Circumscribed Radius" but implementation uses inscribed radius
            cutout_circumradius = active_polygon_cutout_radius_mm / cos(180 / active_polygon_cutout_points);
            rotate([0, 0, cutout_rotate_deg])
                cylinder(h = active_cylinder_height_mm + 2, r = cutout_circumradius, $fn = active_polygon_cutout_points, center = true);
        }
    }
}

// Fixed-point decimal for the DS_PAIR self-check echoes below: the value
// rounded to 1e-6 (micro-units) and printed with all six decimals. str()
// alone formats a number to 6 SIGNIFICANT digits, which cannot show 1e-6
// agreement on a three-digit angle. Two plates that place a partner pair
// correctly therefore echo the identical string, apart from the sign.
function ds_pad3(n) = n < 10 ? str("00", n) : n < 100 ? str("0", n) : str(n);
function ds_fmt_e6(v) =
    let (t = round(abs(v) * 1e6),
         whole = floor(t / 1e6),
         frac = t - whole * 1e6,
         hi = floor(frac / 1000))
    str(v < 0 ? "-" : "", whole, ".", ds_pad3(hi), ds_pad3(frac - hi * 1000));

// Double-sided back-grid placements, shared by BOTH plates so the two walks
// cannot drift: the emboss plate (Cylinder A) cuts a bowl at each position
// (angle_sign +1), and the counter plate (Cylinder B) raises the matching
// back-text dot at the same planar position run through its angle-negation
// mirror (angle_sign -1). A back dot and its recess are therefore partners at
// exact angle negation, same height, by construction.
//
// Where a back dot lands, in two steps, both taken in the planar (pre-seam)
// frame the emboss plate places its own dots in:
//
//   1. MIRROR about the seam plane. Back-side text reads normally from behind
//      the card; seen from the front - the frame both cylinders are laid out in
//      - it reads reversed. The grid is centred on angle 0, so that plane passes
//      through the grid centre and the mirror is just a negated angle.
//   2. ONE DIAGONAL INTERPOINT STEP, in the DS_BACK_DIRECTION sense: around the
//      cylinder by interpoint_offset_x_mm (as an angle, arc / radius) and up the
//      cylinder by interpoint_offset_y_mm. This is what stops a back dot landing
//      on a front one and flattening it.
//
// Ported from the web generator's back_grid_transform() in
// app/geometry/interpoint.py, which stays the authoritative implementation.
//
// radial_offset lifts the child's origin off the shell surface: 0 for the
// bowl, whose sphere is centred ON the surface, and half the dot height for
// the raised dot, whose solid is centred at its own origin.
module ds_back_placements(angle_sign, radial_offset, pair_label) {
    for (row = [0 : min(active_grid_rows - 1, len(_all_back_lines) - 1)]) {
        if (len(_all_back_lines[row]) > 0) {
            y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;

            row_last_col = (text_limit_check == "Off")
                ? len(_all_back_lines[row]) - 1
                : min(active_grid_columns - 1, len(_all_back_lines[row]) - 1);
            for (col = [0 : row_last_col]) {
                // Double-sided forces tactile, so this always resolves to col;
                // it is written as the shared expression so the back walk cannot
                // drift from the front one.
                actual_col = tactile_on ? col :
                             indicator_on ? (col + 2) : (col + 1);
                angle_rad = start_angle + (actual_col * cell_spacing_angle);
                dots = get_dot_pattern(_all_back_lines[row][col]);

                for (i = [0:5]) {
                    if (dots[i] == 1) {
                        dot_pos = dot_positions[i];
                        front_angle_rad = angle_rad + dot_col_angle_offsets[dot_pos[1]];
                        front_dot_y     = y_pos + dot_row_offsets[dot_pos[0]];

                        back_angle_rad = -front_angle_rad
                                         + DS_BACK_DIRECTION * (interpoint_offset_x_mm / radius);
                        back_dot_y     = front_dot_y
                                         + DS_BACK_DIRECTION * interpoint_offset_y_mm;
                        back_angle_deg = angle_sign * (back_angle_rad * 180 / PI);

                        if (ds_self_check)
                            echo(str("DS_PAIR ", pair_label,
                                     " deg=", ds_fmt_e6(back_angle_deg),
                                     " y=", ds_fmt_e6(back_dot_y)));

                        x = (radius + radial_offset) * cos(back_angle_deg);
                        y = (radius + radial_offset) * sin(back_angle_deg);

                        translate([x, y, back_dot_y])
                            rotate([0, 90, back_angle_deg])
                                children();
                    }
                }
            }
        }
    }
}

// Double-sided, Cylinder A: one bowl per ACTUAL back-text dot, never a
// universal grid. Subtracted from the emboss plate, it is the seat the
// opposing cylinder's raised back dot drops into at the nip.
module ds_back_recesses() {
    ds_back_placements(1, 0, "A back_recess") ds_counter_recess();
}

// Double-sided, Cylinder B: the raised BACK-text dots this cylinder embosses.
// The same walk and interpoint transform as ds_back_recesses(), run through
// this plate's angle-negation mirror, so each raised dot lands exactly
// opposite the recess Cylinder A carries for it.
module ds_back_raised_dots() {
    ds_back_placements(-1, DS_DOT_HEIGHT / 2, "B back_dot") ds_braille_dot_centered();
}

// Double-sided, Cylinder B: one bowl per ACTUAL front-text dot - the seat
// Cylinder A's raised front dot drops into at the nip. Replaces the universal
// grid, which double-sided skips entirely: every recess is the 1:1 partner of
// a real dot. The walk is the emboss plate's front-dot walk; the only
// difference is this plate's angle-negation mirror (the same convention the
// universal grid used), so each bowl sits at exactly minus its partner dot's
// angle, same height.
module ds_front_recesses() {
    for (row = [0 : min(active_grid_rows - 1, len(_all_lines) - 1)]) {
        if (len(_all_lines[row]) > 0) {
            y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;

            row_last_col = (text_limit_check == "Off")
                ? len(_all_lines[row]) - 1
                : min(active_grid_columns - 1, len(_all_lines[row]) - 1);
            for (col = [0 : row_last_col]) {
                // Double-sided forces tactile, so this always resolves to col;
                // it is written as the shared expression so this walk cannot
                // drift from the emboss plate's front-dot walk.
                actual_col = tactile_on ? col :
                             indicator_on ? (col + 2) : (col + 1);
                angle_rad = start_angle + (actual_col * cell_spacing_angle);
                dots = get_dot_pattern(_all_lines[row][col]);

                for (i = [0:5]) {
                    if (dots[i] == 1) {
                        dot_pos = dot_positions[i];
                        front_angle_rad = angle_rad + dot_col_angle_offsets[dot_pos[1]];
                        front_dot_y     = y_pos + dot_row_offsets[dot_pos[0]];

                        bowl_angle_deg = -(front_angle_rad * 180 / PI);

                        if (ds_self_check)
                            echo(str("DS_PAIR B front_bowl",
                                     " deg=", ds_fmt_e6(bowl_angle_deg),
                                     " y=", ds_fmt_e6(front_dot_y)));

                        x = radius * cos(bowl_angle_deg);
                        y = radius * sin(bowl_angle_deg);

                        translate([x, y, front_dot_y])
                            rotate([0, 90, bowl_angle_deg])
                                ds_counter_recess();
                    }
                }
            }
        }
    }
}

module cylinder_emboss_plate() {
    translate([0, 0, active_cylinder_height_mm/2]) {
        // Angular grid + dot-positioning constants are derived at top level;
        // see `radius`, `start_angle`, `dot_positions`, etc. above.
        difference() {
            union() {
                // Base cylinder
                cylinder_shell(cutout_rotate_deg = -active_seam_offset_degrees);

                // INVALID CHARACTERS warning — covers the back lines too while
                // double-sided is on (see invalid_characters_warning above).
                invalid_characters_warning();

                // TEXT TOO LONG warning (see top-level max_line_len /
                // text_too_long; bypass with text_limit_check = "Off").
                // The counts render in the MakerWorld customizer preview,
                // which cannot show console output.
                if (text_too_long) {
                    translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET + INVALID_TEXT_STACK_GAP])
                    color("red")
                    linear_extrude(height = INVALID_TEXT_DEPTH)
                    text(str("TEXT TOO LONG: ", max_line_len, "/", active_grid_columns), size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
                }

                // TACTILE GAP TOO SMALL warning (Tactile mode only; no-op otherwise).
                tactile_gap_warning();

                // DOUBLE-SIDED REQUIRES TACTILE / DOTS TOO CLOSE warnings
                // (double-sided mode only; no-op otherwise).
                ds_mode_warnings();

                // TACTILE WALL TOO THIN warning (tactile mode with a polygonal
                // cutout only; no-op otherwise).
                tactile_seam_wall_warning();

                // TOO MANY LINES warning (see top-level rows_used /
                // too_many_rows). The dot loop below stops at active_grid_rows,
                // so without this the text on the extra lines would simply not
                // appear, with nothing on screen to say why.
                if (too_many_rows) {
                    translate([0, 0, active_cylinder_height_mm/2 + INVALID_TEXT_Z_OFFSET + 3 * INVALID_TEXT_STACK_GAP])
                    color("red")
                    linear_extrude(height = INVALID_TEXT_DEPTH)
                    text(str("TOO MANY LINES: ", rows_used, "/", active_grid_rows), size = INVALID_TEXT_SIZE, halign = "center", valign = "center");
                }

                // Tactile mode: raised alignment arrows in the seam gap, one per row.
                if (tactile_on) {
                    tactile_rows_raised();
                }

                // Create braille dots on cylinder surface. Rows past
                // active_grid_rows are dropped; too_many_rows above warns first.
                for (row = [0 : min(active_grid_rows - 1, len(_all_lines) - 1)]) {
                    if (len(_all_lines[row]) > 0) {
                        y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;
                        
                        // Clip each row to the cell capacity unless the user
                        // bypassed the limit (then render every pasted cell).
                        row_last_col = (text_limit_check == "Off")
                            ? len(_all_lines[row]) - 1
                            : min(active_grid_columns - 1, len(_all_lines[row]) - 1);
                        for (col = [0 : row_last_col]) {
                            // Visual mode: shift past the marker columns — triangle
                            // (always) at col 0, plus the indicator letter square at
                            // col 1 when On. Tactile mode has no marker columns.
                            actual_col = tactile_on ? col :
                                         indicator_on ? (col + 2) : (col + 1);
                            angle_rad = start_angle + (actual_col * cell_spacing_angle);
                            angle_deg = angle_rad * 180 / PI;
                            dots = get_dot_pattern(_all_lines[row][col]);
                            
                            for (i = [0:5]) {
                                if (dots[i] == 1) {
                                    dot_pos = dot_positions[i];
                                    dot_angle_rad = angle_rad + dot_col_angle_offsets[dot_pos[1]];
                                    dot_angle_deg = dot_angle_rad * 180 / PI;
                                    dot_y = y_pos + dot_row_offsets[dot_pos[0]];

                                    // Pairing self-check: Cylinder B's
                                    // ds_front_recesses() echoes its bowls the
                                    // same way, so the partner rows must match
                                    // apart from the sign of the angle.
                                    if (ds_on && ds_self_check)
                                        echo(str("DS_PAIR A front_dot",
                                                 " deg=", ds_fmt_e6(dot_angle_deg),
                                                 " y=", ds_fmt_e6(dot_y)));

                                    x = (radius + active_emboss_height/2) * cos(dot_angle_deg);
                                    y = (radius + active_emboss_height/2) * sin(dot_angle_deg);
                                    
                                    translate([x, y, dot_y])
                                        rotate([0, 90, dot_angle_deg])
                                            braille_dot_for_plate();
                                }
                            }
                        }
                    }
                }
            }

            // Subtract indicator recesses (Visual mode only — Tactile replaces the
            // marker columns with the raised arrows added above). The triangle
            // alignment marker is always recessed; place_row_indicators adds the
            // square only when Indicator Letters are On. Emboss renders the shared
            // row layout directly; the counter plate renders the same module under
            // mirror([0,1,0]) for a true mirrored pair (see cylinder_counter_plate).
            if (!tactile_on) {
                for (row = [0 : active_grid_rows - 1]) {
                    y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;
                    place_row_indicators(y_pos, INDICATOR_TRIANGLE_DEPTH_EMBOSS, INDICATOR_RECT_DEPTH_EMBOSS);
                }
            }

            // Double-sided: the seats for the opposing cylinder's back dots.
            // Subtracted last, after the raised dots are unioned in, so a bowl
            // that reaches a neighbouring dot cuts it rather than being buried
            // by it - the same shell -> union raised -> subtract recesses order
            // the web app's manifold worker uses.
            if (ds_on) {
                ds_back_recesses();
            }
        }
    }
}

module cylinder_counter_plate() {
    translate([0, 0, active_cylinder_height_mm/2]) {
        difference() {
            union() {
                // Base cylinder
                cylinder_shell(cutout_rotate_deg = active_seam_offset_degrees);

                // Double-sided: this cylinder's own raised dots - the BACK
                // text it embosses. Unioned in before any recess is subtracted
                // (shell -> union raised -> subtract recesses, the web
                // manifold worker's order) so a bowl that reaches a
                // neighbouring dot cuts it rather than being buried by it.
                if (ds_on) {
                    ds_back_raised_dots();
                }
            }

            // Angular grid + dot-positioning constants are derived at top level;
            // see `radius`, `start_angle`, `dot_positions`, etc. above.

            // Create indicator recesses (Visual mode only — Tactile uses the
            // seam-gap arrow recess below instead). The triangle alignment marker
            // is always recessed; place_row_indicators adds the square only when
            // Indicator Letters are On. The counter plate is an exact mirror of the
            // emboss plate: render the shared emboss-orientation row layout under
            // mirror([0,1,0]) so the triangle->rectangle center spacing is identical
            // on both plates and the triangles point the opposite way (a reflection).
            // Braille dots are radially symmetric and already mirror via angle
            // negation below, so they stay aligned with the mirrored indicators.
            if (!tactile_on) {
                for (row = [0 : active_grid_rows - 1]) {
                    y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;
                    mirror([0, 1, 0])   // counter = exact mirror image of emboss
                        place_row_indicators(y_pos, active_counter_height, active_counter_height);
                }
            }

            // Tactile mode: the arrow recess the emboss plate's raised arrow nests
            // into. It sits at 180°, the fixed point of this plate's mirror /
            // angle-negation construction, so it needs no mirroring of its own —
            // it lands on the emboss arrow either way.
            if (tactile_on) {
                tactile_rows_recessed();
            }

            // Create recesses for ALL possible dot positions - single-sided
            // only. Double-sided replaces this universal grid with the 1:1
            // paired recesses below: a universal field would collide with this
            // plate's own raised back dots, and the web generator skips it the
            // same way. When the text limit is bypassed, also cover any extra
            // columns the emboss plate renders so both plates stay in lockstep.
            if (!ds_on) {
                counter_last_col = (text_limit_check == "Off")
                    ? max(active_grid_columns, max_line_len) - 1
                    : active_grid_columns - 1;
                for (row = [0 : active_grid_rows - 1]) {
                    y_pos = active_cylinder_height_mm/2 - top_margin - (row * active_line_spacing) + active_braille_y_adjust;

                    for (col = [0 : counter_last_col]) {
                        // Visual mode: shift past the marker columns — triangle (always)
                        // at col 0, plus the indicator letter square at col 1 when On.
                        // Tactile mode has no marker columns.
                        actual_col = tactile_on ? col :
                                     indicator_on ? (col + 2) : (col + 1);
                        angle_rad = start_angle + (actual_col * cell_spacing_angle);
                        angle_deg = -(angle_rad * 180 / PI);

                        for (i = [0:5]) {
                            dot_pos = dot_positions[i];
                            dot_angle_rad = angle_rad + dot_col_angle_offsets[dot_pos[1]];
                            dot_angle_deg = -(dot_angle_rad * 180 / PI);
                            dot_y = y_pos + dot_row_offsets[dot_pos[0]];

                            recess_radius_offset = use_rounded_dots ? 0 : INDICATOR_OVERCUT;
                            x = (radius + recess_radius_offset) * cos(dot_angle_deg);
                            y = (radius + recess_radius_offset) * sin(dot_angle_deg);

                            translate([x, y, dot_y])
                            rotate([0, 90, dot_angle_deg])
                            counter_recess();
                        }
                    }
                }
            }

            // Double-sided: the seats for Cylinder A's front-text dots.
            // Subtracted last, after the raised back dots are unioned in, for
            // the same reason ds_back_recesses() is on the emboss plate.
            if (ds_on) {
                ds_front_recesses();
            }
        }

        // INVALID CHARACTERS warning. Shown on this plate too: in double-sided
        // mode the BACK text is what THIS cylinder raises, so untranslated back
        // text blanks this plate and nothing else would say why.
        invalid_characters_warning();

        // TACTILE GAP TOO SMALL warning (Tactile mode only; no-op otherwise). Sits
        // outside the difference() so the recess cuts can't eat it, and is shown on
        // this plate too — a MakerWorld user may generate the counter plate alone.
        tactile_gap_warning();

        // DOUBLE-SIDED REQUIRES TACTILE / DOTS TOO CLOSE, and TACTILE WALL TOO
        // THIN - shown on this plate for the same reason as tactile_gap_warning
        // above. All no-ops unless their condition holds.
        ds_mode_warnings();
        tactile_seam_wall_warning();
    }
}

// =============================================================================
// MAIN RENDERING
// =============================================================================

if (is_emboss_plate) {
    cylinder_emboss_plate();
} else {
    cylinder_counter_plate();
}

// End of file
