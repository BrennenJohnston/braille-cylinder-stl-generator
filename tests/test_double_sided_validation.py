"""
Validation gates for the double-sided (interpoint) beta — Phase 06, 13b.

app/validation.py now enforces four hard gates at request time (until Phase 06,
the double-sided ranges in settings.schema.json were documentation
only): a double-sided request must use the tactile row indicator style, the
interpoint offsets must stay inside [1.15, 1.35] mm, the six ds_* footprint
values must stay inside their documented schema ranges, and the same-surface
gap — the material between a raised dot and the nearest back-side recess
sharing one cylinder surface — must clear the 0.34 mm slicer floor. The
marginal band (0.34–0.50 mm) stays a soft path: validation logs it and
geometry_spec returns the user-facing warning.

PHASE 13b (2026-08-21) moved the FLOOR gate onto the recess's PRINTED mouth
(FD-11b): the worker cuts the bowl as a hemisphere, so it prints wider than
nominal — 1.345 mm for the 0.3 package's 1.3 x 0.5 and 1.480 mm for the 0.4
package's 1.4 x 0.5. The two soft warnings deliberately stay on the nominal
figure, so the numbers below come in matched pairs.

Reference gap numbers (tolerance ±0.001 mm; nominal from the 2026-08-16
research, printed measured 2026-08-21). Option B dot 1.2 + bowl 1.3 x 0.5 →
0.518 nominal / 0.495 printed (clean pass); dot 1.2 + bowl 1.5 → 0.418 nominal
(warn); shipped single-sided dot 1.5 + bowl 1.8 x 0.5 → 0.118 nominal /
−0.042 printed (reject). All checks are gated on double_sided_enabled == 1, so
single-sided requests are validated exactly as before the beta existed.
"""

import logging
import re
from pathlib import Path

import pytest

from app.geometry import interpoint as ip
from app.validation import ValidationError, validate_double_sided_settings, validate_settings

VALIDATION_LOGGER = 'app.validation'
REPO_ROOT = Path(__file__).resolve().parents[1]


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
    """
    Schema min/max values that also clear the gap floor pass validation.

    ds_bowl_depth takes its MINIMUM here rather than its maximum. Since Phase
    13b the floor gate measures the printed mouth, and a 0.5 mm bowl cut 5.0 mm
    deep prints 5.01 mm across — see the test below. Depth 0.0 is the schema
    minimum and has no hemisphere to convert, so it exercises the gate's
    non-positive-depth path as well.
    """
    assert (
        validate_settings(
            _ds_settings(
                ds_dot_base_diameter=0.5,
                ds_dot_base_height=2.0,
                ds_dot_dome_diameter=3.0,
                ds_dot_dome_height=0.1,
                ds_bowl_base_diameter=0.5,
                ds_bowl_depth=0.0,
            )
        )
        is True
    )


def test_schema_maximum_bowl_depth_is_rejected_by_the_printed_mouth():
    """
    A measured consequence of the Phase 13b switch, not a range change.

    ds_bowl_depth_mm still documents 0.0–5.0 in settings.schema.json, but the
    sphere a 0.5 mm mouth cut 5.0 mm deep implies has radius 2.506 mm, and the
    worker cuts its whole lower half: a 5.01 mm crater. The nominal figure hid
    that entirely — it read the recess as 0.5 mm across.
    """
    settings = _ds_settings(ds_dot_base_diameter=0.5, ds_bowl_base_diameter=0.5, ds_bowl_depth=5.0)
    assert ip.printed_bowl_mouth_mm(0.5, 5.0) == pytest.approx(5.0125, abs=0.001)
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(settings)
    assert excinfo.value.details['printed_bowl_mouth_mm'] == pytest.approx(5.013, abs=0.001)
    assert excinfo.value.details['nominal_gap_mm'] == pytest.approx(1.268, abs=0.001)


# -----------------------------------------------------------------------------
# Gate 4: same-surface gap
# -----------------------------------------------------------------------------


def test_shipped_single_sided_footprints_are_rejected():
    """
    Dot 1.5 + bowl 1.8 is under the floor either way you measure it.

    The 1.8 x 0.5 bowl prints 2.12 mm across, so the ridge is −0.042 mm — the
    two footprints actually overlap — where the nominal figure read 0.118 mm.
    Both are below 0.34 mm, so this configuration was rejected before Phase 13b
    and is rejected now; only the quoted number moved.
    """
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(_ds_settings(ds_dot_base_diameter=1.5, ds_bowl_base_diameter=1.8))
    message = str(excinfo.value)
    assert '-0.042' in message
    assert '2.12' in message  # the printed mouth, quoted beside the printed ridge
    assert '0.118' not in message  # the nominal ridge is no longer quoted at the user
    assert f'{ip.SAME_SURFACE_GAP_FLOOR_MM:.2f}' in message
    assert excinfo.value.details['gap_mm'] == pytest.approx(-0.042, abs=0.001)
    assert excinfo.value.details['nominal_gap_mm'] == pytest.approx(0.118, abs=0.001)


def test_marginal_gap_warns_but_passes(caplog):
    """
    Dot 1.2 + bowl 1.5 leaves 0.418 mm nominal — printable, so warn only.

    The logged figure is the NOMINAL one by design (FD-11b): this log mirrors
    the soft warning app/geometry_spec.py shows the user, and that stayed
    nominal so the browser, the generator and the OpenSCAD port quote one
    number. The printed ridge here is 0.355 mm, still clear of the floor.
    """
    with caplog.at_level(logging.WARNING, logger=VALIDATION_LOGGER):
        assert validate_settings(_ds_settings(ds_dot_base_diameter=1.2, ds_bowl_base_diameter=1.5)) is True
    records = _double_sided_log_records(caplog)
    assert len(records) == 1
    assert '0.418' in records[0].message


# -----------------------------------------------------------------------------
# Gate 4, Phase 13b: the floor is measured on the recess's PRINTED mouth
# -----------------------------------------------------------------------------
# Every number below was swept over the documented 1.15-1.35 mm offset range in
# 0.01 mm steps, both packages, on 2026-08-21: the 0.3 package keeps all 441
# combinations, the 0.4 package keeps 297 and loses 132 that the nominal figure
# used to let through.


def _package(preset, **overrides):
    """A double-sided settings dict carrying one shipped footprint package."""
    return _ds_settings(**{**ip.DS_FOOTPRINTS_BY_PRESET[preset], **overrides})


@pytest.mark.parametrize(
    ('preset', 'printed_mouth', 'printed_gap'),
    [('0.3', 1.345, 0.495), ('0.4', 1.480, 0.428)],
)
def test_both_shipped_packages_pass_at_the_default_offsets(preset, printed_mouth, printed_gap):
    """Neither shipped package moved: the switch does not touch what the app ships."""
    footprints = ip.DS_FOOTPRINTS_BY_PRESET[preset]
    mouth = ip.printed_bowl_mouth_mm(footprints['ds_bowl_base_diameter'], footprints['ds_bowl_depth'])
    assert mouth == pytest.approx(printed_mouth, abs=0.001)
    assert ip.same_surface_min_gap(
        footprints['ds_dot_base_diameter'], mouth, 1.25, 1.25, 14, 4
    ) == pytest.approx(printed_gap, abs=0.001)
    assert validate_settings(_package(preset, interpoint_offset_x=1.25, interpoint_offset_y=1.25)) is True


def test_crowded_offset_newly_rejected_on_the_04_package():
    """
    1.16/1.16 on the shipped 0.4 package: accepted before Phase 13b, blocked now.

    Nominal 0.3405 mm cleared the 0.34 mm floor by 0.0005 mm; the printed ridge
    is 0.3005 mm and does not. This one configuration is the whole point of the
    switch — the .scad has refused to render it since Phase 12, and until now
    the web app still exported the pair.
    """
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(_package('0.4', interpoint_offset_x=1.16, interpoint_offset_y=1.16))
    details = excinfo.value.details
    assert details['gap_mm'] == pytest.approx(0.3005, abs=0.001)
    assert details['nominal_gap_mm'] == pytest.approx(0.3405, abs=0.001)
    assert details['nominal_gap_mm'] >= ip.SAME_SURFACE_GAP_FLOOR_MM  # would have passed before
    assert details['gap_mm'] < ip.SAME_SURFACE_GAP_FLOOR_MM


def test_the_same_offset_still_passes_on_the_03_package():
    """The 0.3 package pairs the same dot with a smaller bowl and keeps the whole slider."""
    assert validate_settings(_package('0.3', interpoint_offset_x=1.16, interpoint_offset_y=1.16)) is True
    assert validate_settings(_package('0.3', interpoint_offset_x=1.15, interpoint_offset_y=1.35)) is True


@pytest.mark.parametrize(('offset', 'accepted'), [(1.19, True), (1.18, False), (1.31, True), (1.32, False)])
def test_the_04_package_diagonal_band_edges(offset, accepted):
    """
    Moving both offsets together, the 0.4 package renders over 1.19-1.31 mm.

    Clearance PEAKS at 1.25 mm and falls off symmetrically, so both ends fail
    together: 1.19 leaves 0.3429 mm and 1.18 leaves 0.3288 mm. This is why the
    error message says "move back toward 1.25" rather than raise or lower.
    """
    settings = _package('0.4', interpoint_offset_x=offset, interpoint_offset_y=offset)
    if accepted:
        assert validate_settings(settings) is True
    else:
        with pytest.raises(ValidationError):
            validate_settings(settings)


def test_offset_range_itself_did_not_narrow():
    """FD-11c: the slider keeps 1.15-1.35 mm; only the crowding gate rejects inside it."""
    assert ip.INTERPOINT_OFFSET_MIN_MM == 1.15
    assert ip.INTERPOINT_OFFSET_MAX_MM == 1.35
    assert validate_settings(_package('0.3', interpoint_offset_x=1.15, interpoint_offset_y=1.15)) is True


def test_non_positive_bowl_depth_falls_back_to_the_nominal_diameter(caplog):
    """
    ds_bowl_depth_mm 0.0 is schema-legal, and a hemisphere cannot be built from it.

    The gate measures the nominal diameter in that case — what it did before
    Phase 13b — and says so in the log rather than reporting a printed figure
    it did not compute.
    """
    with caplog.at_level(logging.WARNING, logger=VALIDATION_LOGGER):
        assert validate_settings(_package('0.4', ds_bowl_depth=0.0)) is True
    assert [r for r in _double_sided_log_records(caplog) if 'not positive' in r.message]
    with pytest.raises(ValueError, match='bowl_depth must be > 0'):
        ip.printed_bowl_mouth_mm(1.4, 0.0)

    # And when a zero-depth config does fail the floor, the message must not
    # claim a hemisphere it never computed.
    with pytest.raises(ValidationError) as excinfo:
        validate_settings(_ds_settings(ds_dot_base_diameter=1.5, ds_bowl_base_diameter=1.8, ds_bowl_depth=0.0))
    assert 'the recess is 1.80 mm across' in str(excinfo.value)
    assert 'hemisphere' not in str(excinfo.value)
    assert excinfo.value.details['gap_mm'] == pytest.approx(0.118, abs=0.001)


# -----------------------------------------------------------------------------
# The FD-11(b) split, pinned in both directions
# -----------------------------------------------------------------------------


def test_the_soft_warning_stays_on_the_nominal_figure():
    """
    Behavioural half of the guard: the 0.3 package must not warn about itself.

    Its printed ridge is 0.4953 mm, just under the 0.50 mm reliable line, so a
    warning switched to the printed figure would flag the package Brennen
    recorded embossing clean on 0.3 mm stock (FD-1). That is the reason FD-11b
    moved the assert alone.
    """
    from app.geometry_spec import _double_sided_crowding_warnings
    from app.models import CardSettings

    footprints = ip.DS_FOOTPRINTS_BY_PRESET['0.3']
    settings = CardSettings(
        double_sided_enabled=1,
        indicator_mode='tactile',
        grid_columns=14,
        grid_rows=4,
        **footprints,
    )
    printed = ip.same_surface_min_gap(
        footprints['ds_dot_base_diameter'],
        ip.printed_bowl_mouth_mm(footprints['ds_bowl_base_diameter'], footprints['ds_bowl_depth']),
        cols=14,
        rows=4,
    )
    assert printed < ip.SAME_SURFACE_GAP_RELIABLE_MM  # a printed-figure warning would fire
    assert _double_sided_crowding_warnings(settings, True) == []  # the nominal one does not


def _python_function_source(relative_path: str, name: str) -> str:
    """
    The source of one Python function, cut at the real end of its body.

    ast rather than a regex: a Python function ends by dedent, and a brace- or
    blank-line-terminated pattern silently swallows the rest of the file — which
    would make the assertions below pass no matter what the function said.
    """
    import ast

    source = (REPO_ROOT / relative_path).read_text(encoding='utf-8')
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            assert segment, f'no source segment for {name} in {relative_path}'
            return segment
    raise AssertionError(f'{name} not found in {relative_path}')


def _js_function_source(relative_path: str, signature: str, indent: int) -> str:
    """One brace-delimited function, from its signature to the closing brace at `indent`."""
    source = (REPO_ROOT / relative_path).read_text(encoding='utf-8')
    pad = ' ' * indent
    match = re.search(rf'^{pad}{re.escape(signature)}.*?^{pad}\}}', source, re.DOTALL | re.MULTILINE)
    assert match, f'{signature} not found at indent {indent} in {relative_path}'
    return match.group(0)


def test_only_the_hard_gate_measures_the_printed_mouth():
    """
    Source half of the guard, pinning FD-11(b) in both directions.

    One formula would be tidier and would silently undo Brennen's decision, so
    the split is asserted at the source: the hard gate converts to the printed
    mouth, and the two soft warnings — the generator's and the browser's — do
    not, which is what keeps all three generators quoting one number.
    """
    gate = _python_function_source('app/validation.py', 'validate_double_sided_settings')
    # The call, not the details key of the same name: the key alone would keep
    # this assertion green after someone reverted the conversion itself.
    assert 'interpoint.printed_bowl_mouth_mm(' in gate

    warning = _python_function_source('app/geometry_spec.py', '_double_sided_crowding_warnings')
    assert 'printed_bowl_mouth_mm' not in warning
    assert 'ds_bowl_depth' not in warning  # the nominal diameter is the only bowl figure it reads

    browser = _js_function_source('public/index.html', 'function checkDoubleSidedGap() {', 8)
    assert 'const gap = centerDistance - (dotDiameter + bowlDiameter) / 2;' in browser
    assert 'ds_bowl_depth' not in browser  # no hemisphere conversion in the live warning


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
    assert '-0.042' in response.get_json()['error']


def test_geometry_spec_route_rejects_the_crowded_04_offset(client):
    """The Phase 13b switch reaches the real route, not just the validator."""
    response = client.post(
        '/geometry_spec',
        json=_geometry_spec_payload(
            interpoint_offset_x=1.16,
            interpoint_offset_y=1.16,
            **ip.DS_FOOTPRINTS_BY_PRESET['0.4'],
        ),
    )
    assert response.status_code == 400
    assert '0.300' in response.get_json()['error']


def test_geometry_spec_route_accepts_option_b(client):
    response = client.post('/geometry_spec', json=_geometry_spec_payload())
    assert response.status_code == 200
    spec = response.get_json()
    assert spec.get('dots')
    assert not [w for w in spec.get('warnings', []) if 'Double-sided' in w]
