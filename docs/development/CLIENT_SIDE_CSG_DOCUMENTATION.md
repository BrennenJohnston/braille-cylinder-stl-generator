# Client-Side CSG Architecture Documentation

## Overview

This application uses **client-side CSG (Constructive Solid Geometry)** as the **exclusive method** for generating braille STL files. A **dual-worker architecture** is employed:

- **Standard Worker** (`csg-worker.js`): Uses `three-bvh-csg` for flat cards - fast but may produce non-manifold edges on complex geometry (flat cards are parked: the page offers only cylinders)
- **Manifold Worker** (`csg-worker-manifold.js`): Uses Manifold WASM for cylinders - guarantees watertight/manifold output

> **BUG FIX (2024-12-08):** Prior to this fix, the CSG worker existed but was never integrated into the frontend. The code incorrectly went directly to the server-side `/generate_braille_stl` endpoint. This has been corrected - the frontend now properly initializes the CSG worker and uses client-side generation exclusively. Server-side fallback has been intentionally disabled to ensure the correct generation path is always used.

> **MANIFOLD INTEGRATION (2024-12-08):** The Manifold worker (`csg-worker-manifold.js`) existed but was never integrated. This has been fixed - cylinder generation now automatically uses the Manifold worker, guaranteeing zero non-manifold edges. See `MANIFOLD_CYLINDER_FIX.md` for details.

## Why Client-Side CSG?

### Vercel Hobby Tier Compatibility
- **No timeout limits**: Vercel Hobby has 10-60 second limits on serverless functions
- **No cold start delays**: Processing happens immediately in the browser
- **No external dependencies**: Doesn't require Blender, OpenSCAD, or manifold3d binaries on the server
- **Reduced server load**: Server only provides geometry specifications, not full STL files
- **Better scalability**: Each client does their own rendering work

### Performance
- **Fast enough**: Typical braille card (50-100 dots) generates in 5-15 seconds
- **Predictable**: No variability from serverless cold starts or function reuse
- **Progressive**: User sees progress in browser console (the 3D engine's own messages on every site; the page's step-by-step messages only when it is served from `localhost` or `127.0.0.1`, see Debugging)

### Bundle Size
- **Minimal impact**: Adds ~215-295 KB minified (~60-80 KB gzipped)
- **Cacheable**: Client downloads libraries once, reuses across sessions
- **Already have Three.js**: Most dependencies are the existing three.module.js

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  public/index.html (Main App)                              │ │
│  │  - Collects user input                                     │ │
│  │  - Translates text to braille via liblouis                │ │
│  │  - Requests geometry spec from server                     │ │
│  │  - Selects worker based on shape_type                     │ │
│  │  - Receives STL, renders preview, offers download         │ │
│  └─────────────┬──────────────────────────────────────────────┘ │
│                │                                                 │
│       ┌────────┴────────┐                                       │
│       │  Worker Select  │                                       │
│       │  (shape_type)   │                                       │
│       └────────┬────────┘                                       │
│          ┌─────┴─────┐                                          │
│          │           │                                          │
│          ▼           ▼                                          │
│  ┌───────────────┐  ┌────────────────────┐                     │
│  │ csg-worker.js │  │ csg-worker-        │                     │
│  │ (cards)       │  │ manifold.js        │                     │
│  │               │  │ (cylinders)        │                     │
│  │ three-bvh-csg │  │ Manifold WASM      │                     │
│  │ Fast, ~300KB  │  │ Watertight, ~1.1MB │                     │
│  └───────┬───────┘  └─────────┬──────────┘                     │
│          │                    │                                 │
│          └────────┬───────────┘                                 │
│                   ▼                                             │
│           ┌──────────────┐                                      │
│           │  STL Binary  │                                      │
│           │  + Geometry  │                                      │
│           └──────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
                 │
         ┌───────▼────────────────────────────────────────┐
         │  Vercel Backend (Python Flask)                 │
         │  ┌──────────────────────────────────────────┐  │
         │  │  POST /geometry_spec                     │  │
         │  │  - Receives braille text + settings      │  │
         │  │  - Computes dot positions                │  │
         │  │  - Returns JSON spec (no booleans)       │  │
         │  └──────────────────────────────────────────┘  │
         │  ┌──────────────────────────────────────────┐  │
         │  │  POST /generate_braille_stl (410 Gone)   │  │
         │  │  - Server-side generation removed        │  │
         │  │  - Answers 410 Gone since 2.0.0          │  │
         │  └──────────────────────────────────────────┘  │
         └────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Braille translation (client-side liblouis)
2. **Translated text + settings** → POST /geometry_spec → **JSON spec**
3. **JSON spec** → CSG Worker → **STL ArrayBuffer + Geometry**
4. **STL** → Blob URL → Three.js preview + download link
5. **On error** → Display error message (NO server fallback)

### Geometry Spec Format

The `/geometry_spec` endpoint returns JSON describing primitives:

```json
{
  "shape_type": "card",
  "plate_type": "positive",
  "plate": {
    "width": 85.0,
    "height": 54.0,
    "thickness": 2.0,
    "center_x": 42.5,
    "center_y": 27.0,
    "center_z": 1.0
  },
  "dots": [
    {
      "type": "standard",
      "x": 10.0,
      "y": 40.0,
      "z": 2.0,
      "params": {
        "base_radius": 0.75,
        "top_radius": 0.5,
        "height": 0.5
      }
    },
    {
      "type": "rounded",
      "x": 15.0,
      "y": 40.0,
      "z": 2.0,
      "params": {
        "base_radius": 1.0,
        "top_radius": 0.75,
        "base_height": 0.2,
        "dome_height": 0.6,
        "dome_radius": 0.76875
      }
    }
  ],
  "markers": [
    {
      "type": "triangle",
      "x": 5.0,
      "y": 40.0,
      "z": 2.0,
      "size": 2.5,
      "depth": 0.6
    },
    {
      "type": "rect",
      "x": 7.0,
      "y": 40.0,
      "z": 2.0,
      "width": 2.5,
      "height": 5.0,
      "depth": 0.5
    }
  ]
}
```

This example is a card spec (flat cards are parked). In a rounded dot, `dome_radius` is the radius of the sphere the dome is cut from, (r² + h²) / 2h with r = `top_radius` and h = `dome_height`; it is not the dome's base radius. The page now builds only cylinders: a cylinder spec (`extract_cylinder_geometry_spec` in `app/geometry_spec.py`) has a `cylinder` block (`radius`, `height`, `thickness`, `polygon_points`, and `seam_channel` when the groove fits), dots of type `cylinder_dot` placed by angle (`theta`, `radius`, `is_recess`), `markers`, `indicator_mode` and `warnings`, plus `gears` or `keyed_cutouts` (and a few more `cylinder` keys) when those features are on.

## Files Added/Modified

### New Files
- `static/vendor/three-bvh-csg/index.module.js` - CSG library (vendored from npm)
- `static/vendor/three-bvh-csg/index.module.js.map` - Source map
- `static/vendor/three-mesh-bvh/index.module.js` - BVH library (vendored from npm)
- `static/vendor/three-mesh-bvh/index.module.js.map` - Source map
- `static/examples/STLExporter.js` - STL exporter from three.js
- `static/workers/csg-worker.js` - Web Worker for CSG operations
- `app/geometry_spec.py` - Geometry spec extraction logic
- `CLIENT_SIDE_CSG_DOCUMENTATION.md` - This file
- `CLIENT_SIDE_CSG_TEST_PLAN.md` - Testing guide

### Modified Files
- `backend.py` - Added `/geometry_spec` endpoint
- `public/index.html` - Added CSG worker initialization (no fallback between workers)

## Configuration

### No Fallback Mode (Current Implementation)

As of the 2024-12-08 bug fix, client-side CSG is the **exclusive** STL generation method. There is no automatic fallback to server-side generation. This ensures:

1. The correct generation path is always used
2. Bugs in the client-side path are surfaced immediately (not hidden by fallback)
3. Consistent behavior across all users and browsers

### Error Conditions

If CSG generation fails, users will see an error message. Common causes:
1. Web Workers not supported by browser
2. Worker initialization fails
3. Module worker imports fail (Safari < 15, older browsers)
4. `/geometry_spec` fetch fails or returns error
5. CSG worker throws error during generation
6. Worker timeout (2 minute limit)

### Worker Start-up

The page starts the braille translator, the card worker and the 3D engine one after another when it loads. Generate STL, the Translate buttons and Preview Braille Translation wait for a translator that is still starting, and Generate STL also waits for a 3D engine that is still starting, instead of failing (the `liblouisSettled` and `manifoldSettled` promises in `public/index.html`); while a press waits, a one-sentence notice says so. A worker that does not start in time (30 seconds for the translator, 60 seconds for the 3D engine) still gives the old error message. Details: [UI_INTERFACE_CORE_SPECIFICATIONS.md](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md), section 4.14.

### Browser Requirements

For STL generation to work, the browser must support:
- ES6 Modules
- Module Workers (`new Worker(url, { type: 'module' })`)
- Modern JavaScript (async/await, Promises)

**Supported browsers**: Chrome 80+, Edge 80+, Firefox 114+, Safari 15+

## Browser Compatibility

### Fully Supported (Client-Side CSG)
- ✅ Chrome 80+ (Desktop & Android)
- ✅ Edge 80+
- ✅ Firefox 114+ (Module workers stable)
- ✅ Safari 15+ (Module workers supported)
- ✅ Mobile Safari (iOS 15+) - with background WASM loading
- ✅ Chrome for Android

### Mobile Support (2024-12-08 Fix)

The Manifold worker uses **background WASM loading** to improve mobile compatibility:

1. **Worker loads immediately**: The worker script loads and signals "ready" quickly
2. **WASM loads in the background**: The ~1.1 MB Manifold WASM module starts loading as soon as the worker starts, without delaying its "ready" signal; if that load fails, it is tried again when the first cylinder is generated
3. **Better error messages**: Mobile-specific error messages guide users if loading fails

**Mobile Considerations:**
- First cylinder generation may take longer due to WASM loading
- Manifold WASM is vendored under `/static/vendor/manifold-3d/`; no third-party CDN access is required. The app works offline and under Firefox Enhanced Tracking Protection (Strict), Safari content blockers, and locked-down corporate networks.
- If WASM fails to load (vendored file missing or server error), users see an error that names `/static/vendor/manifold-3d/` and asks them to refresh; the advice for mobile devices appears when the 3D engine itself did not start
- Desktop browser recommended for best performance

### Not Supported (Will Show Error)
- ❌ Safari < 15 (no module workers)
- ❌ Firefox < 114 (module worker bugs)
- ❌ IE 11, older mobile browsers
- ❌ Any browser with JavaScript disabled

> **Note:** Server-side fallback has been intentionally disabled. Users on unsupported browsers will see an error message asking them to use a modern browser.

## Performance Characteristics

### Client-Side CSG
| Model Size | Dots | Time (typical) | Browser Load |
|------------|------|----------------|--------------|
| Small      | 10-20 | 2-5 seconds   | Low |
| Medium     | 50-100 | 5-15 seconds  | Medium |
| Large      | 200-300 | 15-45 seconds | High |
| Very Large | 500+ | 45-120 seconds | Very High (may fail) |

### Memory Usage
- Small models: ~50-100 MB
- Medium models: ~100-200 MB
- Large models: ~200-500 MB
- **Browser limit**: ~500 MB - 2 GB depending on browser/device

### Server Fallback (DISABLED)
Server-side fallback has been intentionally disabled as of 2024-12-08.
- The `/generate_braille_stl` endpoint answers 410 Gone: server-side generation was removed in 2.0.0 (January 2026)
- All STL generation uses client-side CSG exclusively
- This ensures consistent behavior and surfaces bugs immediately

## Debugging

### Enable Debug Logging

The worker variables (`csgWorker`, `csgWorkerReady`, `manifoldWorker`) are declared inside the page's module script, so the browser console cannot read them. To see the page's own debug messages, including the ones below, serve the page from `localhost` or `127.0.0.1`: its `log` helper (`public/index.html`) prints them only there. On any other address the page prints only its errors, while the 3D engine's own messages (they start with `Manifold CSG Worker:`) print everywhere.

### Console Messages

**Successful initialization:**
```
Initializing CSG worker...
CSG Worker file is accessible
CSG Worker initialized and ready
CSG Worker ready for client-side STL generation
```

**Successful generation** (a cylinder; for a card the worker is named `Standard CSG` instead of `Manifold CSG`):
```
Starting client-side CSG generation...
Fetching geometry specification from /geometry_spec...
Received geometry specification: {...}
Geometry spec contains: X dots, Y markers
Sending geometry spec to Manifold CSG worker...
Manifold CSG Worker completed successfully
Client-side CSG generation complete: filename.stl
```

**On error (no fallback):** the console prints the first line, and the page's message box shows the second.
```
Client-side CSG generation failed: [error message]
STL generation failed: [error message]
```

### Common Issues

**Worker fails to initialize:**
- Check browser supports module workers
- Check CORS (all files served from same origin)
- Check files exist: `/static/workers/csg-worker.js`, `/static/vendor/...`

**Geometry spec fails:**
- Check backend endpoint is running: `POST /geometry_spec`
- Check request payload matches expected format
- Check backend logs for Python errors

**CSG operation fails:**
- Check browser memory (Task Manager / Activity Monitor)
- Try smaller model
- Check browser console for detailed error

**Generated STL is invalid:**
- Check watertightness in slicer
- For cylinders, verify Manifold worker initialized successfully
- Report geometry edge cases

## Deployment to Vercel

### No Special Configuration Required

The client-side approach works out-of-the-box on Vercel Hobby:
- Only `public/index.html` is a static build; every other path, `static/` included, goes to the Flask app through `wsgi.py` (`vercel.json` routes; `serve_static` in `backend.py`), which sends `.js`, `.wasm` and `.json` files with 24-hour browser caching
- `/geometry_spec` endpoint is a lightweight serverless function
- No Vercel configuration for WASM: `manifold.wasm` is an ordinary file under `static/vendor/manifold-3d/`, and the Content-Security-Policy that `backend.py` sets allows WebAssembly (`'wasm-unsafe-eval'`)
- No file tracing configuration needed

### Existing Vercel Config

`vercel.json` remains unchanged:
```json
{
  "version": 2,
  "builds": [
    { "src": "public/index.html", "use": "@vercel/static" },
    { "src": "wsgi.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "^/$", "dest": "/public/index.html" },
    { "src": "^/index.html$", "dest": "/public/index.html" },
    { "src": "/(.*)", "dest": "/wsgi.py" }
  ]
}
```

### Cache Behavior

There is no server-side cache. Both plates, embossing and counter, are generated in the browser on every Generate, and no STL file is uploaded to or stored on the server. Redis and Vercel Blob storage were removed in 2.0.0; `backend.py` answers 410 Gone on the old `/lookup_stl` and `/debug/blob_upload` endpoints.

## Maintenance

### Updating three-bvh-csg

These libraries are no longer npm entries of this project (removed 2026-10-02), so fetch them in an empty temporary folder outside the repository:

```bash
npm install --no-save three-bvh-csg@latest three-mesh-bvh@latest
# PowerShell, from the temporary folder
Copy-Item node_modules\three-bvh-csg\build\index.module.js <repo>\static\vendor\three-bvh-csg\ -Force
Copy-Item node_modules\three-mesh-bvh\build\index.module.js <repo>\static\vendor\three-mesh-bvh\ -Force
```

Then point the copies' imports at the local files, as the current copies do: `from 'three'` becomes `from '/static/three.module.js'` in both files, and `from 'three-mesh-bvh'` in `three-bvh-csg` becomes `from '/static/vendor/three-mesh-bvh/index.module.js'`. The npm builds use these bare names, and the page and its workers have no import map to resolve them.

### Updating Three.js

When updating `static/three.module.js`, also update `static/examples/STLExporter.js`. `three` is not an npm entry of this project either, so fetch the version you are updating to in an empty temporary folder (today's `static/three.module.js` is revision 166: its `REVISION` constant):
```bash
npm install --no-save three@<version>
# PowerShell, from the temporary folder
Copy-Item node_modules\three\examples\jsm\exporters\STLExporter.js <repo>\static\examples\ -Force
```

Then change the copy's first line from `from 'three'` to `from '/static/three.module.js'`, as the current copy has it.

## Comparison to Alternatives

### vs. Server-Side manifold3d
| Factor | Client-Side three-bvh-csg | Server manifold3d |
|--------|---------------------------|-------------------|
| Vercel Hobby timeout | ✅ No limit | ❌ 10-60 seconds |
| Performance | ~10-30s typical | ~5-15s typical |
| Robustness | Good for clean geometry | Excellent (guaranteed manifold) |
| Setup complexity | ✅ None | ❌ Wheel availability, dependencies |
| Memory | Browser limit (~500MB-2GB) | Serverless limit (2GB) |
| Cost | ✅ Free (client CPU) | Vercel function time charges |

### vs. Client-Side manifold3d (WASM)
| Factor | three-bvh-csg | manifold3d |
|--------|---------------|------------|
| Bundle size | ~295 KB | ~1.1 MB |
| Browser support | ✅ Excellent | Good (WASM required) |
| Memory management | ✅ Automatic (GC) | ❌ Manual (`delete()` calls) |
| Performance | Good | ✅ Excellent |
| Setup | ✅ Simple | Complex (WASM config) |

## Future Enhancements (Optional)

**COMPLETED (2024-12-08, vendoring 2026-05-26):** The Manifold worker has been fully integrated:
- Manifold WASM (`manifold-3d@2.5.1`) is vendored under `/static/vendor/manifold-3d/` and loaded same-origin (no third-party CDN; works under Firefox ETP Strict, Safari content blockers, and offline)
- `static/workers/csg-worker-manifold.js` handles cylinder generation
- **No fallback**: Cylinders MUST use Manifold worker; cards use standard worker
- See `MANIFOLD_CYLINDER_FIX.md` and `OPTIONAL_MANIFOLD3D_PATH.md` for details

## Support & Troubleshooting

### User Can't Generate STL
1. Check browser console for errors
2. Refresh page and retry
3. Check internet connection (for spec fetch)
4. Try smaller model

### STL is Invalid
1. Open in slicer, check for errors
2. Report geometry edge case

### Slow Performance
1. Check browser task manager (memory usage)
2. Close other tabs
3. Try smaller model (reduce text length or line count)
4. Refresh page and ensure workers initialize properly

### Worker Not Initializing
1. Check browser version (need module worker support)
2. Check CORS errors in console
3. Verify files exist in `static/vendor/` and `static/workers/`
4. Try hard refresh (Ctrl+Shift+R / Cmd+Shift+R)
