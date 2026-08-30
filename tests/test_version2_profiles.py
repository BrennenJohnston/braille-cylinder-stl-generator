"""
Profile math for the Embosser Version 2 keyed cutouts (family R14).

These checks are ANALYTIC. The four peg DXFs in the research folder describe
the Version 7 pegs, which the R14 signature (2026-08-28) retired, so there is
no sample file to measure against until Brennen re-exports the new gears; the
numbers below are the exact geometry the generator and his CAD now share.

The test that matters most is test_fit_matrix_is_the_identity: R14 exists to
make it physically impossible to seat a gear in the wrong end, and that
property has to survive the clearance dial's whole range.

All lengths are millimetres, all angles degrees.
"""

import math

import pytest

from app.geometry import version2 as v2

CLEARANCES = (0.0, 0.075, 0.110, 0.15, 0.30, 0.50)

# audit_fit_matrix.py, family R14: the smallest distance any wrong peg sticks
# out of a hole, per side, at each clearance.
SMALLEST_WRONG_PAIR_PROTRUSION = {
    0.0: 1.000,
    0.075: 0.925,
    0.110: 0.890,
    0.15: 0.850,
    0.30: 0.700,
    0.50: 0.500,
}


def _signed_area(points):
    """Shoelace area; positive means counter-clockwise."""
    total = 0.0
    for index, (x, y) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        total += x * next_y - next_x * y
    return total / 2.0


def _inradius(points):
    """Area over semi-perimeter - exact for any triangle, equilateral or not."""
    perimeter = sum(math.dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))
    return 2 * _signed_area(points) / perimeter


def _extents(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return max(xs) - min(xs), max(ys) - min(ys)


def _rotate(points, degrees):
    angle = math.radians(degrees)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in points]


def _peg_outline(name):
    """The peg itself - the hole is this grown by the clearance."""
    profile = v2.V2_KEY_PROFILES[name]
    return v2.rounded_rectangle(profile['length'], profile['width'], v2.V2_KEY_CORNER_RADIUS_MM)


# Half-degree steps over a quarter turn. Every profile is 180 degree
# symmetric, and swapping the axes covers the other quadrant, so this reaches
# every distinct pose; the dips are tens of degrees wide, far broader than the
# step.
_ROTATIONS = [step * 0.5 for step in range(181)]


def _protrusion(peg_name, hole_name, clearance, degrees):
    """How far the peg sticks out of the hole, per side, at one rotation."""
    hole_x, hole_y = _extents(v2.key_profile(hole_name, clearance))
    peg_x, peg_y = _extents(_rotate(_peg_outline(peg_name), degrees))
    return max(0.0, (peg_x - hole_x) / 2.0, (peg_y - hole_y) / 2.0)


def _best_protrusion(peg_name, hole_name, clearance):
    """
    The peg's best case: the least it sticks out at any rotation.

    Rotating does not always hurt. A 20 x 8 peg held against a 14.3 square hole
    is 2.85 out when square to it and only 2.54 at its best angle, because
    turning trades the long axis against the short one. Error-proofing has to
    hold at that best angle, not at the tidy one.
    """
    return min(_protrusion(peg_name, hole_name, clearance, degrees) for degrees in _ROTATIONS)


def test_every_profile_is_ccw_and_closed():
    for name in v2.V2_KEY_PROFILES:
        points = _peg_outline(name)
        assert _signed_area(points) > 0, f'{name} is not counter-clockwise'
        assert len(points) == 100, f'{name} has {len(points)} points, expected 4 arcs of 25'


@pytest.mark.parametrize('name', sorted(v2.V2_KEY_PROFILES))
def test_profile_area_and_extents_are_exact(name):
    profile = v2.V2_KEY_PROFILES[name]
    length, width = profile['length'], profile['width']
    radius = v2.V2_KEY_CORNER_RADIUS_MM
    points = _peg_outline(name)

    expected_area = length * width - radius**2 * (4 - math.pi)
    assert _signed_area(points) == pytest.approx(expected_area, abs=0.05)

    x_extent, y_extent = _extents(points)
    assert x_extent == pytest.approx(width, abs=1e-9)
    assert y_extent == pytest.approx(length, abs=1e-9)


@pytest.mark.parametrize('name', sorted(v2.V2_KEY_PROFILES))
def test_a_flat_faces_the_arrow_column(name):
    """
    The 180 degree direction must meet a flat, not a corner.

    On Cylinder A's top that flat is what gear A1's notch keys against, and it
    is what keeps the mouth's flare clear of the nub base.
    """
    width = v2.V2_KEY_PROFILES[name]['width']
    points = _peg_outline(name)
    flats = [
        (p, q)
        for p, q in zip(points, points[1:] + points[:1])
        if p[0] == pytest.approx(-width / 2.0, abs=1e-9)
        and q[0] == pytest.approx(-width / 2.0, abs=1e-9)
        and p[1] > 0 > q[1]
    ]
    assert len(flats) == 1, f'{name} does not present one flat edge across the 180 degree ray'


@pytest.mark.parametrize('name', sorted(v2.V2_KEY_PROFILES))
def test_every_key_is_phase_safe(name):
    """
    A gear seated either way round must leave its teeth on the 15 degree pitch.

    Every R14 key is 180 degree symmetric (12 teeth); the square is 90 degree
    symmetric (6 teeth) as well. Both are multiples of the tooth pitch.
    """
    points = _peg_outline(name)
    originals = sorted((round(x, 9), round(y, 9)) for x, y in points)

    rotated = sorted((round(x, 9), round(y, 9)) for x, y in _rotate(points, 180.0))
    for (ox, oy), (rx, ry) in zip(originals, rotated):
        assert ox == pytest.approx(rx, abs=1e-9) and oy == pytest.approx(ry, abs=1e-9)

    profile = v2.V2_KEY_PROFILES[name]
    if profile['length'] == profile['width']:
        quarter = sorted((round(x, 9), round(y, 9)) for x, y in _rotate(points, 90.0))
        for (ox, oy), (rx, ry) in zip(originals, quarter):
            assert ox == pytest.approx(rx, abs=1e-9) and oy == pytest.approx(ry, abs=1e-9)


@pytest.mark.parametrize('clearance', CLEARANCES)
@pytest.mark.parametrize('name', sorted(v2.V2_KEY_PROFILES))
def test_clearance_grows_every_apothem_by_exactly_c(name, clearance):
    peg_x, peg_y = _extents(_peg_outline(name))
    hole_x, hole_y = _extents(v2.key_profile(name, clearance))
    assert hole_x - peg_x == pytest.approx(2 * clearance, abs=1e-9)
    assert hole_y - peg_y == pytest.approx(2 * clearance, abs=1e-9)


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_corner_radius_grows_with_the_clearance(clearance):
    """
    The hole's corner is the peg's corner plus the clearance, exactly.

    Mitering the tessellation instead would put each arc vertex out at
    c/cos(pi/96) - only 0.08 um wide at the default, but it would stop the
    corner being the 0.65 mm the gear specification quotes.
    """
    name = 'b2_rect_20x8'
    profile = v2.V2_KEY_PROFILES[name]
    radius = v2.V2_KEY_CORNER_RADIUS_MM
    centre = (profile['width'] / 2.0 - radius, profile['length'] / 2.0 - radius)

    for points, expected in ((_peg_outline(name), radius), (v2.key_profile(name, clearance), radius + clearance)):
        corner = [p for p in points if p[0] >= centre[0] - 1e-9 and p[1] >= centre[1] - 1e-9]
        assert len(corner) == 25
        for x, y in corner:
            assert math.hypot(x - centre[0], y - centre[1]) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_fit_matrix_is_the_identity(clearance):
    """
    The whole point of family R14: every peg enters its own hole and no other.

    Measured at each peg's BEST rotation, because a user can twist a gear, and
    the margin has to survive the clearance dial's maximum as well as its
    default.
    """
    names = sorted(v2.V2_KEY_PROFILES)
    wrong_pairs = []
    for peg in names:
        for hole in names:
            protrusion = _best_protrusion(peg, hole, clearance)
            if peg == hole:
                assert protrusion == 0.0, f'{peg} does not fit its own hole at c={clearance}'
            else:
                assert protrusion > 0.0, f'{peg} enters the {hole} hole at c={clearance}'
                wrong_pairs.append(protrusion)

    assert min(wrong_pairs) == pytest.approx(SMALLEST_WRONG_PAIR_PROTRUSION[clearance], abs=0.001)


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_the_a_top_mouth_clears_the_nub(clearance):
    """
    Cylinder A's top mouth flares 2 mm outward; the nub starts at r 9.754087.

    If the flare reached the nub it would undercut the base of the feature that
    takes the handle's torque.
    """
    half_width = v2.V2_KEY_PROFILES['a1_square_14']['width'] / 2.0
    mouth_radius = half_width + clearance + v2.V2_COUNTERSINK_OFFSET_MM
    assert mouth_radius < v2.V2_NUB['base_radius'], f'the mouth reaches the nub base at c={clearance}'


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_the_nub_inset_is_fixed_and_the_dial_cannot_reach_it(clearance):
    """
    D-V11 as revised 2026-08-29: the nub is inset by V2_NUB_CLEARANCE_MM, and
    the key-clearance dial does NOT move it.

    Gear A1's notch is a fixed negative that is already cut - it measures
    3.943 x 4.553 mm off the printed gear, which is the nub at exactly
    c = 0.15 - so tightening the holes must not grow the nub into it. The old
    behaviour, where the nub followed the dial, would have done exactly that.

    The inradius is what moves by exactly c. The base gets narrower by about
    sqrt(3) * c - roughly 1.73 times as much - so "inset by c" is a statement
    about the faces, never about the width.
    """
    fixed = v2.V2_NUB_CLEARANCE_MM
    half_width = v2.V2_NUB['side'] / 2.0
    outline = v2.nub_triangle(v2.V2_NUB['base_radius'], v2.V2_NUB['apex_radius'], half_width, v2.V2_ARROW_COLUMN_DEG)
    inset = v2.offset_polygon_miter(outline, -fixed)

    assert _signed_area(outline) > 0
    assert _inradius(outline) - _inradius(inset) == pytest.approx(fixed, abs=1e-9)

    base_shrink = (math.dist(outline[0], outline[2]) - math.dist(inset[0], inset[2])) / 2.0
    assert base_shrink / fixed == pytest.approx(math.sqrt(3), abs=0.001)

    # The dial is swept by the parametrize above; the emitted nub never moves.
    block = v2.keyed_cutout_block('positive', 52.0, clearance)
    emitted = [(point['x'], point['y']) for point in block['nub']['profile']]
    assert emitted == [(round(x, 6), round(y, 6)) for x, y in inset]


def test_the_nub_points_at_the_arrow_column():
    half_width = v2.V2_NUB['side'] / 2.0
    outline = v2.nub_triangle(v2.V2_NUB['base_radius'], v2.V2_NUB['apex_radius'], half_width, v2.V2_ARROW_COLUMN_DEG)
    apex = max(outline, key=lambda p: math.hypot(*p))
    assert math.hypot(*apex) == pytest.approx(v2.V2_NUB['apex_radius'], abs=1e-9)
    assert math.degrees(math.atan2(apex[1], apex[0])) % 360 == pytest.approx(v2.V2_ARROW_COLUMN_DEG, abs=1e-9)


@pytest.mark.parametrize('plate_type', ('positive', 'negative'))
def test_block_matches_the_wire_contract(plate_type):
    block = v2.keyed_cutout_block(plate_type, 52.0, 0.075)
    assert set(block) == {'clearance_mm', 'halves', 'countersinks', 'nub', 'socket'}
    assert block['clearance_mm'] == 0.075

    assert [half['end'] for half in block['halves']] == ['bottom', 'top']
    for half in block['halves']:
        assert set(half) == {'end', 'profile', 'z_from', 'z_to'}
        assert all(set(point) == {'x', 'y'} for point in half['profile'])
    assert block['halves'][0]['z_from'] == pytest.approx(-26.01)
    assert block['halves'][0]['z_to'] == pytest.approx(0.01)
    assert block['halves'][1]['z_from'] == pytest.approx(-0.01)
    assert block['halves'][1]['z_to'] == pytest.approx(26.01)

    assert [sink['end'] for sink in block['countersinks']] == ['bottom', 'top']
    for sink in block['countersinks']:
        assert set(sink) == {'end', 'kind', 'face_profile', 'inner_profile', 'depth'}
        assert sink['kind'] == 'hull', 'the R14 family left one countersink rule; no scaled mouth survives'
        assert sink['depth'] == v2.V2_COUNTERSINK_DEPTH_MM

    # The overlap sits on the FACE side of each feature only: a nub overlaps
    # into the barrel and stops flush at its free top, a socket overlaps out
    # through the bottom face and stops at its blind floor. An overlap at the
    # far end would either bury the nub's chamfer or punch the socket through.
    nub = block['nub']
    assert set(nub) == {'profile', 'top_chamfer', 'base_flare', 'z_from', 'z_to'}
    assert nub['z_from'] == pytest.approx(26.0 - v2.V2_OVERLAP_MM)
    assert nub['z_to'] == pytest.approx(26.0 + v2.V2_NUB['height'])
    assert set(nub['top_chamfer']) == {'depth', 'profile'}
    assert nub['base_flare']['depth'] == pytest.approx(v2.V2_NUB['base_flare'])

    socket = block['socket']
    assert set(socket) == {'profile', 'z_from', 'z_to'}, 'a socket is a plain prism: no chamfer, no flare'
    assert socket['z_from'] == pytest.approx(-26.0 - v2.V2_OVERLAP_MM)
    assert socket['z_to'] == pytest.approx(-26.0 + v2.V2_SOCKET_DEPTH_MM)
    assert all(set(point) == {'x', 'y'} for point in socket['profile'])


def test_each_plate_carries_its_own_pair_of_keys():
    positive = v2.keyed_cutout_block('positive', 52.0, 0.075)
    negative = v2.keyed_cutout_block('negative', 52.0, 0.075)

    # Both plates carry a nub and a socket, and the two plates' shapes differ -
    # a triangle on A, a square on B. Emitting the same shape for both would
    # silently print a pair that cannot tell its own ends apart.
    for feature in ('nub', 'socket'):
        assert feature in positive and feature in negative
        assert positive[feature]['profile'] != negative[feature]['profile']
    for block, (bottom_name, top_name) in (
        (positive, v2.KEY_PROFILES_BY_PLATE['positive']),
        (negative, v2.KEY_PROFILES_BY_PLATE['negative']),
    ):
        for half, name in zip(block['halves'], (bottom_name, top_name)):
            expected = v2.key_profile(name, 0.075)
            assert len(half['profile']) == len(expected)
            assert half['profile'][0]['x'] == pytest.approx(expected[0][0], abs=1e-6)


def test_the_block_scales_with_the_cylinder_height():
    block = v2.keyed_cutout_block('positive', 40.0, 0.075)
    assert block['halves'][0]['z_from'] == pytest.approx(-20.01)
    assert block['halves'][1]['z_to'] == pytest.approx(20.01)
    assert block['nub']['z_from'] == pytest.approx(19.99)
    assert block['nub']['z_to'] == pytest.approx(20.0 + v2.V2_NUB['height'])
    assert block['socket']['z_from'] == pytest.approx(-20.01)
    assert block['socket']['z_to'] == pytest.approx(-20.0 + v2.V2_SOCKET_DEPTH_MM)


@pytest.mark.parametrize(
    'call',
    (
        lambda: v2.keyed_cutout_block('cylinder', 52.0, 0.075),
        lambda: v2.keyed_cutout_block('', 52.0, 0.075),
        lambda: v2.keyed_cutout_block('positive', 0.0, 0.075),
        lambda: v2.keyed_cutout_block('positive', 52.0, 0.75),
        lambda: v2.keyed_cutout_block('positive', 52.0, -0.1),
        lambda: v2.key_profile('a1_star', 0.075),
        lambda: v2.rounded_rectangle(14.0, 14.0, 8.0),
        lambda: v2.rounded_rectangle(0.0, 14.0, 0.5),
    ),
)
def test_bad_input_raises_rather_than_guessing(call):
    with pytest.raises(ValueError):
        call()


def test_size_check_and_message():
    assert v2.matches_v2_barrel(30.5, 52.0)
    assert v2.matches_v2_barrel(30.5005, 52.0)
    assert not v2.matches_v2_barrel(30.8, 52.0)
    assert not v2.matches_v2_barrel(30.5, 51.0)

    message = v2.v2_size_message(30.8, 52.0)
    assert message == ('The Version 2 embosser expects a 30.5 mm x 52 mm cylinder. Received 30.8 mm x 52 mm.')
    assert '52.0 mm' not in message


# --- Anti-rotation features (D-R3-2 .. D-R3-5) -------------------------------
#
# Every gear now carries an anti-rotation feature, so the cylinder needs a nub
# at each TOP face and a socket in each BOTTOM face. The targets below are the
# signed table in 03_IMPLEMENTATION_PLAN_R3.md; the module derives all four from
# V2_NUB or from a MEASURED gear feature, so nothing here is a second copy of a
# number the module owns - it is the expected RESULT of those derivations.
#
# (inner radius, outer radius, half-width, area), all on the arrow column.
ANTIROT_TARGETS = {
    ('positive', 'nub'): (10.054087, 13.547487, 2.016964, 7.0461),
    ('positive', 'socket'): (9.754087, 13.997487, 2.426771, 11.0980),
    ('negative', 'nub'): (9.9500, 12.9500, 1.5000, 9.0000),
    ('negative', 'socket'): (9.9000, 13.2000, 1.6500, 10.8707),
}

# Gear A1's notch is cut 5 um wide of our nominal - CAD rounding, recorded in
# 01_GEAR_V71_AUDIT.md section 3, not a design difference. Fit assertions carry
# it rather than pretending the two agree exactly.
GEAR_CAD_ROUNDING_MM = 0.006


def _radial_extent(points):
    """(inner radius, outer radius, half-width) measured on the arrow column."""
    angle = math.radians(v2.V2_ARROW_COLUMN_DEG)
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    radial = [x * ux + y * uy for x, y in points]
    tangential = [x * vx + y * vy for x, y in points]
    return min(radial), max(radial), max(abs(t) for t in tangential)


def _antirot_profile(plate_type, which):
    if which == 'nub':
        return v2.antirot_nub_profile(plate_type)
    return v2.antirot_socket_profile(plate_type)


def _gear_pin_polygon(plate_type):
    """The gear pin this plate's socket must swallow, as a polygon."""
    if plate_type == 'positive':
        return v2.offset_polygon_miter(
            v2.nub_triangle(
                v2.V2_NUB['base_radius'],
                v2.V2_NUB['apex_radius'],
                v2.V2_NUB['side'] / 2.0,
                v2.V2_ARROW_COLUMN_DEG,
            ),
            -v2.V2_GEAR_TRIANGLE_INSET_MM,
        )
    pin = v2.V2_GEAR_ANTIROT[v2.ANTIROT_BY_PLATE[plate_type]['socket']]
    return v2.radial_rectangle(pin['inner_radius'], pin['outer_radius'], pin['half_width'], 0.0)


def _perimeter(points):
    return sum(math.dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))


@pytest.mark.parametrize(('plate_type', 'which'), sorted(ANTIROT_TARGETS))
def test_antirot_profiles_match_the_signed_table(plate_type, which):
    inner, outer, half_width, area = ANTIROT_TARGETS[(plate_type, which)]
    points = _antirot_profile(plate_type, which)
    measured_inner, measured_outer, measured_half = _radial_extent(points)
    assert measured_inner == pytest.approx(inner, abs=0.001)
    assert measured_outer == pytest.approx(outer, abs=0.001)
    assert measured_half == pytest.approx(half_width, abs=0.001)
    assert _signed_area(points) == pytest.approx(area, abs=0.01)
    # CCW, like every other profile this module emits: the worker extrudes them
    # without checking, so a reversed ring would come out inside-out.
    assert _signed_area(points) > 0


def test_the_derived_clearances_cannot_drift():
    """D-R3-5: the nub stand-off is computed from its two parts, never retyped."""
    assert v2.V2_NUB_CLEARANCE_MM == pytest.approx(v2.V2_GEAR_TRIANGLE_INSET_MM + v2.V2_ANTIROT_CLEARANCE_MM)
    assert v2.V2_SOCKET_DEPTH_MM == pytest.approx(3.0 + v2.V2_ANTIROT_CLEARANCE_MM)
    assert v2.V2_NUB['base_flare'] < v2.V2_ANTIROT_CLEARANCE_MM


def test_the_a_nub_sits_in_gear_a1s_notch_with_the_signed_clearance():
    """
    Fit (a): 0.15 mm perpendicular to every face of a notch already printed.

    The base face is perpendicular to the arrow column, so its gap is radial.
    The two flanks stand at 60 degrees to that column, so a tangential
    half-width difference of d is a perpendicular gap of d / sqrt(3).
    """
    notch = v2.V2_GEAR_ANTIROT['a1_notch']
    inner, outer, half_width = _radial_extent(v2.antirot_nub_profile('positive'))
    assert inner - notch['inner_radius'] == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=GEAR_CAD_ROUNDING_MM)
    assert (notch['half_width'] - half_width) / math.sqrt(3.0) == pytest.approx(
        v2.V2_ANTIROT_CLEARANCE_MM, abs=GEAR_CAD_ROUNDING_MM
    )
    assert outer < notch['outer_radius']


def test_the_b_nub_sits_in_gear_b1s_notch_with_the_signed_clearance():
    """Fit (a) for the square: every face is square-on, so every gap is direct."""
    notch = v2.V2_GEAR_ANTIROT['b1_notch']
    inner, outer, half_width = _radial_extent(v2.antirot_nub_profile('negative'))
    assert inner - notch['inner_radius'] == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=0.001)
    assert notch['outer_radius'] - outer == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=0.001)
    assert notch['half_width'] - half_width == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=0.001)


def test_the_flared_nub_still_enters_the_notch():
    """
    Fit (b), and the defect D-R3-4 exists to fix.

    Neither notch has a mouth relief - probing containment on a 10 um grid gave
    a half-width constant from the mating face to full depth - so the base flare
    has to fit inside the SAME opening as the nub body. At 0.5 it did not, by
    0.49 mm per side, and gear A1 cannot have seated flush on either printed
    pair. At 0.10 the flare leaves 0.05 mm on every face.
    """
    notch = v2.V2_GEAR_ANTIROT['a1_notch']
    flare = v2.offset_polygon_miter(v2.antirot_nub_profile('positive'), v2.V2_NUB['base_flare'])
    inner, outer, half_width = _radial_extent(flare)
    expected = v2.V2_ANTIROT_CLEARANCE_MM - v2.V2_NUB['base_flare']
    assert inner - notch['inner_radius'] == pytest.approx(expected, abs=GEAR_CAD_ROUNDING_MM)
    assert (notch['half_width'] - half_width) / math.sqrt(3.0) == pytest.approx(expected, abs=GEAR_CAD_ROUNDING_MM)
    # The hard requirement behind the tolerance: it must not interfere at all.
    assert inner > notch['inner_radius']
    assert half_width < notch['half_width']
    assert outer < notch['outer_radius']


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_each_nub_clears_the_notch_floor_axially(plate_type):
    """
    Fit (d), the axis nobody named until gear v7.2.

    The lateral fit was argued over for two print rounds and carries a signed
    0.15 mm per face. The AXIAL fit was never stated at all: the nub was 3.0
    tall into a notch measured at 3.0 deep, so at nominal the nub tip reached
    the ceiling at the very instant the gear face reached the cylinder face,
    and print tolerance decided which one took the load. Its three siblings
    each had 0.15 - the sockets are deliberately cut one clearance deeper than
    the pin is tall - which is what made the gap invisible: the constant is
    named for the anti-rotation clearance, so nobody asked which axes it
    reached.

    Brennen deepened both notches to 3.15 in gear v7.2. Nothing in the
    generator reads that depth, so this is the only thing standing between the
    two numbers and a silent regression.
    """
    notch = v2.V2_GEAR_ANTIROT[v2.ANTIROT_BY_PLATE[plate_type]['nub']]
    assert notch['kind'] == 'notch'
    assert notch['depth'] - v2.V2_NUB['height'] == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=0.001)
    # The hard requirement behind the tolerance: the nub must not bottom out.
    assert v2.V2_NUB['height'] < notch['depth']


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_each_socket_clears_its_gear_pin_axially(plate_type):
    """Fit (d) for the other end - the rule the notches now match."""
    pin = v2.V2_GEAR_ANTIROT[v2.ANTIROT_BY_PLATE[plate_type]['socket']]
    assert pin['kind'] == 'pin'
    assert v2.V2_SOCKET_DEPTH_MM - pin['depth'] == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=0.001)
    assert pin['depth'] < v2.V2_SOCKET_DEPTH_MM


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_each_socket_clears_its_gear_pin_and_leaves_barrel_wall(plate_type):
    """Fit (c): 0.15 mm round the pin, and >= 1.2 mm of wall behind it."""
    pin = v2.V2_GEAR_ANTIROT[v2.ANTIROT_BY_PLATE[plate_type]['socket']]
    inner, outer, half_width = _radial_extent(v2.antirot_socket_profile(plate_type))
    assert pin['inner_radius'] - inner == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=GEAR_CAD_ROUNDING_MM)
    assert half_width - pin['half_width'] == pytest.approx(v2.V2_ANTIROT_CLEARANCE_MM, abs=GEAR_CAD_ROUNDING_MM)
    # Measured from the barrel the module owns, never from a literal 15.25, and
    # to the socket's furthest point from the AXIS rather than its reach along
    # the column. Those differ on the square: its corner arc sits at r 13.2859
    # where the column reach is 13.2000, so the column figure overstates
    # Cylinder B's wall by 0.086 mm. On the triangle the apex is on the column
    # and the two agree.
    furthest = max(math.hypot(x, y) for x, y in v2.antirot_socket_profile(plate_type))
    wall = v2.V2_BARREL_DIAMETER_MM / 2.0 - furthest
    assert wall >= 1.2, f'{plate_type} socket leaves only {wall:.4f} mm of wall'


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_sockets_are_parallel_curves_and_not_mitres(plate_type):
    """
    The Minkowski identity is the signature that tells the two apart.

    Growing a polygon by c as a parallel curve adds exactly perimeter*c + pi*c^2
    - each edge sweeps a rectangle, each corner an arc - while a mitre adds more
    and leaves a sharp internal corner, which in a vertically printed barrel is
    the stress riser. Getting this backwards also moves Cylinder A's wall from
    1.2525 mm to 1.1025, under the 1.2 minimum.
    """
    pin = _gear_pin_polygon(plate_type)
    clearance = v2.V2_ANTIROT_CLEARANCE_MM
    expected = _signed_area(pin) + _perimeter(pin) * clearance + math.pi * clearance**2
    assert _signed_area(v2.antirot_socket_profile(plate_type)) == pytest.approx(expected, abs=0.01)
    # A mitre would be measurably bigger, so the check above genuinely separates
    # them rather than passing on either construction.
    mitred = v2.offset_polygon_miter(pin, clearance)
    assert _signed_area(mitred) > expected + 0.01


def test_the_socket_cap_is_a_guard_rail_that_trims_nothing_today():
    """
    D-R3-3. The cap removes exactly 0.0000 mm at the signed clearance, which is
    precisely why it reads like dead code and must not be deleted: it is what
    keeps the >= 1.2 mm wall true if the clearance is ever raised.
    """
    pin = _gear_pin_polygon('positive')

    def apex(clearance, clipped):
        grown = v2.parallel_curve(pin, clearance)
        points = v2.clip_to_max_radius(grown, v2.V2_SOCKET_MAX_RADIUS_MM) if clipped else grown
        return _radial_extent(points)[1]

    for clearance in (v2.V2_ANTIROT_CLEARANCE_MM, 0.1525):
        assert apex(clearance, True) == pytest.approx(apex(clearance, False), abs=1e-9)

    for clearance in (0.16, 0.30):
        assert apex(clearance, False) > v2.V2_SOCKET_MAX_RADIUS_MM
        assert apex(clearance, True) == pytest.approx(v2.V2_SOCKET_MAX_RADIUS_MM, abs=1e-9)
        wall = v2.V2_BARREL_DIAMETER_MM / 2.0 - apex(clearance, True)
        assert wall >= 1.2


@pytest.mark.parametrize('plate_type', ('positive', 'negative'))
def test_the_nub_block_and_the_antirot_nub_stay_one_shape(plate_type):
    """One shape, one source: nub_block only wires antirot_nub_profile up."""
    emitted = [(point['x'], point['y']) for point in v2.nub_block(plate_type)['profile']]
    expected = [(round(x, 6), round(y, 6)) for x, y in v2.antirot_nub_profile(plate_type)]
    assert emitted == expected


def test_nub_block_takes_a_plate_and_never_a_clearance():
    """
    D-V11 forbids ONE thing: the key-clearance dial reaching the nub. A plate
    selector carries no clearance, so it is safe; an argument the dial can reach
    is not. Pinned by signature so a future refactor cannot quietly re-couple
    them.
    """
    import inspect

    names = list(inspect.signature(v2.nub_block).parameters)
    assert names == ['plate_type']
    assert 'clearance' not in names


@pytest.mark.parametrize(
    'call',
    (
        lambda: v2.antirot_nub_profile('cylinder'),
        lambda: v2.antirot_socket_profile(''),
        lambda: v2.radial_rectangle(13.0, 10.0, 1.5, 0.0),
        lambda: v2.radial_rectangle(10.0, 13.0, 0.0, 0.0),
        lambda: v2.radial_rectangle(10.0, 13.0, 1.5, 2.0),
        lambda: v2.parallel_curve([(0.0, 0.0), (1.0, 0.0)], 0.1),
        lambda: v2.parallel_curve([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], -0.1),
        lambda: v2.clip_to_max_radius([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)], 0.0),
    ),
)
def test_antirot_bad_input_raises_rather_than_guessing(call):
    with pytest.raises(ValueError):
        call()
