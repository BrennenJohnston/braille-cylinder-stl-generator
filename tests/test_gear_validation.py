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

from app.geometry import gears
from app.validation import ValidationError, validate_gear_rollers_settings

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
PRE_BETA_FIXTURES = ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small']

# S6, signed off by Brennen 2026-08-24. The route must quote it verbatim.
GEAR_CYLINDER_ONLY_MESSAGE = 'Integrated gears are only available for cylinders.'

# The one cylinder the vendored gears fit. Anything else is refused (S7).
REFERENCE_CYLINDER = {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}

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
    assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, shape_type, REFERENCE_CYLINDER) is True


@pytest.mark.parametrize('shape_type', ['card', 'cylinder'])
def test_absent_flag_adds_no_validation(shape_type):
    assert validate_gear_rollers_settings({}, shape_type, REFERENCE_CYLINDER) is True
    assert validate_gear_rollers_settings({'grid_columns': 14}, shape_type, REFERENCE_CYLINDER) is True


@pytest.mark.parametrize('flag', [1, '1', 1.0])
def test_gears_on_a_cylinder_pass(flag):
    assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, 'cylinder', REFERENCE_CYLINDER) is True
    # shape_type is compared case- and whitespace-insensitively, like the rest
    # of the module's string handling.
    assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, ' Cylinder ', REFERENCE_CYLINDER) is True


@pytest.mark.parametrize('flag', [1, '1', 1.0])
def test_gears_on_a_card_are_rejected_with_the_signed_wording(flag):
    with pytest.raises(ValidationError) as excinfo:
        validate_gear_rollers_settings({'gear_rollers_enabled': flag}, 'card', REFERENCE_CYLINDER)
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
        validate_gear_rollers_settings({'gear_rollers_enabled': junk}, 'cylinder', REFERENCE_CYLINDER)
    assert 'gear_rollers.enabled' in str(excinfo.value)


# --- the reference-roller gate (S7) -----------------------------------------
#
# The gears are baked at fixed heights and do not move with the barrel, so a
# cylinder that is not the reference size does not merely look different - it
# comes apart. Measured on the real assets 2026-08-24: 51.0 mm exports as THREE
# loose bodies (each closed, so the mesh still reports "watertight"), and
# 62.0 mm swallows 5 mm of each gear. Hence a rejection, not a warning.


@pytest.mark.parametrize(
    'diameter,height',
    [
        (30.75, 52.0),  # the Layer-1 schema default: 0.043 mm off the reference barrel
        (30.8, 51.0),  # 1 mm short -> three loose bodies
        (30.8, 62.0),  # 10 mm tall -> gear teeth swallowed
        (32.3, 52.0),  # barrel past the tooth tips -> the pair cannot mesh
        (30.8, 52.01),  # ten times the tolerance
        (30.81, 52.0),
    ],
)
def test_a_cylinder_that_is_not_the_reference_roller_is_rejected(diameter, height):
    params = {**REFERENCE_CYLINDER, 'diameter': diameter, 'height': height}
    with pytest.raises(ValidationError) as excinfo:
        validate_gear_rollers_settings({'gear_rollers_enabled': 1}, 'cylinder', params)

    message = str(excinfo.value)
    assert 'matched to the reference roller' in message
    # The message has to say what was received, or the user cannot tell which
    # of the two dimensions is wrong - and it has to say it the way the SIGNED
    # sentence does, "52 mm" rather than Python's "52.0 mm". %g is an
    # independent formatter, so this is a real check and not a restatement of
    # the production one.
    assert f'{diameter:g}' in message
    assert f'{height:g}' in message
    assert excinfo.value.details['diameter_mm'] == diameter
    assert excinfo.value.details['height_mm'] == height


def test_the_error_spells_numbers_the_way_the_signed_sentence_does():
    """
    The UI shows this same warning live, written by JavaScript, which renders
    52.0 as "52". If the server said "52.0 mm" a user would meet two spellings
    of one signed sentence.
    """
    params = {**REFERENCE_CYLINDER, 'height': 45.0}
    with pytest.raises(ValidationError) as excinfo:
        validate_gear_rollers_settings({'gear_rollers_enabled': 1}, 'cylinder', params)

    message = str(excinfo.value)
    assert 'only fit a 30.8 mm x 52 mm cylinder' in message
    assert 'Received 30.8 mm x 45 mm.' in message
    assert '52.0' not in message
    assert '45.0' not in message


def test_the_reference_roller_itself_passes():
    assert validate_gear_rollers_settings({'gear_rollers_enabled': 1}, 'cylinder', REFERENCE_CYLINDER) is True


@pytest.mark.parametrize('delta', [0.0, 0.0005, -0.0005])
def test_float_slack_is_tolerated_but_nothing_wider(delta):
    """
    The tolerance is float slack only - about 250x a float32 ULP at 32 mm, and
    far below any dimension a user can type into the form.
    """
    params = {**REFERENCE_CYLINDER, 'height': gears.GEAR_BARREL_HEIGHT_MM + delta}
    assert validate_gear_rollers_settings({'gear_rollers_enabled': 1}, 'cylinder', params) is True


def test_the_dimension_gate_is_skipped_entirely_when_gears_are_off():
    """A cylinder no gear would fit is fine as long as nobody asked for gears."""
    params = {**REFERENCE_CYLINDER, 'diameter': 12.0, 'height': 200.0}
    for flag in FLAG_OFF_VALUES:
        assert validate_gear_rollers_settings({'gear_rollers_enabled': flag}, 'cylinder', params) is True
    assert validate_gear_rollers_settings({}, 'cylinder', params) is True


@pytest.mark.parametrize(
    'params,expected_diameter,expected_height',
    [
        ({}, 30.75, 52.0),  # both fall back to the schema defaults (52 = the V1 standard; 54 is V2-only)
        ({'diameter_mm': 30.8, 'height_mm': 52.0}, 30.8, 52.0),  # the _mm spellings work
        ({'diameter': 30.8, 'height': 52.0}, 30.8, 52.0),
    ],
)
def test_dimensions_are_read_the_way_geometry_spec_reads_them(params, expected_diameter, expected_height):
    """
    Both files call gears.cylinder_dimensions, so they cannot disagree about
    what an absent or differently-spelled field means. This pins the contract.
    """
    assert gears.cylinder_dimensions(params) == (expected_diameter, expected_height)


def test_an_empty_cylinder_params_is_rejected_in_gear_mode():
    """
    Falling back to the 30.75 default is exactly the mismatch this gate exists
    to catch, so an omitted cylinder_params must fail rather than pass quietly.
    """
    with pytest.raises(ValidationError) as excinfo:
        validate_gear_rollers_settings({'gear_rollers_enabled': 1}, 'cylinder', {})
    assert '30.75' in str(excinfo.value)


def test_a_cylinder_that_is_not_the_reference_roller_is_rejected_by_the_route(client):
    payload = copy.deepcopy(CYLINDER_PAYLOAD)
    payload['cylinder_params']['height'] = 45.0
    response = post_spec(client, with_gear_flag(payload, 1))
    assert response.status_code == 400
    assert 'matched to the reference roller' in response.get_json()['error']


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
