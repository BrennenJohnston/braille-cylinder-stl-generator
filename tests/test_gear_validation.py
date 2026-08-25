"""
Validation gates for the gear-integrated one-piece rollers (BETA).

Two things are proved here, and the second matters as much as the first:

  1. Gear mode is cylinders-only, enforced through the real /geometry_spec
     route with the signed error wording.
  2. A request that does not ask for gears is validated EXACTLY as it was
     before this beta existed - the flag off, empty, None or absent adds not
     one new check, and the responses stay byte-identical to the pre-beta
     baselines.

The isolation half is the interpoint beta's proof pattern re-run for gears.
"""

import copy
import json
from pathlib import Path

import pytest

from app.validation import ValidationError, validate_gear_rollers_settings

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
PRE_BETA_FIXTURES = ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small']

# S6, signed off by Brennen 2026-08-24. The route must quote it verbatim.
GEAR_CYLINDER_ONLY_MESSAGE = 'Integrated gears are only available for cylinders.'

# Values that all mean "the user did not ask for gears". CardSettings treats
# None and '' as "use the default", so validation has to as well - anything
# else would make an empty form field behave differently from a missing one.
FLAG_OFF_VALUES = [0, '0', 0.0, '', None]

CARD_PAYLOAD = {
    'shape_type': 'card',
    'plate_type': 'positive',
    'lines': ['⠁⠃⠉', '', '', ''],
    'settings': {'grid_columns': 12, 'grid_rows': 4},
}
CYLINDER_PAYLOAD = {
    'shape_type': 'cylinder',
    'plate_type': 'positive',
    'lines': ['⠁⠃⠉', '', '', ''],
    'settings': {'grid_columns': 14, 'grid_rows': 4},
    'cylinder_params': {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
}


def post_spec(client, payload):
    return client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})


def with_gear_flag(payload, value):
    updated = copy.deepcopy(payload)
    updated.setdefault('settings', {})['gear_rollers_enabled'] = value
    return updated


# --- the unit-level gate ----------------------------------------------------


@pytest.mark.parametrize('flag', FLAG_OFF_VALUES)
@pytest.mark.parametrize('shape_type', ['card', 'cylinder', 'anything-else'])
def test_flag_off_adds_no_validation_whatsoever(flag, shape_type):
    """
    A shape_type that WOULD fail the gate passes when gears are not asked for -
    including 'anything-else', which proves the function is not quietly
    validating shape_type on its own behalf.
    """
    assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, shape_type) is True


@pytest.mark.parametrize('shape_type', ['card', 'cylinder'])
def test_absent_flag_adds_no_validation(shape_type):
    assert validate_gear_rollers_settings({}, shape_type) is True
    assert validate_gear_rollers_settings({'grid_columns': 14}, shape_type) is True


@pytest.mark.parametrize('flag', [1, '1', 1.0])
def test_gears_on_a_cylinder_pass(flag):
    assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, 'cylinder') is True
    # shape_type is compared case- and whitespace-insensitively, like the rest
    # of the module's string handling.
    assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, ' Cylinder ') is True


@pytest.mark.parametrize('flag', [1, '1', 1.0])
def test_gears_on_a_card_are_rejected_with_the_signed_wording(flag):
    with pytest.raises(ValidationError) as excinfo:
        validate_gear_rollers_settings({'gear_rollers_enabled': flag}, 'card')
    assert str(excinfo.value) == GEAR_CYLINDER_ONLY_MESSAGE
    assert excinfo.value.details['shape_type'] == 'card'
    assert excinfo.value.details['key'] == 'gear_rollers_enabled'


@pytest.mark.parametrize('junk', ['yes', 'true', [], {}, 'on'])
def test_junk_flag_values_fail_loudly(junk):
    """
    No silent fallback: a value that is neither a number nor an empty field is
    an error, never quietly read as "off" (the project's recorded bug family).
    """
    with pytest.raises(ValidationError) as excinfo:
        validate_gear_rollers_settings({'gear_rollers_enabled': junk}, 'cylinder')
    assert 'gear_rollers.enabled' in str(excinfo.value)


# --- through the real route -------------------------------------------------


def test_card_plus_gears_is_rejected_by_the_route(client):
    response = post_spec(client, with_gear_flag(CARD_PAYLOAD, 1))
    assert response.status_code == 400
    assert response.get_json()['error'] == GEAR_CYLINDER_ONLY_MESSAGE


def test_cylinder_plus_gears_is_accepted_by_the_route(client):
    response = post_spec(client, with_gear_flag(CYLINDER_PAYLOAD, 1))
    assert response.status_code == 200, response.data
    assert response.get_json()['shape_type'] == 'cylinder'


@pytest.mark.parametrize('flag', FLAG_OFF_VALUES)
def test_card_with_the_flag_off_is_still_accepted(client, flag):
    response = post_spec(client, with_gear_flag(CARD_PAYLOAD, flag))
    assert response.status_code == 200, response.data


# --- isolation: off must be indistinguishable from absent -------------------


@pytest.mark.parametrize('fixture_name', PRE_BETA_FIXTURES)
@pytest.mark.parametrize('flag', FLAG_OFF_VALUES)
def test_pre_beta_payloads_are_unchanged_by_an_off_flag(client, fixture_name, flag):
    """
    Beta isolation: every pre-beta golden payload must produce a byte-identical
    /geometry_spec response with the flag off as it does with the flag absent.
    """
    metadata = json.loads((FIXTURES_DIR / f'{fixture_name}.json').read_text(encoding='utf-8'))
    payload = metadata['request_payload']

    baseline = post_spec(client, payload)
    assert baseline.status_code == 200, baseline.data

    toggled_off = post_spec(client, with_gear_flag(payload, flag))
    assert toggled_off.status_code == 200, toggled_off.data
    assert toggled_off.get_json() == baseline.get_json()


def test_a_double_sided_payload_is_unchanged_by_an_off_flag(client):
    """The two betas must not disturb each other while gears are off."""
    payload = {
        'shape_type': 'cylinder',
        'plate_type': 'positive',
        'lines': ['⠁⠃⠉', '', '', ''],
        'back_lines': ['⠙⠑⠋', '', '', ''],
        'settings': {
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
        },
        'cylinder_params': {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 355.0},
    }

    baseline = post_spec(client, payload)
    assert baseline.status_code == 200, baseline.data
    toggled_off = post_spec(client, with_gear_flag(payload, 0))
    assert toggled_off.status_code == 200, toggled_off.data
    assert toggled_off.get_json() == baseline.get_json()


def test_the_isolation_check_can_actually_fail(client):
    """
    Non-vacuity: the deep-equality comparison above must be capable of failing,
    otherwise it proves nothing. A 0.05 mm nudge to the cylinder diameter has
    to show up.
    """
    baseline = post_spec(client, CYLINDER_PAYLOAD)
    assert baseline.status_code == 200, baseline.data

    nudged = copy.deepcopy(CYLINDER_PAYLOAD)
    nudged['cylinder_params']['diameter'] = 30.75
    changed = post_spec(client, nudged)
    assert changed.status_code == 200, changed.data
    assert changed.get_json() != baseline.get_json()
