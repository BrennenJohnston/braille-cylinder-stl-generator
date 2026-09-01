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

# The Version 2 barrel (D-V4). A SOFT preset: an off-size cylinder raises a
# warning and is still built (D-V15), unlike the gears' hard size gate. That
# softness is the point - this number is still being found by printing.
#
# 30.8 since 2026-08-30 - Version 1's long-proven barrel, arrived at by walking
# back up. The prototype shipped at 30.1, which printed with noticeably too
# little embossing pressure; 30.5 (2026-08-29) was the deliberate half-way step
# so one variable moved by one known amount. Brennen ran a 30.5 double-sided
# pair and reported the SAME two symptoms, weaker: the pair felt loose and the
# dots came out shallow and uneven. Two points on the same line, so the search
# stops and the value goes to the size that has always worked.
#
# Both symptoms have the one cause - too little interference between the pair -
# and diameter is the only dial that sets it. Raising it also RELAXES the
# tightest wall in the design: Cylinder A's anti-rotation socket leaves
# 1.4025 mm at this barrel against 1.2525 at 30.5, over the 1.2 minimum either
# way. Nothing about the gear interface moves with it - every key and every
# anti-rotation feature is at a fixed radius from the axis.
#
# Height 54 since 2026-08-31 (was 52, the card's own height): 1 mm of extra
# barrel past EACH card edge, so a card rolled slightly off-axis rides the
# shelf instead of ruffling over the ends. The braille layout centres itself
# in the height, so no row moves; the keyed holes are radial and the nubs,
# sockets and chamfers all place from height/2, so every end feature simply
# follows the new faces. The shelf is VERSION 2's ALONE (Brennen, same day):
# the project-wide default barrel stays at the 52 mm Version 1 standard, and
# it is this preset - forced onto the dials whenever Version 2 is selected -
# that carries a V2 cylinder to 54.
V2_BARREL_DIAMETER_MM = 30.8
V2_BARREL_HEIGHT_MM = 54.0
# Float slack only, matching the gears' tolerance: at 32 mm a float32 ULP is
# 3.8e-6 mm, so 0.001 is far below any dimension a user can type.
V2_SIZE_TOLERANCE_MM = 0.001

# Print clearance per side (D-V3), an Expert-Mode dial. Every KEY HOLE grows
# by this: how loose the four keys are. The error-proofing margin shrinks with
# it, which is why the family is judged at the dial's maximum as well as its
# default.
#
# 0.110 since 2026-08-29, after two printed rounds bracketed it: all four peg
# holes were too loose at 0.15 and too tight at 0.075, so the value lands
# between them (D-R3-1). 0.110 and not the exact midpoint 0.1125, because the
# dial's step is 0.005 and a default that is not a whole number of steps above
# the minimum renders the input :invalid and disables Generate with no message
# anyone can see. 0.110 / 0.005 = 22.
#
# His gears measure exactly nominal - 14x14, 18x10, 16x12 and 20x8, corner
# radius 0.5 - so a hole is its peg plus 2c and the wrong-pair margin is
# 1.000 - c: 0.890 mm here, against 0.925 at 0.075 and 0.850 at 0.15
# (tests/test_version2_profiles.py::SMALLEST_WRONG_PAIR_PROTRUSION).
V2_KEY_CLEARANCE_DEFAULT_MM = 0.110
V2_KEY_CLEARANCE_MIN_MM = 0.0
V2_KEY_CLEARANCE_MAX_MM = 0.5

# Clearance per face on EVERY anti-rotation feature (D-R3-2): between a nub and
# its gear notch, and between a socket and its gear pin. A fixed constant with
# no dial, deliberately - it sets a fit against gears that are already cut, and
# putting a dial on it would spring the same trap D-V11 records just below.
V2_ANTIROT_CLEARANCE_MM = 0.15

# How far Brennen's gear CAD insets the triangle - the notch in A1, the pin on
# A2 - from the nominal V2_NUB outline below. MEASURED off the printed gears
# (01_GEAR_V71_AUDIT.md section 3), not chosen here: A1's notch comes out at
# base radius 9.9091 against this module's 9.904087, and that 5 um is the gear
# CAD's rounding, not a design difference.
V2_GEAR_TRIANGLE_INSET_MM = 0.15

# The nub does NOT follow the key-clearance dial, and has not since 2026-08-29.
# It used to be inset by the same c the holes grew by - one number, opposite
# directions - but gear A1 is already cut, so lowering the dial would have
# GROWN the nub into a notch that cannot be recut without reprinting the gear.
# The dial governs the four holes alone (D-V11).
#
# DERIVED, never retyped (D-R3-5). The notch is already inset from nominal by
# V2_GEAR_TRIANGLE_INSET_MM, so standing the nub off by one more
# V2_ANTIROT_CLEARANCE_MM is exactly what leaves 0.15 mm perpendicular to each
# of its faces. Until 2026-08-29 this was a hard 0.15 and the nub was
# line-to-line in the notch - 5 um of INTERFERENCE on the base face, and no
# print ever reported it. If a printed pair comes back rattling, the one-line
# reversal is to hard-code 0.15 again.
V2_NUB_CLEARANCE_MM = V2_GEAR_TRIANGLE_INSET_MM + V2_ANTIROT_CLEARANCE_MM

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
    # 0.10 since 2026-08-29 (D-R3-4), down from 0.5. Probing gear A1's notch by
    # containment on a 10 um grid showed its tangential half-width CONSTANT from
    # the mating face to full depth - no mouth relief at all - so a 0.5 flare
    # stood 0.49 mm proud per side at the face and A1 cannot have been seating
    # flush on either printed pair. Found by measurement, not reported. At 0.10
    # the flared nub still clears the notch wall by 0.05 mm on every face.
    'base_flare': 0.10,
}

# The four anti-rotation features as MEASURED on Brennen's v7.1 gears
# (01_GEAR_V71_AUDIT.md section 2), in the gear's own frame with +r along the
# arrow column. Top gears carry NOTCHES, bottom gears carry PINS, so the
# cylinder needs a nub at each top face and a socket in each bottom face.
#
# These are printed hardware and are not ours to adjust. The A triangle is NOT
# rebuilt from them - it derives from V2_NUB by an inset, so the shape has one
# source - but the fit tests measure against them.
#
# Measured off gear v7.2 (2026-08-30). Against v7.1 only the two NOTCH depths
# moved, 3.0 -> 3.15: the nub is 3.0 tall, so at 3.0 the notch had ZERO axial
# clearance while its three siblings each had 0.15, and which surface took the
# load was decided by print tolerance. Both PINS are still 3.0, and every
# radius and half-width below is unchanged from v7.1. Nothing reads 'depth' -
# it is recorded measurement, and the generator emits the same bytes either
# way - but a stale number here is how the next wrong derivation starts.
V2_GEAR_ANTIROT = {
    'a1_notch': {
        'gear': 'A1',
        'plate': 'positive',
        'end': 'top',
        'kind': 'notch',
        'shape': 'triangle',
        'inner_radius': 9.9091,
        'outer_radius': 13.8525,
        'half_width': 2.2768,
        'depth': 3.15,
    },
    'a2_pin': {
        'gear': 'A2',
        'plate': 'positive',
        'end': 'bottom',
        'kind': 'pin',
        'shape': 'triangle',
        'inner_radius': 9.9091,
        'outer_radius': 13.8525,
        'half_width': 2.2768,
        'depth': 3.0,
    },
    'b1_notch': {
        'gear': 'B1',
        'plate': 'negative',
        'end': 'top',
        'kind': 'notch',
        'shape': 'square',
        'inner_radius': 9.8000,
        'outer_radius': 13.1000,
        'half_width': 1.6500,
        'depth': 3.15,
    },
    'b2_pin': {
        'gear': 'B2',
        'plate': 'negative',
        'end': 'bottom',
        'kind': 'pin',
        'shape': 'square',
        'inner_radius': 10.0500,
        'outer_radius': 13.0500,
        'half_width': 1.5000,
        'depth': 3.0,
    },
}

# Which gear feature each plate's nub and socket mate with.
ANTIROT_BY_PLATE = {
    'positive': {'nub': 'a1_notch', 'socket': 'a2_pin'},
    'negative': {'nub': 'b1_notch', 'socket': 'b2_pin'},
}

# A socket must leave barrel wall behind it (D-R3-3). At the signed clearance
# the A socket's apex reaches r 13.997487 and the wall is 1.4025 mm, so this cap
# trims exactly 0.0000 mm today. It starts to bite above c = 0.1525 - a figure
# fixed by the pin, not by the barrel, so it did not move with it - and exists
# so the 1.2 mm FDM minimum survives anyone raising the clearance or switching
# a socket to a mitred offset. NOT dead code - a guard rail.
V2_SOCKET_MAX_RADIUS_MM = 14.0

# Socket depth: the gear pin's own 3.0 mm plus one clearance, so the pin cannot
# bottom out before the two faces meet. Derived, so it follows the clearance.
V2_SOCKET_DEPTH_MM = 3.0 + V2_ANTIROT_CLEARANCE_MM

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


def radial_rectangle(
    inner_radius: float,
    outer_radius: float,
    half_width: float,
    corner_radius: float,
    angle_deg: float = V2_ARROW_COLUMN_DEG,
    segments: int = V2_ARC_SEGMENTS,
) -> list[tuple[float, float]]:
    """
    A rectangle lying on `angle_deg`, CCW: radial span inner..outer, tangential
    half-width either side of that column.

    This is the B pair's square feature. rounded_rectangle cannot be reused: it
    centres its shape on the origin, and these sit out at r ~ 11.5 on the arrow
    column. A zero corner radius gives the four sharp corners gear B1's notch
    actually has.
    """
    if outer_radius <= inner_radius:
        raise ValueError(f'radial_rectangle needs outer_radius beyond inner_radius, got {inner_radius}..{outer_radius}')
    if half_width <= 0:
        raise ValueError(f'radial_rectangle needs a positive half-width, got {half_width}')
    if corner_radius < 0:
        raise ValueError(f'radial_rectangle needs a non-negative corner radius, got {corner_radius}')
    depth = outer_radius - inner_radius
    if corner_radius > min(depth / 2.0, half_width):
        raise ValueError(
            f'corner radius {corner_radius} does not fit a {depth} x {2 * half_width} feature '
            f'(maximum {min(depth / 2.0, half_width)})'
        )

    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux

    def place(radial: float, tangential: float) -> tuple[float, float]:
        return (radial * ux + tangential * vx, radial * uy + tangential * vy)

    if corner_radius == 0:
        # CCW in the world frame: (u, v) is right-handed, so walking the
        # rectangle in +radial then +tangential order winds counter-clockwise.
        corners = [
            (inner_radius, -half_width),
            (outer_radius, -half_width),
            (outer_radius, half_width),
            (inner_radius, half_width),
        ]
        return [place(r, t) for r, t in corners]

    steps = max(1, round(segments / 4))
    near = inner_radius + corner_radius
    far = outer_radius - corner_radius
    side = half_width - corner_radius
    points: list[tuple[float, float]] = []
    # Arc centres in the same CCW order, each sweeping 90 degrees. Angles are
    # measured in the (radial, tangential) plane, so 0 points outward.
    for centre_r, centre_t, start_deg in (
        (far, -side, -90.0),
        (far, side, 0.0),
        (near, side, 90.0),
        (near, -side, 180.0),
    ):
        for step in range(steps + 1):
            theta = math.radians(start_deg + 90.0 * step / steps)
            points.append(place(centre_r + corner_radius * math.cos(theta), centre_t + corner_radius * math.sin(theta)))
    return points


def parallel_curve(
    points: list[tuple[float, float]],
    delta: float,
    segments: int = V2_ARC_SEGMENTS,
) -> list[tuple[float, float]]:
    """
    Grow a closed CCW polygon outward by `delta` as an exact parallel curve.

    Every edge moves out along its normal by `delta` and every convex corner
    becomes an arc of radius `delta`, which is the Minkowski sum with a disc.
    That is what a SOCKET needs: a mitred corner would sit delta*sqrt(2) or more
    from the pin's corner instead of delta, and would put a sharp internal
    corner - the stress riser - in a vertically printed barrel.

    Neither existing offset can do this job. offset_polygon_miter is a mitre by
    construction, and grown_key_outline is hard-wired to the rounded-rectangle
    family (it rebuilds a rounded rectangle rather than offsetting any ring), so
    this is a third construction rather than a reuse.
    """
    if delta < 0:
        raise ValueError(f'parallel_curve grows outward; got delta={delta}')
    if not delta:
        return list(points)
    count = len(points)
    if count < 3:
        raise ValueError(f'parallel_curve needs a polygon, got {count} points')
    if segments < 4:
        raise ValueError(f'parallel_curve needs at least 4 segments per circle, got {segments}')

    normals = []
    for index in range(count):
        px, py = points[index]
        qx, qy = points[(index + 1) % count]
        dx, dy = qx - px, qy - py
        length = math.hypot(dx, dy)
        if length == 0:
            raise ValueError(f'parallel_curve found a zero-length edge at index {index}')
        # (ey, -ex) is the outward normal of an edge on a counter-clockwise ring.
        normals.append((dy / length, -dx / length))

    result: list[tuple[float, float]] = []
    for index in range(count):
        px, py = points[index]
        in_nx, in_ny = normals[(index - 1) % count]
        out_nx, out_ny = normals[index]
        cross = in_nx * out_ny - in_ny * out_nx
        start = math.atan2(in_ny, in_nx)
        # One signed angle, never a difference of two atan2 calls: a collinear
        # vertex whose cross product is a hair negative would otherwise wrap a
        # near-zero sweep round to a full circle.
        sweep = math.atan2(cross, in_nx * out_nx + in_ny * out_ny)
        if cross < -1e-12:
            # A reflex corner has no arc: the two offset edges still meet at the
            # mitre point, so fall back to that single vertex.
            result.append(
                (
                    px + (in_nx + out_nx) / (1 + in_nx * out_nx + in_ny * out_ny) * delta,
                    py + (in_ny + out_ny) / (1 + in_nx * out_nx + in_ny * out_ny) * delta,
                )
            )
            continue
        arc_steps = max(1, math.ceil(abs(sweep) / (2 * math.pi) * segments))
        for step in range(arc_steps + 1):
            theta = start + sweep * step / arc_steps
            result.append((px + delta * math.cos(theta), py + delta * math.sin(theta)))
    return result


def clip_to_max_radius(
    points: list[tuple[float, float]],
    max_radius: float,
    angle_deg: float = V2_ARROW_COLUMN_DEG,
) -> list[tuple[float, float]]:
    """
    Truncate a CCW polygon at `max_radius` measured along `angle_deg`.

    One Sutherland-Hodgman half-plane clip, so a shape already inside is
    returned with its vertices unmoved. This is D-R3-3's guard rail on the
    socket depth into the barrel wall.
    """
    if max_radius <= 0:
        raise ValueError(f'clip_to_max_radius needs a positive radius, got {max_radius}')
    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)

    def reach(point: tuple[float, float]) -> float:
        return point[0] * ux + point[1] * uy

    count = len(points)
    if count < 3:
        raise ValueError(f'clip_to_max_radius needs a polygon, got {count} points')
    if all(reach(point) <= max_radius for point in points):
        return list(points)

    clipped: list[tuple[float, float]] = []
    for index in range(count):
        current = points[index]
        following = points[(index + 1) % count]
        d_current = reach(current) - max_radius
        d_next = reach(following) - max_radius
        if d_current <= 0:
            clipped.append(current)
        if (d_current > 0) != (d_next > 0):
            t = d_current / (d_current - d_next)
            clipped.append((current[0] + t * (following[0] - current[0]), current[1] + t * (following[1] - current[1])))
    return clipped


def antirot_nub_profile(plate_type: str) -> list[tuple[float, float]]:
    """
    The anti-rotation NUB standing proud of this plate's TOP face, CCW.

    Cylinder A's is the V2_NUB triangle inset by V2_NUB_CLEARANCE_MM - one
    source for that shape, never rebuilt from the gear measurements. Cylinder
    B's is gear B1's square notch shrunk by one clearance on every face, sharp
    cornered because the notch is.
    """
    if plate_type not in ANTIROT_BY_PLATE:
        raise ValueError(f'unknown plate type {plate_type!r}; known: {sorted(ANTIROT_BY_PLATE)}')
    clearance = V2_ANTIROT_CLEARANCE_MM
    if plate_type == 'positive':
        outline = nub_triangle(V2_NUB['base_radius'], V2_NUB['apex_radius'], V2_NUB['side'] / 2.0, V2_ARROW_COLUMN_DEG)
        return offset_polygon_miter(outline, -V2_NUB_CLEARANCE_MM)
    notch = V2_GEAR_ANTIROT[ANTIROT_BY_PLATE[plate_type]['nub']]
    return radial_rectangle(
        notch['inner_radius'] + clearance,
        notch['outer_radius'] - clearance,
        notch['half_width'] - clearance,
        0.0,
    )


def antirot_socket_profile(plate_type: str) -> list[tuple[float, float]]:
    """
    The anti-rotation SOCKET sunk into this plate's BOTTOM face, CCW.

    Both are the gear pin's exact parallel curve at V2_ANTIROT_CLEARANCE_MM, so
    every face clears by that much and every internal corner carries an arc of
    the same radius. Cylinder A's is then truncated at V2_SOCKET_MAX_RADIUS_MM.
    """
    if plate_type not in ANTIROT_BY_PLATE:
        raise ValueError(f'unknown plate type {plate_type!r}; known: {sorted(ANTIROT_BY_PLATE)}')
    clearance = V2_ANTIROT_CLEARANCE_MM
    if plate_type == 'positive':
        # The pin is the nominal triangle at the inset the gear was cut with -
        # the same outline nub_block emitted before D-R3-5 moved the nub.
        pin = offset_polygon_miter(
            nub_triangle(V2_NUB['base_radius'], V2_NUB['apex_radius'], V2_NUB['side'] / 2.0, V2_ARROW_COLUMN_DEG),
            -V2_GEAR_TRIANGLE_INSET_MM,
        )
        return clip_to_max_radius(parallel_curve(pin, clearance), V2_SOCKET_MAX_RADIUS_MM)
    pin = V2_GEAR_ANTIROT[ANTIROT_BY_PLATE[plate_type]['socket']]
    return radial_rectangle(
        pin['inner_radius'] - clearance,
        pin['outer_radius'] + clearance,
        pin['half_width'] + clearance,
        clearance,
    )


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


def nub_block(plate_type: str) -> dict:
    """
    One plate's anti-rotation nub, standing proud of its TOP face.

    Both cylinders carry one since 2026-08-29: Cylinder A's is the triangle that
    mates with gear A1's notch, Cylinder B's the square that mates with B1's.
    Each is inset from its gear's notch by V2_ANTIROT_CLEARANCE_MM measured
    PERPENDICULAR to every face, which on the triangle moves the base half-width
    in by sqrt(3) * c rather than by c - the faces are what the notch touches.

    It takes a plate selector, and never a CLEARANCE. That is the thing D-V11
    forbids: the key-clearance dial used to reach this function, and re-coupling
    them would drive the nub into an already-printed notch the moment someone
    tightened the holes. A plate selector carries no clearance, so it is safe;
    an argument named clearance, or any argument the dial can reach, is not.
    """
    profile = antirot_nub_profile(plate_type)
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


def socket_block(plate_type: str, height: float) -> dict:
    """
    One plate's anti-rotation socket, sunk into its BOTTOM face.

    A plain prism - no chamfer, no flare, one profile - because the gear pin
    carries its own 0.5 mm lead-in and needs no mouth relief from us. It is cut
    V2_SOCKET_DEPTH_MM deep, one clearance more than the pin is tall, so the pin
    cannot bottom out before the two faces meet, and it overlaps the bottom face
    by V2_OVERLAP_MM so no two solids share an exact plane.
    """
    if height <= 0:
        raise ValueError(f'Version 2 cylinder height must be positive, got {height}')
    half_height = height / 2.0
    return {
        'profile': _wire_points(antirot_socket_profile(plate_type)),
        'z_from': -half_height - V2_OVERLAP_MM,
        'z_to': -half_height + V2_SOCKET_DEPTH_MM,
    }


def keyed_cutout_block(plate_type: str, height: float, clearance: float) -> dict:
    """
    Everything the worker needs to cut one cylinder's keyed through-hole.

    The two halves meet at the centre as a single through-hole (D-V2): the
    bottom key is extruded from the bottom face to the mid-plane and the top
    key from the mid-plane to the top face, each overlapping its face so no two
    solids share an exact plane.

    BOTH plates carry a nub and a socket since 2026-08-29. The nub was positive
    plate only while gear A1 was the only gear with a notch; every gear has an
    anti-rotation feature now, so that invariant is retired. The two plates'
    features are still different shapes, and the plate selector is what picks
    them - guessing a side would silently print the wrong pair.
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
    nub = nub_block(plate_type)
    nub['z_from'] = half_height - V2_OVERLAP_MM
    nub['z_to'] = half_height + V2_NUB['height']
    block['nub'] = nub
    block['socket'] = socket_block(plate_type, height)
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
