"""
Interpoint (double-sided) geometry math.

Double-sided mode embosses both faces of one card in a single pass between two
counter-rotating cylinders. Cylinder A (the embossing plate, plate_type
'positive') carries the FRONT face's raised dots plus recesses that receive
Cylinder B's raised dots; Cylinder B (the counter plate, plate_type 'negative')
carries the BACK face's raised dots plus recesses that receive A's. The back
grid is offset diagonally from the front grid — the industry "interpoint"
offset — so a front dot and a back dot never land on the same spot of paper and
cancel each other out.

Everything here is a pure function: no I/O, no globals mutated, no settings
objects. Lengths are millimetres, angles radians unless a name ends in `_deg`.

Frames used below:
  * card frame — the braille layout unrolled flat. `x` is arc length around the
    cylinder measured from the grid centre (positive = the reading direction),
    `z` is height measured from the cylinder's mid-height. The grid is centred,
    so the seam — and the tactile row arrow that sits in it — is at
    x = +/- pi * radius.
  * cylinder frame — `theta` as used by app/geometry_spec.py, where the
    embossing plate places a card-frame position at theta = -x / radius
    (`apply_seam`) and the counter plate at theta = +x / radius
    (`apply_seam_mirrored`). The arrow sits at theta = pi, which is the fixed
    point of the theta -> -theta mirror between the two plates.

Numbers here come from the approved 2026-08-16 interpoint research
(decisions D1/D2/D3) and are recorded next to each constant. The grid itself
(2.5 / 6.5 / 10.0) is unchanged: interpoint offsets the back grid, it never
re-spaces braille.

numpy is imported inside the nip-clearance functions only, so the light
functions (transform, pairing, same-surface gap, arrow margins) stay importable
on the numpy-free serverless deployment.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any, NamedTuple

# -----------------------------------------------------------------------------
# D1 — INTERPOINT OFFSET (signed off 2026-08-16)
# -----------------------------------------------------------------------------
# Back grid sits (1.25, 1.25) mm diagonally from the front grid. Source: US
# Patent 5,527,117 (Roy, Impact Devices, 1996). A grid search over the
# fully-populated 2.5 / 6.5 / 10.0 lattice confirms this diagonal is the
# optimum: it maximises the smallest front-to-back centre distance (1.76777 mm).
INTERPOINT_OFFSET_X_MM = 1.25
INTERPOINT_OFFSET_Z_MM = 1.25
INTERPOINT_OFFSET_MIN_MM = 1.15
INTERPOINT_OFFSET_MAX_MM = 1.35

# -----------------------------------------------------------------------------
# D3 — WHICH WAY THE BACK GRID SHIFTS (signed off 2026-08-16)
# -----------------------------------------------------------------------------
# The sign of the interpoint translation in the card frame. Both signs give
# identical clearances (the lattice is symmetric); the sign only chooses which
# side of the seam arrow the back grid crowds:
#   direction = +1  ->  back features crowd the arrow at theta just ABOVE pi:
#                       the LEFT of Cylinder A's arrow for someone standing
#                       outside the cylinder, looking at the arrow, top upward.
#                       The back grid slides towards the END of the line, so the
#                       roomier 3.4 mm of land stays on the start-of-line side.
#                       This is D3 as signed off.
#   direction = -1  ->  the mirror image: crowding on the RIGHT of A's arrow,
#                       clear land after the last cell instead.
#
# TROUBLESHOOTING FIRST STOP. D3 was signed off in words ("left of the
# arrows"), never as a number, and "left" only means something from outside the
# cylinder — looked at from straight above the top face the two signs read as
# above/below the arrow, not left/right. +1 is those words traced through
# `apply_seam` here and the theta negation in csg-worker-manifold.js. No
# clearance number can catch a wrong choice, because both signs measure the
# same. So if a printed pair ever comes out crowded on the unexpected side of
# the arrow, or a double-sided pair will not register, FLIP THIS SIGN FIRST.
# `arrow_zone_margins` prints both signs for comparison against a real part.
BACK_GRID_DIRECTION = 1

# -----------------------------------------------------------------------------
# D2 — DOUBLE-SIDED FOOTPRINTS, "Option B" (signed off 2026-08-16)
# -----------------------------------------------------------------------------
# Double-sided mode needs smaller dots than single-sided mode: front and back
# features share one surface, and at the 1.25/1.25 offset the shipped sizes
# leave only 0.118 mm of material between neighbours — below the 0.34 mm that a
# 0.4 mm nozzle can print. Option B leaves 0.518 mm. Single-sided mode keeps
# today's sizes untouched.
DS_DOT_BASE_DIAMETER_MM = 1.2
DS_DOT_BASE_HEIGHT_MM = 0.4
DS_DOT_DOME_DIAMETER_MM = 0.8
DS_DOT_DOME_HEIGHT_MM = 0.4
DS_DOT_HEIGHT_MM = DS_DOT_BASE_HEIGHT_MM + DS_DOT_DOME_HEIGHT_MM
DS_BOWL_DIAMETER_MM = 1.3
DS_BOWL_DEPTH_MM = 0.5

# Footprint packages keyed by the UI's card-stock preset (decided 2026-08-20,
# FD-8/FD-9: the print matrix showed one fixed footprint cannot serve both
# stocks - the package that suits 0.4 mm card tears 0.35 mm card, and the one
# that suits thin card under-forms thick card). The DS_* module constants
# above are the 0.3 mm package (Option B) and stay the schema/CardSettings
# absent-field defaults; the 0.4 mm package is the Q2 print-matrix winner
# (clean emboss on 0.4 mm stock, 2026-08-20). public/index.html's
# DS_FOOTPRINTS must stay in lockstep - tests/test_smoke.py::
# test_ui_ds_footprints_match_interpoint_packages diffs the two.
DS_FOOTPRINTS_BY_PRESET = {
    '0.3': {
        'ds_dot_base_diameter': DS_DOT_BASE_DIAMETER_MM,
        'ds_dot_base_height': DS_DOT_BASE_HEIGHT_MM,
        'ds_dot_dome_diameter': DS_DOT_DOME_DIAMETER_MM,
        'ds_dot_dome_height': DS_DOT_DOME_HEIGHT_MM,
        'ds_bowl_base_diameter': DS_BOWL_DIAMETER_MM,
        'ds_bowl_depth': DS_BOWL_DEPTH_MM,
    },
    '0.4': {
        'ds_dot_base_diameter': 1.2,
        'ds_dot_base_height': 0.5,
        'ds_dot_dome_diameter': 1.0,
        'ds_dot_dome_height': 0.5,
        'ds_bowl_base_diameter': 1.4,
        'ds_bowl_depth': 0.5,
    },
}

# Printability thresholds for the material left between a dot and a neighbouring
# recess on the same surface (Bambu X1C, 0.4 mm nozzle: Arachne widens anything
# from 0.1 to 0.34 mm up to 0.34 mm, and drops below 0.1 mm). Those Arachne
# figures justify the FLOOR. They have never justified the reliable line.
#
# PROVISIONAL, and knowingly so (Brennen, 2026-08-23). The reliable line was
# 0.50 mm with no stated basis anywhere in the code or the specs, while the
# shipped 0.4 preset sits at 0.4678 mm nominal - missing it by 0.0322 mm, which
# is below what you can measure on the part. So the DEFAULT configuration
# warned "the ridge may come out thin or merged" on every double-sided run,
# about a package recorded embossing clean on 2026-08-20. An NVDA walkthrough
# found it as a standing warning, which is how a user learns to ignore warnings.
#
# 0.45 stops that. It is NOT a measured value. The two data points that exist
# (0.4953 and 0.4278 mm printed) BOTH PASSED, and two passing samples cannot
# locate a failure boundary - they only prove it lies somewhere below 0.4278.
# Deriving a threshold from them would repeat the mistake 0.50 already made.
# What should set this number is a print test that walks the gap down until the
# ridge visibly fails. Until that exists, 0.45 removes a false alarm and makes
# no printability claim.
#
# Known consequence, recorded rather than discovered later: at 0.45 the 0.4
# package clears on the NOMINAL figure (0.4678) while its PRINTED ridge (0.4278)
# does not. It also swaps which package demonstrates the nominal/printed split
# of FD-11b - that was the 0.3 package at 0.50, and is the 0.4 package here.
SAME_SURFACE_GAP_RELIABLE_MM = 0.45
SAME_SURFACE_GAP_FLOOR_MM = 0.34

# -----------------------------------------------------------------------------
# GRID AND CYLINDER — mirrors of the canonical defaults, not a new source
# -----------------------------------------------------------------------------
# Canonical sources: settings.schema.json > app/models.py > public/index.html.
# Kept here as function defaults so the math is testable on its own; if a
# default changes there, change it here in the same commit.
DOT_PITCH_MM = 2.5
CELL_PITCH_MM = 6.5
LINE_PITCH_MM = 10.0
TACTILE_COLUMNS = 14
GRID_ROWS = 4
CYLINDER_RADIUS_MM = 15.375

# Tactile row arrow, from app/geometry_spec.py and app/models.py. The counter
# plate's recess outline is the raised arrow grown by the clearance on each side.
TACTILE_ARROW_WIDTH_MM = 4.0
TACTILE_RECESS_CLEARANCE_MM = 0.2

# A dot silhouette: (height_above_the_surface_mm, radius_mm) breakpoints joined
# by straight lines, base first. Used by the nip-clearance functions.
DotProfile = Sequence[tuple[float, float]]


class NipResult(NamedTuple):
    """Result of rolling one raised dot through its paired recess."""

    min_clearance_mm: float
    max_dip_mm: float
    tau_at_min_rad: float


def rounded_dot_profile(
    base_diameter: float = DS_DOT_BASE_DIAMETER_MM,
    base_height: float = DS_DOT_BASE_HEIGHT_MM,
    dome_diameter: float = DS_DOT_DOME_DIAMETER_MM,
    dome_height: float = DS_DOT_DOME_HEIGHT_MM,
    dome_segments: int = 1,
) -> list[tuple[float, float]]:
    """
    Silhouette of a rounded dot as (height, radius) breakpoints.

    `dome_segments=1` is the straight-sided silhouette the research used: the
    dome is treated as a cone from the dome diameter down to a point. The real
    dome is a spherical cap that bulges outside that line (up to 0.15 mm wider
    at mid-height for the Option B dot), so the straight-line model is slightly
    optimistic about clearance. Pass a larger `dome_segments` to sample the true
    spherical cap instead.
    """
    if base_height < 0 or dome_height <= 0:
        raise ValueError('base_height must be >= 0 and dome_height must be > 0')
    if dome_segments < 1:
        raise ValueError('dome_segments must be >= 1')

    top_radius = dome_diameter / 2.0
    profile = [(0.0, base_diameter / 2.0), (base_height, top_radius)]
    if dome_segments == 1:
        profile.append((base_height + dome_height, 0.0))
        return profile

    # Spherical cap of radius sphere_r whose rim is the dome diameter and whose
    # pole is dome_height above that rim.
    sphere_r = (top_radius * top_radius + dome_height * dome_height) / (2.0 * dome_height)
    centre_height = base_height + dome_height - sphere_r
    for step in range(1, dome_segments + 1):
        height = base_height + dome_height * step / dome_segments
        offset = height - centre_height
        radius_sq = max(0.0, sphere_r * sphere_r - offset * offset)
        profile.append((height, math.sqrt(radius_sq)))
    return profile


def cone_dot_profile(base_diameter: float, height: float, flat_hat_diameter: float) -> list[tuple[float, float]]:
    """Silhouette of a cone-frustum dot as (height, radius) breakpoints."""
    if height <= 0:
        raise ValueError('height must be > 0')
    return [(0.0, base_diameter / 2.0), (height, flat_hat_diameter / 2.0)]


# The Option B dot, and the dot the 0.4 mm card preset ships today. The shipped
# dot is kept because the research's nip numbers were measured with it.
DS_DOT_PROFILE = rounded_dot_profile()
SHIPPED_PRESET_DOT_PROFILE = rounded_dot_profile(1.5, 0.5, 1.0, 0.5)


def mirror_theta(theta: float) -> float:
    """
    Mirror an angle between the two plates: theta -> -theta.

    This is the repo's existing counter-plate convention (`apply_seam` vs
    `apply_seam_mirrored` in app/geometry_spec.py). Its fixed points are theta 0
    and theta pi, and pi is where the tactile row arrow sits — so the arrow and
    its recess line up without any special case.
    """
    return -theta


def back_grid_transform(
    x_mm: float,
    z_mm: float,
    offset_x: float = INTERPOINT_OFFSET_X_MM,
    offset_z: float = INTERPOINT_OFFSET_Z_MM,
    direction: int = BACK_GRID_DIRECTION,
) -> tuple[float, float]:
    """
    Card-frame position of a back-side feature.

    A back-side feature reads normally from behind the card; seen from the front
    — the frame both cylinders are laid out in — its layout is mirrored about the
    seam plane, the vertical plane through the tactile arrow midpoint. Because
    the grid is centred, that plane also passes through the grid centre, so the
    mirror is simply x -> -x. The interpoint translation is then added.

    Args:
        x_mm: arc position of the feature in the back's own reading layout,
            measured from the grid centre.
        z_mm: height of the feature, measured from the cylinder's mid-height.
        offset_x: circumferential interpoint offset (D1, default 1.25 mm).
        offset_z: axial interpoint offset (D1, default 1.25 mm).
        direction: +1 or -1, the D3 sign. It applies to both components, so the
            back grid takes one diagonal step; see BACK_GRID_DIRECTION for which
            side of the seam arrow each sign crowds.

    Returns:
        (x_back, z_back) in the card frame. Feed x_back / radius through
        `apply_seam` for Cylinder A or `apply_seam_mirrored` for Cylinder B,
        exactly as front-side positions are fed today.
    """
    if direction not in (-1, 1):
        raise ValueError(f'direction must be -1 or +1, got {direction!r}')
    return (-x_mm + direction * offset_x, z_mm + direction * offset_z)


def _dot_position(dot: Any) -> tuple[float, float, float | None]:
    """Read (theta, height, radius) out of a dot spec dict or a (theta, y) pair."""
    if isinstance(dot, dict):
        try:
            theta = float(dot['theta'])
            height = float(dot['y'])
        except KeyError as exc:
            raise ValueError(f"dot dict needs 'theta' and 'y' keys, got {sorted(dot)}") from exc
        radius = dot.get('radius')
        return theta, height, None if radius is None else float(radius)
    theta, height = dot
    return float(theta), float(height), None


def pairing_map(front_dots: Iterable[Any]) -> list[tuple[Any, dict[str, float]]]:
    """
    Pair every raised dot on one cylinder with its recess on the other.

    A raised dot at cylinder angle theta is met by a recess at -theta on the
    opposing cylinder, at the same height. The mapping is exact — a float
    negation, no tolerance and no rounding — which is what lets a 0.1 mm nip
    clearance be meaningful.

    Args:
        front_dots: dot specs (dicts with 'theta' and 'y', optionally 'radius',
            as app/geometry_spec.py emits) or plain (theta, y) pairs.

    Returns:
        [(dot, paired_recess_position), ...] in the input order. Each position
        carries 'theta' and 'y'; when the dot knows its cylinder radius it also
        carries 'x', 'z' and 'radius' in the same Cartesian convention the
        geometry specs use (x = radius * cos(theta), z = radius * sin(theta)).
    """
    pairs: list[tuple[Any, dict[str, float]]] = []
    for dot in front_dots:
        theta, height, radius = _dot_position(dot)
        paired_theta = mirror_theta(theta)
        position: dict[str, float] = {'theta': paired_theta, 'y': height}
        if radius is not None:
            position['x'] = radius * math.cos(paired_theta)
            position['z'] = radius * math.sin(paired_theta)
            position['radius'] = radius
        pairs.append((dot, position))
    return pairs


def lattice_points(
    cols: int = TACTILE_COLUMNS,
    rows: int = GRID_ROWS,
    dot_pitch: float = DOT_PITCH_MM,
    cell_pitch: float = CELL_PITCH_MM,
    line_pitch: float = LINE_PITCH_MM,
) -> list[tuple[float, float]]:
    """
    Every dot position of a fully-populated grid: all six dots of every cell.

    This is the worst case for same-surface crowding. Real text never fills
    every position, but the counter plate's recesses may, and a user can type
    text that does.
    """
    points: list[tuple[float, float]] = []
    for col in range(cols):
        cell_x = col * cell_pitch
        for col_offset in (-dot_pitch / 2.0, dot_pitch / 2.0):
            for row in range(rows):
                cell_z = -row * line_pitch
                for row_offset in (dot_pitch, 0.0, -dot_pitch):
                    points.append((cell_x + col_offset, cell_z + row_offset))
    return points


def lattice_min_center_distance(
    offset_x: float = INTERPOINT_OFFSET_X_MM,
    offset_z: float = INTERPOINT_OFFSET_Z_MM,
    cols: int = TACTILE_COLUMNS,
    rows: int = GRID_ROWS,
    dot_pitch: float = DOT_PITCH_MM,
    cell_pitch: float = CELL_PITCH_MM,
    line_pitch: float = LINE_PITCH_MM,
) -> float:
    """
    Smallest centre-to-centre distance between a front feature and a back one.

    The back lattice is the front lattice mirrored and then translated, but a
    fully-populated grid is symmetric about its own centre, so the mirror maps
    it onto itself and the worst case reduces to a pure translation by the
    interpoint offset.
    """
    points = lattice_points(cols, rows, dot_pitch, cell_pitch, line_pitch)
    best_sq = math.inf
    for back_x, back_z in points:
        shifted_x = back_x + offset_x
        shifted_z = back_z + offset_z
        for front_x, front_z in points:
            dx = front_x - shifted_x
            dz = front_z - shifted_z
            distance_sq = dx * dx + dz * dz
            if distance_sq < best_sq:
                best_sq = distance_sq
    return math.sqrt(best_sq)


def printed_bowl_mouth_mm(bowl_diameter: float, bowl_depth: float) -> float:
    """
    How wide the bowl actually comes out, which is not its nominal diameter.

    `bowl_diameter` and `bowl_depth` describe a spherical cap — a mouth that
    wide, cut that deep — and the sphere they imply has radius
    (a^2 + h^2) / (2h) for mouth radius a and depth h. But the shipped Manifold
    worker centres that sphere ON the shell surface
    (static/workers/csg-worker-manifold.js, `radialOffset = cylRadius`), so what
    gets cut is the whole lower half of it: a hemisphere `sphere_radius` deep
    and 2 * `sphere_radius` across. The two nominal numbers are shape inputs to
    the sphere and nothing more — neither is a printed dimension.

    At the 0.3 package's 1.3 x 0.5 that is a 1.345 mm mouth; at the 0.4
    package's 1.4 x 0.5, 1.480 mm. Note the sphere radius is MINIMISED at
    bowl_depth = bowl_diameter / 2, so over part of the range a deeper nominal
    bowl prints SHALLOWER and narrower.

    The same convention lives in two places this function cannot reach: the
    Manifold worker named above (JavaScript) and `_ds_bowl_cutter` in
    tests/test_golden.py, which models the worker's mesh rather than calling
    into app code. Change one, check all three.
    """
    if bowl_depth <= 0:
        raise ValueError('bowl_depth must be > 0')
    mouth_radius = bowl_diameter / 2.0
    return (mouth_radius * mouth_radius + bowl_depth * bowl_depth) / bowl_depth


def same_surface_min_gap(
    dot_dia: float,
    recess_dia: float,
    offset_x: float = INTERPOINT_OFFSET_X_MM,
    offset_z: float = INTERPOINT_OFFSET_Z_MM,
    cols: int = TACTILE_COLUMNS,
    rows: int = GRID_ROWS,
    dot_pitch: float = DOT_PITCH_MM,
    cell_pitch: float = CELL_PITCH_MM,
    line_pitch: float = LINE_PITCH_MM,
) -> float:
    """
    Material left between a raised dot and its nearest neighbouring recess.

    Both live on the same cylinder surface: the raised dots of one face and the
    recesses that receive the other face's dots. Negative means the two
    footprints overlap and the printed ridge between them does not exist.

    Compare against SAME_SURFACE_GAP_RELIABLE_MM (0.50) and
    SAME_SURFACE_GAP_FLOOR_MM (0.34).

    `recess_dia` takes either bowl figure, and which one a caller passes is a
    decision, not a detail (Brennen, 2026-08-20). The hard printability gate in
    app/validation.py passes `printed_bowl_mouth_mm(...)`, because that is the
    ridge a printer has to hold. The two soft crowding warnings — in
    app/geometry_spec.py and public/index.html — pass the NOMINAL diameter, so
    the browser, the generator and the OpenSCAD port all report one number to
    the user and no warning threshold had to be re-decided. Feeding the printed
    mouth to the warnings would make the 0.3 package warn about itself
    (0.4953 mm against the 0.50 mm reliable line) even though it embosses
    clean.
    """
    center_distance = lattice_min_center_distance(offset_x, offset_z, cols, rows, dot_pitch, cell_pitch, line_pitch)
    return center_distance - (dot_dia + recess_dia) / 2.0


def arrow_zone_margins(
    direction: int = BACK_GRID_DIRECTION,
    recess_diameter_on_a: float = DS_BOWL_DIAMETER_MM,
    dot_diameter_on_b: float = DS_DOT_BASE_DIAMETER_MM,
    offset_x: float = INTERPOINT_OFFSET_X_MM,
    cols: int = TACTILE_COLUMNS,
    dot_pitch: float = DOT_PITCH_MM,
    cell_pitch: float = CELL_PITCH_MM,
    radius: float = CYLINDER_RADIUS_MM,
    arrow_width: float = TACTILE_ARROW_WIDTH_MM,
    recess_clearance: float = TACTILE_RECESS_CLEARANCE_MM,
) -> dict[str, Any]:
    """
    How close the shifted back grid comes to the tactile row arrow.

    The arrow sits in the seam gap at theta = pi. Shifting the back grid by the
    interpoint offset moves it towards the arrow on one side and away on the
    other; this reports both sides, on both cylinders, from feature edge to
    arrow edge.

    On Cylinder A the neighbouring feature is a back-side recess and the arrow
    is raised at its nominal width. On Cylinder B the feature is a raised back
    dot and the arrow is a recess whose outline is grown by the clearance on
    each side, so B is always the tighter of the two.

    Returns a dict with the seam gap, one entry per side (each naming the side's
    theta on Cylinder A and whether that reads as left or right of A's arrow
    from outside the cylinder), and the tightest margin found.
    """
    if direction not in (-1, 1):
        raise ValueError(f'direction must be -1 or +1, got {direction!r}')

    grid_width = (cols - 1) * cell_pitch
    half_circumference = math.pi * radius
    seam_gap = 2.0 * half_circumference - grid_width
    outermost = grid_width / 2.0 + dot_pitch / 2.0

    sides = []
    for sign in (1, -1):
        # The full back grid is the front grid mirrored (which maps it onto
        # itself) and then translated, so its outermost dot columns sit here.
        back_x = sign * outermost + direction * offset_x
        to_arrow_centre = half_circumference - abs(back_x)
        theta_a_deg = math.degrees(-back_x / radius) % 360.0
        sides.append(
            {
                'card_frame_sign': sign,
                'theta_on_a_deg': theta_a_deg,
                'side_of_arrow_on_a': 'left' if theta_a_deg > 180.0 else 'right',
                'centre_to_arrow_centre_mm': to_arrow_centre,
                'recess_edge_margin_on_a_mm': to_arrow_centre - arrow_width / 2.0 - recess_diameter_on_a / 2.0,
                'dot_edge_margin_on_b_mm': (
                    to_arrow_centre - (arrow_width / 2.0 + recess_clearance) - dot_diameter_on_b / 2.0
                ),
            }
        )

    tight = min(sides, key=lambda side: min(side['recess_edge_margin_on_a_mm'], side['dot_edge_margin_on_b_mm']))
    return {
        'direction': direction,
        'seam_gap_mm': seam_gap,
        'sides': sides,
        'tight_side_of_arrow_on_a': tight['side_of_arrow_on_a'],
        'tight_margin_mm': min(tight['recess_edge_margin_on_a_mm'], tight['dot_edge_margin_on_b_mm']),
    }


def _profile_outline(profile: DotProfile, samples_per_segment: int = 160):
    """Sample a dot silhouette into (radius, height) arrays, both sides of the axis."""
    import numpy as np

    radii: list[float] = []
    heights: list[float] = []
    for (height0, radius0), (height1, radius1) in zip(profile[:-1], profile[1:], strict=True):
        steps = np.linspace(0.0, 1.0, samples_per_segment)
        heights.extend(height0 + (height1 - height0) * steps)
        radii.extend(radius0 + (radius1 - radius0) * steps)
    radius_array = np.array(radii)
    height_array = np.array(heights)
    return np.concatenate([radius_array, -radius_array]), np.concatenate([height_array, height_array])


def _profile_surface(profile: DotProfile, azimuths: int = 36, samples_per_segment: int = 24):
    """Sample a dot silhouette revolved into a 3D surface: (tangential, axial, height) arrays."""
    import numpy as np

    radii: list[float] = []
    heights: list[float] = []
    for (height0, radius0), (height1, radius1) in zip(profile[:-1], profile[1:], strict=True):
        steps = np.linspace(0.0, 1.0, samples_per_segment)
        heights.extend(height0 + (height1 - height0) * steps)
        radii.extend(radius0 + (radius1 - radius0) * steps)
    radius_array = np.array(radii)[:, None]
    height_array = np.array(heights)[:, None]
    angle = np.linspace(0.0, 2.0 * np.pi, azimuths, endpoint=False)[None, :]
    tangential = radius_array * np.cos(angle)
    axial = radius_array * np.sin(angle)
    radial = np.broadcast_to(height_array, tangential.shape)
    return tangential.ravel(), axial.ravel(), radial.ravel()


def paired_nip_clearance(
    profile: DotProfile,
    bowl_diameter: float,
    bowl_depth: float,
    gap: float,
    radius: float = CYLINDER_RADIUS_MM,
    tau_limit: float = 0.5,
    tau_samples: int = 801,
) -> NipResult:
    """
    Roll a raised dot on Cylinder A through its paired recess on Cylinder B.

    Both cylinders have radius `radius` and are set `gap` mm apart surface to
    surface — the card travels through that gap. They counter-rotate at matched
    surface speed, so as A's dot passes the nip at angle -pi/2 + tau, B's bowl
    passes it at +pi/2 - tau. The bowl is modelled the way the shipped Manifold
    worker cuts it — the hemisphere `printed_bowl_mouth_mm` describes, centred
    ON B's surface — so the two nominal numbers are its shape inputs, not the
    hole it leaves.

    Returns:
        NipResult(min_clearance_mm, max_dip_mm, tau_at_min_rad). Clearance is
        the smallest distance from the dot's surface to B's material over the
        whole roll — negative means they intersect. Dip is how far the dot's tip
        reaches below B's nominal surface.
    """
    import numpy as np

    if bowl_depth <= 0:
        raise ValueError('bowl_depth must be > 0')

    tangential, height = _profile_outline(profile)
    sphere_radius = printed_bowl_mouth_mm(bowl_diameter, bowl_depth) / 2.0
    centre_a = np.array([0.0, radius + gap / 2.0])
    centre_b = np.array([0.0, -(radius + gap / 2.0)])

    min_clearance = math.inf
    max_dip = -math.inf
    tau_at_min = 0.0
    for tau in np.linspace(-tau_limit, tau_limit, tau_samples):
        angle_a = -np.pi / 2.0 + tau
        radial = np.array([np.cos(angle_a), np.sin(angle_a)])
        tangent = np.array([-np.sin(angle_a), np.cos(angle_a)])
        points = (
            centre_a[None, :] + (radius + height)[:, None] * radial[None, :] + tangential[:, None] * tangent[None, :]
        )

        angle_b = np.pi / 2.0 - tau
        bowl_centre = centre_b + radius * np.array([np.cos(angle_b), np.sin(angle_b)])
        to_axis = np.linalg.norm(points - centre_b[None, :], axis=1)
        to_bowl = np.linalg.norm(points - bowl_centre[None, :], axis=1)

        # Positive means the point is clear of B: either outside B's shell, or
        # inside the void the bowl carved out of it.
        clearance = float(np.maximum(to_axis - radius, sphere_radius - to_bowl).min())
        if clearance < min_clearance:
            min_clearance = clearance
            tau_at_min = float(tau)
        dip = float((radius - to_axis).max())
        if dip > max_dip:
            max_dip = dip

    return NipResult(min_clearance, max_dip, tau_at_min)


def _min_point_distance(points_a: Any, points_b: Any) -> float:
    """Smallest distance between two point clouds."""
    import numpy as np

    # |a - b|^2 expands to |a|^2 + |b|^2 - 2 a.b, so one matrix product answers
    # the question that an n x m x 3 array of differences would - same result,
    # a fraction of the memory. Points here sit within a few mm of the nip, so
    # the subtraction stays well conditioned; clamp anyway in case a collision
    # drives the squared distance a hair below zero.
    squared_a = (points_a * points_a).sum(axis=1)
    squared_b = (points_b * points_b).sum(axis=1)
    squared_distance = squared_a[:, None] + squared_b[None, :] - 2.0 * (points_a @ points_b.T)
    return math.sqrt(max(0.0, float(np.min(squared_distance))))


def male_male_min_distance(
    profile_a: DotProfile,
    profile_b: DotProfile,
    gap: float,
    offset_arc: float = INTERPOINT_OFFSET_X_MM,
    offset_axial: float = INTERPOINT_OFFSET_Z_MM,
    radius: float = CYLINDER_RADIUS_MM,
    tau_limit: float = 0.30,
    tau_samples: int = 121,
    azimuths: int = 36,
    samples_per_segment: int = 24,
) -> float:
    """
    Closest approach between a raised dot on A and a raised dot on B.

    This is the interaction the interpoint offset exists to prevent: A's front
    dot and B's back dot arrive at the nip together, separated only by
    `offset_arc` around the cylinder and `offset_axial` along it. A distance of
    zero means the two dies would collide.

    Same rolling kinematics as `paired_nip_clearance`: A's dot passes the nip at
    -pi/2 + tau while B's passes at +pi/2 - tau, plus B's arc offset.

    `azimuths` and `samples_per_segment` set how finely each dot surface is
    sampled; the cost of a call grows with the square of their product, so keep
    them low when a profile has many segments.
    """
    import numpy as np

    tangential_a, axial_a, height_a = _profile_surface(profile_a, azimuths, samples_per_segment)
    tangential_b, axial_b, height_b = _profile_surface(profile_b, azimuths, samples_per_segment)
    centre_a = np.array([0.0, radius + gap / 2.0, 0.0])
    centre_b = np.array([0.0, -(radius + gap / 2.0), 0.0])
    axis = np.array([0.0, 0.0, 1.0])
    arc_angle = offset_arc / radius

    best = math.inf
    for tau in np.linspace(-tau_limit, tau_limit, tau_samples):
        angle_a = -np.pi / 2.0 + tau
        radial_a = np.array([np.cos(angle_a), np.sin(angle_a), 0.0])
        tangent_a = np.array([-np.sin(angle_a), np.cos(angle_a), 0.0])
        points_a = (
            centre_a[None, :]
            + (radius + height_a)[:, None] * radial_a[None, :]
            + tangential_a[:, None] * tangent_a[None, :]
            + axial_a[:, None] * axis[None, :]
        )

        angle_b = np.pi / 2.0 - tau + arc_angle
        radial_b = np.array([np.cos(angle_b), np.sin(angle_b), 0.0])
        tangent_b = np.array([-np.sin(angle_b), np.cos(angle_b), 0.0])
        points_b = (
            centre_b[None, :]
            + (radius + height_b)[:, None] * radial_b[None, :]
            + tangential_b[:, None] * tangent_b[None, :]
            + axial_b[:, None] * axis[None, :]
            + np.array([0.0, 0.0, offset_axial])[None, :]
        )

        distance = _min_point_distance(points_a, points_b)
        if distance < best:
            best = distance
    return best


def nip_clearances(
    profile: DotProfile = DS_DOT_PROFILE,
    bowl_diameter: float = DS_BOWL_DIAMETER_MM,
    bowl_depth: float = DS_BOWL_DEPTH_MM,
    gap: float = 0.35,
    radius: float = CYLINDER_RADIUS_MM,
    offset_arc: float = INTERPOINT_OFFSET_X_MM,
    offset_axial: float = INTERPOINT_OFFSET_Z_MM,
    tau_limit: float = 0.30,
    tau_samples: int = 121,
) -> dict[str, float]:
    """
    Every nip interaction at one cylinder gap, in one call.

    `gap` is the surface-to-surface distance between the two cylinders at the
    nip; the card travels through it. Reported distances are surface to surface,
    so a positive number is metal that never touches metal.

    The axis-aligned entry is a control: it is what the same two dots would do
    if the back grid were offset around the cylinder only, with no axial step.
    It comes out at zero — a collision — which is why the offset is diagonal.

    `tau_limit` and `tau_samples` set the roll swept for the two male-male
    passes. The paired pass keeps its own wider sweep, because the dot has to be
    followed all the way into the bowl and out again.
    """
    paired = paired_nip_clearance(profile, bowl_diameter, bowl_depth, gap, radius=radius)
    return {
        'gap_mm': gap,
        'paired_min_clearance_mm': paired.min_clearance_mm,
        'paired_max_dip_mm': paired.max_dip_mm,
        'paired_tau_at_min_rad': paired.tau_at_min_rad,
        'male_male_min_distance_mm': male_male_min_distance(
            profile, profile, gap, offset_arc, offset_axial, radius, tau_limit, tau_samples
        ),
        'male_male_axis_aligned_min_distance_mm': male_male_min_distance(
            profile, profile, gap, offset_arc, 0.0, radius, tau_limit, tau_samples
        ),
    }
