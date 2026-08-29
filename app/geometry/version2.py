"""
Embosser Version 2 (keyed gear pegs, PROTOTYPE) constants and profile math.

Version 2 is a different piece of hardware from the app's Version 1 embosser.
Its drive gears are separate prints again, and each of the four gears carries a
differently shaped peg that enters a matching keyed cutout in the end of a
cylinder, so a gear physically cannot be seated in the wrong place. This module
generates those cutouts; nothing gear-shaped is generated anywhere (D-V7).

Everything here is a pure function or a constant: no I/O, no globals mutated,
no settings objects. Lengths are millimetres, angles degrees. The frame is the
browser worker's: cylinder axis at x=y=0, barrel centred on z=0, angle 0 the
braille seam start and angle 180 the tactile row-arrow column - the direction
that faces the other cylinder.

Every Version 2 number lives here and nowhere else, the way app/geometry/
gears.py owns the gear constants: app/validation.py and app/geometry_spec.py
read this module rather than repeating a value, because cross-file default
drift is this project's most common historical bug.

Why the four keys are rectangles (family R14, signed 2026-08-28, decision
D-V9 / 02 Part 5). Two rules constrain any set of keys:

  * Phase safety. A gear can be pushed on in as many orientations as its key
    has symmetry, and the seated teeth must land on the same 15 degree tooth
    pitch every time, so 360/n must be a multiple of 15. That allows n in
    {1, 2, 3, 4, 6, 8, 12, 24} and rules out pentagons and heptagons.
  * Mutual exclusion. A wrong peg must stick out of a hole by more than the
    print clearance can erase.

No four regular polygons satisfy both - among the phase-safe orders none are
pairwise non-dividing, and two polygons of the same order simply nest by size.
The measured Version 7 sample set failed for exactly that reason: its hexagon
entered all four holes. Rectangles ordered by size are the way out. Each is
180 degree symmetric (12 teeth, phase-safe), each is blocked in either its
short or its long direction by every other hole at every rotation, and a
rectangle carries more torque across print layers than the hexagon it replaces
(torsion index J/r_max 647/640/618/574 against the hexagon's 457).

The Version 7 six-scallop star, hexagon and 15 x 15 squares are RETIRED. Their
measurements survive only in the research folder's 01_V7_SAMPLE_AUDIT.md, as
history. Brennen is re-cutting the gear pegs to match this table, so a number
changed here is a change to physical hardware - never adjust one to make a
test pass.
"""

from __future__ import annotations

import math

from app.geometry.gears import _format_mm

# The Version 2 barrel (D-V4). A SOFT preset: Brennen is "attempting the 30.1
# change ... updated if testing returns errors", so an off-size cylinder raises
# a warning and is still built (D-V15), unlike the gears' hard size gate.
V2_BARREL_DIAMETER_MM = 30.1
V2_BARREL_HEIGHT_MM = 52.0
# Float slack only, matching the gears' tolerance: at 32 mm a float32 ULP is
# 3.8e-6 mm, so 0.001 is far below any dimension a user can type.
V2_SIZE_TOLERANCE_MM = 0.001

# Print clearance per side (D-V3), an Expert-Mode dial. Every hole grows by
# this and the nub shrinks by it, so one number means one thing: how loose the
# keys are. The error-proofing margin shrinks by 2c, which is why the family
# was judged at the dial's maximum as well as its default.
V2_KEY_CLEARANCE_DEFAULT_MM = 0.15
V2_KEY_CLEARANCE_MIN_MM = 0.0
V2_KEY_CLEARANCE_MAX_MM = 0.5

# Each peg's root flares out 2.0 mm per side over its last 2.0 mm at 45
# degrees, so every cutout mouth needs the matching countersink or the gear
# stands 2 mm off the barrel. One rule at all four mouths (D-V16, simplified by
# the R14 family - the Version 7 star's separate scaled mouth retired with it).
V2_COUNTERSINK_OFFSET_MM = 2.0
V2_COUNTERSINK_DEPTH_MM = 2.0

# A sharp internal corner in a vertically printed barrel is the stress riser on
# the cylinder side, so the sockets are filleted and the pegs carry the same
# radius. The hole's corner radius comes out at V2_KEY_CORNER_RADIUS_MM plus
# the clearance - 0.65 at the default, the number the gear specification quotes
# - because grown_key_outline builds the exact parallel curve.
V2_KEY_CORNER_RADIUS_MM = 0.5

# Family R14. Length lies on the y axis (90/270 degrees) and width on the x
# axis (0/180), so every key presents a FLAT to the arrow column: on Cylinder
# A's top that flat is what gear A1's notch needs, and it keeps the mouth's
# flare clear of the nub base at every clearance setting.
V2_KEY_PROFILES = {
    'a1_square_14': {'length': 14.0, 'width': 14.0},
    'a2_rect_18x10': {'length': 18.0, 'width': 10.0},
    'b1_rect_16x12': {'length': 16.0, 'width': 12.0},
    'b2_rect_20x8': {'length': 20.0, 'width': 8.0},
}

# Which key each plate carries, as (bottom, top). Cylinder A is the embossing
# (positive) plate and Cylinder B the counter (negative) one, the same mapping
# the gears use. A's top is the handle end - it takes the square, the strongest
# member, and it is the only end with a nub.
KEY_PROFILES_BY_PLATE = {
    'positive': ('a2_rect_18x10', 'a1_square_14'),
    'negative': ('b2_rect_20x8', 'b1_rect_16x12'),
}

# The keys are generated already oriented, so nothing downstream rotates them.
# Recorded rather than implied: a future family whose profile is drawn on some
# other axis would set this instead of rotating at the call site.
KEY_ROTATION_DEG = 0.0

# The direction Cylinder A's arrows and its key nub both point - at Cylinder B.
V2_ARROW_COLUMN_DEG = 180.0

# The nub on Cylinder A's top face (D-V5), built 1:1 from Brennen's CAD: a
# triangle standing proud of the face, whose exact negative is the notch in gear
# A1's underside. It is what fixes A1's rotation, so the geometry is his, not
# ours - which is why it is very nearly, but not exactly, equilateral: these
# rounded CAD radii put the two flanks at 5.073086 against the 5.073158 base,
# 72 nanometres apart. Reproduced as measured rather than idealised.
V2_NUB = {
    'side': 5.073158,
    'base_radius': 9.754087,
    'apex_radius': 14.147487,
    'height': 3.0,
    'top_chamfer': 0.5,
    'base_flare': 0.5,
}

# Points per full circle for every arc, matching the tessellation the rest of
# the pipeline sends over the wire as polygon_points.
V2_ARC_SEGMENTS = 96

# Solids that share an exact face are non-manifold once float32 STL rounding
# gets to them, so cutters overlap the surfaces they cross by this much:
# "overlap, never touch".
V2_OVERLAP_MM = 0.01


def rounded_rectangle(
    length: float,
    width: float,
    corner_radius: float,
    segments: int = V2_ARC_SEGMENTS,
) -> list[tuple[float, float]]:
    """
    One key profile, centred on the axis: length on y, width on x, CCW.

    The four corner arcs are tessellated at `segments` points per full circle,
    so each 90 degree corner gets segments/4 intervals.
    """
    if length <= 0 or width <= 0:
        raise ValueError(f'rounded_rectangle needs positive sides, got length={length}, width={width}')
    if corner_radius < 0:
        raise ValueError(f'rounded_rectangle needs a non-negative corner radius, got {corner_radius}')
    half_length = length / 2.0
    half_width = width / 2.0
    if corner_radius > min(half_length, half_width):
        raise ValueError(
            f'corner radius {corner_radius} does not fit a {length} x {width} rectangle '
            f'(maximum {min(half_length, half_width)})'
        )
    if segments < 4:
        raise ValueError(f'rounded_rectangle needs at least 4 segments per circle, got {segments}')

    steps = max(1, round(segments / 4))
    cx = half_width - corner_radius
    cy = half_length - corner_radius

    points: list[tuple[float, float]] = []
    # Corner centres in CCW order, each arc sweeping 90 degrees from the +x
    # side round to the -y side.
    for centre_x, centre_y, start_deg in (
        (cx, cy, 0.0),
        (-cx, cy, 90.0),
        (-cx, -cy, 180.0),
        (cx, -cy, 270.0),
    ):
        for step in range(steps + 1):
            angle = math.radians(start_deg + 90.0 * step / steps)
            points.append((centre_x + corner_radius * math.cos(angle), centre_y + corner_radius * math.sin(angle)))
    return points


def offset_polygon_miter(points: list[tuple[float, float]], delta: float) -> list[tuple[float, float]]:
    """
    Grow a closed CCW polygon outward by `delta`, mitering every corner.

    A Python port of offsetPolygonMiter in static/workers/csg-worker-manifold.js
    so the server and the worker share one construction. Each vertex becomes the
    intersection of its two adjacent edges after both have been pushed along
    their outward normals; a negative delta shrinks, which is how the nub is
    inset by the clearance.

    This is exact for a shape whose edges are genuinely straight, like the nub
    triangle. It is NOT the tool for the keys: mitering a tessellated arc pushes
    each vertex out by delta/cos(pi/segments) rather than delta, so the rounded
    rectangles use grown_key_outline's exact parallel curve instead.
    """
    if not delta:
        return list(points)

    count = len(points)
    if count < 3:
        raise ValueError(f'offset_polygon_miter needs a polygon, got {count} points')

    edges = []
    for index in range(count):
        px, py = points[index]
        qx, qy = points[(index + 1) % count]
        dx = qx - px
        dy = qy - py
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError(f'offset_polygon_miter found a zero-length edge at index {index}')
        ex = dx / length
        ey = dy / length
        # (ey, -ex) is the outward normal of an edge on a counter-clockwise ring.
        edges.append((px + delta * ey, py - delta * ex, ex, ey))

    result: list[tuple[float, float]] = []
    for index in range(count):
        in_px, in_py, in_ex, in_ey = edges[(index - 1) % count]
        out_px, out_py, out_ex, out_ey = edges[index]
        denominator = in_ex * out_ey - in_ey * out_ex
        if abs(denominator) < 1e-9:
            # Collinear edges: the offset lines coincide, so either point will do.
            result.append((out_px, out_py))
            continue
        t = ((out_px - in_px) * out_ey - (out_py - in_py) * out_ex) / denominator
        result.append((in_px + t * in_ex, in_py + t * in_ey))
    return result


def nub_triangle(
    base_radius: float,
    apex_radius: float,
    half_width: float,
    angle_deg: float,
) -> list[tuple[float, float]]:
    """
    The key nub's outline, CCW: a triangle with its apex on `angle_deg`.

    The base sits at `base_radius` perpendicular to that direction and the apex
    reaches `apex_radius` along it.
    """
    if apex_radius <= base_radius:
        raise ValueError(f'nub apex radius {apex_radius} must be beyond its base radius {base_radius}')
    if half_width <= 0:
        raise ValueError(f'nub half-width must be positive, got {half_width}')
    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)
    # The base direction, 90 degrees round from the apex direction.
    vx, vy = -uy, ux
    return [
        (base_radius * ux - half_width * vx, base_radius * uy - half_width * vy),
        (apex_radius * ux, apex_radius * uy),
        (base_radius * ux + half_width * vx, base_radius * uy + half_width * vy),
    ]


def grown_key_outline(name: str, delta: float, segments: int = V2_ARC_SEGMENTS) -> list[tuple[float, float]]:
    """
    A key profile grown outward by `delta`, as an exact parallel curve.

    The parallel curve of a rounded rectangle is another rounded rectangle -
    both sides longer by 2*delta, the corner radius larger by delta - so it is
    built directly rather than by mitering the tessellation. Mitering would put
    each arc vertex out at delta/cos(pi/segments) instead of delta: 0.08 um too
    far at the default clearance, which no printer could resolve, but it would
    also mean the hole's corner radius was not the 0.65 mm the gear
    specification Brennen is cutting to says it is.
    """
    if name not in V2_KEY_PROFILES:
        raise ValueError(f'unknown Version 2 key profile {name!r}; known: {sorted(V2_KEY_PROFILES)}')
    profile = V2_KEY_PROFILES[name]
    return rounded_rectangle(
        profile['length'] + 2 * delta,
        profile['width'] + 2 * delta,
        V2_KEY_CORNER_RADIUS_MM + delta,
        segments,
    )


def key_profile(name: str, clearance: float, segments: int = V2_ARC_SEGMENTS) -> list[tuple[float, float]]:
    """One key's cutout outline: its peg profile grown by the print clearance."""
    validate_clearance(clearance)
    return grown_key_outline(name, clearance, segments)


def validate_clearance(clearance: float) -> float:
    """The clearance dial's range (D-V3), enforced wherever a clearance enters."""
    if not V2_KEY_CLEARANCE_MIN_MM <= clearance <= V2_KEY_CLEARANCE_MAX_MM:
        raise ValueError(
            f'Version 2 key clearance {clearance} mm is outside {V2_KEY_CLEARANCE_MIN_MM}-{V2_KEY_CLEARANCE_MAX_MM} mm'
        )
    return clearance


def _wire_points(points: list[tuple[float, float]]) -> list[dict]:
    """Polygon points in the shape the worker reads, rounded to micron-cubed."""
    return [{'x': round(x, 6), 'y': round(y, 6)} for x, y in points]


def nub_block(clearance: float) -> dict:
    """
    Cylinder A's key nub, inset by the clearance (D-V11).

    Gear A1's notch is a fixed negative in Brennen's gear, so shrinking the nub
    by the same c the holes grew by leaves c of clearance perpendicular to each
    of its faces. On an equilateral triangle that moves the base half-width in
    by sqrt(3) * c, not by c - the faces are what the notch touches.
    """
    validate_clearance(clearance)
    half_width = V2_NUB['side'] / 2.0
    outline = nub_triangle(V2_NUB['base_radius'], V2_NUB['apex_radius'], half_width, V2_ARROW_COLUMN_DEG)
    profile = offset_polygon_miter(outline, -clearance)
    return {
        'profile': _wire_points(profile),
        'top_chamfer': {
            'depth': V2_NUB['top_chamfer'],
            'profile': _wire_points(offset_polygon_miter(profile, -V2_NUB['top_chamfer'])),
        },
        'base_flare': {
            'depth': V2_NUB['base_flare'],
            'profile': _wire_points(offset_polygon_miter(profile, V2_NUB['base_flare'])),
        },
    }


def keyed_cutout_block(plate_type: str, height: float, clearance: float) -> dict:
    """
    Everything the worker needs to cut one cylinder's keyed through-hole.

    The two halves meet at the centre as a single through-hole (D-V2): the
    bottom key is extruded from the bottom face to the mid-plane and the top
    key from the mid-plane to the top face, each overlapping its face so no two
    solids share an exact plane. The nub rides on the positive plate only -
    Cylinder B has no nub, and guessing a side would silently print the wrong
    pair.
    """
    if plate_type not in KEY_PROFILES_BY_PLATE:
        raise ValueError(f'unknown plate type {plate_type!r}; known: {sorted(KEY_PROFILES_BY_PLATE)}')
    if height <= 0:
        raise ValueError(f'Version 2 cylinder height must be positive, got {height}')
    validate_clearance(clearance)

    bottom_name, top_name = KEY_PROFILES_BY_PLATE[plate_type]
    half_height = height / 2.0
    bottom_profile = key_profile(bottom_name, clearance)
    top_profile = key_profile(top_name, clearance)

    block = {
        'clearance_mm': clearance,
        'halves': [
            {
                'end': 'bottom',
                'profile': _wire_points(bottom_profile),
                'z_from': -half_height - V2_OVERLAP_MM,
                'z_to': V2_OVERLAP_MM,
            },
            {
                'end': 'top',
                'profile': _wire_points(top_profile),
                'z_from': -V2_OVERLAP_MM,
                'z_to': half_height + V2_OVERLAP_MM,
            },
        ],
        'countersinks': [
            {
                'end': 'bottom',
                'kind': 'hull',
                'face_profile': _wire_points(grown_key_outline(bottom_name, clearance + V2_COUNTERSINK_OFFSET_MM)),
                'inner_profile': _wire_points(bottom_profile),
                'depth': V2_COUNTERSINK_DEPTH_MM,
            },
            {
                'end': 'top',
                'kind': 'hull',
                'face_profile': _wire_points(grown_key_outline(top_name, clearance + V2_COUNTERSINK_OFFSET_MM)),
                'inner_profile': _wire_points(top_profile),
                'depth': V2_COUNTERSINK_DEPTH_MM,
            },
        ],
    }
    if plate_type == 'positive':
        nub = nub_block(clearance)
        nub['z_from'] = half_height - V2_OVERLAP_MM
        nub['z_to'] = half_height + V2_NUB['height']
        block['nub'] = nub
    return block


def matches_v2_barrel(diameter: float, height: float) -> bool:
    """True when this cylinder is the size the Version 2 embosser expects."""
    return (
        abs(diameter - V2_BARREL_DIAMETER_MM) <= V2_SIZE_TOLERANCE_MM
        and abs(height - V2_BARREL_HEIGHT_MM) <= V2_SIZE_TOLERANCE_MM
    )


def v2_size_message(diameter: float, height: float) -> str:
    """
    The S-V5 size note. SIGNED EXACTLY AS DRAFTED by Brennen on 2026-08-28 at
    the Phase 05 gate; a longer variant that also named the remedy was offered
    and declined, so the sentence stays terse and factual. Changing it now is a
    string decision, not a refactor.

    Rendered through the gears module's _format_mm so the number reads "52 mm",
    not "52.0 mm": the UI writes this same sentence, and two spellings of one
    message is how a user ends up believing there are two limits.
    """
    return (
        f'The Version 2 embosser expects a '
        f'{_format_mm(V2_BARREL_DIAMETER_MM)} mm x {_format_mm(V2_BARREL_HEIGHT_MM)} mm cylinder. '
        f'Received {_format_mm(diameter)} mm x {_format_mm(height)} mm.'
    )
