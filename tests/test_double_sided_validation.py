"""
Validation gates for the double-sided (interpoint) beta — Phase 06.

app/validation.py now enforces four hard gates at request time (until this
phase, the double-sided ranges in settings.schema.json were documentation
only): a double-sided request must use the tactile row indicator style, the
interpoint offsets must stay inside [1.15, 1.35] mm, the six ds_* footprint
values must stay inside their documented schema ranges, and the same-surface
gap — the material between a raised dot and the nearest back-side recess
sharing one cylinder surface — must clear the 0.34 mm slicer floor. The
marginal band (0.34–0.50 mm) stays a soft path: validation logs it and
geometry_spec returns the user-facing warning.

Reference gap numbers (tolerance ±0.001 mm, 2026-08-16 research): Option B
dot 1.2 + bowl 1.3 → 0.518 (clean pass); dot 1.2 + bowl 1.5 → 0.418 (warn);
shipped single-sided dot 1.5 + bowl 1.8 → 0.118 (reject). All checks are
gated on double_sided_enabled == 1, so single-sided requests are validated
exactly as before the beta existed.
"""

import logging

import pytest

from app.geometry import interpoint as ip
from app.validation import ValidationError, validate_double_sided_settings, validate_settings

VALIDATION_LOGGER = 'app.validation'


def _ds_settings(**overrides):
    """A minimal valid double-sided settings dict (flat CardSettings spelling)."""
    settings = {
        'double_sided_enabled': 1,
        'indicator_mode': 'tactile',
        'grid_columns': 14,
        'grid_rows': 4,
    }
    settings.update(overrides)
    return settings


def _double_sided_log_records(caplog):
    return [
        record for record in caplog.records if record.name == VALIDATION_LOGGER and 'Double-sided' in record.message
    ]


# -----------------------------------------------------------------------------
# Clean pass: the signed-off Option B configuration
# -----------------------------------------------------------------------------


def test_option_b_defaults_pass_cleanly(caplog):
    """Option B (dot 1.2 + bowl 1.3, offsets 1.25/1.25, gap 0.518) passes without a warning."""
    with caplog.at_level(logging.WARNING, logger=VALIDATION_LOGGER):
        assert validate_settings(_ds_settings()) is True
        assert (
            validate_settings(
                _ds_settings(
                    interpoint_offset_x=1.25,
                    interpoint_offset_y=1.25,
                    ds_dot_base_diameter=1.2,
                    ds_bowl_base_diameter=1.3,
                )
            )
            is True
        )
    assert _double_sided_log_records(caplog) == []


def test_offset_boundaries_are_accepted():
    """1.15 and 1.35 mm are inside the documented offset range, not outside it."""
    assert validate_settings(_ds_settings(interpoint_offset_x=1.15, interpoint_offset_y=1.35)) is True


# -----------------------------------------------------------------------------
# Gate 1: tactile lock
# -----------------------------------------------------------------------------


@pytest.mark.parametrize('mode_override', [{'indicator_mode': 'visual'}, {}])
def test_non_tactile_indicator_mode_is_rejected(mode_override):
    """Double-sided requires tactile; 'visual' and the absent-key default both fail."""
    settings = _ds_settings()
    settings.pop('indicator_mode')
    settings.update(mode_override)
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(settings)
    message = str(excinfo.value)
    assert 'tactile' in message.lower()
    assert 'double-sided' in message.lower()


# -----------------------------------------------------------------------------
# Gate 2: interpoint offset range
# -----------------------------------------------------------------------------


@pytest.mark.parametrize('key', ['interpoint_offset_x', 'interpoint_offset_y'])
@pytest.mark.parametrize('value', [1.14, 1.36, 0.0, 2.5])
def test_out_of_range_offset_is_rejected_with_the_range_quoted(key, value):
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(_ds_settings(**{key: value}))
    message = str(excinfo.value)
    assert str(ip.INTERPOINT_OFFSET_MIN_MM) in message
    assert str(ip.INTERPOINT_OFFSET_MAX_MM) in message
    assert '_mm' in message  # quotes the canonical settings.schema.json spelling


# -----------------------------------------------------------------------------
# Gate 3: ds_* footprint schema ranges
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('key', 'bad_value'),
    [
        ('ds_dot_base_diameter', 0.4),
        ('ds_dot_base_diameter', 3.1),
        ('ds_dot_base_height', -0.1),
        ('ds_dot_base_height', 2.1),
        ('ds_dot_dome_diameter', 0.4),
        ('ds_dot_dome_diameter', 3.1),
        ('ds_dot_dome_height', 0.05),
        ('ds_dot_dome_height', 2.1),
        ('ds_bowl_base_diameter', 0.4),
        ('ds_bowl_base_diameter', 5.1),
        ('ds_bowl_depth', -0.1),
        ('ds_bowl_depth', 5.1),
    ],
)
def test_out_of_range_footprint_is_rejected_with_the_range_quoted(key, bad_value):
    """The six ds_* schema ranges are enforced whenever the beta is on."""
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(_ds_settings(**{key: bad_value}))
    message = str(excinfo.value)
    assert f'{key}_mm' in message  # canonical settings.schema.json spelling
    assert 'between' in message
    assert excinfo.value.details['key'] == key


def test_footprint_boundaries_are_accepted():
    """Schema min/max values that also clear the gap floor pass validation."""
    assert (
        validate_settings(
            _ds_settings(
                ds_dot_base_diameter=0.5,
                ds_dot_base_height=2.0,
                ds_dot_dome_diameter=3.0,
                ds_dot_dome_height=0.1,
                ds_bowl_base_diameter=0.5,
                ds_bowl_depth=5.0,
            )
        )
        is True
    )


# -----------------------------------------------------------------------------
# Gate 4: same-surface gap
# -----------------------------------------------------------------------------


def test_shipped_single_sided_footprints_are_rejected():
    """Dot 1.5 + bowl 1.8 leaves 0.118 mm — under the 0.34 mm nozzle floor."""
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(_ds_settings(ds_dot_base_diameter=1.5, ds_bowl_base_diameter=1.8))
    message = str(excinfo.value)
    assert '0.118' in message
    assert f'{ip.SAME_SURFACE_GAP_FLOOR_MM:.2f}' in message
    assert excinfo.value.details['gap_mm'] == pytest.approx(0.118, abs=0.001)


def test_marginal_gap_warns_but_passes(caplog):
    """Dot 1.2 + bowl 1.5 leaves 0.418 mm — printable at the slicer's floor, so warn only."""
    with caplog.at_level(logging.WARNING, logger=VALIDATION_LOGGER):
        assert validate_settings(_ds_settings(ds_dot_base_diameter=1.2, ds_bowl_base_diameter=1.5)) is True
    records = _double_sided_log_records(caplog)
    assert len(records) == 1
    assert '0.418' in records[0].message


# -----------------------------------------------------------------------------
# The off switch: enabled=0 skips every double-sided check
# -----------------------------------------------------------------------------


@pytest.mark.parametrize('enabled', [0, '0', False, None, '', 'absent'])
def test_disabled_flag_skips_every_double_sided_check(enabled):
    """With the beta off, a config that would fail all four gates still passes."""
    settings = {
        'indicator_mode': 'visual',
        'interpoint_offset_x': 9.0,
        'interpoint_offset_y': 0.1,
        'ds_dot_base_diameter': 1.5,
        'ds_bowl_base_diameter': 1.8,
        'ds_bowl_depth': 9.9,
    }
    if enabled != 'absent':
        settings['double_sided_enabled'] = enabled
    assert validate_settings(settings) is True
    assert validate_double_sided_settings(settings) is True


# -----------------------------------------------------------------------------
# Through the real route: backend.py already calls validate_settings
# -----------------------------------------------------------------------------


def _geometry_spec_payload(**settings_overrides):
    return {
        'lines': ['⠁⠃⠉', '', '', ''],
        'plate_type': 'positive',
        'shape_type': 'cylinder',
        'grade': 'g1',
        'settings': _ds_settings(**settings_overrides),
    }


def test_geometry_spec_route_rejects_double_sided_visual(client):
    response = client.post('/geometry_spec', json=_geometry_spec_payload(indicator_mode='visual'))
    assert response.status_code == 400
    assert 'tactile' in response.get_json()['error'].lower()


def test_geometry_spec_route_rejects_shipped_footprints(client):
    response = client.post(
        '/geometry_spec', json=_geometry_spec_payload(ds_dot_base_diameter=1.5, ds_bowl_base_diameter=1.8)
    )
    assert response.status_code == 400
    assert '0.118' in response.get_json()['error']


def test_geometry_spec_route_accepts_option_b(client):
    response = client.post('/geometry_spec', json=_geometry_spec_payload())
    assert response.status_code == 200
    spec = response.get_json()
    assert spec.get('dots')
    assert not [w for w in spec.get('warnings', []) if 'Double-sided' in w]
