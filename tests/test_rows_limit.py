"""
The Rows limit (Brennen's decisions, 2026-10-09; plan 04_ROWS_LIMIT_FIX_PLAN).

The Rows dial allows 1-200, but a fixed four-line cap (MAX_LINES = 4, back
since the 2025-10-10 validation refactor) refused every request with five or
more lines, so Generate failed at Rows 5+. The count is now the request's own
Rows: a line past Rows must be empty (the geometry reads only Rows lines, so
content there would be dropped without a word), and 200 entries is the
ceiling. Whether the rows fit is a separate gate: the dots must stay on the
card and the tactile arrows on the barrel, or the request is refused with
S-R1 / S-R2 (signed 2026-10-09).
"""

import logging

import pytest

from app.geometry_spec import braille_rows_extent
from app.models import CardSettings
from app.validation import ValidationError, validate_braille_rows_fit, validate_lines, validate_original_lines
from backend import app

logging.disable(logging.CRITICAL)

# What the page sends after the 0.4 mm preset (project-facts invariant 6, Layer 2).
LIVE_04 = {
    'use_rounded_dots': 1,
    'rounded_dot_base_diameter': 1.5,
    'rounded_dot_base_height': 0.5,
    'rounded_dot_dome_diameter': 1.0,
    'rounded_dot_dome_height': 0.5,
    'bowl_counter_dot_base_diameter': 1.8,
    'counter_dot_depth': 0.8,
    'grid_columns': 13,
}
V1_BARREL = {'diameter_mm': 30.8, 'height_mm': 52, 'seam_offset_deg': 0}
V2_BARREL = {'diameter_mm': 30.8, 'height_mm': 54, 'seam_offset_deg': 0}


def settings(**overrides):
    return CardSettings(**{**LIVE_04, **overrides})


def post(lines, setting_overrides, plate='positive', original=None):
    body = {
        'lines': lines,
        'plate_type': plate,
        'shape_type': 'cylinder',
        'settings': {**LIVE_04, **setting_overrides},
        'cylinder_params': V1_BARREL,
    }
    if original is not None:
        body['original_lines'] = original
    response = app.test_client().post('/geometry_spec', json=body)
    return response.status_code, (response.get_json() or {}).get('error', '')


class TestLineCount:
    def test_five_rows_generate(self):
        status, error = post(['⠁'] * 5, {'grid_rows': 5})
        assert (status, error) == (200, '')

    def test_the_counter_plate_four_empty_lines_still_pass_at_fewer_rows(self):
        # The page sends four empty lines for Cylinder B whatever Rows is.
        status, error = post([''] * 4, {'grid_rows': 2}, plate='negative')
        assert (status, error) == (200, '')

    def test_content_past_rows_is_refused_not_dropped(self):
        with pytest.raises(ValidationError, match='Maximum is 2 lines'):
            validate_lines(['⠁', '', '⠃'], 2)

    def test_the_ceiling_is_the_dials_200(self):
        validate_lines([''] * 200, 4)
        with pytest.raises(ValidationError, match='Maximum is 200 lines'):
            validate_lines([''] * 201, 4)

    def test_original_lines_follow_rows(self):
        validate_original_lines(['a'] * 5, 5)
        with pytest.raises(ValidationError, match='Maximum is 3'):
            validate_original_lines(['a', 'b', 'c', 'd'], 3)


class TestExtent:
    def test_the_dots_reach_from_the_widest_dot_or_bowl(self):
        # 4 rows, line spacing 10: top row 15 mm up, dot 1 2.5 above it, bowl radius 0.9
        extent = braille_rows_extent(settings(grid_rows=4), 52)
        assert extent['dots_top'] == pytest.approx(18.4)
        assert extent['dots_bottom'] == pytest.approx(-18.4)
        assert extent['arrows_top'] is None

    def test_the_arrow_recess_has_a_mitred_tip(self):
        # The recess is the arrow grown 0.2 mm; its tip moves 0.2 / sin(atan(2 / 10)) = 1.02 mm.
        extent = braille_rows_extent(settings(grid_rows=4, indicator_mode='tactile'), 52)
        assert extent['arrows_top'] == pytest.approx(15 + 5 + 1.0198, abs=1e-4)
        assert extent['arrows_bottom'] == pytest.approx(-15 - 5 - 0.2)

    def test_y_adjust_moves_every_row(self):
        extent = braille_rows_extent(settings(grid_rows=4, braille_y_adjust=3.0), 52)
        assert extent['dots_top'] == pytest.approx(21.4)
        assert extent['dots_bottom'] == pytest.approx(-15.4)


class TestFit:
    @pytest.mark.parametrize('rows', [1, 4, 5])
    def test_visual_rows_that_fit_52_mm(self, rows):
        assert validate_braille_rows_fit(settings(grid_rows=rows), 'cylinder', V1_BARREL)

    def test_six_visual_rows_run_off_52_mm(self):
        with pytest.raises(ValidationError) as caught:
            validate_braille_rows_fit(settings(grid_rows=6), 'cylinder', V1_BARREL)
        assert str(caught.value) == (
            "These 6 rows need 56.8 mm of the cylinder's 52 mm height, so the top and bottom rows would run "
            'off the ends. Use fewer rows, a smaller line spacing, or a taller cylinder.'
        )

    def test_five_tactile_rows_notch_the_52_mm_rim(self):
        assert validate_braille_rows_fit(settings(grid_rows=4, indicator_mode='tactile'), 'cylinder', V1_BARREL)
        with pytest.raises(ValidationError, match="These 5 rows need 52.04 mm of the cylinder's 52 mm height"):
            validate_braille_rows_fit(settings(grid_rows=5, indicator_mode='tactile'), 'cylinder', V1_BARREL)

    def test_the_card_bounds_the_dots_on_the_54_mm_barrel(self):
        assert validate_braille_rows_fit(settings(grid_rows=5, indicator_mode='tactile'), 'cylinder', V2_BARREL)
        with pytest.raises(ValidationError) as caught:
            validate_braille_rows_fit(settings(grid_rows=6), 'cylinder', V2_BARREL)
        assert str(caught.value) == (
            "These 6 rows need 56.8 mm of the card's 52 mm height, so the top and bottom rows would run off "
            'the card. Use fewer rows or a smaller line spacing.'
        )

    def test_a_smaller_line_spacing_fits_more_rows(self):
        assert validate_braille_rows_fit(settings(grid_rows=6, line_spacing=9.0), 'cylinder', V1_BARREL)

    def test_y_adjust_can_push_rows_off(self):
        with pytest.raises(ValidationError, match='These 4 rows need 56.8 mm'):
            validate_braille_rows_fit(settings(grid_rows=4, braille_y_adjust=10.0), 'cylinder', V1_BARREL)

    def test_the_three_arrow_layout_keeps_its_own_gate(self):
        # three_spaced arrows are not row markings; only the dots are measured here.
        three = settings(grid_rows=5, indicator_mode='tactile', tactile_indicator_layout='three_spaced')
        assert braille_rows_extent(three, 52)['arrows_top'] is None
        assert validate_braille_rows_fit(three, 'cylinder', V1_BARREL)

    def test_cards_are_not_measured(self):
        assert validate_braille_rows_fit(settings(grid_rows=12), 'card', {})

    def test_the_http_refusal_carries_the_sentence(self):
        status, error = post([''] * 6, {'grid_rows': 6})
        assert status == 400
        assert error.startswith('These 6 rows need 56.8 mm')
