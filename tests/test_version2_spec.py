"""
What app/geometry_spec.py emits for Embosser Version 2.

Two halves, and the second matters as much as the first:

  1. Version 2 adds `cylinder.solid` and a `keyed_cutouts` block carrying the
     two key halves, the four mouth countersinks and - on BOTH plates since
     2026-08-29 - an anti-rotation nub above the top face and socket in the
     bottom one, with every number and z range derived from the request rather
     than from the preset.
  2. Version 1 is untouched. With the field absent, 1, '1', 1.0 or '' the spec
     is deep-equal to the one produced with no field at all, across every spec
     variant, and the comparison is proved able to fail.

These need no mesh library - they read the dict the worker will act on.

The Version 2 sentences quoted here are DRAFT: Brennen deferred the strings to
their phase gates on 2026-08-28. FLAGGED FOR BRENNEN.
"""

import copy

import pytest

from app.geometry import version2
from app.geometry_spec import extract_cylinder_geometry_spec
from app.models import CardSettings
from app.utils import braille_to_dots

LINES = ['⠁⠃⠉', '', '', '']
BACK_LINES = ['⠙⠑⠋', '', '', '']

V1_CYLINDER = {'diameter': 30.75, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 355.0}
V2_CYLINDER = {'diameter': 30.5, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}

DOUBLE_SIDED_SETTINGS = {
    'double_sided_enabled': 1,
    'indicator_mode': 'tactile',
    'interpoint_offset_x': 1.25,
    'interpoint_offset_y': 1.25,
    'ds_dot_base_diameter': 1.2,
    'ds_dot_base_height': 0.4,
    'ds_dot_dome_diameter': 0.8,
    'ds_dot_dome_height': 0.4,
    'ds_bowl_base_diameter': 1.3,
    'ds_bowl_depth': 0.5,
}

# Every spelling of "the user did not ask for Version 2".
VERSION_ONE_VALUES = [
    {},
    {'embosser_version': 1},
    {'embosser_version': '1'},
    {'embosser_version': 1.0},
    {'embosser_version': ''},
]

# S-V14, new in this phase, and S-V5. Both DRAFT.
CUTOUT_WARNING = 'The polygonal cutout is not used in Version 2.'
SIZE_WARNING_START = 'The Version 2 embosser expects a 30.5 mm x 52 mm cylinder.'


def build_spec(plate_type='positive', settings=None, cylinder=None, back_lines=None):
    settings_data = {'grid_columns': 14, 'grid_rows': 4, 'indicator_mode': 'tactile'}
    settings_data.update(settings or {})
    return extract_cylinder_geometry_spec(
        LINES,
        'g1',
        CardSettings(**settings_data),
        dict(cylinder or V1_CYLINDER),
        None,
        plate_type,
        braille_to_dots,
        back_lines,
    )


def v2_spec(plate_type='positive', clearance=None, cylinder=None, settings=None):
    data = {'embosser_version': 2}
    if clearance is not None:
        data['v2_key_clearance_mm'] = clearance
    data.update(settings or {})
    return build_spec(plate_type, data, cylinder or V2_CYLINDER)


# --- Version 1 is untouched -------------------------------------------------


def _variants():
    for plate in ('positive', 'negative'):
        for tactile in (False, True):
            for cutout in (False, True):
                settings = {'grid_columns': 14 if tactile else 15}
                settings['indicator_mode'] = 'tactile' if tactile else 'visual'
                cylinder = dict(V1_CYLINDER)
                if cutout:
                    cylinder.update(polygonal_cutout_radius_mm=13.0, polygonal_cutout_sides=12)
                yield plate, settings, cylinder, None
    for plate in ('positive', 'negative'):
        yield plate, dict(DOUBLE_SIDED_SETTINGS), dict(V1_CYLINDER), BACK_LINES


@pytest.mark.parametrize('off', VERSION_ONE_VALUES)
def test_version_one_specs_are_deep_equal_across_every_variant(off):
    for plate, settings, cylinder, back in _variants():
        baseline = build_spec(plate, settings, cylinder, back)
        with_field = build_spec(plate, {**settings, **off}, cylinder, back)
        assert baseline == with_field, f'{plate} spec changed with {off}'


def test_the_comparison_above_can_actually_fail():
    """A 0.01 mm nudge must break it, or the test proves nothing."""
    baseline = build_spec()
    nudged = dict(V1_CYLINDER)
    nudged['diameter'] += 0.01
    assert baseline != build_spec(cylinder=nudged)


@pytest.mark.parametrize('off', VERSION_ONE_VALUES)
def test_version_one_carries_no_new_keys(off):
    spec = build_spec(settings=off)
    assert 'keyed_cutouts' not in spec
    assert 'solid' not in spec['cylinder']


# --- what Version 2 emits ---------------------------------------------------


@pytest.mark.parametrize('plate_type', ('positive', 'negative'))
def test_version_two_forces_the_barrel_solid(plate_type):
    """
    An empty polygon list does not mean "solid" to the worker - it hollows the
    barrel by wall thickness unless told otherwise, which would seal a cavity
    around the keyed hole.
    """
    spec = v2_spec(plate_type)
    assert spec['cylinder']['solid'] is True
    assert spec['cylinder']['polygon_points'] == []


@pytest.mark.parametrize('plate_type', ('positive', 'negative'))
def test_each_plate_gets_its_own_pair_of_keys(plate_type):
    spec = v2_spec(plate_type)
    block = spec['keyed_cutouts']
    bottom_name, top_name = version2.KEY_PROFILES_BY_PLATE[plate_type]

    assert block['clearance_mm'] == version2.V2_KEY_CLEARANCE_DEFAULT_MM
    assert [half['end'] for half in block['halves']] == ['bottom', 'top']
    for half, name in zip(block['halves'], (bottom_name, top_name), strict=True):
        expected = version2.key_profile(name, version2.V2_KEY_CLEARANCE_DEFAULT_MM)
        assert len(half['profile']) == len(expected)
        assert half['profile'][0]['x'] == pytest.approx(expected[0][0], abs=1e-6)
    assert [sink['kind'] for sink in block['countersinks']] == ['hull', 'hull']


def test_both_plates_carry_a_nub_and_a_socket():
    """
    The "nub on Cylinder A only" invariant retired on 2026-08-29, when every
    gear gained an anti-rotation feature. Both plates now carry both, and the
    two plates' shapes must differ or the pair cannot tell its ends apart.
    """
    positive = v2_spec('positive')['keyed_cutouts']
    negative = v2_spec('negative')['keyed_cutouts']
    for feature in ('nub', 'socket'):
        assert feature in positive and feature in negative
        assert positive[feature]['profile'] != negative[feature]['profile']


def test_the_z_ranges_follow_the_cylinder_height():
    """Computed from the request's height, never hardcoded to the preset's 26."""
    tall = dict(V2_CYLINDER, height=60.0)
    block = v2_spec(cylinder=tall)['keyed_cutouts']
    assert block['halves'][0]['z_from'] == pytest.approx(-30.01)
    assert block['halves'][0]['z_to'] == pytest.approx(0.01)
    assert block['halves'][1]['z_from'] == pytest.approx(-0.01)
    assert block['halves'][1]['z_to'] == pytest.approx(30.01)
    assert block['nub']['z_from'] == pytest.approx(29.99)
    assert block['nub']['z_to'] == pytest.approx(33.0)
    assert block['socket']['z_from'] == pytest.approx(-30.01)
    assert block['socket']['z_to'] == pytest.approx(-30.0 + version2.V2_SOCKET_DEPTH_MM)


@pytest.mark.parametrize('clearance', (0.0, 0.075, 0.5))
def test_the_clearance_flows_into_the_profiles(clearance):
    block = v2_spec(clearance=clearance)['keyed_cutouts']
    bottom_name = version2.KEY_PROFILES_BY_PLATE['positive'][0]
    nominal = version2.V2_KEY_PROFILES[bottom_name]['width']
    xs = [point['x'] for point in block['halves'][0]['profile']]
    assert block['clearance_mm'] == clearance
    assert max(xs) - min(xs) == pytest.approx(nominal + 2 * clearance, abs=1e-6)


# --- warnings ---------------------------------------------------------------


def test_the_preset_size_warns_about_nothing():
    assert v2_spec()['warnings'] == []


def test_an_off_size_cylinder_warns_but_is_still_built():
    off_size = dict(V2_CYLINDER, diameter=30.8)
    spec = v2_spec(cylinder=off_size)
    assert any(warning.startswith(SIZE_WARNING_START) for warning in spec['warnings'])
    assert '30.8 mm x 52 mm' in ' '.join(spec['warnings'])
    assert spec['keyed_cutouts']['halves'], 'the cylinder is still built'


def test_a_polygonal_cutout_is_dropped_with_a_warning():
    with_cutout = dict(V2_CYLINDER, polygonal_cutout_radius_mm=13.0, polygonal_cutout_sides=12)
    spec = v2_spec(cylinder=with_cutout)
    assert CUTOUT_WARNING in spec['warnings']
    assert spec['cylinder']['polygon_points'] == []


def test_no_cutout_warning_when_none_was_asked_for():
    assert CUTOUT_WARNING not in v2_spec()['warnings']


# --- coexistence ------------------------------------------------------------


def test_double_sided_and_version_two_coexist():
    """
    Both are cylinder-only betas that touch different things: one the dots, the
    other the ends. A Version 2 pair must still be an interpoint pair.
    """
    spec = build_spec(
        'positive',
        {**DOUBLE_SIDED_SETTINGS, 'embosser_version': 2},
        V2_CYLINDER,
        BACK_LINES,
    )
    assert 'keyed_cutouts' in spec
    assert spec['cylinder']['solid'] is True
    assert any(dot['is_recess'] for dot in spec['dots']), 'the interpoint recesses are still there'
    assert any(not dot['is_recess'] for dot in spec['dots'])


def test_the_tactile_arrows_are_unchanged_by_the_flag():
    """The keys sit on the arrow column but must not move or resize it."""
    baseline = build_spec(cylinder=V2_CYLINDER)
    with_v2 = v2_spec()
    assert [copy.deepcopy(marker) for marker in baseline['markers']] == [
        copy.deepcopy(marker) for marker in with_v2['markers']
    ]


def test_the_seam_offset_does_not_turn_the_keys():
    """
    Gear A1's notch drops onto the nub in exactly one orientation, so the keys
    are tied to the arrow column rather than to the seam.
    """
    turned = dict(V2_CYLINDER, seam_offset_deg=90.0)
    assert v2_spec(cylinder=turned)['keyed_cutouts'] == v2_spec()['keyed_cutouts']
