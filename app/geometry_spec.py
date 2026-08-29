"""
Geometry specification extraction for client-side CSG.

This module extracts geometry specifications (positions, dimensions) from
braille layouts without performing boolean operations, for use by client-side
CSG workers.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

from app.geometry import gears, interpoint, version2

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# TACTILE INDICATOR CONSTANTS
# -----------------------------------------------------------------------------
# Ported verbatim from the OpenSCAD version so both generators produce the same
# arrow; see OpenSCAD/Braille_Cylinder_STL_Generator.scad "TACTILE INDICATOR
# CONSTANTS" and docs/specifications/RECESS_INDICATOR_SPECIFICATIONS.md.

# Clear zone required either side of the indicator, on top of its own width,
# before the seam gap is considered too tight (2 mm dot zone per neighbouring
# cell plus 1 mm of margin).
TACTILE_MIN_GAP_MARGIN = 5.0

# Radial thickness of the working prism the arrow outline is extruded into. Must
# exceed raise + recess depth + base embed so the prism always straddles the
# shell surface; the shell band intersection is what sets the actual depth.
TACTILE_PRISM_SPAN = 6.0

# How far the raised arrow's base sinks below the shell surface, so the union
# with the shell is a solid overlap rather than a coplanar touch.
TACTILE_BASE_EMBED = 0.2

# How far the recess cutter projects past the shell surface, so the cut opening
# never leaves coplanar faces behind.
TACTILE_RECESS_OVERCUT = 1.0

# The grid is centred on angle 0, so the middle of the seam gap — the arc between
# the last and first cell measured the long way round — is always exactly 180°.
# That is also the fixed point of the counter plate's angle-negating mirror, so
# the arrow and its recess line up by construction.
TACTILE_SEAM_THETA = math.pi


# -----------------------------------------------------------------------------
# DOUBLE-SIDED (INTERPOINT) BETA
# -----------------------------------------------------------------------------
# Off by default. When on, the two cylinders stop being "content plate + universal
# counter plate" and become a matched pair: Cylinder A (positive) carries the card
# FRONT's raised dots plus a recess for every BACK dot, Cylinder B (negative)
# carries the BACK's raised dots plus one recess per FRONT dot — no universal
# grid. The back grid is the front grid mirrored and stepped diagonally by the
# interpoint offset; see app/geometry/interpoint.py for that math and the
# research behind the numbers.


class _CylinderLayout(NamedTuple):
    """The grid numbers a dot walk needs, gathered once so helpers stay short."""

    settings: Any
    tactile_on: bool
    height: float
    radius: float
    first_row_center_y: float
    start_angle: float
    cell_spacing_angle: float
    dot_col_angle_offsets: list[float]
    braille_to_dots_func: Callable[[str], list[int]]


def extract_card_geometry_spec(
    lines: list[str],
    grade: str,
    settings: Any,
    original_lines: list[str] | None = None,
    plate_type: str = 'positive',
    braille_to_dots_func: Callable[[str], list[int]] | None = None,
) -> dict[str, Any]:
    """
    Extract geometry specification for a braille card without performing CSG.

    Returns a dict with:
    - plate: dimensions and position of base plate
    - dots: list of dot specifications with positions and parameters
    - markers: list of marker specifications (triangles, rectangles, characters)
    """
    if braille_to_dots_func is None:
        raise ValueError('braille_to_dots_func is required')

    spec = {
        'shape_type': 'card',
        'plate_type': plate_type,
        'plate': {
            'width': settings.card_width,
            'height': settings.card_height,
            'thickness': settings.card_thickness,
            'center_x': settings.card_width / 2,
            'center_y': settings.card_height / 2,
            'center_z': settings.card_thickness / 2,
        },
        'dots': [],
        'markers': [],
    }

    # Counts recesses declined for having no depth, so the omission is reported
    # once per request rather than silently or once per dot.
    zero_depth_recesses = 0

    # Dot positioning constants
    dot_col_offsets = [-settings.dot_spacing / 2, settings.dot_spacing / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # For negative plates (counter plates), generate all dots for all cells
    if plate_type == 'negative':
        for row_num in range(settings.grid_rows):
            y_pos = (
                settings.card_height
                - settings.top_margin
                - (row_num * settings.line_spacing)
                + settings.braille_y_adjust
            )

            x_pos_first = settings.left_margin + settings.braille_x_adjust
            x_pos_last = (
                settings.left_margin + ((settings.grid_columns - 1) * settings.cell_spacing) + settings.braille_x_adjust
            )

            # Square (rectangle) marker at column 0, gated by the Indicator Letters toggle.
            # Universal counter plates ALWAYS use rectangle markers here
            # (never character indicators) - this matches backend.py behavior
            # in create_universal_counter_plate_2d() which uses create_line_marker_polygon()
            if getattr(settings, 'indicator_shapes', 1):
                spec['markers'].append(
                    {
                        'type': 'rect',
                        'x': x_pos_first + settings.dot_spacing / 2,
                        'y': y_pos,
                        'z': settings.card_thickness,
                        'width': settings.dot_spacing,
                        'height': 2 * settings.dot_spacing,
                        'depth': 0.5,
                    }
                )

            # Triangle alignment marker at last column (grid_columns - 1).
            # Always created; the alignment triangles have no user-facing toggle.
            spec['markers'].append(
                {
                    'type': 'triangle',
                    'x': x_pos_last,
                    'y': y_pos,
                    'z': settings.card_thickness,
                    'size': settings.dot_spacing,
                    'depth': 0.6,
                }
            )

            # Add all dots for all columns
            for col_num in range(settings.grid_columns):
                x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust

                # All 6 dots per cell
                for dot_idx in range(6):
                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_x = x_pos + dot_col_offsets[col_off_idx]
                    dot_y = y_pos + dot_row_offsets[row_off_idx]

                    # Choose recess shape based on settings
                    # recess_shape is an integer: 0=hemisphere, 1=bowl, 2=cone
                    recess_shape_int = int(getattr(settings, 'recess_shape', 1))
                    recess_shape_map = {0: 'hemisphere', 1: 'bowl', 2: 'cone'}
                    recess_shape = recess_shape_map.get(recess_shape_int, 'bowl')

                    dot_spec = _create_dot_spec(dot_x, dot_y, settings, recess_shape, plate_type)
                    if dot_spec is None:
                        zero_depth_recesses += 1
                    else:
                        spec['dots'].append(dot_spec)

    else:
        # Positive plate: add row indicators for ALL rows (including empty rows),
        # and add dots only for rows that have braille characters.
        # This matches the backend.py behavior in create_positive_plate_mesh().
        for row_num in range(settings.grid_rows):
            # Get line content if available
            line = lines[row_num] if row_num < len(lines) else ''

            y_pos = (
                settings.card_height
                - settings.top_margin
                - (row_num * settings.line_spacing)
                + settings.braille_y_adjust
            )

            # Add markers for ALL rows. The indicator letter (column 0) is gated by the
            # Indicator Letters toggle; the triangle (last column) is always created.
            x_pos_first = settings.left_margin + settings.braille_x_adjust
            x_pos_last = (
                settings.left_margin + ((settings.grid_columns - 1) * settings.cell_spacing) + settings.braille_x_adjust
            )

            if getattr(settings, 'indicator_shapes', 1):
                # Character or rectangle indicator at first column (column 0)
                if original_lines and row_num < len(original_lines):
                    orig = (original_lines[row_num] or '').strip()
                    indicator_char = orig[0] if orig else ''
                    if indicator_char and (indicator_char.isalpha() or indicator_char.isdigit()):
                        spec['markers'].append(
                            {
                                'type': 'character',
                                'char': indicator_char,
                                'x': x_pos_first,
                                'y': y_pos,
                                'z': settings.card_thickness,
                                'size': settings.dot_spacing * 1.5,
                                'depth': 1.0,
                            }
                        )
                    else:
                        spec['markers'].append(
                            {
                                'type': 'rect',
                                'x': x_pos_first + settings.dot_spacing / 2,
                                'y': y_pos,
                                'z': settings.card_thickness,
                                'width': settings.dot_spacing,
                                'height': 2 * settings.dot_spacing,
                                'depth': 0.5,
                            }
                        )
                else:
                    spec['markers'].append(
                        {
                            'type': 'rect',
                            'x': x_pos_first + settings.dot_spacing / 2,
                            'y': y_pos,
                            'z': settings.card_thickness,
                            'width': settings.dot_spacing,
                            'height': 2 * settings.dot_spacing,
                            'depth': 0.5,
                        }
                    )

            # Triangle alignment marker at last column (grid_columns - 1).
            # Always created; the alignment triangles have no user-facing toggle.
            spec['markers'].append(
                {
                    'type': 'triangle',
                    'x': x_pos_last,
                    'y': y_pos,
                    'z': settings.card_thickness,
                    'size': settings.dot_spacing,
                    'depth': 0.6,
                }
            )

            # Only process braille dots if the line has content
            if not line:
                continue

            # Process each character in the line
            chars = list(line)
            for col_num, char in enumerate(chars):
                if col_num >= settings.grid_columns:
                    break

                x_pos = settings.left_margin + (col_num * settings.cell_spacing) + settings.braille_x_adjust

                # Get dots for this character
                dots = braille_to_dots_func(char)

                # braille_to_dots returns a 6-length list of 0/1 indicators.
                for dot_idx, dot_val in enumerate(dots):
                    if dot_val != 1:
                        continue
                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_x = x_pos + dot_col_offsets[col_off_idx]
                    dot_y = y_pos + dot_row_offsets[row_off_idx]

                    dot_spec = _create_dot_spec(dot_x, dot_y, settings, 'standard', plate_type)
                    spec['dots'].append(dot_spec)

    if zero_depth_recesses:
        logger.warning(
            f'A recess depth of 0 mm was requested, so {zero_depth_recesses} counter recess(es) '
            'were not cut. Nothing is carved at that depth; set a positive depth if you wanted bowls.'
        )

    return spec


def _create_dot_spec(
    x: float, y: float, settings: Any, shape_type: str = 'standard', plate_type: str = 'positive'
) -> dict[str, Any] | None:
    """Create a dot specification dict, or None when the dot has no volume to cut."""
    z = settings.card_thickness

    if shape_type == 'hemisphere':
        # Hemisphere for counter plates
        # Use hemi_counter_dot_base_diameter to match CardSettings
        try:
            hemi_base = float(
                getattr(settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.6))
            )
        except Exception:
            hemi_base = 1.6
        radius = hemi_base / 2
        return {
            'type': 'rounded',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': 0,
                'top_radius': 0,
                'base_height': 0,
                'dome_height': radius,
                'dome_radius': radius,
            },
        }
    elif shape_type == 'bowl':
        # Bowl (spherical cap) for counter plates
        # Use bowl_counter_dot_base_diameter and counter_dot_depth to match CardSettings
        try:
            bowl_base = float(
                getattr(settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.8))
            )
        except Exception:
            bowl_base = 1.8
        radius = bowl_base / 2
        depth = float(getattr(settings, 'counter_dot_depth', 0.8))
        # A zero-depth bowl is not a shallow bowl, it is no bowl: the spherical
        # cap has no volume and its sphere radius (a^2 + h^2) / 2h is undefined.
        # Cut nothing, and let the caller count the omission.
        if depth <= 0:
            return None
        return {
            'type': 'rounded',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': 0,
                'top_radius': 0,
                'base_height': 0,
                'dome_height': depth,
                'dome_radius': (radius * radius + depth * depth) / (2.0 * depth),
            },
        }
    elif shape_type == 'cone':
        # Cone frustum for counter plates
        # Use cone_counter_dot parameters to match CardSettings and backend.py
        base_dia = float(
            getattr(settings, 'cone_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.6))
        )
        top_dia = float(getattr(settings, 'cone_counter_dot_flat_hat', 0.4))
        height = float(getattr(settings, 'cone_counter_dot_height', 0.8))
        return {
            'type': 'standard',
            'x': x,
            'y': y,
            'z': z,
            'params': {'base_radius': base_dia / 2, 'top_radius': top_dia / 2, 'height': height},
        }
    elif getattr(settings, 'use_rounded_dots', 0):
        # Rounded dots for positive plates
        base_dia = float(getattr(settings, 'rounded_dot_base_diameter', 2.0))
        dome_dia = float(getattr(settings, 'rounded_dot_dome_diameter', 1.5))
        base_h = float(getattr(settings, 'rounded_dot_base_height', 0.2))
        dome_h = float(getattr(settings, 'rounded_dot_dome_height', 0.6))
        top_radius = dome_dia / 2.0
        if dome_h > 0:
            R = (top_radius * top_radius + dome_h * dome_h) / (2.0 * dome_h)
        else:
            R = max(top_radius, 1.0)
        return {
            'type': 'rounded',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': base_dia / 2,
                'top_radius': dome_dia / 2,
                'base_height': base_h,
                'dome_height': dome_h,
                'dome_radius': R,
            },
        }
    else:
        # Standard cone frustum (default)
        return {
            'type': 'standard',
            'x': x,
            'y': y,
            'z': z,
            'params': {
                'base_radius': settings.emboss_dot_base_diameter / 2,
                'top_radius': settings.emboss_dot_flat_hat / 2,
                'height': settings.emboss_dot_height,
            },
        }


def extract_cylinder_geometry_spec(
    lines: list[str],
    grade: str,
    settings: Any,
    cylinder_params: dict[str, Any] | None = None,
    original_lines: list[str] | None = None,
    plate_type: str = 'positive',
    braille_to_dots_func: Callable[[str], list[int]] | None = None,
    back_lines: list[str] | None = None,
) -> dict[str, Any]:
    """
    Extract geometry specification for a braille cylinder without performing CSG.

    Returns a dict with:
    - cylinder: shell dimensions and cutout polygon
    - dots: list of dot specifications with 3D positions on cylinder surface
    - markers: list of marker specifications

    `back_lines` is the braille for the card's BACK face (the request's
    text.back_lines). It is read only in double-sided mode; single-sided mode
    ignores it entirely.
    """
    if braille_to_dots_func is None:
        raise ValueError('braille_to_dots_func is required')

    if cylinder_params is None:
        cylinder_params = {}

    # One reader for both spellings of each key, shared with app/validation.py's
    # gear gate so the two can never disagree about what an absent field means.
    diameter, height = gears.cylinder_dimensions(cylinder_params, settings.card_height)
    thickness = float(cylinder_params.get('wall_thickness', cylinder_params.get('thickness', 2.0)))
    polygonal_cutout_radius = float(cylinder_params.get('polygonal_cutout_radius_mm', 0))
    polygonal_cutout_sides = int(cylinder_params.get('polygonal_cutout_sides', 12) or 12)
    seam_offset = float(cylinder_params.get('seam_offset_deg', 355))

    logger.info(f'Cylinder seam_offset_deg received: {seam_offset} (rotates polygon cutout ONLY, not braille content)')

    radius = diameter / 2

    # Row indicator style. Tactile drops the marker columns entirely and puts one
    # raised arrow (emboss) / matching recess (counter) per row in the seam gap.
    tactile_on = str(getattr(settings, 'indicator_mode', 'visual')).lower() == 'tactile'

    # Double-sided (interpoint) BETA. Read the flag once: every double-sided
    # branch below tests this name, so with the toggle off the function runs the
    # same lines it ran before the feature existed. It is a 0/1 int like
    # indicator_shapes, not a bool.
    double_sided = int(getattr(settings, 'double_sided_enabled', 0)) == 1
    double_sided_warnings: list[str] = []
    if double_sided:
        if not tactile_on:
            # A double-sided pair has no marker columns to spare and no visual
            # side to read them on, so the row indicator style is locked to the
            # tactile seam arrows. app/validation.py hard-rejects this case on
            # the request route; this branch stays as defense-in-depth for
            # direct callers.
            indicator_mode = str(getattr(settings, 'indicator_mode', 'visual')).lower()
            # User-facing wording signed off by Brennen (2026-08-16); reword only with his sign-off.
            warning = (
                'Double-sided mode is a beta that locks the row indicator style to the tactile '
                f"seam arrows; '{indicator_mode}' was requested and 'tactile' was used instead."
            )
            double_sided_warnings.append(warning)
            logger.warning(warning)
            tactile_on = True
        double_sided_warnings.extend(_double_sided_crowding_warnings(settings, tactile_on))

    # Gear-integrated one-piece rollers BETA. Read once, exactly as the
    # double-sided flag above is: with the toggle off every gear line below is
    # skipped and the function runs as it did before the feature existed.
    gear_rollers = int(getattr(settings, 'gear_rollers_enabled', 0)) == 1
    gear_warnings: list[str] = []
    if gear_rollers and not gears.matches_reference_roller(diameter, height):
        # Unreachable from the request route - app/validation.py rejects this
        # outright - but direct callers (tests, the golden fixture generator)
        # bypass validation, and a gear spec for the wrong barrel silently
        # produces loose or swallowed gears. Same defense-in-depth as the
        # double-sided indicator_mode branch above.
        warning = gears.reference_roller_message(diameter, height)
        gear_warnings.append(warning)
        logger.warning(warning)

    # Embosser Version 2 (keyed gear pegs) PROTOTYPE. Read once, exactly as the
    # two betas above are: with Version 1 selected - absent, 1, '1', 1.0 or '' -
    # every Version 2 line below is skipped and the function emits precisely the
    # spec it emitted before the prototype existed, new keys included.
    embosser_v2 = int(getattr(settings, 'embosser_version', 1)) == 2
    v2_warnings: list[str] = []
    if embosser_v2 and not version2.matches_v2_barrel(diameter, height):
        # D-V15: the Version 2 size is a soft preset, not a requirement -
        # Brennen is still testing whether 30.1 is right - so this is a warning
        # even on the request route, unlike the gear size above, which is a
        # rejection because the vendored gears cannot move with the barrel.
        # Wording S-V5 is DRAFT. FLAGGED FOR BRENNEN.
        warning = version2.v2_size_message(diameter, height)
        v2_warnings.append(warning)
        logger.warning(warning)

    # Calculate grid layout parameters (needed for polygon alignment).
    # settings.grid_columns is the TOTAL column count: in visual mode the frontend
    # has already added the marker columns, in tactile mode it adds none.
    grid_width = (settings.grid_columns - 1) * settings.cell_spacing
    grid_angle = grid_width / radius
    start_angle = -grid_angle / 2
    cell_spacing_angle = settings.cell_spacing / radius
    dot_spacing_angle = settings.dot_spacing / radius

    # Compute polygon cutout alignment angle
    # Seam offset rotates ONLY the polygon cutout, NOT the braille content
    # This allows users to align polygon vertices independently of braille position
    seam_offset_rad = math.radians(seam_offset)
    if plate_type == 'negative':
        # Counter plate: rotate polygon CLOCKWISE (positive angle direction)
        cutout_align_theta = seam_offset_rad
    else:
        # Embossing plate: rotate polygon COUNTER-CLOCKWISE (negative angle direction)
        cutout_align_theta = -seam_offset_rad

    logger.info(f'Cylinder cutout_align_theta: {math.degrees(cutout_align_theta):.2f} degrees')

    # Compute polygon cutout points if specified, with rotation applied
    polygon_points = []
    if gear_rollers and polygonal_cutout_radius > 0:
        # Decision D-2: the barrel is forced solid while gear mode is on. A
        # one-piece roller has no through-path along its axis anyway - the gear
        # bores are blind pockets - so keeping the cutout would seal a cavity
        # nothing can reach or drain. Wording (S3) signed off by Brennen
        # 2026-08-24; reword only with his sign-off.
        warning = 'The polygonal cutout is not used while integrated gears are on.'
        gear_warnings.append(warning)
        logger.warning(warning)
    elif embosser_v2 and polygonal_cutout_radius > 0:
        # The Version 2 barrel is solid: its keyed cutout is the only hole, and
        # a polygonal one running the length of the axis would break into it.
        # Mirrors the gear rule above, and like it the barrel is forced solid
        # rather than the request refused, so a saved cutout radius cannot lock
        # a user out of the prototype. Wording S-V14 is DRAFT, new in this
        # phase. FLAGGED FOR BRENNEN.
        warning = 'The polygonal cutout is not used in Version 2.'
        v2_warnings.append(warning)
        logger.warning(warning)
    elif polygonal_cutout_radius > 0:
        circumscribed_radius = polygonal_cutout_radius / math.cos(math.pi / polygonal_cutout_sides)
        for i in range(polygonal_cutout_sides):
            base_angle = 2 * math.pi * i / polygonal_cutout_sides
            # Apply the cutout alignment rotation
            rotated_angle = base_angle + cutout_align_theta
            polygon_points.append(
                {
                    'x': circumscribed_radius * math.cos(rotated_angle),
                    'y': circumscribed_radius * math.sin(rotated_angle),
                }
            )
        # Log first 3 polygon points for debugging
        logger.info(f'Polygon points (first 3): {polygon_points[:3]}')

    spec: dict[str, Any] = {
        'shape_type': 'cylinder',
        'plate_type': plate_type,
        'indicator_mode': 'tactile' if tactile_on else 'visual',
        'cylinder': {
            'radius': radius,
            'height': height,
            'thickness': thickness,
            'polygon_points': polygon_points,
        },
        'dots': [],
        'markers': [],
        'warnings': [],
    }
    spec['warnings'].extend(double_sided_warnings)
    spec['warnings'].extend(gear_warnings)
    spec['warnings'].extend(v2_warnings)

    if embosser_v2:
        # 'solid' is emitted ONLY here, so a Version 1 spec carries no new key
        # at all. It has to be explicit: an empty polygon_points list does NOT
        # mean "solid" to the worker, which hollows the barrel by wall thickness
        # unless it is told otherwise - the lesson decision D-2 recorded when
        # gear mode sealed an undrainable cavity.
        spec['cylinder']['solid'] = True
        # Every number in the block comes from app/geometry/version2.py, and the
        # z ranges are computed from THIS cylinder's height rather than the
        # preset's, so an off-size barrel still gets a hole that meets in the
        # middle. A missing plate_type raises there rather than guessing a side,
        # exactly as the gear asset lookup does.
        v2_clearance = float(getattr(settings, 'v2_key_clearance_mm', version2.V2_KEY_CLEARANCE_DEFAULT_MM))
        spec['keyed_cutouts'] = version2.keyed_cutout_block(plate_type, height, v2_clearance)

    if gear_rollers:
        # The vendored asset already sits in the worker's frame (Phase 01 baked
        # the sample-to-program transform in), so the worker applies no
        # placement and no theta negation to it - see
        # static/assets/gears/gears_manifest.json. A missing plate_type raises
        # rather than guessing a side.
        spec['gears'] = {
            'asset': gears.GEAR_ASSET_BY_PLATE[plate_type],
            'weld_rings': gears.weld_rings(height),
        }

    # Counts recesses declined for having no depth, so the omission is reported
    # once per request rather than silently or once per dot.
    zero_depth_recesses = 0

    # Seam gap: the arc between the last and first cell centers, measured the long
    # way around through the seam, where the tactile indicator sits. Warn (do not
    # fail) when the gap can no longer hold the indicator plus a clear zone either
    # side of it, matching the OpenSCAD version's behavior.
    if tactile_on:
        tactile_width = float(getattr(settings, 'tactile_indicator_width', 4.0))
        seam_gap_mm = math.pi * diameter - grid_width
        if seam_gap_mm < tactile_width + TACTILE_MIN_GAP_MARGIN:
            warning = (
                f'Tactile indicator needs a seam gap of at least '
                f'{tactile_width + TACTILE_MIN_GAP_MARGIN:.1f} mm; this layout leaves '
                f'{seam_gap_mm:.1f} mm. Reduce the number of braille cells, increase the '
                f'cylinder diameter, or narrow the indicator.'
            )
            spec['warnings'].append(warning)
            logger.warning(warning)

    # Dot positioning with angular offsets for columns, linear for rows
    dot_col_angle_offsets = [-dot_spacing_angle / 2, dot_spacing_angle / 2]
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]

    # Calculate vertical centering
    braille_content_height = (settings.grid_rows - 1) * settings.line_spacing + 2 * settings.dot_spacing
    space_above = (height - braille_content_height) / 2.0
    first_row_center_y = height - space_above - settings.dot_spacing

    # Note: seam_offset only affects polygon cutout rotation (computed above)
    # Braille content positioning uses fixed angles (not affected by seam_offset)
    # The Version 2 keys are not rotated by it either. They are tied to the
    # tactile arrow column - gear A1's notch drops onto the nub in exactly one
    # orientation - so turning them with the seam would break the pairing.

    def apply_seam(angle: float) -> float:
        """Convert planar angle to cylinder theta (for embossing plate).

        Braille content is positioned independently of seam_offset.
        Content flows counter-clockwise when viewed from above.
        """
        return -angle

    def apply_seam_mirrored(angle: float) -> float:
        """Convert planar angle to cylinder theta with mirrored direction (for counter plate).

        Uses + instead of - to reverse the angular direction, making content flow
        clockwise instead of counter-clockwise when viewed from above.
        Braille content is positioned independently of seam_offset.
        """
        return angle

    layout = _CylinderLayout(
        settings=settings,
        tactile_on=tactile_on,
        height=height,
        radius=radius,
        first_row_center_y=first_row_center_y,
        start_angle=start_angle,
        cell_spacing_angle=cell_spacing_angle,
        dot_col_angle_offsets=dot_col_angle_offsets,
        braille_to_dots_func=braille_to_dots_func,
    )

    if plate_type == 'negative':
        # Counter plate: Mirror of embossing plate along vertical axis
        # Layout: triangle at col 0, rectangle placeholder at col 1, braille cells at cols 2+
        # Note: Counter plates use rectangle placeholders (not character indicators) at column 1
        # Uses mirrored angular direction so content flows CLOCKWISE instead of counter-clockwise
        for row_num in range(settings.grid_rows):
            y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
            y_local = y_pos - (height / 2.0)

            if tactile_on:
                # The recess the emboss plate's raised arrow nests into. It sits at
                # 180°, the fixed point of this plate's angle-negating mirror, so it
                # needs no mirroring of its own.
                spec['markers'].append(
                    _create_tactile_indicator_spec(y_local, radius, settings, is_recess=True, gear_rollers=gear_rollers)
                )

            # Add markers (same column positions as embossing, but mirrored direction)
            # Triangle marker at column 0 (first position, same as embossing).
            # Always created in visual mode; the alignment triangles have no
            # user-facing toggle. Tactile mode has no marker columns at all.
            # Use rotate_180=True for counter plate to properly align with embosser plate
            if not tactile_on:
                triangle_angle = apply_seam_mirrored(start_angle)
                marker_spec = _create_cylinder_marker_spec(
                    triangle_angle,
                    y_local,
                    radius,
                    settings,
                    'triangle',
                    original_lines,
                    row_num,
                    plate_type='negative',
                    rotate_180=True,
                )
                spec['markers'].append(marker_spec)

            if not tactile_on and getattr(settings, 'indicator_shapes', 1):
                # Rectangle (square) placeholder marker at column 1 (second position),
                # gated by the Indicator Letters toggle.
                # Counter plates ALWAYS use rectangle placeholders, not character indicators
                # This matches the Python backend behavior in cylinder.py which uses
                # create_cylinder_line_end_marker for this position
                char_col_angle = apply_seam_mirrored(start_angle + cell_spacing_angle)
                marker_spec = _create_cylinder_marker_spec(
                    char_col_angle,
                    y_local,
                    radius,
                    settings,
                    'rect',  # Always rectangle for counter plate (not character)
                    original_lines,
                    row_num,
                    plate_type='negative',
                )
                spec['markers'].append(marker_spec)

            # Generate all 6 dots for all TEXT cells (same layout as embossing)
            # Uses mirrored angular direction so dots flow clockwise
            # Double-sided mode replaces this universal grid with 1:1 paired
            # recesses, generated once after the row loop.
            if not double_sided:
                reserved = _reserved_marker_columns(settings, tactile_on)
                num_text_cols = settings.grid_columns - reserved
                for col_num in range(num_text_cols):
                    # Braille cells start after the reserved marker columns
                    actual_col = col_num + reserved
                    col_raw_angle = start_angle + (actual_col * cell_spacing_angle)

                    for dot_idx in range(6):
                        row_off_idx, col_off_idx = dot_positions[dot_idx]
                        # Use mirrored seam for clockwise direction
                        dot_angle = apply_seam_mirrored(col_raw_angle + dot_col_angle_offsets[col_off_idx])
                        dot_y = y_local + dot_row_offsets[row_off_idx]

                        # Transform to 3D cylindrical coordinates
                        dot_spec = _create_cylinder_dot_spec(dot_angle, dot_y, radius, settings, plate_type='negative')
                        if dot_spec is None:
                            zero_depth_recesses += 1
                        else:
                            spec['dots'].append(dot_spec)

        if double_sided:
            # Cylinder B in double-sided mode. The order mirrors Cylinder A's —
            # front features first, then back — so A's dot list and B's line up
            # index for index, each pair meeting at theta and -theta.
            for planar_angle, dot_y in _text_dot_placements(layout, lines):
                ds_recess = _create_ds_cylinder_dot_spec(
                    apply_seam_mirrored(planar_angle), dot_y, radius, settings, is_recess=True
                )
                if ds_recess is None:
                    zero_depth_recesses += 1
                else:
                    spec['dots'].append(ds_recess)
            for planar_angle, dot_y in _back_dot_placements(layout, back_lines):
                spec['dots'].append(
                    _create_ds_cylinder_dot_spec(
                        apply_seam_mirrored(planar_angle), dot_y, radius, settings, is_recess=False
                    )
                )

    else:
        # Positive plate: add row indicators for ALL rows (including empty rows),
        # and add dots only for rows with braille characters.
        # Layout matches Python backend: Triangle at column 0, Character at column 1
        for row_num in range(settings.grid_rows):
            # Get line content if available
            line = lines[row_num] if row_num < len(lines) else ''

            y_pos = first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
            y_local = y_pos - (height / 2.0)

            if tactile_on:
                # Raised alignment arrow in the seam gap, apex toward the cylinder
                # top so a blind user can feel which end is up.
                spec['markers'].append(
                    _create_tactile_indicator_spec(
                        y_local, radius, settings, is_recess=False, gear_rollers=gear_rollers
                    )
                )

            # Indicators (visual mode only — tactile has no marker columns):
            # - Triangle at column 0 (first position) - ALWAYS created (no user toggle)
            # - Character indicator (or rectangle fallback) at column 1 (second position),
            #   gated by the Indicator Letters toggle
            if not tactile_on:
                triangle_angle = apply_seam(start_angle)
                triangle_spec = _create_cylinder_marker_spec(
                    triangle_angle,
                    y_local,
                    radius,
                    settings,
                    'triangle',
                    original_lines,
                    row_num,
                    plate_type='positive',
                )
                spec['markers'].append(triangle_spec)

            if not tactile_on and getattr(settings, 'indicator_shapes', 1):
                # Character (or rectangle fallback) at column 1 (second position)
                char_col_angle = apply_seam(start_angle + cell_spacing_angle)
                if original_lines and row_num < len(original_lines):
                    orig = (original_lines[row_num] or '').strip()
                    first_char = orig[0] if orig else ''
                    logger.info(
                        f"Row {row_num}: original_line='{orig}', first_char='{first_char}', isalnum={first_char and (first_char.isalpha() or first_char.isdigit())}"
                    )
                    if first_char and (first_char.isalpha() or first_char.isdigit()):
                        char_spec = _create_cylinder_marker_spec(
                            char_col_angle,
                            y_local,
                            radius,
                            settings,
                            'character',
                            original_lines,
                            row_num,
                            char=first_char.upper(),
                            plate_type='positive',
                        )
                        logger.info(f"Row {row_num}: Created character marker for '{first_char.upper()}'")
                    else:
                        char_spec = _create_cylinder_marker_spec(
                            char_col_angle,
                            y_local,
                            radius,
                            settings,
                            'rect',
                            original_lines,
                            row_num,
                            plate_type='positive',
                        )
                        logger.info(f'Row {row_num}: Created rectangle marker (non-alphanumeric)')
                else:
                    char_spec = _create_cylinder_marker_spec(
                        char_col_angle,
                        y_local,
                        radius,
                        settings,
                        'rect',
                        original_lines,
                        row_num,
                        plate_type='positive',
                    )
                    logger.info(f'Row {row_num}: Created rectangle marker (no original_lines)')
                spec['markers'].append(char_spec)

            # Process braille characters (dots) only if the row has braille
            has_braille = any(0x2800 <= ord(c) <= 0x28FF for c in line) if line else False
            if not has_braille:
                continue

            # Braille content starts after the reserved marker columns (none in
            # tactile mode).
            reserved = _reserved_marker_columns(settings, tactile_on)
            max_cols = max(0, settings.grid_columns - reserved)
            chars = list(line.strip())[:max_cols]

            for col_num, braille_char in enumerate(chars):
                # Shift braille cells past the reserved marker columns
                actual_col = col_num + reserved
                col_raw_angle = start_angle + (actual_col * cell_spacing_angle)

                # Get dot pattern for this braille character
                dots = braille_to_dots_func(braille_char)

                for dot_idx, dot_val in enumerate(dots):
                    if dot_val != 1:
                        continue

                    row_off_idx, col_off_idx = dot_positions[dot_idx]
                    dot_angle = apply_seam(col_raw_angle + dot_col_angle_offsets[col_off_idx])
                    dot_y = y_local + dot_row_offsets[row_off_idx]

                    # Transform to 3D cylindrical coordinates
                    if double_sided:
                        dot_spec = _create_ds_cylinder_dot_spec(dot_angle, dot_y, radius, settings, is_recess=False)
                    else:
                        dot_spec = _create_cylinder_dot_spec(dot_angle, dot_y, radius, settings, plate_type='positive')
                    spec['dots'].append(dot_spec)

        if double_sided:
            # Cylinder A also carries a recess for every raised dot Cylinder B
            # will bring to the nip — one per ACTUAL back-text dot, never a
            # universal grid. Same mapping as A's own dots (apply_seam), so the
            # recess lands at -theta of B's dot: an exact pairing.
            for planar_angle, dot_y in _back_dot_placements(layout, back_lines):
                ds_recess = _create_ds_cylinder_dot_spec(
                    apply_seam(planar_angle), dot_y, radius, settings, is_recess=True
                )
                if ds_recess is None:
                    zero_depth_recesses += 1
                else:
                    spec['dots'].append(ds_recess)

    if zero_depth_recesses:
        zero_depth_note = (
            f'A recess depth of 0 mm was requested, so {zero_depth_recesses} counter recess(es) '
            'were not cut. Nothing is carved at that depth; set a positive depth if you wanted bowls.'
        )
        spec['warnings'].append(zero_depth_note)
        logger.warning(zero_depth_note)

    logger.info(
        f'Cylinder geometry spec ({spec["indicator_mode"]} indicators): '
        f'{len(spec["dots"])} dots, {len(spec["markers"])} markers'
    )
    return spec


def _reserved_marker_columns(settings: Any, tactile_on: bool) -> int:
    """
    Number of leading grid columns consumed by row markers.

    Tactile mode: 0 — the indicator lives in the seam gap, so every column is text.
    Visual mode: 2 with indicator letters on (triangle at col 0, letter at col 1),
    or 1 when off (the alignment triangle is always present).
    """
    if tactile_on:
        return 0
    return 2 if getattr(settings, 'indicator_shapes', 1) else 1


def _text_dot_placements(layout: _CylinderLayout, lines: list[str] | None) -> list[tuple[float, float]]:
    """
    Planar angle and height of every raised dot in `lines`.

    The same walk the embossing plate does inline — row by row, cell by cell,
    dot by dot, with the same column truncation — but it stops one step short of
    the seam mapping. That leaves the caller free to send each position to
    either cylinder: apply_seam() puts it on Cylinder A, apply_seam_mirrored()
    on Cylinder B, and the two land at theta and -theta, which is exactly the
    pairing app/geometry/interpoint.py expects.

    Double-sided mode only. Angles are planar (pre-seam) radians; heights are mm
    relative to the cylinder's mid-height.
    """
    settings = layout.settings
    dot_row_offsets = [settings.dot_spacing, 0, -settings.dot_spacing]
    dot_positions = [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1]]
    reserved = _reserved_marker_columns(settings, layout.tactile_on)
    max_cols = max(0, settings.grid_columns - reserved)

    placements: list[tuple[float, float]] = []
    for row_num in range(settings.grid_rows):
        line = lines[row_num] if lines and row_num < len(lines) else ''
        has_braille = any(0x2800 <= ord(c) <= 0x28FF for c in line) if line else False
        if not has_braille:
            continue

        y_pos = layout.first_row_center_y - (row_num * settings.line_spacing) + settings.braille_y_adjust
        y_local = y_pos - (layout.height / 2.0)

        for col_num, braille_char in enumerate(list(line.strip())[:max_cols]):
            col_raw_angle = layout.start_angle + ((col_num + reserved) * layout.cell_spacing_angle)
            for dot_idx, dot_val in enumerate(layout.braille_to_dots_func(braille_char)):
                if dot_val != 1:
                    continue
                row_off_idx, col_off_idx = dot_positions[dot_idx]
                placements.append(
                    (
                        col_raw_angle + layout.dot_col_angle_offsets[col_off_idx],
                        y_local + dot_row_offsets[row_off_idx],
                    )
                )
    return placements


def _back_dot_placements(layout: _CylinderLayout, back_lines: list[str] | None) -> list[tuple[float, float]]:
    """
    The same placements for the card's BACK face, moved onto the interpoint grid.

    A back-side feature is laid out in its own reading order, then seen from the
    front — the frame both cylinders share — it reads mirrored, and the diagonal
    interpoint step is added so a back dot never lands on a front one.
    `interpoint.back_grid_transform` does both, in the card frame, so the angle
    is converted to arc length on the way in (x = angle * radius) and back on
    the way out.

    Double-sided mode only.
    """
    settings = layout.settings
    offset_x = float(getattr(settings, 'interpoint_offset_x', interpoint.INTERPOINT_OFFSET_X_MM))
    # Naming bridge: the settings field is the card's y (up the cylinder axis);
    # interpoint.py calls that same axis z. Same number, two names.
    offset_z = float(getattr(settings, 'interpoint_offset_y', interpoint.INTERPOINT_OFFSET_Z_MM))

    placements: list[tuple[float, float]] = []
    for planar_angle, y_local in _text_dot_placements(layout, back_lines):
        x_back, z_back = interpoint.back_grid_transform(
            planar_angle * layout.radius,
            y_local,
            offset_x,
            offset_z,
            interpoint.BACK_GRID_DIRECTION,
        )
        placements.append((x_back / layout.radius, z_back))
    return placements


def _double_sided_crowding_warnings(settings: Any, tactile_on: bool) -> list[str]:
    """
    Warn when a dot and its neighbouring back-side recess leave too little material.

    In double-sided mode both faces' features share one cylinder surface, so the
    closest front-to-back centre distance minus the two radii is the printed
    ridge between them. Below interpoint.SAME_SURFACE_GAP_RELIABLE_MM a 0.4 mm
    nozzle widens or thins that ridge unpredictably; below
    SAME_SURFACE_GAP_FLOOR_MM it cannot lay it down at all.
    """
    dot_diameter = float(getattr(settings, 'ds_dot_base_diameter', interpoint.DS_DOT_BASE_DIAMETER_MM))
    bowl_diameter = float(getattr(settings, 'ds_bowl_base_diameter', interpoint.DS_BOWL_DIAMETER_MM))
    offset_x = float(getattr(settings, 'interpoint_offset_x', interpoint.INTERPOINT_OFFSET_X_MM))
    offset_z = float(getattr(settings, 'interpoint_offset_y', interpoint.INTERPOINT_OFFSET_Z_MM))
    columns = max(1, settings.grid_columns - _reserved_marker_columns(settings, tactile_on))

    gap = interpoint.same_surface_min_gap(
        dot_diameter,
        bowl_diameter,
        offset_x,
        offset_z,
        columns,
        settings.grid_rows,
        settings.dot_spacing,
        settings.cell_spacing,
        settings.line_spacing,
    )
    if gap >= interpoint.SAME_SURFACE_GAP_RELIABLE_MM:
        return []

    # User-facing wording signed off by Brennen (2026-08-16); reword only with his sign-off.
    if gap < interpoint.SAME_SURFACE_GAP_FLOOR_MM:
        severity = (
            f'less than the {interpoint.SAME_SURFACE_GAP_FLOOR_MM:.2f} mm a 0.4 mm nozzle can lay down, so the '
            f'ridge between them would not print'
        )
    else:
        severity = (
            f'less than the {interpoint.SAME_SURFACE_GAP_RELIABLE_MM:.2f} mm needed to print reliably, so the '
            f'ridge between them may come out thin or merged'
        )
    warning = (
        f'Double-sided crowding: a {dot_diameter:.2f} mm dot next to a {bowl_diameter:.2f} mm recess at the '
        f'{offset_x:.2f} / {offset_z:.2f} mm interpoint offset leaves {gap:.3f} mm of material between them — '
        f'{severity}. Reduce the double-sided dot or recess diameter, or check the interpoint offsets.'
    )
    logger.warning(warning)
    return [warning]


def _create_tactile_indicator_spec(
    y_local: float, radius: float, settings: Any, is_recess: bool, gear_rollers: bool
) -> dict[str, Any]:
    """
    Create one tactile row indicator spec at the seam-gap centre (180°).

    Port of the OpenSCAD `tactile_raised` / `tactile_recess_cut` modules. Both are
    the same construction: an isosceles arrow outline (symmetric around the
    cylinder, apex toward the top) extruded radially through the shell surface,
    then intersected with a band concentric with the shell. The band is what makes
    the raise and the recess depth radially uniform — a flat 4 mm prism on a
    15.4 mm radius would otherwise lose ~0.13 mm at its edges to the chord sagitta,
    which is large next to a 0.2 mm nesting margin.

    Args:
        y_local: Height position relative to cylinder center
        radius: Cylinder radius
        settings: CardSettings
        is_recess: True for the counter plate's recess (subtracted, grown by the
            clearance and extra depth), False for the emboss plate's raised arrow
            (unioned).
        gear_rollers: True when the gear beta is on, which grows the RAISED
            arrow's outline by GEAR_ARROW_WELD_MM (D-8a). Recess arrows are
            unaffected - their clearance growth already overlaps.
    """
    theta = TACTILE_SEAM_THETA
    width = float(getattr(settings, 'tactile_indicator_width', 4.0))
    length = float(getattr(settings, 'tactile_indicator_length', 10.0))
    raise_mm = float(getattr(settings, 'tactile_indicator_raise', 0.5))

    if is_recess:
        # Grown in the plane and radially so the arrow still enters the recess when
        # the two cylinders are slightly out of register.
        clearance = float(getattr(settings, 'tactile_recess_clearance', 0.2))
        extra_depth = float(getattr(settings, 'tactile_recess_extra_depth', 0.2))
        inner_radius = radius - raise_mm - extra_depth
        outer_radius = radius + TACTILE_RECESS_OVERCUT
        outline_delta = clearance
    else:
        clearance = 0.0
        extra_depth = 0.0
        inner_radius = radius - TACTILE_BASE_EMBED
        outer_radius = radius + raise_mm
        # Decision D-8a: gear mode promises a watertight one-piece roller, and
        # a 10 mm arrow on 10 mm line spacing touches its neighbour exactly -
        # a tangency float32 STL rounding turns into a pinch edge. 5 um makes
        # it a real overlap. Off, the outline is untouched, so today's exports
        # keep the exact tangency they ship with.
        outline_delta = gears.GEAR_ARROW_WELD_MM if gear_rollers else 0.0

    return {
        'type': 'cylinder_tactile_arrow',
        'x': radius * math.cos(theta),
        'y': y_local,
        'z': radius * math.sin(theta),
        'theta': theta,
        'radius': radius,
        'width': width,
        'length': length,
        'outline_delta': outline_delta,
        'inner_radius': inner_radius,
        'outer_radius': outer_radius,
        'prism_span': TACTILE_PRISM_SPAN,
        'is_recess': is_recess,
    }


def _create_cylinder_dot_spec(
    theta: float, y_local: float, radius: float, settings: Any, plate_type: str = 'positive'
) -> dict[str, Any] | None:
    """
    Create a dot spec with 3D position on cylinder surface.

    Args:
        theta: Angle around cylinder (radians)
        y_local: Height position relative to cylinder center (becomes Z in Three.js Y-up coords)
        radius: Cylinder radius
        settings: CardSettings
        plate_type: 'positive' or 'negative'
    """
    # Convert cylindrical to 3D Cartesian
    # Server code uses Z-up, Three.js uses Y-up, so we swap Y and Z
    x = radius * math.cos(theta)
    z = radius * math.sin(theta)  # This becomes Z in Three.js (which is depth)
    y = y_local  # Height becomes Y in Three.js

    dot_height = settings.active_dot_height

    if plate_type == 'negative':
        # Counter plate - use recess shape
        # recess_shape is an integer: 0=hemisphere, 1=bowl, 2=cone
        recess_shape = int(getattr(settings, 'recess_shape', 1))

        if recess_shape == 0:  # Hemisphere
            # Use hemisphere counter dot base diameter
            try:
                hemi_base = float(
                    getattr(
                        settings, 'hemi_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.6)
                    )
                )
            except Exception:
                hemi_base = 1.6
            recess_radius = hemi_base / 2
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': True,
                'params': {
                    'shape': 'hemisphere',
                    'recess_radius': recess_radius,
                },
            }
        elif recess_shape == 1:  # Bowl
            # Use bowl counter dot base diameter
            try:
                bowl_base = float(
                    getattr(
                        settings, 'bowl_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.8)
                    )
                )
            except Exception:
                bowl_base = 1.8
            bowl_radius = bowl_base / 2
            bowl_depth = float(getattr(settings, 'counter_dot_depth', 0.8))
            # See _create_dot_spec: depth 0 means no recess, not a default one.
            if bowl_depth <= 0:
                return None
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': True,
                'params': {
                    'shape': 'bowl',
                    'bowl_radius': bowl_radius,
                    'bowl_depth': bowl_depth,
                },
            }
        else:  # Cone (recess_shape == 2)
            # Use cone counter dot parameters matching CardSettings and cylinder.py
            base_dia = float(
                getattr(settings, 'cone_counter_dot_base_diameter', getattr(settings, 'counter_dot_base_diameter', 1.6))
            )
            top_dia = float(getattr(settings, 'cone_counter_dot_flat_hat', 0.4))
            cone_height = float(getattr(settings, 'cone_counter_dot_height', 0.8))
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': True,
                'params': {
                    'shape': 'cone',
                    'base_radius': base_dia / 2,
                    'top_radius': top_dia / 2,
                    'height': cone_height,
                },
            }
    else:
        # Positive plate - embossed dots
        if getattr(settings, 'use_rounded_dots', 0):
            base_dia = float(getattr(settings, 'rounded_dot_base_diameter', 2.0))
            dome_dia = float(getattr(settings, 'rounded_dot_dome_diameter', 1.5))
            base_h = float(getattr(settings, 'rounded_dot_base_height', 0.2))
            dome_h = float(getattr(settings, 'rounded_dot_dome_height', 0.6))
            top_radius = dome_dia / 2.0
            if dome_h > 0:
                R = (top_radius * top_radius + dome_h * dome_h) / (2.0 * dome_h)
            else:
                R = max(top_radius, 1.0)
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': False,
                'params': {
                    'shape': 'rounded',
                    'base_radius': base_dia / 2,
                    'top_radius': dome_dia / 2,
                    'base_height': base_h,
                    'dome_height': dome_h,
                    'dome_radius': R,
                },
            }
        else:
            # Standard cone frustum
            return {
                'type': 'cylinder_dot',
                'x': x,
                'y': y,
                'z': z,
                'theta': theta,
                'radius': radius,
                'is_recess': False,
                'params': {
                    'shape': 'standard',
                    'base_radius': settings.emboss_dot_base_diameter / 2,
                    'top_radius': settings.emboss_dot_flat_hat / 2,
                    'height': dot_height,
                },
            }


def _create_ds_cylinder_dot_spec(
    theta: float, y_local: float, radius: float, settings: Any, is_recess: bool
) -> dict[str, Any] | None:
    """
    Create one double-sided dot spec: a rounded raised dot or its paired bowl.

    Double-sided mode uses its own, smaller footprint (the ds_* settings) because
    a raised dot and a neighbouring back-side recess share one cylinder surface;
    single-sided mode is unaffected and keeps the shipped sizes. Both plates use
    this same footprint, so a dot on one cylinder always meets an identically
    sized bowl on the other.

    The emitted 'rounded' and 'bowl' shapes are the ones the CSG workers already
    build — double-sided mode changes the numbers, not the shape vocabulary.

    Args:
        theta: Angle around cylinder (radians), already seam-mapped for its plate
        y_local: Height position relative to cylinder center
        radius: Cylinder radius
        settings: CardSettings
        is_recess: True for the bowl that receives the opposing cylinder's dot,
            False for the raised dot itself.
    """
    x = radius * math.cos(theta)
    z = radius * math.sin(theta)

    if is_recess:
        bowl_diameter = float(getattr(settings, 'ds_bowl_base_diameter', interpoint.DS_BOWL_DIAMETER_MM))
        bowl_depth = float(getattr(settings, 'ds_bowl_depth', interpoint.DS_BOWL_DEPTH_MM))
        # See _create_dot_spec: depth 0 means no recess, not a default one.
        if bowl_depth <= 0:
            return None
        return {
            'type': 'cylinder_dot',
            'x': x,
            'y': y_local,
            'z': z,
            'theta': theta,
            'radius': radius,
            'is_recess': True,
            'params': {
                'shape': 'bowl',
                'bowl_radius': bowl_diameter / 2,
                'bowl_depth': bowl_depth,
            },
        }

    base_dia = float(getattr(settings, 'ds_dot_base_diameter', interpoint.DS_DOT_BASE_DIAMETER_MM))
    dome_dia = float(getattr(settings, 'ds_dot_dome_diameter', interpoint.DS_DOT_DOME_DIAMETER_MM))
    base_h = float(getattr(settings, 'ds_dot_base_height', interpoint.DS_DOT_BASE_HEIGHT_MM))
    dome_h = float(getattr(settings, 'ds_dot_dome_height', interpoint.DS_DOT_DOME_HEIGHT_MM))
    top_radius = dome_dia / 2.0
    if dome_h > 0:
        R = (top_radius * top_radius + dome_h * dome_h) / (2.0 * dome_h)
    else:
        R = max(top_radius, 1.0)
    return {
        'type': 'cylinder_dot',
        'x': x,
        'y': y_local,
        'z': z,
        'theta': theta,
        'radius': radius,
        'is_recess': False,
        'params': {
            'shape': 'rounded',
            'base_radius': base_dia / 2,
            'top_radius': top_radius,
            'base_height': base_h,
            'dome_height': dome_h,
            'dome_radius': R,
        },
    }


def _create_cylinder_marker_spec(
    theta: float,
    y_local: float,
    radius: float,
    settings: Any,
    marker_type: str,
    original_lines: list[str] | None = None,
    row_num: int = 0,
    char: str | None = None,
    plate_type: str = 'positive',
    rotate_180: bool = False,
) -> dict[str, Any]:
    """
    Create a marker spec with 3D position on cylinder surface.

    Note: Markers (triangles, characters, rectangles) are ALWAYS recessed
    (subtracted) on both positive and negative cylinder plates. The is_recess
    flag should always be True for markers - this differs from dots which
    are only recessed on negative (counter) plates.

    Args:
        theta: Angle around cylinder (radians)
        y_local: Height position relative to cylinder center
        radius: Cylinder radius
        settings: CardSettings
        marker_type: Type of marker ('triangle', 'character', 'rect')
        original_lines: Original text lines for character extraction
        row_num: Row number for character extraction
        char: Character for character markers
        plate_type: 'positive' or 'negative'
        rotate_180: If True, rotate triangle 180 degrees from center (for counter plate alignment)
    """
    # Convert cylindrical to 3D Cartesian (Y-up for Three.js)
    x = radius * math.cos(theta)
    z = radius * math.sin(theta)
    y = y_local
    # Markers are ALWAYS recessed (subtracted) regardless of plate type
    # This matches the local Python behavior in generate_cylinder_stl()
    # where markers are subtracted using mesh_difference()
    is_recess = True

    if marker_type == 'triangle':
        return {
            'type': 'cylinder_triangle',
            'x': x,
            'y': y,
            'z': z,
            'theta': theta,
            'radius': radius,
            'size': settings.dot_spacing,
            'depth': 0.6,
            'is_recess': is_recess,
            'rotate_180': rotate_180,
        }
    elif marker_type == 'character':
        return {
            'type': 'cylinder_character',
            'x': x,
            'y': y,
            'z': z,
            'theta': theta,
            'radius': radius,
            'char': char or 'A',
            'size': settings.dot_spacing * 1.5,
            'depth': 0.5,
            'is_recess': is_recess,
        }
    else:  # rect
        return {
            'type': 'cylinder_rect',
            'x': x,
            'y': y,
            'z': z,
            'theta': theta,
            'radius': radius,
            'width': settings.dot_spacing,
            'height': 2 * settings.dot_spacing,
            'depth': 0.5,
            'is_recess': is_recess,
        }
