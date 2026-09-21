"""
Golden/regression tests for geometry specs (/geometry_spec).

The project now uses client-side CSG for STL generation; the backend is minimal
and only returns deterministic geometry specs (positions + parameters).

These tests validate the geometry spec response shape and key invariants to
catch unintended changes that would break client-side generation.
"""

import copy
import io
import json
import math
from pathlib import Path

import pytest

from app import geometry_spec
from app.geometry import interpoint, version2
from app.geometry_spec import extract_cylinder_geometry_spec
from app.models import CardSettings
from app.utils import braille_to_dots
from tests.test_gear_rollers import load_gear_asset, tooth_band_phase


@pytest.fixture(scope='module')
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / 'fixtures'


def load_fixture_metadata(fixtures_dir, fixture_name):
    """Load metadata for a golden fixture."""
    metadata_path = fixtures_dir / f'{fixture_name}.json'
    with open(metadata_path) as f:
        return json.load(f)


def _count_raised_dots(lines: list[str], max_cols: int | None = None) -> int:
    total = 0
    for line in lines:
        for col, ch in enumerate(line or ''):
            if max_cols is not None and col >= max_cols:
                break
            dots = braille_to_dots(ch)
            total += sum(1 for d in dots if d == 1)
    return total


def _expected_counts(payload: dict) -> tuple[int, int]:
    """
    Return (expected_dots, expected_markers) for /geometry_spec based on the
    behavior in app/geometry_spec.py.
    """
    settings = CardSettings(**payload.get('settings', {}))
    shape_type = payload.get('shape_type', 'card')
    plate_type = payload.get('plate_type', 'positive')
    lines = payload.get('lines', ['', '', '', ''])

    indicator_shapes = bool(getattr(settings, 'indicator_shapes', 1))
    # Triangle alignment markers are always created (1 per row); the indicator
    # letter/square marker (1 per row) is gated by the indicator_shapes toggle.
    expected_markers = settings.grid_rows * 2 if indicator_shapes else settings.grid_rows

    if shape_type == 'card':
        if plate_type == 'negative':
            expected_dots = settings.grid_rows * settings.grid_columns * 6
        else:
            expected_dots = _count_raised_dots(lines, max_cols=settings.grid_columns)
        return expected_dots, expected_markers

    # cylinder: 2 reserved columns with indicator letters on, 1 (triangle) when off
    reserved = 2 if indicator_shapes else 1
    max_text_cols = settings.grid_columns - reserved

    if plate_type == 'negative':
        expected_dots = settings.grid_rows * max_text_cols * 6
    else:
        expected_dots = _count_raised_dots(lines, max_cols=max_text_cols)

    return expected_dots, expected_markers


@pytest.mark.parametrize(
    'fixture_name',
    ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small'],
)
def test_golden_geometry_spec(client, fixtures_dir, fixture_name):
    """Validate /geometry_spec invariants for each fixture payload."""
    metadata = load_fixture_metadata(fixtures_dir, fixture_name)
    payload = metadata['request_payload']

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data is not None

    assert data.get('shape_type') == payload.get('shape_type')
    assert data.get('plate_type') == payload.get('plate_type')
    assert isinstance(data.get('dots'), list)
    assert isinstance(data.get('markers'), list)

    expected_dots, expected_markers = _expected_counts(payload)
    assert len(data['markers']) == expected_markers
    assert len(data['dots']) == expected_dots

    # Minimal structural validation on dot specs
    if data['shape_type'] == 'card':
        assert 'plate' in data
        if data['dots']:
            d0 = data['dots'][0]
            assert 'x' in d0 and 'y' in d0 and 'z' in d0
            assert 'type' in d0
            assert 'params' in d0 and isinstance(d0['params'], dict)
    else:
        assert 'cylinder' in data
        if data['dots']:
            d0 = data['dots'][0]
            assert 'x' in d0 and 'y' in d0 and 'z' in d0
            assert 'theta' in d0 and 'radius' in d0
            assert 'type' in d0
            assert 'params' in d0 and isinstance(d0['params'], dict)


@pytest.mark.parametrize(
    'fixture_name',
    ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small'],
)
def test_golden_specs_ignore_an_absent_or_off_double_sided_flag(client, fixtures_dir, fixture_name):
    """
    Beta isolation: the double-sided toggle at 0 must be indistinguishable from
    the toggle not existing. Every pre-beta payload omits it, so both forms have
    to produce byte-identical /geometry_spec responses for the golden inputs.
    """
    metadata = load_fixture_metadata(fixtures_dir, fixture_name)
    payload = metadata['request_payload']

    baseline = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert baseline.status_code == 200, baseline.data

    off_payload = copy.deepcopy(payload)
    off_payload.setdefault('settings', {})['double_sided_enabled'] = 0
    toggled_off = client.post('/geometry_spec', json=off_payload, headers={'Content-Type': 'application/json'})
    assert toggled_off.status_code == 200, toggled_off.data

    assert toggled_off.get_json() == baseline.get_json()


# ---------------------------------------------------------------------------
# Double-sided (interpoint) beta golden pair
#
# The STL fixtures ds_cylinderA_golden.stl / ds_cylinderB_golden.stl pin the
# paired-cylinder geometry of the double-sided beta. They are rendered from the
# /geometry_spec output with trimesh + manifold3d (dev-only dependencies), in
# the repo's Python Z-up convention: theta is used as emitted, the base ends at
# z = 0. The browser workers negate theta for Three.js; the pairing mirror
# (A at theta, B at -theta) is unaffected by that global sign.
#
# Bowls are cut with the shipping worker's centre-on-surface convention (cut
# depth = sphere radius, mouth = its diameter), NOT the exact-depth Python
# convention - decided 2026-08-19 (the app's geometry is what has been
# printed and embossed); fixtures regenerated 2026-08-20, and again on
# 2026-09-20 when the 0.3 mm preset's tactile arrows became three fixed ones.
#
# The specs are built by calling extract_cylinder_geometry_spec directly:
# back_lines has no request route until the backend plumbing phase lands.
# ---------------------------------------------------------------------------

DS_FIXTURE_FRONT_LINES = ['⠁⠃⠉', '', '', '']  # 1 + 2 + 2 = 5 raised dots
DS_FIXTURE_BACK_LINES = ['⠙⠑⠋', '', '', '']  # 3 + 2 + 3 = 8 raised dots
DS_FIXTURE_SETTINGS = {
    # The golden pairs are 14-column geometry references, not 90 mm card rows:
    # since the card-fit check (D-T4, 2026-09-21) a 14-cell tactile row warns
    # that it runs off a 90 mm card, and the generator refuses a fixture spec
    # with warnings. Declared for a 100 mm card, which the gear and Version 2
    # settings inherit by spreading this dict. The warning itself is pinned in
    # tests/test_smoke.py.
    'card_width': 100.0,
    'grid_columns': 14,
    'grid_rows': 4,
    'indicator_mode': 'tactile',
    # The ds_* package below is the 0.3 mm card-stock preset's, and since
    # 2026-09-20 that preset marks its cylinders with three fixed seam arrows
    # (mid-height and 15 mm either side) instead of one per row - so the pair
    # carries the layout the UI sends for it. Regenerated the same day.
    'tactile_indicator_layout': 'three_spaced',
    'double_sided_enabled': 1,
    'interpoint_offset_x': 1.25,
    'interpoint_offset_y': 1.25,
    'ds_dot_base_diameter': 1.2,
    'ds_dot_base_height': 0.4,
    'ds_dot_dome_diameter': 0.8,
    'ds_dot_dome_height': 0.4,
    'ds_bowl_base_diameter': 1.3,
    'ds_bowl_depth': 0.5,
}
DS_FIXTURE_CYLINDER_PARAMS = {'diameter': 30.75, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 355.0}
DS_FIXTURE_NAMES = {'positive': 'ds_cylinderA_golden', 'negative': 'ds_cylinderB_golden'}

# Renderer resolution. Shell and band share one segment count so their radial
# difference is constant (same reasoning as the Manifold worker's 64); the
# frustum matches dot_shapes.py's 48; icosphere level 3 keeps the touched
# dome/bowl surfaces smooth.
_DS_SHELL_SECTIONS = 64
_DS_FRUSTUM_SECTIONS = 48
_DS_SPHERE_SUBDIVISIONS = 3
# Radial overlap between a raised feature and the curved shell, so unions join
# solid material instead of touching along a line (must exceed the 64-segment
# chord sagitta of about 0.019 mm at radius 15.375 mm).
_DS_EMBED_MM = 0.05
# Outline growth for RAISED arrows only. At the default 10 mm indicator length
# on 10 mm line spacing, each arrow's apex touches the next arrow's base
# exactly; float32 STL rounding welds that tangency into a non-manifold pinch
# edge. 5 µm turns it into a true overlap (recess outlines already overlap via
# their 0.2 mm clearance growth). Physically negligible: 2.5% of the nesting
# clearance, far below the 0.1 mm print accuracy.
_DS_ARROW_WELD_MM = 0.005


def _ds_fixture_spec(plate_type):
    """Geometry spec for one side of the double-sided golden pair."""
    settings = CardSettings(**DS_FIXTURE_SETTINGS)
    return extract_cylinder_geometry_spec(
        DS_FIXTURE_FRONT_LINES,
        'g1',
        settings,
        DS_FIXTURE_CYLINDER_PARAMS,
        None,
        plate_type,
        braille_to_dots_func=braille_to_dots,
        back_lines=DS_FIXTURE_BACK_LINES,
    )


def _offset_polygon_miter(points, delta):
    """
    Mitered outward offset of a counter-clockwise outline.

    Port of the Manifold worker's offsetPolygonMiter: each vertex becomes the
    intersection of its two adjacent edges after both are pushed out by delta,
    which keeps the arrow apex sharp instead of rounding or squaring it.
    """
    if not delta:
        return list(points)
    count = len(points)
    edges = []
    for i in range(count):
        px, py = points[i]
        qx, qy = points[(i + 1) % count]
        ex, ey = qx - px, qy - py
        norm = math.hypot(ex, ey) or 1.0
        ex, ey = ex / norm, ey / norm
        edges.append((px + delta * ey, py - delta * ex, ex, ey))
    result = []
    for i in range(count):
        ax, ay, aex, aey = edges[(i - 1) % count]
        bx, by, bex, bey = edges[i]
        denom = aex * bey - aey * bex
        if abs(denom) < 1e-9:
            result.append((bx, by))
            continue
        t = ((bx - ax) * bey - (by - ay) * bex) / denom
        result.append((ax + t * aex, ay + t * aey))
    return result


def _ds_rounded_dot_meshes(dot):
    """Frustum + dome for one raised dot, placed on the shell in Z-up coordinates."""
    import numpy as np
    import trimesh

    params = dot['params']
    base_radius = params['base_radius']
    top_radius = params['top_radius']
    base_height = params['base_height']
    dome_height = params['dome_height']
    dome_radius = params['dome_radius']
    if base_height <= 0:
        raise ValueError('ds golden renderer expects a frustum base under every raised dot')

    # Extend the frustum below z=0 with the same linear taper: the skirt sinks
    # into the shell so the union overlaps solid material.
    skirt_radius = base_radius + (base_radius - top_radius) * _DS_EMBED_MM / base_height
    total_height = base_height + _DS_EMBED_MM
    frustum = trimesh.creation.cylinder(radius=skirt_radius, height=total_height, sections=_DS_FRUSTUM_SECTIONS)
    frustum.apply_translation([0.0, 0.0, total_height / 2.0 - _DS_EMBED_MM])
    top_z = frustum.vertices[:, 2].max()
    is_top = np.isclose(frustum.vertices[:, 2], top_z)
    frustum.vertices[is_top, :2] *= top_radius / skirt_radius

    dome = trimesh.creation.icosphere(subdivisions=_DS_SPHERE_SUBDIVISIONS, radius=dome_radius)
    dome.apply_translation([0.0, 0.0, base_height + dome_height - dome_radius])

    theta = dot['theta']
    tangent_axis = np.array([-math.sin(theta), math.cos(theta), 0.0])
    to_radial = trimesh.transformations.rotation_matrix(math.pi / 2.0, tangent_axis)
    base_center = np.array([dot['radius'] * math.cos(theta), dot['radius'] * math.sin(theta), dot['y']])
    parts = []
    for part in (frustum, dome):
        part.apply_transform(to_radial)
        part.apply_translation(base_center)
        parts.append(part)
    return parts


def _ds_bowl_cutter(dot):
    """
    Bowl sphere centred ON the shell surface (the shipping worker convention).

    csg-worker-manifold.js sets radialOffset = cylRadius, so the printed bowl
    is a hemisphere of radius sphere_radius: the cut is sphere_radius deep
    and 2 * sphere_radius across, and bowl_depth sets NEITHER directly.
    """
    import trimesh

    params = dot['params']
    bowl_radius = params['bowl_radius']
    bowl_depth = params['bowl_depth']
    sphere_radius = (bowl_radius * bowl_radius + bowl_depth * bowl_depth) / (2.0 * bowl_depth)
    sphere = trimesh.creation.icosphere(subdivisions=_DS_SPHERE_SUBDIVISIONS, radius=sphere_radius)
    theta = dot['theta']
    center_radius = dot['radius']
    sphere.apply_translation([center_radius * math.cos(theta), center_radius * math.sin(theta), dot['y']])
    return sphere


def _ds_tactile_arrow_mesh(marker):
    """
    Arrow outline extruded radially, clipped to the concentric shell band.

    Same construction as the Manifold worker (and the OpenSCAD modules it
    ports): the band intersection is what makes the raise/recess depth radially
    uniform across the arrow.
    """
    import numpy as np
    import trimesh
    from shapely.geometry import Polygon

    width = marker['width']
    length = marker['length']
    # Gear mode puts the same 5 um weld in the SPEC (decision D-8a), so adding
    # the renderer's own would double it. When the spec already grew a raised
    # arrow, its value is the whole story.
    spec_delta = marker['outline_delta']
    if marker['is_recess'] or spec_delta:
        delta = spec_delta
    else:
        delta = spec_delta + _DS_ARROW_WELD_MM
    span = marker['prism_span']
    outline = _offset_polygon_miter(
        [(-width / 2.0, -length / 2.0), (width / 2.0, -length / 2.0), (0.0, length / 2.0)], delta
    )
    prism = trimesh.creation.extrude_polygon(Polygon(outline), height=span)
    prism.apply_translation([0.0, 0.0, -span / 2.0])

    theta = marker['theta']
    place = np.eye(4)
    place[:3, 0] = [-math.sin(theta), math.cos(theta), 0.0]  # outline x -> circumferential
    place[:3, 1] = [0.0, 0.0, 1.0]  # outline y -> toward the cylinder top
    place[:3, 2] = [math.cos(theta), math.sin(theta), 0.0]  # extrusion -> radially outward
    place[:3, 3] = [marker['radius'] * math.cos(theta), marker['radius'] * math.sin(theta), marker['y']]
    prism.apply_transform(place)

    band = trimesh.creation.annulus(
        r_min=marker['inner_radius'],
        r_max=marker['outer_radius'],
        height=length + 2.0 * delta + 2.0,
        sections=_DS_SHELL_SECTIONS,
    )
    band.apply_translation([0.0, 0.0, marker['y']])
    return trimesh.boolean.intersection([prism, band], engine='manifold')


def _seam_channel_cutter(channel, radius, height):
    """
    The slicer seam channel's cutter: a V cross-section in the radial /
    circumferential plane, extruded the barrel height plus the overshoot at
    both ends, at the spec's theta AS EMITTED (this renderer's convention for
    every dot and marker; the worker places it at -theta like every dot).

    Port of scripts/seam_spike.py channel_cutter, the shape the 2026-09-20
    slicing spike measured, and of csg-worker-manifold.js
    createSeamChannelManifold: the V's sides are extended outward to the lip
    so the mouth is cut rather than touched.
    """
    import trimesh
    from shapely.geometry import Polygon

    width, depth, lip, overshoot = channel['width'], channel['depth'], channel['lip'], channel['overshoot']
    r_out = radius + lip
    half_mouth = (width / 2.0) * (depth + lip) / depth
    section = [(r_out, -half_mouth), (r_out, half_mouth), (radius - depth, 0.0)]
    theta = channel['theta']
    c, s = math.cos(theta), math.sin(theta)
    outline = Polygon([(u * c - v * s, u * s + v * c) for u, v in section])
    # Full height plus the overshoot, or - tactile mode, D-T6 - the stretches
    # outside the arrow chain the spec lists (createSeamChannelManifold does
    # the same).
    full = height + 2.0 * overshoot
    spans = [(seg['z_from'], seg['z_to']) for seg in channel.get('segments', [])] or [(-full / 2.0, full / 2.0)]
    prisms = []
    for z_from, z_to in spans:
        prism = trimesh.creation.extrude_polygon(outline, height=z_to - z_from)
        prism.apply_translation([0.0, 0.0, z_from])
        prisms.append(prism)
    return trimesh.util.concatenate(prisms) if len(prisms) > 1 else prisms[0]


def _build_ds_cylinder_mesh(spec, shell=None):
    """
    Render a double-sided cylinder spec to a watertight mesh.

    Booleans go straight to the manifold engine so any backend problem raises
    instead of silently degrading — a golden must fail loudly. Raised features
    union in before recesses cut, matching the worker's ordering, so a recess
    can never be filled back in.

    `shell` lets Embosser Version 2 hand in its own barrel, already keyed and
    countersunk. Left None this builds the plain solid barrel it always has, so
    the double-sided and gear pairs regenerate byte-identical.
    """
    import trimesh

    cylinder = spec['cylinder']
    radius = cylinder['radius']
    height = cylinder['height']
    if cylinder['polygon_points']:
        raise ValueError('ds golden renderer models a solid shell; drop the polygonal cutout from the fixture params')

    # A SOLID shell, which is also what gear mode needs. csg-worker-manifold.js
    # hollows the barrel by wall thickness unless the spec carries gears, in
    # which case it builds a solid one too (decision D-2) - so in gear mode this
    # renderer and the worker agree by construction rather than by luck. For
    # NON-gear specs they do not: this has always modelled a solid barrel where
    # the worker makes a tube. That predates the gear beta and is left alone.
    if shell is None:
        shell = trimesh.creation.cylinder(radius=radius, height=height, sections=_DS_SHELL_SECTIONS)

    # Slicer seam channel (2026-09-20 programme): cut from the bare shell
    # FIRST, before any raised feature joins, exactly where the worker cuts it,
    # so nothing added later can be undercut. Absent key, absent cut - the
    # pre-channel bytes. All three families pass through here, so one place
    # gives every pair the same groove.
    channel = cylinder.get('seam_channel')
    if channel:
        cutter = _seam_channel_cutter(channel, radius, height)
        shell = trimesh.boolean.difference([shell, cutter], engine='manifold')
    raised = [shell]

    # Gear-integrated one-piece rollers (BETA): the vendored gear pair plus its
    # two hidden weld rings, unioned in with the other raised features so the
    # recess-last order is untouched.
    gears_block = spec.get('gears')
    if gears_block:
        raised.append(load_gear_asset(gears_block['asset']))
        for ring in gears_block['weld_rings']:
            band = trimesh.creation.annulus(
                r_min=ring['r_in'], r_max=ring['r_out'], height=ring['height'], sections=_DS_SHELL_SECTIONS
            )
            band.apply_translation([0.0, 0.0, ring['z_center']])
            raised.append(band)
        # Fused Version 2 (decision D-6): each top gear's anti-rotation notch is
        # filled with hidden material so the solid barrel cannot seal a void
        # under it. The same prism the worker's keyedPrismManifold builds.
        for fill in gears_block.get('notch_fills', []):
            from shapely.geometry import Polygon

            prism = trimesh.creation.extrude_polygon(
                Polygon([(point['x'], point['y']) for point in fill['profile']]), height=fill['z_to'] - fill['z_from']
            )
            prism.apply_translation([0.0, 0.0, fill['z_from']])
            raised.append(prism)
    cutters = []
    for marker in spec['markers']:
        if marker['type'] != 'cylinder_tactile_arrow':
            raise ValueError(f'unexpected marker type {marker["type"]!r} in a double-sided spec')
        arrow = _ds_tactile_arrow_mesh(marker)
        (cutters if marker['is_recess'] else raised).append(arrow)
    for dot in spec['dots']:
        if dot['is_recess']:
            cutters.append(_ds_bowl_cutter(dot))
        else:
            raised.extend(_ds_rounded_dot_meshes(dot))

    solid = trimesh.boolean.union(raised, engine='manifold')
    # A single-sided EMBOSS plate cuts nothing: its dots and its tactile arrows
    # are all raised. Both beta pairs are double-sided, which always leaves
    # recesses on both plates, so this was unreachable until Version 2 - and
    # trimesh's manifold union returns None for an empty list rather than
    # raising, which surfaces two frames later as an AttributeError.
    if cutters:
        solid = trimesh.boolean.difference(
            [solid, trimesh.boolean.union(cutters, engine='manifold')], engine='manifold'
        )
    # Fixture convention: reseat so the barrel's base sits at z = 0. In gear
    # mode that puts the gears at z -10..0 and 52..62 - the sample assembly's
    # own frame - so a geared fixture spans z -10..62, not 0..52.
    solid.apply_translation([0.0, 0.0, height / 2.0])
    return _stabilize_for_stl(solid)


def _stabilize_for_stl(mesh):
    """
    Make the mesh survive STL's float32 precision.

    CSG output carries sliver faces on intersection curves that collapse when
    vertices round to float32, leaving degenerate topology in the written file.
    Quantize to float32 up front, weld, and drop the collapsed faces, so the
    exported bytes reload watertight. Fails loudly if that isn't achieved —
    a golden fixture with broken topology would poison every later comparison.
    """
    import numpy as np

    for _ in range(4):
        mesh.vertices = mesh.vertices.astype(np.float32).astype(np.float64)
        mesh.merge_vertices()
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        if mesh.is_watertight:
            return mesh
    raise ValueError('mesh did not stabilize to a watertight float32 STL')


def generate_ds_golden_fixtures():
    """
    Regenerate the double-sided golden STL pair and its metadata.

    Run manually (python -m tests.test_golden from the repo root) — never from
    the test suite. This is the only supported way to regenerate the pair.
    Existing single-sided fixtures are not touched.
    """
    import importlib.metadata

    fixtures_dir = Path(__file__).parent / 'fixtures'
    for plate_type, fixture_name in DS_FIXTURE_NAMES.items():
        spec = _ds_fixture_spec(plate_type)
        if spec['warnings']:
            raise ValueError(f'fixture spec for {fixture_name} has warnings: {spec["warnings"]}')
        mesh = _build_ds_cylinder_mesh(spec)
        stl_bytes = mesh.export(file_type='stl')
        (fixtures_dir / f'{fixture_name}.stl').write_bytes(stl_bytes)

        metadata = {
            'description': (
                f'Double-sided (interpoint) beta golden: Cylinder {"A" if plate_type == "positive" else "B"} '
                f'({plate_type}) of the paired set'
            ),
            'fixture_name': fixture_name,
            'plate_type': plate_type,
            'generation': {
                'note': (
                    'Rendered by tests/test_golden.py generate_ds_golden_fixtures() from '
                    'extract_cylinder_geometry_spec called directly with back_lines= (no request route yet). '
                    'Z-up, theta as emitted; browser workers negate theta for Three.js. '
                    'Bowls are cut centre-on-surface (the shipping worker convention). '
                    'Since 2026-09-20 the barrel also carries the slicer seam channel, a V 1.0 x 0.5 mm '
                    'groove cut from the bare shell at cylinder.seam_channel.theta before anything joins.'
                ),
                'front_lines': DS_FIXTURE_FRONT_LINES,
                'back_lines': DS_FIXTURE_BACK_LINES,
                'settings': DS_FIXTURE_SETTINGS,
                'cylinder_params': DS_FIXTURE_CYLINDER_PARAMS,
                'generated': '2026-09-20',
                'trimesh_version': importlib.metadata.version('trimesh'),
                'manifold3d_version': importlib.metadata.version('manifold3d'),
            },
            # Informational snapshot; the test compares against the STL itself
            # with tolerances, because face counts may differ across manifold3d
            # versions even when the geometry is identical.
            'expected_properties': {
                'face_count': len(mesh.faces),
                'vertex_count': len(mesh.vertices),
                'is_watertight': bool(mesh.is_watertight),
                'bbox_min': mesh.bounds[0].tolist(),
                'bbox_max': mesh.bounds[1].tolist(),
                'volume': float(mesh.volume),
                'surface_area': float(mesh.area),
            },
        }
        (fixtures_dir / f'{fixture_name}.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        print(
            f'{fixture_name}: {len(mesh.faces)} faces, volume {mesh.volume:.3f} mm^3, watertight {mesh.is_watertight}'
        )


def test_ds_golden_pair_is_paired_dot_for_recess_with_a_printable_gap():
    """
    The fixture pair must satisfy the double-sided contract: every raised dot
    on one cylinder meets exactly one recess at -theta on the other, and the
    Option-B footprints leave a printable same-surface ridge (>= 0.50 mm).
    """
    plate_a = _ds_fixture_spec('positive')
    plate_b = _ds_fixture_spec('negative')

    for spec in (plate_a, plate_b):
        assert spec['warnings'] == []
        assert spec['indicator_mode'] == 'tactile'
        # Three fixed arrows, the 0.3 mm preset's marking - not one per row
        assert [m['type'] for m in spec['markers']] == ['cylinder_tactile_arrow'] * 3
        assert [m['y'] for m in spec['markers']] == [15.0, 0.0, -15.0]

    front_dots = sum(sum(braille_to_dots(char)) for char in DS_FIXTURE_FRONT_LINES[0])
    back_dots = sum(sum(braille_to_dots(char)) for char in DS_FIXTURE_BACK_LINES[0])
    assert (front_dots, back_dots) == (5, 8)

    # Front features first, then back — on both plates, in the same order.
    assert [dot['is_recess'] for dot in plate_a['dots']] == [False] * front_dots + [True] * back_dots
    assert [dot['is_recess'] for dot in plate_b['dots']] == [True] * front_dots + [False] * back_dots

    # Positions are distinct on each plate, so the exact index-for-index mirror
    # below means every male has exactly ONE recess partner and vice versa.
    for spec in (plate_a, plate_b):
        positions = [(dot['theta'], dot['y']) for dot in spec['dots']]
        assert len(set(positions)) == len(positions)

    for (dot_on_a, expected), dot_on_b in zip(interpoint.pairing_map(plate_a['dots']), plate_b['dots'], strict=True):
        assert dot_on_b['theta'] == expected['theta']
        assert dot_on_b['y'] == expected['y']
        assert dot_on_b['is_recess'] is not dot_on_a['is_recess']

    # The fixture pins the signed-off values: D1 offset and Option-B footprints.
    assert DS_FIXTURE_SETTINGS['interpoint_offset_x'] == interpoint.INTERPOINT_OFFSET_X_MM
    assert DS_FIXTURE_SETTINGS['interpoint_offset_y'] == interpoint.INTERPOINT_OFFSET_Z_MM
    assert DS_FIXTURE_SETTINGS['ds_dot_base_diameter'] == interpoint.DS_DOT_BASE_DIAMETER_MM
    assert DS_FIXTURE_SETTINGS['ds_bowl_base_diameter'] == interpoint.DS_BOWL_DIAMETER_MM

    settings = CardSettings(**DS_FIXTURE_SETTINGS)
    gap = interpoint.same_surface_min_gap(
        settings.ds_dot_base_diameter,
        settings.ds_bowl_base_diameter,
        settings.interpoint_offset_x,
        settings.interpoint_offset_y,
        settings.grid_columns,  # tactile mode reserves no marker columns
        settings.grid_rows,
        settings.dot_spacing,
        settings.cell_spacing,
        settings.line_spacing,
    )
    assert gap >= interpoint.SAME_SURFACE_GAP_RELIABLE_MM


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_ds_golden_fixture_metadata_records_the_module_inputs(fixtures_dir, plate_type):
    """Fixture metadata and the inputs the test regenerates from cannot drift apart."""
    metadata = load_fixture_metadata(fixtures_dir, DS_FIXTURE_NAMES[plate_type])
    generation = metadata['generation']
    assert generation['front_lines'] == DS_FIXTURE_FRONT_LINES
    assert generation['back_lines'] == DS_FIXTURE_BACK_LINES
    assert generation['settings'] == DS_FIXTURE_SETTINGS
    assert generation['cylinder_params'] == DS_FIXTURE_CYLINDER_PARAMS


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_ds_golden_fixture_matches_regenerated_geometry(fixtures_dir, plate_type):
    """
    The committed STL must match a fresh render of today's geometry spec, and
    must physically carry every dot, recess and arrow where the spec puts it.
    """
    trimesh = pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    pytest.importorskip('shapely')
    import numpy as np

    fixture_name = DS_FIXTURE_NAMES[plate_type]
    fixture_mesh = trimesh.load(str(fixtures_dir / f'{fixture_name}.stl'), file_type='stl', force='mesh')

    spec = _ds_fixture_spec(plate_type)
    rebuilt = _build_ds_cylinder_mesh(spec)
    # Round-trip through STL bytes so both meshes carry the same float32 rounding.
    rebuilt = trimesh.load(io.BytesIO(rebuilt.export(file_type='stl')), file_type='stl', force='mesh')

    assert fixture_mesh.is_watertight
    assert rebuilt.is_watertight
    # One raised dot is ~0.4 mm^3 and ~2.5 mm^2, so these tolerances catch any
    # moved, missing or resized feature while shrugging off float noise.
    assert fixture_mesh.volume == pytest.approx(rebuilt.volume, abs=0.02)
    assert fixture_mesh.area == pytest.approx(rebuilt.area, abs=0.2)
    assert fixture_mesh.bounds == pytest.approx(rebuilt.bounds, abs=1e-3)

    half_height = spec['cylinder']['height'] / 2.0

    def surface_point(theta, radial, z_local):
        return (radial * math.cos(theta), radial * math.sin(theta), z_local + half_height)

    inside_points = []
    outside_points = []
    for dot in spec['dots']:
        theta, y_local, radius = dot['theta'], dot['y'], dot['radius']
        if dot['is_recess']:
            bowl_radius = dot['params']['bowl_radius']
            bowl_depth = dot['params']['bowl_depth']
            # Centre-on-surface: the cut is a hemisphere sphere-radius deep,
            # not bowl_depth deep - probe against the depth actually cut.
            cut_depth = (bowl_radius**2 + bowl_depth**2) / (2.0 * bowl_depth)
            outside_points.append(surface_point(theta, radius - cut_depth / 2.0, y_local))
            inside_points.append(surface_point(theta, radius - cut_depth - 0.2, y_local))
        else:
            dot_height = dot['params']['base_height'] + dot['params']['dome_height']
            inside_points.append(surface_point(theta, radius + 0.75 * dot_height, y_local))
            outside_points.append(surface_point(theta, radius + dot_height + 0.1, y_local))
    for marker in spec['markers']:
        theta, y_local, radius = marker['theta'], marker['y'], marker['radius']
        if marker['is_recess']:
            outside_points.append(surface_point(theta, (radius + marker['inner_radius']) / 2.0, y_local))
            inside_points.append(surface_point(theta, marker['inner_radius'] - 0.1, y_local))
        else:
            inside_points.append(surface_point(theta, (radius + marker['outer_radius']) / 2.0, y_local))
            outside_points.append(surface_point(theta, marker['outer_radius'] + 0.1, y_local))

    assert fixture_mesh.contains(np.array(inside_points)).all()
    assert not fixture_mesh.contains(np.array(outside_points)).any()


# ---------------------------------------------------------------------------
# Gear-integrated one-piece rollers (BETA) golden pair
#
# Same inputs as the double-sided pair, with gears on, so one fixture covers
# both betas at once. Two deliberate differences from the DS pair:
#
#   * the cylinder is 30.8 mm, not 30.75. The vendored gears were measured
#     against a 15.400 mm radius barrel, and app/validation.py hard-rejects
#     anything else while gears are on (decision S7, signed 2026-08-24). At
#     30.75 app/geometry_spec.py emits a warning, and a spec carrying warnings
#     cannot be turned into a fixture at all.
#   * the roller spans z -10..62, not 0..52: the gears sit outside the barrel
#     at both ends, which is what makes it a 72 mm one-piece part.
# ---------------------------------------------------------------------------

# The double-sided pair's three-arrow layout is NOT inherited here: only that
# pair was approved for regeneration on 2026-09-20, so the gear pair keeps its
# per-row arrows and its fixtures stay byte-identical (the key is dropped, not
# set to 'per_row', so the recorded settings do not change either).
GEAR_FIXTURE_SETTINGS = {
    **{key: value for key, value in DS_FIXTURE_SETTINGS.items() if key != 'tactile_indicator_layout'},
    'gear_rollers_enabled': 1,
}
GEAR_FIXTURE_CYLINDER_PARAMS = {**DS_FIXTURE_CYLINDER_PARAMS, 'diameter': 30.8}
GEAR_FIXTURE_NAMES = {'positive': 'gear_rollerA_golden', 'negative': 'gear_rollerB_golden'}
GEAR_FIXTURE_ASSETS = {'positive': 'gears_a', 'negative': 'gears_b'}

_GEAR_TOOTH_COUNT = 24
_GEAR_TIP_RADIUS_MM = 16.1093702290795
# The roller in the fixture frame: barrel 0..52 with a 10 mm gear at each end.
_GEAR_FIXTURE_Z_MIN = -10.0
_GEAR_FIXTURE_Z_MAX = 62.0


def _gear_fixture_spec(plate_type):
    """Geometry spec for one side of the gear-mode golden pair."""
    settings = CardSettings(**GEAR_FIXTURE_SETTINGS)
    return extract_cylinder_geometry_spec(
        DS_FIXTURE_FRONT_LINES,
        'g1',
        settings,
        GEAR_FIXTURE_CYLINDER_PARAMS,
        None,
        plate_type,
        braille_to_dots_func=braille_to_dots,
        back_lines=DS_FIXTURE_BACK_LINES,
    )


def generate_gear_golden_fixtures():
    """
    Regenerate the gear-mode golden STL pair and its metadata.

    Run manually (python -m tests.test_golden from the repo root) - never from
    the test suite, and only when a geometry change is intended. Existing
    fixtures, single-sided and double-sided alike, are not touched.
    """
    import importlib.metadata

    fixtures_dir = Path(__file__).parent / 'fixtures'
    for plate_type, fixture_name in GEAR_FIXTURE_NAMES.items():
        spec = _gear_fixture_spec(plate_type)
        if spec['warnings']:
            raise ValueError(f'fixture spec for {fixture_name} has warnings: {spec["warnings"]}')
        mesh = _build_ds_cylinder_mesh(spec)
        (fixtures_dir / f'{fixture_name}.stl').write_bytes(mesh.export(file_type='stl'))

        metadata = {
            'description': (
                f'Gear-integrated one-piece roller BETA golden: {"Cylinder A" if plate_type == "positive" else "Cylinder B"} '
                f'({plate_type}), barrel plus its top and bottom gears as one part'
            ),
            'fixture_name': fixture_name,
            'plate_type': plate_type,
            'generation': {
                'note': (
                    'Rendered by tests/test_golden.py generate_gear_golden_fixtures() from '
                    'extract_cylinder_geometry_spec called directly with back_lines= and '
                    'gear_rollers_enabled=1, so this pair covers the gear beta ON TOP of the '
                    'double-sided one. Z-up, theta as emitted, base of the barrel reseated to '
                    'z=0 - which puts the gears at z -10..0 and 52..62. The gear geometry is '
                    'the vendored asset from static/assets/gears/, unmodified: the sample-to-'
                    'program transform is already baked into those bytes. Since 2026-09-20 the '
                    'barrel also carries the slicer seam channel (V 1.0 x 0.5 mm, cut from the bare '
                    'shell before the gears join, so the gear discs fill its overshoot).'
                ),
                'cylinder_diameter_note': (
                    'ds_cylinder*_golden uses 30.75 mm; this pair uses 30.8 mm because the '
                    'vendored gears were measured against a 15.400 mm radius barrel and gear '
                    'mode rejects any other size (S7, signed 2026-08-24).'
                ),
                'gear_asset': GEAR_FIXTURE_ASSETS[plate_type],
                'front_lines': DS_FIXTURE_FRONT_LINES,
                'back_lines': DS_FIXTURE_BACK_LINES,
                'settings': GEAR_FIXTURE_SETTINGS,
                'cylinder_params': GEAR_FIXTURE_CYLINDER_PARAMS,
                'generated': '2026-09-20',
                'trimesh_version': importlib.metadata.version('trimesh'),
                'manifold3d_version': importlib.metadata.version('manifold3d'),
            },
            'expected_properties': {
                'face_count': len(mesh.faces),
                'vertex_count': len(mesh.vertices),
                'is_watertight': bool(mesh.is_watertight),
                'bbox_min': mesh.bounds[0].tolist(),
                'bbox_max': mesh.bounds[1].tolist(),
                'volume': float(mesh.volume),
                'surface_area': float(mesh.area),
            },
        }
        (fixtures_dir / f'{fixture_name}.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        print(
            f'{fixture_name}: {len(mesh.faces)} faces, volume {mesh.volume:.3f} mm^3, '
            f'watertight {mesh.is_watertight}, z {mesh.bounds[0][2]:.3f}..{mesh.bounds[1][2]:.3f}'
        )


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_gear_golden_fixture_metadata_records_the_module_inputs(fixtures_dir, plate_type):
    """Fixture metadata and the inputs the test regenerates from cannot drift apart."""
    metadata = load_fixture_metadata(fixtures_dir, GEAR_FIXTURE_NAMES[plate_type])
    generation = metadata['generation']
    assert generation['front_lines'] == DS_FIXTURE_FRONT_LINES
    assert generation['back_lines'] == DS_FIXTURE_BACK_LINES
    assert generation['settings'] == GEAR_FIXTURE_SETTINGS
    assert generation['cylinder_params'] == GEAR_FIXTURE_CYLINDER_PARAMS
    assert generation['gear_asset'] == GEAR_FIXTURE_ASSETS[plate_type]
    # The two betas' fixtures MUST differ here, and the reason is recorded.
    assert generation['cylinder_params']['diameter'] == 30.8
    assert DS_FIXTURE_CYLINDER_PARAMS['diameter'] == 30.75


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_gear_golden_fixture_matches_regenerated_geometry(fixtures_dir, plate_type):
    """The committed roller must match a fresh render of today's gear-mode spec."""
    trimesh = pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    pytest.importorskip('shapely')

    fixture_name = GEAR_FIXTURE_NAMES[plate_type]
    fixture_mesh = trimesh.load(str(fixtures_dir / f'{fixture_name}.stl'), file_type='stl', force='mesh')

    spec = _gear_fixture_spec(plate_type)
    rebuilt = _build_ds_cylinder_mesh(spec)
    rebuilt = trimesh.load(io.BytesIO(rebuilt.export(file_type='stl')), file_type='stl', force='mesh')

    assert fixture_mesh.is_watertight
    assert rebuilt.is_watertight
    assert fixture_mesh.volume == pytest.approx(rebuilt.volume, abs=0.02)
    assert fixture_mesh.area == pytest.approx(rebuilt.area, abs=0.2)
    assert fixture_mesh.bounds == pytest.approx(rebuilt.bounds, abs=1e-3)


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_gear_golden_fixture_is_a_one_piece_roller(fixtures_dir, plate_type):
    """
    The shape of the thing: 72 mm tall, gears at both ends, 24 teeth on each.

    Body counting is deliberately not a bare "== 1". On the EMBOSS plate the
    raised dot domes come out as separate small bodies - the recorded second
    tangency inside every rounded dot, which predates this beta and is present
    with gears off too. So: exactly one body is the roller, and every other
    body must look like one of those domes.
    """
    trimesh = pytest.importorskip('trimesh')
    import numpy as np

    mesh = trimesh.load(str(fixtures_dir / f'{GEAR_FIXTURE_NAMES[plate_type]}.stl'), file_type='stl', force='mesh')
    mesh.merge_vertices()

    bodies = mesh.split(only_watertight=False)
    # A negative volume is an enclosed void - what a hollow barrel plus the
    # weld rings produced before gear mode forced the shell solid.
    assert all(body.volume > 0 for body in bodies)

    rollers = [body for body in bodies if body.bounds[1][2] - body.bounds[0][2] > 70.0]
    assert len(rollers) == 1
    roller = rollers[0]

    assert roller.bounds[0][2] == pytest.approx(_GEAR_FIXTURE_Z_MIN, abs=1e-3)
    assert roller.bounds[1][2] == pytest.approx(_GEAR_FIXTURE_Z_MAX, abs=1e-3)

    for body in bodies:
        if body is roller:
            continue
        assert body.volume < 1.0
        assert np.hypot(body.vertices[:, 0], body.vertices[:, 1]).min() >= GEAR_FIXTURE_CYLINDER_PARAMS['diameter'] / 2

    # Both gear bands, in the fixture frame (barrel 0..52).
    for z_low, z_high in ((-9.0, -1.0), (53.0, 61.0)):
        count, _ = tooth_band_phase(roller.vertices, z_low, z_high)
        assert count == _GEAR_TOOTH_COUNT


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_gear_golden_fixture_has_material_where_a_tooth_is(fixtures_dir, plate_type):
    """
    Containment probes on the gears themselves: solid inside a tooth, air just
    beyond the tips. Catches a gear that landed but at the wrong radius.
    """
    trimesh = pytest.importorskip('trimesh')
    import numpy as np

    mesh = trimesh.load(str(fixtures_dir / f'{GEAR_FIXTURE_NAMES[plate_type]}.stl'), file_type='stl', force='mesh')
    spec = _gear_fixture_spec(plate_type)

    # Sample the fixture's own tooth angles rather than assuming a phase: take
    # the tip band of the top gear and probe along one measured tooth centre.
    top = mesh.vertices[(mesh.vertices[:, 2] > 55.0) & (mesh.vertices[:, 2] < 59.0)]
    radial = np.hypot(top[:, 0], top[:, 1])
    tips = top[radial > _GEAR_TIP_RADIUS_MM - 0.05]
    assert len(tips) > 0
    theta = math.atan2(tips[0][1], tips[0][0])

    inside = []
    outside = []
    for z in (-5.0, 57.0):  # one probe per gear
        inside.append((0.75 * _GEAR_TIP_RADIUS_MM * math.cos(theta), 0.75 * _GEAR_TIP_RADIUS_MM * math.sin(theta), z))
        outside.append(
            ((_GEAR_TIP_RADIUS_MM + 0.5) * math.cos(theta), (_GEAR_TIP_RADIUS_MM + 0.5) * math.sin(theta), z)
        )

    assert mesh.contains(np.array(inside)).all()
    assert not mesh.contains(np.array(outside)).any()
    assert spec['gears']['asset'] == GEAR_FIXTURE_ASSETS[plate_type]


# ---------------------------------------------------------------------------
# Embosser Version 2 (keyed gear pegs) PROTOTYPE golden pair
#
# The same braille and the same tactile arrows as the two beta pairs, so the
# only thing these fixtures add is the keyed cutout itself. Three deliberate
# differences from the double-sided pair:
#
#   * the cylinder is 30.8 mm, not 30.75. That is Version 2's preset barrel
#     (D-V4). At any other size app/geometry_spec.py emits the S-V5 size note,
#     and a spec carrying warnings cannot be turned into a fixture at all - so
#     a Version 2 fixture can only ever exist at the preset size, as intended.
#   * the double-sided flag is dropped and no back_lines are passed: this is a
#     plain single-sided Version 2 cylinder. The interpoint dial values stay in
#     the settings, inert, so the two families' inputs remain comparable.
#   * the barrel comes from tests/test_version2_keyed.build_v2_cylinder - the
#     very builder the acceptance harness measures - so the golden pair and
#     that harness cannot drift apart.
#   * the grid is 3 columns wide, not 14. Turning the double-sided flag off
#     brings back the UNIVERSAL COUNTER GRID, which puts a bowl at every dot
#     position on Cylinder B: at 14 columns that is 336 bowls and a 13.01 MB
#     fixture - larger than all nine existing fixtures put together, added
#     again to git history at every regeneration. Three columns is the width
#     the fixture's own braille line actually uses, gives 72 bowls and 2.88 MB,
#     and costs nothing this pair is here to prove: the counter grid is
#     Version 1 geometry, already pinned by cylinder_counter_small.stl, while
#     the keyed cutout, the four countersinks and the nub are unaffected by
#     how many bowls sit beside them. Brennen's call, 2026-08-28.
# ---------------------------------------------------------------------------

V2_FIXTURE_SETTINGS = {
    # Neither the double-sided flag nor its pair's three-arrow layout (see the
    # gear pair's note) is inherited; this pair keeps its per-row arrows.
    **{
        key: value
        for key, value in DS_FIXTURE_SETTINGS.items()
        if key not in ('double_sided_enabled', 'tactile_indicator_layout')
    },
    'grid_columns': 3,
    'embosser_version': 2,
    'v2_key_clearance_mm': version2.V2_KEY_CLEARANCE_DEFAULT_MM,
}
V2_FIXTURE_CYLINDER_PARAMS = {
    **DS_FIXTURE_CYLINDER_PARAMS,
    'diameter': version2.V2_BARREL_DIAMETER_MM,
    # The Version 2 preset barrel grew to 54 mm on 2026-08-31 (1 mm card shelf
    # at each end); any other size makes the spec carry the S-V5 note, and the
    # generator below refuses a spec with warnings.
    'height': version2.V2_BARREL_HEIGHT_MM,
}
V2_FIXTURE_NAMES = {'positive': 'v2_cylinderA_golden', 'negative': 'v2_cylinderB_golden'}

# The barrel in the fixture frame (base reseated to z = 0). Cylinder A carries
# the nub on top of that, so it reaches z 57.
_V2_FIXTURE_Z_MIN = 0.0
_V2_FIXTURE_Z_MAX = version2.V2_BARREL_HEIGHT_MM


def _v2_fixture_spec(plate_type):
    """Geometry spec for one side of the Version 2 golden pair."""
    settings = CardSettings(**V2_FIXTURE_SETTINGS)
    return extract_cylinder_geometry_spec(
        DS_FIXTURE_FRONT_LINES,
        'g1',
        settings,
        V2_FIXTURE_CYLINDER_PARAMS,
        None,
        plate_type,
        braille_to_dots_func=braille_to_dots,
    )


def _build_v2_cylinder_mesh(spec):
    """
    Render a Version 2 keyed cylinder spec to a watertight mesh.

    Only the BARREL differs from the double-sided renderer: it arrives already
    solid, cut through by both keys, countersunk at all four mouths, and
    carrying Cylinder A's nub. Dots, markers, the union-raised-then-subtract-
    recesses order and the fixture reseat are _build_ds_cylinder_mesh's, reused
    rather than copied so the two families cannot drift.

    build_v2_cylinder is imported here rather than at module scope because it
    pulls in manifold3d and trimesh at import time, and this file is collected
    on machines that have neither - every renderer test importorskips them.
    """
    from tests.test_version2_keyed import build_v2_cylinder

    cylinder = spec['cylinder']
    if cylinder['polygon_points']:
        raise ValueError('a Version 2 barrel is solid; drop the polygonal cutout from the fixture params')
    if not spec.get('keyed_cutouts'):
        raise ValueError('this spec carries no keyed_cutouts - is embosser_version 2 set in the fixture settings?')

    shell = build_v2_cylinder(spec['keyed_cutouts'], cylinder['radius'], cylinder['height'], spec['plate_type'])
    return _build_ds_cylinder_mesh(spec, shell=shell)


def generate_v2_golden_fixtures():
    """
    Regenerate the Embosser Version 2 golden STL pair and its metadata.

    Run manually (python -m tests.test_golden from the repo root) - never from
    the test suite, and only when a geometry change is intended. Existing
    fixtures - single-sided, double-sided and gear alike - are not touched.
    """
    import importlib.metadata

    fixtures_dir = Path(__file__).parent / 'fixtures'
    for plate_type, fixture_name in V2_FIXTURE_NAMES.items():
        spec = _v2_fixture_spec(plate_type)
        if spec['warnings']:
            raise ValueError(f'fixture spec for {fixture_name} has warnings: {spec["warnings"]}')
        mesh = _build_v2_cylinder_mesh(spec)
        (fixtures_dir / f'{fixture_name}.stl').write_bytes(mesh.export(file_type='stl'))

        metadata = {
            'description': (
                f'Embosser Version 2 (keyed gear pegs) PROTOTYPE golden: '
                f'{"Cylinder A" if plate_type == "positive" else "Cylinder B"} ({plate_type}), '
                f'barrel with its keyed through-cutout, four countersunk mouths'
                f'{" and the key nub" if plate_type == "positive" else ""}'
            ),
            'fixture_name': fixture_name,
            'plate_type': plate_type,
            'generation': {
                'note': (
                    'Rendered by tests/test_golden.py generate_v2_golden_fixtures() from '
                    'extract_cylinder_geometry_spec called directly with embosser_version=2 and no '
                    'back_lines, so this pair is a SINGLE-SIDED Version 2 cylinder. The barrel comes '
                    'from tests/test_version2_keyed.build_v2_cylinder, the same builder the acceptance '
                    'harness measures. Z-up, theta as emitted, base of the barrel reseated to z=0 - '
                    'which puts Cylinder A nub at z 54..57 and leaves Cylinder B at z 0..54. Since '
                    '2026-09-20 the barrel also carries the slicer seam channel (V 1.0 x 0.5 mm, cut '
                    'from the keyed shell before anything joins).'
                ),
                'cylinder_diameter_note': (
                    'ds_cylinder*_golden uses 30.75 mm; this pair uses 30.8 mm because that is the '
                    'Version 2 preset barrel (D-V4), which walked back on 2026-08-30 to the size '
                    'Version 1 has always used '
                    'and so now matches gear_roller*_golden. Any other size makes '
                    'app/geometry_spec.py emit the S-V5 size note, and a spec carrying warnings is '
                    'refused by the generator above - so these fixtures exist only at the preset size.'
                ),
                'grid_columns_note': (
                    'ds_cylinder*_golden and gear_roller*_golden use 14 columns; this pair uses 3, the '
                    'width its own braille line occupies. Single-sided mode restores the universal '
                    'counter grid, so 14 columns would put 336 bowls on Cylinder B and make the fixture '
                    '13.01 MB against 2.88 MB here. The counter grid is Version 1 geometry pinned by '
                    'cylinder_counter_small.stl; nothing this pair exists to prove depends on it.'
                ),
                'key_profiles': {
                    'bottom': version2.KEY_PROFILES_BY_PLATE[plate_type][0],
                    'top': version2.KEY_PROFILES_BY_PLATE[plate_type][1],
                },
                'front_lines': DS_FIXTURE_FRONT_LINES,
                'settings': V2_FIXTURE_SETTINGS,
                'cylinder_params': V2_FIXTURE_CYLINDER_PARAMS,
                'generated': '2026-09-20',
                'trimesh_version': importlib.metadata.version('trimesh'),
                'manifold3d_version': importlib.metadata.version('manifold3d'),
            },
            'expected_properties': {
                'face_count': len(mesh.faces),
                'vertex_count': len(mesh.vertices),
                'is_watertight': bool(mesh.is_watertight),
                'bbox_min': mesh.bounds[0].tolist(),
                'bbox_max': mesh.bounds[1].tolist(),
                'volume': float(mesh.volume),
                'surface_area': float(mesh.area),
            },
        }
        (fixtures_dir / f'{fixture_name}.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        print(
            f'{fixture_name}: {len(mesh.faces)} faces, volume {mesh.volume:.3f} mm^3, '
            f'watertight {mesh.is_watertight}, z {mesh.bounds[0][2]:.3f}..{mesh.bounds[1][2]:.3f}'
        )


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_golden_fixture_metadata_records_the_module_inputs(fixtures_dir, plate_type):
    """Fixture metadata and the inputs the test regenerates from cannot drift apart."""
    metadata = load_fixture_metadata(fixtures_dir, V2_FIXTURE_NAMES[plate_type])
    generation = metadata['generation']
    assert generation['front_lines'] == DS_FIXTURE_FRONT_LINES
    assert generation['settings'] == V2_FIXTURE_SETTINGS
    assert generation['cylinder_params'] == V2_FIXTURE_CYLINDER_PARAMS
    # Single-sided by construction: no back braille went into these.
    assert 'back_lines' not in generation
    assert 'double_sided_enabled' not in generation['settings']
    # Each family's diameter is recorded with its reason. Version 2 and the
    # gear rollers SHARE 30.8 as of 2026-08-30 - the gears were always pinned
    # to it and Version 2's preset walked back to it - so diameter no longer
    # tells all three families apart. What does is asserted above and below:
    # the keyed cutouts, the double-sided flag and the grid width.
    assert generation['cylinder_params']['diameter'] == 30.8
    assert DS_FIXTURE_CYLINDER_PARAMS['diameter'] == 30.75
    assert GEAR_FIXTURE_CYLINDER_PARAMS['diameter'] == 30.8
    # The narrower grid is deliberate and its reason is recorded beside it:
    # single-sided mode restores the universal counter grid on Cylinder B.
    assert generation['settings']['grid_columns'] == 3
    assert DS_FIXTURE_SETTINGS['grid_columns'] == 14
    # The two keys this plate owns, named so a swapped pair is visible here too.
    assert (generation['key_profiles']['bottom'], generation['key_profiles']['top']) == version2.KEY_PROFILES_BY_PLATE[
        plate_type
    ]


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_golden_fixture_matches_regenerated_geometry(fixtures_dir, plate_type):
    """The committed cylinder must match a fresh render of today's Version 2 spec."""
    trimesh = pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    pytest.importorskip('shapely')

    fixture_name = V2_FIXTURE_NAMES[plate_type]
    fixture_mesh = trimesh.load(str(fixtures_dir / f'{fixture_name}.stl'), file_type='stl', force='mesh')

    spec = _v2_fixture_spec(plate_type)
    assert spec['warnings'] == []
    rebuilt = _build_v2_cylinder_mesh(spec)
    rebuilt = trimesh.load(io.BytesIO(rebuilt.export(file_type='stl')), file_type='stl', force='mesh')

    assert fixture_mesh.is_watertight
    assert rebuilt.is_watertight
    assert fixture_mesh.volume == pytest.approx(rebuilt.volume, abs=0.02)
    assert fixture_mesh.area == pytest.approx(rebuilt.area, abs=0.2)
    assert fixture_mesh.bounds == pytest.approx(rebuilt.bounds, abs=1e-3)


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_golden_fixture_is_a_keyed_cylinder(fixtures_dir, plate_type):
    """
    The shape of the thing: a barrel with a hole right through it, the nub on
    Cylinder A only, and a 15.050 mm rim.

    Body counting is deliberately not a bare "== 1", for the same reason the
    gear fixture gives: on the EMBOSS plate the raised dot domes come out as
    separate small bodies (the recorded second tangency inside every rounded
    dot, which predates all three betas).
    """
    trimesh = pytest.importorskip('trimesh')
    import numpy as np

    mesh = trimesh.load(str(fixtures_dir / f'{V2_FIXTURE_NAMES[plate_type]}.stl'), file_type='stl', force='mesh')
    mesh.merge_vertices()

    bodies = mesh.split(only_watertight=False)
    # A negative volume would be an enclosed void - exactly what a barrel
    # hollowed by wall thickness under a keyed cutout would leave.
    assert all(body.volume > 0 for body in bodies)

    barrels = [body for body in bodies if body.bounds[1][2] - body.bounds[0][2] > 50.0]
    assert len(barrels) == 1
    barrel = barrels[0]

    # Both plates carry an anti-rotation nub since 2026-08-29, so both reach the
    # same height; only the SHAPE differs, triangle on A and square on B.
    expected_top = _V2_FIXTURE_Z_MAX + version2.V2_NUB['height']
    assert barrel.bounds[0][2] == pytest.approx(_V2_FIXTURE_Z_MIN, abs=1e-3)
    assert barrel.bounds[1][2] == pytest.approx(expected_top, abs=1e-3)

    # The rim: the 64-gon barrel puts its vertices ON the radius.
    radius = version2.V2_BARREL_DIAMETER_MM / 2.0
    for face_z in (_V2_FIXTURE_Z_MIN, _V2_FIXTURE_Z_MAX):
        rim = barrel.vertices[np.isclose(barrel.vertices[:, 2], face_z, atol=1e-3)]
        assert len(rim) > 0
        assert np.hypot(rim[:, 0], rim[:, 1]).max() == pytest.approx(radius, abs=2e-3)

    # A through-hole, not two blind pockets: the axis is air the whole way.
    axis = [[0.0, 0.0, float(z)] for z in range(1, int(_V2_FIXTURE_Z_MAX))]
    assert not mesh.contains(np.array(axis)).any()

    # Each plate stands its own nub above the top face - the "Cylinder A alone"
    # rule retired on 2026-08-29 when every gear gained an anti-rotation feature.
    above = mesh.vertices[mesh.vertices[:, 2] > _V2_FIXTURE_Z_MAX + 1e-3]
    assert len(above) > 0
    # Measured against the profile the module actually emits, not against the
    # nominal apex with slop: the nub is inset by V2_NUB_CLEARANCE_MM, which
    # moved from 0.15 to 0.30 on 2026-08-29, and a tolerance wide enough to
    # swallow that is wide enough to miss a real regression.
    nub_apex = max(np.hypot(x, y) for x, y in version2.antirot_nub_profile(plate_type))
    assert np.hypot(above[:, 0], above[:, 1]).max() == pytest.approx(nub_apex, abs=2e-3)

    # The socket is a blind pocket in the BOTTOM face, not a second through-hole:
    # material is still there above it.
    socket_top = _V2_FIXTURE_Z_MIN + version2.V2_SOCKET_DEPTH_MM
    centre = np.array(version2.antirot_socket_profile(plate_type)).mean(axis=0)
    assert not mesh.contains(np.array([[centre[0], centre[1], _V2_FIXTURE_Z_MIN + 1.0]]))[0]
    assert mesh.contains(np.array([[centre[0], centre[1], socket_top + 1.0]]))[0]


@pytest.mark.parametrize(
    'fixture_name',
    ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small'],
)
def test_golden_specs_ignore_an_absent_or_off_gear_flag(client, fixtures_dir, fixture_name):
    """
    Beta isolation, the same proof the double-sided toggle gets: gears at 0 must
    be indistinguishable from gears not existing, for every pre-beta payload.
    """
    metadata = load_fixture_metadata(fixtures_dir, fixture_name)
    payload = metadata['request_payload']

    baseline = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert baseline.status_code == 200, baseline.data

    off_payload = copy.deepcopy(payload)
    off_payload.setdefault('settings', {})['gear_rollers_enabled'] = 0
    toggled_off = client.post('/geometry_spec', json=off_payload, headers={'Content-Type': 'application/json'})
    assert toggled_off.status_code == 200, toggled_off.data

    assert toggled_off.get_json() == baseline.get_json()


def test_a_double_sided_request_is_unchanged_by_an_off_gear_flag(client):
    """The gear flag at 0 must not disturb the other beta either."""
    payload = {
        'shape_type': 'cylinder',
        'plate_type': 'positive',
        'lines': DS_FIXTURE_FRONT_LINES,
        'back_lines': DS_FIXTURE_BACK_LINES,
        'settings': dict(DS_FIXTURE_SETTINGS),
        'cylinder_params': dict(DS_FIXTURE_CYLINDER_PARAMS),
    }

    baseline = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert baseline.status_code == 200, baseline.data

    off_payload = copy.deepcopy(payload)
    off_payload['settings']['gear_rollers_enabled'] = 0
    toggled_off = client.post('/geometry_spec', json=off_payload, headers={'Content-Type': 'application/json'})
    assert toggled_off.status_code == 200, toggled_off.data

    assert toggled_off.get_json() == baseline.get_json()


@pytest.mark.parametrize(
    'fixture_name',
    ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small'],
)
def test_golden_specs_ignore_an_absent_or_version_1_embosser_version(client, fixtures_dir, fixture_name):
    """
    Version 2 isolation, the proof both betas already get: embosser_version 1
    must be indistinguishable from the field not existing, for every pre-beta
    payload. A card payload is in here on purpose - Version 1 must stay
    untouched on the shape Version 2 refuses outright.
    """
    metadata = load_fixture_metadata(fixtures_dir, fixture_name)
    payload = metadata['request_payload']

    baseline = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert baseline.status_code == 200, baseline.data

    off_payload = copy.deepcopy(payload)
    off_payload.setdefault('settings', {})['embosser_version'] = 1
    toggled_off = client.post('/geometry_spec', json=off_payload, headers={'Content-Type': 'application/json'})
    assert toggled_off.status_code == 200, toggled_off.data

    assert toggled_off.get_json() == baseline.get_json()


def test_a_double_sided_request_is_unchanged_by_a_version_1_embosser_version(client):
    """Version 1 must not disturb the other two betas either."""
    payload = {
        'shape_type': 'cylinder',
        'plate_type': 'positive',
        'lines': DS_FIXTURE_FRONT_LINES,
        'back_lines': DS_FIXTURE_BACK_LINES,
        'settings': dict(DS_FIXTURE_SETTINGS),
        'cylinder_params': dict(DS_FIXTURE_CYLINDER_PARAMS),
    }

    baseline = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert baseline.status_code == 200, baseline.data

    off_payload = copy.deepcopy(payload)
    off_payload['settings']['embosser_version'] = 1
    toggled_off = client.post('/geometry_spec', json=off_payload, headers={'Content-Type': 'application/json'})
    assert toggled_off.status_code == 200, toggled_off.data

    assert toggled_off.get_json() == baseline.get_json()


# ---------------------------------------------------------------------------
# Fused Version 2 rollers (2026-09-20 programme, sub-plan B, phase B5)
#
# The Version 2 pair with fixed gears: the same inputs as the keyed Version 2
# pair plus gear_rollers_enabled=1, so the only things this pair adds are the
# v8 gear set, its weld rings and the notch fills - and the only thing it
# removes is the keyed cutout (decision D-6: the barrel is plain solid). Built
# by the double-sided renderer with its default solid shell, so the geometry is
# exactly what the worker builds: shell -> gears + rings + fills -> raised ->
# recesses. The seam channel is on, as on every pair since phase A5.
# ---------------------------------------------------------------------------

V2_GEAR_FIXTURE_SETTINGS = {**V2_FIXTURE_SETTINGS, 'gear_rollers_enabled': 1}
V2_GEAR_FIXTURE_NAMES = {'positive': 'v2_gear_rollerA_golden', 'negative': 'v2_gear_rollerB_golden'}
V2_GEAR_FIXTURE_ASSETS = {'positive': 'v2_gears_a', 'negative': 'v2_gears_b'}
# The fused roller in the fixture frame (barrel base reseated to z = 0): gears
# at -10..0 and 54..64, nothing above - no nub in fused mode.
_V2_GEAR_FIXTURE_Z_MIN = -10.0
_V2_GEAR_FIXTURE_Z_MAX = version2.V2_BARREL_HEIGHT_MM + 10.0


def _v2_gear_fixture_spec(plate_type):
    """Geometry spec for one side of the fused Version 2 golden pair."""
    settings = CardSettings(**V2_GEAR_FIXTURE_SETTINGS)
    return extract_cylinder_geometry_spec(
        DS_FIXTURE_FRONT_LINES,
        'g1',
        settings,
        V2_FIXTURE_CYLINDER_PARAMS,
        None,
        plate_type,
        braille_to_dots_func=braille_to_dots,
    )


def generate_v2_gear_golden_fixtures():
    """
    Regenerate the fused Version 2 golden STL pair and its metadata.

    Run manually - never from the test suite, and only when a geometry change is
    intended. The other pairs are not touched.
    """
    import importlib.metadata

    fixtures_dir = Path(__file__).parent / 'fixtures'
    for plate_type, fixture_name in V2_GEAR_FIXTURE_NAMES.items():
        spec = _v2_gear_fixture_spec(plate_type)
        if spec['warnings']:
            raise ValueError(f'fixture spec for {fixture_name} has warnings: {spec["warnings"]}')
        if 'keyed_cutouts' in spec:
            raise ValueError(f'{fixture_name}: a fused Version 2 spec must carry no keyed cutout (D-6)')
        mesh = _build_ds_cylinder_mesh(spec)
        (fixtures_dir / f'{fixture_name}.stl').write_bytes(mesh.export(file_type='stl'))

        metadata = {
            'description': (
                f'Fused Embosser Version 2 golden: {"Cylinder A" if plate_type == "positive" else "Cylinder B"} '
                f'({plate_type}), solid 54 mm barrel plus its fixed v8 gears as one part, notch filled'
            ),
            'fixture_name': fixture_name,
            'plate_type': plate_type,
            'generation': {
                'note': (
                    'Rendered by tests/test_golden.py generate_v2_gear_golden_fixtures() from '
                    'extract_cylinder_geometry_spec called directly with embosser_version=2 and '
                    'gear_rollers_enabled=1 (no back_lines: single-sided). The barrel is the plain '
                    'solid cylinder - no keyed holes, countersinks, nub or socket (decision D-6) - with '
                    'the vendored v8 gear set from static/assets/gears/v2_gears_*.bin, the two weld '
                    'rings and the top gear notch fill unioned in before any recess is cut. Z-up, theta '
                    'as emitted, base of the barrel reseated to z=0, which puts the gears at z -10..0 '
                    'and 54..64. The slicer seam channel is cut as on every pair.'
                ),
                'gear_asset': V2_GEAR_FIXTURE_ASSETS[plate_type],
                'front_lines': DS_FIXTURE_FRONT_LINES,
                'settings': V2_GEAR_FIXTURE_SETTINGS,
                'cylinder_params': V2_FIXTURE_CYLINDER_PARAMS,
                'generated': '2026-09-21',
                'trimesh_version': importlib.metadata.version('trimesh'),
                'manifold3d_version': importlib.metadata.version('manifold3d'),
            },
            'expected_properties': {
                'face_count': len(mesh.faces),
                'vertex_count': len(mesh.vertices),
                'is_watertight': bool(mesh.is_watertight),
                'bbox_min': mesh.bounds[0].tolist(),
                'bbox_max': mesh.bounds[1].tolist(),
                'volume': float(mesh.volume),
                'surface_area': float(mesh.area),
            },
        }
        (fixtures_dir / f'{fixture_name}.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        print(
            f'{fixture_name}: {len(mesh.faces)} faces, volume {mesh.volume:.3f} mm^3, watertight {mesh.is_watertight}, '
            f'z {mesh.bounds[0][2]:.3f}..{mesh.bounds[1][2]:.3f}'
        )


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_gear_golden_spec_is_fused(plate_type):
    """The spec the pair is built from: solid, no keys, the v8 asset, one notch fill, no warnings."""
    spec = _v2_gear_fixture_spec(plate_type)
    assert spec['warnings'] == []
    assert spec['cylinder']['solid'] is True
    assert 'keyed_cutouts' not in spec
    assert spec['gears']['asset'] == V2_GEAR_FIXTURE_ASSETS[plate_type]
    assert len(spec['gears']['notch_fills']) == 1
    assert 'seam_channel' in spec['cylinder']


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_gear_golden_fixture_metadata_records_the_module_inputs(fixtures_dir, plate_type):
    metadata = load_fixture_metadata(fixtures_dir, V2_GEAR_FIXTURE_NAMES[plate_type])
    generation = metadata['generation']
    assert generation['settings'] == V2_GEAR_FIXTURE_SETTINGS
    assert generation['cylinder_params'] == V2_FIXTURE_CYLINDER_PARAMS
    assert generation['gear_asset'] == V2_GEAR_FIXTURE_ASSETS[plate_type]
    assert generation['settings']['gear_rollers_enabled'] == 1
    assert generation['settings']['embosser_version'] == 2


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_gear_golden_fixture_matches_regenerated_geometry(fixtures_dir, plate_type):
    """The committed roller must match a fresh render of today's fused Version 2 spec."""
    trimesh = pytest.importorskip('trimesh')
    pytest.importorskip('manifold3d')
    pytest.importorskip('shapely')

    fixture_name = V2_GEAR_FIXTURE_NAMES[plate_type]
    fixture_mesh = trimesh.load(str(fixtures_dir / f'{fixture_name}.stl'), file_type='stl', force='mesh')

    spec = _v2_gear_fixture_spec(plate_type)
    rebuilt = _build_ds_cylinder_mesh(spec)
    rebuilt = trimesh.load(io.BytesIO(rebuilt.export(file_type='stl')), file_type='stl', force='mesh')

    assert fixture_mesh.is_watertight
    assert rebuilt.is_watertight
    assert fixture_mesh.volume == pytest.approx(rebuilt.volume, abs=0.02)
    assert fixture_mesh.area == pytest.approx(rebuilt.area, abs=0.2)
    assert fixture_mesh.bounds == pytest.approx(rebuilt.bounds, abs=1e-3)


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_gear_golden_fixture_is_one_sealed_roller_with_no_void(fixtures_dir, plate_type):
    """
    The D-6 acceptance: ONE body and no enclosed void - a sealed notch would
    appear as a second shell in split(only_watertight=False) - 74 mm tall,
    gears at both ends with 24 teeth each, the old keyed-hole region SOLID,
    the notch region solid, the barrel rim still 15.4 mm, nothing proud of the
    top face (no nub in fused mode).
    """
    trimesh = pytest.importorskip('trimesh')
    import numpy as np

    mesh = trimesh.load(str(fixtures_dir / f'{V2_GEAR_FIXTURE_NAMES[plate_type]}.stl'), file_type='stl', force='mesh')
    mesh.merge_vertices()

    bodies = mesh.split(only_watertight=False)
    assert all(body.volume > 0 for body in bodies)
    rollers = [body for body in bodies if body.bounds[1][2] - body.bounds[0][2] > 70.0]
    assert len(rollers) == 1
    roller = rollers[0]
    for body in bodies:
        if body is roller:
            continue
        # Only the recorded dot-dome tangency bodies may exist beside the roller.
        assert body.volume < 1.0
        assert np.hypot(body.vertices[:, 0], body.vertices[:, 1]).min() >= version2.V2_BARREL_DIAMETER_MM / 2

    assert roller.bounds[0][2] == pytest.approx(_V2_GEAR_FIXTURE_Z_MIN, abs=1e-3)
    assert roller.bounds[1][2] == pytest.approx(_V2_GEAR_FIXTURE_Z_MAX, abs=1e-3)

    # 24 teeth on both gears, in the fixture frame (barrel 0..54).
    for z_low, z_high in ((-9.0, -1.0), (55.0, 63.0)):
        count, _ = tooth_band_phase(roller.vertices, z_low, z_high)
        assert count == _GEAR_TOOTH_COUNT

    # The rim: the 64-gon barrel's vertices sit ON the radius at mid-height.
    mid = roller.vertices[np.abs(roller.vertices[:, 2] - version2.V2_BARREL_HEIGHT_MM / 2) < 1.0]
    radial = np.hypot(mid[:, 0], mid[:, 1])
    assert radial[radial > 15.0].min() == pytest.approx(version2.V2_BARREL_DIAMETER_MM / 2, abs=0.02)

    # Solid where the keyed hole and the socket used to be, and inside the
    # notch volume the fill closed (r 12 on the arrow column, 1.5 mm into the
    # top gear), and through the whole axis.
    axis = np.array([[0.0, 0.0, float(z)] for z in range(1, int(version2.V2_BARREL_HEIGHT_MM))])
    assert roller.contains(axis).all()
    column = math.radians(version2.V2_ARROW_COLUMN_DEG)
    probes = np.array(
        [
            [12.0 * math.cos(column), 12.0 * math.sin(column), version2.V2_BARREL_HEIGHT_MM + 1.5],
            [12.0 * math.cos(column), 12.0 * math.sin(column), 1.5],
            [12.0 * math.cos(column), 12.0 * math.sin(column), version2.V2_BARREL_HEIGHT_MM - 1.5],
        ]
    )
    assert roller.contains(probes).all()


@pytest.mark.parametrize('plate_type', ['positive', 'negative'])
def test_v2_gear_golden_fixture_keeps_the_vendored_gear_surface(fixtures_dir, plate_type):
    """Points sampled on the vendored gears lie on the roller's surface: the union moved nothing."""
    trimesh = pytest.importorskip('trimesh')
    import numpy as np

    from tests.test_gear_rollers import surface_distances

    roller = trimesh.load(str(fixtures_dir / f'{V2_GEAR_FIXTURE_NAMES[plate_type]}.stl'), file_type='stl', force='mesh')
    gears_mesh = load_gear_asset(V2_GEAR_FIXTURE_ASSETS[plate_type])
    gears_mesh.apply_translation([0.0, 0.0, version2.V2_BARREL_HEIGHT_MM / 2])  # fixture frame
    points, distances = surface_distances(gears_mesh, roller, 4000, seed=7)
    # The pegs are buried in the solid barrel and the notch is filled, so only
    # the gear surface OUTSIDE the barrel must survive - and the gear/barrel
    # contact planes at z 0 and z 54 are interior to the union, so points
    # within 0.1 mm of them are excluded as the Version 1 harness does.
    z = points[:, 2]
    outside = (z < -0.1) | (z > version2.V2_BARREL_HEIGHT_MM + 0.1)
    # The top gear's notch walls and floor are buried inside the fill (D-6), so
    # points sampled on them are interior now - the very thing the fill exists
    # to do. Exclude the notch window: on the arrow column, inside r 14.2, in
    # the notch's depth band above the barrel face.
    angles = np.degrees(np.arctan2(points[:, 1], points[:, 0])) % 360.0
    on_column = np.abs(angles - version2.V2_ARROW_COLUMN_DEG) < 20.0
    in_notch = (
        on_column
        & (np.hypot(points[:, 0], points[:, 1]) < 14.2)
        & (z > version2.V2_BARREL_HEIGHT_MM - 0.1)
        & (z < version2.V2_BARREL_HEIGHT_MM + 3.5)
    )
    keep = outside & ~in_notch
    assert keep.sum() > 500
    assert float(np.percentile(distances[keep], 99)) < 0.01
    assert float(distances[keep].max()) < 0.05


# ---------------------------------------------------------------------------
# Slicer seam channel (2026-09-20 programme, sub-plan A)
#
# Every cylinder fixture carries the groove since 2026-09-20; all six STLs were
# regenerated once for it (decision D-2). The check is by containment, not by
# vertex hunting: bowl vertices also pass through the groove's radius, so a
# "no vertices at R - 0.5 elsewhere" rule would fail on every counter plate.
# ---------------------------------------------------------------------------

_SEAM_CHANNEL_FIXTURES = [
    ('ds', 'positive'),
    ('ds', 'negative'),
    ('gear', 'positive'),
    ('gear', 'negative'),
    ('v2', 'positive'),
    ('v2', 'negative'),
    ('v2_gear', 'positive'),
    ('v2_gear', 'negative'),
]


def _seam_channel_fixture(family, plate_type):
    if family == 'ds':
        return DS_FIXTURE_NAMES[plate_type], _ds_fixture_spec(plate_type)
    if family == 'gear':
        return GEAR_FIXTURE_NAMES[plate_type], _gear_fixture_spec(plate_type)
    if family == 'v2_gear':
        return V2_GEAR_FIXTURE_NAMES[plate_type], _v2_gear_fixture_spec(plate_type)
    return V2_FIXTURE_NAMES[plate_type], _v2_fixture_spec(plate_type)


@pytest.mark.parametrize('family, plate_type', _SEAM_CHANNEL_FIXTURES)
def test_golden_fixture_has_the_seam_channel(fixtures_dir, family, plate_type):
    """
    Air in the groove at the spec's angle and solid wall 2.5 degrees either
    side of it, near both ends - and, since D-T6 (2026-09-21), solid at
    mid-height on the embossing plate: every golden is a tactile layout, whose
    groove runs down the arrow column in two stretches that stop short of the
    arrow chain, so mid-height sits under a raised arrow there. Both plates of
    every pair carry it, and the two angles of a pair sum to 360 degrees.

    Only the margin band is probed for solid: the seam centre is the arrow
    RECESS on every counter plate, and on a double-sided pair the far side of
    the seam is crowded by the back grid, so neither is a fair "untouched
    surface" probe.
    """
    trimesh = pytest.importorskip('trimesh')
    import numpy as np

    fixture_name, spec = _seam_channel_fixture(family, plate_type)
    channel = spec['cylinder']['seam_channel']
    assert channel['width'] == geometry_spec.SEAM_CHANNEL_WIDTH_MM
    assert channel['depth'] == geometry_spec.SEAM_CHANNEL_DEPTH_MM

    mesh = trimesh.load(str(fixtures_dir / f'{fixture_name}.stl'), file_type='stl', force='mesh')
    radius = spec['cylinder']['radius']
    height = spec['cylinder']['height']
    theta = channel['theta']
    # Just under the surface: inside the V at its centre line (the groove is
    # 0.5 deep there), clear of it 0.67 mm to either side (inside the 0.25 mm
    # margin band, where the surface is untouched).
    probe_radius = radius - 0.2
    side = math.radians(2.5)

    def point(angle, z):
        return [probe_radius * math.cos(angle), probe_radius * math.sin(angle), z]

    segments = channel.get('segments')
    if segments:
        # Tactile: probe inside each stretch (fixture z runs from 0 at the
        # base; the spec's z_from/z_to are about mid-height) and check the
        # chain in between is untouched on the embossing plate.
        heights = [
            (max(seg['z_from'], -height / 2.0) + min(seg['z_to'], height / 2.0)) / 2.0 + height / 2.0
            for seg in segments
        ]
        if plate_type == 'positive':
            assert mesh.contains(np.array([point(theta, height / 2.0)])).all(), (
                f'{fixture_name}: the groove reaches the arrow chain at mid-height'
            )
    else:
        heights = [2.0, height / 2.0, height - 2.0]
    air = np.array([point(theta, z) for z in heights])
    solid = np.array([point(angle, z) for z in heights for angle in (theta - side, theta + side)])
    assert not mesh.contains(air).any(), f'{fixture_name}: no groove at {math.degrees(theta):.2f} deg'
    assert mesh.contains(solid).all(), f'{fixture_name}: surface missing beside the groove'

    mirror_name, mirror_spec = _seam_channel_fixture(family, 'negative' if plate_type == 'positive' else 'positive')
    assert theta + mirror_spec['cylinder']['seam_channel']['theta'] == pytest.approx(2 * math.pi, abs=1e-12)


if __name__ == '__main__':
    generate_ds_golden_fixtures()
    generate_gear_golden_fixtures()
    generate_v2_golden_fixtures()
    generate_v2_gear_golden_fixtures()
