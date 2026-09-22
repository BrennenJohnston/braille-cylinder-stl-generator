"""
What app/geometry_spec.py emits for the slicer seam channel (2026-09-20 programme, phase A2).

The channel is a shallow V-groove cut the full height of the barrel's outer
surface, inside the seam gap beside the row-indicator column, so a slicer's
"aligned" seam mode hides every layer's seam there instead of in a dot. These
tests read the dict the worker acts on; they need no mesh library.

  1. Placement: the groove sits in the middle of the free window between the
     features either side of the seam gap, and the two plates mirror exactly.
  2. Fit: the groove is left out, with a warning, when the window is narrower
     than the groove plus its margins, or when the wall under it would be
     thinner than the FDM minimum.
  3. Off: with the switch off (or the channel left out) the spec is
     byte-identical to the one built before the channel existed.

The warning sentences quoted here (S-C2, S-C3) were signed off by Brennen on 2026-09-21; reword only with his sign-off.
"""

import copy
import json
import math
from pathlib import Path

import pytest

from app import geometry_spec
from app.geometry_spec import extract_cylinder_geometry_spec
from app.models import CardSettings
from app.utils import braille_to_dots

FULL_CELL = '⠿'  # all six dots
LINES = [FULL_CELL * 13] * 4
BACK_LINES = [FULL_CELL * 14] * 4

# The 0.4 mm card-stock preset's dot families, the ones the UI sends on load.
PRESET_04 = {
    'grid_rows': 4,
    'use_rounded_dots': 1,
    'rounded_dot_base_diameter': 1.5,
    'rounded_dot_base_height': 0.5,
    'rounded_dot_dome_diameter': 1.0,
    'rounded_dot_dome_height': 0.5,
    'recess_shape': 1,
    'bowl_counter_dot_base_diameter': 1.8,
    'counter_dot_depth': 0.8,
}
DS_04 = {
    'double_sided_enabled': 1,
    'indicator_mode': 'tactile',
    'interpoint_offset_x': 1.25,
    'interpoint_offset_y': 1.25,
    'ds_dot_base_diameter': 1.2,
    'ds_dot_base_height': 0.5,
    'ds_dot_dome_diameter': 1.0,
    'ds_dot_dome_height': 0.5,
    'ds_bowl_base_diameter': 1.4,
    'ds_bowl_depth': 0.5,
}

V1_CYLINDER = {
    'diameter': 30.8,
    'height': 52.0,
    'wall_thickness': 2.0,
    'seam_offset_deg': 0.0,
    'polygonal_cutout_radius_mm': 13.0,
    'polygonal_cutout_sides': 12,
}

# Wording signed off by Brennen (2026-09-21), phase A2; reword only with his sign-off.
GAP_WARNING = 'The seam channel was left out: the seam gap is too narrow for it at this cell count and diameter.'
WALL_WARNING = 'The seam channel was left out: the cylinder wall would be thinner than 1.2 mm under it.'


def build_spec(plate_type='positive', settings=None, cylinder=None, lines=None, back_lines=None):
    settings_data = {**PRESET_04, 'grid_columns': 15, 'indicator_mode': 'visual'}
    settings_data.update(settings or {})
    return extract_cylinder_geometry_spec(
        lines if lines is not None else LINES,
        'g1',
        CardSettings(**settings_data),
        dict(cylinder or V1_CYLINDER),
        None,
        plate_type,
        braille_to_dots,
        back_lines,
    )


def channel_of(spec):
    return spec['cylinder']['seam_channel']


def angular_distance(a, b):
    """Smallest angle between two directions, in radians."""
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


# ---------------------------------------------------------------------------
# 1. Placement
# ---------------------------------------------------------------------------


def test_constants_are_the_signed_groove():
    """Decision D-15 (2026-09-20): V 1.0 x 0.5 mm, 0.25 mm margins, 1.2 mm wall."""
    assert geometry_spec.SEAM_CHANNEL_WIDTH_MM == 1.0
    assert geometry_spec.SEAM_CHANNEL_DEPTH_MM == 0.5
    assert geometry_spec.SEAM_CHANNEL_MARGIN_MM == 0.25
    assert geometry_spec.SEAM_CHANNEL_OVERSHOOT_MM == 1.0
    assert geometry_spec.SEAM_CHANNEL_LIP_MM == 0.5
    assert geometry_spec.SEAM_CHANNEL_MIN_WALL_MM == 1.2


def test_block_carries_the_constants_and_nothing_else():
    block = channel_of(build_spec())
    assert set(block) == {'theta', 'width', 'depth', 'overshoot', 'lip'}
    assert block['width'] == geometry_spec.SEAM_CHANNEL_WIDTH_MM
    assert block['depth'] == geometry_spec.SEAM_CHANNEL_DEPTH_MM
    assert block['overshoot'] == geometry_spec.SEAM_CHANNEL_OVERSHOOT_MM
    assert block['lip'] == geometry_spec.SEAM_CHANNEL_LIP_MM


def test_visual_15_columns_worked_numbers():
    """
    30.8 mm, 0.4 preset, 15 columns visual: gap 5.761 mm, free window from
    -0.731 (last cell's dots) to +1.631 (column 0's triangle), so the groove
    centre sits 0.450 mm toward column 0 - 178.33 degrees on the embossing
    plate and 181.67 on the counter plate. The spike measured exactly these on
    its own STLs (build/seam_spike/REPORT.md, 2026-09-20).
    """
    assert math.degrees(channel_of(build_spec('positive'))['theta']) == pytest.approx(178.326, abs=0.005)
    assert math.degrees(channel_of(build_spec('negative'))['theta']) == pytest.approx(181.674, abs=0.005)


def test_tactile_14_columns_worked_numbers():
    """
    Tactile mode since D-T6 / D-T7 (2026-09-21): the groove runs down the
    arrow column itself - 180 degrees on both plates, the arrow's own angle -
    the full height, and the embossing plate recuts it through the raised
    arrows. 4 rows on 10 mm spacing put the arrows at +/-15 and +/-5 mm, a
    chain from -20 to +20; the recut spans it plus 0.3 mm at each end, with
    the V's sides carried 0.5 mm past the arrows' 0.5 mm raise. The counter
    plate's recesses are deeper than the groove, so it gets no recut.
    """
    tactile = {'grid_columns': 14, 'indicator_mode': 'tactile'}
    lines = [FULL_CELL * 14] * 4
    a = channel_of(build_spec('positive', tactile, lines=lines))
    b = channel_of(build_spec('negative', tactile, lines=lines))
    assert a['theta'] == pytest.approx(math.pi) and b['theta'] == pytest.approx(math.pi)
    assert set(a) == {'theta', 'width', 'depth', 'overshoot', 'lip', 'arrow_recut'}
    assert set(b) == {'theta', 'width', 'depth', 'overshoot', 'lip'}
    recut = a['arrow_recut']
    assert (round(recut['z_from'], 3), round(recut['z_to'], 3), recut['lip']) == (-20.3, 20.3, 1.0)


def test_the_recut_covers_every_raised_arrow():
    """
    From the emitted markers, not the formula: on every tactile layout the
    embossing plate's recut spans every raised arrow's outline plus the margin,
    its lip clears the arrows' raise by the channel lip, it stays inside the
    end faces, and the groove's angle is the arrows' own.
    """
    margin = geometry_spec.SEAM_CHANNEL_ARROW_MARGIN_MM
    for columns, extra in ((13, {}), (14, {}), (12, {'tactile_indicator_layout': 'three_spaced'})):
        settings = {'grid_columns': columns, 'indicator_mode': 'tactile', **extra}
        spec = build_spec('positive', settings, lines=[FULL_CELL * columns] * 4)
        groove = channel_of(spec)
        recut = groove['arrow_recut']
        height = spec['cylinder']['height']
        arrows = [m for m in spec['markers'] if m['type'] == 'cylinder_tactile_arrow']
        assert arrows
        assert -height / 2.0 < recut['z_from'] < recut['z_to'] < height / 2.0
        for arrow in arrows:
            assert groove['theta'] == pytest.approx(arrow['theta'])
            assert arrow['is_recess'] is False
            low = arrow['y'] - arrow['length'] / 2.0 - arrow['outline_delta']
            high = arrow['y'] + arrow['length'] / 2.0 + arrow['outline_delta']
            assert recut['z_from'] <= low - margin + 1e-9 and recut['z_to'] >= high + margin - 1e-9, (
                f'{columns} columns: the recut {recut} misses the arrow at {arrow["y"]}'
            )
            raise_mm = float(arrow['outer_radius']) - float(arrow['radius'])
            assert recut['lip'] == pytest.approx(raise_mm + geometry_spec.SEAM_CHANNEL_LIP_MM)


@pytest.mark.parametrize(
    'settings, lines',
    [
        ({}, LINES),
        ({'grid_columns': 13}, [FULL_CELL * 11] * 4),
        ({'grid_columns': 14, 'indicator_mode': 'tactile'}, [FULL_CELL * 14] * 4),
        ({'grid_columns': 12, 'indicator_mode': 'tactile', 'tactile_indicator_layout': 'three_spaced'}, LINES),
        ({**DS_04, 'grid_columns': 14}, [FULL_CELL * 14] * 4),
    ],
    ids=['visual15', 'visual13', 'tactile14', 'tactile12-three-arrows', 'double-sided14'],
)
def test_the_two_plates_mirror_exactly(settings, lines):
    """theta_A + theta_B == 2 pi: the counter plate is the emboss plate's mirror."""
    back = BACK_LINES if settings.get('double_sided_enabled') else None
    a = channel_of(build_spec('positive', settings, lines=lines, back_lines=back))
    b = channel_of(build_spec('negative', settings, lines=lines, back_lines=back))
    assert a['theta'] + b['theta'] == pytest.approx(2 * math.pi, abs=1e-12)
    if settings.get('indicator_mode') == 'tactile':
        # Down the arrow column on both plates: 180 degrees, its own mirror (D-T6).
        assert a['theta'] == pytest.approx(math.pi) and b['theta'] == pytest.approx(math.pi)
    else:
        assert a['theta'] < math.pi < b['theta']


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
@pytest.mark.parametrize(
    'settings, lines',
    [
        ({}, LINES),
        ({'grid_columns': 14, 'indicator_mode': 'tactile'}, [FULL_CELL * 14] * 4),
        ({**DS_04, 'grid_columns': 14}, [FULL_CELL * 14] * 4),
    ],
    ids=['visual15', 'tactile14', 'double-sided14'],
)
def test_the_groove_keeps_its_margin_from_every_dot_and_marker(settings, lines, plate_type):
    """
    From the emitted coordinates, not the formula: the nearest edge of any dot,
    triangle or arrow is at least half the mouth plus the margin from the
    groove's centre line, on both plates and in every layout.
    """
    back = BACK_LINES if settings.get('double_sided_enabled') else None
    spec = build_spec(plate_type, settings, lines=lines, back_lines=back)
    radius = spec['cylinder']['radius']
    theta_c = channel_of(spec)['theta']
    clear = geometry_spec.SEAM_CHANNEL_WIDTH_MM / 2.0 + geometry_spec.SEAM_CHANNEL_MARGIN_MM

    assert spec['dots'], 'the layout must put dots on the plate for this to prove anything'
    for dot in spec['dots']:
        params = dot['params']
        feature_radius = params.get('bowl_radius') or params.get('recess_radius') or params.get('base_radius')
        arc = radius * angular_distance(dot['theta'], theta_c)
        assert arc - feature_radius >= clear - 1e-9, f'dot at {math.degrees(dot["theta"]):.2f} deg crowds the groove'

    for marker in spec['markers']:
        arc = radius * angular_distance(marker['theta'], theta_c)
        if marker['type'] == 'cylinder_tactile_arrow':
            # Tactile mode (D-T6): the groove shares the arrow's column and keeps
            # clear of it along the AXIS instead - test_tactile_groove_never_reaches_an_arrow_outline.
            continue
        elif marker['type'] == 'cylinder_triangle':
            half = marker['size'] / 2.0
        else:
            continue  # letter / rectangle markers sit a whole cell further from the seam
        assert arc - half >= clear - 1e-9, f'{marker["type"]} crowds the groove'


def test_double_sided_uses_its_own_package_for_the_footprint():
    """
    Double-sided replaces every dot with the ds_* package, so the single-sided
    families do not widen the footprint: with a 3.0 mm single-sided dot dialled
    in the double-sided groove does not move.
    """
    lines = [FULL_CELL * 14] * 4
    base = channel_of(build_spec('positive', {**DS_04, 'grid_columns': 14}, lines=lines, back_lines=BACK_LINES))
    fat = channel_of(
        build_spec(
            'positive',
            {**DS_04, 'grid_columns': 14, 'rounded_dot_base_diameter': 3.0},
            lines=lines,
            back_lines=BACK_LINES,
        )
    )
    assert fat['theta'] == base['theta']


# ---------------------------------------------------------------------------
# 2. Fit
# ---------------------------------------------------------------------------


def test_tactile_15_columns_still_gets_its_groove():
    """
    15 columns tactile leaves a 5.761 mm gap - the layout draws the signed
    'needs at least 9 mm' tactile warning - but the groove sits on the arrow
    column, not in the gap, so it is cut regardless (D-T6).
    """
    spec = build_spec('positive', {'grid_columns': 15, 'indicator_mode': 'tactile'}, lines=[FULL_CELL * 15] * 4)
    assert 'seam_channel' in spec['cylinder']
    assert GAP_WARNING not in spec['warnings']
    assert any(w.startswith('Tactile indicator needs a seam gap') for w in spec['warnings'])


def test_a_short_barrel_keeps_the_recut_inside_its_end_faces():
    """
    4 rows on 10 mm spacing with 10 mm arrows span 40 mm; on a 40 mm barrel
    the chain plus its margin would reach past the end faces, and the recut is
    clamped SEAM_CHANNEL_RECUT_INSET_MM inside them instead - the full-height
    cut has already taken the groove there, and a gear face must never be
    nicked. The groove itself is never left out in tactile mode.
    """
    short = {'diameter': 30.8, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}
    spec = build_spec(
        'positive', {'grid_columns': 13, 'indicator_mode': 'tactile'}, cylinder=short, lines=[FULL_CELL * 13] * 4
    )
    recut = channel_of(spec)['arrow_recut']
    inset = 20.0 - geometry_spec.SEAM_CHANNEL_RECUT_INSET_MM
    assert (recut['z_from'], recut['z_to']) == pytest.approx((-inset, inset))
    assert not any(w.startswith('The seam channel was left out') for w in spec['warnings'])


def test_narrow_barrel_visual_has_no_room_and_says_so():
    """A 26 mm barrel at 15 columns: gap -9.3 mm, nowhere to put anything."""
    spec = build_spec('negative', cylinder={**V1_CYLINDER, 'diameter': 26.0})
    assert 'seam_channel' not in spec['cylinder']
    assert spec['warnings'] == [GAP_WARNING]


def test_default_cutout_leaves_enough_wall():
    """15.4 - 0.5 - 13.459 (12-gon circumradius of a 13.0 inscribed cutout) = 1.441 mm."""
    spec = build_spec()
    assert 'seam_channel' in spec['cylinder']
    assert spec['warnings'] == []


def test_a_wide_cutout_leaves_too_little_wall_and_says_so():
    """A 13.5 mm inscribed cutout (circumradius 13.977) leaves 0.923 mm: S-C3."""
    spec = build_spec(cylinder={**V1_CYLINDER, 'polygonal_cutout_radius_mm': 13.5})
    assert 'seam_channel' not in spec['cylinder']
    assert spec['warnings'] == [WALL_WARNING]


def test_the_wall_rule_reads_the_polygon_not_the_inscribed_radius():
    """
    The thinnest wall is at the polygon's VERTICES. A 13.25 mm inscribed
    12-gon has a 13.717 circumradius: 15.4 - 0.5 - 13.717 = 1.183, under 1.2,
    although 15.4 - 0.5 - 13.25 = 1.65 would have passed.
    """
    spec = build_spec(cylinder={**V1_CYLINDER, 'polygonal_cutout_radius_mm': 13.25})
    assert 'seam_channel' not in spec['cylinder']
    assert spec['warnings'] == [WALL_WARNING]


def test_no_cutout_means_the_wall_thickness_tube():
    """
    Without a polygon the worker hollows by wall thickness: 2.0 - 0.5 = 1.5 mm
    fits, 1.5 - 0.5 = 1.0 mm does not. A missing thickness field means 2 mm.
    """
    no_cutout = {'diameter': 30.8, 'height': 52.0, 'seam_offset_deg': 0.0}
    assert 'seam_channel' in build_spec(cylinder={**no_cutout, 'wall_thickness': 2.0})['cylinder']
    assert 'seam_channel' in build_spec(cylinder=no_cutout)['cylinder']
    thin = build_spec(cylinder={**no_cutout, 'wall_thickness': 1.5})
    assert 'seam_channel' not in thin['cylinder']
    assert thin['warnings'] == [WALL_WARNING]


def test_solid_barrels_skip_the_wall_rule():
    """
    Gear mode and Version 2 force the barrel solid, so there is no bore to keep
    a wall from. 13 cells: the most a 90 mm card holds in tactile mode, so no
    card-fit warning joins the (empty) list.
    """
    lines = [FULL_CELL * 13] * 4
    tactile = {'grid_columns': 13, 'indicator_mode': 'tactile'}
    thin = {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 1.0, 'seam_offset_deg': 0.0}

    geared = build_spec('positive', {**tactile, 'gear_rollers_enabled': 1}, cylinder=thin, lines=lines)
    assert 'gears' in geared
    assert 'seam_channel' in geared['cylinder']
    assert geared['warnings'] == []

    v2 = build_spec('positive', {**tactile, 'embosser_version': 2}, cylinder={**thin, 'height': 54.0}, lines=lines)
    assert v2['cylinder']['solid'] is True
    assert 'seam_channel' in v2['cylinder']
    assert v2['warnings'] == []


# ---------------------------------------------------------------------------
# 3. Off, and byte-identity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('off_value', [0, '0', 0.0, False])
@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_the_switch_off_removes_the_key_and_nothing_else(plate_type, off_value):
    on = build_spec(plate_type)
    off = build_spec(plate_type, {'seam_channel_enabled': off_value})
    assert 'seam_channel' not in off['cylinder']
    assert 'seam_channel' not in json.dumps(off)

    expected = copy.deepcopy(on)
    del expected['cylinder']['seam_channel']
    assert off == expected


@pytest.mark.parametrize('on_value', [1, '1', 1.0, '', None])
def test_absent_or_blank_means_on(on_value):
    settings = {} if on_value is None else {'seam_channel_enabled': on_value}
    assert 'seam_channel' in build_spec('positive', settings)['cylinder']


def test_an_omitted_channel_leaves_only_its_warning_behind():
    """Left out for fit, the spec is the off-switch spec plus one warning."""
    narrow = {**V1_CYLINDER, 'polygonal_cutout_radius_mm': 13.5}
    omitted = build_spec(cylinder=narrow)
    off = build_spec(settings={'seam_channel_enabled': 0}, cylinder=narrow)
    assert omitted['warnings'] == [WALL_WARNING]
    expected = copy.deepcopy(omitted)
    expected['warnings'] = []
    assert off == expected


def test_the_browser_request_gets_the_channel_over_the_route(client):
    """
    The exact request body the browser sent for the pre-channel e2e fixture
    (tests/e2e/fixtures) now comes back with the channel at 178.33 degrees;
    with seam_channel_enabled: 0 the response carries no such key.
    """
    fixture = (
        Path(__file__).resolve().parent / 'e2e' / 'fixtures' / 'embossing_0.4_abc_before_seam_channel.request.json'
    )
    payload = json.loads(fixture.read_text(encoding='utf-8'))

    on = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert on.status_code == 200, on.data
    block = on.get_json()['cylinder']['seam_channel']
    assert math.degrees(block['theta']) == pytest.approx(178.326, abs=0.005)

    off_payload = copy.deepcopy(payload)
    off_payload['settings']['seam_channel_enabled'] = 0
    off = client.post('/geometry_spec', json=off_payload, headers={'Content-Type': 'application/json'})
    assert off.status_code == 200, off.data
    assert 'seam_channel' not in off.get_json()['cylinder']
    assert 'seam_channel' not in off.get_data(as_text=True)


def test_cards_never_get_a_channel(client):
    payload = {
        'lines': ['⠁⠃⠉', '', '', ''],
        'grade': 'g2',
        'plate_type': 'positive',
        'shape_type': 'card',
        'settings': {'grid_columns': 12, 'grid_rows': 4},
    }
    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert response.status_code == 200, response.data
    assert 'seam_channel' not in response.get_data(as_text=True)
