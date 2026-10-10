# Project Structure

## Directory overview

```
braille-cylinder-stl-generator/
├── app/                      Main application package
│   ├── geometry/             Geometry modules (gears, double-sided, Version 2, dots, plates, cylinders)
│   ├── api.py                Placeholder; the routes live in backend.py
│   ├── exporters.py          STL export helpers from the removed server-side path (nothing imports them)
│   ├── geometry_spec.py      Geometry spec extraction for client-side CSG
│   ├── models.py             Data models and settings
│   ├── utils.py              Braille-to-dot conversion, logging and helpers
│   └── validation.py         Input validation
├── docs/                     Documentation
│   ├── specifications/       Technical specs (20 files)
│   ├── deployment/           Deployment guides
│   ├── development/          Dev notes and implementation guides
│   ├── guides/               User-facing guides (cylinder, business card)
│   └── security/             Security docs and audit reports
├── OpenSCAD/                 Vendored offline copy of the OpenSCAD program (never edit here; see OpenSCAD/README.md)
├── public/                   Production HTML (served on Vercel and by Flask locally)
├── scripts/                  Utility scripts
├── static/                   Three.js, Web Workers, vendored libraries, liblouis, gear assets
│   ├── assets/gears/         Gear meshes for the fused rollers (made by scripts/derive_gear_assets*.py)
│   ├── liblouis/             liblouis build and translation tables
│   ├── vendor/               Vendored Manifold, three-bvh-csg and three-mesh-bvh
│   └── workers/              CSG Web Workers (Manifold for cylinders, three-bvh-csg for cards)
├── tests/                    Test suite (15 Python test files)
│   ├── e2e/                  Playwright browser tests (27 spec files)
│   ├── fixtures/             Golden STL files for regression tests
│   ├── frontend/             Vitest unit tests (one placeholder today)
│   ├── test_smoke.py         Endpoint smoke tests
│   └── test_golden.py        Golden file regression tests
├── third_party/              Vendored liblouis tables
├── backend.py                Flask app entry point
├── wsgi.py                   Vercel serverless entry point
├── requirements.txt          Production dependencies (Flask and Flask-CORS)
├── requirements-dev.txt      Dev dependencies (numpy, trimesh, pytest, etc.)
├── settings.schema.json      JSON Schema describing the settings (documentation; nothing loads it)
└── vercel.json               Vercel deployment config
```

## How it works

The project uses a **client-side generation** architecture:

1. The browser translates the text to braille with liblouis, in a Web Worker
2. The browser sends the braille and the settings to the server, which validates them and returns a JSON geometry spec
3. The browser runs CSG boolean operations to build the 3D model
4. The STL file is generated and downloaded entirely in the browser

The server is minimal — just Flask serving static files and one JSON endpoint. All the heavy computation happens client-side using Web Workers.

### Backend

- **`backend.py`** — Flask server for local development
- **`wsgi.py`** — Serverless wrapper for Vercel
- **`app/models.py`** — `CardSettings` and `CylinderParams` data models
- **`app/geometry_spec.py`** — Builds the JSON geometry spec that the browser uses
- **`app/geometry/`** — `gears.py`, `interpoint.py` and `version2.py` hold the gear, double-sided and Embosser Version 2 numbers that the geometry spec and validation use; the dot shape, plate, cylinder, layout and boolean modules build meshes in Python and are used only in development and tests

### Frontend

- **`static/workers/csg-worker.js`** — Web Worker using three-bvh-csg for flat cards (parked: the page offers only cylinders)
- **`static/workers/csg-worker-manifold.js`** — Web Worker using Manifold WASM for cylinders
- **`static/liblouis-module-worker.js`** — Web Worker for braille translation; it runs `static/liblouis-engine.js`
- **Three.js** — 3D preview rendering
- **`public/index.html`** — The single HTML build, served both on Vercel and by Flask locally (`send_from_directory('public', 'index.html')`). The former `templates/index.html` twin was an unserved stale copy and has been removed.

### API endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve the UI |
| `/health` | GET | Health check |
| `/liblouis/tables` | GET | List braille translation tables |
| `/geometry_spec` | POST | Return geometry spec JSON for client-side CSG |

Old server-side STL endpoints (`/generate_braille_stl`, `/generate_counter_plate_stl`, `/lookup_stl`) and the old `/debug/blob_upload` return 410 Gone.

## Dependencies

**Production** (what Vercel installs):
- Flask, Flask-CORS

**Development** (what you install locally):
- numpy, trimesh, shapely — 3D geometry operations
- pytest, ruff, mypy — testing and linting
- Playwright, Vitest — browser and unit tests (npm, `package.json`)

**Client-side**:
- Three.js — 3D rendering
- three-bvh-csg — CSG for flat cards
- Manifold WASM — CSG for cylinders (vendored in `static/vendor/manifold-3d/`, version 2.5.1)
- liblouis — braille translation (liblouis 3.39.0 compiled to WebAssembly, with its tables, vendored in `static/vendor/liblouis-3.39.0/`)

## Configuration files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python metadata; ruff, mypy and pytest settings |
| `vercel.json` | Vercel deployment settings |
| `settings.schema.json` | JSON Schema describing every setting. Documentation only: nothing loads it at runtime; `app/validation.py` enforces the ranges |
| `.pre-commit-config.yaml` | Pre-commit hooks (file checks and ruff) |
| `package.json` | npm scripts (`npm test` runs Vitest, `npm run test:e2e` runs Playwright) and the `liblouis` package |
| `playwright.config.ts` | Browser tests in Chromium, Firefox and WebKit, against `python backend.py` on port 5001 |
| `vitest.config.js` | Vitest settings |
| `lighthouserc.json` | Lighthouse CI accessibility check (run by CI) |
