"""
Interpoint (double-sided) math and geometry-spec tests.

These are the numbers the double-sided beta stands on. If the mirror, the
offset, or the footprint sizes are wrong, they are wrong here — before any
settings, worker or UI code is written.

Reference values come from the approved 2026-08-16 interpoint research
(clearance_check.py and 01_RESEARCH_FINDINGS.md); the tolerance is +/-0.001 mm.

The second half of the file tests app/geometry_spec.py rather than the math
module: that the double-sided toggle builds the paired A/B cylinders, and — the
hard constraint of the whole beta — that with the toggle off the spec is
byte-identical to the one the code produced before double-sided mode existed.
"""

import json
import math

import pytest

from app.geometry import interpoint as ip
from app.geometry_spec import extract_cylinder_geometry_spec
from app.models import CardSettings
from app.utils import braille_to_dots

# Repo dot map, dots 1-6 as [row, col]; see app/geometry_spec.py. Never reordered.
DOT_POSITIONS = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

# The male-male sweep is narrowed from the research's +/-0.30 rad to +/-0.12 at
# the same 0.005 rad step: the closest approach happens at tau = 0, dead centre
# of the nip, and the distance climbs away from it in both directions, so the
# narrower band finds the same minimum in a third of the time.
MALE_MALE_TAU_LIMIT = 0.12
MALE_MALE_TAU_SAMPLES = 49


def _three_cell_front_dots(patterns=((0,), (0, 1), (0, 3)), radius=ip.CYLINDER_RADIUS_MM):
    """
    Raised dots for a three-cell braille pattern, positioned the way
    app/geometry_spec.py positions them on an embossing cylinder.

    `patterns` gives the raised dot indices (0-5) of each cell.
    """
    grid_angle = (len(patterns) - 1) * ip.CELL_PITCH_MM / radius
    start_angle = -grid_angle / 2
    cell_angle = ip.CELL_PITCH_MM / radius
    dot_angle = ip.DOT_PITCH_MM / radius
    col_offsets = [-dot_angle / 2, dot_angle / 2]
    row_offsets = [ip.DOT_PITCH_MM, 0.0, -ip.DOT_PITCH_MM]

    dots = []
    for col, pattern in enumerate(patterns):
        cell_raw_angle = start_angle + col * cell_angle
        for dot_index in pattern:
            row_off_idx, col_off_idx = DOT_POSITIONS[dot_index]
            # apply_seam() on the embossing plate: planar angle -> theta = -angle
            theta = -(cell_raw_angle + col_offsets[col_off_idx])
            dots.append(
                {
                    'theta': theta,
                    'y': row_offsets[row_off_idx],
                    'x': radius * math.cos(theta),
                    'z': radius * math.sin(theta),
                    'radius': radius,
                }
            )
    return dots


# -----------------------------------------------------------------------------
# Same-surface crowding: the feasibility crux
# -----------------------------------------------------------------------------


def test_option_b_leaves_printable_material_between_neighbours():
    """Option B (dot 1.2 + bowl 1.3) is the signed-off double-sided footprint."""
    gap = ip.same_surface_min_gap(1.2, 1.3)
    assert gap == pytest.approx(0.518, abs=0.001)
    assert gap >= ip.SAME_SURFACE_GAP_RELIABLE_MM


def test_shipped_footprints_are_below_the_printable_floor():
    """Why double-sided mode needs its own sizes: today's 0.4 preset does not fit."""
    gap = ip.same_surface_min_gap(1.5, 1.8)
    assert gap == pytest.approx(0.118, abs=0.001)
    assert gap < ip.SAME_SURFACE_GAP_FLOOR_MM


def test_legacy_cone_footprints_overlap():
    """A 1.8 dot beside a 1.8 bowl has no material between them at all."""
    gap = ip.same_surface_min_gap(1.8, 1.8)
    assert gap == pytest.approx(-0.032, abs=0.001)
    assert gap < 0


def test_diagonal_offset_maximises_front_to_back_distance():
    """The 1.25/1.25 diagonal buys 1.768 mm; shifting around the cylinder only buys 1.250."""
    assert ip.lattice_min_center_distance(1.25, 1.25) == pytest.approx(1.76777, abs=0.001)
    assert ip.lattice_min_center_distance(1.25, 0.0) == pytest.approx(1.250, abs=0.001)
    assert ip.lattice_min_center_distance(0.0, 1.25) == pytest.approx(1.250, abs=0.001)


def test_worst_case_lattice_is_every_dot_of_every_cell():
    assert len(ip.lattice_points()) == ip.TACTILE_COLUMNS * ip.GRID_ROWS * 6 == 336


# -----------------------------------------------------------------------------
# The mirror and the pairing
# -----------------------------------------------------------------------------


def test_mirror_fixes_the_grid_centre_and_the_seam_arrow():
    """theta -> -theta holds 0 and pi still; pi is where the tactile arrow sits."""
    assert ip.mirror_theta(0.0) == 0.0
    assert math.cos(ip.mirror_theta(math.pi)) == pytest.approx(math.cos(math.pi), abs=1e-12)
    assert math.sin(ip.mirror_theta(math.pi)) == pytest.approx(math.sin(math.pi), abs=1e-12)


def test_back_grid_transform_mirrors_then_shifts():
    assert ip.back_grid_transform(0.0, 0.0) == (1.25, 1.25)
    assert ip.back_grid_transform(0.0, 0.0, direction=-1) == (-1.25, -1.25)
    # With the interpoint step removed, all that is left is the mirror.
    assert ip.back_grid_transform(7.5, 3.0, offset_x=0.0, offset_z=0.0) == (-7.5, 3.0)


def test_default_direction_crowds_the_left_of_cylinder_a_s_arrow():
    """
    D3 as signed off: the back grid crowds the LEFT of Cylinder A's seam arrow,
    seen from outside the cylinder with its top upward.

    If this fails, BACK_GRID_DIRECTION was flipped. That is a physical
    orientation choice no clearance number can check - confirm it against a
    printed cylinder before accepting the new sign.
    """
    report = ip.arrow_zone_margins()
    assert report['direction'] == ip.BACK_GRID_DIRECTION
    assert report['tight_side_of_arrow_on_a'] == 'left'


def test_back_grid_transform_rejects_a_direction_that_is_not_a_sign():
    with pytest.raises(ValueError):
        ip.back_grid_transform(0.0, 0.0, direction=0)


def test_back_grid_never_lands_on_a_front_feature():
    """Every back position stays the full diagonal away from the front dot it mirrors."""
    for x_mm, z_mm in ip.lattice_points(cols=3, rows=2):
        back_x, back_z = ip.back_grid_transform(x_mm, z_mm)
        assert math.hypot(back_x - (-x_mm), back_z - z_mm) == pytest.approx(math.hypot(1.25, 1.25), abs=1e-12)


def test_pairing_map_is_exact_for_a_three_cell_pattern():
    """
    Every raised dot meets a recess at exactly -theta on the opposite cylinder,
    same height. Positions must agree to 1e-9 mm.
    """
    front_dots = _three_cell_front_dots()
    pairs = ip.pairing_map(front_dots)
    assert len(pairs) == len(front_dots) == 5

    for dot, recess in pairs:
        # Exact, not approximate: the mirror is a sign flip, nothing more.
        assert recess['theta'] == -dot['theta']
        assert recess['y'] == dot['y']
        assert recess['radius'] == dot['radius']
        # Mirroring the angle mirrors the position across the seam plane: the
        # same x on the cylinder, the opposite z.
        assert recess['x'] == pytest.approx(dot['x'], abs=1e-9)
        assert recess['z'] == pytest.approx(-dot['z'], abs=1e-9)
        assert recess['x'] == pytest.approx(dot['radius'] * math.cos(-dot['theta']), abs=1e-9)
        assert recess['z'] == pytest.approx(dot['radius'] * math.sin(-dot['theta']), abs=1e-9)


def test_pairing_map_takes_plain_angle_height_pairs():
    pairs = ip.pairing_map([(0.4, 2.0), (math.pi, -2.0)])
    assert [recess['theta'] for _, recess in pairs] == [-0.4, -math.pi]
    assert [recess['y'] for _, recess in pairs] == [2.0, -2.0]
    assert 'x' not in pairs[0][1]


def test_pairing_map_rejects_a_dot_without_a_position():
    with pytest.raises(ValueError):
        ip.pairing_map([{'x': 1.0, 'z': 2.0}])


# -----------------------------------------------------------------------------
# The nip: what happens when the two cylinders roll together
# -----------------------------------------------------------------------------


def test_diagonal_offset_keeps_the_two_dies_apart_at_the_nip():
    """
    Metal-to-metal worst case (gap 0.0). The diagonal offset leaves 0.274 mm
    between a front dot on A and a back dot on B; offsetting around the cylinder
    only, with no axial step, collides.

    The paired figure from this call is not meaningful at gap 0.0 - the dot is
    taller than the bowl is deep, so it bottoms out - the male-male pair is what
    this case is for.
    """
    result = ip.nip_clearances(
        profile=ip.SHIPPED_PRESET_DOT_PROFILE,
        bowl_diameter=1.8,
        bowl_depth=0.8,
        gap=0.0,
        tau_limit=MALE_MALE_TAU_LIMIT,
        tau_samples=MALE_MALE_TAU_SAMPLES,
    )
    assert result['male_male_min_distance_mm'] >= 0.27
    assert result['male_male_axis_aligned_min_distance_mm'] <= 0.01


def test_paired_dot_and_bowl_reproduce_the_research_roll():
    """Shipped 0.4-preset dot into its 1.8 x 0.8 bowl, cylinders 0.35 mm apart."""
    result = ip.paired_nip_clearance(ip.SHIPPED_PRESET_DOT_PROFILE, 1.8, 0.8, 0.35)
    assert result.min_clearance_mm == pytest.approx(0.199, abs=0.001)
    assert result.max_dip_mm == pytest.approx(0.650, abs=0.001)


def test_option_b_dot_clears_its_bowl_by_at_least_a_tenth():
    """
    The signed-off requirement: a raised dot meets its recess with controllable
    clearance, never intersecting, adjustable down to 0.1 mm. Option B holds
    that from a 0.5 mm gap down to about 0.25 mm, and closing further does
    intersect - so the gap has a floor.
    """
    for gap in (0.5, 0.4, 0.35, 0.3):
        result = ip.paired_nip_clearance(ip.DS_DOT_PROFILE, ip.DS_BOWL_DIAMETER_MM, ip.DS_BOWL_DEPTH_MM, gap)
        assert result.min_clearance_mm >= 0.1, f'gap {gap} mm leaves only {result.min_clearance_mm:.3f} mm'
        assert result.max_dip_mm == pytest.approx(ip.DS_DOT_HEIGHT_MM - gap, abs=0.001)

    too_close = ip.paired_nip_clearance(ip.DS_DOT_PROFILE, ip.DS_BOWL_DIAMETER_MM, ip.DS_BOWL_DEPTH_MM, 0.1)
    assert too_close.min_clearance_mm < 0


# -----------------------------------------------------------------------------
# D3: which side of the seam arrow the back grid crowds
# -----------------------------------------------------------------------------


def test_d3_sign_variants_report_their_arrow_zone_margins():
    """
    Prints the arrow-zone margins for both D3 signs so the implemented sign can
    be checked against a physical part. Run with -s to see the table.

    Nothing about the margin sizes is asserted here on purpose: the two signs
    are mirror images, so they produce the same numbers on opposite sides of the
    arrow. What is asserted is exactly that - the sign chooses the side.
    """
    footprints = (
        ('shipped sizes (recess 1.8 / dot 1.5)', 1.8, 1.5),
        ('Option B (recess 1.3 / dot 1.2)', ip.DS_BOWL_DIAMETER_MM, ip.DS_DOT_BASE_DIAMETER_MM),
    )
    tight_sides = {}
    print()
    print('Arrow-zone margins, 14 columns, R = 15.375 mm, arrow 4.0 mm wide (recess outline +0.2 each side)')
    for direction in (-1, 1):
        for label, recess_on_a, dot_on_b in footprints:
            report = ip.arrow_zone_margins(direction, recess_on_a, dot_on_b)
            print(f'  direction {direction:+d}, {label}: seam gap {report["seam_gap_mm"]:.3f} mm')
            for side in report['sides']:
                print(
                    f'    theta on A {side["theta_on_a_deg"]:7.3f} deg '
                    f"({side['side_of_arrow_on_a']:>5s} of A's arrow): "
                    f'centre to arrow centre {side["centre_to_arrow_centre_mm"]:.3f} mm, '
                    f'recess edge on A {side["recess_edge_margin_on_a_mm"]:+.3f} mm, '
                    f'dot edge on B {side["dot_edge_margin_on_b_mm"]:+.3f} mm'
                )
            print(
                f'    tightest: {report["tight_margin_mm"]:+.3f} mm, '
                f"on the {report['tight_side_of_arrow_on_a']} of A's arrow"
            )
            tight_sides[(direction, label)] = report['tight_side_of_arrow_on_a']

    for label, _, _ in footprints:
        assert tight_sides[(-1, label)] != tight_sides[(1, label)]
    assert tight_sides[(1, footprints[0][0])] == 'left'


def test_arrow_zone_margins_reject_a_direction_that_is_not_a_sign():
    with pytest.raises(ValueError):
        ip.arrow_zone_margins(direction=2)


# -----------------------------------------------------------------------------
# app/geometry_spec.py: the paired A/B cylinders
# -----------------------------------------------------------------------------

# One small double-sided job, used by every test below. Tactile row indicators
# (double-sided mode allows nothing else) so all four grid columns hold text.
DS_CYLINDER_PARAMS = {'diameter': 30.75, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 355.0}
DS_SETTINGS = {'grid_rows': 2, 'grid_columns': 4, 'indicator_mode': 'tactile', 'double_sided_enabled': 1}
DS_FRONT_LINES = ['⠁⠃⠉', '⠊', '', '']  # 5 raised dots + 2
DS_BACK_LINES = ['⠑⠋', '', '', '']  # 5 raised dots


def _raised_dot_count(lines, max_cols):
    """Raised dots the geometry spec will emit for `lines`."""
    return sum(sum(braille_to_dots(char)) for line in lines for char in list(line.strip())[:max_cols])


def _double_sided_spec(plate_type, front=DS_FRONT_LINES, back=DS_BACK_LINES, **setting_overrides):
    settings = CardSettings(**{**DS_SETTINGS, **setting_overrides})
    return extract_cylinder_geometry_spec(
        front,
        'g1',
        settings,
        DS_CYLINDER_PARAMS,
        None,
        plate_type,
        braille_to_dots_func=braille_to_dots,
        back_lines=back,
    )


def test_double_sided_cylinder_a_carries_front_dots_and_back_recesses():
    """
    Cylinder A: one raised dot per front-text dot, one recess per BACK-text dot.

    The recesses are 1:1 with real back dots — a double-sided A is not a
    universal grid with extras bolted on.
    """
    spec = _double_sided_spec('positive')
    front_dots = _raised_dot_count(DS_FRONT_LINES, DS_SETTINGS['grid_columns'])
    back_dots = _raised_dot_count(DS_BACK_LINES, DS_SETTINGS['grid_columns'])
    assert (front_dots, back_dots) == (7, 5)

    males = [dot for dot in spec['dots'] if not dot['is_recess']]
    recesses = [dot for dot in spec['dots'] if dot['is_recess']]
    assert len(males) == front_dots
    assert len(recesses) == back_dots
    assert len(spec['dots']) == front_dots + back_dots


def test_double_sided_cylinder_b_carries_back_dots_and_no_universal_grid():
    """
    Cylinder B: raised dots for the back text, one recess per FRONT dot.

    The count is the point. Today's counter plate recesses every possible dot
    position (rows x columns x 6 = 96 here); in double-sided mode it must
    recess exactly the front dots that will actually arrive.
    """
    spec = _double_sided_spec('negative')
    front_dots = _raised_dot_count(DS_FRONT_LINES, DS_SETTINGS['grid_columns'])
    back_dots = _raised_dot_count(DS_BACK_LINES, DS_SETTINGS['grid_columns'])

    males = [dot for dot in spec['dots'] if not dot['is_recess']]
    recesses = [dot for dot in spec['dots'] if dot['is_recess']]
    assert len(males) == back_dots
    assert len(recesses) == front_dots

    universal_grid = DS_SETTINGS['grid_rows'] * DS_SETTINGS['grid_columns'] * 6
    assert universal_grid == 48
    assert len(spec['dots']) == front_dots + back_dots < universal_grid


def test_double_sided_plates_pair_dot_for_recess_through_pairing_map():
    """
    Every feature on A meets its opposite number on B at exactly -theta.

    Both plates emit front features first, then back, so the two dot lists line
    up index for index; `pairing_map` says where each one's partner has to be,
    and the answer must be exact, not approximate — a 0.1 mm nip clearance
    means nothing if the positions only agree to a rounding.
    """
    plate_a = _double_sided_spec('positive')
    plate_b = _double_sided_spec('negative')
    assert len(plate_a['dots']) == len(plate_b['dots'])

    for (dot_on_a, expected), dot_on_b in zip(ip.pairing_map(plate_a['dots']), plate_b['dots'], strict=True):
        assert dot_on_b['theta'] == expected['theta']
        assert dot_on_b['y'] == expected['y']
        assert dot_on_b['radius'] == expected['radius']
        assert dot_on_b['x'] == pytest.approx(expected['x'], abs=1e-9)
        assert dot_on_b['z'] == pytest.approx(expected['z'], abs=1e-9)
        # A raised dot is always met by a recess, never by another dot.
        assert dot_on_b['is_recess'] is not dot_on_a['is_recess']


def test_double_sided_front_dots_sit_where_single_sided_puts_them():
    """
    Double-sided mode moves nothing on the front face.

    Cylinder A's raised dots must land at the same angles and heights the
    single-sided embossing plate uses for the same text — only their footprint
    changes. This is what proves the paired-feature walk agrees with the
    untouched inline loop it was extracted from.
    """
    double_sided = _double_sided_spec('positive')
    single_sided = _double_sided_spec('positive', double_sided_enabled=0)

    males = [dot for dot in double_sided['dots'] if not dot['is_recess']]
    assert len(males) == len(single_sided['dots'])
    for ds_dot, single_dot in zip(males, single_sided['dots'], strict=True):
        assert ds_dot['theta'] == single_dot['theta']
        assert ds_dot['y'] == single_dot['y']


def test_back_features_sit_one_interpoint_step_from_the_front_ones():
    """
    The back grid is the front grid mirrored, then stepped diagonally.

    Feeding the same text to both faces makes the relationship visible: in the
    card frame (x = arc from the grid centre, z = height) every back feature
    lands at -x + 1.25, z + 1.25 from the front dot it mirrors, in the
    direction BACK_GRID_DIRECTION chooses.
    """
    spec = _double_sided_spec('positive', back=DS_FRONT_LINES)
    radius = DS_CYLINDER_PARAMS['diameter'] / 2
    step = ip.BACK_GRID_DIRECTION * ip.INTERPOINT_OFFSET_X_MM

    males = [dot for dot in spec['dots'] if not dot['is_recess']]
    recesses = [dot for dot in spec['dots'] if dot['is_recess']]
    assert len(males) == len(recesses)

    for male, recess in zip(males, recesses, strict=True):
        # Cylinder A maps a card-frame x to theta = -x / radius (apply_seam).
        front_x = -male['theta'] * radius
        back_x = -recess['theta'] * radius
        assert back_x == pytest.approx(-front_x + step, abs=1e-9)
        assert recess['y'] == pytest.approx(male['y'] + ip.BACK_GRID_DIRECTION * ip.INTERPOINT_OFFSET_Z_MM, abs=1e-9)


def test_double_sided_uses_its_own_footprint_on_both_plates():
    """Option B sizes, from the ds_* settings — not the single-sided dot."""
    plate_a = _double_sided_spec('positive')
    plate_b = _double_sided_spec('negative')

    for spec in (plate_a, plate_b):
        for dot in spec['dots']:
            if dot['is_recess']:
                assert dot['params'] == {
                    'shape': 'bowl',
                    'bowl_radius': ip.DS_BOWL_DIAMETER_MM / 2,
                    'bowl_depth': ip.DS_BOWL_DEPTH_MM,
                }
            else:
                assert dot['params']['shape'] == 'rounded'
                assert dot['params']['base_radius'] == ip.DS_DOT_BASE_DIAMETER_MM / 2
                assert dot['params']['top_radius'] == ip.DS_DOT_DOME_DIAMETER_MM / 2
                assert dot['params']['base_height'] == ip.DS_DOT_BASE_HEIGHT_MM
                assert dot['params']['dome_height'] == ip.DS_DOT_DOME_HEIGHT_MM


def test_double_sided_forces_tactile_row_indicators_and_says_so():
    """Visual row markers would eat the columns the second face needs."""
    spec = _double_sided_spec('positive', indicator_mode='visual')
    assert spec['indicator_mode'] == 'tactile'
    assert any('tactile' in warning for warning in spec['warnings'])
    assert [marker['type'] for marker in spec['markers']] == ['cylinder_tactile_arrow'] * DS_SETTINGS['grid_rows']


def test_double_sided_warns_when_the_footprints_crowd_each_other():
    """
    The shipped single-sided sizes leave 0.118 mm between a dot and its
    neighbouring recess — under the 0.34 mm a 0.4 mm nozzle can print. Someone
    who types those numbers into the double-sided fields must be told.
    """
    crowded = _double_sided_spec('positive', ds_dot_base_diameter=1.5, ds_bowl_base_diameter=1.8)
    assert ip.same_surface_min_gap(1.5, 1.8, cols=DS_SETTINGS['grid_columns'], rows=DS_SETTINGS['grid_rows']) == (
        pytest.approx(0.118, abs=0.001)
    )
    assert any('0.118' in warning for warning in crowded['warnings'])

    roomy = _double_sided_spec('positive')
    assert roomy['warnings'] == []


# -----------------------------------------------------------------------------
# The hard constraint: with the toggle off, nothing moved
# -----------------------------------------------------------------------------

# Captured from commit a0a9103 (app/geometry_spec.py as it stood before
# double-sided mode existed) by running the two calls in
# `test_single_sided_specs_are_unchanged_by_the_double_sided_code` against it.
# Regenerate ONLY if the single-sided geometry is deliberately changed, and say
# why in the commit message — an unexplained diff here means the beta leaked
# into the path every existing user depends on.
PRE_DOUBLE_SIDED_SPECS = json.loads("""
{
  "negative": {
    "cylinder": {"height":52.0,"polygon_points":[{"x":11.954336377100946,"y":-1.0458689129718997},{"x":-5.071419140888384,"y":10.875693444439802},{"x":-6.882917236212549,"y":-9.829824531467901}],"radius":15.375,"thickness":2.0},
    "dots": [
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":7.5,"z":5.148570523732917},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":5.0,"z":5.148570523732917},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":2.5,"z":5.148570523732917},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":7.5,"z":7.425955512548307},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":5.0,"z":7.425955512548307},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":2.5,"z":7.425955512548307},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":-2.5,"z":5.148570523732917},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":-5.0,"z":5.148570523732917},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":-7.5,"z":5.148570523732917},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":-2.5,"z":7.425955512548307},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":-5.0,"z":7.425955512548307},
      {"is_recess":true,"params":{"bowl_depth":0.8,"bowl_radius":0.9,"shape":"bowl"},"radius":15.375,"theta":0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":-7.5,"z":7.425955512548307}
    ],
    "indicator_mode": "visual",
    "markers": [
      {"depth":0.6,"is_recess":true,"radius":15.375,"rotate_180":true,"size":2.5,"theta":-0.42276422764227645,"type":"cylinder_triangle","x":14.021359025454359,"y":5.0,"z":-6.308099244567222},
      {"depth":0.5,"height":5.0,"is_recess":true,"radius":15.375,"theta":0.0,"type":"cylinder_rect","width":2.5,"x":15.375,"y":5.0,"z":0.0},
      {"depth":0.6,"is_recess":true,"radius":15.375,"rotate_180":true,"size":2.5,"theta":-0.42276422764227645,"type":"cylinder_triangle","x":14.021359025454359,"y":-5.0,"z":-6.308099244567222},
      {"depth":0.5,"height":5.0,"is_recess":true,"radius":15.375,"theta":0.0,"type":"cylinder_rect","width":2.5,"x":15.375,"y":-5.0,"z":0.0}
    ],
    "plate_type": "negative",
    "shape_type": "cylinder",
    "warnings": []
  },
  "positive": {
    "cylinder": {"height":52.0,"polygon_points":[{"x":11.954336377100946,"y":1.0458689129718997},{"x":-6.882917236212546,"y":9.829824531467905},{"x":-5.071419140888396,"y":-10.875693444439797}],"radius":15.375,"thickness":2.0},
    "dots": [
      {"is_recess":false,"params":{"base_height":0.2,"base_radius":1.0,"dome_height":0.6,"dome_radius":0.76875,"shape":"rounded","top_radius":0.75},"radius":15.375,"theta":-0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":7.5,"z":-5.148570523732917},
      {"is_recess":false,"params":{"base_height":0.2,"base_radius":1.0,"dome_height":0.6,"dome_radius":0.76875,"shape":"rounded","top_radius":0.75},"radius":15.375,"theta":-0.34146341463414637,"type":"cylinder_dot","x":14.48733400464518,"y":-2.5,"z":-5.148570523732917},
      {"is_recess":false,"params":{"base_height":0.2,"base_radius":1.0,"dome_height":0.6,"dome_radius":0.76875,"shape":"rounded","top_radius":0.75},"radius":15.375,"theta":-0.5040650406504066,"type":"cylinder_dot","x":13.462756394054429,"y":-2.5,"z":-7.425955512548307}
    ],
    "indicator_mode": "visual",
    "markers": [
      {"depth":0.6,"is_recess":true,"radius":15.375,"rotate_180":false,"size":2.5,"theta":0.42276422764227645,"type":"cylinder_triangle","x":14.021359025454359,"y":5.0,"z":6.308099244567222},
      {"char":"A","depth":0.5,"is_recess":true,"radius":15.375,"size":3.75,"theta":-0.0,"type":"cylinder_character","x":15.375,"y":5.0,"z":-0.0},
      {"depth":0.6,"is_recess":true,"radius":15.375,"rotate_180":false,"size":2.5,"theta":0.42276422764227645,"type":"cylinder_triangle","x":14.021359025454359,"y":-5.0,"z":6.308099244567222},
      {"char":"C","depth":0.5,"is_recess":true,"radius":15.375,"size":3.75,"theta":-0.0,"type":"cylinder_character","x":15.375,"y":-5.0,"z":-0.0}
    ],
    "plate_type": "positive",
    "shape_type": "cylinder",
    "warnings": []
  }
}
""")

# The job that produced the snapshot: visual row markers, a character indicator
# from original_lines, one line long enough to be truncated by grid_columns, and
# a rotated polygon cutout — the single-sided details most at risk of drift.
PRE_DOUBLE_SIDED_CYLINDER_PARAMS = {
    'diameter': 30.75,
    'height': 52.0,
    'wall_thickness': 2.0,
    'seam_offset_deg': 355.0,
    'polygonal_cutout_radius_mm': 6.0,
    'polygonal_cutout_sides': 3,
}
PRE_DOUBLE_SIDED_SETTINGS = {'grid_rows': 2, 'grid_columns': 3}
PRE_DOUBLE_SIDED_LINES = ['⠁⠃', '⠉', '', '']
PRE_DOUBLE_SIDED_ORIGINAL_LINES = ['ab', 'c', '', '']


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_single_sided_specs_are_unchanged_by_the_double_sided_code(plate_type):
    """
    With the toggle absent, the spec equals the one captured before this feature.

    Deep equality, every dot, marker and polygon point. Public training videos
    depend on the single-sided workflow, so double-sided mode is only allowed to
    add branches that a missing toggle never enters. `back_lines` is passed here
    on purpose: single-sided mode has to ignore it.
    """
    spec = extract_cylinder_geometry_spec(
        PRE_DOUBLE_SIDED_LINES,
        'g1',
        CardSettings(**PRE_DOUBLE_SIDED_SETTINGS),
        PRE_DOUBLE_SIDED_CYLINDER_PARAMS,
        PRE_DOUBLE_SIDED_ORIGINAL_LINES,
        plate_type,
        braille_to_dots_func=braille_to_dots,
        back_lines=DS_BACK_LINES,
    )
    assert spec == PRE_DOUBLE_SIDED_SPECS[plate_type]
