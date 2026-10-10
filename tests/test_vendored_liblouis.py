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


def _table_list(client):
    response = client.get('/liblouis/tables')
    assert response.status_code == 200
    return response.get_json()['tables']


def test_the_table_list_offers_every_usable_translation_table_once(client):
    """/liblouis/tables (the language dropdown) offers each 3.39.0 translation
    table liblouis describes (a #-display-name), and each undescribed one that no
    described table includes (decision M1, 2026-10-09): 252 + 13. The 58 left out
    are building blocks of a described table, such as en-GB-g2.ctb inside
    en_GB.tbl. No include file, nothing from the 3.2.0 or native 3.34.0 folders,
    and every table offered was compared with native 3.39.0 (decision E2)."""
    import json

    index = json.loads((VENDOR / 'tables.json').read_text(encoding='utf-8'))
    reference_path = Path(__file__).resolve().parent / 'fixtures' / 'liblouis-reference' / 'table-samples-3.39.0.json'
    verified = json.loads(reference_path.read_text(encoding='utf-8'))['tables']
    tables = _table_list(client)
    files = [table['file'] for table in tables]

    assert len(files) == len(set(files)) == 265
    assert sum(1 for table in tables if table['display_name']) == 252
    assert set(files) <= set(verified)
    translation_tables = {name for name in index['closures'] if name.endswith(('.ctb', '.utb', '.tbl'))}
    left_out = translation_tables - set(files)
    assert len(left_out) == 58
    described = [table['file'] for table in tables if table['display_name']]
    included = {part for name in described for part in index['closures'][name][1:]}
    assert left_out <= included
    assert {'en_GB.tbl', 'en-ueb-g2.ctb', 'en-ueb-g1.ctb', 'en-us-g1.ctb', 'sin.utb', 'ks-in-g1.utb'} <= set(files)
    # en-us-g2.ctb is a building block of en_US.tbl; the page still offers it as a default.
    for absent in ('en-GB-g2.ctb', 'en-us-g2.ctb', 'fr-fr-g1.utb', 'UEBC-g2.ctb', 'de-de-accents.cti'):
        assert absent not in files


def test_each_table_carries_its_own_liblouis_metadata(client):
    """The fields come from the table's opening '#-' / '#+' lines, null where it
    gives none; file, path, locale and description keep their earlier meaning."""
    by_file = {table['file']: table for table in _table_list(client)}
    for table in by_file.values():
        assert table['path'] == table['description'] == table['file']
    assert by_file['en-ueb-g2.ctb'] == {
        'file': 'en-ueb-g2.ctb',
        'path': 'en-ueb-g2.ctb',
        'locale': 'en-ueb',
        'description': 'en-ueb-g2.ctb',
        'display_name': 'Unified English contracted braille',
        'index_name': 'English, unified, contracted',
        'language': 'en',
        'region': None,
        'type': 'literary',
        'grade': '2',
        'contraction': 'full',
        'dots': None,
    }
    assert by_file['en_GB.tbl']['display_name'] == 'English contracted braille as used in the U.K.'
    assert by_file['en_GB.tbl']['region'] == 'en-GB'
    assert by_file['en_GB.tbl']['locale'] is None
    assert by_file['de-g2.ctb']['display_name'] == 'German contracted braille'
    assert by_file['de-g2.ctb']['index_name'] == 'German, contracted'
    assert by_file['no-no-comp8.ctb']['dots'] == 8
    assert by_file['no-no-comp8.ctb']['type'] == 'computer'
    assert all(value is None for key, value in by_file['sin.utb'].items() if key not in ('file', 'path', 'description'))
