"""
Input validation for braille STL generation.

This module provides validation functions for incoming requests,
ensuring security, correctness, and helpful error messages.
"""

from typing import Any

from app.geometry import interpoint
from app.utils import get_logger

# Configure logging
logger = get_logger(__name__)

# Validation constants
MAX_LINE_LENGTH = 50
MAX_LINES = 4
BRAILLE_UNICODE_START = 0x2800
BRAILLE_UNICODE_END = 0x28FF


class ValidationError(ValueError):
    """Custom exception for validation errors with structured details."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def validate_lines(lines: Any) -> bool:
    """
    Validate the lines input for security and correctness.

    Args:
        lines: Input lines to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails with details
    """
    if not isinstance(lines, list):
        raise ValidationError('Lines must be a list', {'type': type(lines).__name__})

    if len(lines) > MAX_LINES:
        raise ValidationError(
            f'Too many lines provided. Maximum is {MAX_LINES} lines.', {'provided': len(lines), 'max': MAX_LINES}
        )

    for i, line in enumerate(lines):
        if not isinstance(line, str):
            raise ValidationError(f'Line {i + 1} must be a string', {'line_number': i + 1, 'type': type(line).__name__})

        # Check length to prevent extremely long inputs
        if len(line) > MAX_LINE_LENGTH:
            raise ValidationError(
                f'Line {i + 1} is too long (max {MAX_LINE_LENGTH} characters)',
                {'line_number': i + 1, 'length': len(line), 'max': MAX_LINE_LENGTH},
            )

        # Basic sanitization - check for potentially harmful characters
        harmful_chars = ['<', '>', '&', '"', "'", '\x00']
        found_harmful = [char for char in harmful_chars if char in line]
        if found_harmful:
            raise ValidationError(
                f'Line {i + 1} contains invalid characters: {found_harmful}',
                {'line_number': i + 1, 'invalid_chars': found_harmful},
            )

    return True


def validate_braille_lines(lines: list[str], plate_type: str = 'positive') -> bool:
    """
    Validate that lines contain valid braille Unicode characters.

    Only validates non-empty lines for positive plates (counter plates generate all dots).

    Args:
        lines: List of text lines
        plate_type: 'positive' or 'negative'

    Returns:
        True if valid

    Raises:
        ValidationError: If invalid braille characters found
    """
    if plate_type != 'positive':
        return True  # Counter plates don't need braille validation

    errors = []

    for i, line in enumerate(lines):
        if line.strip():  # Only validate non-empty lines
            # Check each character in the line
            for j, char in enumerate(line):
                # Allow standard ASCII space characters which represent blank braille cells
                if char == ' ':
                    continue

                char_code = ord(char)
                if char_code < BRAILLE_UNICODE_START or char_code > BRAILLE_UNICODE_END:
                    errors.append(
                        {
                            'line': i + 1,
                            'position': j + 1,
                            'character': char,
                            'char_code': f'U+{char_code:04X}',
                            'expected': f'U+{BRAILLE_UNICODE_START:04X} to U+{BRAILLE_UNICODE_END:04X}',
                        }
                    )

    if errors:
        error_details = []
        for err in errors[:5]:  # Show first 5 errors to avoid spam
            error_details.append(
                f'Line {err["line"]}, position {err["position"]}: '
                f"'{err['character']}' ({err['char_code']}) is not a valid braille character"
            )

        if len(errors) > 5:
            error_details.append(f'... and {len(errors) - 5} more errors')

        raise ValidationError(
            'Invalid braille characters detected. Translation may have failed.\n'
            + '\n'.join(error_details)
            + '\n\nPlease ensure text is properly translated to braille before generating STL.',
            {'error_count': len(errors), 'errors': errors[:10]},  # Include up to 10 errors in details
        )

    return True


def validate_settings(settings_data: Any) -> bool:
    """
    Validate settings data for security and correctness.

    Args:
        settings_data: Settings dictionary from request

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(settings_data, dict):
        raise ValidationError('Settings must be a dictionary', {'type': type(settings_data).__name__})

    # Define allowed settings keys and their types/ranges
    allowed_settings = {
        'card_width': (float, 50, 200),
        'card_height': (float, 30, 150),
        'card_thickness': (float, 1, 10),
        'grid_columns': (int, 1, 20),
        'grid_rows': (int, 1, 200),
        'cell_spacing': (float, 2, 15),
        'line_spacing': (float, 5, 25),
        'dot_spacing': (float, 1, 5),
        'emboss_dot_base_diameter': (float, 0.5, 3),
        'emboss_dot_height': (float, 0.3, 2),
        'emboss_dot_flat_hat': (float, 0.1, 2),
        # Rounded dome
        'use_rounded_dots': (int, 0, 1),
        'rounded_dot_diameter': (float, 0.5, 3),
        'rounded_dot_height': (float, 0.2, 2),
        # New rounded dot with cone base params
        'rounded_dot_base_diameter': (float, 0.5, 3),
        'rounded_dot_cylinder_height': (float, 0.0, 2.0),
        'rounded_dot_base_height': (float, 0.0, 2.0),
        'rounded_dot_dome_height': (float, 0.1, 2.0),
        'rounded_dot_dome_diameter': (float, 0.5, 3.0),
        'braille_x_adjust': (float, -10, 10),
        'braille_y_adjust': (float, -10, 10),
        # Counter plate parameters
        'counter_plate_dot_size_offset': (float, 0, 2),
        'counter_dot_base_diameter': (float, 0.1, 5.0),
        'hemi_counter_dot_base_diameter': (float, 0.1, 5.0),
        'bowl_counter_dot_base_diameter': (float, 0.1, 5.0),
        'hemisphere_subdivisions': (int, 1, 3),
        'cone_segments': (int, 8, 32),
        'use_bowl_recess': (int, 0, 1),
        'recess_shape': (int, 0, 2),
        'cone_counter_dot_base_diameter': (float, 0.1, 5.0),
        'cone_counter_dot_height': (float, 0.0, 5.0),
        'cone_counter_dot_flat_hat': (float, 0.0, 5.0),
        'counter_dot_depth': (float, 0.0, 5.0),
        'indicator_shapes': (int, 0, 1),
        # Tactile indicator mode (cylinder only). Ranges mirror the OpenSCAD sliders.
        'tactile_indicator_width': (float, 2.0, 10.0),
        'tactile_indicator_length': (float, 2.0, 15.0),
        'tactile_indicator_raise': (float, 0.0, 2.0),
        'tactile_recess_clearance': (float, 0.0, 1.0),
        'tactile_recess_extra_depth': (float, 0.0, 1.0),
    }

    # indicator_mode is a string enum, so it cannot go through the numeric loop below.
    if 'indicator_mode' in settings_data:
        mode = settings_data['indicator_mode']
        if str(mode).strip().lower() not in ('visual', 'tactile'):
            raise ValidationError(
                "Setting 'indicator_mode' must be 'visual' or 'tactile'",
                {'key': 'indicator_mode', 'value': mode, 'valid_options': ['visual', 'tactile']},
            )

    for key, value in settings_data.items():
        if key not in allowed_settings:
            continue  # Ignore unknown settings (CardSettings will use defaults)

        expected_type, min_val, max_val = allowed_settings[key]

        # Type validation with better error messages
        try:
            if expected_type is int:  # Use 'is' for type comparison
                value = int(float(value))  # Allow "2.0" to become int 2
            else:
                value = float(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Setting '{key}' must be a number", {'key': key, 'value': value, 'expected_type': 'number'}
            ) from e

        # Range validation
        if not (min_val <= value <= max_val):
            raise ValidationError(
                f"Setting '{key}' must be between {min_val} and {max_val}",
                {'key': key, 'value': value, 'min': min_val, 'max': max_val},
            )

    validate_double_sided_settings(settings_data)

    return True


def _double_sided_number(settings_data: dict, flat_key: str, schema_name: str, default: float) -> float:
    """
    Read one numeric setting the way CardSettings will: absent, None, or ''
    fall back to the default. `schema_name` is the canonical grouped
    settings.schema.json spelling, quoted in error messages; `flat_key` is the
    flat CardSettings spelling the request actually carries.
    """
    value = settings_data.get(flat_key, default)
    if value is None or value == '':
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"Setting '{schema_name}' must be a number",
            {'key': flat_key, 'value': value, 'expected_type': 'number'},
        ) from e


def validate_double_sided_settings(settings_data: dict) -> bool:
    """
    Hard gates for the double-sided (interpoint) beta.

    Every check is skipped when double_sided.enabled is off, so single-sided
    requests are validated exactly as before the beta existed. This is the
    first RUNTIME enforcement of the double-sided ranges: the minimum/maximum
    values in settings.schema.json are documentation only.

    Four gates:
    1. The row indicator style must be tactile (the beta has no marker columns
       to spare and no visual side to read them on).
    2. interpoint offsets must stay inside [INTERPOINT_OFFSET_MIN_MM,
       INTERPOINT_OFFSET_MAX_MM] (1.15-1.35 mm).
    3. The six ds_* footprint values must stay inside their documented
       settings.schema.json ranges (the range literals below mirror the
       schema, the same way the allowed_settings table above mirrors it -
       change both in the same commit).
    4. The same-surface gap - material between a raised dot and the nearest
       back-side recess sharing one cylinder surface - must clear
       SAME_SURFACE_GAP_FLOOR_MM (0.34 mm, what a 0.4 mm nozzle can lay down).
       The marginal band up to SAME_SURFACE_GAP_RELIABLE_MM (0.50 mm) is NOT
       rejected here: geometry_spec.py returns it as a soft warning in the
       spec's warnings array and the UI shows it live; this function only logs.

    User-facing message wording signed off by Brennen (2026-08-16); reword
    only with his sign-off.

    Args:
        settings_data: Settings dictionary from the request (flat CardSettings
            key spelling).

    Returns:
        True if valid (or the beta is off)

    Raises:
        ValidationError: If a double-sided request fails a hard gate
    """
    enabled_raw = settings_data.get('double_sided_enabled', 0)
    if enabled_raw is None or enabled_raw == '':
        return True
    try:
        enabled = int(float(enabled_raw))
    except (TypeError, ValueError) as e:
        raise ValidationError(
            "Setting 'double_sided.enabled' must be 0 or 1",
            {'key': 'double_sided_enabled', 'value': enabled_raw},
        ) from e
    if enabled != 1:
        return True

    indicator_mode = str(settings_data.get('indicator_mode', 'visual')).strip().lower()
    if indicator_mode != 'tactile':
        raise ValidationError(
            'Double-sided mode is a beta that requires the tactile row indicator style: '
            "set the Row Indicator Style to 'Tactile seam arrow' (indicator_mode 'tactile') "
            f"or turn double-sided mode off. Received indicator_mode '{indicator_mode}'.",
            {'key': 'indicator_mode', 'value': indicator_mode, 'required': 'tactile'},
        )

    offsets: dict[str, float] = {}
    for flat_key, schema_name, default in (
        ('interpoint_offset_x', 'double_sided.interpoint_offset_x_mm', interpoint.INTERPOINT_OFFSET_X_MM),
        ('interpoint_offset_y', 'double_sided.interpoint_offset_y_mm', interpoint.INTERPOINT_OFFSET_Z_MM),
    ):
        value = _double_sided_number(settings_data, flat_key, schema_name, default)
        if not (interpoint.INTERPOINT_OFFSET_MIN_MM <= value <= interpoint.INTERPOINT_OFFSET_MAX_MM):
            raise ValidationError(
                f"Setting '{schema_name}' must be between {interpoint.INTERPOINT_OFFSET_MIN_MM} and "
                f'{interpoint.INTERPOINT_OFFSET_MAX_MM} mm; received {value}.',
                {
                    'key': flat_key,
                    'value': value,
                    'min': interpoint.INTERPOINT_OFFSET_MIN_MM,
                    'max': interpoint.INTERPOINT_OFFSET_MAX_MM,
                },
            )
        offsets[flat_key] = value

    footprints: dict[str, float] = {}
    for flat_key, schema_name, default, min_val, max_val in (
        ('ds_dot_base_diameter', 'double_sided.ds_dot_base_diameter_mm', interpoint.DS_DOT_BASE_DIAMETER_MM, 0.5, 3.0),
        ('ds_dot_base_height', 'double_sided.ds_dot_base_height_mm', interpoint.DS_DOT_BASE_HEIGHT_MM, 0.0, 2.0),
        ('ds_dot_dome_diameter', 'double_sided.ds_dot_dome_diameter_mm', interpoint.DS_DOT_DOME_DIAMETER_MM, 0.5, 3.0),
        ('ds_dot_dome_height', 'double_sided.ds_dot_dome_height_mm', interpoint.DS_DOT_DOME_HEIGHT_MM, 0.1, 2.0),
        ('ds_bowl_base_diameter', 'double_sided.ds_bowl_base_diameter_mm', interpoint.DS_BOWL_DIAMETER_MM, 0.5, 5.0),
        ('ds_bowl_depth', 'double_sided.ds_bowl_depth_mm', interpoint.DS_BOWL_DEPTH_MM, 0.0, 5.0),
    ):
        value = _double_sided_number(settings_data, flat_key, schema_name, default)
        if not (min_val <= value <= max_val):
            raise ValidationError(
                f"Setting '{schema_name}' must be between {min_val} and {max_val} mm; received {value}.",
                {'key': flat_key, 'value': value, 'min': min_val, 'max': max_val},
            )
        footprints[flat_key] = value
    dot_diameter = footprints['ds_dot_base_diameter']
    bowl_diameter = footprints['ds_bowl_base_diameter']
    # Grid defaults mirror app/models.py CardSettings; spacing defaults are the
    # canonical 2.5 / 6.5 / 10.0 already mirrored in interpoint.py. The tactile
    # lock above guarantees zero reserved marker columns, so grid_columns is the
    # dot-lattice width as-is (matches _double_sided_crowding_warnings in
    # app/geometry_spec.py, which computes the same gap for its soft warning).
    grid_columns = int(_double_sided_number(settings_data, 'grid_columns', 'grid_columns', 15))
    grid_rows = int(_double_sided_number(settings_data, 'grid_rows', 'grid_rows', 4))
    dot_spacing = _double_sided_number(settings_data, 'dot_spacing', 'spacing.dot_spacing_mm', interpoint.DOT_PITCH_MM)
    cell_spacing = _double_sided_number(
        settings_data, 'cell_spacing', 'spacing.cell_spacing_mm', interpoint.CELL_PITCH_MM
    )
    line_spacing = _double_sided_number(
        settings_data, 'line_spacing', 'spacing.line_spacing_mm', interpoint.LINE_PITCH_MM
    )

    same_surface_gap = interpoint.same_surface_min_gap(
        dot_diameter,
        bowl_diameter,
        offsets['interpoint_offset_x'],
        offsets['interpoint_offset_y'],
        grid_columns,
        grid_rows,
        dot_spacing,
        cell_spacing,
        line_spacing,
    )
    if same_surface_gap < interpoint.SAME_SURFACE_GAP_FLOOR_MM:
        raise ValidationError(
            f'Double-sided crowding: a {dot_diameter:.2f} mm dot next to a {bowl_diameter:.2f} mm recess at the '
            f'{offsets["interpoint_offset_x"]:.2f} / {offsets["interpoint_offset_y"]:.2f} mm interpoint offset '
            f'leaves {same_surface_gap:.3f} mm of material between them — less than the '
            f'{interpoint.SAME_SURFACE_GAP_FLOOR_MM:.2f} mm a 0.4 mm nozzle can lay down, so the ridge between '
            'them would not print. Reduce the double-sided dot or recess diameter, or check the interpoint offsets.',
            {
                'gap_mm': round(same_surface_gap, 3),
                'floor_mm': interpoint.SAME_SURFACE_GAP_FLOOR_MM,
                'dot_diameter_mm': dot_diameter,
                'bowl_diameter_mm': bowl_diameter,
            },
        )
    if same_surface_gap < interpoint.SAME_SURFACE_GAP_RELIABLE_MM:
        logger.warning(
            f'Double-sided same-surface gap {same_surface_gap:.3f} mm is below the reliable '
            f'{interpoint.SAME_SURFACE_GAP_RELIABLE_MM:.2f} mm; accepting — geometry_spec returns the soft warning.'
        )

    return True


def validate_shape_type(shape_type: str) -> str:
    """
    Validate and normalize shape_type parameter.

    Args:
        shape_type: Shape type string

    Returns:
        Normalized shape type

    Raises:
        ValidationError: If invalid
    """
    normalized = str(shape_type).lower().strip()
    if normalized not in ['card', 'cylinder']:
        raise ValidationError(
            f"Invalid shape_type: '{shape_type}'. Must be 'card' or 'cylinder'.",
            {'provided': shape_type, 'valid_options': ['card', 'cylinder']},
        )
    return normalized


def validate_plate_type(plate_type: str) -> str:
    """
    Validate and normalize plate_type parameter.

    Args:
        plate_type: Plate type string

    Returns:
        Normalized plate type

    Raises:
        ValidationError: If invalid
    """
    normalized = str(plate_type).lower().strip()
    if normalized not in ['positive', 'negative']:
        raise ValidationError(
            f"Invalid plate_type: '{plate_type}'. Must be 'positive' or 'negative'.",
            {'provided': plate_type, 'valid_options': ['positive', 'negative']},
        )
    return normalized


def validate_grade(grade: str) -> str:
    """
    Validate and normalize braille grade parameter.

    Args:
        grade: Grade string

    Returns:
        Normalized grade

    Raises:
        ValidationError: If invalid
    """
    normalized = str(grade).lower().strip()
    if normalized not in ['g1', 'g2']:
        raise ValidationError(
            f"Invalid grade: '{grade}'. Must be 'g1' or 'g2'.",
            {'provided': grade, 'valid_options': ['g1', 'g2']},
        )
    return normalized


def validate_request_has_content(lines: list[str], plate_type: str) -> bool:
    """
    Validate that positive plates have at least some text content.

    Args:
        lines: List of text lines
        plate_type: 'positive' or 'negative'

    Returns:
        True if valid

    Raises:
        ValidationError: If positive plate has no content
    """
    if plate_type == 'positive' and all(not line.strip() for line in lines):
        raise ValidationError(
            'Please enter text in at least one line',
            {'plate_type': plate_type, 'lines_provided': len(lines), 'non_empty': 0},
        )
    return True


def validate_original_lines(original_lines: Any) -> bool:
    """
    Validate optional original_lines parameter.

    Args:
        original_lines: Original text lines before braille conversion

    Returns:
        True if valid

    Raises:
        ValidationError: If validation fails
    """
    if original_lines is None:
        return True

    if not isinstance(original_lines, list):
        raise ValidationError('original_lines must be a list', {'type': type(original_lines).__name__})

    if len(original_lines) > MAX_LINES:
        raise ValidationError(
            f'Too many original_lines. Maximum is {MAX_LINES}.', {'provided': len(original_lines), 'max': MAX_LINES}
        )

    for i, line in enumerate(original_lines):
        if not isinstance(line, str):
            raise ValidationError(
                f'original_line {i + 1} must be a string', {'line_number': i + 1, 'type': type(line).__name__}
            )
        if len(line) > MAX_LINE_LENGTH * 2:  # More lenient for original text
            raise ValidationError(
                f'original_line {i + 1} is too long',
                {'line_number': i + 1, 'length': len(line), 'max': MAX_LINE_LENGTH * 2},
            )

    return True


def validate_line_lengths(
    lines: list[str],
    grid_columns: int,
    shape_type: str,
    indicator_shapes: int = 0,
    indicator_mode: str = 'visual',
) -> bool:
    """
    Validate that braille lines do not exceed available grid columns.

    SAFETY-CRITICAL: This function prevents silent truncation (S0 bug).
    Backend geometry extraction previously silently dropped characters
    exceeding grid_columns. This validation fails closed instead.

    Args:
        lines: List of braille text lines
        grid_columns: Total grid columns (including reserved columns)
        shape_type: 'card' or 'cylinder'
        indicator_shapes: 1 if indicators enabled, 0 otherwise
        indicator_mode: 'visual' (marker columns) or 'tactile' (no marker columns)

    Returns:
        True if all lines fit within available columns

    Raises:
        ValidationError: If any line exceeds available columns
    """
    if shape_type == 'cylinder':
        # Cylinders reserve marker columns (mirrors _reserved_marker_columns()
        # in app/geometry_spec.py and getReservedMarkerColumns() in the UI):
        # - tactile mode: 0 columns (the indicator lives in the seam gap)
        # - indicator letters ON: 2 columns (triangle at col 0, letter at col 1)
        # - indicator letters OFF: 1 column (the alignment triangle is always present)
        reserved = 0 if str(indicator_mode).lower() == 'tactile' else (2 if indicator_shapes else 1)
        available_columns = max(0, grid_columns - reserved)
    else:
        # Cards: all grid_columns are available for braille. Verified against
        # extract_card_geometry_spec(), which places braille cells at columns
        # 0..grid_columns-1 and draws the indicator/triangle markers at the
        # first/last column positions without shifting the text columns.
        available_columns = grid_columns

    errors = []

    for i, line in enumerate(lines):
        if not line:
            continue

        # Count actual characters (braille cells)
        line_length = len(line.strip()) if shape_type == 'cylinder' else len(line)

        if line_length > available_columns:
            errors.append(
                {
                    'line_number': i + 1,
                    'line_length': line_length,
                    'available_columns': available_columns,
                    'overflow': line_length - available_columns,
                }
            )

    if errors:
        error_messages = []
        for err in errors[:5]:  # Show first 5 errors
            error_messages.append(
                f'Line {err["line_number"]} contains {err["line_length"]} characters '
                f'but grid allows {err["available_columns"]}. '
                f'Overflow: {err["overflow"]} character(s).'
            )

        if len(errors) > 5:
            error_messages.append(f'... and {len(errors) - 5} more line(s) with overflow.')

        raise ValidationError(
            'Braille text exceeds available columns. Reduce text or increase grid columns.\n'
            + '\n'.join(error_messages),
            {
                'shape_type': shape_type,
                'grid_columns': grid_columns,
                'available_columns': available_columns,
                'errors': errors,
            },
        )

    return True
