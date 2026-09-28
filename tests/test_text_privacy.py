"""
Text-input privacy (Brennen, 2026-09-28): no text or braille input is ever
persisted - only 3D design settings are. Before this date the Back of Card
text was saved under braille_prefs_back_text and restored on the next visit
while the front text was not. This pins the page's source: no persistence
call names a text or braille key, the old key is scrubbed on load, and the
text-entry placeholders are in place.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HTML = (REPO / 'public' / 'index.html').read_text(encoding='utf-8')

TEXT_KEYS = r'braille_prefs_(?:back_text|auto_text|line\d+|back_line\d+|braille_unicode|back_braille_unicode|braille)\b'


def test_no_text_or_braille_input_is_persisted():
    writes = re.findall(rf"(?:persistValue|localStorage\.setItem|sessionStorage\.setItem)\(\s*'{TEXT_KEYS}", HTML)
    assert writes == [], writes
    reads = re.findall(rf"(?:readPersisted|localStorage\.getItem)\(\s*'{TEXT_KEYS}", HTML)
    assert reads == [], reads


def test_the_old_back_text_key_is_scrubbed_on_load_and_by_reset():
    assert "localStorage.removeItem('braille_prefs_back_text')" in HTML
    assert "'braille_prefs_back_text'," in HTML  # still in the Reset list, so older values go too


def test_the_text_boxes_carry_the_sample_and_the_braille_boxes_its_translation():
    assert 'placeholder="Input your text information here."' in HTML
    front = re.search(r'id="braille-unicode"[^>]*placeholder="([^"]+)"', HTML, re.S)
    back = re.search(r'id="back-braille-unicode"[^>]*placeholder="([^"]+)"', HTML, re.S)
    assert front and back
    for placeholder in (front.group(1), back.group(1)):
        rows = placeholder.split('&#10;')
        assert 1 < len(rows) <= 4
        for row in rows:
            assert row and all(ch == ' ' or 0x2800 <= ord(ch) <= 0x28FF for ch in row), row
            assert len(row) <= 13
    assert '--text-placeholder:' in HTML
    assert 'textarea::placeholder' in HTML
