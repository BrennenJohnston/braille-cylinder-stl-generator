# Verification Guide

How to check that the app still works after a change. Everything here is a command you can
run yourself, with the result you should expect.

Run these from the repo root:
`C:\Users\WATAP\Documents\github\braille-cylinder-stl-generator`

**Read the output text, never the exit code.** Some tools in this project exit 0 while
reporting failures.

---

## 1. The named checks (always run these)

These two are the bar for any change. Both must be clean before you commit.

```bash
python -m ruff check .
python -m pytest tests/ -v
```

Expected, measured 2026-09-30:

| Command | Expected result |
|---------|-----------------|
| `python -m ruff check .` | `All checks passed!` |
| `python -m ruff format --check .` | every file already formatted (CI runs this too) |
| `python -m pytest tests/ -v` | `744 passed, 4 skipped` in about a minute |

### The fast loop

While you are working, this one takes well under a second:

```bash
python -m pytest tests/test_smoke.py -q
```

Expected: `52 passed`.

Use it between edits, but run the full suite before you commit — the smoke file is 52 of
the 748 tests and does not cover geometry or the vendored OpenSCAD copy.

---

## 2. What the Python suite covers

| Test file | What it protects |
|-----------|------------------|
| `tests/test_smoke.py` | Settings defaults, schema/model agreement, validation, braille-to-dots conversion |
| `tests/test_golden.py` | Geometry output, compared against saved STL fixtures |
| `tests/test_interpoint_math.py` | The double-sided pairing mirror and back-grid offset |
| `tests/test_double_sided_validation.py` | The double-sided validation gates |
| `tests/test_vendored_openscad.py` | That the vendored `OpenSCAD/` copy has not been edited here |

### Golden fixtures

`tests/test_golden.py` compares generated geometry against saved STL files in
`tests/fixtures/`:

| Fixture | What it pins |
|---------|--------------|
| `card_positive_small.stl`, `card_counter_small.stl` | Flat card plates (feature parked, fixtures kept) |
| `cylinder_positive_small.stl`, `cylinder_counter_small.stl` | Single-sided cylinder plates |
| `ds_cylinderA_golden.stl`, `ds_cylinderB_golden.stl` | The double-sided Cylinder A / Cylinder B pair |
| `gear_rollerA_golden.stl`, `gear_rollerB_golden.stl` | The Version 1 fused (Simplified gears) rollers, vented since 2026-09-30 |
| `v2_cylinderA_golden.stl`, `v2_cylinderB_golden.stl` | The Version 2 keyed cylinders |
| `v2_gear_rollerA_golden.stl`, `v2_gear_rollerB_golden.stl` | The Version 2 fused rollers |

**A golden test failing means the geometry changed.** That is either a bug you just
introduced, or a deliberate change. Never edit or regenerate a fixture to make a red test go
green unless you meant to change the geometry — and say why in the commit message.

When you *do* mean to change it, regenerate the double-sided pair with:

```bash
python -m tests.test_golden
```

That is the only supported way to regenerate the `ds_` pair. It rebuilds both STL files and
their JSON metadata from the current code.

---

## 3. End-to-end browser tests

```bash
npx playwright test tests/e2e/ --project=chromium --project=firefox
```

Expected: **334 tests, 2 of them skipped by design**, in about 15 minutes. Measured
2026-09-30 on Windows: 322 passed, 2 skipped, 10 failed under full parallel load — every
failed file passed again on its own with `--workers=2`, except a known local Firefox
failure in `brailleFieldAutoFill.spec.ts` (see [KNOWN_ISSUES.md](../KNOWN_ISSUES.md)).
CI (Linux, one worker, two retries) passes all three browsers.

Chromium + Firefox is the local pass bar. Two notes on what you may see:

- **If a test fails with `Liblouis worker not initialized` or `requires the Manifold 3D
  engine`, it pressed a button before that worker was up.** Firefox is slower to start both
  under parallel load, and locally Playwright runs many workers with **no retries** (CI runs
  one worker with two retries, which is why this class of failure hides on CI). The fix is
  never a blanket retry: press through the helper that waits for readiness and rethrows
  anything else — `previewBraille`, `generateBoth`, and `generateFully` in
  `tests/e2e/doubleSided.spec.ts` are the working examples. A test that presses a
  worker-backed button bare is the bug.
- **WebKit on Windows is not a known failure any more.** This note used to say it fails
  for environmental reasons; re-measured on 2026-08-21 it passed, and
  [KNOWN_ISSUES.md](../KNOWN_ISSUES.md) records the correction. The local pass bar is still
  Chromium + Firefox, and CI runs WebKit on Linux.

---

## 4. Server smoke check

Start the app:

```bash
python backend.py
```

Expected: `Running on http://127.0.0.1:5001`. Open <http://localhost:5001>.

Port 5001 is not optional for local work — `backend.py`'s CORS allowlist only accepts
`localhost:5001` and `127.0.0.1:5001`.

Health check:

```bash
curl http://localhost:5001/health
```

Expected: `{"status":"ok","timestamp":"..."}`.

Geometry spec endpoint — this is what the browser calls before generating an STL:

```bash
curl -X POST http://localhost:5001/geometry_spec \
  -H "Content-Type: application/json" \
  -d "{\"lines\": [\"\u2801\", \"\", \"\", \"\"], \"plate_type\": \"positive\", \"shape_type\": \"cylinder\", \"grade\": \"g1\", \"settings\": {}}"
```

`\u2801` is the braille letter A, written as a JSON escape on purpose: pasting the braille
character itself into a Windows terminal mangles it to `?`, and the endpoint then correctly
rejects it with "is not a valid braille character" — a confusing failure that looks like an
app bug but is really the terminal's encoding.

Expected: a JSON geometry specification, opening with the cylinder block and a list of dots.
The browser hands that to a Web Worker, which does the actual STL generation.

The old `/generate_braille_stl` endpoint returns **410 Gone**. STL generation has been
client-side only since v2.0.0.

---

## 5. Manual check in the browser

With the app open at <http://localhost:5001>:

- The page loads and you can type text
- Type `hello`, press **Generate STL**, and a 3D preview appears
- A **Download STL** button appears beside Generate; pressing it saves the file
- The saved file opens in a 3D viewer (Blender, MeshLab, your slicer)

### Double-sided check

Worth running whenever you touch double-sided cards, the workers, or the download flow:

1. Under **Embosser setup**, choose **Double-sided** in **Card sides**
2. Confirm the **Back of Card** section becomes active and Row Indicator Style (Expert
   Mode) locks to tactile
3. Type `abc` in the front text box and `def` in **Back of Card Text**
4. Open Expert Mode and press **Preview Braille Translation** — the panel shows both a
   **Front of Card** and a **Back of Card** heading with braille under each
5. Press **Generate STL** — one press builds both cylinders
6. Confirm **nothing downloads by itself**
7. Press **Download STL**

Expect exactly one file, `Cylinder_Pair_*.stl`, holding Cylinder A and Cylinder B side by
side and named from the **front** text. To check the single files, choose Cylinder A, then
Cylinder B, under **Expert Mode → Cylinders to Generate** and generate each: they download
as `Cylinder_A_*.stl` and `Cylinder_B_*.stl`.

---

## 6. Accessibility

UI changes have their own procedure — the checks above do not cover accessibility.

Follow [ADA_ACCESSIBILITY_VALIDATION_SOP.md](../development/ADA_ACCESSIBILITY_VALIDATION_SOP.md):
W3C validator at 0 errors, Lighthouse accessibility at 100, contrast at 4.5:1 for text and
3:1 for UI components, and accordions keeping `aria-expanded` and `aria-controls` current.

Automated tools do not catch everything. Three defects in this app's live regions scored
100/100 on Lighthouse and were only found by listening with a screen reader — see
[NVDA_DOUBLE_SIDED_WALKTHROUGH.md](../development/NVDA_DOUBLE_SIDED_WALKTHROUGH.md).

---

## 7. If something fails

**A test fails.** Re-run just that test with more detail:

```bash
python -m pytest tests/test_smoke.py -v --tb=long
```

**Imports fail.** Check you are in the repo root, and that dependencies are installed:
`pip install -r requirements-dev.txt`.

**The server will not start.** Something else may be on port 5001:

```bash
netstat -ano | findstr :5001
```

**A commit fails with "files were modified by this hook".** Expected — the pre-commit hooks
fixed your files. Run `git add -A` and commit again; the second attempt succeeds.

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025 | Original guide, written for the Phase 0 / Phase 1.1 refactor (13 tests) |
| 2.0 | 2026-08-18 | Full rewrite to current reality: the named checks and their real counts (ruff clean, 119 pytest, 30 smoke), the e2e bar at 104 tests, golden fixtures including the double-sided pair and how to regenerate it, port 5001, the double-sided end-to-end check, and a pointer to the accessibility SOP |
| 2.1 | 2026-09-30 | Counts re-measured after the approved build (744 pytest + 4 skipped, 52 smoke, 334 e2e in Chromium + Firefox) and `ruff format --check` added; the double-sided check follows the Card sides choice and the one Generate / one Download flow; the golden table lists all four pairs; the WebKit note follows KNOWN_ISSUES' 2026-08-21 correction. |

---

## Related Documents

- [Specifications Index](SPECIFICATIONS_INDEX.md)
- [Known Issues](../KNOWN_ISSUES.md)
- [ADA Accessibility Validation SOP](../development/ADA_ACCESSIBILITY_VALIDATION_SOP.md)
- [Interpoint (Double-Sided) Specifications](INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md)
