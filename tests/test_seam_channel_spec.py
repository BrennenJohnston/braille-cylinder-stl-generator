"""
What app/geometry_spec.py emits for the slicer seam channel (2026-09-20 programme, phase A2).

The channel is a shallow V-groove cut the full height of the barrel's outer
surface, inside the seam gap beside the row-indicator column, so a slicer's
"aligned" seam mode hides every layer's seam there instead of in a dot. These
tests read the dict the worker acts on; they need no mesh library.

  1. Placement: the groove sits in the middle of the free window between the
     features either side of the seam gap, and the two plates mirror exactly.
     In tactile mode it runs down the arrow column, and on the embossing plate
     it steps round every raised arrow on the first-cell side (D-T8).
  2. Fit: the groove is left out, with a warning, when the window - in
     tactile mode, the first-cell side of the arrow column - is narrower than
     the groove plus its margins, or when the wall under it would be thinner
     than the FDM minimum.
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


def detour_of(spec):
    """The embossing plate's groove centre line as (x, z): x across the arrow column, negative toward the first cell."""
    radius = spec['cylinder']['radius']
    return [(radius * math.sin(point['theta'] - math.pi), point['z']) for point in channel_of(spec)['path']]


def arrow_outline(arrow):
    """A raised arrow's outline in its tangent plane, grown by its outline_delta as the worker's mitre grows it."""
    half, length, delta = arrow['width'] / 2.0, arrow['length'], arrow['outline_delta']
    half_base = half + delta * (math.hypot(half, length) + half) / length
    tip = length / 2.0 + delta / math.sin(math.atan2(half, length))
    return [
        (-half_base, arrow['y'] - length / 2.0 - delta),
        (half_base, arrow['y'] - length / 2.0 - delta),
        (0.0, arrow['y'] + tip),
    ]


def distance_to_segment(p, a, b):
    ax, az = a
    dx, dz = b[0] - ax, b[1] - az
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(p[0] - ax - t * dx, p[1] - az - t * dz)


def closest_approach(line, outline):
    """Smallest distance between a polyline and a triangle's edges, walked in 2 um steps."""
    edges = list(zip(outline, outline[1:] + outline[:1]))
    closest = math.inf
    for a, b in zip(line, line[1:]):
        steps = max(1, math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.002))
        for k in range(steps + 1):
            p = (a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps)
            closest = min(closest, min(distance_to_segment(p, *edge) for edge in edges))
    return closest


def test_tactile_14_columns_worked_numbers():
    """
    Tactile mode since D-T6 / D-T7 / D-T8: the groove runs down the arrow
    column itself - 180 degrees on both plates, the arrow's own angle - the
    full height, and on the embossing plate it steps round the raised arrows
    on the first-cell side instead of cutting through them. 4 rows on 10 mm
    spacing put the 4 x 10 mm arrows at +/-15 and +/-5 mm, a chain touching
    tip to base from -20 to +20. The centre line keeps 0.75 mm (half the
    groove and its 0.25 margin) from the arrows and slants at 45 degrees: it
    leaves the centre 3.061 mm below the bottom base, rounds each base corner
    2.75 mm out, runs up each side, zig-zags out to the next corner 1.15 mm
    short of each join, and is back on the centre 1.061 mm above the top tip.
    The counter plate's recesses are deeper than the groove, so its groove
    stays straight.
    """
    tactile = {'grid_columns': 14, 'indicator_mode': 'tactile'}
    lines = [FULL_CELL * 14] * 4
    a = build_spec('positive', tactile, lines=lines)
    b = channel_of(build_spec('negative', tactile, lines=lines))
    assert channel_of(a)['theta'] == pytest.approx(math.pi) and b['theta'] == pytest.approx(math.pi)
    assert set(channel_of(a)) == {'theta', 'width', 'depth', 'overshoot', 'lip', 'path'}
    assert set(b) == {'theta', 'width', 'depth', 'overshoot', 'lip'}

    line = detour_of(a)
    assert line[0] == (0.0, -27.0) and line[-1] == (0.0, 27.0)
    centred = [z for x, z in line if x == 0.0]
    assert max(z for z in centred if z < 0) == pytest.approx(-23.061, abs=1e-3)
    assert min(z for z in centred if z > 0) == pytest.approx(21.061, abs=1e-3)
    assert min(x for x, _ in line) == pytest.approx(-2.75, abs=0.01)
    joins = [x for x, z in line if any(abs(z - (join - 1.913)) < 1e-3 for join in (-10.0, 0.0, 10.0))]
    assert joins == pytest.approx([-1.147] * 3, abs=1e-3)


@pytest.mark.parametrize(
    'settings, cylinder',
    [
        ({'grid_columns': 13}, None),
        ({'grid_columns': 14}, None),
        ({'grid_columns': 12, 'tactile_indicator_layout': 'three_spaced'}, None),
        ({'grid_columns': 13, 'gear_rollers_enabled': 1}, None),
        ({'grid_columns': 13, 'embosser_version': 2}, {**V1_CYLINDER, 'height': 54.0}),
        ({'grid_columns': 13, 'tactile_indicator_length': 15.0}, None),
        ({'grid_columns': 13, 'tactile_indicator_width': 10.0, 'tactile_indicator_length': 3.0}, None),
        ({'grid_columns': 13}, {'diameter': 30.8, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}),
        ({**DS_04, 'grid_columns': 14}, None),
    ],
    ids=[
        'per-row13',
        'per-row14',
        'three-spaced',
        'gears',
        'version2',
        'overlapping-arrows',
        'short-wide-arrows',
        'barrel-40mm',
        'double-sided14',
    ],
)
def test_the_detour_clears_every_raised_arrow(settings, cylinder):
    """
    From the emitted markers, not the formula: on every tactile layout the
    embossing plate's groove centre line keeps half the groove plus its margin
    from every raised arrow's outline (grown by the gear weld where there is
    one), stays on the first-cell side, never slants more than 45 degrees,
    and runs from the overshoot below the bottom face to the overshoot above
    the top one. (Where the chain reaches an end face, as on the 40 mm barrel,
    the groove leaves that face already stepping round the end arrow.)
    """
    back = BACK_LINES if settings.get('double_sided_enabled') else None
    spec = build_spec('positive', {'indicator_mode': 'tactile', **settings}, cylinder, [FULL_CELL * 14] * 4, back)
    line = detour_of(spec)
    end = spec['cylinder']['height'] / 2.0 + geometry_spec.SEAM_CHANNEL_OVERSHOOT_MM
    assert (line[0][1], line[-1][1]) == pytest.approx((-end, end))
    assert all(z1 > z0 for (_, z0), (_, z1) in zip(line, line[1:]))
    assert all(x <= 0.0 for x, _ in line)
    slant = math.tan(math.radians(geometry_spec.SEAM_CHANNEL_DETOUR_SLANT_DEG))
    assert all(abs(x1 - x0) <= slant * (z1 - z0) + 1e-9 for (x0, z0), (x1, z1) in zip(line, line[1:]))

    clear = geometry_spec.SEAM_CHANNEL_WIDTH_MM / 2.0 + geometry_spec.SEAM_CHANNEL_MARGIN_MM
    arrows = [m for m in spec['markers'] if m['type'] == 'cylinder_tactile_arrow']
    assert arrows and not any(arrow['is_recess'] for arrow in arrows)
    for arrow in arrows:
        assert closest_approach(line, arrow_outline(arrow)) >= clear - 1e-6, (
            f'the groove crowds the arrow at {arrow["y"]}'
        )


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
    groove's centre line, on both plates and in every layout - including the
    embossing plate's detour round the tactile arrows, measured along it.
    """
    back = BACK_LINES if settings.get('double_sided_enabled') else None
    spec = build_spec(plate_type, settings, lines=lines, back_lines=back)
    radius = spec['cylinder']['radius']
    channel = channel_of(spec)
    theta_c = channel['theta']
    clear = geometry_spec.SEAM_CHANNEL_WIDTH_MM / 2.0 + geometry_spec.SEAM_CHANNEL_MARGIN_MM
    # Arc along the surface from the column, and height: the detour's own
    # points, or the straight groove's two ends.
    if 'path' in channel:
        groove = [(radius * (point['theta'] - theta_c), point['z']) for point in channel['path']]
    else:
        groove = [(0.0, -spec['cylinder']['height']), (0.0, spec['cylinder']['height'])]

    assert spec['dots'], 'the layout must put dots on the plate for this to prove anything'
    for dot in spec['dots']:
        params = dot['params']
        feature_radius = params.get('bowl_radius') or params.get('recess_radius') or params.get('base_radius')
        arc = radius * ((dot['theta'] - theta_c + math.pi) % (2 * math.pi) - math.pi)
        gap = min(distance_to_segment((arc, dot['y']), a, b) for a, b in zip(groove, groove[1:]))
        assert gap - feature_radius >= clear - 1e-9, f'dot at {math.degrees(dot["theta"]):.2f} deg crowds the groove'

    for marker in spec['markers']:
        arc = radius * angular_distance(marker['theta'], theta_c)
        if marker['type'] == 'cylinder_tactile_arrow':
            # Tactile mode: the groove shares the arrow's column and steps
            # round the raised arrows - test_the_detour_clears_every_raised_arrow.
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


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_tactile_15_columns_has_no_room_for_the_detour(plate_type):
    """
    D-T8: the embossing plate's groove steps round the arrows on the
    first-cell side, which needs half an arrow + the groove + a margin either
    side of it = 3.5 mm before the first cell's dots. 15 columns leave 5.761 mm
    of gap - 0.731 mm from the column to the dots, the arrows themselves
    already overlap them and the signed tactile-gap warning speaks - so both
    plates leave the groove out and say so with S-C2, the visual-mode sentence.
    """
    spec = build_spec(plate_type, {'grid_columns': 15, 'indicator_mode': 'tactile'}, lines=[FULL_CELL * 15] * 4)
    assert 'seam_channel' not in spec['cylinder']
    assert GAP_WARNING in spec['warnings']
    assert any(w.startswith('Tactile indicator needs a seam gap') for w in spec['warnings'])


def test_the_tactile_room_rule_worked_numbers():
    """
    The first-cell side's room is gap/2 - footprint, against arrow width/2 +
    1.0 + 2 x 0.25. 14 cells at 30.8 mm leave 3.981 mm: room for the 3.5 mm a
    4 mm arrow needs, not for the 4.1 mm a 5.2 mm one does. 30.4 mm leaves
    14 cells only 3.352 mm.
    """
    tactile = {'grid_columns': 14, 'indicator_mode': 'tactile'}
    lines = [FULL_CELL * 14] * 4
    assert 'seam_channel' in build_spec('positive', tactile, lines=lines)['cylinder']
    wide = build_spec('positive', {**tactile, 'tactile_indicator_width': 5.2}, lines=lines)
    assert 'seam_channel' not in wide['cylinder'] and GAP_WARNING in wide['warnings']
    narrow = build_spec('negative', tactile, cylinder={**V1_CYLINDER, 'diameter': 30.4}, lines=lines)
    assert 'seam_channel' not in narrow['cylinder'] and GAP_WARNING in narrow['warnings']


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
