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
