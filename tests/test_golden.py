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

from app.geometry import interpoint
from app.geometry_spec import extract_cylinder_geometry_spec
from app.models import CardSettings
from app.utils import braille_to_dots


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
# printed and embossed); fixtures regenerated 2026-08-20.
#
# The specs are built by calling extract_cylinder_geometry_spec directly:
# back_lines has no request route until the backend plumbing phase lands.
# ---------------------------------------------------------------------------

DS_FIXTURE_FRONT_LINES = ['⠁⠃⠉', '', '', '']  # 1 + 2 + 2 = 5 raised dots
DS_FIXTURE_BACK_LINES = ['⠙⠑⠋', '', '', '']  # 3 + 2 + 3 = 8 raised dots
DS_FIXTURE_SETTINGS = {
    'grid_columns': 14,
    'grid_rows': 4,
    'indicator_mode': 'tactile',
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
    delta = marker['outline_delta'] + (0.0 if marker['is_recess'] else _DS_ARROW_WELD_MM)
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


def _build_ds_cylinder_mesh(spec):
    """
    Render a double-sided cylinder spec to a watertight mesh.

    Booleans go straight to the manifold engine so any backend problem raises
    instead of silently degrading — a golden must fail loudly. Raised features
    union in before recesses cut, matching the worker's ordering, so a recess
    can never be filled back in.
    """
    import trimesh

    cylinder = spec['cylinder']
    radius = cylinder['radius']
    height = cylinder['height']
    if cylinder['polygon_points']:
        raise ValueError('ds golden renderer models a solid shell; drop the polygonal cutout from the fixture params')

    shell = trimesh.creation.cylinder(radius=radius, height=height, sections=_DS_SHELL_SECTIONS)
    raised = [shell]
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
    solid = trimesh.boolean.difference([solid, trimesh.boolean.union(cutters, engine='manifold')], engine='manifold')
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
                    'Bowls are cut centre-on-surface (the shipping worker convention).'
                ),
                'front_lines': DS_FIXTURE_FRONT_LINES,
                'back_lines': DS_FIXTURE_BACK_LINES,
                'settings': DS_FIXTURE_SETTINGS,
                'cylinder_params': DS_FIXTURE_CYLINDER_PARAMS,
                'generated': '2026-08-20',
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
        assert [m['type'] for m in spec['markers']] == ['cylinder_tactile_arrow'] * DS_FIXTURE_SETTINGS['grid_rows']

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


if __name__ == '__main__':
    generate_ds_golden_fixtures()
