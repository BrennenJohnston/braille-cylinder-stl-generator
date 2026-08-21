# OpenSCAD to Web App Parameter Mapping

This document maps the OpenSCAD customizer parameters to the web-based braille generator UI controls.

**Note:** this is a vendored copy — see [`VENDORED.json`](VENDORED.json). The canonical version lives in [braille-cylinder-stl-generator-openscad](https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad); edit it there. This mapping ensures the OpenSCAD Customizer stays aligned with web UI terminology and defaults.

## Overview

The OpenSCAD version has been updated to match the web-based generator's UI parameters. The only differences are:
1. OpenSCAD requires **pre-translated Unicode braille** characters (no automatic translation). The web app can now take pre-translated braille too — it has a Braille (Unicode) field that is used verbatim — so this is a one-way gap: translation is web-only, direct braille input works in both.
2. OpenSCAD is **cylinder-only** (card support removed)

## Translation Workflow

1. **Web App**: Automatic translation using Liblouis (Grade 1 or Grade 2), or
   paste pre-translated braille into its Braille (Unicode) field, which is used
   verbatim — the same workflow as below
2. **OpenSCAD**: Manual translation required at https://www.branah.com/braille-translator
   - User must select Grade 1 or Grade 2 manually
   - Copy Unicode braille output
   - Paste into OpenSCAD Line_1, Line_2, etc.

## Parameter Mapping

### Text Input - Pre-Translated Braille
| OpenSCAD Parameter | Web App Equivalent | Notes |
|--------------------|-------------------|-------|
| `Line_1` | Line 1 text input | Must be pre-translated Unicode braille |
| `Line_2` | Line 2 text input | Must be pre-translated Unicode braille |
| `Line_3` | Line 3 text input | Must be pre-translated Unicode braille |
| `Line_4` | Line 4 text input | Must be pre-translated Unicode braille |
| `Line_5` | Line 5 text input | Must be pre-translated Unicode braille |
| `Line_6` | Line 6 text input | Must be pre-translated Unicode braille |
| `Line_7` | Line 7 text input | Must be pre-translated Unicode braille |
| `Line_8` | Line 8 text input | Must be pre-translated Unicode braille |
| `text_limit_check` | *(OpenSCAD-only)* | `"On"` (default) shows the `TEXT TOO LONG` warning and clips rows to the cell capacity; `"Off"` renders every pasted cell (rows may crowd the seam). The web app validates cell counts before generation instead. |

### More Braille Lines (Advanced)

`grid_rows` goes up to 10, but the Customizer cannot add input fields on demand
the way the web app grows its line list. Showing all ten at once would push the
other tabs off screen for the common case, so the last two live in their own
collapsed tab. Parameter names are unchanged, so presets and `-D` overrides
that set `Line_9` / `Line_10` keep working regardless of which tab they display in.

| OpenSCAD Parameter | Web App Equivalent | Notes |
|--------------------|-------------------|-------|
| `Line_9` | Line 9 text input | Must be pre-translated Unicode braille; raise `grid_rows` to 9 or more to render it |
| `Line_10` | Line 10 text input | Must be pre-translated Unicode braille; raise `grid_rows` to 10 to render it |

Only the first `grid_rows` lines are rendered. Filling a line beyond that limit
triggers a `TOO MANY LINES: n/grid_rows` warning — a console `echo()` plus red
text above the cylinder for the MakerWorld preview, which has no console. The
web app blocks the same case before generation instead of warning after.

### Plate Selection
| OpenSCAD Parameter | Web App Equivalent | Values |
|--------------------|-------------------|--------|
| `plate_type` | Select Plate to Generate | `"Embossing Plate"`, `"Counter Plate"` |

### Indicator Mode

This mode originated here and the web app has since ported it, so every
parameter below now has a web equivalent under the same name. The web app's
runtime settings field names are identical; only the enum casing differs
(`"Visual"`/`"Tactile"` here, `visual`/`tactile` on the wire). In
`settings.schema.json` they live under `indicators.*`, and the web UI presents
them as **Row Indicator Style** plus a **Tactile Indicator Dimensions** group in
Expert Mode.

| OpenSCAD Parameter | `web_api_name` | Default | Range / Values | Notes |
|--------------------|----------------|---------|----------------|-------|
| `indicator_mode` | `indicator_mode` | `"Visual"` | `"Visual"`, `"Tactile"` | `Visual` = recessed marker cells at the start of each row (current behavior). `Tactile` = raised arrow on the emboss plate + matching recess on the counter plate, in the seam gap. See Note 3. |
| `tactile_indicator_width` | `tactile_indicator_width` | 4.0 mm | 2–10 mm | Indicator width around the cylinder |
| `tactile_indicator_length` | `tactile_indicator_length` | 10.0 mm | 2–15 mm | Indicator length along the cylinder axis; long enough for a fingertip to read the direction of the point in one pass. At the 10 mm default `line_spacing`, each row's arrow meets the base of the one above |
| `tactile_indicator_raise` | `tactile_indicator_raise` | 0.5 mm | 0–2 mm | How far the emboss arrow stands proud. Kept below the braille dot height so the dots carry the rolling pressure |
| `tactile_recess_clearance` | `tactile_recess_clearance` | 0.2 mm | 0–1 mm | Outline margin around the counter recess |
| `tactile_recess_extra_depth` | `tactile_recess_extra_depth` | 0.2 mm | 0–1 mm | Counter recess depth beyond the raise; 0 = exact same-depth nesting |

Defaults are asserted equal on the web side
(`tests/test_smoke.py::test_tactile_settings_defaults_match_openscad`), so the
two generators produce the same arrow. Change a default here and that test fails
there — deliberately.

The five tactile sliders are **not** preset-driven — same policy as
`grid_columns`. The paper-thickness presets describe paper and dot geometry;
the indicator is a mechanical alignment feature and must not move when the
user switches preset.

### Paper Thickness Preset
| OpenSCAD Parameter | Web App Equivalent | Default | Values |
|--------------------|-------------------|---------|--------|
| `paper_thickness_preset` | Card Thickness | `"0.4mm"` | `"0.4mm"`, `"0.3mm"`, `"Custom"` |

**Note:** The web UI label is "Card Thickness" but this is NOT the removed card-geometry feature. This is a parametric memory system that automatically sets 21 parameters (spacing, dot dimensions, and cylinder settings) to known-good values optimized for different paper thicknesses. Selecting "0.4mm" or "0.3mm" forces all preset-controlled parameters to specific values. "Custom" indicates that values deviate from presets. `grid_columns` and `grid_rows` are deliberately not preset-driven: the sliders always govern text capacity, matching the web app, where presets never override the columns/rows dials.

### Expert Mode - Shape Selection
| OpenSCAD Parameter | Web App Equivalent | Values |
|--------------------|-------------------|--------|
| `dot_shape` | Braille Dot Shape | `"Rounded"` (default), `"Cone"` |
| `indicators` | Indicator Letters (Emboss and Counter) | `"On"` (default), `"Off"` — gates only the square marker; the triangle alignment indicator is always generated. **Visual indicator mode only** — ignored when `indicator_mode = "Tactile"` |

### Expert Mode - Cylinder Dimensions
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `cylinder_diameter_mm` | Diameter | 30.8 mm | 10-100 mm |
| `cylinder_height_mm` | Height | 52 mm | 20-150 mm |
| `polygon_cutout_radius_mm` | Cutout Radius | 13.0 mm | 0-50 mm |
| `polygon_cutout_points` | Cutout Points/Sides | 12 | 3-24 |
| `seam_offset_degrees` | Seam Offset | 0.0° | 0-360° |

### Expert Mode - Braille Spacing
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `grid_columns` | Number of Braille Cells | 13 | 1-20 |
| `grid_rows` | Number of Braille Lines | 4 | 1-10 (every row has a `Line_N` field; 9 and 10 are under the Advanced tab) |
| `cell_spacing` | Braille Cell Spacing | 6.5 mm | 2-15 mm |
| `line_spacing` | Braille Line Spacing | 10.0 mm | 5-25 mm |
| `dot_spacing` | Braille Dot Spacing | 2.5 mm | 1-5 mm |

### Expert Mode - Braille Positioning
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `braille_y_adjust` | Y Adjust | 0.0 mm | -10 to 10 mm |

> Removed in v2.2.0: `braille_x_adjust`. On a cylinder the X axis is the angular
> wrap around the seam, so a linear "X adjust" had no useful meaning. Use
> `seam_offset_degrees` (Cylinder Dimensions) for angular pattern offset.

### Expert Mode - Emboss Dot Dimensions (Rounded Shape)
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `rounded_dot_base_diameter` | Rounded dot base diameter (cone base) | 1.5 mm | 0.5-3 mm |
| `rounded_dot_base_height` | Rounded dot base height (cone height) | 0.5 mm | 0-2 mm |
| `rounded_dot_dome_diameter` | Rounded dome diameter | 1.0 mm | 0.5-3 mm |
| `rounded_dot_dome_height` | Rounded dot dome height | 0.5 mm | 0.1-2 mm |

### Expert Mode - Emboss Dot Dimensions (Cone Shape)
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `emboss_dot_base_diameter` | Dot diameter | 1.5 mm | 0.5-3 mm |
| `emboss_dot_height` | Dot height | 0.8 mm | 0.3-2 mm |
| `emboss_dot_flat_hat` | Flat hat diameter | 0.4 mm | 0.1-2 mm |

### Expert Mode - Counter Dot Dimensions (Rounded Shape / Bowl)
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `bowl_counter_dot_base_diameter` | Bowl Recess Dot Base Diameter | 1.8 mm | 0.5-5 mm |
| `counter_dot_depth` | Bowl Recess Depth | 0.8 mm | 0.1-2 mm |

### Expert Mode - Counter Dot Dimensions (Cone Shape)
| OpenSCAD Parameter | Web App Equivalent | Default | Range |
|--------------------|-------------------|---------|-------|
| `cone_counter_dot_base_diameter` | Cone recess base diameter | 1.9 mm | 0.5-3 mm |
| `cone_counter_dot_height` | Cone recess height | 0.7 mm | 0.3-2 mm |
| `cone_counter_dot_flat_hat` | Cone recess flat hat diameter | 1.0 mm | 0.1-2 mm |

### Rendering Quality
| OpenSCAD Parameter | Web App Equivalent | Default | Values |
|--------------------|-------------------|---------|--------|
| `render_quality` | Render Quality | `"Medium"` | `"Low"` (24 segments), `"Medium"` (32 segments), `"High"` (64 segments) |
| `cone_segments` | Cone Segments | 16 | 8-64 |

## Key Features Implemented

### 1. **Unified Shape Selection**
- `dot_shape` parameter (Customizer dropdown) controls both emboss and
  counter plate dot shapes
- When set to `"Rounded"`: Uses rounded dome dots for emboss, bowl
  recesses for counter
- When set to `"Cone"`: Uses cone frustum dots for emboss, cone recesses
  for counter

> **Backward compatibility:** the test harness and older configs may
> still set `combined_shape` (lowercase: `"rounded"` / `"cone"`). It
> lives in the `[Hidden]` block of the SCAD file and is normalized into
> `dot_shape` at load time. New code should always use `dot_shape`.

### 2. **Indicator Letters — Visual mode (cylinder-only)**
- The **triangle alignment indicator at column 0 is always generated** —
  it is critical to the mechanical device the cylinder mounts into and
  has no user-facing toggle.
- `indicator_on` (Customizer toggle "Indicator Letters", On/Off) gates
  only the square/rectangle marker next to the triangle.
- Text capacity always stays at `grid_columns`; the grid is widened at
  the leading edge of the cylinder by the marker cells:
  - When **On** (default), 2 marker cells are added (text shifted right
    by two cells):
    - **Column 0:** Triangle (orientation marker, always present)
    - **Column 1:** Rectangle (alignment / "this side up" marker)
  - When **Off**, 1 marker cell is added (text shifted right by one
    cell): only the triangle at column 0. This frees 1 cell of physical
    space per row for braille text on the same cylinder.
  - On the **counter plate**, the triangle is rotated 180° to mate with
    the emboss plate; the rectangle is rendered identically.

> Card indicators (rectangle at column 0, triangle at column N-1) were
> removed when card support was retired in v2.0. Only the cylinder
> layout above ships now.

### 3. **Tactile indicator mode (cylinder-only)**
Setting `indicator_mode = "Tactile"` swaps the marker columns for a
blind-accessible indicator carried by both plates. Cylinder diameter, height,
and the polygonal cutout are unchanged — only surface features differ.

- **Placement.** One indicator per braille row, centred in the seam gap
  between the last and first cell. The grid is centred on angle 0, so that
  midpoint is always exactly **180°** — and 180° is the fixed point of the
  counter plate's `mirror([0,1,0])` / angle-negation construction, so the
  emboss arrow and the counter recess self-align radially with no extra maths,
  at any rotation of the paired cylinders.
- **Shape.** An isosceles triangle, **symmetric circumferentially** (so the
  mirrored recess has an identical outline and the two nest rather than
  collide) and **asymmetric axially, apex toward the cylinder top** (so a
  blind user feels which end is up on either plate). Raised-vs-recessed
  distinguishes the embosser from the counter by touch.
- **Crush safety.** The default 0.8 mm raise is below the 1.0 mm braille dot
  height, so the dots always carry the rolling pressure. At defaults the arrow
  tip sits at radius 16.2 mm and the recess floor at 14.4 mm — 0.2 mm of radial
  slack, 0.2 mm of outline clearance, and ~0.93 mm of wall left over the
  polygonal cutout.
- **Uniform raise/depth.** Both features are a radial prism intersected with a
  shell band tessellated at `CYLINDER_SHELL_FN`, so the raise and depth stay
  constant across the arrow. A flat prism 4 mm wide on a 15.4 mm radius would
  lose ~0.13 mm at its edges to the chord sagitta — large next to the 0.2 mm
  nesting margin.
- **Capacity.** No marker cells, so `actual_grid_columns == grid_columns` and
  up to 14 text cells fit the default cylinder. `indicators` is ignored.
- **Seam-gap guard.** When the gap drops below
  `tactile_indicator_width + 5 mm`, both plates render a red
  `TACTILE GAP TOO SMALL: <gap>mm` extrusion above the cylinder and the desktop
  console echoes the measured gap plus the fix.

### 4. **Flexible Counter Plate Recesses**
- **Bowl Recess (Rounded)**: Spherical cap with adjustable diameter and depth
- **Cone Recess (Cone)**: Frustum cone matching emboss dot shape
- Universal counter plates work for all possible dot positions

### 5. **Multiple Dot Shapes**
- **Rounded**: Cone base + hemispherical dome (more comfortable to touch)
- **Cone**: Frustum cone (traditional, easier to print)

### 6. **Cylinder Support**
- Full parametric control over diameter, height, and polygonal cutout
- Seam offset allows rotation adjustment
- Supports both rounded and cone dot shapes on curved surfaces

## Default Values Alignment

All default values match the web-based generator's defaults (0.4mm paper preset applied on load):
- Cylinder: 30.8mm diameter × 52mm height
- Grid: 13 text cells × 4 rows (in Visual indicator mode with Indicator Letters ON, 2 additional cells are reserved = 15 total; with Indicator Letters OFF only the triangle cell is reserved; Tactile indicator mode reserves none — either narrower layout fits up to 14 text cells on the default cylinder)
- Spacing matches BANA specifications
- Default shape: Rounded (the dropdown still offers Cone)
- Default indicator mode: Visual (the dropdown still offers Tactile)
- Default preset: 0.4mm (optimized for thicker paper, larger dots)

## Workflow Comparison

### Web App Workflow:
1. Enter English text
2. Select language/grade
3. Choose shape and plate type
4. Adjust expert parameters (optional)
5. Generate STL
6. Download

### OpenSCAD Workflow:
1. Translate text at https://www.branah.com/braille-translator
2. Copy Unicode braille output
3. Open OpenSCAD file
4. Paste braille into Line_1, Line_2, etc.
5. Choose `dot_shape` and `plate_type` in Customizer
6. Adjust expert parameters (optional)
7. Render (F6)
8. Export STL (File → Export → Export as STL)

## Advantages of Each Version

### Web App Advantages:
- ✅ Automatic braille translation (Liblouis)
- ✅ Live 3D preview in browser
- ✅ No software installation required
- ✅ Auto-placement mode (word wrapping)
- ✅ Multi-language support (100+ braille tables)

### OpenSCAD Advantages:
- ✅ Works offline (after text translation)
- ✅ Full parametric control in native CAD environment
- ✅ Can modify and extend code
- ✅ Integration with existing OpenSCAD workflows
- ✅ Version control friendly (plain text .scad files)
- ✅ Batch processing possible via command line

## Notes

1. **Paper Thickness Preset System**: This is a convenience system that sets 21 parameters to known-good values:
   - **0.4mm preset** (thicker paper, larger dots): Default setting that matches web app on-load behavior
   - **0.3mm preset** (thinner paper, smaller dots): Alternative optimized for thinner materials
   - **Custom**: Indicator state when values deviate from presets
   - The preset controls: spacing (4 params: cell/line/dot spacing + Y adjust), emboss rounded (4 params), emboss cone (3 params), counter bowl (2 params), counter cone (3 params), and cylinder dimensions (5 params)
   - Text, plate type, shape selection, rendering quality, and grid layout (`grid_columns`/`grid_rows`) remain user-controlled

2. **Indicator Letters**: Visual indicator mode only. The triangle alignment
   indicator at column 0 is **always generated** (no user-facing toggle). When
   Indicator Letters is enabled (`indicator_on = true` in the Customizer;
   `indicator_shapes = "on"` is the legacy backward-compat alias), the cylinder
   reserves the **first two cells** (col 0 = triangle, col 1 = rectangle) at
   the leading edge for alignment markers; when disabled, only the triangle
   cell is reserved. The `grid_columns` parameter represents the number of
   cells *available for text*, not including markers — the code internally adds
   2 cells when Indicator Letters is On and 1 cell when Off.

3. **Indicator Mode**: `indicator_mode = "Tactile"` reserves **no** marker
   cells (`actual_grid_columns == grid_columns`), places the alignment
   indicator in the seam gap at 180° instead, and ignores `indicators`
   entirely. `Visual` is the default and reproduces the layout in Note 2
   exactly. Both plates of a pair must use the same mode.

4. **Rounded vs. Cone**: The web app calls these "Rounded" and "Cone" - both terms refer to the combined emboss+counter shape pair.

5. **Counter Plate Universality**: Counter plates have recesses at ALL possible dot positions (all 6 dots × all cells × all rows), making them universal for any braille pattern.

6. **Parameter Names**: OpenSCAD uses snake_case (e.g., `grid_columns`) to match the web app's JavaScript variable names, ensuring consistency across platforms.

7. **"Card Thickness" UI Label**: Despite the web UI label "Card Thickness", this preset system is NOT the removed card-geometry feature. It's a parametric memory system for setting multiple dials at once.

## References

- Web-based Generator: https://braille-cylinder-stl-generator.vercel.app
- Web App Source: https://github.com/BrennenJohnston/braille-cylinder-stl-generator
- OpenSCAD Version: https://github.com/BrennenJohnston/braille-cylinder-stl-generator-openscad
- Branah Braille Translator: https://www.branah.com/braille-translator
- BANA Size & Spacing: https://brailleauthority.org/size-and-spacing-braille-characters

