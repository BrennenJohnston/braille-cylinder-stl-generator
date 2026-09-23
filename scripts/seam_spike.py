"""Seam-channel slicing spike (2026-09-20 programme, Phase A0). Dev-only; changes nothing in the app.

Question: does a full-height groove beside the row-indicator column make a slicer in its
default "aligned" seam mode put every layer's outer-wall seam in the groove instead of on a
braille dot or bowl - and does turning the part so the groove faces +Y do the same for
"rear" mode?

    python scripts/seam_spike.py            # build, slice, report -> build/seam_spike/REPORT.md
    python scripts/seam_spike.py --no-slice # build the STLs only
    python scripts/seam_spike.py --layouts tactile14,tactile13 --channels none,v10 --no-rear \
        --out build/seam_spike_through      # the 2026-09-21 D-T7 rerun (full height, recut through the arrows)
    python scripts/seam_spike.py --layouts tactile13,tactile14,tactile12x3 --channels none,v10 --no-rear \
        --out build/seam_spike_detour       # the 2026-09-22 D-T8 rerun (round the raised arrows)

2026-09-21 (D-T6, D-T7): in tactile mode the groove runs down the arrow column itself (180
degrees) the full height. 2026-09-22 (D-T8): on the embossing plate it steps round the raised
arrows on the first-cell side instead of being recut through them, so the tactile groove here is
the spec's own block - angle and path, cut with the golden renderer's cutter - "in channel" is
measured against the path's angle at each layer's height, and main() refuses to run if this
script and the spec disagree about the angle.

Cylinders are built with the repo's own geometry spec (app.geometry_spec) and the golden
fixture renderer's helpers (tests/test_golden.py), so dots, bowls and tactile arrows are the
shipped ones. The visual-mode triangle and letter markers are modelled as simple recesses
(the worker hulls the same outlines). The barrel carries the Version 1 twelve-sided bore.
Slicing uses the PrusaSlicer console with the local user profiles; Bambu Studio's seam
placer is a fork of PrusaSlicer's, so this is the automatable proxy and Bambu Studio is the
human confirmation (NEEDS-HUMAN, plan A0 step 6).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app.geometry_spec import extract_cylinder_geometry_spec  # noqa: E402
from app.models import CardSettings  # noqa: E402
from app.utils import braille_to_dots  # noqa: E402
from tests.test_golden import (  # noqa: E402
    _DS_SHELL_SECTIONS,
    _ds_bowl_cutter,
    _ds_rounded_dot_meshes,
    _ds_tactile_arrow_mesh,
    _seam_channel_cutter,
    _stabilize_for_stl,
)

OUT = REPO / 'build' / 'seam_spike'
PRUSA = Path(r'C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe')
PROFILES = Path(os.environ.get('APPDATA', '')) / 'PrusaSlicer'

# The live-UI (Layer 2) 0.4 mm preset cylinder, as the app sends it.
CYLINDER_PARAMS = {
    'diameter': 30.8,
    'height': 52.0,
    'wall_thickness': 2.0,
    'polygonal_cutout_radius_mm': 13.0,
    'polygonal_cutout_sides': 12,
    'seam_offset_deg': 0.0,
}
BASE_SETTINGS = {
    'grid_rows': 4,
    'cell_spacing': 6.5,
    'line_spacing': 10.0,
    'dot_spacing': 2.5,
    'use_rounded_dots': 1,
    'rounded_dot_base_diameter': 1.5,
    'rounded_dot_base_height': 0.5,
    'rounded_dot_dome_diameter': 1.0,
    'rounded_dot_dome_height': 0.5,
    'recess_shape': 1,
    'bowl_counter_dot_base_diameter': 1.8,
    'counter_dot_depth': 0.8,
    'indicator_shapes': 1,
}
# Every cell full of dots: the hardest case for a seam placer looking for corners.
FULL_ROW = '\u283f'
LAYOUTS = {
    # name: (indicator_mode, total grid_columns, text cells per row)
    'visual15': ('visual', 15, 13),
    'tactile14': ('tactile', 14, 14),
    # The tactile recommendation since 2026-09-21 (D-T4): 14 fit the cylinder
    # but run off a 90 mm card loaded at the arrow.
    'tactile13': ('tactile', 13, 13),
    # The 0.3 mm preset's marking: three separated arrows (2026-09-20), so the
    # D-T8 groove returns to the column between them.
    'tactile12x3': ('tactile', 12, 12),
}
# Settings only some layouts carry, on top of BASE_SETTINGS.
LAYOUT_SETTINGS = {'tactile12x3': {'tactile_indicator_layout': 'three_spaced'}}
# Plan A2 constants (D-4): V 1.2 x 0.6 first, 1.0 x 0.5 as the fallback, a rectangle for contrast.
CHANNELS = {
    'none': None,
    'v12': {'shape': 'v', 'width': 1.2, 'depth': 0.6},
    'v10': {'shape': 'v', 'width': 1.0, 'depth': 0.5},
    'rect10': {'shape': 'rect', 'width': 1.0, 'depth': 0.5},
}
CHANNEL_MARGIN_MM = 0.25
CHANNEL_LIP_MM = 0.5
CHANNEL_OVERSHOOT_MM = 1.0
SEAM_TOLERANCE_MM = 0.3  # the seam counts as "in the channel" within half the width + this
SLICE_CENTER = (127.0, 77.0)


def settings_for(layout: str) -> CardSettings:
    mode, columns, _ = LAYOUTS[layout]
    return CardSettings(
        **{**BASE_SETTINGS, 'grid_columns': columns, 'indicator_mode': mode, **LAYOUT_SETTINGS.get(layout, {})}
    )


def lines_for(layout: str) -> list[str]:
    _, _, text_cells = LAYOUTS[layout]
    return [FULL_ROW * text_cells] * 4


def spec_for(layout: str, plate_type: str) -> dict:
    settings = settings_for(layout)
    lines = lines_for(layout)
    return extract_cylinder_geometry_spec(
        lines, 'g1', settings, CYLINDER_PARAMS, ['a', 'b', 'c', 'd'], plate_type, braille_to_dots_func=braille_to_dots
    )


# --------------------------------------------------------------------------------------
# Channel placement: plan A2, signed arc s from the seam centre, positive toward column 0.
# --------------------------------------------------------------------------------------
def channel_placement(layout: str, plate_type: str, settings: CardSettings, channel: dict | None) -> dict:
    radius = CYLINDER_PARAMS['diameter'] / 2.0
    mode, columns, _ = LAYOUTS[layout]
    gap = math.pi * CYLINDER_PARAMS['diameter'] - (columns - 1) * settings.cell_spacing
    footprint = settings.dot_spacing / 2.0 + max(
        settings.rounded_dot_base_diameter / 2.0, settings.bowl_counter_dot_base_diameter / 2.0
    )
    if mode == 'visual':
        lo = -(gap / 2.0 - footprint)
        hi = gap / 2.0 - settings.dot_spacing / 2.0
    else:
        # D-T6 (2026-09-21): down the arrow column itself, outside the arrow
        # chain - no window to fit. The stretches come from the spec's block.
        return {'gap_mm': gap, 'free_mm': math.inf, 'need_mm': 0.0, 'fits': True, 's_c_mm': 0.0, 'theta': math.pi}
    free = hi - lo
    width = channel['width'] if channel else 0.0
    need = width + 2.0 * CHANNEL_MARGIN_MM
    s_c = (lo + hi) / 2.0
    theta = math.pi - s_c / radius if plate_type == 'positive' else math.pi + s_c / radius
    return {'gap_mm': gap, 'free_mm': free, 'need_mm': need, 'fits': free >= need, 's_c_mm': s_c, 'theta': theta}


def channel_cutter(channel: dict, theta: float, radius: float, height: float) -> trimesh.Trimesh:
    """
    Groove cutter: V or rectangle cross-section in the (radial, circumferential)
    plane, the full height plus the overshoot.
    """
    width, depth = channel['width'], channel['depth']
    r_out = radius + CHANNEL_LIP_MM
    if channel['shape'] == 'v':
        w_out = width * (depth + CHANNEL_LIP_MM) / depth
        section = [(r_out, -w_out / 2.0), (r_out, w_out / 2.0), (radius - depth, 0.0)]
    else:
        section = [
            (r_out, -width / 2.0),
            (r_out, width / 2.0),
            (radius - depth, width / 2.0),
            (radius - depth, -width / 2.0),
        ]
    # local (u radial, v circumferential) -> world xy at angle theta
    c, s = math.cos(theta), math.sin(theta)
    poly = Polygon([(u * c - v * s, u * s + v * c) for u, v in section])
    full = height + 2.0 * CHANNEL_OVERSHOOT_MM
    prism = trimesh.creation.extrude_polygon(poly, height=full)
    prism.apply_translation([0.0, 0.0, -full / 2.0])
    return prism


def bore_cutter(spec: dict) -> trimesh.Trimesh:
    points = [(p['x'], p['y']) for p in spec['cylinder']['polygon_points']]
    length = spec['cylinder']['height'] * 1.5
    prism = trimesh.creation.extrude_polygon(Polygon(points), height=length)
    prism.apply_translation([0.0, 0.0, -length / 2.0])
    return prism


def _radial_prism(
    outline_xy: list[tuple[float, float]], theta: float, radius: float, y: float, depth: float
) -> trimesh.Trimesh:
    """An outline in the arrow's local frame (x circumferential, y axial) extruded radially from R-depth to R+0.5."""
    span = depth + CHANNEL_LIP_MM
    prism = trimesh.creation.extrude_polygon(Polygon(outline_xy), height=span)
    prism.apply_translation([0.0, 0.0, -depth])  # z: -depth .. +lip, then z -> radial
    place = np.eye(4)
    place[:3, 0] = [-math.sin(theta), math.cos(theta), 0.0]
    place[:3, 1] = [0.0, 0.0, 1.0]
    place[:3, 2] = [math.cos(theta), math.sin(theta), 0.0]
    place[:3, 3] = [radius * math.cos(theta), radius * math.sin(theta), y]
    prism.apply_transform(place)
    return prism


def visual_marker_cutter(marker: dict) -> trimesh.Trimesh:
    """Triangle / letter / rectangle markers as plain recesses of the worker's outline sizes."""
    kind = marker['type']
    radius, theta, y = marker['radius'], marker['theta'], marker['y']
    if kind == 'cylinder_triangle':
        size, depth = marker['size'], marker['depth']
        if marker.get('rotate_180'):
            outline = [(size / 2.0, size), (size / 2.0, -size), (-size / 2.0, 0.0)]
        else:
            outline = [(-size / 2.0, -size), (-size / 2.0, size), (size / 2.0, 0.0)]
        return _radial_prism(outline, theta, radius, y, depth)
    if kind == 'cylinder_character':
        size, depth = marker['size'], marker['depth']
        h = size / 2.0
        return _radial_prism([(-h, -h), (h, -h), (h, h), (-h, h)], theta, radius, y, depth)
    if kind == 'cylinder_rect':
        w, h, depth = marker['width'] / 2.0, marker['height'] / 2.0, marker['depth']
        return _radial_prism([(-w, -h), (w, -h), (w, h), (-w, h)], theta, radius, y, depth)
    raise ValueError(f'unexpected marker type {kind!r}')


def build_cylinder(
    spec: dict, channel: dict | None, theta_c: float | None, detour: dict | None = None
) -> trimesh.Trimesh:
    """`detour` is the spec's own seam_channel block when it carries a path (D-T8): cut instead of a straight groove."""
    cylinder = spec['cylinder']
    radius, height = cylinder['radius'], cylinder['height']
    shell = trimesh.creation.cylinder(radius=radius, height=height, sections=_DS_SHELL_SECTIONS)
    cutters = [bore_cutter(spec)]
    if detour is not None:
        cutters.append(_seam_channel_cutter(detour, radius, height))
    elif channel and theta_c is not None:
        cutters.append(channel_cutter(channel, theta_c, radius, height))
    # Shell stage first (bore + channel), then raised features, then recesses - the worker's order.
    shell = trimesh.boolean.difference([shell, trimesh.boolean.union(cutters, engine='manifold')], engine='manifold')
    raised = [shell]
    recesses = []
    for marker in spec['markers']:
        if marker['type'] == 'cylinder_tactile_arrow':
            (recesses if marker['is_recess'] else raised).append(_ds_tactile_arrow_mesh(marker))
        else:
            recesses.append(visual_marker_cutter(marker))
    for dot in spec['dots']:
        if dot['is_recess']:
            recesses.append(_ds_bowl_cutter(dot))
        else:
            raised.extend(_ds_rounded_dot_meshes(dot))
    solid = trimesh.boolean.union(raised, engine='manifold')
    if recesses:
        solid = trimesh.boolean.difference(
            [solid, trimesh.boolean.union(recesses, engine='manifold')], engine='manifold'
        )
    return _stabilize_for_stl(solid)


def rotate_to_face_rear(mesh: trimesh.Trimesh, theta_c: float) -> trimesh.Trimesh:
    turned = mesh.copy()
    turned.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2.0 - theta_c, [0, 0, 1]))
    return turned


# --------------------------------------------------------------------------------------
# Slicing and seam extraction
# --------------------------------------------------------------------------------------
def slice_stl(stl: Path, seam_mode: str, gcode: Path) -> None:
    # Command-line flags only: `--load` of the local user profiles segfaults the
    # console build (measured 2026-09-20); the built-in defaults plus these
    # overrides slice cleanly. 0.4 mm nozzle, 0.45 mm walls, three perimeters,
    # 0.2 mm layers - the Bambu Studio X1C defaults.
    command = [
        str(PRUSA),
        '--export-gcode',
        '--seam-position',
        seam_mode,
        '--layer-height',
        '0.2',
        '--first-layer-height',
        '0.2',
        '--nozzle-diameter',
        '0.4',
        '--perimeters',
        '3',
        '--extrusion-width',
        '0.45',
        '--fill-density',
        '15%',
        '--gcode-comments',
        '--center',
        f'{SLICE_CENTER[0]},{SLICE_CENTER[1]}',
        '--output',
        str(gcode),
        str(stl),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode != 0 or not gcode.exists():
        raise RuntimeError(
            f'slicing failed for {stl.name} ({seam_mode}):\n{result.stdout[-1500:]}\n{result.stderr[-1500:]}'
        )


_MOVE = re.compile(r'^G[01]\b(?=.*\bX(?P<x>-?[\d.]+))(?=.*\bY(?P<y>-?[\d.]+))?(?=.*\bE(?P<e>-?[\d.]+))?')


def outer_wall_seams(gcode: Path, radius: float, first_per_layer: bool = True) -> list[tuple[float, float]]:
    """
    (z, theta_deg) of the layer seam: the start of the OUTER wall's first external
    perimeter on every layer.

    The slicer labels every external-perimeter PATH, and on a layer through a dot
    row it prints the outer wall in many paths - one per dot bump, each with its own
    `;TYPE:External perimeter` line and its own start point. Those starts march
    around the barrel at the dot pitch and are path breaks, not seam choices, so
    only the first outer-wall start per layer is the seam. `first_per_layer=False`
    returns every start (the 2026-09-20 first-pass numbers were computed that way
    and looked like a 45 % failure that did not exist).
    """
    seams = []
    seen_layers = set()
    z = None
    relative_e = False
    last_e = 0.0
    pos = None
    awaiting = False
    cx, cy = SLICE_CENTER
    for raw in gcode.read_text(encoding='utf-8', errors='replace').splitlines():
        line = raw.strip()
        if line.startswith(';Z:'):
            z = float(line[3:])
            continue
        if line.startswith(';TYPE:'):
            awaiting = line == ';TYPE:External perimeter'
            continue
        if line.startswith('M83'):
            relative_e = True
            continue
        if line.startswith('M82'):
            relative_e = False
            continue
        if line.startswith('G92') and 'E' in line:
            last_e = 0.0
            continue
        if not line.startswith(('G1', 'G0')):
            continue
        parts = dict(re.findall(r'\b([XYZE])(-?[\d.]+)', line))
        e = float(parts['E']) if 'E' in parts else None
        extruding = False
        if e is not None:
            extruding = (e > 0.0) if relative_e else (e > last_e)
            if not relative_e:
                last_e = e
        if 'X' in parts and 'Y' in parts:
            new_pos = (float(parts['X']), float(parts['Y']))
            if awaiting and extruding and pos is not None and z is not None:
                r = math.hypot(pos[0] - cx, pos[1] - cy)
                if r > radius - 1.0:  # the outer wall, not the bore
                    layer = round(z, 3)
                    if not first_per_layer or layer not in seen_layers:
                        seen_layers.add(layer)
                        seams.append((z, math.degrees(math.atan2(pos[1] - cy, pos[0] - cx)) % 360.0))
                    awaiting = False
            pos = new_pos
    return seams


def angular_error_deg(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def groove_angle_at(detour: dict | None, theta_c: float, height: float):
    """The groove's angle (deg) at a layer's height above the bed: the column, or the detour path's there (D-T8)."""
    if detour is None:
        return lambda z: math.degrees(theta_c)
    heights = [point['z'] + height / 2.0 for point in detour['path']]
    angles = [point['theta'] for point in detour['path']]
    return lambda z: math.degrees(float(np.interp(z, heights, angles)))


def dot_windows(spec: dict) -> list[tuple[float, float, float]]:
    """(z_from_base, theta_deg, half_width_deg) for every dot or bowl footprint."""
    radius = spec['cylinder']['radius']
    height = spec['cylinder']['height']
    out = []
    for dot in spec['dots']:
        params = dot['params']
        if dot['is_recess']:
            r_feature = params.get('bowl_radius', 0.9)
        else:
            r_feature = params.get('base_diameter', 1.5) / 2.0
        half = math.degrees((r_feature + 0.2) / radius)
        out.append((dot['y'] + height / 2.0, math.degrees(dot['theta']) % 360.0, half))
    return out


def seam_in_a_dot(z: float, theta: float, windows: list[tuple[float, float, float]]) -> bool:
    return any(abs(z - wz) <= 1.2 and angular_error_deg(theta, wt) <= half for wz, wt, half in windows)


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--no-slice', action='store_true', help='build the STLs only')
    parser.add_argument('--layouts', default='visual15,tactile14')
    parser.add_argument('--channels', default=','.join(CHANNELS), help='which CHANNELS entries to build')
    parser.add_argument('--no-rear', action='store_true', help='skip the rotated "rear" variants (D-14 evidence)')
    parser.add_argument(
        '--out',
        default=str(OUT),
        help='output directory (a fresh one for a rerun: STLs and G-code are reused if present)',
    )
    args = parser.parse_args()
    OUT = Path(args.out)
    OUT.mkdir(parents=True, exist_ok=True)
    channels = {name: CHANNELS[name] for name in args.channels.split(',')}

    rows = []
    manifest = {}
    for layout in args.layouts.split(','):
        settings = settings_for(layout)
        for plate_type in ('positive', 'negative'):
            spec = spec_for(layout, plate_type)
            radius = spec['cylinder']['radius']
            windows = dot_windows(spec)
            for name, channel in channels.items():
                placement = channel_placement(layout, plate_type, settings, channel)
                theta_c = placement['theta'] if channel else None
                # The spec is the source of truth for where the groove goes; this
                # script only mirrors it. Refuse to measure a groove the app
                # would not cut there.
                emitted = spec['cylinder'].get('seam_channel')
                if channel and name == 'v10' and emitted is not None and abs(emitted['theta'] - theta_c) > 1e-9:
                    raise SystemExit(
                        f'{layout} {plate_type}: spike places the groove at {math.degrees(theta_c):.3f} deg, '
                        f'the spec at {math.degrees(emitted["theta"]):.3f} deg - mirror the spec first'
                    )
                if channel and not placement['fits']:
                    print(
                        f'[skip] {layout} {plate_type} {name}: free {placement["free_mm"]:.2f} < need {placement["need_mm"]:.2f}'
                    )
                    continue
                # D-T8: the tactile embossing plate's groove is the spec's own
                # path round the raised arrows. Only the shipped groove (v10)
                # has one; any other profile would run under the arrows.
                has_path = emitted is not None and 'path' in emitted
                if channel and has_path and name != 'v10':
                    print(f'[skip] {layout} {plate_type} {name}: only the shipped groove steps round the arrows')
                    continue
                detour = emitted if channel and has_path else None
                stem = f'{layout}_{plate_type}_{name}'
                stl = OUT / f'{stem}.stl'
                if not stl.exists():
                    print(f'[build] {stem}')
                    mesh = build_cylinder(spec, channel, theta_c, detour)
                    mesh.export(stl)
                    if channel and not args.no_rear:
                        rotate_to_face_rear(mesh, theta_c).export(OUT / f'{stem}_rear.stl')
                manifest[stem] = {
                    'layout': layout,
                    'plate_type': plate_type,
                    'channel': channel,
                    'placement': {k: (round(v, 4) if isinstance(v, float) else v) for k, v in placement.items()},
                }
                if args.no_slice:
                    continue
                variants = [('aligned', stl, theta_c)]
                if channel and not args.no_rear:
                    variants.append(('rear', OUT / f'{stem}_rear.stl', math.pi / 2.0))
                for seam_mode, model, target in variants:
                    gcode = OUT / f'{model.stem}_{seam_mode}.gcode'
                    if not gcode.exists():
                        print(f'[slice] {model.name} {seam_mode}')
                        slice_stl(model, seam_mode, gcode)
                    seams = outer_wall_seams(gcode, radius)
                    layers = len(seams)
                    # Every later outer-wall path start on a layer is a path break
                    # (one per dot bump), reported beside the seams, never mixed in.
                    path_breaks = len(outer_wall_seams(gcode, radius, first_per_layer=False)) - layers
                    # The rear variant is the whole part turned: the groove and
                    # the dot windows are in the unturned frame.
                    shift = 0.0 if seam_mode == 'aligned' else math.degrees(math.pi / 2.0 - theta_c)
                    if channel:
                        tol = math.degrees((channel['width'] / 2.0 + SEAM_TOLERANCE_MM) / radius)
                        groove = groove_angle_at(detour, theta_c, spec['cylinder']['height'])
                        in_channel = sum(angular_error_deg(t, groove(z) + shift) <= tol for z, t in seams)
                    else:
                        in_channel = 0
                    in_dot = sum(seam_in_a_dot(z, (t - shift) % 360.0, windows) for z, t in seams)
                    spread = sorted(t for _, t in seams)
                    rows.append(
                        {
                            'stem': stem,
                            'mode': seam_mode,
                            'layers': layers,
                            'path_breaks': path_breaks,
                            'pct_in_channel': round(100.0 * in_channel / layers, 1) if layers else None,
                            'pct_in_dot': round(100.0 * in_dot / layers, 1) if layers else None,
                            'theta_target_deg': round(math.degrees(target), 2) if target is not None else None,
                            'theta_median_deg': round(spread[len(spread) // 2], 2) if spread else None,
                            'theta_min_deg': round(spread[0], 2) if spread else None,
                            'theta_max_deg': round(spread[-1], 2) if spread else None,
                        }
                    )
                    print(
                        f'  {stem} {seam_mode}: layers {layers}, in channel {rows[-1]["pct_in_channel"]}%, in a dot {rows[-1]["pct_in_dot"]}%'
                    )

    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if args.no_slice:
        return
    lines = [
        '# Seam-channel slicing spike (Phase A0)',
        '',
        'PrusaSlicer console, built-in defaults with a 0.4 mm nozzle, 0.45 mm walls, 3 perimeters, 0.2 mm layers.',
        'One seam per layer: the start of the outer wall\'s FIRST external-perimeter path. "in channel" = that start',
        f'within half the channel width + {SEAM_TOLERANCE_MM} mm of arc of the channel angle (on a tactile embossing plate, the',
        'angle of the groove\'s path round the arrows at that layer\'s height, D-T8); "in a dot" = inside a dot or',
        'bowl footprint (+0.2 mm) at that height. "path breaks" = later outer-wall path starts on the same layers (the',
        'slicer prints each dot bump as its own path; they are not seam choices). Acceptance (plan A0): >= 95 % in',
        'channel in aligned mode on both plates.',
        '',
        '| model | seam mode | layers | in channel % | in a dot % | path breaks | target deg | median deg | min | max |',
        '|---|---|---|---|---|---|---|---|---|---|',
    ]
    for r in rows:
        lines.append(
            f'| {r["stem"]} | {r["mode"]} | {r["layers"]} | {r["pct_in_channel"]} | {r["pct_in_dot"]} | {r["path_breaks"]} | '
            f'{r["theta_target_deg"]} | {r["theta_median_deg"]} | {r["theta_min_deg"]} | {r["theta_max_deg"]} |'
        )
    lines += ['', '## Channel placement per model', '', '```json', json.dumps(manifest, indent=2), '```']
    (OUT / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[ok] wrote {OUT / "REPORT.md"}')


if __name__ == '__main__':
    main()
