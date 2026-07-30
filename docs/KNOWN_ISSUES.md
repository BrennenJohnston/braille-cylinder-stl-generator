# Known Issues

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
