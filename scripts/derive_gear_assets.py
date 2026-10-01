"""Derive the vendored gear assets for the gear-integrated one-piece rollers.

Reads Brennen's four Version 1 gear holders - the parts the standard embosser's
cylinders slide onto (A1/A2/B1/B2 v6) - keeps only the 10 mm gear ring of each
one, seats that ring on the barrel end, moves it from the assembly frame into the
browser worker's cylinder frame (axis at x=y=0, barrel centered on z 0 so the
cylinder spans z -26..+26), and writes one packed indexed binary per roller set
plus a provenance manifest.

    python scripts/derive_gear_assets.py

Outputs (regenerate ONLY with this script):
    static/assets/gears/gears_a.bin        A1 (top) + A2 (bottom) as two bodies
    static/assets/gears/gears_b.bin        B1 (top) + B2 (bottom) as two bodies
    static/assets/gears/gears_manifest.json

The rings are a 1:1 replication of the holders' own gear rings - no
reconstruction, no resampling. The only geometry removed is each holder's 40 mm
boss, which would sit inside the cylinder. History: until 2026-09-28 the assets
were the 2026-08-24 "Rollers v7 (Gear Sample ...)" set, whose Cylinder B gears
carry the newer design's smaller hub (a 9 mm bore where the Version 1 housing's
pin needs the 14 mm pocket); Brennen's print found they do not fit the Version 1
embosser. TRANSFORM below is unchanged from that derivation (01_SAMPLE_GEOMETRY_AUDIT.md
sections 2, 3, 10) because the holders sit in the same assembly frame.

Byte layout of a .bin asset (little-endian, header is 14 bytes so the float
block starts at offset 14 - copy the slice before making a typed-array view):

    bytes 0..5              magic b'BCGR1\\x00'
    uint32                  vertCount
    uint32                  triCount
    float32[3 * vertCount]  vertProperties (x, y, z interleaved)
    uint32[3 * triCount]    triVerts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import manifold3d
import numpy as np
import trimesh

MAGIC = b'BCGR1\x00'

DEFAULT_SOURCE = Path(r'C:\Users\WATAP\Documents\Research\Braille Embosser\New Developement_2026_09_28\V1 Gears')
DEFAULT_OUT_DIR = Path('static/assets/gears')

# Bump only when the source parts change: it keeps re-runs byte-idempotent.
DERIVED_DATE = '2026-09-28'

PROVENANCE_NOTE = (
    "Derived 1:1 from Brennen's Version 1 gear holders (each holder's gear ring only, seated on the "
    'barrel end); regenerate only via scripts/derive_gear_assets.py'
)

SAMPLE_FILES = {
    'a': [
        ('A1', 'A1 v6 (0.2) v3.stl'),
        ('A2', 'A2 v6 (0.2) v3.stl'),
    ],
    'b': [
        ('B1', 'B1 v6 (0.2) v3.stl'),
        ('B2', 'B2 v6 (0.2) v3.stl'),
    ],
}

# Each holder is its 10 mm gear ring plus a 40 mm boss that the standard
# cylinder slides over (measured 2026-09-28: rings at z 53..63 and -11..-1, the
# bosses reaching z 12.74 and 39.26). Only the ring ships; the cut is an exact
# Manifold intersection with this band, and the barrel-side face it leaves is a
# full solid disk (checked below - a void there would seal a cavity in the union).
RING_Z_BAND_SOURCE = {
    'A1': (53.0, 63.0),
    'A2': (-11.0, -1.0),
    'B1': (53.0, 63.0),
    'B2': (-11.0, -1.0),
}
# The standard housing holds each ring 1 mm off its barrel end. The fused roller
# seats the ring ON the barrel end instead - the 72 mm roller of Brennen's
# 2026-08-24 samples, his call on 2026-09-28 - so each ring moves 1 mm toward
# the barrel before the frame transform.
RING_SEAT_SHIFT_MM = {
    'A1': -1.0,
    'A2': 1.0,
    'B1': -1.0,
    'B2': 1.0,
}
RING_CUT_HALF_XY_MM = 30.0
RING_CUT_FACE_PROBE_MM = 0.0005

# Canonical transforms, audit section 10.2. Assembly frame -> browser program frame.
#   A: p = Rz(180) * (p_sample - (-16.0000, 0.0000, 0)) - (0, 0, 26.0000)
#   B: p =           (p_sample - (+16.0473, -0.0079, 0)) - (0, 0, 26.0000)
TRANSFORM = {
    'a': {'axis_x_mm': -16.0000, 'axis_y_mm': 0.0000, 'rotation_z_deg': 180.0},
    'b': {'axis_x_mm': 16.0473, 'axis_y_mm': -0.0079, 'rotation_z_deg': 0.0},
}
Z_SHIFT_MM = -26.0000

TOOTH_COUNT = 24
TIP_RADIUS_MM = 16.1093702290795
TIP_RADIUS_TOL_MM = 0.001
TIP_BAND_DEPTH_MM = 0.05
# The teeth are herringbone: over the whole ring each tooth's tip vertices sweep
# several degrees and the holders' tessellation splits them into two groups, so
# teeth are counted in a thin slice at the chevron apex, where every tooth is
# one tight cluster.
TOOTH_MID_PLANE_HALF_MM = 0.5
TOOTH_MID_GAP_DEG = 5.0
GEAR_THICKNESS_MM = 10.0

# Each gear's z band in the program frame: top gears above the barrel, bottom below.
EXPECTED_Z_BANDS = {
    'A1': (26.000, 36.000),
    'A2': (-36.000, -26.000),
    'B1': (26.000, 36.000),
    'B2': (-36.000, -26.000),
}
Z_BAND_TOL_MM = 0.001

# (x_min_floor, x_max_ceil, y_min_floor, y_max_ceil) - the audit's per-asset envelope.
ASSET_XY_BOUNDS = {
    'a': (-16.110, 16.110, -16.110, 16.110),
    'b': (-16.109, 16.110, -16.110, 16.110),
}


class CheckFailed(RuntimeError):
    """Raised when a self-check misses. The assets are never written past a miss."""


class Checker:
    """Collects every self-check result so one run reports all failures, then fails loudly."""

    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, ok: bool, label: str, detail: str) -> None:
        print(f'  [{"ok" if ok else "FAIL"}] {label}: {detail}')
        if not ok:
            self.failures.append(f'{label}: {detail}')

    def raise_if_failed(self) -> None:
        if self.failures:
            raise CheckFailed('self-checks failed:\n  - ' + '\n  - '.join(self.failures))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def load_holder(path: Path) -> trimesh.Trimesh:
    """Load one holder STL and exact-merge its vertices (STL ships every triangle unshared)."""
    mesh = trimesh.load_mesh(str(path), process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise CheckFailed(f'{path.name}: expected a single mesh, got {type(mesh).__name__}')
    mesh.merge_vertices()
    if not mesh.is_watertight:
        raise CheckFailed(f'{path.name}: not watertight after exact vertex merge')
    return mesh


def ring_only(checker: Checker, role: str, asset: str, holder: trimesh.Trimesh) -> trimesh.Trimesh:
    """Cut the holder down to its gear ring: an exact intersection with the ring's z band."""
    z_low, z_high = RING_Z_BAND_SOURCE[role]
    axis_x, axis_y = TRANSFORM[asset]['axis_x_mm'], TRANSFORM[asset]['axis_y_mm']
    solid = manifold3d.Manifold(
        manifold3d.Mesh(
            vert_properties=np.asarray(holder.vertices, dtype=np.float32),
            tri_verts=np.asarray(holder.faces, dtype=np.uint32),
        )
    )
    slab = manifold3d.Manifold.cube([2 * RING_CUT_HALF_XY_MM, 2 * RING_CUT_HALF_XY_MM, z_high - z_low]).translate(
        [axis_x - RING_CUT_HALF_XY_MM, axis_y - RING_CUT_HALF_XY_MM, z_low]
    )
    ring = solid ^ slab

    # The face that will meet the barrel: one loop, no holes - a solid disk.
    barrel_side_z = z_low if z_low > 0 else z_high
    probe_z = barrel_side_z + (RING_CUT_FACE_PROBE_MM if z_low > 0 else -RING_CUT_FACE_PROBE_MM)
    loops = ring.slice(probe_z).to_polygons()
    checker.check(
        len(loops) == 1, f'{role} barrel-side face is one solid disk', f'{len(loops)} loop(s) at z {probe_z:.4f}'
    )

    packed = ring.to_mesh()
    mesh = trimesh.Trimesh(
        vertices=np.asarray(packed.vert_properties, dtype=np.float64)[:, :3],
        faces=np.asarray(packed.tri_verts, dtype=np.int64),
        process=False,
    )
    mesh.merge_vertices()
    bodies = mesh.split(only_watertight=False)
    checker.check(
        len(bodies) == 1 and mesh.is_watertight,
        f'{role} ring is one watertight body',
        f'{len(bodies)} body(ies), watertight={mesh.is_watertight}',
    )
    lo, hi = float(mesh.vertices[:, 2].min()), float(mesh.vertices[:, 2].max())
    checker.check(
        abs(lo - z_low) <= Z_BAND_TOL_MM and abs(hi - z_high) <= Z_BAND_TOL_MM,
        f'{role} ring z band (assembly frame)',
        f'[{lo:.3f}, {hi:.3f}] mm (expected [{z_low:.3f}, {z_high:.3f}] +/- {Z_BAND_TOL_MM})',
    )
    return mesh


def to_program_frame(vertices: np.ndarray, asset: str) -> np.ndarray:
    """Apply the canonical transform, then round to the float32 the asset actually ships."""
    constants = TRANSFORM[asset]
    moved = np.array(vertices, dtype=np.float64)
    moved[:, 0] -= constants['axis_x_mm']
    moved[:, 1] -= constants['axis_y_mm']
    if constants['rotation_z_deg'] == 180.0:
        moved[:, 0] = -moved[:, 0]
        moved[:, 1] = -moved[:, 1]
    elif constants['rotation_z_deg'] != 0.0:
        raise CheckFailed(f'asset {asset}: only 0 and 180 degree z rotations are canonical')
    moved[:, 2] += Z_SHIFT_MM
    return moved.astype(np.float32).astype(np.float64)


def tooth_clusters(vertices: np.ndarray, gap_deg: float = TOOTH_MID_GAP_DEG) -> int:
    """Count teeth by clustering tip-band vertex angles in a thin slice at the ring's mid-plane.

    The meshes carry vertices only on feature edges; the tip band is the one radius
    where every tooth has them, and the chevron apex (mid-plane) is where each tooth's
    tip vertices form one tight cluster. Axis at x=y=0.
    """
    z_mid = (vertices[:, 2].min() + vertices[:, 2].max()) / 2.0
    radius = np.hypot(vertices[:, 0], vertices[:, 1])
    band = vertices[
        (radius > (TIP_RADIUS_MM - TIP_BAND_DEPTH_MM)) & (np.abs(vertices[:, 2] - z_mid) <= TOOTH_MID_PLANE_HALF_MM)
    ]
    if len(band) == 0:
        return 0
    angles = np.sort(np.degrees(np.arctan2(band[:, 1], band[:, 0])) % 360.0)
    gaps = np.diff(np.concatenate([angles, [angles[0] + 360.0]]))
    return max(1, int((gaps > gap_deg).sum()))


def check_gear(checker: Checker, role: str, vertices: np.ndarray) -> dict:
    """Per-gear self-checks: tooth count, tip radius, z band."""
    teeth = tooth_clusters(vertices)
    checker.check(teeth == TOOTH_COUNT, f'{role} tooth count', f'{teeth} (expected {TOOTH_COUNT})')

    radius = np.hypot(vertices[:, 0], vertices[:, 1])
    tip = float(radius.max())
    checker.check(
        abs(tip - TIP_RADIUS_MM) <= TIP_RADIUS_TOL_MM,
        f'{role} tip radius',
        f'{tip:.6f} mm (expected {TIP_RADIUS_MM:.6f} +/- {TIP_RADIUS_TOL_MM})',
    )

    z_lo, z_hi = float(vertices[:, 2].min()), float(vertices[:, 2].max())
    want_lo, want_hi = EXPECTED_Z_BANDS[role]
    checker.check(
        abs(z_lo - want_lo) <= Z_BAND_TOL_MM and abs(z_hi - want_hi) <= Z_BAND_TOL_MM,
        f'{role} z band',
        f'[{z_lo:.3f}, {z_hi:.3f}] mm (expected [{want_lo:.3f}, {want_hi:.3f}] +/- {Z_BAND_TOL_MM})',
    )
    return {'tooth_count': teeth, 'tip_radius_mm': round(tip, 6), 'z_span_mm': [round(z_lo, 6), round(z_hi, 6)]}


def concatenate_bodies(gears: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    """Stack the two gears of a set into one mesh with two disjoint bodies."""
    vertex_blocks: list[np.ndarray] = []
    face_blocks: list[np.ndarray] = []
    offset = 0
    for vertices, faces in gears:
        vertex_blocks.append(vertices)
        face_blocks.append(faces + offset)
        offset += len(vertices)
    return np.vstack(vertex_blocks), np.vstack(face_blocks)


def check_asset(checker: Checker, asset: str, vertices: np.ndarray, faces: np.ndarray) -> dict:
    """Whole-asset self-checks: two watertight bodies, both z bands present, xy envelope."""
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    bodies = mesh.split(only_watertight=False)
    checker.check(len(bodies) == 2, f'asset {asset} body count', f'{len(bodies)} (expected 2)')

    watertight = [bool(body.is_watertight) for body in bodies]
    checker.check(
        all(watertight) and len(watertight) > 0,
        f'asset {asset} watertight per body',
        str(watertight),
    )

    body_spans = sorted((round(float(body.bounds[0][2]), 6), round(float(body.bounds[1][2]), 6)) for body in bodies)
    wanted_spans = sorted({EXPECTED_Z_BANDS[role] for role, _ in SAMPLE_FILES[asset]})
    spans_ok = len(body_spans) == len(wanted_spans) and all(
        abs(got[0] - want[0]) <= Z_BAND_TOL_MM and abs(got[1] - want[1]) <= Z_BAND_TOL_MM
        for got, want in zip(body_spans, wanted_spans, strict=True)
    )
    checker.check(spans_ok, f'asset {asset} z bands', f'{body_spans} mm (expected {wanted_spans})')

    x_floor, x_ceil, y_floor, y_ceil = ASSET_XY_BOUNDS[asset]
    lo, hi = mesh.bounds
    checker.check(
        lo[0] >= x_floor and hi[0] <= x_ceil,
        f'asset {asset} x envelope',
        f'[{lo[0]:.6f}, {hi[0]:.6f}] mm (expected within [{x_floor}, {x_ceil}])',
    )
    checker.check(
        lo[1] >= y_floor and hi[1] <= y_ceil,
        f'asset {asset} y envelope',
        f'[{lo[1]:.6f}, {hi[1]:.6f}] mm (expected within [{y_floor}, {y_ceil}])',
    )

    volumes = [round(float(body.volume), 6) for body in bodies]
    return {
        'bounds_mm': {
            'min': [round(float(v), 6) for v in lo],
            'max': [round(float(v), 6) for v in hi],
        },
        'body_volumes_mm3': volumes,
        'volume_mm3': round(sum(volumes), 6),
        'bodies_watertight': watertight,
    }


def pack_asset(vertices: np.ndarray, faces: np.ndarray) -> bytes:
    """Pack to the little-endian indexed format the worker reads."""
    if faces.max() >= len(vertices) or faces.min() < 0:
        raise CheckFailed('triangle index out of range')
    header = struct.pack('<6sII', MAGIC, len(vertices), len(faces))
    body = vertices.astype('<f4').tobytes() + faces.astype('<u4').tobytes()
    return header + body


def derive(source: Path, out_dir: Path) -> dict:
    checker = Checker()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_assets: dict[str, dict] = {}
    for asset in ('a', 'b'):
        print(f'[asset] gears_{asset}.bin')
        gears: list[tuple[np.ndarray, np.ndarray]] = []
        sources: list[dict] = []
        for role, filename in SAMPLE_FILES[asset]:
            path = source / filename
            if not path.is_file():
                raise CheckFailed(f'missing holder STL: {path}')
            holder = load_holder(path)
            ring = ring_only(checker, role, asset, holder)
            seated = np.array(ring.vertices, dtype=np.float64)
            seated[:, 2] += RING_SEAT_SHIFT_MM[role]
            vertices = to_program_frame(seated, asset)
            metrology = check_gear(checker, role, vertices)
            gears.append((vertices, np.asarray(ring.faces, dtype=np.int64)))
            sources.append(
                {
                    'role': role,
                    'file': filename,
                    'sha256': sha256_of(path),
                    'holder_vert_count': int(len(holder.vertices)),
                    'holder_tri_count': int(len(holder.faces)),
                    'ring_z_band_source_mm': list(RING_Z_BAND_SOURCE[role]),
                    'seat_shift_mm': RING_SEAT_SHIFT_MM[role],
                    'vert_count': int(len(vertices)),
                    'tri_count': int(len(ring.faces)),
                    **metrology,
                }
            )

        vertices, faces = concatenate_bodies(gears)
        measurements = check_asset(checker, asset, vertices, faces)
        payload = pack_asset(vertices, faces)

        out_path = out_dir / f'gears_{asset}.bin'
        out_path.write_bytes(payload)
        print(f'  [ok] wrote {len(payload):,} bytes -> {out_path}')

        manifest_assets[out_path.name] = {
            'sources': sources,
            'vert_count': int(len(vertices)),
            'tri_count': int(len(faces)),
            'byte_size': len(payload),
            **measurements,
            'sha256': sha256_of(out_path),
        }

    checker.raise_if_failed()

    manifest = {
        'note': PROVENANCE_NOTE,
        'derived': DERIVED_DATE,
        'source_parts': (
            "Brennen's Version 1 gear holders A1/A2/B1/B2 (v6): the parts the standard Version 1 "
            'cylinders slide onto, each a 10 mm gear ring plus a 40 mm boss. Only the ring ships, cut '
            'by an exact Manifold intersection with ring_z_band_source_mm and seated on the barrel '
            'end by seat_shift_mm. Until 2026-09-28 the assets were the 2026-08-24 "Rollers v7 (Gear '
            'Sample ...)" set, whose B gears carry a 9 mm bore the Version 1 housing pin cannot enter.'
        ),
        'frame': (
            'Browser worker cylinder frame: axis at x=y=0, barrel centered on z=0 '
            '(cylinder spans z -26..+26, gears -36..-26 and +26..+36). Millimeters, Z-up.'
        ),
        'format': {
            'magic': 'BCGR1\\x00',
            'byte_order': 'little-endian',
            'layout': 'magic[6] + uint32 vertCount + uint32 triCount + float32[3*vertCount] + uint32[3*triCount]',
            'header_bytes': 14,
        },
        'transform': {
            'source': "01_SAMPLE_GEOMETRY_AUDIT.md section 10.2 (the holders share the samples' assembly frame)",
            'a': 'p_programA = Rz(180) * (p_sample - (-16.0000, 0.0000, 0)) - (0, 0, 26.0000)',
            'b': 'p_programB = (p_sample - (+16.0473, -0.0079, 0)) - (0, 0, 26.0000)',
            'constants': {
                'a_axis_x_mm': TRANSFORM['a']['axis_x_mm'],
                'a_axis_y_mm': TRANSFORM['a']['axis_y_mm'],
                'a_rotation_z_deg': TRANSFORM['a']['rotation_z_deg'],
                'b_axis_x_mm': TRANSFORM['b']['axis_x_mm'],
                'b_axis_y_mm': TRANSFORM['b']['axis_y_mm'],
                'b_rotation_z_deg': TRANSFORM['b']['rotation_z_deg'],
                'z_shift_mm': Z_SHIFT_MM,
            },
        },
        'gear_metrology': {
            'tooth_count': TOOTH_COUNT,
            'tip_radius_mm': TIP_RADIUS_MM,
            'gear_thickness_mm': GEAR_THICKNESS_MM,
        },
        'assets': manifest_assets,
    }

    manifest_path = out_dir / 'gears_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'[ok] wrote {manifest_path}')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE, help='folder holding the four holder STLs')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT_DIR, help='output folder for the vendored assets')
    args = parser.parse_args()

    manifest = derive(args.source, args.out)

    print('\n[summary]')
    for name, entry in manifest['assets'].items():
        print(
            f'  {name}: {entry["vert_count"]:,} verts / {entry["tri_count"]:,} tris, '
            f'volume {entry["volume_mm3"]:.3f} mm^3, sha256 {entry["sha256"][:16]}...'
        )
    print('[ok] all self-checks passed')


if __name__ == '__main__':
    main()
