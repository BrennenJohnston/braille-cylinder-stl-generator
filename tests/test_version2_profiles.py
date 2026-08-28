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

CLEARANCES = (0.0, 0.15, 0.30, 0.50)

# audit_fit_matrix.py, family R14: the smallest distance any wrong peg sticks
# out of a hole, per side, at each clearance.
SMALLEST_WRONG_PAIR_PROTRUSION = {0.0: 1.000, 0.15: 0.850, 0.30: 0.700, 0.50: 0.500}


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


@pytest.mark.parametrize('clearance', (0.0, 0.15, 0.50))
def test_the_nub_inset_moves_every_face_in_by_c(clearance):
    """
    D-V11: the dial shrinks the nub by the same c the holes grew by, because
    gear A1's notch is a fixed negative and wants clearance on each face.

    The inradius is what moves by exactly c. The base gets narrower by about
    sqrt(3) * c - roughly 1.73 times as much - so "shrinks by c" is a statement
    about the faces, never about the width.
    """
    half_width = v2.V2_NUB['side'] / 2.0
    outline = v2.nub_triangle(v2.V2_NUB['base_radius'], v2.V2_NUB['apex_radius'], half_width, v2.V2_ARROW_COLUMN_DEG)
    inset = v2.offset_polygon_miter(outline, -clearance)

    assert _signed_area(outline) > 0
    assert _inradius(outline) - _inradius(inset) == pytest.approx(clearance, abs=1e-9)

    base_shrink = (math.dist(outline[0], outline[2]) - math.dist(inset[0], inset[2])) / 2.0
    if clearance:
        assert base_shrink / clearance == pytest.approx(math.sqrt(3), abs=0.001)


def test_the_nub_points_at_the_arrow_column():
    half_width = v2.V2_NUB['side'] / 2.0
    outline = v2.nub_triangle(v2.V2_NUB['base_radius'], v2.V2_NUB['apex_radius'], half_width, v2.V2_ARROW_COLUMN_DEG)
    apex = max(outline, key=lambda p: math.hypot(*p))
    assert math.hypot(*apex) == pytest.approx(v2.V2_NUB['apex_radius'], abs=1e-9)
    assert math.degrees(math.atan2(apex[1], apex[0])) % 360 == pytest.approx(v2.V2_ARROW_COLUMN_DEG, abs=1e-9)


def test_block_matches_the_wire_contract():
    block = v2.keyed_cutout_block('positive', 52.0, 0.15)
    assert set(block) == {'clearance_mm', 'halves', 'countersinks', 'nub'}
    assert block['clearance_mm'] == 0.15

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

    nub = block['nub']
    assert set(nub) == {'profile', 'top_chamfer', 'base_flare', 'z_from', 'z_to'}
    assert nub['z_from'] == pytest.approx(25.99)
    assert nub['z_to'] == pytest.approx(29.0)
    assert set(nub['top_chamfer']) == {'depth', 'profile'}


def test_each_plate_carries_its_own_pair_of_keys():
    positive = v2.keyed_cutout_block('positive', 52.0, 0.15)
    negative = v2.keyed_cutout_block('negative', 52.0, 0.15)

    assert 'nub' not in negative, 'only Cylinder A carries the nub'
    for block, (bottom_name, top_name) in (
        (positive, v2.KEY_PROFILES_BY_PLATE['positive']),
        (negative, v2.KEY_PROFILES_BY_PLATE['negative']),
    ):
        for half, name in zip(block['halves'], (bottom_name, top_name)):
            expected = v2.key_profile(name, 0.15)
            assert len(half['profile']) == len(expected)
            assert half['profile'][0]['x'] == pytest.approx(expected[0][0], abs=1e-6)


def test_the_block_scales_with_the_cylinder_height():
    block = v2.keyed_cutout_block('positive', 40.0, 0.15)
    assert block['halves'][0]['z_from'] == pytest.approx(-20.01)
    assert block['halves'][1]['z_to'] == pytest.approx(20.01)
    assert block['nub']['z_from'] == pytest.approx(19.99)


@pytest.mark.parametrize(
    'call',
    (
        lambda: v2.keyed_cutout_block('cylinder', 52.0, 0.15),
        lambda: v2.keyed_cutout_block('', 52.0, 0.15),
        lambda: v2.keyed_cutout_block('positive', 0.0, 0.15),
        lambda: v2.keyed_cutout_block('positive', 52.0, 0.75),
        lambda: v2.keyed_cutout_block('positive', 52.0, -0.1),
        lambda: v2.key_profile('a1_star', 0.15),
        lambda: v2.rounded_rectangle(14.0, 14.0, 8.0),
        lambda: v2.rounded_rectangle(0.0, 14.0, 0.5),
    ),
)
def test_bad_input_raises_rather_than_guessing(call):
    with pytest.raises(ValueError):
        call()


def test_size_check_and_message():
    assert v2.matches_v2_barrel(30.1, 52.0)
    assert v2.matches_v2_barrel(30.1005, 52.0)
    assert not v2.matches_v2_barrel(30.8, 52.0)
    assert not v2.matches_v2_barrel(30.1, 51.0)

    message = v2.v2_size_message(30.8, 52.0)
    assert message == ('The Version 2 embosser expects a 30.1 mm x 52 mm cylinder. Received 30.8 mm x 52 mm.')
    assert '52.0 mm' not in message
