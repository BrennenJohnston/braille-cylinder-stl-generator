# Known Issues

## Double-sided (interpoint) beta — status

The Double-Sided Card (BETA) toggle is **physically validated**. In August 2026 two
rounds of Cylinder A / Cylinder B pairs were printed on a Bambu Lab X1C with a 0.4 mm
nozzle and used to emboss real card stock; the braille came out legible on **both** faces.
The dot and bowl sizes it ships with (dot 1.2 mm across, bowl 1.3 mm across × 0.5 mm deep)
are therefore final — there are no size dials to tune.

It keeps the BETA label because it has been proven by one builder on one printer with one
paper stock, not because anything is known to be wrong with it.

Two caveats remain:

- **Rotational sync is a mechanical requirement, not a software one.** The two cylinders
  have to stay within about **1.0 degree** of each other as they turn. Further out of
  phase than that and a front dot can meet the back of the card where its paired bowl is
  not, so the emboss degrades. Nothing in this app can enforce that — it belongs to
  whoever builds and aligns the machine.
- **Local WebKit end-to-end tests fail on Windows.** Running the Playwright suite locally
  against WebKit on Windows produces 26 failures that are environmental (the Windows
  WebKit build), not defects in the app. The local pass bar is Chromium + Firefox; CI runs
  WebKit on Linux, where it passes.

Full technical detail: `docs/specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md`.

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
