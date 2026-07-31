"""
Guards the vendored OpenSCAD copy in OpenSCAD/ against silent drift.

OpenSCAD/ is a verbatim copy of a tagged release of the standalone repo
braille-cylinder-stl-generator-openscad. It exists so a web app visitor can
download the offline version without leaving the site; it is not a fork, and
nothing in it should ever be edited here.

The failure mode this catches is the one that actually happened: someone
tweaks a vendored file in place, or the copy quietly ages past the release it
claims to be, and the two versions diverge with no record of it. So:

- every vendored file must hash to exactly what VENDORED.json records, and
- VENDORED.json must stay complete and internally consistent with the tree.

The hash check originally covered only the .scad, which let a wording edit to
two of the vendored docs ride along unnoticed while the .scad failure was the
only thing CI reported. Every file carries a hash now.

Neither check can tell you whether a *newer* upstream release exists — that
needs the network. Refreshing the copy is a release-checklist step; see
docs/deployment/DEPLOYMENT_CHECKLIST.md.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = REPO_ROOT / 'OpenSCAD'
PROVENANCE_FILE = VENDOR_DIR / 'VENDORED.json'
SCAD_NAME = 'Braille_Cylinder_STL_Generator.scad'


def _load_provenance():
    if not PROVENANCE_FILE.exists():
        return None
    return json.loads(PROVENANCE_FILE.read_text(encoding='utf-8'))


# Read at import time so each vendored file gets its own test case, which keeps
# a failure naming the file that drifted rather than the first one checked.
PROVENANCE = _load_provenance()
RECORDED_FILES = sorted(PROVENANCE['files']) if PROVENANCE else []


@pytest.fixture(scope='module')
def provenance():
    assert PROVENANCE is not None, (
        f'{PROVENANCE_FILE.relative_to(REPO_ROOT)} is missing. The vendored '
        'OpenSCAD copy must record which upstream tag it came from.'
    )
    return PROVENANCE


@pytest.mark.parametrize('relative_path', RECORDED_FILES)
def test_vendored_file_matches_recorded_hash(provenance, relative_path):
    """
    Every vendored file must be byte-identical to what VENDORED.json records.

    A mismatch means either the file was edited here (don't — edit upstream and
    re-vendor) or the copy was refreshed without updating VENDORED.json.

    For a file whose record carries an 'edited on copy' note the hash is of the
    adjusted copy, not of upstream, so this still catches drift either way.
    """
    vendored = VENDOR_DIR / relative_path
    assert vendored.exists(), f'{relative_path} is recorded in VENDORED.json but missing from OpenSCAD/'

    expected = provenance['files'][relative_path].get('sha256')
    assert expected, (
        f'VENDORED.json records {relative_path} without a sha256. Every '
        'vendored file needs one, otherwise it can be edited here without any '
        'check noticing.'
    )

    actual = hashlib.sha256(vendored.read_bytes()).hexdigest()
    assert actual == expected, (
        f'{relative_path} does not match the hash recorded in VENDORED.json '
        f'for upstream {provenance["upstream_tag"]}.\n'
        f'  recorded: {expected}\n'
        f'  actual:   {actual}\n'
        'Do not edit the vendored copy. Change it upstream in '
        'braille-cylinder-stl-generator-openscad, tag a release, then re-vendor '
        'and update VENDORED.json.'
    )


def test_the_scad_itself_is_still_vendored(provenance):
    """
    The per-file hash checks only cover what VENDORED.json happens to list, so
    they would all pass if the .scad were dropped from the folder and the
    record at the same time. It is the one file the folder exists to ship.
    """
    assert SCAD_NAME in provenance['files'], f'VENDORED.json no longer records {SCAD_NAME}'
    assert (VENDOR_DIR / SCAD_NAME).exists(), f'{SCAD_NAME} is missing from OpenSCAD/'


def test_every_vendored_file_is_recorded(provenance):
    """
    VENDORED.json must account for every file in OpenSCAD/, so a reader can
    tell at a glance that nothing in the folder is locally authored.
    """
    on_disk = {p.relative_to(VENDOR_DIR).as_posix() for p in VENDOR_DIR.rglob('*') if p.is_file()}
    # The provenance file and the folder README describe the vendoring itself
    # rather than being vendored artifacts.
    on_disk -= {'VENDORED.json', 'README.md'}
    recorded = set(provenance['files'])

    unrecorded = on_disk - recorded
    assert not unrecorded, (
        'Files in OpenSCAD/ are not listed in VENDORED.json: '
        f'{sorted(unrecorded)}. Add them with their upstream path, or delete '
        'them if they are not part of the vendored release.'
    )

    missing = recorded - on_disk
    assert not missing, f'VENDORED.json lists files that are not in OpenSCAD/: {sorted(missing)}.'


def test_provenance_records_a_resolvable_upstream_release(provenance):
    """
    'Vendored from somewhere, sometime' is useless. The record needs a repo, a
    tag, a full commit sha, and the date it was copied.
    """
    assert provenance['upstream_repo'].endswith('braille-cylinder-stl-generator-openscad'), (
        f'upstream_repo must point at the standalone OpenSCAD repo, got {provenance["upstream_repo"]}'
    )
    assert re.fullmatch(r'v\d+\.\d+\.\d+', provenance['upstream_tag']), (
        f'upstream_tag must be a release tag like v2.4.0, got {provenance["upstream_tag"]}'
    )
    assert re.fullmatch(r'[0-9a-f]{40}', provenance['upstream_commit']), (
        'upstream_commit must be a full 40-character sha so the exact tree can '
        f'be recovered even if the tag moves, got {provenance["upstream_commit"]}'
    )
    for field in ('vendored_on', 'upstream_release_date'):
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', provenance[field]), (
            f'{field} must be an ISO date, got {provenance[field]}'
        )


def test_readme_states_upstream_is_canonical(provenance):
    """
    The old vendored README claimed the standalone repo was 'no longer the
    active home for this project', which sent contributors to the wrong place.
    Keep the correction and the tag visible in the README, not only in JSON.
    """
    readme = (VENDOR_DIR / 'README.md').read_text(encoding='utf-8')
    assert 'vendored copy' in readme.lower(), (
        'OpenSCAD/README.md must say up front that this folder is a vendored copy, not the source of truth'
    )
    assert 'braille-cylinder-stl-generator-openscad' in readme, (
        'OpenSCAD/README.md must name the canonical upstream repo'
    )
    assert provenance['upstream_tag'] in readme, (
        f'OpenSCAD/README.md must state the vendored tag '
        f'({provenance["upstream_tag"]}); a reader should not have to open '
        'VENDORED.json to learn how old this copy is'
    )
