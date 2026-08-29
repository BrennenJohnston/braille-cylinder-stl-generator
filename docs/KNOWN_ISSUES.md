# Known Issues

## Double-sided (interpoint) beta — status

The Double-Sided Card (BETA) toggle is **feature-complete and physically validated**. In
August 2026 two rounds of Cylinder A / Cylinder B pairs were printed on a Bambu Lab X1C with
a 0.4 mm nozzle and used to emboss real card stock; the braille came out legible on **both**
faces. The dot and bowl sizes it ships with (dot 1.2 mm across, bowl 1.3 mm across × 0.5 mm
deep, back grid offset 1.25 mm diagonally) are therefore final — there are no size dials to
tune.

What the finished beta does:

- Turning the toggle on reveals a **Back of Card** section and locks the Row Indicator Style
  to the tactile seam arrow, which both cylinders of a pair need.
- Back text has the same handling as front text: translated with the same language and
  grade, wrapped across the rows for you with whole words kept together, and warned about
  live while you type if it overruns.
- The braille preview shows **both sides**, under Front of Card and Back of Card headings.
- **Generate Both Cylinders (A and B)** builds the whole pair from one press.
- Each file is then saved by pressing its own button — **Download Cylinder A** and
  **Download Cylinder B**. Nothing downloads by itself.

It keeps the BETA label because it has been proven by one builder on one printer with one
paper stock, not because anything is known to be wrong with it.

Two caveats remain:

- **Rotational sync is a mechanical requirement, not a software one.** The two cylinders
  have to stay within about **1.0 degree** of each other as they turn. Further out of
  phase than that and a front dot can meet the back of the card where its paired bowl is
  not, so the emboss degrades. Nothing in this app can enforce that — it belongs to
  whoever builds and aligns the machine.
- ~~**Local WebKit end-to-end tests fail on Windows.**~~ **Not reproducible — corrected
  2026-08-21.** This entry used to say that running the suite locally against WebKit on
  Windows "fails almost everything", citing 41 failed / 6 passed / 5 skipped of 52 on
  2026-08-18. A full run the same day passed everything, so one of the two numbers was
  always wrong. Re-measured deliberately on 2026-08-21, three consecutive runs on this
  machine: **56 passed, 5 skipped, 0 failed** every time (61 tests — the suite has grown
  since the 52 quoted above). The five skips are deliberate `test.skip()` calls, not
  errors: four WebGL-degradation tests and one scrollbar test that the suite excludes on
  WebKit by design.

  The local pass bar is still Chromium + Firefox, and CI still runs WebKit on Linux. The
  original 41-failure reading has no surviving evidence; a whole-suite collapse of that
  shape is what the stale-server trap below produces, which remains the most likely
  explanation but cannot now be confirmed. The per-test fill flake described below is a
  second known cause of spurious local failures, though it would not by itself take down
  41 tests at once.

**A leftover server on port 5001 used to hijack local runs (fixed 2026-08-21).**
`playwright.config.ts` set `reuseExistingServer: !process.env.CI`, so locally any server
already holding port 5001 — a `backend.py` left over from another checkout, a worktree, or
an interrupted run — was silently adopted, and the suite then tested *that* tree's code
while your own files looked correct. Reproduced on 2026-08-21 by staging a pre-fix server
on 5001: `tactileIndicator.spec.ts:123` failed with "Expected: 10, Received: 5" against a
working tree that already had the fix. CI never saw it, because CI set the flag to `false`.
The setting is now `false` unconditionally, so a busy port is a loud error instead of a
silent substitution. If a run now fails to start, something else is on 5001 — find it with
`netstat -ano | findstr :5001` and stop it.

**The suite had a second, unrelated flake, also fixed 2026-08-22.** The stale
server was a real cause and was reproduced, but it was not the only one: a single
Playwright `fill()` on `#braille-unicode` does not always land under full-suite
parallelism, which surfaced as an intermittent "Please enter text in at least one
line" from `generate()` - most often at `tests/e2e/tactileIndicator.spec.ts:123`,
the same test the stale server also broke, which is how the two got conflated.
It is NOT the app clearing the field: instrumenting the textarea's `value` setter
to record every write caught a run that ended empty with **zero writes**, so
nothing in page script touched it. All fourteen braille fills across five specs
now go through a `fillBraille()` helper that verifies the text landed and re-fills
if it did not, failing with a named message rather than a confusing downstream one.

Two related traps were fixed in the same pass. `generate()` read `#error-text`
and treated anything there as fatal, but that element also carries
**informational** notices - the card-thickness preset's "All parameters updated."
lands there with class `info` on the wrapper whenever a preset is clicked (and,
until 2026-08-22, on every page load) - so a notice could fail a
run; the check now skips `info`. And `restoreThicknessPreset()` re-applies the
card-stock preset across every dial after load, and can apply more than once, so
**an e2e test that edits a dial can have its edit silently overwritten** and then
assert the preset's value instead. That last one is not fixed - pin dial values at
the source instead (see
`tests/test_smoke.py::test_payload_fallback_literals_match_the_shipped_defaults`).

One more thing worth knowing when running the local suite: locally Playwright uses many
parallel workers and **no** retries, while CI uses one worker and two retries. Firefox is
slower to start the liblouis and Manifold workers under that load, so any test that presses
a worker-backed button without waiting for readiness can fail locally while passing on CI.
The suite's helpers wait for readiness and rethrow anything that is not the documented
not-ready message; a bare press is the bug, not the browser.

Worker startup itself used to be the other half of this. Every message to the liblouis
worker shared one 10-second timeout, including `init` — and an `init` that times out is
terminal, because the catch around it nulls the worker and disables translation for the
rest of the page with no retry. Under enough parallel workers, WASM startup crossed 10
seconds and whole spec files failed with `Worker message timeout`. `init` now gets 30
seconds and every other message keeps the 10-second budget, so the page survives a slow
start instead of giving up on it.

The OpenSCAD version has this feature: the double-sided port shipped in the OpenSCAD
generator v2.6 and was refined in v2.7 (2026-08-23).

Full technical detail: `docs/specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md`.
Step-by-step instructions: `docs/guides/CYLINDER_GUIDE.md`.

## Gear-integrated one-piece rollers (BETA) — status

A generated cylinder can ship as ONE solid part with its top and bottom drive gears
already attached, instead of a bare barrel that separately printed gears are pushed
onto. Meshing the two rollers' gears is also what holds the paired cylinders
rotationally synchronised — the assembly risk the double-sided work recorded as about
±1.0°. That budget note still stands: the gears hold phase to roughly their backlash,
measured at 0.65 mm of flank clearance on the reference set.

**Cylinders only, and off by default.** With the toggle off nothing changes: the
request body, the geometry and the filenames are byte-identical to a build without the
feature. With it on the download gains a `Geared_` segment
(`Embossing_Cylinder_Geared_0.4_name.stl`).

**The gears are not adjustable, and the cylinder size is fixed while they are on.**
They are a 1:1 replica of the reference set — 24 teeth, tip diameter 32.2187 mm,
10 mm thick, sitting at z −10..0 and 52..62 around the barrel for a 72 mm roller, with
the pair meshing at an axis distance of 32.0473 mm. Because that geometry is fixed, a
gear-mode request for anything other than a 30.8 mm × 52.0 mm cylinder is REFUSED: a
shorter barrel would export as loose pieces and a taller one would swallow the teeth.
The app says so live before you press Generate.

**The barrel prints solid while gears are on.** The polygonal cutout is dropped, and
the app says so when you had one set. A one-piece roller has no through-path along its
axis anyway — the gear bores are blind pockets — so keeping the cutout would seal a
cavity nothing can reach or drain.

**Known limitation, inherited not introduced.** On the EMBOSSING plate the exported
file is one watertight roller plus one small separate body per raised braille dot —
the dome of each dot. That is a long-standing tangency issue in the dot geometry,
present with gears off too, and it is tracked separately. The counter plate exports as
exactly one body.

**OpenSCAD:** the desktop build gets integrated gears; the MakerWorld single-file
variant does not. Tested in the real product 2026-08-25: MakerWorld's customizer
has no way to accept a mesh file at all, so there is no packaging of the gears
that could reach it. Use the desktop build or this web app for geared cylinders.

Wording in this section signed off by Brennen 2026-08-25; reword only with his
sign-off. The MakerWorld paragraph was re-signed the same day, when a probe of
the real customizer replaced the reasoning about mesh size with the tested
reason.

Full technical detail: `docs/specifications/GEAR_INTEGRATED_ROLLERS_SPECIFICATIONS.md`.

## Embosser Version 2 (prototype) — status

Version 2 is a new embosser design: its drive gears are separate prints again, each
carrying a differently shaped peg, and each end of each cylinder gets a matching keyed
hole — so a gear cannot be seated in the wrong place. Choose it from the selector at
the top of the page.

**It is a work-in-progress prototype.** The cylinder size, the cutout shapes and the
fit may all change as testing continues. Nothing about it is final.

**The gears must be re-cut.** The holes are family **R14** — four rounded rectangles,
14 × 14 mm at Cylinder A's top (the nub end), 18 × 10 at A's bottom, 16 × 12 at B's
top and 20 × 8 at B's bottom, each with a 0.5 mm corner radius. **None of the earlier
v7 pegs fits**: the six-scallop star, the hexagon and both 15 × 15 mm squares are
retired, and no one of them will enter an R14 hole. A cylinder printed today pairs
only with gears cut to `GEAR_PEG_SPEC_R14`, which are not published yet.

**Version 1 is the default and is untouched.** Leave the selector alone and you get
exactly the app that shipped before Version 2 existed: the same request, the same
geometry, the same filenames. That is checked rather than assumed — the exported STL
bytes and the request body are compared before and after every change.

**Cylinders only.** Version 2 has no meaning for a flat plate, and the API refuses the
combination.

Wording in this section signed off by Brennen 2026-08-28; reword only with his
sign-off. He chose this shorter shape deliberately: the key-clearance dial, the
error-proofing margins, the soft 30.1 × 52 preset, the one-fewer-braille-cell change
in visual mode, the Version-1-only integrated gears and the OpenSCAD/MakerWorld status
all live in the specification instead.

Full technical detail: `docs/specifications/EMBOSSER_VERSION_2_KEYED_CUTOUTS_SPECIFICATIONS.md`
(written in Phase 10).


## Flat business card plates are parked

Flat card generation is disabled in the UI (since December 2025) and will not be
re-enabled in this repo. The card geometry code, specs, and the BANA formatting
guide are all still present, but the feature is parked, not in progress.

Why: the flat-card path depended on the Vercel Blob storage flow that v2.0.0
removed, and the emboss/counter card pair is a different enough tool from the
cylinder that it deserves its own repo rather than a second mode here. This
repo is now the **cylinder** generator, and its name says so.

Where card work continues instead:

- [braille-wedge-card-openscad](https://github.com/BrennenJohnston/braille-wedge-card-openscad)
  — directly readable braille cards, printed leaning at 75°. Shipping today.
- A flat emboss/counter card plate tool may return as its own repo. Nothing is
  scheduled.

## Resolved (historical)

These issues existed in v1.x and were resolved by removing the systems entirely in v2.0.0:

1. **Vercel Blob storage caching** — Blob caching for counter plate STLs didn't work reliably. Resolved by removing Blob storage and moving to client-side generation.

2. **Upstash Redis inactivity failures** — Free tier archives databases after 14 days of inactivity, causing all requests to fail. Resolved by removing Redis entirely.

3. **Server-side STL generation on Vercel** — manifold3d requires native binaries not available in Vercel's Python runtime. Resolved by moving all generation to client-side (three-bvh-csg for cards, Manifold WASM for cylinders).

## Reporting issues

Check [GitHub Issues](https://github.com/BrennenJohnston/braille-cylinder-stl-generator/issues) first, then open a new issue with steps to reproduce, browser/OS info, and any console errors.
