"""Derive the vendored gear assets for the Embosser Version 2 fixed-gear (one-piece) rollers.

Reads Brennen's four v8 Version 2 gear STLs, moves each one from its own source
frame into the browser worker's cylinder frame (axis at x=y=0, barrel centred on
z 0 so the 54 mm Version 2 barrel spans z -27..+27), and writes one packed
indexed binary per roller set plus a provenance manifest.

    python scripts/derive_gear_assets_v2.py

Outputs (regenerate ONLY with this script):
    static/assets/gears/v2_gears_a.bin        A1 (top) + A2 (bottom) as two bodies
    static/assets/gears/v2_gears_b.bin        B1 (top) + B2 (bottom) as two bodies
    static/assets/gears/v2_gears_manifest.json

The gears are a 1:1 replication of the reference geometry - no reconstruction,
no resampling. Unlike scripts/derive_gear_assets.py (Version 1), every axis is
MEASURED here by a least-squares circle fit on each gear's own tip band rather
than typed in, and each gear is centred on its own fitted axis: the two gears
of a set differ by up to 0.005 mm, float noise that must not be silently
averaged away (2026-09-20 programme, phase B1).

Byte layout of a .bin asset is the Version 1 one (little-endian, 14-byte
header, the float block starts at offset 14):

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
import math
import struct
from pathlib import Path

import numpy as np
import trimesh

MAGIC = b'BCGR1\x00'

DEFAULT_SOURCE = Path(r'C:\Users\WATAP\Documents\Research\Braille Embosser\New Developement_2026_09_20\Gear Parts')
DEFAULT_OUT_DIR = Path('static/assets/gears')

# Bump only when the source files change: it keeps re-runs byte-idempotent.
DERIVED_DATE = '2026-09-21'

PROVENANCE_NOTE = (
    "Derived 1:1 from Brennen's v8 Version 2 gear STLs; regenerate only via scripts/derive_gear_assets_v2.py"
)

SAMPLE_FILES = {
    'a': [
        ('A1', 'A1 Gear v8 (0.2 Layer Height).stl'),
        ('A2', 'A2 Gear v8 (0.2 Layer Height).stl'),
    ],
    'b': [
        ('B1', 'B1 Gear v8 (0.2 Layer Height).stl'),
        ('B2', 'B2 Gear v8 (0.2 Layer Height).stl'),
    ],
}

# Source frame -> program frame. The A set's notch and pin sit at 0 degrees in
# the files, the B set's at 180; the program puts every anti-rotation feature
# on the 180 degree arrow column (app/geometry/version2.py V2_ARROW_COLUMN_DEG),
# so A turns by 180 and B keeps its clocking - the same rule as Version 1.
ROTATION_Z_DEG = {'a': 180.0, 'b': 0.0}
# The files place the 54 mm barrel at z 0..54; the program centres it on z 0.
Z_SHIFT_MM = -27.0
ARROW_COLUMN_DEG = 180.0

TOOTH_COUNT = 24
TIP_RADIUS_MM = 16.1093702290795
TIP_RADIUS_TOL_MM = 0.001
TIP_BAND_DEPTH_MM = 0.05
TOOTH_GAP_DEG = 2.0
GEAR_THICKNESS_MM = 10.0
AXIS_AGREEMENT_TOL_MM = 0.02

# Program-frame z band of each gear INCLUDING its 15 mm peg (which sits inside
# the barrel): body 27..37 / -37..-27, peg 12..27 / -27..-12.
EXPECTED_Z_BANDS = {
    'A1': (12.000, 37.000),
    'A2': (-37.000, -12.000),
    'B1': (12.000, 37.000),
    'B2': (-37.000, -12.000),
}
Z_BAND_TOL_MM = 0.001
BARREL_FACE_Z = {'A1': 27.0, 'A2': -27.0, 'B1': 27.0, 'B2': -27.0}
PEG_LENGTH_MM = 15.0

# Peg outline at its free end (measured 3 mm in from the end, past the tapered
# tip), program frame: (x extent, y extent). The long side lies along y so a
# flat always faces the arrow column - app/geometry/version2.py V2_KEY_PROFILES.
EXPECTED_PEG_OUTLINE_MM = {
    'A1': (14.0, 14.0),
    'A2': (10.0, 18.0),
    'B1': (12.0, 16.0),
    'B2': (8.0, 20.0),
}
PEG_OUTLINE_TOL_MM = 0.05
PEG_SECTION_FROM_END_MM = 3.0

FEATURE_KIND = {'A1': 'notch', 'A2': 'pin', 'B1': 'notch', 'B2': 'pin'}
FEATURE_ANGLE_TOL_DEG = 1.0
FEATURE_SCAN_RADIUS_MM = 11.5
FEATURE_SCAN_DEPTH_MM = 1.5
FEATURE_WINDOW_HALF_DEG = 20.0
ROOT_RADIUS_MIN_MM = 13.65
PROBE_ANGLES_DEG = np.arange(0.0, 360.0, 5.0)
PROBE_INSET_MM = 0.05
WELD_RING_RADII_MM = (8.0, 9.5)
WELD_BAND_RADII_MM = (10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0)

# xy envelope of the whole asset (tip radius plus float noise).
ASSET_XY_BOUND_MM = 16.110


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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gear(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise CheckFailed(f'{path.name}: expected a single mesh, got {type(mesh).__name__}')
    mesh.merge_vertices()
    if not mesh.is_watertight:
        raise CheckFailed(f'{path.name}: not watertight after exact vertex merge')
    return mesh


def fit_axis(vertices: np.ndarray) -> tuple[float, float, float]:
    """Least-squares circle through the tip-band vertices: (axis_x, axis_y, fitted tip radius)."""
    cx0 = (vertices[:, 0].min() + vertices[:, 0].max()) / 2.0
    cy0 = (vertices[:, 1].min() + vertices[:, 1].max()) / 2.0
    provisional = np.hypot(vertices[:, 0] - cx0, vertices[:, 1] - cy0)
    band = vertices[provisional > TIP_RADIUS_MM - TIP_BAND_DEPTH_MM]
    x, y = band[:, 0], band[:, 1]
    design = np.column_stack([2 * x, 2 * y, np.ones_like(x)])
    (cx, cy, c), *_ = np.linalg.lstsq(design, x * x + y * y, rcond=None)
    return float(cx), float(cy), float(math.sqrt(c + cx * cx + cy * cy))


def to_program_frame(vertices: np.ndarray, axis: tuple[float, float], asset: str) -> np.ndarray:
    moved = np.array(vertices, dtype=np.float64)
    moved[:, 0] -= axis[0]
    moved[:, 1] -= axis[1]
    if ROTATION_Z_DEG[asset] == 180.0:
        moved[:, 0] = -moved[:, 0]
        moved[:, 1] = -moved[:, 1]
    moved[:, 2] += Z_SHIFT_MM
    return moved.astype(np.float32).astype(np.float64)


def tooth_clusters(vertices: np.ndarray) -> int:
    radius = np.hypot(vertices[:, 0], vertices[:, 1])
    band = vertices[radius > (TIP_RADIUS_MM - TIP_BAND_DEPTH_MM)]
    if len(band) == 0:
        return 0
    angles = np.sort(np.degrees(np.arctan2(band[:, 1], band[:, 0])) % 360.0)
    gaps = np.diff(np.concatenate([angles, [angles[0] + 360.0]]))
    return max(1, int((gaps > TOOTH_GAP_DEG).sum()))


def angular_distance_deg(angles: np.ndarray, centre: float) -> np.ndarray:
    return np.abs(((angles - centre + 180.0) % 360.0) - 180.0)


def circle_points(radius: float, angles_deg: np.ndarray, z: float) -> np.ndarray:
    rad = np.radians(angles_deg)
    return np.column_stack([radius * np.cos(rad), radius * np.sin(rad), np.full_like(rad, z)])


def measure_peg_outline(mesh: trimesh.Trimesh, role: str) -> tuple[float, float]:
    top = BARREL_FACE_Z[role] > 0
    free_end = BARREL_FACE_Z[role] - PEG_LENGTH_MM if top else BARREL_FACE_Z[role] + PEG_LENGTH_MM
    z = free_end + PEG_SECTION_FROM_END_MM if top else free_end - PEG_SECTION_FROM_END_MM
    section = mesh.section(plane_origin=[0.0, 0.0, z], plane_normal=[0.0, 0.0, 1.0])
    if section is None:
        raise CheckFailed(f'{role}: no cross-section at z {z:.2f} - is the peg where the frame says it is?')
    points = np.asarray(section.vertices)
    return float(points[:, 0].max() - points[:, 0].min()), float(points[:, 1].max() - points[:, 1].min())


def measure_feature(mesh: trimesh.Trimesh, role: str) -> dict:
    """The anti-rotation notch (top gears) or pin (bottom gears) by containment scans."""
    top = BARREL_FACE_Z[role] > 0
    face = BARREL_FACE_Z[role]
    kind = FEATURE_KIND[role]
    # Notches are cut INTO the gear from its barrel-facing face; pins stand OUT of it
    # into the barrel. Scan 1.5 mm into whichever side holds the feature.
    z = face + FEATURE_SCAN_DEPTH_MM if top else face - FEATURE_SCAN_DEPTH_MM
    if kind == 'pin':
        z = face - FEATURE_SCAN_DEPTH_MM if top else face + FEATURE_SCAN_DEPTH_MM
    angles = np.arange(0.0, 360.0, 0.25)
    inside = mesh.contains(circle_points(FEATURE_SCAN_RADIUS_MM, angles, z))
    selected = angles[~inside] if kind == 'notch' else angles[inside]
    if len(selected) == 0:
        raise CheckFailed(f'{role}: no {kind} found at r {FEATURE_SCAN_RADIUS_MM} mm, z {z:.2f}')
    rad = np.radians(selected)
    centre = math.degrees(math.atan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360.0
    half_deg = float(angular_distance_deg(selected, centre).max()) + 0.125
    # Radial extent along the column.
    radii = np.arange(9.0, 14.6, 0.05)
    column = np.column_stack(
        [radii * math.cos(math.radians(centre)), radii * math.sin(math.radians(centre)), np.full_like(radii, z)]
    )
    inside_r = mesh.contains(column)
    radial = radii[~inside_r] if kind == 'notch' else radii[inside_r]
    # Depth (notch) or height (pin) along the column at r 12.
    zs = np.arange(face - 4.0, face + 4.0, 0.05)
    axial = np.column_stack(
        [
            np.full_like(zs, 12.0 * math.cos(math.radians(centre))),
            np.full_like(zs, 12.0 * math.sin(math.radians(centre))),
            zs,
        ]
    )
    inside_z = mesh.contains(axial)
    if kind == 'notch':
        air = zs[~inside_z & ((zs > face) if top else (zs < face))]
        extent = float(abs(air.max() - face)) if top else float(abs(face - air.min()))
    else:
        solid = zs[inside_z & ((zs < face) if top else (zs > face))]
        extent = float(abs(face - solid.min())) if top else float(abs(solid.max() - face))
    return {
        'kind': kind,
        'angle_deg': round(centre, 3),
        'half_width_deg_at_r11_5': round(half_deg, 3),
        'half_width_mm_at_r11_5': round(FEATURE_SCAN_RADIUS_MM * math.sin(math.radians(half_deg)), 4),
        'inner_radius_mm': round(float(radial.min()), 3),
        'outer_radius_mm': round(float(radial.max()), 3),
        'depth_mm' if kind == 'notch' else 'height_mm': round(extent, 3),
    }


def measure_root_radius(vertices: np.ndarray) -> float:
    radius = np.hypot(vertices[:, 0], vertices[:, 1])
    tip_band = vertices[radius > TIP_RADIUS_MM - 0.5]
    z_lo, z_hi = float(tip_band[:, 2].min()), float(tip_band[:, 2].max())
    angles = np.degrees(np.arctan2(vertices[:, 1], vertices[:, 0])) % 360.0
    mask = (
        (vertices[:, 2] > z_lo)
        & (vertices[:, 2] < z_hi)
        & (radius > 13.0)
        & (angular_distance_deg(angles, ARROW_COLUMN_DEG) > 25.0)
    )
    return float(radius[mask].min())


def check_gear(checker: Checker, role: str, mesh: trimesh.Trimesh) -> dict:
    vertices = mesh.vertices
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
        f'{role} z band (gear + peg)',
        f'[{z_lo:.3f}, {z_hi:.3f}] mm (expected [{want_lo:.3f}, {want_hi:.3f}] +/- {Z_BAND_TOL_MM})',
    )

    outline = measure_peg_outline(mesh, role)
    want = EXPECTED_PEG_OUTLINE_MM[role]
    checker.check(
        abs(outline[0] - want[0]) <= PEG_OUTLINE_TOL_MM and abs(outline[1] - want[1]) <= PEG_OUTLINE_TOL_MM,
        f'{role} peg outline {PEG_SECTION_FROM_END_MM} mm from its end',
        f'{outline[0]:.3f} x {outline[1]:.3f} mm (expected {want[0]} x {want[1]} +/- {PEG_OUTLINE_TOL_MM})',
    )

    feature = measure_feature(mesh, role)
    checker.check(
        angular_distance_deg(np.array([feature['angle_deg']]), ARROW_COLUMN_DEG)[0] <= FEATURE_ANGLE_TOL_DEG,
        f'{role} {feature["kind"]} on the arrow column',
        f'{feature["angle_deg"]:.3f} deg (expected {ARROW_COLUMN_DEG} +/- {FEATURE_ANGLE_TOL_DEG})',
    )

    root = measure_root_radius(vertices)
    checker.check(
        root >= ROOT_RADIUS_MIN_MM, f'{role} root radius', f'{root:.4f} mm (expected >= {ROOT_RADIUS_MIN_MM})'
    )

    # Weld-ring band, 0.05 mm inside the gear from its barrel-facing face: solid at
    # r 8.0 and 9.5 at every angle, and at r 10..13 everywhere outside the notch window.
    face = BARREL_FACE_Z[role]
    z_probe = face + PROBE_INSET_MM if face > 0 else face - PROBE_INSET_MM
    for r_probe in WELD_RING_RADII_MM:
        inside = mesh.contains(circle_points(r_probe, PROBE_ANGLES_DEG, z_probe))
        hollow = PROBE_ANGLES_DEG[~inside]
        checker.check(len(hollow) == 0, f'{role} solid at r {r_probe} on the face', f'hollow at {hollow.tolist()}')
    outside_window = angular_distance_deg(PROBE_ANGLES_DEG, ARROW_COLUMN_DEG) > FEATURE_WINDOW_HALF_DEG
    for r_probe in WELD_BAND_RADII_MM:
        inside = mesh.contains(circle_points(r_probe, PROBE_ANGLES_DEG[outside_window], z_probe))
        hollow = PROBE_ANGLES_DEG[outside_window][~inside]
        checker.check(
            len(hollow) == 0,
            f'{role} solid at r {r_probe} outside the feature window',
            f'hollow at {hollow.tolist()}',
        )

    return {
        'tooth_count': teeth,
        'tip_radius_mm': round(tip, 6),
        'z_span_mm': [round(z_lo, 6), round(z_hi, 6)],
        'peg_outline_mm': [round(outline[0], 3), round(outline[1], 3)],
        'root_radius_mm': round(root, 4),
        'feature': feature,
    }


def concatenate_bodies(gears: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    vertex_blocks: list[np.ndarray] = []
    face_blocks: list[np.ndarray] = []
    offset = 0
    for vertices, faces in gears:
        vertex_blocks.append(vertices)
        face_blocks.append(faces + offset)
        offset += len(vertices)
    return np.vstack(vertex_blocks), np.vstack(face_blocks)


def check_asset(checker: Checker, asset: str, vertices: np.ndarray, faces: np.ndarray) -> dict:
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    bodies = mesh.split(only_watertight=False)
    checker.check(len(bodies) == 2, f'asset {asset} body count', f'{len(bodies)} (expected 2)')
    watertight = [bool(body.is_watertight) for body in bodies]
    checker.check(all(watertight) and len(watertight) > 0, f'asset {asset} watertight per body', str(watertight))

    lo, hi = mesh.bounds
    checker.check(
        lo[0] >= -ASSET_XY_BOUND_MM
        and hi[0] <= ASSET_XY_BOUND_MM
        and lo[1] >= -ASSET_XY_BOUND_MM
        and hi[1] <= ASSET_XY_BOUND_MM,
        f'asset {asset} xy envelope',
        f'x [{lo[0]:.6f}, {hi[0]:.6f}] y [{lo[1]:.6f}, {hi[1]:.6f}] mm (expected within +/- {ASSET_XY_BOUND_MM})',
    )
    volumes = [round(float(body.volume), 6) for body in bodies]
    return {
        'bounds_mm': {'min': [round(float(v), 6) for v in lo], 'max': [round(float(v), 6) for v in hi]},
        'body_volumes_mm3': volumes,
        'volume_mm3': round(sum(volumes), 6),
        'bodies_watertight': watertight,
    }


def pack_asset(vertices: np.ndarray, faces: np.ndarray) -> bytes:
    if faces.max() >= len(vertices) or faces.min() < 0:
        raise CheckFailed('triangle index out of range')
    header = struct.pack('<6sII', MAGIC, len(vertices), len(faces))
    return header + vertices.astype('<f4').tobytes() + faces.astype('<u4').tobytes()


def derive(source: Path, out_dir: Path) -> dict:
    checker = Checker()
    out_dir.mkdir(parents=True, exist_ok=True)

    # (a) the four sources must be four different files - the mistake found on
    # 2026-09-20, when B2 arrived as a byte copy of A1.
    hashes = {role: sha256_of(source / filename) for pairs in SAMPLE_FILES.values() for role, filename in pairs}
    checker.check(
        len(set(hashes.values())) == 4, 'four distinct source files', str({k: v[:12] for k, v in hashes.items()})
    )

    manifest_assets: dict[str, dict] = {}
    for asset in ('a', 'b'):
        print(f'[asset] v2_gears_{asset}.bin')
        gears: list[tuple[np.ndarray, np.ndarray]] = []
        sources: list[dict] = []
        axes: dict[str, tuple[float, float]] = {}
        for role, filename in SAMPLE_FILES[asset]:
            path = source / filename
            if not path.is_file():
                raise CheckFailed(f'missing source STL: {path}')
            raw = load_gear(path)
            axis_x, axis_y, fitted_tip = fit_axis(raw.vertices)
            axes[role] = (axis_x, axis_y)
            checker.check(
                abs(fitted_tip - TIP_RADIUS_MM) <= TIP_RADIUS_TOL_MM,
                f'{role} fitted tip radius',
                f'{fitted_tip:.6f} mm about axis ({axis_x:.4f}, {axis_y:.4f})',
            )
            vertices = to_program_frame(raw.vertices, (axis_x, axis_y), asset)
            faces = np.asarray(raw.faces, dtype=np.int64)
            placed = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
            metrology = check_gear(checker, role, placed)
            gears.append((vertices, faces))
            sources.append(
                {
                    'role': role,
                    'file': filename,
                    'sha256': hashes[role],
                    'axis_fit_source_frame_mm': [round(axis_x, 4), round(axis_y, 4)],
                    'vert_count': int(len(vertices)),
                    'tri_count': int(len(faces)),
                    **metrology,
                }
            )
        (r1, r2) = (SAMPLE_FILES[asset][0][0], SAMPLE_FILES[asset][1][0])
        agreement = math.hypot(axes[r1][0] - axes[r2][0], axes[r1][1] - axes[r2][1])
        checker.check(
            agreement <= AXIS_AGREEMENT_TOL_MM,
            f'asset {asset} axes agree',
            f'{r1} vs {r2} differ by {agreement:.4f} mm (allowed {AXIS_AGREEMENT_TOL_MM}); each gear is centred on its own',
        )

        vertices, faces = concatenate_bodies(gears)
        measurements = check_asset(checker, asset, vertices, faces)
        payload = pack_asset(vertices, faces)
        out_path = out_dir / f'v2_gears_{asset}.bin'
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
        'frame': (
            'Browser worker cylinder frame: axis at x=y=0, barrel centred on z=0 '
            '(the 54 mm Version 2 barrel spans z -27..+27; gear bodies +27..+37 and -37..-27; '
            'the 15 mm pegs sit inside the barrel at |z| 12..27). Millimeters, Z-up.'
        ),
        'format': {
            'magic': 'BCGR1\\x00',
            'byte_order': 'little-endian',
            'layout': 'magic[6] + uint32 vertCount + uint32 triCount + float32[3*vertCount] + uint32[3*triCount]',
            'header_bytes': 14,
        },
        'transform': {
            'source': '01_V2_GEAR_AUDIT.md (2026-09-20 programme, phase B1)',
            'rule': (
                'each gear is centred on its OWN least-squares tip-band axis (recorded per source); '
                'A set: p = Rz(180) * (p_source - axis) + (0, 0, -27); B set: p = (p_source - axis) + (0, 0, -27)'
            ),
            'constants': {
                'a_rotation_z_deg': ROTATION_Z_DEG['a'],
                'b_rotation_z_deg': ROTATION_Z_DEG['b'],
                'z_shift_mm': Z_SHIFT_MM,
                'arrow_column_deg': ARROW_COLUMN_DEG,
            },
        },
        'gear_metrology': {
            'tooth_count': TOOTH_COUNT,
            'tip_radius_mm': TIP_RADIUS_MM,
            'gear_thickness_mm': GEAR_THICKNESS_MM,
            'peg_length_mm': PEG_LENGTH_MM,
            'root_radius_min_mm': ROOT_RADIUS_MIN_MM,
        },
        'assets': manifest_assets,
    }
    manifest_path = out_dir / 'v2_gears_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'[ok] wrote {manifest_path}')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE, help='folder holding the four v8 STLs')
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
