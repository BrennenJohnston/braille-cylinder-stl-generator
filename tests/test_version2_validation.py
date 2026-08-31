"""
Validation gates for the Embosser Version 2 keyed gear-peg prototype.

Two things are proved here, and the second matters as much as the first:

  1. Version 2 is cylinders-only, its clearance dial is bounded, and it cannot
     be combined with the integrated-gears beta - all through the real
     /geometry_spec route, with the error wording the UI will show.
  2. A request that does not ask for Version 2 is validated EXACTLY as it was
     before the prototype existed: the field absent, 1, '1', 1.0 or '' adds not
     one new check, and the responses stay byte-identical to the baselines.

The isolation half is the gear beta's proof pattern re-run for Version 2.

Every user-facing sentence quoted below is DRAFT. Brennen deferred the Version
2 strings to their phase gates on 2026-08-28, so these are FLAGGED FOR BRENNEN
and not yet signed.
"""

import copy
import json
from pathlib import Path

import pytest

from app.geometry import version2
from app.validation import ValidationError, validate_embosser_version_settings

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
PRE_BETA_FIXTURES = ['card_positive_small', 'card_counter_small', 'cylinder_positive_small', 'cylinder_counter_small']

# S-V6 and S-V7, DRAFT. The route must quote whichever wording is signed.
CYLINDER_ONLY_MESSAGE = 'Version 2 is only available for cylinders.'
NO_GEARS_MESSAGE = 'Integrated gears are not available in Version 2.'

# Values that all mean "the user did not ask for Version 2". CardSettings reads
# None and '' as "use the default", so validation has to as well, or an empty
# form field would behave differently from a missing one.
VERSION_ONE_VALUES = [1, '1', 1.0, '', None]

V2_CYLINDER = {'diameter': 30.8, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0}

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
    'cylinder_params': dict(V2_CYLINDER),
}
DOUBLE_SIDED_PAYLOAD = {
    'shape_type': 'cylinder',
    'plate_type': 'positive',
    'lines': ['⠁⠃⠉', '', '', ''],
    'back_lines': ['⠙⠑⠋', '', '', ''],
    'settings': {
        'grid_columns': 14,
        'grid_rows': 4,
        'indicator_mode': 'tactile',
        'double_sided_enabled': 1,
    },
    'cylinder_params': {'diameter': 30.75, 'height': 52.0, 'wall_thickness': 2.0, 'seam_offset_deg': 0.0},
}


def post_spec(client, payload):
    return client.post('/geometry_spec', json=payload, headers={'Content-Type': 'application/json'})


def with_settings(payload, **values):
    updated = copy.deepcopy(payload)
    updated.setdefault('settings', {}).update(values)
    return updated


# --- the unit-level gate ----------------------------------------------------


@pytest.mark.parametrize('value', VERSION_ONE_VALUES)
@pytest.mark.parametrize('shape_type', ['card', 'cylinder', 'anything-else'])
def test_version_one_adds_no_validation_whatsoever(value, shape_type):
    """
    A shape_type that WOULD fail the gate passes when Version 2 is not asked
    for - 'anything-else' included, which proves the function is not quietly
    validating shape_type on its own behalf.
    """
    settings = {'embosser_version': value, 'v2_key_clearance_mm': 99.0, 'gear_rollers_enabled': 1}
    assert validate_embosser_version_settings(settings, shape_type, V2_CYLINDER) is True


@pytest.mark.parametrize('shape_type', ['card', 'cylinder'])
def test_an_absent_field_adds_no_validation(shape_type):
    assert validate_embosser_version_settings({}, shape_type, V2_CYLINDER) is True


def test_version_two_on_a_cylinder_passes():
    assert validate_embosser_version_settings({'embosser_version': 2}, 'cylinder', V2_CYLINDER) is True


@pytest.mark.parametrize('value', ['two', 3, -1, 0, 2.5])
def test_an_unknown_version_is_refused_loudly(value):
    with pytest.raises(ValidationError) as raised:
        validate_embosser_version_settings({'embosser_version': value}, 'cylinder', V2_CYLINDER)
    assert 'embosser_version' in str(raised.value)


@pytest.mark.parametrize('clearance', [0.0, 0.075, 0.5])
def test_a_clearance_inside_the_dial_passes(clearance):
    settings = {'embosser_version': 2, 'v2_key_clearance_mm': clearance}
    assert validate_embosser_version_settings(settings, 'cylinder', V2_CYLINDER) is True


@pytest.mark.parametrize('clearance', [-0.01, 0.51, 5.0])
def test_a_clearance_outside_the_dial_is_refused(clearance):
    settings = {'embosser_version': 2, 'v2_key_clearance_mm': clearance}
    with pytest.raises(ValidationError) as raised:
        validate_embosser_version_settings(settings, 'cylinder', V2_CYLINDER)
    message = str(raised.value)
    assert 'version_2.key_clearance_mm' in message
    assert str(version2.V2_KEY_CLEARANCE_MAX_MM) in message


def test_the_size_is_not_gated():
    """
    D-V15: 30.8 x 52 is a soft preset, so an off-size cylinder is accepted here
    and only warned about in the geometry spec.
    """
    off_size = {'diameter': 30.8, 'height': 60.0, 'wall_thickness': 2.0}
    assert validate_embosser_version_settings({'embosser_version': 2}, 'cylinder', off_size) is True


# --- through the real route -------------------------------------------------


@pytest.mark.parametrize('value', VERSION_ONE_VALUES)
def test_version_one_requests_still_succeed(client, value):
    response = post_spec(client, with_settings(CYLINDER_PAYLOAD, embosser_version=value))
    assert response.status_code == 200


def test_version_two_cylinder_succeeds(client):
    response = post_spec(client, with_settings(CYLINDER_PAYLOAD, embosser_version=2))
    assert response.status_code == 200


def test_version_two_card_is_refused_with_the_drafted_sentence(client):
    response = post_spec(client, with_settings(CARD_PAYLOAD, embosser_version=2))
    assert response.status_code == 400
    assert CYLINDER_ONLY_MESSAGE in response.get_json()['error']


@pytest.mark.parametrize('value', ['two', 3, -1])
def test_junk_versions_are_refused_by_the_route(client, value):
    response = post_spec(client, with_settings(CYLINDER_PAYLOAD, embosser_version=value))
    assert response.status_code == 400
    assert 'embosser_version' in response.get_json()['error']


@pytest.mark.parametrize('clearance', [-0.01, 0.51])
def test_an_out_of_range_clearance_is_refused_by_the_route(client, clearance):
    payload = with_settings(CYLINDER_PAYLOAD, embosser_version=2, v2_key_clearance_mm=clearance)
    response = post_spec(client, payload)
    assert response.status_code == 400
    assert 'key_clearance_mm' in response.get_json()['error']


@pytest.mark.parametrize('clearance', [0.0, 0.075, 0.5])
def test_an_in_range_clearance_is_accepted_by_the_route(client, clearance):
    payload = with_settings(CYLINDER_PAYLOAD, embosser_version=2, v2_key_clearance_mm=clearance)
    assert post_spec(client, payload).status_code == 200


def test_gears_with_version_two_name_the_real_conflict(client):
    """
    Both betas on must report the incompatibility, not the cylinder size.

    Since 2026-08-30 both presets are 30.8, so at the preset size the two gates
    agree about the cylinder and the ordering does not show here. It still has
    to hold - see the off-size case below, which is where it bites.
    """
    payload = with_settings(CYLINDER_PAYLOAD, embosser_version=2, gear_rollers_enabled=1)
    response = post_spec(client, payload)
    assert response.status_code == 400
    assert NO_GEARS_MESSAGE in response.get_json()['error']


def test_gears_with_version_two_name_the_conflict_even_off_size(client):
    """
    The ordering proof, on a cylinder the gear gate really would reject.

    Version 2's gate must answer first, or the user is sent off resizing a
    cylinder when the real problem is that they asked for two different
    machines at once. This used to be provable at the preset size, because the
    two presets were 30.5 and 30.8; they agree now, so the case has to be built
    rather than assumed.
    """
    payload = copy.deepcopy(CYLINDER_PAYLOAD)
    payload['cylinder_params']['diameter'] = 30.5
    response = post_spec(client, with_settings(payload, embosser_version=2, gear_rollers_enabled=1))
    assert response.status_code == 400
    error = response.get_json()['error']
    assert NO_GEARS_MESSAGE in error
    assert 'reference roller' not in error, 'the gear size gate answered first'


def test_gears_without_version_two_still_answer_for_themselves(client):
    """
    The existing gear gate is untouched: its own size message still wins.

    The size is set explicitly rather than inherited. This test used to pass on
    CYLINDER_PAYLOAD alone, because that carried Version 2's 30.5 preset, which
    the gears reject. Both presets are 30.8 since 2026-08-30, so an inherited
    size would now sail through the gate this test exists to exercise.
    """
    payload = copy.deepcopy(CYLINDER_PAYLOAD)
    payload['cylinder_params']['diameter'] = 30.5
    response = post_spec(client, with_settings(payload, gear_rollers_enabled=1))
    assert response.status_code == 400
    assert 'Integrated gears are matched to the reference roller' in response.get_json()['error']


def test_an_off_size_version_two_cylinder_is_accepted_by_the_route(client):
    payload = copy.deepcopy(CYLINDER_PAYLOAD)
    payload['cylinder_params']['diameter'] = 30.5
    assert post_spec(client, with_settings(payload, embosser_version=2)).status_code == 200


# --- isolation --------------------------------------------------------------


@pytest.mark.parametrize('value', VERSION_ONE_VALUES)
@pytest.mark.parametrize('fixture_name', PRE_BETA_FIXTURES)
def test_pre_beta_payloads_are_unchanged_by_a_version_one_field(client, fixture_name, value):
    metadata = json.loads((FIXTURES_DIR / f'{fixture_name}.json').read_text(encoding='utf-8'))
    payload = metadata['request_payload']

    baseline = post_spec(client, payload)
    with_field = post_spec(client, with_settings(payload, embosser_version=value))
    assert baseline.status_code == with_field.status_code == 200
    assert baseline.get_json() == with_field.get_json()


@pytest.mark.parametrize('value', VERSION_ONE_VALUES)
def test_a_double_sided_payload_is_unchanged_by_a_version_one_field(client, value):
    baseline = post_spec(client, DOUBLE_SIDED_PAYLOAD)
    with_field = post_spec(client, with_settings(DOUBLE_SIDED_PAYLOAD, embosser_version=value))
    assert baseline.status_code == with_field.status_code == 200
    assert baseline.get_json() == with_field.get_json()


def test_the_isolation_check_can_actually_fail(client):
    """
    The comparison above is only worth having if it notices a difference.
    A 0.01 mm nudge to the cylinder must break it.
    """
    baseline = post_spec(client, CYLINDER_PAYLOAD)
    nudged = copy.deepcopy(CYLINDER_PAYLOAD)
    nudged['cylinder_params']['diameter'] += 0.01
    assert baseline.status_code == 200
    assert baseline.get_json() != post_spec(client, nudged).get_json()
