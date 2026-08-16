"""
Interpoint (double-sided) math tests.

These are the numbers the double-sided beta stands on. If the mirror, the
offset, or the footprint sizes are wrong, they are wrong here — before any
settings, worker or UI code is written.

Reference values come from the approved 2026-08-16 interpoint research
(clearance_check.py and 01_RESEARCH_FINDINGS.md); the tolerance is +/-0.001 mm.
"""

import math

import pytest

from app.geometry import interpoint as ip

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
