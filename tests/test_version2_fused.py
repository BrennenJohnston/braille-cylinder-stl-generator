"""
Fused (fixed-gear) Version 2 rollers: the constants and math sub-plan B adds
to app/geometry/gears.py and app/geometry/version2.py (2026-09-20 programme,
phase B2).

  1. The gear helpers become version-aware: which asset a plate carries, which
     barrel the gears were measured against, and the rejection sentence - S7
     (signed) for Version 1, S-G1 (DRAFT) for Version 2.
  2. The notch fill: each top gear's measured notch grown by 0.05 mm as an exact
     parallel curve, on the arrow column, inside the 13.95 mm cap and clear of
     the other roller's teeth, extruded from just inside the barrel face to
     just past the notch floor.

No mesh library needed: these read dicts and polygons. The S-G1 sentence is
DRAFT. FLAGGED FOR BRENNEN.
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
    """S-G1, DRAFT (phase B2) - FLAGGED FOR BRENNEN. Numbers spelled the signed way: 54, not 54.0."""
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
