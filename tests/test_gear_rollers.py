"""
Acceptance harness for the gear-integrated one-piece rollers (BETA).

This is the numeric contract from 01_SAMPLE_GEOMETRY_AUDIT.md section 11, run
BEFORE any application code exists: if the Phase 01 transform or the union
strategy is wrong, it fails here rather than in a printed part.

What is proved:
  * the vendored assets are the exact bytes their manifest records;
  * barrel + gears + weld rings unions into ONE watertight body;
  * the union does not move, deform or lose any gear surface;
  * the barrel keeps its 15.400 mm radius and the roller is 72.000 mm tall;
  * with the reference samples present, the whole assembled roller matches
    Brennen's own one-piece roller export.

All lengths are millimeters, all angles degrees. The frame is the browser
worker's: cylinder axis at x=y=0, barrel centered on z=0 (z -26..+26), gears
at z -36..-26 and +26..+36.
"""

import hashlib
import json
import math
import struct
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / 'static' / 'assets' / 'gears'
MANIFEST_PATH = ASSETS_DIR / 'gears_manifest.json'
ASSET_NAMES = ('gears_a', 'gears_b')

# Phase 01 binary format. The header is 14 bytes, so the float block starts at
# an offset that is NOT a multiple of 4: numpy.frombuffer accepts that, a
# browser Float32Array view does not (see the worker phase).
GEAR_MAGIC = b'BCGR1\x00'
GEAR_HEADER_BYTES = 14

# The barrel the worker builds: Manifold.cylinder(52, 15.4, 15.4, 64, true).
BARREL_RADIUS_MM = 15.4
BARREL_HEIGHT_MM = 52.0
SHELL_SECTIONS = 64

# Hidden weld ring at each gear/barrel interface (audit section 5): a 0.1 mm
# tall annulus straddling the contact plane, proved solid on both sides at
# every probed angle, and entirely invisible from outside.
WELD_RING_R_IN_MM = 8.0
WELD_RING_R_OUT_MM = 13.0
WELD_RING_HEIGHT_MM = 0.1
WELD_RING_VOLUME_MM3 = math.pi * (WELD_RING_R_OUT_MM**2 - WELD_RING_R_IN_MM**2) * WELD_RING_HEIGHT_MM  # 32.99

# Gear metrology (audit section 3), verbatim from the STEP entities.
TOOTH_COUNT = 24
TIP_RADIUS_MM = 16.1093702290795
TIP_BAND_DEPTH_MM = 0.05  # tip band = radial distance > tip radius - this
TOOTH_GAP_DEG = 2.0  # angular gap that separates one tooth from the next

# --- tolerances, each with its audit section 11 justification ---------------
# 11.2 bounds: float32 ULP at 32 mm is 3.8e-6 mm, so 0.001 is ~250x the noise.
BOUNDS_TOL_MM = 0.001
# 11.3 barrel rim: 0.005 is 4x below the 64-gon sagitta the tessellation itself
# introduces (0.0186 mm), so it pins the radius, not the segment count.
RIM_TOL_MM = 0.005
# 11.4 gear surface: 0.01 absorbs float32 round-trips. Measured against the
# vendored asset the union reproduces it exactly (max distance 0.000000), and
# the smallest real defect this must catch - a half-degree clocking error -
# moves flank points by 0.11 mm, eleven times the tolerance.
SURFACE_TOL_MM = 0.01
# 11.5 clocking: 0.01 deg is 0.0028 mm of arc at the tip radius.
PHASE_TOL_DEG = 0.01
# 11.6 volume: one raised braille dot is about 0.4 mm^3, so 0.5 mm^3 catches a
# missing or doubled feature while ignoring tessellation noise.
VOLUME_TOL_MM3 = 0.5

# The gear/barrel contact planes at z = +/-26 are INTERIOR to the union: the
# gear's interface face is a solid disk out to r 14.609 and the barrel's end
# cap is solid beneath it, so that surface stops existing once they fuse.
# Sampled points there are inside the solid and are excluded from surface
# comparisons - 0.1 mm also clears the weld ring's 0.05 mm half-height.
INTERFACE_BAND_MM = 0.1

# The reference samples live outside the repo; the deep comparison skips when
# the folder is absent (CI), and runs on Brennen's machine.
SAMPLES_DIR = Path(r'C:\Users\WATAP\Documents\Research\Braille Embosser\New Developement_2026_08_24\Roller Samples')
# Sample assembly frame -> program frame (audit section 10.2), the same
# constants scripts/derive_gear_assets.py baked into the assets.
SAMPLE_ROLLERS = {
    'gears_a': {
        'file': 'Rollers v7 (Cylinder A and Top and Bottom Gears).stl',
        'axis_x_mm': -16.0000,
        'axis_y_mm': 0.0000,
        'rotation_z_deg': 180.0,
    },
    'gears_b': {
        'file': 'Rollers v7 (Cylinder B and Top and Bottom Gears).stl',
        'axis_x_mm': 16.0473,
        'axis_y_mm': -0.0079,
        'rotation_z_deg': 0.0,
    },
}
Z_SHIFT_MM = -26.0

# Deep-comparison tolerances. Brennen's roller export and our vendored gears
# tessellate the SAME B-spline flanks differently, so the residual is chord
# error between two tessellations, not placement error: measured p99 0.0073 mm
# and max 0.0129 mm over five sampling seeds. A real placement fault is orders
# above both - a 15 deg mis-mesh reads 2.57 mm, a wrong 180 deg rotation
# 1.20 mm, and even a half-degree clocking slip 0.11 mm.
SAMPLE_GEAR_P99_TOL_MM = 0.01
SAMPLE_GEAR_MAX_TOL_MM = 0.02
# The sample barrel is a 180-gon; ours is the worker's 64-gon. The radial
# difference is the sagitta gap between the two, 15.4 * (1 - cos(180/64 deg))
# = 0.0186 mm, which is geometry we deliberately reproduce, not error.
SAMPLE_BARREL_TOL_MM = 0.019

_ROLLER_CACHE: dict = {}


def load_gear_asset(asset_name):
    """Read one vendored .bin asset into a trimesh.Trimesh (two disjoint bodies)."""
    import numpy as np
    import trimesh

    path = ASSETS_DIR / f'{asset_name}.bin'
    if not path.is_file():
        raise FileNotFoundError(f'vendored gear asset missing: {path}. Regenerate with scripts/derive_gear_assets.py')
    data = path.read_bytes()
    if data[:6] != GEAR_MAGIC:
        raise ValueError(f'{path.name}: bad magic {data[:6]!r}, expected {GEAR_MAGIC!r}')
    vert_count, tri_count = struct.unpack_from('<II', data, 6)
    vertices = np.frombuffer(data, dtype='<f4', count=3 * vert_count, offset=GEAR_HEADER_BYTES)
    faces = np.frombuffer(data, dtype='<u4', count=3 * tri_count, offset=GEAR_HEADER_BYTES + 12 * vert_count)
    return trimesh.Trimesh(
        vertices=vertices.reshape(-1, 3).astype(np.float64),
        faces=faces.reshape(-1, 3).astype(np.int64),
        process=False,
    )


def build_barrel():
    """The worker's cylinder shell: 64 segments, centered on the origin."""
    import trimesh

    return trimesh.creation.cylinder(radius=BARREL_RADIUS_MM, height=BARREL_HEIGHT_MM, sections=SHELL_SECTIONS)


def build_weld_ring(z_center):
    import trimesh

    ring = trimesh.creation.annulus(
        r_min=WELD_RING_R_IN_MM, r_max=WELD_RING_R_OUT_MM, height=WELD_RING_HEIGHT_MM, sections=SHELL_SECTIONS
    )
    ring.apply_translation([0.0, 0.0, z_center])
    return ring


def build_one_piece_roller(asset_name):
    """Barrel + both gears + both weld rings, fused into one solid."""
    import trimesh

    half_height = BARREL_HEIGHT_MM / 2.0
    parts = [
        build_barrel(),
        load_gear_asset(asset_name),
        build_weld_ring(-half_height),
        build_weld_ring(half_height),
    ]
    return trimesh.boolean.union(parts, engine='manifold')


def one_piece_roller(asset_name):
    """Cached build - the union costs about a second and every test wants it."""
    if asset_name not in _ROLLER_CACHE:
        _ROLLER_CACHE[asset_name] = build_one_piece_roller(asset_name)
    return _ROLLER_CACHE[asset_name]


def tooth_band_phase(vertices, z_low, z_high):
    """
    Measure a gear band's tooth count and angular phase.

    These meshes carry vertices only on feature edges, so a mid-band slice
    finds nothing (audit section 2). The tip band is the one radius where every
    tooth is guaranteed to have vertices. Phase is the circular mean of the
    angles modulo the 15 degree pitch, so it is independent of which tooth is
    called first.
    """
    import numpy as np

    in_band = vertices[(vertices[:, 2] > z_low) & (vertices[:, 2] < z_high)]
    radius = np.hypot(in_band[:, 0], in_band[:, 1])
    tips = in_band[radius > (TIP_RADIUS_MM - TIP_BAND_DEPTH_MM)]
    if len(tips) == 0:
        return 0, float('nan')

    angles = np.degrees(np.arctan2(tips[:, 1], tips[:, 0])) % 360.0
    ordered = np.sort(angles)
    gaps = np.diff(np.concatenate([ordered, [ordered[0] + 360.0]]))
    count = max(1, int((gaps > TOOTH_GAP_DEG).sum()))

    pitch = 360.0 / TOOTH_COUNT
    scaled = np.radians((angles % pitch) * TOOTH_COUNT)
    mean = math.degrees(math.atan2(np.sin(scaled).mean(), np.cos(scaled).mean())) / TOOTH_COUNT
    return count, mean % pitch


def surface_distances(source_mesh, target_mesh, count, seed):
    """Nearest distance from points sampled on source_mesh to target_mesh's surface."""
    import trimesh

    points, _ = trimesh.sample.sample_surface(source_mesh, count, seed=seed)
    return points, trimesh.proximity.closest_point(target_mesh, points)[1]


def outside_interface_band(points):
    """Mask dropping points on the buried gear/barrel contact planes."""
    import numpy as np

    return np.abs(np.abs(points[:, 2]) - BARREL_HEIGHT_MM / 2.0) > INTERFACE_BAND_MM


@pytest.fixture(scope='module')
def geometry_stack():
    """trimesh + manifold3d are dev-only extras; the spec tests below need neither."""
    pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')


# Hook for checking a roller the BROWSER actually produced. Everything else here
# measures Python's own union; this measures the file a user would download.
# Point the variables at STLs generated by the Manifold worker in a real
# browser, then run this file:
#   GEAR_ROLLER_BROWSER_STL_A=...\gears_a.stl pytest tests/test_gear_rollers.py
BROWSER_STL_ENV = {'gears_a': 'GEAR_ROLLER_BROWSER_STL_A', 'gears_b': 'GEAR_ROLLER_BROWSER_STL_B'}


def browser_stl_path(asset_name):
    import os

    value = os.environ.get(BROWSER_STL_ENV[asset_name])
    return Path(value) if value else None


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_vendored_asset_is_the_bytes_its_manifest_records(asset_name):
    """
    Provenance: the assets are a 1:1 replication of Brennen's reference gears,
    and nothing but scripts/derive_gear_assets.py may change them. Pinning the
    hash makes any silent re-derivation - a different transform, a different
    source file - fail loudly here rather than reach a printer.
    """
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    recorded = manifest['assets'][f'{asset_name}.bin']

    payload = (ASSETS_DIR / f'{asset_name}.bin').read_bytes()
    assert hashlib.sha256(payload).hexdigest() == recorded['sha256']
    assert len(payload) == recorded['byte_size']

    vert_count, tri_count = struct.unpack_from('<II', payload, 6)
    assert vert_count == recorded['vert_count']
    assert tri_count == recorded['tri_count']
    assert len(payload) == GEAR_HEADER_BYTES + 12 * vert_count + 12 * tri_count

    for source in recorded['sources']:
        assert source['tooth_count'] == TOOTH_COUNT
        assert source['tip_radius_mm'] == pytest.approx(TIP_RADIUS_MM, abs=BOUNDS_TOL_MM)


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_one_piece_roller_is_a_single_watertight_body(geometry_stack, asset_name):
    """Audit 11.1 - the whole point of the feature: one solid, not three shells."""
    roller = one_piece_roller(asset_name)
    assert len(roller.split(only_watertight=False)) == 1
    assert roller.is_watertight
    assert roller.is_volume


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_one_piece_roller_survives_the_float32_stl_round_trip(geometry_stack, asset_name):
    """
    STL stores float32. Exact tangencies collapse into non-manifold pinch edges
    when coordinates round, which is the failure the weld rings exist to avoid;
    the file the user downloads has to still be one watertight solid.
    """
    import io

    import trimesh

    roller = one_piece_roller(asset_name)
    reloaded = trimesh.load(io.BytesIO(roller.export(file_type='stl')), file_type='stl', force='mesh')
    assert len(reloaded.split(only_watertight=False)) == 1
    assert reloaded.is_watertight


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_one_piece_roller_envelope(geometry_stack, asset_name):
    """Audit 11.2 - the 72.000 mm roller: gears reach z +/-36, nothing exceeds the tips."""
    roller = one_piece_roller(asset_name)
    low, high = roller.bounds

    assert low[2] == pytest.approx(-36.0, abs=BOUNDS_TOL_MM)
    assert high[2] == pytest.approx(36.0, abs=BOUNDS_TOL_MM)
    assert high[2] - low[2] == pytest.approx(72.0, abs=BOUNDS_TOL_MM)

    for axis in (0, 1):
        assert low[axis] >= -(TIP_RADIUS_MM + BOUNDS_TOL_MM)
        assert high[axis] <= TIP_RADIUS_MM + BOUNDS_TOL_MM


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_barrel_radius_survives_the_union(geometry_stack, asset_name):
    """
    Audit 11.3. A tessellated cylinder carries vertices ONLY on its two rim
    rings, and those rims are now buried at the gear interfaces - so measure a
    cross-section through the free barrel wall instead of hunting for vertices.
    The section's corners sit on the true radius; its edge midpoints sit at the
    64-gon inscribed radius.
    """
    import numpy as np
    import trimesh

    roller = one_piece_roller(asset_name)
    section = trimesh.intersections.mesh_plane(roller, plane_normal=[0.0, 0.0, 1.0], plane_origin=[0.0, 0.0, 0.0])
    points = section.reshape(-1, 3)
    assert len(points) > 0, 'no cross-section at mid-height'

    radial = np.hypot(points[:, 0], points[:, 1])
    inscribed = BARREL_RADIUS_MM * math.cos(math.pi / SHELL_SECTIONS)
    assert radial.max() == pytest.approx(BARREL_RADIUS_MM, abs=RIM_TOL_MM)
    assert radial.min() == pytest.approx(inscribed, abs=RIM_TOL_MM)


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_union_preserves_the_vendored_gear_surface(geometry_stack, asset_name):
    """
    Audit 11.4 - the union must fuse the gears in without deforming them. Every
    sampled point on the vendored asset has to land on the roller's surface,
    apart from the buried contact planes.
    """
    import numpy as np

    roller = one_piece_roller(asset_name)
    asset = load_gear_asset(asset_name)

    points, distances = surface_distances(asset, roller, 2000, seed=1234)
    external = outside_interface_band(points)
    assert external.sum() > 1000, 'too few sampled points left to be meaningful'
    assert np.max(distances[external]) <= SURFACE_TOL_MM

    # The excluded band is excluded for a reason, not to hide a defect: those
    # points are interior to the solid, which is exactly what fusing means.
    assert np.max(distances[~external]) > SURFACE_TOL_MM


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_tooth_count_and_phase_survive_the_union(geometry_stack, asset_name):
    """Audit 11.5 - 24 teeth at both ends, clocked exactly as the asset is."""
    roller = one_piece_roller(asset_name)
    asset = load_gear_asset(asset_name)

    for z_low, z_high in ((27.0, 35.0), (-35.0, -27.0)):
        roller_count, roller_phase = tooth_band_phase(roller.vertices, z_low, z_high)
        asset_count, asset_phase = tooth_band_phase(asset.vertices, z_low, z_high)
        assert roller_count == TOOTH_COUNT
        assert asset_count == TOOTH_COUNT
        assert roller_phase == pytest.approx(asset_phase, abs=PHASE_TOL_DEG)

    # Both gears of a set share one clocking (audit section 4: A1 = A2 to
    # 0.0000 deg), which is what lets the pair mesh top and bottom at once.
    top = tooth_band_phase(roller.vertices, 27.0, 35.0)[1]
    bottom = tooth_band_phase(roller.vertices, -35.0, -27.0)[1]
    assert top == pytest.approx(bottom, abs=PHASE_TOL_DEG)


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_union_volume_is_the_parts_plus_at_most_the_two_rings(geometry_stack, asset_name):
    """
    Audit 11.6. The barrel and the gears only touch - they do not overlap - so
    the fused volume is their sum, plus whatever of the weld rings was not
    already inside one of them. That gives a two-sided bracket rather than a
    single number, and the assertion is built from the measured pieces.
    """
    roller = one_piece_roller(asset_name)
    parts_volume = build_barrel().volume + load_gear_asset(asset_name).volume

    assert roller.volume >= parts_volume - VOLUME_TOL_MM3
    assert roller.volume <= parts_volume + 2.0 * WELD_RING_VOLUME_MM3 + VOLUME_TOL_MM3


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_weld_rings_are_invisible_from_outside(geometry_stack, asset_name):
    """
    Decision D-3 promised the rings change no external dimension. Prove it: the
    roller built without them has the same bounds and the same volume, so the
    rings are pure insurance against an exact-tangency union.
    """
    import trimesh

    with_rings = one_piece_roller(asset_name)
    without_rings = trimesh.boolean.union([build_barrel(), load_gear_asset(asset_name)], engine='manifold')

    assert with_rings.bounds == pytest.approx(without_rings.bounds, abs=BOUNDS_TOL_MM)
    assert with_rings.volume == pytest.approx(without_rings.volume, abs=VOLUME_TOL_MM3)


@pytest.mark.skipif(not SAMPLES_DIR.is_dir(), reason='reference roller samples are not on this machine')
@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_one_piece_roller_matches_the_original_roller_samples(geometry_stack, asset_name):
    """
    The deep check: does the roller we assemble actually match the roller
    Brennen exported? This is the ONLY test that can catch a wrong transform.
    The others compare the union against the same asset it was built from, and
    a 24-tooth ring is 15 deg periodic, so a wrong rotation still lands teeth
    on teeth - only the reference assembly knows where the bores, the handle
    connector and the barrel really sit.
    """
    import numpy as np
    import trimesh

    placement = SAMPLE_ROLLERS[asset_name]
    sample = trimesh.load_mesh(str(SAMPLES_DIR / placement['file']), process=False)
    sample.merge_vertices()
    # The samples ship as three kissing shells per roller - that is the state
    # this whole feature replaces.
    assert len(sample.split(only_watertight=False)) == 3

    vertices = np.array(sample.vertices, dtype=np.float64)
    vertices[:, 0] -= placement['axis_x_mm']
    vertices[:, 1] -= placement['axis_y_mm']
    if placement['rotation_z_deg'] == 180.0:
        vertices[:, 0] = -vertices[:, 0]
        vertices[:, 1] = -vertices[:, 1]
    vertices[:, 2] += Z_SHIFT_MM
    sample.vertices = vertices

    roller = one_piece_roller(asset_name)
    assert sample.bounds == pytest.approx(roller.bounds, abs=SAMPLE_BARREL_TOL_MM)

    points, distances = surface_distances(sample, roller, 4000, seed=99)
    z = points[:, 2]
    half_height = BARREL_HEIGHT_MM / 2.0
    gear_zone = np.abs(z) > half_height + INTERFACE_BAND_MM
    barrel_zone = np.abs(z) < half_height - INTERFACE_BAND_MM

    assert gear_zone.sum() > 1000
    assert np.percentile(distances[gear_zone], 99) <= SAMPLE_GEAR_P99_TOL_MM
    assert np.max(distances[gear_zone]) <= SAMPLE_GEAR_MAX_TOL_MM

    assert barrel_zone.sum() > 1000
    assert np.max(distances[barrel_zone]) <= SAMPLE_BARREL_TOL_MM


@pytest.mark.parametrize('asset_name', ASSET_NAMES)
def test_a_browser_generated_roller_carries_its_gears(geometry_stack, asset_name):
    """
    The end of the chain: an STL the Manifold worker produced in a real browser.

    Everything above measures Python's own union of the same parts. This checks
    the file a user would actually download - the worker fetched the vendored
    asset over HTTP, parsed the packed binary, and unioned it into a cylinder
    that also carries braille dots and tactile arrows.

    Skipped unless the environment names a file, because generating one needs a
    browser. See BROWSER_STL_ENV above.
    """
    import numpy as np
    import trimesh

    path = browser_stl_path(asset_name)
    if path is None:
        pytest.skip(f'set {BROWSER_STL_ENV[asset_name]} to a browser-generated gear-mode STL')
    assert path.is_file(), f'{BROWSER_STL_ENV[asset_name]} points at a missing file: {path}'

    roller = trimesh.load(str(path), file_type='stl', force='mesh')
    roller.merge_vertices()

    # Watertight overall. On a tactile plate this also pins decision D-8a:
    # without the gear-mode arrow weld the arrow tip-to-base tangency rounds
    # into pinch edges under float32 and the export is NOT watertight.
    assert roller.is_watertight

    bodies = roller.split(only_watertight=False)

    # NO SEALED CAVITY. A negative-volume body is an enclosed void - which is
    # what a hollow barrel plus the weld rings produced before the shell was
    # made solid in gear mode (measured -29253 mm3 in Chromium). D-2 exists to
    # prevent exactly that, and an empty polygon_points list does not achieve
    # it on its own.
    assert all(body.volume > 0 for body in bodies), 'a body with negative volume is a sealed void'

    # Exactly one body IS the roller: it must span the full 72 mm and carry
    # both gear bands.
    rollers = [body for body in bodies if body.bounds[1][2] - body.bounds[0][2] > 70.0]
    assert len(rollers) == 1
    solid = rollers[0]

    low, high = solid.bounds
    assert low[2] == pytest.approx(-36.0, abs=BOUNDS_TOL_MM)
    assert high[2] == pytest.approx(36.0, abs=BOUNDS_TOL_MM)

    for z_low, z_high in ((27.0, 35.0), (-35.0, -27.0)):
        count, _ = tooth_band_phase(solid.vertices, z_low, z_high)
        assert count == TOOTH_COUNT

    # Any OTHER body can only be one of the raised dot domes that this
    # generator has separated since before the gear beta: a known, recorded,
    # deliberately deferred second tangency inside every rounded dot. Pin its
    # signature so a NEW kind of loose body cannot hide behind it.
    for body in bodies:
        if body is solid:
            continue
        assert body.volume < 1.0
        assert body.is_watertight
        assert np.hypot(body.vertices[:, 0], body.vertices[:, 1]).min() >= BARREL_RADIUS_MM

    # The gears themselves came through the worker unchanged.
    asset = load_gear_asset(asset_name)
    points, distances = surface_distances(asset, solid, 2000, seed=4242)
    external = outside_interface_band(points)
    assert np.max(distances[external]) <= SURFACE_TOL_MM


# ---------------------------------------------------------------------------
# The geometry spec side: what app/geometry_spec.py emits for gear mode.
#
# These need no mesh library - they read the spec dict the worker will act on.
# ---------------------------------------------------------------------------

REFERENCE_CYLINDER_PARAMS = {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 355.0}
GEAR_ARROW_WELD_MM = 0.005  # D-8a
CUTOUT_WARNING = 'The polygonal cutout is not used while integrated gears are on.'  # S3


def build_spec(plate_type='positive', gears_on=True, tactile=True, cutout=False, back_lines=None, **overrides):
    from app.geometry_spec import extract_cylinder_geometry_spec
    from app.models import CardSettings
    from app.utils import braille_to_dots

    settings_data = {'grid_columns': 14 if tactile else 15, 'grid_rows': 4}
    if tactile:
        settings_data['indicator_mode'] = 'tactile'
    if gears_on:
        settings_data['gear_rollers_enabled'] = 1
    if back_lines is not None:
        settings_data.update(
            {
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
        )
    settings_data.update(overrides.pop('settings', {}))

    cylinder_params = dict(REFERENCE_CYLINDER_PARAMS, **overrides)
    if cutout:
        cylinder_params['polygonal_cutout_radius_mm'] = 13.0
        cylinder_params['polygonal_cutout_sides'] = 12

    return extract_cylinder_geometry_spec(
        ['⠁⠃⠉', '', '', ''],
        'g1',
        CardSettings(**settings_data),
        cylinder_params,
        None,
        plate_type,
        braille_to_dots_func=braille_to_dots,
        back_lines=back_lines,
    )


def test_no_gears_block_when_the_flag_is_off():
    for plate_type in ('positive', 'negative'):
        assert 'gears' not in build_spec(plate_type, gears_on=False)


@pytest.mark.parametrize('plate_type,expected_asset', [('positive', 'gears_a'), ('negative', 'gears_b')])
def test_each_plate_gets_its_own_gear_set(plate_type, expected_asset):
    """Cylinder A takes the A gears, Cylinder B the B ones - B's teeth are
    clocked to mesh with A's, so swapping them would stop the pair meshing."""
    assert build_spec(plate_type)['gears']['asset'] == expected_asset


def test_weld_rings_sit_at_the_two_gear_interfaces():
    rings = build_spec()['gears']['weld_rings']
    assert [ring['z_center'] for ring in rings] == [-26.0, 26.0]
    for ring in rings:
        assert (ring['r_in'], ring['r_out'], ring['height']) == (8.0, 13.0, 0.1)


def test_ring_z_follows_the_cylinder_height_rather_than_a_hardcoded_26():
    """
    The request route can only ever send 52.0 (validation rejects anything
    else), but the ring z is computed from height/2 so a future height change
    moves the rings with the barrel instead of stranding them.
    """
    from app.geometry import gears as gears_module

    assert [ring['z_center'] for ring in gears_module.weld_rings(60.0)] == [-30.0, 30.0]


def test_gear_mode_forces_the_barrel_solid_and_says_so():
    """D-2: the cutout is dropped while gears are on, with the signed S3 note."""
    with_cutout = build_spec(cutout=True)
    assert with_cutout['cylinder']['polygon_points'] == []
    assert CUTOUT_WARNING in with_cutout['warnings']


def test_no_cutout_warning_when_the_user_never_asked_for_one():
    assert CUTOUT_WARNING not in build_spec(cutout=False)['warnings']


def test_the_cutout_still_works_with_gears_off():
    """Toggle-off behavior is untouched: the 12-gon is still cut."""
    spec = build_spec(gears_on=False, cutout=True)
    assert len(spec['cylinder']['polygon_points']) == 12
    assert CUTOUT_WARNING not in spec['warnings']


def test_raised_arrows_get_the_gear_mode_weld_and_recesses_do_not():
    """
    D-8a. A 10 mm arrow on 10 mm line spacing touches its neighbour exactly,
    and float32 STL rounding turns that tangency into a pinch edge - which
    would break the watertight one-piece roller. 5 um makes it a real overlap.
    """
    raised = build_spec('positive')['markers']
    assert raised and all(marker['outline_delta'] == GEAR_ARROW_WELD_MM for marker in raised)
    assert all(marker['is_recess'] is False for marker in raised)

    recessed = build_spec('negative')['markers']
    assert recessed and all(marker['is_recess'] is True for marker in recessed)
    # The recess keeps its own 0.2 mm clearance growth, unchanged by gear mode.
    assert all(marker['outline_delta'] == 0.2 for marker in recessed)


def test_arrow_outlines_are_untouched_with_gears_off():
    assert all(marker['outline_delta'] == 0.0 for marker in build_spec('positive', gears_on=False)['markers'])
    assert all(marker['outline_delta'] == 0.2 for marker in build_spec('negative', gears_on=False)['markers'])


def test_gears_and_double_sided_coexist():
    """
    Both betas at once: every raised dot on A still meets exactly one recess on
    B, and both plates carry their own gear block. The pairing is a mirror -
    a dot at A's theta meets its recess at B's -theta - so this reuses
    interpoint.pairing_map, the same check the double-sided golden test makes.
    """
    from app.geometry import interpoint

    back_lines = ['⠙⠑⠋', '', '', '']
    plate_a = build_spec('positive', back_lines=back_lines)
    plate_b = build_spec('negative', back_lines=back_lines)

    assert plate_a['gears']['asset'] == 'gears_a'
    assert plate_b['gears']['asset'] == 'gears_b'
    assert plate_a['dots'] and plate_b['dots']

    for (dot_on_a, expected), dot_on_b in zip(interpoint.pairing_map(plate_a['dots']), plate_b['dots'], strict=True):
        assert dot_on_b['theta'] == expected['theta']
        assert dot_on_b['y'] == expected['y']
        assert dot_on_b['is_recess'] is not dot_on_a['is_recess']


def test_a_wrong_sized_cylinder_warns_when_validation_is_bypassed():
    """
    Direct callers - tests, the golden fixture generator - never go through
    app/validation.py, and a gear spec for the wrong barrel silently produces
    loose or swallowed gears. The spec says so instead.
    """
    spec = build_spec(height=45.0)
    assert any('matched to the reference roller' in warning for warning in spec['warnings'])
    assert build_spec()['warnings'] == []
