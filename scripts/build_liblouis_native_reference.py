"""Record what native liblouis 3.39.0 writes for every vendored translation table.

    python scripts/build_liblouis_native_reference.py --native <liblouis-3.39.0-win64 folder>

Output (regenerate ONLY with this script, from the official release build):
    tests/fixtures/liblouis-reference/table-samples-3.39.0.json

For each .ctb, .utb and .tbl file in static/vendor/liblouis-3.39.0/tables/ it
runs the release's own lou_translate on SAMPLES with the table chain
"unicode.dis,<table>" and the vendored tables, and keeps one line of braille
per sample, every blank cell written as the ASCII space the app carries
(project-facts invariant 4; 3.39.0 writes U+2800). A table the native engine
cannot compile is recorded as {"error": ...}. tests/frontend/
liblouis-engine.test.js then requires the vendored WebAssembly build to give
the same cells, table by table (Brennen's decision E2, 2026-10-09: compare
every table against native 3.39.0). It proves the build and the shipped
tables match upstream, not that upstream's braille is right for a language.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / 'static' / 'vendor' / 'liblouis-3.39.0' / 'tables'
OUT = ROOT / 'tests' / 'fixtures' / 'liblouis-reference' / 'table-samples-3.39.0.json'
# Latin with capitals, digits and punctuation; accented Latin; three other scripts.
SAMPLES = ['Hello World 123.', 'café naïve', 'Ελληνικά Русский 中文']
BLANK = chr(0x2800)


def native_translate(exe: Path, table: str) -> dict | list:
    env = {**os.environ, 'LOUIS_TABLEPATH': str(TABLES)}
    result = subprocess.run(
        [str(exe), f'unicode.dis,{table}'],
        input=('\n'.join(SAMPLES) + '\n').encode('utf-8'),
        capture_output=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        return {'error': result.stderr.decode('utf-8', errors='replace').strip().splitlines()[-1:]}
    lines = result.stdout.decode('utf-8').splitlines()
    if len(lines) != len(SAMPLES):
        return {'error': [f'{len(lines)} lines for {len(SAMPLES)} samples']}
    return [line.replace(BLANK, ' ') for line in lines]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--native', required=True, help='the unpacked liblouis-3.39.0-win64 release folder')
    native = Path(parser.parse_args().native)
    exe = native / 'bin' / 'lou_translate.exe'
    tables = sorted(path.name for path in TABLES.iterdir() if path.suffix in ('.ctb', '.utb', '.tbl'))
    reference = {
        'liblouis': '3.39.0',
        'engine': 'lou_translate.exe from liblouis-3.39.0-win64.zip (official release)',
        'samples': SAMPLES,
        'tables': {table: native_translate(exe, table) for table in tables},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(reference, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    failed = sum(1 for value in reference['tables'].values() if isinstance(value, dict))
    print(f'{len(tables)} tables, {failed} the native engine cannot compile -> {OUT}')


if __name__ == '__main__':
    main()
