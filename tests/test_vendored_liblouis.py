"""
The vendored liblouis 3.39.0 engine and tables (the engine round, plan
05_LIBLOUIS_3_39_UPGRADE_PLAN, decisions E1-E6 of 2026-10-09).

static/vendor/liblouis-3.39.0/ holds the WebAssembly build copied byte for
byte from openscad-assistive-forge 4355e8a and the 3.39.0 release's tables.
Nothing there may be edited by hand: each file is checked against the size
and SHA-256 its README.txt records, so a changed byte fails here first.
"""

import hashlib
import re
from pathlib import Path

VENDOR = Path(__file__).resolve().parents[1] / 'static' / 'vendor' / 'liblouis-3.39.0'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_engine_files_are_the_recorded_bytes():
    readme = (VENDOR / 'README.txt').read_text(encoding='utf-8')
    recorded = re.findall(r'^\s+(\S+)\s+(\d+) bytes\s+sha256 ([0-9a-f]{64})$', readme, re.MULTILINE)
    assert sorted(name for name, _, _ in recorded) == ['liblouis.js', 'liblouis.wasm']
    for name, size, digest in recorded:
        path = VENDOR / name
        assert path.stat().st_size == int(size), name
        assert _sha256(path) == digest, name


def test_the_lgpl_text_ships_beside_the_engine():
    assert 'GNU LESSER GENERAL PUBLIC LICENSE' in (VENDOR / 'COPYING.LESSER.liblouis').read_text(encoding='utf-8')


def test_every_table_is_the_recorded_bytes_and_nothing_else_ships():
    import json

    index = json.loads((VENDOR / 'tables.json').read_text(encoding='utf-8'))
    assert index['liblouis'] == '3.39.0'
    shipped = sorted(path.name for path in (VENDOR / 'tables').iterdir())
    assert shipped == sorted(index['files'])
    assert len(shipped) == 478
    for name, record in index['files'].items():
        path = VENDOR / 'tables' / name
        assert path.stat().st_size == record['bytes'], name
        assert _sha256(path) == record['sha256'], name


def test_every_tables_include_closure_ships():
    import json

    index = json.loads((VENDOR / 'tables.json').read_text(encoding='utf-8'))
    assert index['missing'] == {}
    for name, closure in index['closures'].items():
        assert closure[0] == name
        assert set(closure) <= set(index['files']), name
    # The forge ships exactly this closure for contracted UEB.
    assert set(index['closures']['en-ueb-g2.ctb']) == {
        'en-ueb-g2.ctb',
        'en-ueb-g1.ctb',
        'en-ueb-chardefs.uti',
        'en-ueb-math.ctb',
        'braille-patterns.cti',
        'text_nabcc.dis',
        'spaces.uti',
        'latinLetterDef6Dots.uti',
        'latinUppercaseComp6.uti',
    }


def test_the_table_list_offers_exactly_the_translation_tables_verified_against_native(client):
    """/liblouis/tables (the language dropdown) lists the 3.39.0 translation
    tables and nothing else: no include file (.cti, .uti, .dis, .dic) and no
    table from the 3.2.0 or native 3.34.0 folders it scanned before phase 7,
    which the worker cannot load. Each listed table is one the engine was
    compared with native 3.39.0 on (decision E2)."""
    import json

    index = json.loads((VENDOR / 'tables.json').read_text(encoding='utf-8'))
    reference_path = Path(__file__).resolve().parent / 'fixtures' / 'liblouis-reference' / 'table-samples-3.39.0.json'
    verified = json.loads(reference_path.read_text(encoding='utf-8'))['tables']

    response = client.get('/liblouis/tables')
    assert response.status_code == 200
    tables = response.get_json()['tables']
    files = [table['file'] for table in tables]

    translation_tables = sorted(name for name in index['closures'] if name.endswith(('.ctb', '.utb', '.tbl')))
    assert sorted(files) == translation_tables == sorted(verified)
    assert len(files) == 323
    assert {'en-ueb-g2.ctb', 'en-ueb-g1.ctb', 'en-us-g2.ctb', 'en-us-g1.ctb'} <= set(files)
    for gone in ('fr-fr-g1.utb', 'UEBC-g2.ctb', 'de-de-accents.cti'):
        assert gone not in files
    for table in tables:
        assert table['path'] == table['file']
        assert table['description'] == table['file']
    by_file = {table['file']: table for table in tables}
    assert by_file['en-ueb-g2.ctb']['locale'] == 'en-ueb'
    assert by_file['en_US.tbl']['locale'] is None
