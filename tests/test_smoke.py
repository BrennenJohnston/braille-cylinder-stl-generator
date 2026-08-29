"""
Smoke tests for the minimal backend (client-side generation architecture).

These tests verify that:
1. Basic endpoints are responsive
2. /geometry_spec works for all 4 combinations (card/cylinder × positive/negative)
3. Legacy server-side STL endpoints are deprecated (410 Gone)
"""

from __future__ import annotations

import pytest

from app.models import CardSettings
from app.utils import braille_to_dots


def _count_raised_dots(lines: list[str], max_cols: int | None = None) -> int:
    """Count raised dots implied by braille characters in lines."""
    total = 0
    for line in lines:
        for col, ch in enumerate(line or ''):
            if max_cols is not None and col >= max_cols:
                break
            dots = braille_to_dots(ch)
            total += sum(1 for d in dots if d == 1)
    return total


def test_health_endpoint(client):
    """Test the /health endpoint returns 200."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'status' in data


def test_liblouis_tables_endpoint(client):
    """Test the /liblouis/tables endpoint returns table list."""
    response = client.get('/liblouis/tables')
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert 'tables' in data
    assert len(data['tables']) > 0


def test_geometry_spec_card_positive(client):
    """Card + positive plate returns a geometry spec with expected dot/marker counts."""
    lines = ['⠁⠃', '', '', '']
    payload = {
        'lines': lines,
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        # Keep the grid small/deterministic for test stability
        'settings': {'grid_rows': 4, 'grid_columns': 4},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'card'
    assert data.get('plate_type') == 'positive'
    assert 'plate' in data and isinstance(data['plate'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    assert len(data['markers']) == settings.grid_rows * 2  # rect/character + triangle per row
    assert len(data['dots']) == _count_raised_dots(lines, max_cols=settings.grid_columns)


def test_geometry_spec_card_negative(client):
    """Card + negative plate returns a dense grid of recess dots (all cells)."""
    payload = {
        'lines': ['⠁⠃', '', '', ''],  # ignored for negative cards
        'plate_type': 'negative',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'card'
    assert data.get('plate_type') == 'negative'
    assert 'plate' in data and isinstance(data['plate'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    assert len(data['markers']) == settings.grid_rows * 2
    assert len(data['dots']) == settings.grid_rows * settings.grid_columns * 6


def test_geometry_spec_cylinder_positive(client):
    """Cylinder + positive plate returns cylinder spec and dot list."""
    lines = ['⠁⠃', '', '', '']
    payload = {
        'lines': lines,
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'cylinder'
    assert data.get('plate_type') == 'positive'
    assert 'cylinder' in data and isinstance(data['cylinder'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    reserved = 2 if settings.indicator_shapes else 1
    max_text_cols = settings.grid_columns - reserved
    assert len(data['markers']) == settings.grid_rows * 2
    assert len(data['dots']) == _count_raised_dots(lines, max_cols=max_text_cols)


def test_geometry_spec_cylinder_negative(client):
    """Cylinder + negative plate returns all recess dots for all text cells (no text required)."""
    payload = {
        'lines': ['⠁⠃', '', '', ''],  # ignored for negative cylinders (all cells generated)
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1},
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data and data.get('shape_type') == 'cylinder'
    assert data.get('plate_type') == 'negative'
    assert 'cylinder' in data and isinstance(data['cylinder'], dict)
    assert 'dots' in data and isinstance(data['dots'], list)
    assert 'markers' in data and isinstance(data['markers'], list)

    settings = CardSettings(**payload['settings'])
    reserved = 2 if settings.indicator_shapes else 1
    num_text_cols = settings.grid_columns - reserved
    assert len(data['markers']) == settings.grid_rows * 2
    assert len(data['dots']) == settings.grid_rows * num_text_cols * 6


def test_deprecated_endpoints_return_410(client):
    """Legacy server-side endpoints should remain present but return 410 Gone."""
    endpoints = [
        ('/generate_braille_stl', 'POST', {}),
        ('/generate_counter_plate_stl', 'POST', {}),
        ('/lookup_stl', 'GET', None),
        ('/debug/blob_upload', 'GET', None),
    ]

    for path, method, payload in endpoints:
        if method == 'POST':
            resp = client.post(path, json=payload, headers={'Content-Type': 'application/json'})
        else:
            resp = client.get(path)
        assert resp.status_code == 410, f'{path} expected 410, got {resp.status_code}'
        data = resp.get_json()
        assert data and data.get('status') == 'deprecated'


def test_validation_empty_input(client):
    """Empty braille input should still return a valid geometry spec (markers only)."""
    payload = {'lines': ['', '', '', ''], 'plate_type': 'positive', 'shape_type': 'card', 'grade': 'g1', 'settings': {}}

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    data = response.get_json()
    assert data and data.get('shape_type') == 'card'
    assert 'dots' in data and isinstance(data['dots'], list)


def test_validation_invalid_shape_type(client):
    """Test that invalid shape_type returns 400."""
    payload = {'lines': ['⠁'], 'plate_type': 'positive', 'shape_type': 'invalid', 'grade': 'g1', 'settings': {}}

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_validation_card_column_overflow(client):
    """
    SAFETY-CRITICAL: Test that card column overflow returns 400.

    This tests PR-2 fix for silent truncation (S0 bug).
    Previously, characters exceeding grid_columns were silently dropped
    at geometry_spec.py:211-212. Now they must fail with validation error.
    """
    # Create a braille line longer than grid_columns
    # 10 braille characters but only 4 columns allowed
    long_braille_line = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚'  # 10 characters
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},  # Only 4 columns allowed
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400, f'Expected 400 for column overflow, got {response.status_code}: {response.data}'
    data = response.get_json()
    assert 'error' in data
    # Error message should mention the overflow
    assert (
        'column' in data['error'].lower() or 'overflow' in data['error'].lower() or 'exceeds' in data['error'].lower()
    )


def test_validation_cylinder_column_overflow(client):
    """
    SAFETY-CRITICAL: Test that cylinder column overflow returns 400.

    This tests PR-2 fix for silent truncation (S0 bug).
    Previously, characters were silently truncated via [:max_cols] at
    geometry_spec.py:602. Now they must fail with validation error.
    """
    # Cylinders reserve 2 columns for indicators, so with grid_columns=4,
    # only 2 columns are available for text
    long_braille_line = '⠁⠃⠉⠙⠑'  # 5 characters, but only 2 available after indicator reservation
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'indicator_shapes': 1},  # 2 reserved for indicators
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400, (
        f'Expected 400 for cylinder overflow, got {response.status_code}: {response.data}'
    )
    data = response.get_json()
    assert 'error' in data


def test_validation_cylinder_no_indicators_overflow(client):
    """
    Test cylinder column overflow when indicator letters are disabled.

    With indicator letters disabled, only 1 column (the always-present alignment
    triangle) is reserved, so grid_columns - 1 cells are available for text.
    This test verifies the indicator_shapes=0 path.
    """
    # 10 braille characters but only 3 columns available (1 reserved for the triangle)
    long_braille_line = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚'  # 10 characters
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {
            'grid_rows': 4,
            'grid_columns': 4,
            'indicator_shapes': 0,
        },  # Indicator letters off: 3 of 4 columns available for text
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 400, f'Expected 400 for overflow, got {response.status_code}: {response.data}'
    data = response.get_json()
    assert 'error' in data


def test_validation_card_exact_fit_succeeds(client):
    """Test that card with exact column count succeeds (boundary test)."""
    # Exactly 4 braille characters with 4 columns = should succeed
    exact_fit_line = '⠁⠃⠉⠙'  # 4 characters
    payload = {
        'lines': [exact_fit_line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    assert response.status_code == 200, f'Expected 200 for exact fit, got {response.status_code}: {response.data}'
    data = response.get_json()
    assert data and data.get('shape_type') == 'card'


def test_validation_negative_plate_skips_column_check(client):
    """Test that negative plates skip column validation (they generate all dots)."""
    # Long braille line for a negative plate - should succeed because
    # negative plates ignore the text content
    long_braille_line = '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚'  # 10 characters
    payload = {
        'lines': [long_braille_line, '', '', ''],
        'plate_type': 'negative',  # Negative plate
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1},
    }

    response = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})

    # Negative plates should succeed regardless of line length
    # because they generate recesses for all cells, ignoring text
    assert response.status_code == 200, f'Expected 200 for negative plate, got {response.status_code}: {response.data}'


# =============================================================================
# Tactile Row Indicator Mode (cylinder only)
# =============================================================================
#
# Ported from the OpenSCAD version: instead of recessed markers in the first
# cells of each row, one arrow per row sits in the seam gap - raised on the
# embossing plate, recessed on the counter plate. See
# docs/specifications/RECESS_INDICATOR_SPECIFICATIONS.md.


TACTILE_CYLINDER_PARAMS = {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}


def _tactile_spec(client, plate_type: str, lines: list[str], **settings_overrides):
    settings = {'grid_rows': 4, 'grid_columns': 4, 'indicator_mode': 'tactile'}
    settings.update(settings_overrides)
    payload = {
        'lines': lines,
        'plate_type': plate_type,
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': settings,
        'cylinder_params': TACTILE_CYLINDER_PARAMS,
    }
    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    return resp.get_json()


def test_tactile_mode_drops_marker_columns_on_positive(client):
    """Tactile mode frees the marker columns: all grid_columns hold text."""
    lines = ['⠁⠃⠉⠙', '', '', '']  # 4 cells == grid_columns, which only fits with 0 reserved
    data = _tactile_spec(client, 'positive', lines)

    assert data['indicator_mode'] == 'tactile'
    # No triangle/letter markers - only one tactile arrow per row
    assert [m['type'] for m in data['markers']] == ['cylinder_tactile_arrow'] * 4
    # Every column carried text, so every raised dot is present
    assert len(data['dots']) == _count_raised_dots(lines)


def test_tactile_mode_drops_marker_columns_on_negative(client):
    """Counter plate in tactile mode recesses every cell and every arrow."""
    data = _tactile_spec(client, 'negative', ['', '', '', ''], recess_shape=1)

    settings = CardSettings(grid_rows=4, grid_columns=4, indicator_mode='tactile')
    assert [m['type'] for m in data['markers']] == ['cylinder_tactile_arrow'] * 4
    assert all(m['is_recess'] is True for m in data['markers'])
    # reserved == 0, so all 4 columns get recesses
    assert len(data['dots']) == settings.grid_rows * settings.grid_columns * 6


def test_tactile_arrow_is_raised_on_positive_and_recessed_on_negative(client):
    """The pair only nests if the emboss arrow is unioned and the counter cut."""
    positive = _tactile_spec(client, 'positive', ['⠁', '', '', ''])['markers'][0]
    negative = _tactile_spec(client, 'negative', ['', '', '', ''])['markers'][0]

    radius = TACTILE_CYLINDER_PARAMS['diameter'] / 2

    assert positive['is_recess'] is False
    assert positive['outer_radius'] == pytest.approx(radius + 0.5)  # tactile_indicator_raise
    assert positive['inner_radius'] == pytest.approx(radius - 0.2)  # TACTILE_BASE_EMBED
    assert positive['outline_delta'] == pytest.approx(0.0)

    assert negative['is_recess'] is True
    # Recess is grown radially by raise + extra depth, and in-plane by the clearance
    assert negative['inner_radius'] == pytest.approx(radius - 0.5 - 0.2)
    assert negative['outer_radius'] == pytest.approx(radius + 1.0)  # TACTILE_RECESS_OVERCUT
    assert negative['outline_delta'] == pytest.approx(0.2)  # tactile_recess_clearance


def test_tactile_arrow_sits_at_the_seam_gap_centre_on_both_plates(client):
    """
    180 degrees is the fixed point of the counter plate's angle-negating mirror,
    so the arrow and its recess line up without any extra bookkeeping.
    """
    import math

    positive = _tactile_spec(client, 'positive', ['⠁', '', '', ''])['markers']
    negative = _tactile_spec(client, 'negative', ['', '', '', ''])['markers']

    for marker in positive + negative:
        assert marker['theta'] == pytest.approx(math.pi)

    # One indicator per row, at the same row pitch the visual markers use
    assert [m['y'] for m in positive] == pytest.approx([m['y'] for m in negative])
    assert len({round(m['y'], 6) for m in positive}) == 4


def test_tactile_gap_warning_when_seam_gap_too_small(client):
    """
    Warn (do not fail) when the seam gap can no longer hold the indicator plus a
    clear zone either side, matching the OpenSCAD version.
    """
    # 14 cells at 6.5 mm on the default 30.75 mm cylinder leaves
    # 96.6 - 84.5 = 12.1 mm, comfortably over the 4 + 5 mm the arrow needs.
    # The UI recommends 13 for tactile mode; 14 is still a valid layout, which
    # is exactly what this case pins.
    roomy = {
        'lines': ['', '', '', ''],
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 14, 'cell_spacing': 6.5, 'indicator_mode': 'tactile'},
        'cylinder_params': {'diameter': 30.75, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }
    resp = client.post('/geometry_spec', json=roomy, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    assert resp.get_json()['warnings'] == []

    # 16 cells leaves 96.6 - 97.5 = -0.9 mm: no gap at all.
    payload = {
        'lines': ['', '', '', ''],
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 16, 'cell_spacing': 6.5, 'indicator_mode': 'tactile'},
        'cylinder_params': {'diameter': 30.75, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }
    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    warnings = resp.get_json()['warnings']
    assert any('seam gap' in w for w in warnings), warnings


def test_visual_mode_emits_no_tactile_arrows(client):
    """Default (visual) mode must be untouched by the tactile port."""
    payload = {
        'lines': ['⠁⠃', '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4},
        'cylinder_params': TACTILE_CYLINDER_PARAMS,
    }
    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()

    assert data['indicator_mode'] == 'visual'
    assert data['warnings'] == []
    assert not any(m['type'] == 'cylinder_tactile_arrow' for m in data['markers'])
    assert len(data['markers']) == 4 * 2  # triangle + letter/square per row


def test_tactile_mode_column_validation_allows_full_width(client):
    """
    A line filling every column is valid in tactile mode but overflows in visual
    mode, where marker columns are reserved.
    """
    line = '⠁⠃⠉⠙'  # exactly grid_columns
    base = {
        'lines': [line, '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'cylinder_params': TACTILE_CYLINDER_PARAMS,
    }

    tactile = client.post(
        '/geometry_spec',
        json={**base, 'settings': {'grid_rows': 4, 'grid_columns': 4, 'indicator_mode': 'tactile'}},
        headers={'Content-Type': 'application/json'},
    )
    assert tactile.status_code == 200, tactile.data

    visual = client.post(
        '/geometry_spec',
        json={**base, 'settings': {'grid_rows': 4, 'grid_columns': 4}},
        headers={'Content-Type': 'application/json'},
    )
    assert visual.status_code == 400, visual.data


def test_indicator_mode_rejects_unknown_value(client):
    """A typo must be rejected, not silently treated as tactile."""
    payload = {
        'lines': ['⠁', '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'indicator_mode': 'tactilee'},
        'cylinder_params': TACTILE_CYLINDER_PARAMS,
    }
    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 400, resp.data
    assert 'indicator_mode' in resp.get_json()['error']


def test_tactile_settings_defaults():
    """
    These five numbers are also written into both Card Thickness presets in
    public/index.html, so a change here has to be mirrored there.
    """
    settings = CardSettings()
    assert settings.indicator_mode == 'visual'
    assert settings.tactile_indicator_width == 4.0
    assert settings.tactile_indicator_length == 10.0
    assert settings.tactile_indicator_raise == 0.5
    assert settings.tactile_recess_clearance == 0.2
    assert settings.tactile_recess_extra_depth == 0.2


def test_schema_and_models_agree_on_indicator_fields():
    """
    settings.schema.json is the single source of truth for settings, so its
    defaults must match CardSettings. Drift between the two is the failure the
    cross-validation checklist in .cursorrules exists to catch.
    """
    import json
    from pathlib import Path

    schema_path = Path(__file__).resolve().parents[1] / 'settings.schema.json'
    indicators = json.loads(schema_path.read_text(encoding='utf-8'))['properties']['indicators']['properties']
    settings = CardSettings()

    assert indicators['indicator_mode']['enum'] == ['visual', 'tactile']
    assert indicators['indicator_mode']['default'] == settings.indicator_mode

    for field in (
        'tactile_indicator_width',
        'tactile_indicator_length',
        'tactile_indicator_raise',
        'tactile_recess_clearance',
        'tactile_recess_extra_depth',
    ):
        assert field in indicators, f'{field} missing from settings.schema.json'
        assert indicators[field]['default'] == getattr(settings, field), (
            f'{field} default disagrees between settings.schema.json and CardSettings'
        )


def test_schema_and_models_agree_on_embosser_version_fields():
    """
    The Version 2 fields, guarded the same way.

    settings.schema.json is loaded by nothing at runtime, so a wrong number in
    it fails no other check - this test is the only thing that notices. The
    clearance is compared against app/geometry/version2.py too, because that
    module is where the value actually lives.
    """
    import json
    from pathlib import Path

    from app.geometry import version2

    schema_path = Path(__file__).resolve().parents[1] / 'settings.schema.json'
    properties = json.loads(schema_path.read_text(encoding='utf-8'))['properties']
    settings = CardSettings()

    assert properties['embosser_version']['enum'] == [1, 2]
    assert properties['embosser_version']['default'] == settings.embosser_version == 1

    clearance = properties['version_2']['properties']['key_clearance_mm']
    assert clearance['default'] == settings.v2_key_clearance_mm == version2.V2_KEY_CLEARANCE_DEFAULT_MM
    assert clearance['minimum'] == version2.V2_KEY_CLEARANCE_MIN_MM
    assert clearance['maximum'] == version2.V2_KEY_CLEARANCE_MAX_MM


# =============================================================================
# PR-8: braille_to_dots() Strict Mode Tests (Defense-in-Depth)
# =============================================================================


def test_braille_to_dots_valid_character():
    """Test that valid braille characters return correct dot patterns."""
    # ⠁ (U+2801) = dot 1 only
    result = braille_to_dots('⠁')
    assert result == [1, 0, 0, 0, 0, 0], f'Expected [1,0,0,0,0,0] for ⠁, got {result}'

    # ⠓ (U+2813) = dots 1, 2, 5 (binary: 010011 = 1+2+16)
    result = braille_to_dots('⠓')
    assert result == [1, 1, 0, 0, 1, 0], f'Expected [1,1,0,0,1,0] for ⠓, got {result}'

    # ⠿ (U+283F) = all 6 dots (binary: 111111 = 63)
    result = braille_to_dots('⠿')
    assert result == [1, 1, 1, 1, 1, 1], f'Expected [1,1,1,1,1,1] for ⠿, got {result}'


def test_braille_to_dots_space_returns_empty():
    """Test that space character returns empty cell (valid blank braille)."""
    result = braille_to_dots(' ')
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for space, got {result}'


def test_braille_to_dots_empty_returns_empty():
    """Test that empty string returns empty cell."""
    result = braille_to_dots('')
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for empty string, got {result}'

    result = braille_to_dots(None)
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for None, got {result}'


def test_braille_to_dots_invalid_character_raises():
    """
    SAFETY-CRITICAL: Test that non-braille characters raise ValueError.

    This tests PR-8 defense-in-depth fix. Previously, non-braille characters
    silently returned empty dots [0,0,0,0,0,0], which could cause silent
    data loss if validation was bypassed. Now they must raise ValueError.
    """
    # ASCII letter should raise
    with pytest.raises(ValueError) as exc_info:
        braille_to_dots('X')
    assert 'Invalid braille character' in str(exc_info.value)
    assert 'U+0058' in str(exc_info.value)  # Unicode code point for 'X'

    # Number should raise
    with pytest.raises(ValueError) as exc_info:
        braille_to_dots('5')
    assert 'Invalid braille character' in str(exc_info.value)

    # Special character should raise
    with pytest.raises(ValueError) as exc_info:
        braille_to_dots('@')
    assert 'Invalid braille character' in str(exc_info.value)


def test_braille_to_dots_unicode_outside_braille_range_raises():
    """Test that Unicode characters outside braille range raise ValueError."""
    # Unicode character just before braille block
    with pytest.raises(ValueError):
        braille_to_dots('\u27ff')  # U+27FF is just before U+2800

    # Unicode character just after braille block
    with pytest.raises(ValueError):
        braille_to_dots('\u2900')  # U+2900 is just after U+28FF

    # Common Unicode character (emoji)
    with pytest.raises(ValueError):
        braille_to_dots('😀')


def test_braille_to_dots_braille_blank_pattern():
    """Test that braille blank pattern ⠀ (U+2800) returns empty cell."""
    # U+2800 is the "braille pattern blank" - a valid braille character with no dots
    result = braille_to_dots('⠀')
    assert result == [0, 0, 0, 0, 0, 0], f'Expected empty cell for ⠀ (U+2800), got {result}'


def test_ui_ds_footprints_match_interpoint_packages():
    """
    public/index.html's DS_FOOTPRINTS and app/geometry/interpoint.py's
    DS_FOOTPRINTS_BY_PRESET are two copies of the same signed-off packages
    (0.3 -> Option B, 0.4 -> the 2026-08-20 Q2 print-matrix winner).
    Cross-file default drift is this project's #1 historical bug source,
    so the two copies are diffed here.
    """
    import re
    from pathlib import Path

    from app.geometry import interpoint

    html = (Path(__file__).resolve().parents[1] / 'public' / 'index.html').read_text(encoding='utf-8')
    match = re.search(r'const DS_FOOTPRINTS = \{(.*?)\n {8}\};', html, re.DOTALL)
    assert match, 'DS_FOOTPRINTS block not found in public/index.html'
    ui_packages = {}
    for preset in re.finditer(r"'(0\.[34])': \{(.*?)\}", match.group(1), re.DOTALL):
        pairs = re.findall(r'(ds_\w+): ([0-9.]+)', preset.group(2))
        assert len(pairs) == 6, f'expected 6 ds fields in the {preset.group(1)} package'
        ui_packages[preset.group(1)] = {name: float(value) for name, value in pairs}
    assert ui_packages == interpoint.DS_FOOTPRINTS_BY_PRESET


def test_zero_recess_depth_cuts_no_cylinder_bowls(client):
    """
    Bowl Recess Dot Depth 0 mm means NO recess, not the shipped default.

    The Manifold worker substitutes 0.8 mm for a non-positive bowl_depth
    (static/workers/csg-worker-manifold.js), so a spec that still carried
    depth 0 handed the user an 0.8 mm bowl they never asked for. The spec now
    declines to emit those dots, which makes that substitution unreachable.
    """
    payload = {
        'lines': ['⠁⠃', '', '', ''],
        'plate_type': 'negative',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1, 'counter_dot_depth': 0.0},
        'cylinder_params': {'diameter': 60.0, 'height': 40.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert data['dots'] == [], f'expected no recesses at 0 mm depth, got {len(data["dots"])}'
    assert any('0 mm' in w for w in data.get('warnings', [])), (
        f'the omission must be reported to the user, not silent; warnings were {data.get("warnings")}'
    )

    # Markers are untouched: only the recess dots go.
    settings = CardSettings(**payload['settings'])
    assert len(data['markers']) == settings.grid_rows * 2


def test_zero_recess_depth_does_not_crash_the_card_plate(client):
    """
    The card counter plate divides by the depth to size its sphere, so 0 mm
    used to raise ZeroDivisionError and return a 500. It now cuts nothing.
    """
    payload = {
        'lines': ['⠁⠃', '', '', ''],
        'plate_type': 'negative',
        'shape_type': 'card',
        'grade': 'g1',
        'settings': {'grid_rows': 4, 'grid_columns': 4, 'recess_shape': 1, 'counter_dot_depth': 0.0},
    }

    resp = client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})
    assert resp.status_code == 200, resp.data
    data = resp.get_json()
    assert all(d.get('type') != 'rounded' for d in data['dots']), 'no bowl may be cut at 0 mm depth'


def test_positive_recess_depths_are_unchanged():
    """
    The zero-depth guard must not move any dimension a user actually prints.
    These are the shipped depths: 0.8 mm single-sided, 0.5 mm double-sided.
    """
    from app.geometry_spec import _create_cylinder_dot_spec, _create_dot_spec, _create_ds_cylinder_dot_spec

    settings = CardSettings(**{'counter_dot_depth': 0.8, 'recess_shape': 1, 'use_bowl_recess': 1})
    card = _create_dot_spec(0.0, 0.0, settings, shape_type='bowl', plate_type='negative')
    assert card['params']['dome_height'] == 0.8

    cylinder = _create_cylinder_dot_spec(0.0, 0.0, 15.4, settings, plate_type='negative')
    assert cylinder['params'] == {'shape': 'bowl', 'bowl_radius': 0.9, 'bowl_depth': 0.8}

    ds_settings = CardSettings(**{'shape_type': 'cylinder'})
    ds_settings.ds_bowl_depth = 0.5
    ds = _create_ds_cylinder_dot_spec(0.0, 0.0, 15.4, ds_settings, is_recess=True)
    assert ds['params'] == {'shape': 'bowl', 'bowl_radius': 0.65, 'bowl_depth': 0.5}


def test_zero_ds_bowl_depth_cuts_no_paired_recess():
    """
    ds_bowl_depth_mm is schema-legal at 0.0 and reaches the same worker line
    as the single-sided depth, so it gets the same treatment.
    """
    from app.geometry_spec import _create_ds_cylinder_dot_spec

    settings = CardSettings(**{'shape_type': 'cylinder'})
    settings.ds_bowl_depth = 0.0
    assert _create_ds_cylinder_dot_spec(0.0, 0.0, 15.4, settings, is_recess=True) is None

    # The raised dot on the same cylinder is unaffected - only the bowl goes.
    raised = _create_ds_cylinder_dot_spec(0.0, 0.0, 15.4, settings, is_recess=False)
    assert raised is not None and raised['is_recess'] is False


def test_payload_fallback_literals_match_the_shipped_defaults():
    """
    The /geometry_spec payload builder in public/index.html reads each dial as
    `document.getElementById('x')?.value || 'literal'`. An empty input is the
    empty string, which is falsy, so CLEARING a box hands that literal straight
    to the geometry - these are live fallbacks, not dead code.

    Nothing pinned them, and twice now a literal has been left behind when the
    real default moved: the tactile pair sat at the OpenSCAD generator's old
    5.0 / 0.8 after the defaults became 10.0 / 0.5 (fixed 33f11d6), and
    counter_dot_depth carried 0.6 - which is not this parameter's default at all
    but `indicators.depth_mm`, a different schema field (fixed 2026-08-22).

    Pinned at the source rather than through the browser on purpose: an e2e test
    has to edit a dial, and restoreThicknessPreset() re-applies the card-stock
    preset over every dial on load, which makes any such test racy. Measured at
    roughly 1 run in 3 before it was abandoned.
    """
    import re
    from pathlib import Path

    html = (Path(__file__).resolve().parents[1] / 'public' / 'index.html').read_text(encoding='utf-8')

    # field name -> the value the app should fall back to, and where that is set
    expected = {
        'counter_dot_depth': ('0.8', 'settings.schema.json dots.bowl.depth_mm and app/models.py'),
        'tactile_indicator_length': ('10.0', 'the 2026-07-30 tactile defaults'),
        'tactile_indicator_raise': ('0.5', 'the 2026-07-30 tactile defaults'),
    }

    for field, (want, source) in expected.items():
        pattern = rf"{field}: document\.getElementById\('{field}'\)\?\.value \|\| '([0-9.]+)'"
        match = re.search(pattern, html)
        assert match, f'payload fallback for {field} not found in public/index.html'
        assert match.group(1) == want, (
            f'Emptying the {field} box would send {match.group(1)}, but the shipped default is '
            f'{want} ({source}). A fallback literal must never be a second, drifting copy of a default.'
        )
