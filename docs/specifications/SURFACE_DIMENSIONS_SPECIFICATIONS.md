# Surface Dimensions Specifications

## Document Purpose

This document specifies all Surface Dimensions controls available in the application UI. It serves as an authoritative reference for future development by documenting:

1. **UI Controls** — The input fields and their intended behaviors
2. **Parameter Processing** — How values flow from UI through backend systems
3. **Geometric Effects** — Exact dimensional impacts on generated STL geometry
4. **Cross-Platform Consistency** — Behavior across backend and client-side CSG implementations

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source
2. `wsgi.py` / `app/models.py` — Configuration, startup, and defaults
3. `static/workers/csg-worker.js` — Client-side CSG (three-bvh-csg)
4. Manifold WASM — Mesh repair and validation fallback

---

## Table of Contents

1. [UI Layout: Surface Dimensions Submenu](#1-ui-layout-surface-dimensions-submenu)
2. [Cylinder Dimensions](#2-cylinder-dimensions)
   - 2.1 [Cylinder Diameter](#21-cylinder-diameter)
   - 2.2 [Cylinder Height](#22-cylinder-height)
   - 2.3 [Polygonal Cutout Circumscribed Radius](#23-polygonal-cutout-circumscribed-radius)
   - 2.4 [Polygonal Cutout Points](#24-polygonal-cutout-points)
   - 2.5 [Seam Offset](#25-seam-offset)
   - 2.6 [Slicer Seam Channel](#26-slicer-seam-channel)
3. [Plate Dimensions](#3-plate-dimensions)
   - 3.1 [Plate Width](#31-plate-width)
   - 3.2 [Plate Height](#32-plate-height)
   - 3.3 [Plate Thickness](#33-plate-thickness)
4. [Parameter Flow: UI to Backend](#4-parameter-flow-ui-to-backend)
5. [Geometry Construction Details](#5-geometry-construction-details)
6. [CSG Worker Implementation](#6-csg-worker-implementation)
7. [Default Values Reference](#7-default-values-reference)
8. [Validation and Constraints](#8-validation-and-constraints)
9. [Interrelationships with Other Settings](#9-interrelationships-with-other-settings)
10. [Known Issues and Edge Cases](#10-known-issues-and-edge-cases)

---

## 1. UI Layout: Surface Dimensions Submenu

### Location in Application

The Surface Dimensions controls are located under:

```
Expert Mode → Surface Dimensions (submenu)
```

This submenu is **collapsed by default** and must be expanded by clicking the toggle button.

### Submenu Structure

The submenu contains **two grouped sections**:

```
┌──────────────────────────────────────────────────────────────────┐
│  ▼ Surface Dimensions                                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─ Cylinder Dimensions ─────────────────────────────────────────┐│
│  │  • Cylinder Diameter (mm)                    [30.75]         ││
│  │  • Cylinder Height (mm)                      [54]            ││
│  │  • Polygonal Cutout Circumscribed Radius (mm) [13]           ││
│  │      Creates a polygonal cutout along the cylinder's length. ││
│  │      Set to 0 for no cutout.                                 ││
│  │  • Polygonal Cutout Points                   [12]            ││
│  │      Lower values create simpler shapes (e.g., 6);           ││
│  │      higher values approximate a circle.                     ││
│  │  • Seam Offset (degrees)                     [355]           ││
│  │      Rotates the starting position of braille text           ││
│  │      around the cylinder                                     ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─ Plate Dimensions ────────────────────────────────────────────┐│
│  │  • Plate Width                               [90]            ││
│  │  • Plate Height                              [52]            ││
│  │  • Plate Thickness                           [2.0]           ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### HTML Implementation

```html
<!-- Submenu: Surface Dimensions -->
<div class="expert-submenu">
    <!-- The heading wrapper is required: the WAI-ARIA APG Accordion pattern
         says each header button is the sole child of an element with role
         heading. See UI_INTERFACE_CORE_SPECIFICATIONS.md §4.11. -->
    <h3 class="expert-submenu-heading">
        <button type="button" class="expert-submenu-toggle" aria-expanded="false"
                aria-controls="expert-panel-dimensions">
            <span class="expert-submenu-title">Surface Dimensions</span>
            <span class="expert-submenu-icon" aria-hidden="true">▼</span>
        </button>
    </h3>
    <div id="expert-panel-dimensions" class="expert-submenu-content" style="display: none;">
        <!-- Cylinder Dimensions group -->
        <!-- Plate Dimensions group -->
    </div>
</div>
```

---

## 2. Cylinder Dimensions

Cylinder dimensions control the physical shape and structure of cylindrical braille output. These parameters are critical for generating braille cylinders that fit specific pen holders, rollers, or educational tools.

### 2.1 Cylinder Diameter

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Cylinder Diameter (mm):` |
| Input ID | `cylinder_diameter_mm` |
| Input Name | `cylinder_diameter_mm` |
| Type | `number` |
| Default | `30.75` |
| Step | `0.1` |
| Min | `10` |
| Max | `200` |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `cylinder_diameter_mm` | Primary input name |
| `app/models.py` | `diameter_mm` | In `CylinderParams` dataclass |
| `backend.py` | `diameter_mm`, `diameter` | Both accepted for compatibility |
| `geometry_spec.py` | `diameter`, `diameter_mm` | Fallback chain |
| `csg-worker.js` | `radius` | Derived as `diameter / 2` |

#### Backend Processing (app/models.py - CylinderParams)

```python
@dataclass
class CylinderParams:
    diameter_mm: float = 31.35

    @staticmethod
    def from_dict(data: dict) -> 'CylinderParams':
        return CylinderParams(
            diameter_mm=float(data.get('diameter_mm', data.get('diameter', 31.35))),
            # ... other parameters
        )
```

#### Geometric Effect

The cylinder diameter determines the **outer radius** of the cylindrical shell:

```
                    ┌─────────────────┐
                   /                   \
                  /     Cylinder        \
                 │        Shell          │
                 │                       │
          ────────┼─────────────────────┼────────
                 │◄─── Diameter (mm) ───►│
                 │                       │
                  \                     /
                   \                   /
                    └─────────────────┘
```

**Key Relationships:**
- `radius = diameter / 2`
- Affects angular spacing of braille cells: `cell_spacing_angle = cell_spacing / radius`
- Affects dot spacing angle: `dot_spacing_angle = dot_spacing / radius`
- Affects grid wrap angle: `grid_angle = grid_width / radius`

#### geometry_spec.py Implementation

```python
def extract_cylinder_geometry_spec(...):
    diameter = float(cylinder_params.get('diameter', cylinder_params.get('diameter_mm', 60.0)))
    radius = diameter / 2

    # Grid layout calculations depend on radius
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_angle = grid_width / radius
    start_angle = -grid_angle / 2
    cell_spacing_angle = settings.cell_spacing / radius
    dot_spacing_angle = settings.dot_spacing / radius
```

#### csg-worker.js Implementation

```javascript
function createCylinderShell(spec) {
    const { radius, height, thickness, polygon_points } = spec;
    const validRadius = (radius && radius > 0) ? radius : 30;

    // Create outer cylinder geometry
    const outerGeom = new THREE.CylinderGeometry(validRadius, validRadius, validHeight, 64);
    // ...
}
```

---

### 2.2 Cylinder Height

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Cylinder Height (mm):` |
| Input ID | `cylinder_height_mm` |
| Input Name | `cylinder_height_mm` |
| Type | `number` |
| Default | `52` |
| Step | `0.1` |
| Min | `10` |
| Max | `200` |

**Why 52 (2026-08-31):** 52 is the **Version 1 standard barrel** — the height
every previously shipped V1 gear model pairs with, and the size the
integrated-gears BETA is hard-gated to (S7). The default spent part of this
day at 54 (a 1 mm card shelf past each card edge), which broke gear mode on
untouched dials; Brennen's deployment verdict moved the shelf to **Embosser
Version 2 only** (its preset forces 30.8 × 54 — see
EMBOSSER_VERSION_2_KEYED_CUTOUTS_SPECIFICATIONS.md) and returned the default
to 52. Cylinder height no longer defaults to the card height (also 52); the
two remain independent settings.

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `cylinder_height_mm` | Primary input name |
| `app/models.py` | `height_mm` | In `CylinderParams` dataclass |
| `backend.py` | `height_mm`, `height` | Both accepted |
| `geometry_spec.py` | `height`, `height_mm` | Fallback to `52` (`gears.DEFAULT_CYLINDER_HEIGHT_MM`, no longer `settings.card_height`) |
| `csg-worker.js` | `height` | Direct usage |

#### Backend Processing (app/models.py - CylinderParams)

```python
@dataclass
class CylinderParams:
    height_mm: float = 52.0

    @staticmethod
    def from_dict(data: dict) -> 'CylinderParams':
        return CylinderParams(
            height_mm=float(data.get('height_mm', data.get('height', 52.0))),
            # ...
        )
```

#### Geometric Effect

The cylinder height determines the **vertical extent** of the cylindrical shell:

```
               ┌─────────────────┐ ▲
              /                   \│
             /                     \│
            │                       │ Height (mm)
            │       Cylinder        │
            │        Shell          │
             \                     /│
              \                   /│
               └─────────────────┘ ▼
```

**Key Relationships:**
- Braille content is vertically centered within the height
- Affects `first_row_center_y` calculation for vertical positioning
- Must accommodate `(grid_rows - 1) * line_spacing + 2 * dot_spacing`

#### geometry_spec.py Implementation

```python
# Calculate vertical centering
braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
space_above = (height - braille_content_height) / 2.0
first_row_center_y = height - space_above - settings.dot_spacing
```

---

### 2.3 Polygonal Cutout Circumscribed Radius

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Polygonal Cutout Circumscribed Radius (mm):` |
| Input ID | `cylinder_polygonal_cutout_radius_mm` |
| Input Name | `cylinder_polygonal_cutout_radius_mm` |
| Type | `number` |
| Default | `13` |
| Step | `0.1` |
| Min | `0` |
| Max | `50` |
| Note | Creates a polygonal cutout along the cylinder's length. Set to 0 for no cutout. |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `cylinder_polygonal_cutout_radius_mm` | Primary input name |
| `app/models.py` | `polygonal_cutout_radius_mm` | In `CylinderParams` dataclass |
| `geometry_spec.py` | `polygonal_cutout_radius_mm` | Direct usage |
| `csg-worker.js` | `polygon_points` | Computed from radius |

#### Backend Processing (app/models.py - CylinderParams)

```python
@dataclass
class CylinderParams:
    polygonal_cutout_radius_mm: float = 13.0

    @staticmethod
    def from_dict(data: dict) -> 'CylinderParams':
        return CylinderParams(
            polygonal_cutout_radius_mm=float(data.get('polygonal_cutout_radius_mm', 13.0)),
            # ...
        )
```

#### Geometric Effect

The polygonal cutout creates an **inner cavity** within the cylinder shell:

```
          CROSS-SECTION VIEW (Top-Down)

            Outer Cylinder Shell
                    ↓
                ┌───────┐
               /         \
              /  ┌─────┐  \
             │   │     │   │ ← Polygonal Cutout
             │   │     │   │
              \  └─────┘  /
               \         /
                └───────┘

          ◄─────────────────►
             Outer Diameter

              ◄─────────►
           Polygonal Cutout
         (Circumscribed Radius)
```

**Key Formulas:**

The circumscribed radius defines the distance from the polygon center to each vertex:

```python
# From geometry_spec.py
if polygonal_cutout_radius > 0:
    circumscribed_radius = polygonal_cutout_radius / math.cos(math.pi / polygonal_cutout_sides)
    for i in range(polygonal_cutout_sides):
        base_angle = 2 * math.pi * i / polygonal_cutout_sides
        rotated_angle = base_angle + cutout_align_theta
        polygon_points.append({
            'x': circumscribed_radius * math.cos(rotated_angle),
            'y': circumscribed_radius * math.sin(rotated_angle),
        })
```

**Special Value:**
- When `polygonal_cutout_radius_mm = 0`: No inner cutout is created; the cylinder is solid

---

### 2.4 Polygonal Cutout Points

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Polygonal Cutout Points:` |
| Input ID | `cylinder_polygonal_cutout_sides` |
| Input Name | `cylinder_polygonal_cutout_sides` |
| Type | `number` |
| Default | `12` |
| Step | `1` |
| Min | `3` |
| Max | `60` |
| Note | Lower values create simpler shapes (e.g., 6); higher values approximate a circle. |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `cylinder_polygonal_cutout_sides` | Primary input name |
| `app/models.py` | `polygonal_cutout_sides` | In `CylinderParams` dataclass |
| `geometry_spec.py` | `polygonal_cutout_sides` | Direct usage |
| `csg-worker.js` | `polygon_points.length` | Derived from points array |

#### Geometric Effect

The number of sides determines the **shape of the inner cutout**:

```
         3 sides          6 sides          12 sides         60 sides
          (tri)           (hex)            (dodecagon)      (≈circle)

           △               ⬡                 ⬢               ○
        /  |  \         /      \          /        \        (smooth)
       /___|___\       │        │        │          │
                        \      /          \        /
                          \__/              \____/
```

**Visual Polygon Reference:**

| Sides | Shape Name | Typical Use Case |
|-------|------------|------------------|
| 3 | Triangle | Unique orientation indicator |
| 4 | Square | Pen/pencil holders |
| 6 | Hexagon | Standard pen holders |
| 8 | Octagon | Larger tool holders |
| 12 | Dodecagon | Near-circular fit |
| 24+ | Near-circle | Smooth cylindrical fit |

---

### 2.5 Seam Offset

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Seam Offset (degrees):` |
| Input ID | `seam_offset_deg` |
| Input Name | `seam_offset_deg` |
| Type | `number` |
| Default | `355` |
| Step | `1` |
| Min | `0` |
| Max | `360` |
| Note | Rotates the starting position of braille text around the cylinder |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `seam_offset_deg` | Primary input name |
| `app/models.py` | `seam_offset_deg` | In `CylinderParams` dataclass |
| `geometry_spec.py` | `seam_offset_deg` → `seam_offset` | Converted to radians |
| `backend.py` | `seam_offset_deg`, `seam_offset_degrees` | Both accepted |

#### Backend Processing (app/models.py - CylinderParams)

```python
@dataclass
class CylinderParams:
    seam_offset_deg: float = 355.0

    @staticmethod
    def from_dict(data: dict) -> 'CylinderParams':
        return CylinderParams(
            seam_offset_deg=float(data.get('seam_offset_deg', data.get('seam_offset_degrees', 355.0))),
            # ...
        )
```

#### Geometric Effect

**Critical Behavior Note:**
The seam offset rotates **ONLY the polygonal cutout**, NOT the braille content. This allows users to align the polygon vertices (useful for pen holder compatibility) independently of where the braille text appears.

```
          TOP-DOWN VIEW - Seam Offset Effect

      Seam Offset = 0°              Seam Offset = 90°
           ⬡                              ◇
          / \                            /   \
         /   \                          /     \
        |     |                        /       \
         \   /                         \       /
          \ /                           \     /
                                         \   /
                                          \ /

      Polygon vertex at 0°         Polygon vertex rotated 90°
      (Braille unchanged)          (Braille unchanged)
```

#### geometry_spec.py Implementation

```python
seam_offset_rad = math.radians(seam_offset)

if plate_type == 'negative':
    # Counter plate: rotate polygon CLOCKWISE (positive angle direction)
    cutout_align_theta = seam_offset_rad
else:
    # Embossing plate: rotate polygon COUNTER-CLOCKWISE (negative angle direction)
    cutout_align_theta = -seam_offset_rad

# Apply rotation only to polygon points
for i in range(polygonal_cutout_sides):
    base_angle = 2 * math.pi * i / polygonal_cutout_sides
    rotated_angle = base_angle + cutout_align_theta  # ← Seam offset applied here
    polygon_points.append({
        'x': circumscribed_radius * math.cos(rotated_angle),
        'y': circumscribed_radius * math.sin(rotated_angle),
    })
```

#### Emboss vs Counter Plate Rotation Direction

| Plate Type | Rotation Direction | Formula |
|------------|-------------------|---------|
| Positive (Emboss) | Counter-clockwise | `cutout_align_theta = -seam_offset_rad` |
| Negative (Counter) | Clockwise | `cutout_align_theta = seam_offset_rad` |

This ensures that when the emboss and counter plates are aligned face-to-face, their polygon cutouts match up correctly.

### 2.6 Slicer Seam Channel

**Since 2026-09-20 (programme decisions D-1, D-2, D-13, D-14, D-15).** Every cylinder carries a shallow V-groove along its OUTER surface, on both plates: the full height beside the row-indicator column in visual mode, and since 2026-09-21 (D-T6, D-T7) the full height down the tactile arrow column itself in tactile mode, where on the embossing plate it steps round each raised arrow on the first-cell side instead of cutting through it (D-T8, 2026-09-22). A slicer's default "aligned" seam mode snaps each layer's seam into a concave corner, and on a smooth barrel the only corners are where dots and bowls meet the surface; a layer seam inside a dot ruins that dot on paper. The groove is a better corner, so the seam never needs painting.

#### UI Element

| Property | Value |
|----------|-------|
| Location | Expert Mode → Surface Dimensions → "Slicer Seam Channel" fieldset |
| Control | `<input type="checkbox" id="seam_channel_enabled" checked>` |
| Label | `Slicer seam channel` (S-C1, signed 2026-09-21) |
| Description (`aria-describedby="seam-channel-note"`, 19 words) | "A shallow groove beside the row markers where the slicer hides its layer seam, keeping it off the dots." (S-C1 (signed 2026-09-21)) |
| Default | ON |
| Persistence | `braille_prefs_seam_channel_enabled` (`'1'`/`'0'`); reset restores ON |
| Live note | `#seam-channel-warning` / `#seam-channel-message`, shown before Generate when the groove will be left out (S-C2 / S-C3 below), announced once through `#a11y-status` on its hidden-to-shown edge |

#### Wire

| Switch | Request body |
|--------|--------------|
| ON (default) | Nothing is added. An untouched request body is byte-identical to a pre-channel one (pinned by `tests/e2e/seamChannel.spec.ts` against the captured `tests/e2e/fixtures/*.request.json`). |
| OFF | `settings.seam_channel_enabled: 0` and nothing else. |

Schema: `settings.schema.json` → `seam_channel.enabled` (boolean, default `true`). Model: `app/models.py` → flat `seam_channel_enabled`, default `1`; an absent or blank field means ON.

#### Geometry (constants, not dials)

The groove is print-tuned, so its size lives in `app/geometry_spec.py` and nowhere a user can edit:

| Constant | Value | Meaning |
|----------|-------|---------|
| `SEAM_CHANNEL_WIDTH_MM` | 1.0 mm | mouth width at the surface (a 90° V) |
| `SEAM_CHANNEL_DEPTH_MM` | 0.5 mm | apex depth below the surface |
| `SEAM_CHANNEL_MARGIN_MM` | 0.25 mm | clear surface kept either side of the mouth |
| `SEAM_CHANNEL_OVERSHOOT_MM` | 1.0 mm | the cutter runs this far past both end faces |
| `SEAM_CHANNEL_LIP_MM` | 0.5 mm | the cutter's mouth starts this far outside the surface, so the mouth is cut rather than touched |
| `SEAM_CHANNEL_MIN_WALL_MM` | 1.2 mm | FDM minimum wall left under the apex |

Documented safe ranges (a change needs Brennen's decision and a new slicing spike): width 0.8–1.6 mm, depth 0.3–0.8 mm. The 2026-09-20 spike (`scripts/seam_spike.py`, PrusaSlicer 0.2 mm layers, first outer-wall seam per layer) measured: in aligned mode the 1.0 × 0.5 groove captured 100 % of layers on both visual plates and on the tactile counter plate, and 90.8 % on the tactile embossing plate with every escaped layer on a raised arrow tip and none in a dot; 1.2 × 0.6 and sharper or deeper profiles captured the same. Without a groove, 18–24 % of layers landed in a dot or bowl. "Back"/"rear" seam mode cannot be made safe for the embossing plate by any export orientation (a raised dot within about 20° of the rear always out-reaches the channel floor), so exports are NOT rotated (D-14) and users whose profile says Back switch it to Aligned once.

Placement, as signed arc `s` along the surface from the seam centre, positive toward column 0 (`R` = radius):

```
gap       = π · diameter − (grid_columns_total − 1) · cell_spacing
footprint = dot_spacing / 2 + max(active dot base radius, active recess mouth radius)
            (double-sided: the ds_* package's dot and bowl radii; the SAME number on both plates)
visual :  lo = −(gap/2 − footprint)                  hi = gap/2 − dot_spacing/2        (column 0's triangle)
tactile:  The groove runs down the arrow column itself (D-T6, 2026-09-21): theta = π on BOTH plates, the FULL
          height (D-T7, same day, after Brennen's print: wherever the groove stopped, the slicer chose a dot).
          COUNTER plate: straight, the same cut as visual mode - its recesses are deeper (0.7 mm) than the groove
          (0.5), so the cut runs through them. EMBOSSING plate (D-T8, 2026-09-22): the groove steps round every
          raised arrow on the FIRST-CELL side (theta below π in the spec, the side toward column 0) instead of
          running through it, so the arrows stay whole. Worked in the arrows' tangent plane at 180°, x across the
          column (negative toward the first cell), its centre line keeps d = SEAM_CHANNEL_WIDTH_MM / 2 +
          SEAM_CHANNEL_MARGIN_MM = 0.75 mm from each raised outline (grown by the gear weld, 0.005, in gear
          mode) and never slants more than SEAM_CHANNEL_DETOUR_SLANT_DEG (45°) off the axis. Round one arrow of
          half-base b, base z_b and tip z_t, with γ = 45°:
            leaves the centre at z_b − (d + b·cos γ) / sin γ     (3.061 mm below the base at the defaults)
            slants at γ to the circle of radius d about the base corner, rounds it (widest: b + d = 2.75 mm)
            runs parallel to the long side, rounds the circle of radius d about the tip
            slants back at γ to the centre at z_t + d / sin γ    (1.061 mm above the tip)
          (an arrow whose side is flatter than γ - short and wide - goes straight from its base corner's circle
          back to the centre, its tip already clear). With several arrows the centre line is the lower envelope
          of the one-arrow lines: the line nearest the column that clears them all. The per-row arrows touch tip
          to base, so there it zig-zags - up each arrow's side, then out at γ to the next arrow's base corner,
          1.147 mm from the column at its nearest (1.913 mm below each join) - and is on the column only below
          the chain and above it; the 0.3 preset's three arrows are 5 mm apart, so between them it returns to
          the column for 0.878 mm. The slant, not a run along the base, is what keeps a V on every printed layer
          (a groove running across a layer leaves only a shallow flat step there). Emitted as `path`: (theta,
          z) points from the overshoot below the bottom face to the overshoot above the top one, theta = π +
          asin(x / R), the round corners as chords of at most SEAM_CHANNEL_DETOUR_ARC_STEP_DEG (7.5°) set
          outside the circle, and every sideways stretch split into pieces of at most
          SEAM_CHANNEL_DETOUR_STEP_MM (1.0) so each chord stays within 0.005 mm of the barrel.
          free = gap/2 − footprint (the first-cell side's room)
          need = tactile_indicator_width / 2 + SEAM_CHANNEL_WIDTH_MM + 2 · SEAM_CHANNEL_MARGIN_MM = 3.5 mm
          The rule is nominal, in the tangent plane. On the surface the path reaches R·asin(x / R) plus the
          outside-chord bulge, about 0.016 mm beyond b + d at the defaults, so exactly at the limit (14 cells
          on a 30.5 mm barrel: free 3.509) the flat beside the first cell's dots is 0.243 mm, not 0.25 - far
          below print resolution, and the UI mirrors the same simple rule.
visual:   free = hi − lo ;  need = SEAM_CHANNEL_WIDTH_MM + 2 · SEAM_CHANNEL_MARGIN_MM = 1.5 mm
          s_c = (lo + hi) / 2
          theta = π − s_c / R  (positive plate)      theta = π + s_c / R  (negative plate)
```

**The raised arrows stay whole (D-T8, 2026-09-22, Brennen's decisions).** From D-T7 until 2026-09-22 the embossing plate's groove was recut through the raised arrows (`arrow_recut`): each arrow kept its base half as two ridges and lost its point, and Brennen's testing showed that changed the arrow's feel and made it less distinguishable to a blind user. He chose the detour above on four counts, each from options put to him: the first-cell side (the only side with room in every supported layout — at 14 cells double-sided the nearest dot edge is 4.28 mm from the column there, 4.181 by the room rule's footprint, and 2.93 on the last-cell side), 0.25 mm of flat between the arrow and the groove (the channel's own margin, so the arrow's edge and 0.5 mm raise feel exactly as before), the 45° slant rather than a run along the base, and leaving the groove out with S-C2 where the detour has no room rather than falling back to the recut. The groove's size and the arrow are unchanged; the counter plate's recess is unchanged, so the arrow still nests. These are tactile-shape decisions: never move the detour to the other side, narrow its margin or cut an arrow again on your own.

`theta` is emitted in the SAME convention as every dot's `theta` in the spec (column 0 at +grid_angle/2 on the positive plate, seam centre at π, the counter plate mirrored), so `theta_A + theta_B = 2π`. The Manifold worker negates every theta it places — dots, markers and this channel alike — which is what puts the groove beside column 0 in the STL; the Python golden renderer uses theta as emitted. Neither may treat this angle differently from a dot's.

**Rerun round the arrows (2026-09-22, D-T8):** `scripts/seam_spike.py --layouts tactile13,tactile14,tactile12x3 --channels none,v10 --no-rear --out build/seam_spike_detour` — PrusaSlicer aligned mode, 260 layers per file; the embossing plate cut with the spec's own `path` through the golden renderer's cutter, and "in channel" measured against the path's angle at each layer's height. Embossing plate: 90.8 % of layers in the groove at 13 and at 14 cells (per-row chain), 93.1 % with the 0.3 preset's three arrows (`tactile12x3`); every other layer is one of the six just under an arrow's tip, where the seam sits on the arrow's own point at 180.0° — the price of the whole arrow, the same 90.8 % the 2026-09-20 spike measured with the arrows untouched. Counter plate unchanged: 36.9 % in the groove (52.7 % with three arrows), the rest on the recess arrows' own edges. **0 % in a dot or bowl on every plate** (without the groove, the three-arrow layout put 14.2 % / 10.0 % of layers in one). The print is still the evidence (see the D-T6 note below): Brennen's print test of this build decides it.

**Rerun through the arrows (2026-09-21, D-T7, superseded by D-T8):** `build/seam_spike_through` — the groove at 180° the full height and recut through the raised arrows. Embossing plate: 100 % of layers in the groove at 13 and at 14 cells, every seam between 180.00° and 180.02°. Counter plate: 36.9 % within 0.8 mm of arc of 180°, the rest on the recess arrows' own edges (170.7°–189.3°), where the deeper recess interrupts the groove; 0 % in a dot or bowl on every plate, with or without the groove. The D-T6 rerun (`build/seam_spike_column`, two stretches outside the chain: 60 % / 37 %, 0 % in a dot by this metric) is superseded — Brennen's Bambu Studio print of that build put seams in dots wherever the groove stopped, which this metric did not predict; the print, not the study, is the evidence. The script reads the tactile angle and path from the spec's own block and refuses to run if it and the spec disagree about the angle.

Worked numbers (30.8 mm, 0.4 mm preset, footprint 2.15 mm):

| Layout | gap | free | Result |
|--------|-----|------|--------|
| 15 columns, visual | 5.761 | 2.361 | s_c 0.450 → 178.33° (A) / 181.67° (B); in the STL 181.67° (A) / 178.33° (B) |
| 14 columns, tactile | 12.261 | 3.981 (need 3.5) | θ = 180° on both plates, the full height; the embossing plate's path leaves the column at z −23.061, reaches 2.75 mm out at each base corner, zig-zags 1.147 mm from the column at each join and is back at z 21.061 (4 rows, 52 mm); counter plate straight |
| 13 columns, tactile | 18.761 | 7.231 | the same — the arrow column does not move with the cell count (D-T6) |
| 14 columns, double-sided (0.4 package) | 12.261 | 4.181 | the same (tactile is locked on while double-sided); the back grid moves toward the last-cell side, 2.93 mm from the column there (4.28 on the first-cell side, measured to the nearest dot edge), which is why the detour takes the first-cell side |
| 15 columns, tactile | 5.761 | 0.731 | **left out on both plates, S-C2** — the arrows themselves already overlap the dots and the seam-GAP warning speaks too |

Fit rules (each leaves the groove out and adds one warning to `spec.warnings`; the UI shows the same sentence live):

| Rule | Warning (signed 2026-09-21) |
|------|---------------------------|
| visual: `free < 1.5 mm`; tactile (D-T8): the first-cell side's `gap/2 − footprint` under `tactile_indicator_width/2 + 1.5 mm` — the room the embossing plate's detour needs, applied to both plates so they keep or lose the groove together | S-C2: "The seam channel was left out: the seam gap is too narrow for it at this cell count and diameter." |
| wall under the apex `< 1.2 mm` — against the polygonal cutout's circumradius (`r / cos(π/sides)`), or `wall_thickness − depth` for a barrel hollowed by wall thickness (2 mm when the field is absent); solid barrels (integrated gears, Version 2) skip this rule | S-C3: "The seam channel was left out: the cylinder wall would be thinner than 1.2 mm under it." |

At the default 13.0 mm cutout (12-gon, circumradius 13.459) the wall under the apex is 15.4 − 0.5 − 13.459 = 1.441 mm; a 13.25 mm inscribed cutout (circumradius 13.717) already breaks 1.2.

Spec block, emitted only when the groove fits: `cylinder.seam_channel = {theta, width, depth, overshoot, lip}`, plus `path: [{theta, z}, …]` on the tactile embossing plate only (absent = the straight full-height groove, so every visual-mode spec and every counter plate is unchanged by D-T8). With the switch off, or the groove left out, the spec is byte-identical to the pre-channel spec apart from the omission warning.

#### Worker and golden renderer

`static/workers/csg-worker-manifold.js` → `createSeamChannelManifold()` builds the V in the radial/circumferential plane, extrudes it `height + 2 · overshoot` along the axis and subtracts it from the bare outer cylinder BEFORE the bore, the keyed pockets or the solid branch, so every barrel kind gets the same groove and nothing added later can be undercut. `tests/test_golden.py` → `_seam_channel_cutter()` does the same in `_build_ds_cylinder_mesh`; all six golden fixtures were regenerated once on 2026-09-20 (each gained exactly 8 triangles and lost the groove's 12.4–12.8 mm³, bounds unchanged). Proof from a real browser export: apex vertices at 181.67° (A) / 178.33° (B), nothing else at that radius on the end caps.

A block with a `path` (D-T8) goes to `createSeamChannelPathManifold()` instead: a cone at every point — apex `depth` under the surface, axis radial, sides at the V's slope, mouth carried `lip` past the surface, 32 segments so a straight run keeps the exact V — hulled with the next one, and the hulls unioned, which sweeps the same V along the path. It is cut in the same shell stage, from the bare barrel: the path never comes within 0.25 mm of an arrow's outline, so the arrows' embedded base cannot fill it back and nothing has to be cut after they join (the D-T7 recut stage is gone, and with it `SEAM_CHANNEL_ARROW_MARGIN_MM`, `SEAM_CHANNEL_RECUT_INSET_MM` and `tactile_arrow_span()`). `_seam_channel_path_cutter()` in `tests/test_golden.py` is the same construction with manifold3d; the four embossing-plate golden fixtures were regenerated on 2026-09-22 and the four counter-plate ones are byte-identical.

Cards never get a channel.

---

## 3. Plate Dimensions

Plate dimensions control the physical size of flat braille cards/plates. These are the foundational parameters that determine the overall surface area available for braille content.

### 3.1 Plate Width

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Plate Width:` |
| Input ID | `card_width` |
| Input Name | `card_width` |
| Type | `number` |
| Default | `90` |
| Step | `0.1` |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `card_width` | Primary input name |
| `app/models.py` | `card_width` | In `CardSettings` class |
| `geometry_spec.py` | `settings.card_width` | Direct usage |
| `csg-worker.js` | `plate.width` | In geometry spec |

#### Backend Processing (app/models.py - CardSettings)

```python
class CardSettings:
    def __init__(self, **kwargs):
        defaults = {
            'card_width': 90,
            # ...
        }
        # ...
        # Grid width calculation
        self.grid_width = (self.grid_columns - 1) * self.cell_spacing

        # Center the grid on the card with calculated margins
        self.left_margin = (self.card_width - self.grid_width) / 2
        self.right_margin = (self.card_width - self.grid_width) / 2
```

#### Geometric Effect

The plate width determines the **horizontal extent** of the braille card:

```
        ◄────────────── Plate Width (mm) ──────────────────►

        ┌────────────────────────────────────────────────────┐
        │                                                     │
        │  ◄─ left_margin ─►│◄── grid_width ──►│◄─ right ─►  │
        │                   │                   │  margin     │
        │                   │  ⬤ ⬤   ⬤   ⬤ ⬤ │              │
        │                   │  ⬤ ⬤   ⬤   ⬤ ⬤ │              │
        │                   │  ⬤ ⬤   ⬤   ⬤ ⬤ │              │
        │                   │                   │              │
        └────────────────────────────────────────────────────┘
```

**Key Calculations:**
```python
grid_width = (grid_columns - 1) * cell_spacing
left_margin = (card_width - grid_width) / 2
right_margin = (card_width - grid_width) / 2
```

---

### 3.2 Plate Height

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Plate Height:` |
| Input ID | `card_height` |
| Input Name | `card_height` |
| Type | `number` |
| Default | `52` |
| Step | `0.1` |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `card_height` | Primary input name |
| `app/models.py` | `card_height` | In `CardSettings` class |
| `geometry_spec.py` | `settings.card_height` | Direct usage |
| `csg-worker.js` | `plate.height` | In geometry spec |

#### Backend Processing (app/models.py - CardSettings)

```python
class CardSettings:
    def __init__(self, **kwargs):
        defaults = {
            'card_height': 52,
            # ...
        }
        # ...
        # Grid height calculation
        self.grid_height = (self.grid_rows - 1) * self.line_spacing

        # Center the grid on the card with calculated margins
        self.top_margin = (self.card_height - self.grid_height) / 2
        self.bottom_margin = (self.card_height - self.grid_height) / 2
```

#### Geometric Effect

The plate height determines the **vertical extent** of the braille card:

```
                          ▲
                          │
        ┌─────────────────┤ top_margin
        │                 │
        │   ⬤ ⬤   ⬤ ⬤ ⬤ │
        │   ⬤ ⬤   ⬤ ⬤ ⬤ │
    P   │   ⬤ ⬤   ⬤ ⬤ ⬤ │ grid_height
    l   │                 │
    a   │   ⬤ ⬤   ⬤ ⬤ ⬤ │
    t   │   ⬤ ⬤   ⬤ ⬤ ⬤ │
    e   │   ⬤ ⬤   ⬤ ⬤ ⬤ │
        │                 │
    H   │                 │
    e   ├─────────────────┤ bottom_margin
    i   │                 │
    g   └─────────────────┘
    h                     ▼
    t
```

**Key Calculations:**
```python
grid_height = (grid_rows - 1) * line_spacing
top_margin = (card_height - grid_height) / 2
bottom_margin = (card_height - grid_height) / 2
```

---

### 3.3 Plate Thickness

#### UI Element

| Property | Value |
|----------|-------|
| Label | `Plate Thickness:` |
| Input ID | `card_thickness` |
| Input Name | `card_thickness` |
| Type | `number` |
| Default | `2.0` |
| Step | `0.1` |

#### Parameter Names Across Codebase

| Source | Parameter Name | Notes |
|--------|----------------|-------|
| HTML/UI | `card_thickness` | Primary input name |
| `app/models.py` | `card_thickness`, `plate_thickness_mm` | Both in `CardSettings` |
| `geometry_spec.py` | `settings.card_thickness` | Direct usage |
| `csg-worker.js` | `plate.thickness` | In geometry spec |
| `backend.py` | `params.plate_thickness` | Used in recess depth calculations |

#### Backend Processing (app/models.py - CardSettings)

```python
class CardSettings:
    def __init__(self, **kwargs):
        defaults = {
            'card_thickness': 2.0,
            'plate_thickness_mm': 2.0,
            # ...
        }
        # ...
        # Clamp depth to safe bounds (0..plate_thickness)
        depth = float(getattr(self, 'counter_dot_depth', 0.8))
        self.counter_dot_depth = max(0.0, min(depth, self.card_thickness - self.epsilon_mm))
        self.plate_thickness = self.card_thickness
```

#### Geometric Effect

The plate thickness determines the **depth (Z-dimension)** of the braille card:

```
        SIDE VIEW (Cross-Section)

        ←───────── Width ──────────→

        ┌──────────────────────────┐ ─┬─
        │      Embossed Dots       │  │
        │         ⬤                │  │ Dot Height
        ├──────────────────────────┤ ─┴─
        │                          │  │
        │    Plate Base Material   │  │ Plate Thickness
        │                          │  │
        └──────────────────────────┘ ─┴─
```

**Key Relationships:**
- Dots are positioned at `z = card_thickness + active_dot_height / 2`
- Counter plate recesses are constrained to `max_depth = plate_thickness - epsilon`
- Z-coordinate system: `z=0` is bottom surface, `z=plate_thickness` is top surface

---

## 4. Parameter Flow: UI to Backend

### Complete Parameter Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UI (index.html)                                │
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────────────┐│
│  │ Cylinder Dimensions │  │  Plate Dimensions   │  │  Other Expert Mode   ││
│  │  cylinder_diameter  │  │    card_width       │  │    Parameters        ││
│  │  cylinder_height    │  │    card_height      │  │                      ││
│  │  cutout_radius      │  │    card_thickness   │  │                      ││
│  │  cutout_sides       │  │                     │  │                      ││
│  │  seam_offset_deg    │  │                     │  │                      ││
│  └─────────┬───────────┘  └──────────┬──────────┘  └──────────┬───────────┘│
│            │                         │                        │            │
└────────────┼─────────────────────────┼────────────────────────┼────────────┘
             │                         │                        │
             ▼                         ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Form Serialization                                   │
│  (JavaScript collects form values → POST /generate_braille_stl)             │
└─────────────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              backend.py                                     │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  CardSettings(**kwargs)                                               │  │
│  │    - Parses plate dimensions from settings dict                       │  │
│  │    - Calculates grid_width, grid_height                               │  │
│  │    - Calculates left_margin, top_margin (centering)                   │  │
│  │    - Validates margins and dot clearances                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  CylinderParams.from_dict(data)                                       │  │
│  │    - Parses diameter_mm, height_mm, seam_offset_deg                   │  │
│  │    - Parses polygonal_cutout_radius_mm, polygonal_cutout_sides        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
             │
             ├──────────────────────────────────┐
             ▼                                  ▼
┌────────────────────────────────┐  ┌────────────────────────────────────────┐
│  geometry_spec.py              │  │  app/geometry/cylinder.py              │
│                                │  │                                        │
│  extract_card_geometry_spec()  │  │  generate_cylinder_stl()               │
│  extract_cylinder_geometry_spec│  │  generate_cylinder_counter_plate()     │
│                                │  │                                        │
│  Creates JSON spec with:       │  │  Creates 3D geometry with trimesh:     │
│  - plate: {width, height, ...} │  │  - Cylinder shell                      │
│  - cylinder: {radius, ...}     │  │  - Polygonal cutout subtraction        │
│  - dots: [{x, y, z, params}]   │  │  - Dot addition/subtraction            │
│  - markers: [{type, ...}]      │  │  - Marker subtraction                  │
└────────────────────────────────┘  └────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          csg-worker.js                                      │
│                                                                             │
│  processGeometrySpec(spec)                                                  │
│    ├── createCylinderShell(spec.cylinder)                                   │
│    │     - THREE.CylinderGeometry(radius, height)                           │
│    │     - Polygon cutout via ExtrudeGeometry + SUBTRACTION                 │
│    │                                                                        │
│    ├── Card: THREE.BoxGeometry(width, height, thickness)                    │
│    │                                                                        │
│    ├── createCylinderDot(dotSpec) / createBrailleDot(dotSpec)               │
│    │                                                                        │
│    └── Boolean operations (ADDITION / SUBTRACTION)                          │
│                                                                             │
│  exportToSTL(geometry) → ArrayBuffer                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Geometry Construction Details

### 5.1 Card Plate Construction

#### Base Plate Creation (backend.py)

```python
# From build_counter_plate_hemispheres() and similar functions
plate_mesh = trimesh.creation.box(
    extents=(params.card_width, params.card_height, params.plate_thickness)
)
plate_mesh.apply_translation(
    (params.card_width / 2, params.card_height / 2, params.plate_thickness / 2)
)
```

#### geometry_spec.py Output

```python
spec = {
    'shape_type': 'card',
    'plate_type': plate_type,
    'plate': {
        'width': settings.card_width,
        'height': settings.card_height,
        'thickness': settings.card_thickness,
        'center_x': settings.card_width / 2,
        'center_y': settings.card_height / 2,
        'center_z': settings.card_thickness / 2,
    },
    'dots': [],
    'markers': [],
}
```

#### csg-worker.js Implementation

```javascript
// Card plate
const { width, height, thickness, center_x, center_y, center_z } = plate;
baseGeometry = new THREE.BoxGeometry(width, height, thickness);
baseGeometry.translate(center_x, center_y, center_z);
```

### 5.2 Cylinder Shell Construction

#### geometry_spec.py Cylinder Specification

```python
spec = {
    'shape_type': 'cylinder',
    'plate_type': plate_type,
    'cylinder': {
        'radius': radius,               # diameter / 2
        'height': height,               # From cylinder_height_mm
        'thickness': thickness,         # Wall thickness (not used when polygon specified)
        'polygon_points': polygon_points,  # Computed polygon vertices
    },
    'dots': [],
    'markers': [],
}
```

#### csg-worker.js Cylinder Shell Implementation

```javascript
function createCylinderShell(spec) {
    const { radius, height, thickness, polygon_points } = spec;

    const validRadius = (radius && radius > 0) ? radius : 30;
    const validHeight = (height && height > 0) ? height : 80;

    // Create outer cylinder
    const outerGeom = new THREE.CylinderGeometry(validRadius, validRadius, validHeight, 64);
    const outerBrush = new Brush(outerGeom);

    // Check if polygon cutout is specified with valid points
    const validPoints = (polygon_points && polygon_points.length > 0)
        ? polygon_points.filter(pt => pt && isFinite(pt.x) && isFinite(pt.y))
        : [];

    if (validPoints.length >= 3) {
        // Polygon cutout specified: use polygon as the inner boundary
        const polygonShape = new THREE.Shape();
        validPoints.forEach((pt, i) => {
            if (i === 0) {
                polygonShape.moveTo(pt.x, pt.y);
            } else {
                polygonShape.lineTo(pt.x, pt.y);
            }
        });
        polygonShape.closePath();

        const extrudeSettings = {
            depth: validHeight * 1.5,  // Ensure it cuts all the way through
            bevelEnabled: false
        };

        const cutoutGeom = new THREE.ExtrudeGeometry(polygonShape, extrudeSettings);
        cutoutGeom.translate(0, 0, -validHeight * 0.75);
        cutoutGeom.rotateX(Math.PI / 2);  // Align with cylinder's Y-axis

        const cutoutBrush = new Brush(cutoutGeom);

        // Subtract polygon from outer cylinder
        const shellBrush = evaluator.evaluate(outerBrush, cutoutBrush, SUBTRACTION);
        return shellBrush.geometry;
    } else {
        // No polygon cutout: return solid cylinder
        return outerGeom;
    }
}
```

**Important Implementation Note:**
The `thickness` parameter in `cylinder` is NOT used when a polygon cutout is specified. The polygon vertices define the exact inner boundary, and the thickness parameter would conflict with this. This is documented in the csg-worker.js code:

```javascript
/**
 * NOTE: The 'thickness' parameter is NOT used when a polygon cutout is specified,
 * because the polygon defines the inner boundary. This prevents the issue where
 * increasing the outer diameter causes the inner cylinder (based on fixed wall
 * thickness) to grow larger than the polygon cutout, making it invisible.
 */
```

---

## 6. CSG Worker Implementation

### 6.1 Overview

The `csg-worker.js` runs in a Web Worker to perform computationally intensive boolean operations without blocking the main thread.

### 6.2 Coordinate System Transformation

```
        Server (backend.py)           Client (csg-worker.js)
        ─────────────────────         ────────────────────────
              Z-up                          Y-up
               ↑                             ↑
               │                             │
               │ Z (height)                  │ Y (height)
               │                             │
        ───────┼──────► X              ──────┼─────► X
              /                             /
             /                             /
            ↙ Y                           ↙ Z

        Rotation for STL export:
        geometry.rotateX(Math.PI / 2)  // Y-up → Z-up
```

### 6.3 Final Orientation Correction

```javascript
// For cylinders: rotate from Y-up (Three.js) to Z-up (STL/CAD convention)
if (isCylinder) {
    finalGeometry.rotateX(Math.PI / 2);
    console.log('CSG Worker: Rotated cylinder to Z-up orientation');
}
```

---

## 7. Default Values Reference

### 7.1 Cylinder Parameters (from app/models.py)

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `diameter_mm` | `31.35` | mm | Outer cylinder diameter |
| `height_mm` | `None` (uses `card_height`) | mm | Cylinder height |
| `wall_thickness` | `2.0` | mm | Shell wall thickness (when no polygon) |
| `seam_offset_deg` | `355.0` | degrees | Polygon rotation offset |
| `polygonal_cutout_radius_mm` | `13.0` | mm | Inner polygon circumscribed radius |
| `polygonal_cutout_sides` | `12` | count | Number of polygon vertices |

### 7.2 Card Parameters (from app/models.py)

| Parameter | Default | Unit | Description |
|-----------|---------|------|-------------|
| `card_width` | `90` | mm | Card width (X dimension) |
| `card_height` | `52` | mm | Card height (Y dimension) |
| `card_thickness` | `2.0` | mm | Card thickness (Z dimension) |
| `plate_thickness_mm` | `2.0` | mm | Alias for card_thickness |
| `epsilon_mm` | `0.001` | mm | Numerical tolerance |

### 7.3 UI Default Values (from index.html)

| Input ID | Default Value | Step | Range |
|----------|---------------|------|-------|
| `cylinder_diameter_mm` | `30.75` | 0.1 | 10-200 |
| `cylinder_height_mm` | `52` | 0.1 | 10-200 |
| `cylinder_polygonal_cutout_radius_mm` | `13` | 0.1 | 0-50 |
| `cylinder_polygonal_cutout_sides` | `12` | 1 | 3-60 |
| `seam_offset_deg` | `355` | 1 | 0-360 |
| `card_width` | `90` | 0.1 | none |
| `card_height` | `52` | 0.1 | none |
| `card_thickness` | `2.0` | 0.1 | none |

---

## 8. Validation and Constraints

### 8.1 Margin Safety Validation (CardSettings)

```python
def _validate_margins(self):
    """Validate that margins provide enough space for braille dots."""

    # Safety margin minimum (½ of cell spacing)
    self.min_safe_margin = self.cell_spacing / 2

    # Check if margins meet minimum safety requirements
    if self.left_margin < self.min_safe_margin:
        logger.warning(f'Left margin ({self.left_margin:.2f}mm) < min safe ({self.min_safe_margin:.2f}mm)')

    # Check if outermost dots will be within boundaries
    max_dot_extension = self.dot_spacing / 2
    left_edge_clearance = self.left_margin - max_dot_extension
    if left_edge_clearance < 0:
        logger.warning(f'Left edge dots will extend {-left_edge_clearance:.2f}mm beyond card edge')
```

### 8.2 Counter Dot Depth Clamping

```python
# Clamp depth to safe bounds (0..plate_thickness)
depth = float(getattr(self, 'counter_dot_depth', 0.8))
self.counter_dot_depth = max(0.0, min(depth, self.card_thickness - self.epsilon_mm))
```

---

## 9. Document History

| Date | Change |
|------|--------|
| 2026-08-31 | Cylinder height default 52 → 54 mm: the barrel now carries a 1 mm shelf past each edge of the 52 mm card so a slightly mis-rolled card cannot ruffle over the ends. Braille rows remain centered (the layout centers itself in the height). Cylinder height no longer falls back to `card_height` anywhere — the absent-field default is 54, owned by `app/geometry/gears.py` (`DEFAULT_CYLINDER_HEIGHT_MM`). |
| 2026-08-31 | **Cylinder height default returns to 52 mm — the 54 mm card-shelf barrel is Embosser Version 2 only** (Brennen's deployment verdict, same day). 52 is the Version 1 standard barrel, the height every previously shipped V1 gear model pairs with; the one-day 54 default made the integrated-gears BETA warn/reject on untouched dials. The decoupling from `card_height` stays: the absent-field fallback is 52, still owned by `gears.DEFAULT_CYLINDER_HEIGHT_MM`, and Version 2 still forces 30.8 × 54 via its preset overrides. Both card-stock presets carry 52 again. |
| 2026-09-20 | **Slicer seam channel (new §2.6).** Every cylinder now carries a V 1.0 × 0.5 mm groove the full height of its outer surface, in the seam gap beside the row-indicator column, on both plates, so a slicer's default "aligned" seam mode hides each layer's seam there instead of in a dot. ON by default; Expert Mode switch `#seam_channel_enabled` turns it off and is the only thing that sends `seam_channel_enabled: 0`. Constants in `app/geometry_spec.py` (`SEAM_CHANNEL_*`), placement and fit rules with worked numbers, the two DRAFT omission warnings S-C2/S-C3, the worker cut, the regenerated goldens and the slicing-spike evidence are all in §2.6. Decisions D-1, D-2, D-13, D-14 (no export rotation), D-15 (groove size). |
| 2026-09-21 | **§2.6: the tactile groove moves behind the arrow.** With the tactile arrow at a fixed lead-in before column 0 (RECESS_INDICATOR_SPECIFICATIONS.md v3.9, D-T1), the lead-in side keeps only its 1 mm margin, so in tactile mode the window is now between the last cell's dots (the back grid's, an interpoint offset closer, when double-sided) and the arrow recess; the visual window is unchanged. Worked numbers: 14 tactile 190.05° / 169.95°, 13 tactile the same, double-sided 187.72° / 172.28°. The slicing study reran on the new side (`scripts/seam_spike.py --layouts tactile14,tactile13 --channels none,v10 --no-rear --out build/seam_spike_leadin`, PrusaSlicer, aligned mode): counter plate 100 % of layers in the groove at both 13 and 14 cells, embossing plate 90.8 % with every escaped layer on a raised arrow tip and 0 % in any dot — the same figures as the 2026-09-20 study on the old side. All eight golden pairs regenerated. |
| 2026-09-21 | **§2.6: in tactile mode the groove runs down the arrow column itself (D-T6).** Brennen's test of the "behind the arrow" build showed the groove beside the arrows and a large trailing space; he asked for it centred on the arrows and the spacing back to even (the arrow returned to the seam-gap midpoint, RECESS_INDICATOR_SPECIFICATIONS.md v3.10). Tactile placement is now θ = 180° on both plates as two stretches (`segments`) that stop 0.3 mm (`SEAM_CHANNEL_ARROW_MARGIN_MM`) short of the arrow chain reported by `tactile_arrow_span()`; a stretch under 1.0 mm (`SEAM_CHANNEL_MIN_SEGMENT_MM`) is dropped and no stretch at all leaves the groove out with S-C4 (DRAFT). The worker and the golden renderer cut one prism per stretch. The slicing study reran on the column (`build/seam_spike_column`): 0 % of layers in a dot on every plate, 60 % / 37 % within 0.8 mm of 180°, the rest on the arrows' own edges. The visual groove is unchanged. All eight golden pairs regenerated. |
| 2026-09-21 | **§2.6: the tactile groove runs the full height and is recut through the raised arrows (D-T7).** Brennen's print of the D-T6 build: wherever the groove stopped short of the arrow chain the slicer chose a braille dot or bowl. His instruction: extend the channel through the triangles and between them along the axis; his choice for the cut through each raised arrow: the same V, its sides continued (2 mm wide at the top face — each arrow keeps its base half as two ridges and loses its point). Tactile placement is now θ = 180° on both plates the full height (no `segments`; S-C4 retired — nothing can leave the groove out in tactile mode), plus `arrow_recut = {z_from, z_to, lip}` on the embossing plate: the chain plus 0.3 mm at each end (`SEAM_CHANNEL_ARROW_MARGIN_MM`), clamped 0.05 mm inside the end faces (`SEAM_CHANNEL_RECUT_INSET_MM`, new), lip = raise + 0.5. The worker and the golden renderer subtract it after the raised arrows join. The slicing study reran (`build/seam_spike_through`): embossing plate 100 % in the groove, counter plate 36.9 % with the rest on the recess edges, 0 % in a dot. All eight golden pairs regenerated. |
| 2026-09-22 | **§2.6: on the embossing plate the tactile groove steps round the raised arrows instead of through them (D-T8).** Brennen's testing of the D-T7 build: the V through each raised arrow changed its feel and made the triangle less distinguishable to a blind user; he asked for the channel to stay on the arrow column, follow the outline of each triangle and return to the centre between them. His choices, from options put to him: the first-cell side, 0.25 mm of flat between arrow and groove, a 45° slant (`SEAM_CHANNEL_DETOUR_SLANT_DEG`, new) rather than a run along the base, and the groove left out with S-C2 when the first-cell side has no room (now also a tactile rule: `gap/2 − footprint` against `tactile_indicator_width/2 + 1.5`, both plates, mirrored live by `updateSeamChannelUI()`; 15 tactile cells now lose the groove). The embossing plate's block carries `path` instead of `arrow_recut`; the recut stage, `SEAM_CHANNEL_ARROW_MARGIN_MM`, `SEAM_CHANNEL_RECUT_INSET_MM` and `tactile_arrow_span()` are gone; the counter plate and visual mode are unchanged. The slicing study reran (`build/seam_spike_detour`): embossing plate 90.8 % in the groove (93.1 % with three arrows), the rest on the arrow tips, counter plate unchanged, 0 % in a dot. The four embossing-plate golden fixtures regenerated; the four counter-plate fixtures are byte-identical. |

### 8.3 Polygon Point Validation (csg-worker.js)

```javascript
// Check if polygon cutout is specified with valid points
const validPoints = (polygon_points && polygon_points.length > 0)
    ? polygon_points.filter(pt => pt && isFinite(pt.x) && isFinite(pt.y))
    : [];

if (validPoints.length >= 3) {
    // Valid polygon - proceed with cutout
} else {
    // No valid polygon - return solid cylinder
}
```

### 8.4 Cylinder Radius/Height Validation (csg-worker.js)

```javascript
function createCylinderDot(spec) {
    const { theta, radius: cylRadius, params } = spec;

    // Validate essential parameters
    if (!isFinite(theta) || !isFinite(cylRadius) || cylRadius <= 0) {
        console.warn('createCylinderDot: Invalid theta or cylRadius, skipping dot');
        return null;
    }
    // ...
}
```

---

## 9. Interrelationships with Other Settings

### 9.1 Plate Size ↔ Grid Layout

The plate dimensions must accommodate the grid layout:

```
Required Width  ≥ grid_width + (2 × min_safe_margin)
                ≥ (grid_columns - 1) × cell_spacing + cell_spacing

Required Height ≥ grid_height + (2 × min_safe_margin)
                ≥ (grid_rows - 1) × line_spacing + cell_spacing
```

### 9.2 Plate Thickness ↔ Counter Dot Depth

```
counter_dot_depth ≤ plate_thickness - epsilon_mm
```

If the user enters a depth greater than plate thickness, it will be clamped.

### 9.3 Cylinder Diameter ↔ Braille Layout

The cylinder diameter affects angular spacing:

```
cell_spacing_angle = cell_spacing / radius
dot_spacing_angle = dot_spacing / radius
grid_angle = grid_width / radius
```

**Smaller diameter** → **larger angles** → **fewer columns fit** → **text may wrap or overflow**

### 9.4 Cylinder Height ↔ Card Height Inheritance

When `cylinder_height_mm` is not specified or is `None`, it inherits from `card_height`:

```python
height_mm=float(data.get('height_mm', data.get('height', card_height)))
```

This ensures vertical consistency between card and cylinder outputs.

---

## 10. Known Issues and Edge Cases

### 10.1 Polygon Cutout vs Wall Thickness Conflict

**Issue:** When a polygonal cutout is specified, the `thickness` parameter is ignored because the polygon defines the exact inner boundary.

**Resolution:** This is intentional behavior documented in `csg-worker.js`. The polygon always takes precedence.

### 10.2 Seam Offset Only Affects Polygon

**Issue:** Some users expect seam offset to rotate the braille content. It only rotates the polygon cutout.

**Resolution:** This is documented behavior. Braille content position is fixed; only the polygon alignment is adjustable via seam offset.

### 10.3 Very Small Diameter Cylinders

**Issue:** Small cylinder diameters can cause:
- Large angular spread of braille cells
- Dots may overlap or exceed 360° wrap
- Grid overflow warnings

**Minimum Recommended:** `diameter_mm ≥ (grid_columns × cell_spacing) / π`

### 10.4 Zero Polygonal Cutout Radius

**Issue:** When `polygonal_cutout_radius_mm = 0`, the cylinder is solid with no inner cavity.

**Behavior:** This is valid and intentional. CSG worker handles this by returning a solid cylinder.

### 10.5 High Polygon Side Counts (>30)

**Issue:** Very high polygon side counts (approaching a circle) can:
- Increase mesh complexity
- Slow down boolean operations
- Provide diminishing visual improvement

**Recommendation:** 12-24 sides is usually sufficient for smooth appearance.

### 10.6 Plate Dimension Input Validation

**Issue:** The HTML inputs for `card_width`, `card_height`, and `card_thickness` do not specify min/max constraints.

**Current Behavior:** CardSettings accepts any numeric value. Extremely small or negative values may cause issues.

**Recommendation for Future:** Add HTML5 validation attributes:
```html
<input type="number" min="10" max="500" step="0.1" ...>
```

### 10.7 Cylinder Diameter and Dot Positioning Coordination (FIXED & VERIFIED - Dec 2024)

**Issue:** When the cylinder diameter was adjusted via the UI radio dial, braille dots (especially rounded shape dots) appeared to float away from the cylinder surface along the radial line instead of maintaining contact.

**Root Cause:** The CSG worker's centering logic for rounded dots used bounding-box-based centering (`recenterGeometryAlongY()`), which could produce different results than the Python backend's explicit translation by `-dome_height / 2`. This inconsistency caused the radial positioning calculation to be off.

**Critical Implementation Requirement:**

The cylinder radius MUST be consistently used across:
1. **Cylinder shell creation** (`createCylinderShell()` in `csg-worker.js`)
2. **Dot positioning** (`createCylinderDot()` in `csg-worker.js`)
3. **Geometry spec generation** (`extract_cylinder_geometry_spec()` in `geometry_spec.py`)

**Parameter Flow for Cylinder Radius:**

```
UI Input (cylinder_diameter_mm)
    ↓
geometry_spec.py: radius = diameter / 2
    ↓
spec.cylinder.radius   AND   spec.dots[i].radius  (MUST be identical)
    ↓
csg-worker.js: createCylinderShell(spec.cylinder)
               createCylinderDot(spec.dots[i])
```

**Formula for Dot Radial Position:**

```javascript
// For embossing (positive) plates:
radialOffset = cylRadius + dotHeight / 2 + epsilon

// Where:
// - cylRadius: Cylinder radius from spec (diameter / 2)
// - dotHeight: Total dot height (base_height + dome_height for rounded)
// - epsilon: Small overlap for robust CSG (typically 0)
```

**Mathematical Proof of Correct Positioning:**

After centering, the dot geometry spans `[-dotHeight/2, +dotHeight/2]` along its axis.
When positioned at `radialOffset = cylRadius + dotHeight/2`:
- Inner edge: `radialOffset - dotHeight/2 = cylRadius` (flush with surface) ✓
- Outer edge: `radialOffset + dotHeight/2 = cylRadius + dotHeight` ✓

**Fix Applied (December 2024):**

Modified `csg-worker.js` to use explicit centering that matches the Python backend:
- Changed from: `recenterGeometryAlongY(geometry)` (bounding box-based)
- Changed to: `geometry.translate(0, -validDomeHeight / 2, 0)` (explicit, matching Python)

This ensures that the dot height calculation is consistent and the radial offset formula produces correct results across all cylinder diameter values.

**Debug Logging (Added December 2024):**

The CSG worker now logs critical values for debugging:

```javascript
// Cylinder shell creation
console.log(`CSG Worker: Creating cylinder shell with radius=${validRadius}mm, height=${validHeight}mm`);

// Rounded dot positioning
console.log(`CSG Worker: Rounded dot positioning: cylRadius=${cylRadius}, dotHeight=${dotHeight}, radialOffset=${radialOffset}`);
console.log(`CSG Worker: Expected dot base at radius ${radialOffset - dotHeight/2}, top at ${radialOffset + dotHeight/2}`);
```

**Validation:**
- Test with cylinder diameter = 20mm, 30.75mm (default), 40mm, 60mm, 80mm
- Verify dots remain flush with cylinder surface (no floating, no sinking)
- Compare client-side CSG output with Python backend output for consistency
- Check browser console for debug logs to verify radius values match

**Troubleshooting Checklist:**

If dots are floating away from the surface:
1. Check console for `CSG Worker: Creating cylinder shell with radius=X` - this is the shell radius
2. Check console for `CSG Worker: Rounded dot positioning: cylRadius=Y` - this should equal X
3. Check that `Expected dot base at radius` equals the shell radius
4. Verify the geometry spec is being regenerated when diameter changes (no caching issues)

**Important Note (December 2024):**

The cylinder CSG generation uses `csg-worker-manifold.js` (Manifold3D), NOT `csg-worker.js` (Three.js/three-bvh-csg). The same centering fix was required in both files:

**Manifold Worker Fix (`csg-worker-manifold.js`):**
```javascript
// After creating combined frustum+dome geometry (which spans [0, dotHeight] along Z):
dot = combinedDot.translate([0, 0, -dotHeight / 2]);
```

This centers the geometry at the origin so it spans `[-dotHeight/2, +dotHeight/2]`, matching the standard cone frustum behavior.

**Related Specifications:**
- See `BRAILLE_DOT_SHAPE_SPECIFICATIONS.md` Bug 7 for detailed analysis
- See `BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md` for coordinate system details

---

## Appendix A: Complete Parameter Cross-Reference

| UI Input ID | CardSettings Attribute | CylinderParams Attribute | geometry_spec Key | csg-worker.js Key |
|-------------|------------------------|--------------------------|-------------------|-------------------|
| `card_width` | `card_width` | — | `plate.width` | `plate.width` |
| `card_height` | `card_height` | — | `plate.height` | `plate.height` |
| `card_thickness` | `card_thickness`, `plate_thickness` | — | `plate.thickness` | `plate.thickness` |
| `cylinder_diameter_mm` | — | `diameter_mm` | `cylinder.radius` | `cylinder.radius` |
| `cylinder_height_mm` | — | `height_mm` | `cylinder.height` | `cylinder.height` |
| `cylinder_polygonal_cutout_radius_mm` | — | `polygonal_cutout_radius_mm` | `cylinder.polygon_points` | `cylinder.polygon_points` |
| `cylinder_polygonal_cutout_sides` | — | `polygonal_cutout_sides` | (via polygon_points) | (via polygon_points) |
| `seam_offset_deg` | — | `seam_offset_deg` | (applied to polygon_points) | (pre-applied) |

---

## Appendix B: Formula Reference

### B.1 Grid Centering

```python
grid_width = (grid_columns - 1) × cell_spacing
grid_height = (grid_rows - 1) × line_spacing
left_margin = (card_width - grid_width) / 2
top_margin = (card_height - grid_height) / 2
```

### B.2 Cylinder Angular Spacing

```python
radius = diameter / 2
cell_spacing_angle = cell_spacing / radius  # radians
dot_spacing_angle = dot_spacing / radius    # radians
grid_angle = grid_width / radius            # radians
start_angle = -grid_angle / 2               # radians (centered)
```

### B.3 Polygon Cutout Vertices

```python
circumscribed_radius = polygonal_cutout_radius / cos(π / polygonal_cutout_sides)

for i in range(polygonal_cutout_sides):
    base_angle = 2π × i / polygonal_cutout_sides
    rotated_angle = base_angle + cutout_align_theta
    x = circumscribed_radius × cos(rotated_angle)
    y = circumscribed_radius × sin(rotated_angle)
```

### B.4 Vertical Centering (Cylinder)

```python
braille_content_height = (grid_rows - 1) × line_spacing + 2 × dot_spacing
space_above = (height - braille_content_height) / 2
first_row_center_y = height - space_above - dot_spacing
```

---

*Document Version: 1.6*
*Last Updated: 2026-09-20*
*Revision Notes (1.6, 2026-09-20): New §2.6 Slicer Seam Channel and a Document History row — the groove every cylinder carries since 2026-09-20, its Expert Mode switch, wire, constants, placement and fit rules, worker cut and golden regeneration. The Table of Contents gained the 2.6 entry. No other section changed.*
*Revision Notes: Added detailed debug logging information and troubleshooting checklist for cylinder dot positioning (Section 10.7)*
*Revision Notes (1.2, 2026-08-21): Documentation only — the Source Files Referenced line named `templates/index.html`, an empty deprecated folder; it now names `public/index.html`. Part of the templates/ reference sweep (Phase 07b).*
*Revision Notes (1.3, 2026-08-22): Documentation only — the HTML Implementation sample in Section 1 showed the accordion chevron as a bare `<span class="expert-submenu-icon">`, which is no longer what ships. All six live chevrons gained `aria-hidden="true"` so the decorative `▼` stops being read as part of the toggle's accessible name (POST15_7 audit finding F-B; UI_INTERFACE_CORE_SPECIFICATIONS.md v1.20 §4.5). The sample is updated to match so it is not copied into a new submenu without the attribute. No dimension, formula or measurement changed.*
*Revision Notes (1.4, 2026-08-22): Documentation only — the same Section 1 sample still showed the accordion button as a bare `<button>`. Every one of the six is now the sole child of an `<h3 class="expert-submenu-heading">`, which the WAI-ARIA APG Accordion pattern requires and which gives the page a heading outline (audit finding F-A, decision D1). The `aria-controls` attribute and the panel `id`, always present in the real markup, are shown too: the click handler now resolves the panel through `aria-controls`, because the button no longer has a next sibling. Outline and rationale in UI_INTERFACE_CORE_SPECIFICATIONS.md v1.22 §4.11.*
*Revision Notes (1.5, 2026-08-22): The three plate-dimension inputs `card_width`, `card_height` and `card_thickness` in `public/index.html` now declare `min`/`max` (50–200, 30–150, 1–10 mm), copied verbatim from `app/validation.py`, which already enforced those ranges. No dimension, default or enforced limit changed. Recorded here for completeness rather than as an accessibility gain: these three sit inside a `<div hidden>` with `tabindex="-1"` as hidden carriers of the schema defaults, and were measured as absent from the accessibility tree both before and after, so no screen reader reaches them. The announcement fix in POST15_7 item E (audit finding F-M, decision D8) is real for the other ten dials only.*
*Source Files Referenced: backend.py, wsgi.py, app/models.py, geometry_spec.py, static/workers/csg-worker.js, public/index.html*
