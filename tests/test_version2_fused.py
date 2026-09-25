"""
Fused (fixed-gear) Version 2 rollers: the constants and math sub-plan B adds
to app/geometry/gears.py and app/geometry/version2.py (2026-09-20 programme,
phase B2).

  1. The gear helpers become version-aware: which asset a plate carries, which
     barrel the gears were measured against, and the rejection sentence - S7
     (signed 2026-08-24) for Version 1, S-G1 (signed 2026-09-21) for Version 2.
  2. The notch fill: each top gear's measured notch grown by 0.05 mm as an exact
     parallel curve, on the arrow column, inside the 13.95 mm cap and clear of
     the other roller's teeth, extruded from just inside the barrel face to
     just past the notch floor.
  3. The v9 update (2026-09-24, decisions D-1, D-2): the barrel's bottom-edge
     chamfer and the two axis cuts - the 2 mm vent the length of the roller and
     the cone that makes each bottom socket's ceiling self-supporting - with
     every z following the request's height.

No mesh library needed: these read dicts and polygons. The S-G1 sentence is
signed off by Brennen on 2026-09-21; reword only with his sign-off.
"""

import math

import pytest

from app.geometry import gears, version2

# ---------------------------------------------------------------------------
# 1. Version-aware gear helpers
# ---------------------------------------------------------------------------


def test_each_version_has_its_own_asset_pair():
    assert gears.gear_asset_for('positive') == 'gears_a'
    assert gears.gear_asset_for('negative') == 'gears_b'
    assert gears.gear_asset_for('positive', 1) == 'gears_a'
    assert gears.gear_asset_for('positive', 2) == 'v2_gears_a'
    assert gears.gear_asset_for('negative', 2) == 'v2_gears_b'
    assert gears.V2_GEAR_ASSET_BY_PLATE == {'positive': 'v2_gears_a', 'negative': 'v2_gears_b'}


@pytest.mark.parametrize('bad', [{'plate_type': 'both'}, {'plate_type': 'positive', 'version': 3}])
def test_unknown_plates_and_versions_raise(bad):
    with pytest.raises(ValueError):
        gears.gear_asset_for(bad['plate_type'], bad.get('version', 1))


def test_the_reference_barrel_is_read_from_the_version_module_never_retyped():
    assert gears.reference_barrel(1) == (gears.GEAR_BARREL_DIAMETER_MM, gears.GEAR_BARREL_HEIGHT_MM) == (30.8, 52.0)
    assert gears.reference_barrel(2) == (version2.V2_BARREL_DIAMETER_MM, version2.V2_BARREL_HEIGHT_MM) == (30.8, 54.0)


def test_matching_follows_the_version():
    assert gears.matches_reference_roller(30.8, 52.0)
    assert gears.matches_reference_roller(30.8, 52.0, 1)
    assert not gears.matches_reference_roller(30.8, 54.0, 1)
    assert gears.matches_reference_roller(30.8, 54.0, 2)
    assert not gears.matches_reference_roller(30.8, 52.0, 2)
    assert gears.matches_reference_roller(30.8005, 54.0005, 2)
    assert not gears.matches_reference_roller(30.802, 54.0, 2)


def test_the_version_one_sentence_is_untouched():
    """S7, signed 2026-08-24: the default call and the explicit version 1 call say the same words."""
    expected = (
        'Integrated gears are matched to the reference roller and only fit a 30.8 mm x 52 mm cylinder. '
        'Received 30.8 mm x 54 mm.'
    )
    assert gears.reference_roller_message(30.8, 54.0) == expected
    assert gears.reference_roller_message(30.8, 54.0, 1) == expected


def test_the_version_two_sentence_is_s_g1():
    """S-G1, signed 2026-09-21 (phase B2). Numbers spelled the signed way: 54, not 54.0."""
    assert gears.reference_roller_message(30.8, 52.0, 2) == (
        'Fixed gears for the Version 2 embosser fit only a 30.8 mm x 54 mm cylinder. Received 30.8 mm x 52 mm.'
    )


# ---------------------------------------------------------------------------
# 2. The notch fill
# ---------------------------------------------------------------------------


def shoelace_area(points):
    return 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1], strict=True)))


def perimeter(points):
    return sum(math.dist(p, q) for p, q in zip(points, points[1:] + points[:1], strict=True))


def notch_outline(plate_type):
    notch = version2.V2_GEAR_ANTIROT[version2.ANTIROT_BY_PLATE[plate_type]['nub']]
    if notch['shape'] == 'triangle':
        return version2.nub_triangle(
            notch['inner_radius'], notch['outer_radius'], notch['half_width'], version2.V2_ARROW_COLUMN_DEG
        )
    return version2.radial_rectangle(notch['inner_radius'], notch['outer_radius'], notch['half_width'], 0.0)


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_fill_area_is_the_notch_grown_by_the_parallel_curve(plate_type):
    """
    A parallel curve at distance d of a convex polygon with area A and perimeter
    P has area A + P d + pi d^2 (Steiner). The fill must be that, not a mitre
    (which would add the sharp-apex spike on the A triangle).
    """
    base = notch_outline(plate_type)
    d = version2.V2_NOTCH_FILL_GROWTH_MM
    expected = shoelace_area(base) + perimeter(base) * d + math.pi * d * d
    fill = version2.notch_fill_outline(plate_type)
    # The arcs are tessellated (96 per circle), so the area falls a hair short of the exact disc.
    assert shoelace_area(fill) == pytest.approx(expected, rel=2e-3)
    assert shoelace_area(fill) > shoelace_area(base)


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_fill_sits_on_the_arrow_column_within_the_cap(plate_type):
    fill = version2.notch_fill_outline(plate_type)
    angles = [math.degrees(math.atan2(y, x)) % 360.0 for x, y in fill]
    assert all(abs(a - version2.V2_ARROW_COLUMN_DEG) < 20.0 for a in angles)
    # The cap is on the true distance from the axis - a rectangle's corners
    # reach further than its outer edge - and that is what must clear the
    # other roller.
    reach = max(math.hypot(x, y) for x, y in fill)
    assert reach <= version2.V2_NOTCH_FILL_MAX_RADIUS_MM
    notch = version2.V2_GEAR_ANTIROT[version2.ANTIROT_BY_PLATE[plate_type]['nub']]
    # Along the column the fill spans exactly inner - growth .. outer + growth:
    # grown by the growth and no more, so the A apex is an arc, not a mitre spike.
    column = math.radians(version2.V2_ARROW_COLUMN_DEG)
    along = [x * math.cos(column) + y * math.sin(column) for x, y in fill]
    assert max(along) == pytest.approx(notch['outer_radius'] + version2.V2_NOTCH_FILL_GROWTH_MM, abs=1e-6)
    assert min(along) == pytest.approx(notch['inner_radius'] - version2.V2_NOTCH_FILL_GROWTH_MM, abs=1e-6)


def test_the_fill_can_never_reach_the_other_roller():
    """13.95 mm cap against the mating tip circle at the Version 1 operating distance."""
    assert version2.MATING_TIP_CIRCLE_RADIUS_MM == pytest.approx(32.0473 - 16.1093702290795)
    assert version2.V2_NOTCH_FILL_MAX_RADIUS_MM < version2.MATING_TIP_CIRCLE_RADIUS_MM
    assert version2.MATING_TIP_CIRCLE_RADIUS_MM - version2.V2_NOTCH_FILL_MAX_RADIUS_MM > 1.9


@pytest.mark.parametrize('plate_type, gear, shape', [('positive', 'A1', 'triangle'), ('negative', 'B1', 'square')])
def test_fill_block_spans_barrel_face_to_notch_floor(plate_type, gear, shape):
    block = version2.notch_fill_block(plate_type, 54.0)
    assert block['gear'] == gear
    assert block['shape'] == shape
    assert block['z_from'] == pytest.approx(27.0 - version2.V2_NOTCH_FILL_OVERLAP_MM)
    assert block['z_to'] == pytest.approx(27.0 + 3.15 + version2.V2_NOTCH_FILL_OVERLAP_MM)
    assert all(set(point) == {'x', 'y'} for point in block['profile'])
    assert len(block['profile']) >= 3
    # Follows the request's height, never the preset.
    assert version2.notch_fill_block(plate_type, 52.0)['z_from'] == pytest.approx(
        26.0 - version2.V2_NOTCH_FILL_OVERLAP_MM
    )


def test_fill_block_refuses_a_non_positive_height():
    with pytest.raises(ValueError):
        version2.notch_fill_block('positive', 0.0)


def test_fill_refuses_an_unknown_plate():
    with pytest.raises(ValueError):
        version2.notch_fill_outline('both')


# ---------------------------------------------------------------------------
# 3. The v9 update: chamfer, vent, socket cone (2026-09-24)
# ---------------------------------------------------------------------------


def test_the_socket_table_is_the_measured_hardware():
    """Recorded off the v8 assets (01_V9_STL_AUDIT.md section 4); a retype is a hardware change."""
    assert version2.V2_GEAR_SOCKET == {
        'positive': {
            'gear': 'A2',
            'bore_radius': 7.0,
            'rim_radius': 5.3,
            'ceiling_below_face': 1.5,
            'mouth_chamfer': 1.0,
        },
        'negative': {
            'gear': 'B2',
            'bore_radius': 5.0,
            'rim_radius': 3.3,
            'ceiling_below_face': 1.5,
            'mouth_chamfer': 1.0,
        },
    }
    assert (version2.V2_FUSED_BARREL_CHAMFER_MM, version2.V2_VENT_RADIUS_MM) == (0.65, 1.0)
    assert gears.GEAR_BODY_THICKNESS_MM == 10.0


def test_bottom_chamfer_block_is_the_signed_size_with_its_lip():
    assert version2.bottom_chamfer_block(version2.V2_BARREL_DIAMETER_MM / 2) == {'size': 0.65, 'lip': 1.0}


def test_bottom_chamfer_refuses_a_foot_inside_the_gear_root_circle():
    """14.0 - 0.65 = 13.35 sits inside the 13.6613 root circle: the barrel would stand on air."""
    with pytest.raises(ValueError):
        version2.bottom_chamfer_block(14.0)


@pytest.mark.parametrize(
    'plate_type, gear, r_from, z_to',
    [('positive', 'A2', 5.81, -24.2), ('negative', 'B2', 3.81, -26.2)],
)
def test_axis_cuts_at_the_version_two_height(plate_type, gear, r_from, z_to):
    """
    The vent runs the whole roller plus 1 mm out of each mouth; the cone starts
    0.5 below the old ceiling (z -28.5) at the rim grown 0.5 + 0.01 and rises at
    45 degrees to the vent radius + 0.01.
    """
    vent, cone = version2.axis_cut_blocks(plate_type, 54.0)
    assert vent == {'kind': 'vent', 'radius': 1.0, 'z_from': -38.0, 'z_to': 38.0}
    assert cone['kind'] == 'cone'
    assert cone['gear'] == gear
    assert cone['z_from'] == pytest.approx(-29.0)
    assert cone['r_from'] == pytest.approx(r_from)
    assert cone['z_to'] == pytest.approx(z_to)
    assert cone['r_to'] == pytest.approx(1.01)
    # 45 degrees: the radius falls exactly as fast as z rises.
    assert (cone['r_from'] - cone['r_to']) == pytest.approx(cone['z_to'] - cone['z_from'])


def test_axis_cuts_follow_the_height_never_the_preset():
    vent, cone = version2.axis_cut_blocks('positive', 52.0)
    assert (vent['z_from'], vent['z_to']) == (-37.0, 37.0)
    assert cone['z_from'] == pytest.approx(-28.0)
    assert cone['z_to'] == pytest.approx(-23.2)


@pytest.mark.parametrize('plate_type, height', [('both', 54.0), ('positive', 0.0), ('negative', -1.0)])
def test_axis_cuts_refuse_bad_input(plate_type, height):
    with pytest.raises(ValueError):
        version2.axis_cut_blocks(plate_type, height)


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_the_cone_stays_inside_the_weld_rings_and_the_vent_inside_every_peg(plate_type):
    vent, cone = version2.axis_cut_blocks(plate_type, 54.0)
    assert cone['r_from'] < gears.WELD_RING_R_IN_MM
    narrowest = min(min(p['length'], p['width']) for p in version2.V2_KEY_PROFILES.values()) / 2.0
    assert narrowest == 4.0
    assert vent['radius'] < narrowest
