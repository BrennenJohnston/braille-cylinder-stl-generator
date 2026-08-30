"""
Acceptance harness for the Embosser Version 2 keyed cutouts (family R14).

This is the numeric contract from 01_V7_SAMPLE_AUDIT.md section 12, run BEFORE
any application code reads app/geometry/version2.py: if the profile maths or
the build order is wrong it fails here, not in a printed part.

What is proved:
  * a Version 2 cylinder is ONE watertight body with a keyed through-hole;
  * each pocket matches the analytic R14 profile grown by the clearance;
  * a flat faces the tactile arrow column at both ends;
  * all four mouths carry the same 45 degree countersink, 2.0 deep;
  * the nub is on Cylinder A only, on the arrow column;
  * the barrel wall never drops below 1.2;
  * AS BUILT, the four keys still form the identity fit matrix - the property
    the whole family exists for;
  * six deliberate mutations are each caught by the check that owns them.

The Version 7 sample STLs are still compared, but ONLY for what family R14 did
not change: the barrel and the nub. Their key pockets are the retired v7 star,
hexagon and squares, and none of those pegs fits an R14 hole.

All lengths are millimetres, all angles degrees. The frame is the browser
worker's: axis at x = y = 0, barrel centred on z = 0.
"""

import math
import os
from functools import cache
from pathlib import Path

import manifold3d
import numpy as np
import pytest
import trimesh
from manifold3d import CrossSection, Manifold

from app.geometry import version2 as v2

# The worker's barrel tessellation: Manifold.cylinder(height, r, r, 64, true).
SHELL_SECTIONS = 64

# A hull needs two solids, not two planes, so each countersink is built from
# two slabs this thin. Their placement matters: the hull's tapering face is
# supported by the OUTER edge of each slab, so the wide slab hangs outside the
# barrel face and the narrow one sits with its far edge exactly at the
# countersink depth. Put either slab the other way round and the 45 degree
# taper overshoots by the slab's own thickness.
SLAB_MM = 0.01

PLATES = ('positive', 'negative')
CLEARANCES = (0.0, 0.075, 0.5)
FIXTURE_HEIGHT_MM = 52.0
FIXTURE_RADIUS_MM = 15.05

# Sections taken in the straight part of each half, clear of both countersinks.
POCKET_PROBE_Z = (-20.0, -8.0, 8.0, 20.0)

SAMPLES_DIR = Path(
    r'C:\Users\WATAP\Documents\Research\Braille Embosser'
    r'\New Developement_2026_08_27\STL\Cylinder Cuttout examples'
)
SAMPLE_CYLINDERS = {
    'positive': 'Cylinder A v7 (no idicator triangles).stl',
    'negative': 'Cylinder B v7 (no idicator triangles).stl',
}
SAMPLE_RIM_TOL_MM = 0.005
SAMPLE_NUB_AREA_TOL_MM2 = 0.1

# Set these to STLs downloaded from a real browser run to put them through the
# same checks (the GEAR_ROLLER_BROWSER_STL_A precedent):
#   V2_BROWSER_STL_A=...\a.stl V2_BROWSER_STL_B=...\b.stl python -m pytest ...
BROWSER_STL_ENV = {'positive': 'V2_BROWSER_STL_A', 'negative': 'V2_BROWSER_STL_B'}


def _cross_section(profile):
    """One wire-contract polygon as a Manifold CrossSection."""
    points = [(point['x'], point['y']) for point in profile]
    if len(points) < 3:
        raise ValueError(f'a keyed profile needs at least 3 points, got {len(points)}')
    if not all(math.isfinite(value) for point in points for value in point):
        raise ValueError('a keyed profile carries a non-finite coordinate')
    return CrossSection([points], manifold3d.FillRule.NonZero)


def _prism(profile, z_from, thickness):
    return Manifold.extrude(_cross_section(profile), thickness).translate((0.0, 0.0, z_from))


def _countersink(sink, height):
    """
    One mouth chamfer: the hull of the flared profile at the face and the hole
    profile `depth` in, which is a true 45 degree taper when the offset and the
    depth match.
    """
    if sink['kind'] != 'hull':
        raise ValueError(f'unknown countersink kind {sink["kind"]!r}')
    half_height = height / 2.0
    if sink['end'] == 'bottom':
        face_z = -half_height - SLAB_MM
        inner_z = -half_height + sink['depth'] - SLAB_MM
    elif sink['end'] == 'top':
        face_z = half_height
        inner_z = half_height - sink['depth']
    else:
        raise ValueError(f'unknown countersink end {sink["end"]!r}')
    face = _prism(sink['face_profile'], face_z, SLAB_MM)
    inner = _prism(sink['inner_profile'], inner_z, SLAB_MM)
    return Manifold.batch_hull([face, inner])


def _nub_manifold(nub):
    """
    The key nub: a flared base, a straight body, a chamfered top.

    Built as THREE parts unioned, not one hull over all four slabs. The nub
    widens at the base and narrows again at the top, so it is not a convex
    solid: a single convex hull bridges straight from the flare to the chamfer
    and bulges the body out by 0.2 mm - measured 14.396 mm2 where the profile
    is 11.144. Gear A1's notch is this shape's exact negative, so the bulge
    would have jammed the gear that carries the handle torque.
    """
    body_bottom = nub['z_from'] + nub['base_flare']['depth']
    body_top = nub['z_to'] - nub['top_chamfer']['depth']
    if body_top <= body_bottom:
        raise ValueError('the nub is too short for its flare and chamfer')

    # As with the mouth countersinks, a taper is supported by the far edge of
    # each slab, so each slab sits with its top at the end of its own taper.
    flare = Manifold.batch_hull(
        [
            _prism(nub['base_flare']['profile'], nub['z_from'] - SLAB_MM, SLAB_MM),
            _prism(nub['profile'], body_bottom - SLAB_MM, SLAB_MM),
        ]
    )
    body = _prism(nub['profile'], body_bottom, body_top - body_bottom)
    chamfer = Manifold.batch_hull(
        [
            _prism(nub['profile'], body_top - SLAB_MM, SLAB_MM),
            _prism(nub['top_chamfer']['profile'], nub['z_to'] - SLAB_MM, SLAB_MM),
        ]
    )
    return flare + body + chamfer


def _stabilize_for_float32(mesh):
    """
    Make the mesh survive STL's float32 precision, as the browser's export does.

    The same treatment tests/test_golden.py gives its fixtures, repeated here
    rather than imported because Phase 07 imports build_v2_cylinder from this
    module - the dependency has to point one way.
    """
    for _ in range(4):
        mesh.vertices = mesh.vertices.astype(np.float32).astype(np.float64)
        mesh.merge_vertices()
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        if mesh.is_watertight:
            return mesh
    raise ValueError('the Version 2 cylinder did not stabilize to a watertight float32 mesh')


def build_v2_cylinder(block, radius, height, plate_type):
    """
    The reference Version 2 cylinder: a solid barrel, both key halves cut
    through, all four mouths countersunk, and the nub added on Cylinder A.

    Booleans go straight to Manifold, matching the worker. Phase 07 imports
    this so the golden fixtures and this harness can never drift apart.
    """
    if plate_type not in v2.KEY_PROFILES_BY_PLATE:
        raise ValueError(f'unknown plate type {plate_type!r}')
    if ('nub' in block) != (plate_type == 'positive'):
        raise ValueError(f'the nub belongs to the positive plate only; block for {plate_type!r} disagrees')

    solid = Manifold.cylinder(height, radius, radius, SHELL_SECTIONS, True)
    for half in block['halves']:
        span = half['z_to'] - half['z_from']
        if span <= 0:
            raise ValueError(f'half {half["end"]!r} has z_to <= z_from')
        solid -= _prism(half['profile'], half['z_from'], span)
    for sink in block['countersinks']:
        solid -= _countersink(sink, height)
    if 'nub' in block:
        solid += _nub_manifold(block['nub'])

    raw = solid.to_mesh()
    mesh = trimesh.Trimesh(
        vertices=np.asarray(raw.vert_properties)[:, :3],
        faces=np.asarray(raw.tri_verts),
        process=False,
    )
    return _stabilize_for_float32(mesh)


@cache
def _cylinder(plate_type, clearance):
    block = v2.keyed_cutout_block(plate_type, FIXTURE_HEIGHT_MM, clearance)
    return build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, plate_type)


def _loops(mesh, z):
    """The closed outlines where a horizontal plane meets the mesh."""
    section = mesh.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
    if section is None:
        raise ValueError(f'the plane z={z} misses the mesh entirely')
    return [np.asarray(loop)[:, :2] for loop in section.discrete]


def _hole_loop(mesh, z):
    """The pocket outline: the inner loop, the one that is not the barrel rim."""
    loops = _loops(mesh, z)
    assert len(loops) == 2, f'expected a rim and a pocket at z={z}, found {len(loops)} loops'
    return min(loops, key=lambda loop: np.hypot(loop[:, 0], loop[:, 1]).max())


def _polygon_area(points):
    x, y = points[:, 0], points[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)) / 2.0)


def _extents(points):
    return (
        float(points[:, 0].max() - points[:, 0].min()),
        float(points[:, 1].max() - points[:, 1].min()),
    )


def _max_boundary_distance(measured, expected):
    """The farthest any measured point sits from the expected outline."""
    target = np.asarray(expected, dtype=float)
    starts = target
    ends = np.roll(target, -1, axis=0)
    edges = ends - starts
    lengths = np.einsum('ij,ij->i', edges, edges)
    worst = 0.0
    for point in measured:
        offsets = point - starts
        t = np.clip(np.einsum('ij,ij->i', offsets, edges) / lengths, 0.0, 1.0)
        closest = starts + t[:, None] * edges
        worst = max(worst, float(np.hypot(*(point - closest).T).min()))
    return worst


def _rotate(points, degrees):
    angle = math.radians(degrees)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rotation = np.array([[cos_a, sin_a], [-sin_a, cos_a]])
    return np.asarray(points) @ rotation


def _arrow_column_flat(loop):
    """
    The flat wall facing 180 degrees, or None when the outline shows a corner
    there instead. Returns the two endpoints of the flat.
    """
    candidates = loop[loop[:, 0] <= loop[:, 0].min() + 1e-4]
    if len(candidates) < 2:
        return None
    if candidates[:, 1].min() >= 0.0 or candidates[:, 1].max() <= 0.0:
        return None
    lowest = candidates[np.argmin(candidates[:, 1])]
    highest = candidates[np.argmax(candidates[:, 1])]
    if abs(highest[0] - lowest[0]) > 1e-6:
        return None
    return lowest, highest


def _plate_key_names(plate_type):
    return v2.KEY_PROFILES_BY_PLATE[plate_type]


def _key_at(plate_type, z):
    bottom, top = _plate_key_names(plate_type)
    return bottom if z < 0 else top


@pytest.mark.parametrize('plate_type', PLATES)
def test_the_cylinder_is_one_watertight_body(plate_type):
    """
    The counter plate must be a single solid; so must the emboss plate here,
    because this builder carries no braille dots and therefore none of the
    loose domes the gear specification exempts.
    """
    mesh = _cylinder(plate_type, 0.075)
    assert mesh.is_watertight
    assert mesh.body_count == 1
    assert mesh.volume > 0


@pytest.mark.parametrize('plate_type', PLATES)
def test_bounds(plate_type):
    mesh = _cylinder(plate_type, 0.075)
    expected_top = FIXTURE_HEIGHT_MM / 2.0 + (v2.V2_NUB['height'] if plate_type == 'positive' else 0.0)
    assert mesh.bounds[0] == pytest.approx([-15.05, -15.05, -26.0], abs=0.001)
    assert mesh.bounds[1] == pytest.approx([15.05, 15.05, expected_top], abs=0.001)


@pytest.mark.parametrize('plate_type', PLATES)
def test_rim_radius(plate_type):
    """The barrel is untouched between the two mouths."""
    mesh = _cylinder(plate_type, 0.075)
    for z in (-20.0, 0.0, 20.0):
        rim = max(_loops(mesh, z), key=lambda loop: np.hypot(loop[:, 0], loop[:, 1]).max())
        radii = np.hypot(rim[:, 0], rim[:, 1])
        assert radii.max() == pytest.approx(FIXTURE_RADIUS_MM, abs=SAMPLE_RIM_TOL_MM)


@pytest.mark.parametrize('clearance', CLEARANCES)
@pytest.mark.parametrize('plate_type', PLATES)
@pytest.mark.parametrize('z', POCKET_PROBE_Z)
def test_pocket_sections_match_the_profile(plate_type, clearance, z):
    mesh = _cylinder(plate_type, clearance)
    measured = _hole_loop(mesh, z)
    expected = v2.key_profile(_key_at(plate_type, z), clearance)

    assert _max_boundary_distance(measured, expected) <= 0.01
    assert _polygon_area(measured) == pytest.approx(_polygon_area(np.asarray(expected)), abs=0.5)


@pytest.mark.parametrize('plate_type', PLATES)
@pytest.mark.parametrize('z', (-20.0, 20.0))
def test_a_flat_faces_the_arrow_column(plate_type, z):
    """
    The 180 degree ray must meet a flat wall, not a corner: that flat is what
    gear A1's notch keys against and what keeps the mouth clear of the nub.
    """
    clearance = 0.075
    mesh = _cylinder(plate_type, clearance)
    measured = _hole_loop(mesh, z)
    half_width = v2.V2_KEY_PROFILES[_key_at(plate_type, z)]['width'] / 2.0 + clearance

    flat = _arrow_column_flat(measured)
    assert flat is not None, 'no flat wall straddles the arrow column'
    lowest, highest = flat
    assert lowest[0] == pytest.approx(-half_width, abs=0.01)
    # The wall's own direction, which must be perpendicular to the column.
    span = highest - lowest
    assert abs(math.degrees(math.atan2(span[0], span[1]))) <= 0.05


@pytest.mark.parametrize('plate_type', PLATES)
def test_the_hole_goes_all_the_way_through(plate_type):
    mesh = _cylinder(plate_type, 0.075)
    axis = [[0.0, 0.0, float(z)] for z in range(-25, 26)]
    assert not mesh.contains(axis).any()


@pytest.mark.parametrize('plate_type', PLATES)
@pytest.mark.parametrize('depth', (0.1, 1.0, 1.9))
def test_countersink_is_one_45_degree_rule_at_every_mouth(plate_type, depth):
    clearance = 0.075
    mesh = _cylinder(plate_type, clearance)
    half_height = FIXTURE_HEIGHT_MM / 2.0
    for sign in (-1.0, 1.0):
        z = sign * (half_height - depth)
        name = _key_at(plate_type, z)
        profile = v2.V2_KEY_PROFILES[name]
        grown = clearance + v2.V2_COUNTERSINK_OFFSET_MM * (1.0 - depth / v2.V2_COUNTERSINK_DEPTH_MM)
        width, length = _extents(_hole_loop(mesh, z))
        assert width == pytest.approx(profile['width'] + 2 * grown, abs=0.02)
        assert length == pytest.approx(profile['length'] + 2 * grown, abs=0.02)


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_the_nub_is_on_cylinder_a_only(clearance):
    positive = _cylinder('positive', clearance)
    negative = _cylinder('negative', clearance)
    assert negative.bounds[1][2] == pytest.approx(FIXTURE_HEIGHT_MM / 2.0, abs=0.001)
    assert positive.bounds[1][2] == pytest.approx(FIXTURE_HEIGHT_MM / 2.0 + v2.V2_NUB['height'], abs=0.001)

    block = v2.keyed_cutout_block('positive', FIXTURE_HEIGHT_MM, clearance)
    expected = np.array([(point['x'], point['y']) for point in block['nub']['profile']])
    section = _loops(positive, 27.5)
    assert len(section) == 1, 'only the nub stands above the top face'
    assert _polygon_area(section[0]) == pytest.approx(_polygon_area(expected), abs=0.05)
    assert _max_boundary_distance(section[0], expected) <= 0.01

    apex = max(section[0], key=lambda point: math.hypot(*point))
    expected_apex = max(math.hypot(*point) for point in expected)
    assert math.hypot(*apex) == pytest.approx(expected_apex, abs=0.01)
    assert math.degrees(math.atan2(apex[1], apex[0])) % 360.0 == pytest.approx(v2.V2_ARROW_COLUMN_DEG, abs=0.05)


def test_the_uncleared_nub_matches_the_audit_area():
    """
    11.144 mm2 is the number 01_V7_SAMPLE_AUDIT.md section 6 measured.

    Taken from the raw triangle rather than from a keyed_cutout_block: since
    2026-08-29 the emitted nub is always inset by V2_NUB_CLEARANCE_MM, so no
    clearance argument produces an uncleared one any more. The audit pin is
    about Brennen's CAD, which has not changed.
    """
    half_width = v2.V2_NUB['side'] / 2.0
    outline = v2.nub_triangle(
        v2.V2_NUB['base_radius'], v2.V2_NUB['apex_radius'], half_width, v2.V2_ARROW_COLUMN_DEG
    )
    assert _polygon_area(np.array(outline)) == pytest.approx(11.144, abs=0.01)


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_minimum_wall(clearance):
    """
    The barrel is thinnest where a flared mouth reaches farthest out. Computed
    from the profiles, then confirmed with a containment probe in the material
    that should be left standing there.
    """
    thinnest = None
    for plate_type in PLATES:
        block = v2.keyed_cutout_block(plate_type, FIXTURE_HEIGHT_MM, clearance)
        for sink in block['countersinks']:
            reach = max(math.hypot(point['x'], point['y']) for point in sink['face_profile'])
            wall = FIXTURE_RADIUS_MM - reach
            assert wall >= 1.2, f'{plate_type} {sink["end"]} mouth leaves only {wall:.3f} mm of wall'
            if thinnest is None or wall < thinnest[0]:
                thinnest = (wall, plate_type, sink['end'], reach)

    wall, plate_type, end, reach = thinnest
    mesh = _cylinder(plate_type, clearance)
    z = (-1.0 if end == 'bottom' else 1.0) * (FIXTURE_HEIGHT_MM / 2.0 - 0.1)
    corner = max(
        _hole_loop(mesh, z),
        key=lambda point: math.hypot(*point),
    )
    direction = corner / math.hypot(*corner)
    probe = direction * (reach + wall / 2.0)
    assert mesh.contains([[probe[0], probe[1], z]])[0], 'the wall behind the widest mouth corner is missing'


@pytest.mark.parametrize('clearance', CLEARANCES)
def test_as_built_fit_matrix_is_the_identity(clearance):
    """
    Family R14's whole reason for existing, measured on the rendered solid
    rather than on the maths: no peg enters any hole but its own, at any
    rotation, at any clearance the dial offers.
    """
    holes = {}
    for plate_type in PLATES:
        mesh = _cylinder(plate_type, clearance)
        for z in (-20.0, 20.0):
            holes[_key_at(plate_type, z)] = _hole_loop(mesh, z)
    assert set(holes) == set(v2.V2_KEY_PROFILES)

    rotations = [step * 0.5 for step in range(181)]
    wrong_pairs = []
    for peg_name, peg_loop in holes.items():
        # The peg is the hole less the clearance it was grown by.
        peg = peg_loop - np.sign(peg_loop) * clearance
        for hole_name, hole_loop in holes.items():
            hole_x, hole_y = _extents(hole_loop)
            best = min(
                max(0.0, (rx - hole_x) / 2.0, (ry - hole_y) / 2.0)
                for rx, ry in (_extents(_rotate(peg, degrees)) for degrees in rotations)
            )
            if peg_name == hole_name:
                assert best == pytest.approx(0.0, abs=0.01), f'{peg_name} does not fit its own hole'
            else:
                assert best > 0.1, f'{peg_name} enters the {hole_name} hole at c={clearance}'
                wrong_pairs.append(best)

    assert min(wrong_pairs) == pytest.approx(1.0 - clearance, abs=0.02)


@pytest.mark.skipif(not SAMPLES_DIR.is_dir(), reason='the v7 sample cylinders are not on this machine')
@pytest.mark.parametrize('plate_type', PLATES)
def test_sample_barrel_matches(plate_type):
    """
    The v7 samples still rule the barrel: family R14 changed the keys only.
    Their pockets are the retired shapes and are deliberately not compared.
    """
    sample = trimesh.load_mesh(str(SAMPLES_DIR / SAMPLE_CYLINDERS[plate_type]), process=False)
    vertices = np.asarray(sample.vertices)
    axis_x = (vertices[:, 0].min() + vertices[:, 0].max()) / 2.0
    axis_y = (vertices[:, 1].min() + vertices[:, 1].max()) / 2.0

    barrel = vertices[(vertices[:, 2] > 10.0) & (vertices[:, 2] < 40.0)]
    radii = np.hypot(barrel[:, 0] - axis_x, barrel[:, 1] - axis_y)
    assert radii.max() == pytest.approx(FIXTURE_RADIUS_MM, abs=SAMPLE_RIM_TOL_MM)
    assert vertices[:, 2].min() == pytest.approx(0.0, abs=0.001)


@pytest.mark.skipif(not SAMPLES_DIR.is_dir(), reason='the v7 sample cylinders are not on this machine')
def test_sample_nub_matches():
    """The nub is Brennen's, unchanged by R14, so the sample still rules it."""
    sample = trimesh.load_mesh(str(SAMPLES_DIR / SAMPLE_CYLINDERS['positive']), process=True)
    vertices = np.asarray(sample.vertices)
    axis_x = (vertices[:, 0].min() + vertices[:, 0].max()) / 2.0
    axis_y = (vertices[:, 1].min() + vertices[:, 1].max()) / 2.0
    assert vertices[:, 2].max() == pytest.approx(FIXTURE_HEIGHT_MM + v2.V2_NUB['height'], abs=0.001)

    section = sample.section(plane_origin=[0.0, 0.0, 53.5], plane_normal=[0.0, 0.0, 1.0])
    loops = [np.asarray(loop)[:, :2] - np.array([axis_x, axis_y]) for loop in section.discrete]
    assert len(loops) == 1, 'only the nub stands above the sample top face'
    assert _polygon_area(loops[0]) == pytest.approx(11.144, abs=SAMPLE_NUB_AREA_TOL_MM2)
    apex = max(loops[0], key=lambda point: math.hypot(*point))
    assert math.hypot(*apex) == pytest.approx(v2.V2_NUB['apex_radius'], abs=0.35)


@pytest.mark.parametrize('plate_type', PLATES)
def test_browser_generated_stl(plate_type):
    """
    The same checks against an STL downloaded from a real browser run.

    Skipped unless the environment names a file, because producing one needs
    Chromium - Phase 06 sets these variables.
    """
    variable = BROWSER_STL_ENV[plate_type]
    value = os.environ.get(variable)
    if not value:
        pytest.skip(f'set {variable} to a browser-generated Version 2 STL')
    path = Path(value)
    assert path.is_file(), f'{variable} points at a missing file: {path}'

    mesh = trimesh.load_mesh(str(path), process=True)
    expected_top = FIXTURE_HEIGHT_MM / 2.0 + (v2.V2_NUB['height'] if plate_type == 'positive' else 0.0)
    assert mesh.is_watertight
    assert mesh.bounds[1][2] == pytest.approx(expected_top, abs=0.01)
    assert not mesh.contains([[0.0, 0.0, float(z)] for z in range(-25, 26)]).any()
    for z in POCKET_PROBE_Z:
        measured = _hole_loop(mesh, z)
        expected = v2.key_profile(_key_at(plate_type, z), v2.V2_KEY_CLEARANCE_DEFAULT_MM)
        assert _max_boundary_distance(measured, expected) <= 0.02


def _mutate(block, kind):
    """Break the block one specific way, to prove a check is actually load-bearing."""
    import copy

    broken = copy.deepcopy(block)
    if kind == 'swapped_halves':
        broken['halves'][0]['profile'], broken['halves'][1]['profile'] = (
            broken['halves'][1]['profile'],
            broken['halves'][0]['profile'],
        )
    elif kind == 'rotated_key':
        turned = _rotate([(p['x'], p['y']) for p in broken['halves'][0]['profile']], 30.0)
        broken['halves'][0]['profile'] = [{'x': float(x), 'y': float(y)} for x, y in turned]
    elif kind == 'clearance_inward':
        name = v2.KEY_PROFILES_BY_PLATE['negative'][0]
        shrunk = v2.grown_key_outline(name, -0.075)
        broken['halves'][0]['profile'] = [{'x': x, 'y': y} for x, y in shrunk]
    elif kind == 'shallow_countersink':
        broken['countersinks'][0]['depth'] = 1.0
    elif kind == 'blind_hole':
        broken['halves'][0]['z_to'] -= 1.0
        broken['halves'][1]['z_from'] += 1.0
    else:
        raise ValueError(f'unknown mutation {kind!r}')
    return broken


def test_swapped_halves_are_caught():
    block = _mutate(v2.keyed_cutout_block('negative', FIXTURE_HEIGHT_MM, 0.075), 'swapped_halves')
    mesh = build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')
    expected = v2.key_profile(v2.KEY_PROFILES_BY_PLATE['negative'][0], 0.075)
    assert _max_boundary_distance(_hole_loop(mesh, -20.0), expected) > 0.01


def test_a_rotated_key_is_caught():
    block = _mutate(v2.keyed_cutout_block('negative', FIXTURE_HEIGHT_MM, 0.075), 'rotated_key')
    mesh = build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')
    measured = _hole_loop(mesh, -20.0)
    assert _arrow_column_flat(measured) is None, 'a 30 degree turn left a flat on the arrow column'
    expected = v2.key_profile(v2.KEY_PROFILES_BY_PLATE['negative'][0], 0.075)
    assert _max_boundary_distance(measured, expected) > 0.01


def test_clearance_applied_inward_is_caught():
    # Widths derived from the clearance rather than typed: the dial's default
    # has moved once already (0.15 -> 0.075, 2026-08-29) and a hardcoded 2c
    # turns a real regression into an arithmetic failure that reads like one.
    clearance = v2.V2_KEY_CLEARANCE_DEFAULT_MM
    block = _mutate(v2.keyed_cutout_block('negative', FIXTURE_HEIGHT_MM, clearance), 'clearance_inward')
    mesh = build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')
    width, _ = _extents(_hole_loop(mesh, -20.0))
    assert width == pytest.approx(8.0 - 2 * clearance, abs=0.01), 'the mutation did not shrink the hole'
    assert width < 8.0 + 2 * clearance - 0.01, 'a hole cut smaller than its peg went unnoticed'


def test_a_shallow_countersink_is_caught():
    block = _mutate(v2.keyed_cutout_block('negative', FIXTURE_HEIGHT_MM, 0.075), 'shallow_countersink')
    mesh = build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')
    width, _ = _extents(_hole_loop(mesh, -24.1))
    correct = 8.0 + 2 * (0.075 + 2.0 * (1.0 - 1.9 / 2.0))
    assert abs(width - correct) > 0.02


def test_a_blind_hole_is_caught():
    block = _mutate(v2.keyed_cutout_block('negative', FIXTURE_HEIGHT_MM, 0.075), 'blind_hole')
    mesh = build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')
    assert mesh.contains([[0.0, 0.0, 0.0]])[0], 'the through-hole check would not notice a blind hole'


def test_the_nub_on_the_wrong_plate_is_refused():
    """The builder refuses rather than quietly printing a Cylinder B with a nub."""
    block = v2.keyed_cutout_block('positive', FIXTURE_HEIGHT_MM, 0.075)
    with pytest.raises(ValueError, match='positive plate only'):
        build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')


@pytest.mark.parametrize(
    'block',
    (
        {'halves': [{'end': 'bottom', 'profile': [{'x': 0.0, 'y': 0.0}], 'z_from': -26.0, 'z_to': 0.0}]},
        {'halves': [{'end': 'bottom', 'profile': [{'x': float('nan'), 'y': 0.0}] * 4, 'z_from': -26.0, 'z_to': 0.0}]},
    ),
)
def test_a_malformed_block_raises(block):
    block = {'clearance_mm': 0.075, 'countersinks': [], **block}
    with pytest.raises(ValueError):
        build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')


def test_an_unknown_countersink_kind_raises():
    block = v2.keyed_cutout_block('negative', FIXTURE_HEIGHT_MM, 0.075)
    block['countersinks'][0]['kind'] = 'scale'
    with pytest.raises(ValueError, match='unknown countersink kind'):
        build_v2_cylinder(block, FIXTURE_RADIUS_MM, FIXTURE_HEIGHT_MM, 'negative')
