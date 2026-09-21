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
their phase gates on 2026-08-28.
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
V2_CYLINDER = {'diameter': 30.8, 'height': 54.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}

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

# S-T1 (DRAFT, 2026-09-21): a 14-cell tactile row does not fit a 90 mm card,
# and every 14-column layout in this module says so. The arrow lead-in
# (D-T1..D-T4) is what put the sentence here; 13 cells is the tactile maximum.
CARD_FIT_WARNING = 'The last braille cell would run off the card: this layout needs 92.9 mm of card from the alignment arrow and the card is 90 mm. Use 13 cells or fewer.'
SIZE_WARNING_START = 'The Version 2 embosser expects a 30.8 mm x 54 mm cylinder.'


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


# --- fused Version 2: fixed gears (2026-09-20 programme, sub-plan B, phase B3) ---


def fused_spec(plate_type='positive', cylinder=None, settings=None):
    return v2_spec(plate_type, cylinder=cylinder, settings={'gear_rollers_enabled': 1, **(settings or {})})


@pytest.mark.parametrize('plate_type, asset', [('positive', 'v2_gears_a'), ('negative', 'v2_gears_b')])
def test_fused_version_two_is_a_solid_barrel_with_its_own_gears_and_a_notch_fill(plate_type, asset):
    """
    Decision D-6: with fixed gears the Version 2 barrel is solid and carries NO
    keyed holes, countersinks, nub or socket; the gears come from the v8 asset
    pair, weld on at +/- height/2, and the top gear's notch is filled.
    """
    spec = fused_spec(plate_type)
    assert spec['cylinder']['solid'] is True
    assert spec['cylinder']['polygon_points'] == []
    assert 'keyed_cutouts' not in spec
    assert spec['warnings'] == [CARD_FIT_WARNING]
    gears = spec['gears']
    assert gears['asset'] == asset
    assert [ring['z_center'] for ring in gears['weld_rings']] == [-27.0, 27.0]
    (fill,) = gears['notch_fills']
    assert fill['gear'] == ('A1' if plate_type == 'positive' else 'B1')
    assert fill['z_from'] == pytest.approx(27.0 - version2.V2_NOTCH_FILL_OVERLAP_MM)
    assert fill['z_to'] == pytest.approx(27.0 + 3.15 + version2.V2_NOTCH_FILL_OVERLAP_MM)
    assert all(set(point) == {'x', 'y'} for point in fill['profile'])


def test_version_two_without_gears_is_byte_identical_to_before():
    """Fixed gears off: the keyed spec of 2026-09-20, key for key, and no gears block."""
    for plate_type in ('positive', 'negative'):
        plain = v2_spec(plate_type)
        explicit_off = v2_spec(plate_type, settings={'gear_rollers_enabled': 0})
        assert plain == explicit_off
        assert 'gears' not in plain
        assert 'keyed_cutouts' in plain


def test_version_one_gear_mode_carries_no_notch_fill_and_the_version_one_asset():
    """The Version 1 one-piece roller is untouched by the fused Version 2 work."""
    settings = {'grid_columns': 14, 'indicator_mode': 'tactile', 'gear_rollers_enabled': 1}
    cylinder = {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}
    spec = build_spec('positive', settings, cylinder)
    assert spec['gears']['asset'] == 'gears_a'
    assert 'notch_fills' not in spec['gears']
    assert 'solid' not in spec['cylinder']
    assert spec['warnings'] == [CARD_FIT_WARNING]


def test_fused_version_two_at_the_version_one_height_warns_with_the_version_two_sentence():
    """
    Direct callers bypass validation: a fused Version 2 spec on the 52 mm
    Version 1 barrel carries the S-G1 warning (signed 2026-09-21), and a Version 1 gear spec
    on the 54 mm barrel carries S7 - each version answers for its own gears.
    """
    fused = fused_spec(cylinder={**V2_CYLINDER, 'height': 52.0})
    # Two notes, each its own: the gears' S-G1 and the barrel's soft S-V5.
    assert fused['warnings'] == [
        'Fixed gears for the Version 2 embosser fit only a 30.8 mm x 54 mm cylinder. Received 30.8 mm x 52 mm.',
        'The Version 2 embosser expects a 30.8 mm x 54 mm cylinder. Received 30.8 mm x 52 mm.',
        CARD_FIT_WARNING,
    ]
    assert not any('reference roller' in warning for warning in fused['warnings'])
    settings = {'grid_columns': 14, 'indicator_mode': 'tactile', 'gear_rollers_enabled': 1}
    tall = build_spec('positive', settings, {**V2_CYLINDER, 'height': 54.0})
    assert tall['warnings'] == [
        'Integrated gears are matched to the reference roller and only fit a 30.8 mm x 52 mm cylinder. '
        'Received 30.8 mm x 54 mm.',
        CARD_FIT_WARNING,
    ]


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
    """Computed from the request's height, never hardcoded to the preset's 27."""
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
    """Nothing about the SIZE: the one warning is the 14-cell card fit."""
    assert v2_spec()['warnings'] == [CARD_FIT_WARNING]


def test_an_off_size_cylinder_warns_but_is_still_built():
    off_size = dict(V2_CYLINDER, diameter=30.5)
    spec = v2_spec(cylinder=off_size)
    assert any(warning.startswith(SIZE_WARNING_START) for warning in spec['warnings'])
    assert '30.5 mm x 54 mm' in ' '.join(spec['warnings'])
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


def test_the_tactile_arrow_recess_clears_the_anti_rotation_socket():
    """
    Both features sit on the 180 degree arrow column, and from FIVE rows up they
    share an axial band: the lowest arrow reaches z -23.00 where the socket
    still reaches -22.85.

    It is safe, but only because of which plate gets which. The plate that
    RECESSES its arrows is Cylinder B, whose socket is the short square reaching
    r 13.20 - so 1.35 mm of wall. The far-reaching triangle socket, r 13.9975,
    belongs to Cylinder A, whose arrows stand PROUD and cut nothing into the
    barrel at all. Swap either half of that pairing and the wall is 0.55 mm,
    under the 1.2 mm FDM minimum, in a place no dial would warn about.

    Asserted as the invariant rather than as the two numbers, so it keeps
    holding whatever the row count and whichever socket profile moves.
    """
    for plate_type in ('positive', 'negative'):
        spec = v2_spec(plate_type, settings={'grid_rows': 5})
        arrows = [m for m in spec['markers'] if m['type'] == 'cylinder_tactile_arrow']
        assert arrows, 'the tactile arrows are what this test is about'
        recessed = [arrow for arrow in arrows if arrow['is_recess']]
        if not recessed:
            continue
        floor = min(arrow['inner_radius'] for arrow in recessed)
        reach = max(-point[0] for point in version2.antirot_socket_profile(plate_type))
        wall = floor - reach
        assert wall >= 1.2, f'{plate_type}: only {wall:.4f} mm between the arrow recess and the socket'
