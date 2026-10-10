"""Write the index of the vendored liblouis 3.39.0 tables.

    python scripts/build_liblouis_tables_index.py

Output (regenerate ONLY with this script):
    static/vendor/liblouis-3.39.0/tables.json

For every file in static/vendor/liblouis-3.39.0/tables/ it records the size
and SHA-256 (tests/test_vendored_liblouis.py checks the bytes against them)
and the include closure: the files liblouis reads to compile that table, the
table itself first, so the worker can fetch them all before a table's first
translation. An include that names a file the release does not ship is listed
under "missing" for that table. The include parsing and the closure walk are
ported from openscad-assistive-forge scripts/setup-liblouis.js (parseIncludes,
resolveTableClosure; 4355e8a), the same author's code.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'static' / 'vendor' / 'liblouis-3.39.0'
TABLES = VENDOR / 'tables'
INCLUDE = re.compile(r'^\s*include\s+(\S+)')


def includes(path: Path) -> list[str]:
    names = []
    for line in path.read_bytes().decode('utf-8', errors='replace').splitlines():
        match = INCLUDE.match(line)
        if match:
            names.append(match.group(1))
    return names


def closure(seed: str) -> tuple[list[str], list[str]]:
    seen: list[str] = []
    missing: list[str] = []
    queue = [seed]
    while queue:
        name = queue.pop(0)
        if name in seen or name in missing:
            continue
        path = TABLES / name
        if not path.is_file():
            missing.append(name)
            continue
        seen.append(name)
        queue.extend(includes(path))
    return seen, sorted(missing)


def main() -> None:
    names = sorted(path.name for path in TABLES.iterdir() if path.is_file())
    files = {}
    closures = {}
    missing = {}
    for name in names:
        data = (TABLES / name).read_bytes()
        files[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        found, absent = closure(name)
        closures[name] = found
        if absent:
            missing[name] = absent
    index = {
        'liblouis': '3.39.0',
        'source': 'liblouis-3.39.0-win64.zip (official release), share/liblouis/tables',
        'files': files,
        'closures': closures,
        'missing': missing,
    }
    (VENDOR / 'tables.json').write_text(json.dumps(index, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{len(files)} tables, {len(missing)} with missing includes -> {VENDOR / "tables.json"}')


if __name__ == '__main__':
    main()
