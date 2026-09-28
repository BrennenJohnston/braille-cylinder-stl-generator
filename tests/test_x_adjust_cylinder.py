"""
X Adjust on cylinders (2026-09-27).

Until this date the cylinder spec builder never read `braille_x_adjust`: the
dial was sent, validated and stored, then ignored (Y Adjust worked). Now the
whole text grid slides round the barrel by the dial's value in mm of arc, in
the card frame both plates share, so:

  * every grid feature moves - front dots, back dots, their paired recesses and
    the visual markers - by the same arc on both cylinders, and a pair still
    meets at theta and -theta;
  * the tactile arrows, the tactile groove and the Version 2 keys stay put;
  * negative brings the FIRST cell toward the alignment arrow on both plates
    (Cylinder A's grid moves left and Cylinder B's right as the preview's
    default camera shows them), which is what Brennen asked for after his
    2026-09-27 print: the front's first cell sat too far from the card's
    leading edge and its last cell ran off the card;
  * the room rules follow the shift: the tactile arrow-gap rule, the seam
    channel's window (visual) and first/last-cell room (tactile), and the
    card-fit need;
  * at 0 - the default - nothing changes at all.
"""

import copy
import math
import re
from pathlib import Path

import pytest

from app import geometry_spec
from app.geometry_spec import extract_cylinder_geometry_spec
from app.models import CardSettings
from app.utils import braille_to_dots

REPO = Path(__file__).resolve().parents[1]
RADIUS = 15.4
V2_CYLINDER = {'diameter_mm': 30.8, 'height_mm': 54.0, 'seam_offset_deg': 0.0}
V1_CYLINDER = {
    'diameter_mm': 30.8,
    'height_mm': 52.0,
    'wall_thickness': 2.0,
    'seam_offset_deg': 0.0,
    'polygonal_cutout_radius_mm': 13.0,
    'polygonal_cutout_sides': 12,
}
FRONT = ['⠁⠃⠉']  # abc
BACK = ['⠭⠽⠵']  # xyz
FULL_ROW = ['⠿' * 13] * 4

S_C5 = (
    'The seam channel was left out: there is not enough room for it beside the alignment arrows. '
    'Reduce the number of braille cells, increase the cylinder diameter, or narrow the indicator.'
)


def tactile_pair_settings(x_adjust=0.0, **overrides):
    fields = {
        'indicator_mode': 'tactile',
        'embosser_version': 2,
        'double_sided_enabled': 1,
        'grid_columns': 13,
        'braille_x_adjust': x_adjust,
    }
    fields.update(overrides)
    return CardSettings(**fields)


def tactile_pair(plate, x_adjust=0.0, lines=FRONT, back_lines=BACK, **overrides):
    return extract_cylinder_geometry_spec(
        lines,
        'g2',
        tactile_pair_settings(x_adjust, **overrides),
        dict(V2_CYLINDER),
        ['abc'],
        plate,
        braille_to_dots,
        back_lines=back_lines,
    )


def visual_plate(plate, x_adjust=0.0, **overrides):
    fields = {'indicator_mode': 'visual', 'grid_columns': 15, 'braille_x_adjust': x_adjust}
    fields.update(overrides)
    return extract_cylinder_geometry_spec(
        FRONT, 'g2', CardSettings(**fields), dict(V1_CYLINDER), ['abc'], plate, braille_to_dots
    )


def arc_from_arrow_in_the_stl(theta):
    """
    Signed arc (mm) from the arrow column in the exported STL's frame. The worker
    places every feature at -theta; the arrow is at pi; positive is what the
    preview's default camera shows to the RIGHT.
    """
    world = -theta
    return ((world - math.pi + math.pi) % (2 * math.pi) - math.pi) * RADIUS


@pytest.mark.parametrize('plate', ['positive', 'negative'])
def test_zero_and_an_absent_field_both_leave_the_spec_as_it_was(plate):
    settings = tactile_pair_settings(0.0)
    absent = copy.copy(settings)
    del absent.braille_x_adjust
    assert not hasattr(absent, 'braille_x_adjust')
    with_zero = extract_cylinder_geometry_spec(
        FRONT, 'g2', settings, dict(V2_CYLINDER), ['abc'], plate, braille_to_dots, back_lines=BACK
    )
    with_absent = extract_cylinder_geometry_spec(
        FRONT, 'g2', absent, dict(V2_CYLINDER), ['abc'], plate, braille_to_dots, back_lines=BACK
    )
    assert with_zero == with_absent


@pytest.mark.parametrize(('plate', 'sign'), [('positive', -1), ('negative', +1)])
def test_every_grid_feature_slides_by_the_dial_and_nothing_else_moves(plate, sign):
    """
    In spec theta Cylinder A's features move by -shift/R and Cylinder B's by
    +shift/R (the two seam mappings are each other's negation), front dots and
    back recesses alike; the arrows and the tactile groove do not move.
    """
    before = tactile_pair(plate, 0.0)
    after = tactile_pair(plate, -3.0)
    assert len(after['dots']) == len(before['dots']) == 18
    for old, new in zip(before['dots'], after['dots']):
        assert old['is_recess'] == new['is_recess']
        assert (new['theta'] - old['theta']) * RADIUS == pytest.approx(sign * -3.0, abs=1e-9)
        assert new['y'] == old['y']
        assert math.hypot(new['x'], new['z']) == pytest.approx(math.hypot(old['x'], old['z']), abs=1e-9)
    assert [m['theta'] for m in after['markers']] == [m['theta'] for m in before['markers']]
    assert after['markers'][0]['theta'] == geometry_spec.TACTILE_SEAM_THETA
    assert after['cylinder']['seam_channel']['theta'] == before['cylinder']['seam_channel']['theta']
    assert after['cylinder']['seam_channel'].get('path') == before['cylinder']['seam_channel'].get('path')
    assert after['keyed_cutouts'] == before['keyed_cutouts']


def test_the_pair_still_meets_at_theta_and_minus_theta():
    a = tactile_pair('positive', -3.0)['dots']
    b = tactile_pair('negative', -3.0)['dots']
    assert len(a) == len(b)
    for dot_a, dot_b in zip(a, b):
        assert dot_a['theta'] == pytest.approx(-dot_b['theta'], abs=1e-12)
        assert dot_a['y'] == dot_b['y']
        assert dot_a['is_recess'] != dot_b['is_recess']


def test_negative_brings_the_first_cell_toward_the_arrow_on_both_plates():
    """
    Brennen's ask (2026-09-27): a negative X moves Cylinder A's dots and
    recesses LEFT and Cylinder B's RIGHT as the default camera shows them, so
    the first cell of the front text starts nearer the alignment arrow on both
    cylinders. Front text is column 0..2, so its nearest feature to the arrow is
    the first cell's leading dot column.
    """
    for plate, front_is_recess in (('positive', False), ('negative', True)):
        before = [
            arc_from_arrow_in_the_stl(d['theta'])
            for d in tactile_pair(plate, 0.0)['dots']
            if d['is_recess'] == front_is_recess
        ]
        after = [
            arc_from_arrow_in_the_stl(d['theta'])
            for d in tactile_pair(plate, -3.0)['dots']
            if d['is_recess'] == front_is_recess
        ]
        assert len(before) == len(after) == 5  # a b c = 1 + 2 + 2 dots
        # Every front feature moved 3 mm the same way: left on A, right on B.
        shifts = {round(new - old, 9) for old, new in zip(before, after)}
        assert shifts == {-3.0 if plate == 'positive' else 3.0}
        # And that way is toward the arrow: the leading dot column of cell 0
        # sits gap/2 - dot_spacing/2 = 8.127 mm out at 0 and 5.127 mm at -3.
        nearest_before = min(before, key=abs)
        nearest_after = min(after, key=abs)
        assert abs(nearest_before) == pytest.approx(math.pi * 15.4 - 39.0 - 1.25, abs=1e-6)
        assert abs(nearest_after) == pytest.approx(abs(nearest_before) - 3.0, abs=1e-6)
        assert (nearest_before > 0) == (plate == 'positive')


@pytest.mark.parametrize(('plate', 'sign'), [('positive', -1), ('negative', +1)])
def test_visual_mode_moves_the_markers_and_the_groove_with_the_grid(plate, sign):
    before = visual_plate(plate, 0.0)
    after = visual_plate(plate, -3.0)
    for old, new in zip(before['markers'], after['markers']):
        assert old['type'] == new['type']
        assert (new['theta'] - old['theta']) * RADIUS == pytest.approx(sign * -3.0, abs=1e-9)
    for old, new in zip(before['dots'], after['dots']):
        assert (new['theta'] - old['theta']) * RADIUS == pytest.approx(sign * -3.0, abs=1e-9)
    # The groove keeps its window: it slides with the grid, so its margins to
    # the last cell's dots and column 0's triangle are exactly what they were.
    old_channel = before['cylinder']['seam_channel']['theta']
    new_channel = after['cylinder']['seam_channel']['theta']
    assert (new_channel - old_channel) * RADIUS == pytest.approx(sign * -3.0, abs=1e-9)


def test_the_tactile_seam_channel_needs_room_on_the_side_the_shift_crowds():
    """
    13 tactile cells on the 30.8 barrel: gap/2 is 9.377 mm and the schema dot
    families give a 2.25 mm footprint, so the first-cell side has 7.127 mm
    against the detour's 3.5 mm need. A shift of -3 leaves 4.127 (kept), -4
    leaves 3.127 (left out, S-C5, on BOTH plates); +9 crowds the last-cell
    side past the straight groove's 0.75 mm (left out too).
    """
    for plate in ('positive', 'negative'):
        assert 'seam_channel' in tactile_pair(plate, 0.0, double_sided_enabled=0)['cylinder']
        assert 'seam_channel' in tactile_pair(plate, -3.0, double_sided_enabled=0)['cylinder']
        crowded = tactile_pair(plate, -4.0, double_sided_enabled=0)
        assert 'seam_channel' not in crowded['cylinder']
        assert S_C5 in crowded['warnings']
        other_side = tactile_pair(plate, 9.0, double_sided_enabled=0)
        assert 'seam_channel' not in other_side['cylinder']
        assert S_C5 in other_side['warnings']


def test_the_arrow_gap_rule_reads_the_gap_left_after_the_shift():
    """13 cells leave 18.75 mm; the arrow needs 9.0. A 5 mm shift leaves 8.75 on the crowded side's terms."""
    quiet = tactile_pair('positive', 0.0, double_sided_enabled=0)
    assert not any(w.startswith('Tactile indicator needs a seam gap') for w in quiet['warnings'])
    crowded = tactile_pair('positive', -5.0, double_sided_enabled=0)
    gap_warnings = [w for w in crowded['warnings'] if w.startswith('Tactile indicator needs a seam gap')]
    assert len(gap_warnings) == 1
    assert 'at least 9.0 mm; this layout leaves 8.8 mm' in gap_warnings[0]


def test_the_card_need_moves_with_the_first_cell():
    settings = tactile_pair_settings(0.0, double_sided_enabled=0)
    grid_width = 12 * 6.5
    gap = math.pi * 30.8 - grid_width
    need0 = geometry_spec.tactile_card_need_mm(settings, False, grid_width, gap)
    need3 = geometry_spec.tactile_card_need_mm(settings, False, grid_width, gap, -3.0)
    assert need3 == pytest.approx(need0 - 3.0)
    assert geometry_spec.tactile_max_cells(settings, False, 90.0, 30.8, -3.0) >= geometry_spec.tactile_max_cells(
        settings, False, 90.0, 30.8
    )
    # 14 tactile cells need 92.8 mm of a 90 mm card at 0 (S-T1 warns) and
    # 89.8 at -3 (it fits).
    fourteen = tactile_pair_settings(0.0, double_sided_enabled=0, grid_columns=14)
    at_zero = extract_cylinder_geometry_spec(
        FULL_ROW, 'g2', fourteen, dict(V2_CYLINDER), ['abc'], 'positive', braille_to_dots
    )
    assert any(w.startswith('The last braille cell would run off the card') for w in at_zero['warnings'])
    fourteen.braille_x_adjust = -3.0
    shifted = extract_cylinder_geometry_spec(
        FULL_ROW, 'g2', fourteen, dict(V2_CYLINDER), ['abc'], 'positive', braille_to_dots
    )
    assert not any(w.startswith('The last braille cell would run off the card') for w in shifted['warnings'])


def test_the_live_ui_rules_read_the_dial_too():
    """
    The three live boxes mirror the server's rules, so each must read the dial
    the server reads: a rule the page computes without the shift would tell the
    user one thing before Generate and the server another after.
    """
    html = (REPO / 'public' / 'index.html').read_text(encoding='utf-8')
    for name in ('updateSeamChannelUI', 'updateCardFitUI', 'checkPhysicalFitNow'):
        body = re.search(rf'function {name}\(\) \{{(.*?)\n        \}}', html, re.S)
        assert body, name
        assert "getElementById('braille_x_adjust')" in body.group(1), f'{name} does not read X Adjust'
