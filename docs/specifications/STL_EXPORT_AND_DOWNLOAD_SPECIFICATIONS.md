# STL Export and Download Core Specifications

## Document Purpose

This document specifies the STL export and download system in the Braille Card and Cylinder STL Generator application. It serves as a reference for future development by documenting:

1. **Generation Architecture** — Client-side CSG (exclusive method, no fallback)
2. **Geometry Specification Format** — JSON structure sent to CSG workers
3. **CSG Worker System** — Web Worker communication, processing, and error handling
4. **STL Export Format** — Binary STL format details and file naming conventions
5. **Download Button State Machine** — Generate/Download state transitions
6. **Error Handling** — No automatic fallback; errors displayed to user
7. **Server Endpoints** — `/geometry_spec` API (primary), `/generate_braille_stl` (legacy, unused)

> **BUG FIX (2024-12-08):** Prior to this fix, the CSG worker existed but was never integrated into the frontend. The frontend incorrectly called `/generate_braille_stl` directly. This has been corrected - the frontend now properly uses client-side CSG exclusively via `/geometry_spec` → CSG Worker. Server-side fallback has been intentionally disabled.

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source for server-side logic
2. `geometry_spec.py` — Geometry specification extraction
3. `static/workers/csg-worker.js` — Client-side CSG for cards (three-bvh-csg)
4. `static/workers/csg-worker-manifold.js` — Client-side CSG for cylinders (Manifold WASM, guarantees manifold output)
5. `public/index.html` — Frontend orchestration with dual worker selection

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Generation Strategy Selection](#2-generation-strategy-selection)
3. [Geometry Specification Format](#3-geometry-specification-format)
4. [CSG Worker System](#4-csg-worker-system)
5. [Manifold WASM Integration](#5-manifold-wasm-integration)
6. [STL Binary Export Format](#6-stl-binary-export-format)
7. [File Naming Conventions](#7-file-naming-conventions)
8. [Download Button State Machine](#8-download-button-state-machine)
9. [Fallback Mechanisms](#9-fallback-mechanisms)
10. [Counter Plate Caching](#10-counter-plate-caching)
11. [Server Endpoints](#11-server-endpoints)
12. [Error Handling](#12-error-handling)
13. [Performance Characteristics](#13-performance-characteristics)
14. [Cross-Implementation Consistency](#14-cross-implementation-consistency)
15. [Paired Generation — Generate Both Cylinders (Double-Sided Beta)](#15-paired-generation--generate-both-cylinders-double-sided-beta)

---

## 1. Architecture Overview

### Design Philosophy

The STL generation system follows a **client-only architecture** where:

1. **Exclusive path:** Client-side CSG using Web Workers
2. **No fallback:** Server-side generation is disabled (endpoint exists but unused)
3. **All plate types:** Both positive and negative plates generated client-side

> **Updated 2024-12-08:** Server-side fallback has been intentionally disabled to ensure consistent behavior and surface bugs immediately.

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER CLICKS "GENERATE STL"                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND ORCHESTRATION (index.html)                       │
│                                                                              │
│  1. Translate text to braille Unicode (via liblouis worker)                 │
│  2. Collect all form settings                                               │
│  3. Call generateSTLClientSide() - NO FALLBACK                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │ Client-Side     │
                            │ CSG Path ONLY   │
                            └────────┬────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────┐
                   │   POST /geometry_spec          │
                   │   - Returns JSON spec          │
                   │   - Lightweight computation    │
                   │   - No boolean operations      │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │   CSG WORKER (Web Worker)      │
                   │   - Receives JSON spec         │
                   │   - Creates 3D primitives      │
                   │   - Performs boolean ops       │
                   │   - Exports to STL binary      │
                   │   - Optional: Manifold repair  │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STL BINARY RECEIVED                                       │
│                                                                              │
│  1. Create Blob URL from ArrayBuffer                                        │
│  2. Load into Three.js scene for preview                                    │
│  3. Set download link href                                                  │
│  4. Transition button to "Download STL" state                               │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────┐
                    │   ON ERROR: Display error message   │
                    │   (NO automatic server fallback)    │
                    └─────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `index.html` | Orchestration, CSG worker init, state management |
| `csg-worker.js` | Exclusive CSG operations using three-bvh-csg |
| `geometry_spec.py` | Extract JSON spec from braille data |
| `backend.py` | `/geometry_spec` endpoint (primary); `/generate_braille_stl` exists but unused |

---

## 2. Generation Strategy Selection

### Decision Logic (Updated 2024-12-08)

```javascript
// From public/index.html - NO FALLBACK
// All STL generation uses client-side CSG exclusively

// On form submit, after braille translation:
try {
    const stlData = await generateSTLClientSide({
        lines: translatedLines,
        originalLines: originalForIndicators,
        placementMode: placementMode,
        plateType: plateType,
        shapeType: shapeType,
        cylinderParams: cylinderParams,
        perLineLanguageTables: perLineLanguageTables,
        settings: settings
    });
    // Success: create blob, show preview, enable download
} catch (csgError) {
    // Error: show error message to user (NO server fallback)
    errorText.textContent = 'STL generation failed: ' + csgError.message;
}
```

### Strategy Matrix (Simplified)

| Plate Type | Worker Ready | Strategy |
|------------|--------------|----------|
| Positive | true | Client-side CSG |
| Positive | false | **Error** (no fallback) |
| Negative | true | Client-side CSG |
| Negative | false | **Error** (no fallback) |

### No Feature Flag

Server-side fallback has been intentionally disabled. There is no feature flag to toggle between methods. This guarantees:
- Consistent behavior across all users
- Bugs are surfaced immediately (not hidden by fallback)
- The correct generation path is always used

---

## 3. Geometry Specification Format

### Overview

The `/geometry_spec` endpoint returns a JSON object describing all geometric primitives needed to construct the STL file. This separates the "what to build" (server calculation) from "how to build it" (client CSG operations).

### Card (Flat Plate) Specification

```json
{
    "shape_type": "card",
    "plate_type": "positive",
    "plate": {
        "width": 90.0,
        "height": 52.0,
        "thickness": 2.0,
        "center_x": 45.0,
        "center_y": 26.0,
        "center_z": 1.0
    },
    "dots": [
        {
            "type": "standard",
            "x": 10.5,
            "y": 42.0,
            "z": 2.0,
            "params": {
                "shape": "standard",
                "base_radius": 0.9,
                "top_radius": 0.2,
                "height": 1.0
            }
        },
        {
            "type": "rounded",
            "x": 17.0,
            "y": 42.0,
            "z": 2.0,
            "params": {
                "shape": "rounded",
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
            "x": 83.5,
            "y": 42.0,
            "z": 2.0,
            "size": 2.5,
            "depth": 0.6
        },
        {
            "type": "rect",
            "x": 5.75,
            "y": 42.0,
            "z": 2.0,
            "width": 2.5,
            "height": 5.0,
            "depth": 0.5
        },
        {
            "type": "char",
            "x": 5.75,
            "y": 32.0,
            "z": 2.0,
            "char": "J",
            "size": 3.75,
            "depth": 0.5
        }
    ]
}
```

### Cylinder Specification

```json
{
    "shape_type": "cylinder",
    "plate_type": "positive",
    "cylinder": {
        "radius": 15.375,
        "height": 52.0,
        "thickness": 2.0,
        "polygon_points": [
            {"x": 13.464, "y": 0.0},
            {"x": 11.648, "y": 6.732},
            {"x": 6.732, "y": 11.648}
        ]
    },
    "dots": [
        {
            "type": "cylinder_dot",
            "x": 15.0,
            "y": 26.0,
            "z": 0.0,
            "theta": 0.15,
            "radius": 15.375,
            "is_recess": false,
            "params": {
                "shape": "standard",
                "base_radius": 0.9,
                "top_radius": 0.2,
                "height": 1.0
            }
        }
    ],
    "markers": [
        {
            "type": "cylinder_triangle",
            "theta": -0.5,
            "y": 42.0,
            "radius": 15.375,
            "size": 2.5,
            "depth": 0.6,
            "rotate_180": false
        }
    ]
}
```

### Specification Field Reference

#### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `shape_type` | `"card"` \| `"cylinder"` | Output geometry type |
| `plate_type` | `"positive"` \| `"negative"` | Embossing or counter plate |
| `plate` | object | Card plate dimensions (cards only) |
| `cylinder` | object | Cylinder dimensions (cylinders only) |
| `dots` | array | Braille dot specifications |
| `markers` | array | Indicator marker specifications |

#### Plate Fields (Cards)

| Field | Type | Description |
|-------|------|-------------|
| `width` | float | Card width in mm |
| `height` | float | Card height in mm |
| `thickness` | float | Card thickness in mm |
| `center_x` | float | X-center for positioning |
| `center_y` | float | Y-center for positioning |
| `center_z` | float | Z-center for positioning |

#### Cylinder Fields

| Field | Type | Description |
|-------|------|-------------|
| `radius` | float | Cylinder outer radius in mm |
| `height` | float | Cylinder height in mm |
| `thickness` | float | Wall thickness (when no polygon) |
| `polygon_points` | array | Array of {x, y} vertices for inner cutout |

#### Dot Types

| Type | Usage | Key Params |
|------|-------|------------|
| `standard` | Card emboss cone | `base_radius`, `top_radius`, `height` |
| `rounded` | Card emboss dome | `base_radius`, `top_radius`, `base_height`, `dome_height`, `dome_radius` |
| `cylinder_dot` | All cylinder dots | `theta`, `radius`, `is_recess`, `params.shape` |

#### Marker Types

| Type | Usage | Key Params |
|------|-------|------------|
| `triangle` | Card row-end marker | `size`, `depth` |
| `rect` | Card fallback/counter marker | `width`, `height`, `depth` |
| `char` | Card character indicator | `char`, `size`, `depth` |
| `cylinder_triangle` | Cylinder row marker | `theta`, `size`, `depth`, `rotate_180` |
| `cylinder_rect` | Cylinder fallback marker | `theta`, `size`, `depth` |
| `cylinder_char` | Cylinder character marker | `theta`, `char`, `size`, `depth` |

---

## 4. CSG Worker System

### Worker Initialization

**Source:** `public/index.html` — the CSG worker setup inside the `window` `load` handler. The `initCSGWorker()` wrapper below is illustrative only; the real code runs inline and probes the worker file with `fetch()` first.

```javascript
// Initialize CSG worker
let csgWorker = null;
let workerReady = false;

function initCSGWorker() {
    try {
        csgWorker = new Worker('/static/workers/csg-worker.js', { type: 'module' });

        csgWorker.onmessage = function(e) {
            if (e.data.type === 'ready') {
                workerReady = true;
                console.log('CSG Worker initialized and ready');
            } else if (e.data.type === 'result') {
                handleWorkerResult(e.data);
            } else if (e.data.type === 'error') {
                handleWorkerError(e.data);
            }
        };

        csgWorker.onerror = function(error) {
            console.error('CSG Worker error:', error);
            workerReady = false;
        };
    } catch (error) {
        console.warn('Failed to initialize CSG worker:', error);
        workerReady = false;
    }
}
```

### Worker Message Protocol

#### Request Message

```javascript
{
    type: 'generate',
    id: 1702345678901,           // Unique request ID (timestamp)
    spec: { ... },               // Geometry specification object
    useManifold: false           // Optional: use Manifold for repair
}
```

#### Success Response

```javascript
{
    type: 'result',
    id: 1702345678901,           // Matches request ID
    stlData: ArrayBuffer,        // Binary STL data
    geometry: BufferGeometry,    // Three.js geometry for preview
    stats: {
        dots: 97,
        markers: 8,
        vertices: 15420,
        triangles: 5140,
        time_ms: 12450
    }
}
```

#### Error Response

```javascript
{
    type: 'error',
    id: 1702345678901,
    error: 'CSG operation failed: ...',
    details: { ... }
}
```

### Worker Internal Architecture

**Source:** `static/workers/csg-worker.js`

```javascript
// Worker initialization
importScripts(...);  // Load Three.js, three-bvh-csg

self.onmessage = async function(e) {
    const { type, id, spec, useManifold } = e.data;

    if (type === 'generate') {
        try {
            console.log(`CSG Worker: Starting generation for request ${id}`);

            // 1. Create base geometry (plate or cylinder shell)
            let geometry = createBaseGeometry(spec);

            // 2. Process all dots (union or subtraction)
            for (const dot of spec.dots) {
                const dotGeom = createDotGeometry(dot, spec);
                geometry = performBoolean(geometry, dotGeom, dot.is_recess);
            }

            // 3. Process all markers (always subtraction)
            for (const marker of spec.markers) {
                const markerGeom = createMarkerGeometry(marker, spec);
                geometry = performBoolean(geometry, markerGeom, true);
            }

            // 4. Optional: Manifold repair
            if (useManifold && manifoldReady) {
                geometry = repairGeometryWithManifold(geometry);
            }

            // 5. Export to STL
            const stlData = exportToSTL(geometry);

            self.postMessage({
                type: 'result',
                id: id,
                stlData: stlData,
                geometry: geometry.toJSON(),
                stats: collectStats(spec, geometry)
            });

        } catch (error) {
            self.postMessage({
                type: 'error',
                id: id,
                error: error.message
            });
        }
    }
};

// Notify main thread that worker is ready
self.postMessage({ type: 'ready' });
```

### Boolean Operations

```javascript
// Using three-bvh-csg
import { Evaluator, Brush, ADDITION, SUBTRACTION } from 'three-bvh-csg';

const evaluator = new Evaluator();

function performBoolean(baseGeom, toolGeom, isSubtraction) {
    const baseBrush = new Brush(baseGeom);
    const toolBrush = new Brush(toolGeom);

    const operation = isSubtraction ? SUBTRACTION : ADDITION;
    const resultBrush = evaluator.evaluate(baseBrush, toolBrush, operation);

    return resultBrush.geometry;
}
```

---

## 5. Manifold WASM Integration

### Purpose

Manifold 3D WASM provides mesh repair capabilities to fix non-manifold edges that can occur during CSG operations.

### Initialization

**Source:** `static/workers/csg-worker.js` (lines 81-106)

Manifold is vendored under `/static/vendor/manifold-3d/` (manifold.js + manifold.wasm) so it loads from the same origin as the app. This removes the dependency on `cdn.jsdelivr.net` / `unpkg.com`, which keeps the worker functional under Firefox Enhanced Tracking Protection (Strict), Safari content blockers, locked-down corporate networks, and offline use.

```javascript
let ManifoldModule = null;
let manifoldReady = false;

async function initManifold() {
    const manifoldJsUrl = '/static/vendor/manifold-3d/manifold.js';
    const manifoldWasmUrl = '/static/vendor/manifold-3d/manifold.wasm';

    try {
        ManifoldModule = await import(manifoldJsUrl);
        // Pin the .wasm sibling path so it resolves correctly even when the
        // worker itself is loaded from a blob: URL or a different origin.
        await ManifoldModule.default({
            locateFile: (path) => path.endsWith('.wasm') ? manifoldWasmUrl : path,
        });
        manifoldReady = true;
        console.log('CSG Worker: Manifold3D WASM loaded from', manifoldJsUrl);
    } catch (error) {
        console.warn('CSG Worker: Manifold3D not available, mesh repair disabled:', error.message);
    }
}
```

### Repair Function

```javascript
function repairGeometryWithManifold(geometry) {
    if (!manifoldReady || !ManifoldModule) {
        return geometry;  // Pass through if not available
    }

    try {
        // Convert Three.js BufferGeometry to Manifold mesh format
        const positions = geometry.attributes.position.array;
        const indices = geometry.index ? geometry.index.array : null;

        // Create Manifold mesh (automatically repairs during construction)
        const mesh = new ManifoldModule.Mesh({
            numProp: 3,
            vertProperties: Array.from(positions),
            triVerts: indices ? Array.from(indices) : undefined
        });

        const manifold = new ManifoldModule.Manifold(mesh);

        // Extract repaired mesh
        const repairedMesh = manifold.getMesh();

        // Convert back to Three.js
        const repairedGeometry = new THREE.BufferGeometry();
        // ... conversion logic ...

        // Clean up Manifold objects
        manifold.delete();
        mesh.delete();

        console.log('CSG Worker: Mesh repaired with Manifold3D');
        return repairedGeometry;

    } catch (error) {
        console.warn('CSG Worker: Manifold repair failed:', error);
        return geometry;  // Return original if repair fails
    }
}
```

### Usage in Generation Pipeline

```javascript
// In worker message handler
let geometry = processGeometrySpec(spec);

// Apply Manifold repair if requested and available
if (useManifold !== false) {
    geometry = repairGeometryWithManifold(geometry);
}

const stlData = exportToSTL(geometry);
```

---

## 6. STL Binary Export Format

### STL Binary Structure

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER (80 bytes)                                           │
│  - Arbitrary text, often empty or application name           │
├──────────────────────────────────────────────────────────────┤
│  TRIANGLE COUNT (4 bytes, uint32 little-endian)              │
│  - Number of triangular facets in the mesh                   │
├──────────────────────────────────────────────────────────────┤
│  TRIANGLE 1 (50 bytes)                                       │
│  ├─ Normal vector (12 bytes: 3 × float32)                    │
│  ├─ Vertex 1 (12 bytes: 3 × float32)                         │
│  ├─ Vertex 2 (12 bytes: 3 × float32)                         │
│  ├─ Vertex 3 (12 bytes: 3 × float32)                         │
│  └─ Attribute byte count (2 bytes, typically 0)              │
├──────────────────────────────────────────────────────────────┤
│  TRIANGLE 2 (50 bytes)                                       │
│  ... repeats for each triangle ...                           │
└──────────────────────────────────────────────────────────────┘
```

### Export Implementation

**Source:** `static/examples/STLExporter.js`

```javascript
class STLExporter {
    parse(geometry, options = {}) {
        // Ensure we have a non-indexed geometry
        let geom = geometry;
        if (geometry.index !== null) {
            geom = geometry.toNonIndexed();
        }

        const positions = geom.attributes.position.array;
        const normals = geom.attributes.normal ? geom.attributes.normal.array : null;

        const triangleCount = positions.length / 9;
        const bufferLength = 80 + 4 + (triangleCount * 50);
        const buffer = new ArrayBuffer(bufferLength);
        const dataView = new DataView(buffer);

        // Write header (80 bytes)
        // Typically left as zeros or contains metadata

        // Write triangle count (uint32, little-endian)
        dataView.setUint32(80, triangleCount, true);

        let offset = 84;
        for (let i = 0; i < triangleCount; i++) {
            const idx = i * 9;

            // Normal vector
            // ... calculate from vertices if not provided ...

            // Write normal (3 × float32)
            dataView.setFloat32(offset + 0, nx, true);
            dataView.setFloat32(offset + 4, ny, true);
            dataView.setFloat32(offset + 8, nz, true);

            // Write vertex 1
            dataView.setFloat32(offset + 12, positions[idx + 0], true);
            dataView.setFloat32(offset + 16, positions[idx + 1], true);
            dataView.setFloat32(offset + 20, positions[idx + 2], true);

            // Write vertex 2
            dataView.setFloat32(offset + 24, positions[idx + 3], true);
            dataView.setFloat32(offset + 28, positions[idx + 4], true);
            dataView.setFloat32(offset + 32, positions[idx + 5], true);

            // Write vertex 3
            dataView.setFloat32(offset + 36, positions[idx + 6], true);
            dataView.setFloat32(offset + 40, positions[idx + 7], true);
            dataView.setFloat32(offset + 44, positions[idx + 8], true);

            // Attribute byte count (always 0)
            dataView.setUint16(offset + 48, 0, true);

            offset += 50;
        }

        return buffer;
    }
}
```

### Coordinate System

**CRITICAL:** The final STL must use Z-up orientation (standard CAD convention):

| Axis | Direction |
|------|-----------|
| X | Width (left-right) |
| Y | Depth (front-back) |
| Z | Height (up-down) |

**Three.js uses Y-up internally.** For cylinders, a rotation is applied:

```javascript
// In csg-worker.js
if (isCylinder) {
    finalGeometry.rotateX(Math.PI / 2);  // Y-up → Z-up
    console.log('CSG Worker: Rotated cylinder to Z-up orientation');
}
```

---

## 7. File Naming Conventions

### Naming Pattern

```
Embossing_Cylinder_{preset}_{name}.stl     (single-sided, plate_type positive)
Counter_Cylinder_{preset}_{name}.stl       (single-sided, plate_type negative)
Cylinder_A_{preset}_{name}.stl             (double-sided beta, plate_type positive)
Cylinder_B_{preset}_{name}.stl             (double-sided beta, plate_type negative)
```

Both plates of a pair therefore differ only in their first word, and both carry the print
settings and the content in the name — so a folder of downloads stays sortable and a plate
can be matched to the counter plate it was designed against without opening either file.

When the Double-Sided Card beta is on (cylinder shape only), the pair is named with the
beta's Cylinder A / Cylinder B vocabulary instead. The single-sided prefixes are frozen:
public training videos reference them, so the A/B naming applies to the double-sided flow
only.

### Components

| Component | Source | Values |
|-----------|--------|--------|
| Prefix | `plate_type` + double-sided toggle | Single-sided: `Embossing_Cylinder` (positive) or `Counter_Cylinder` (negative). Double-sided beta: `Cylinder_A` (positive) or `Cylinder_B` (negative) |
| `{preset}` | Selected Card Thickness preset | `0.4`, `0.3`, or `Custom` (the custom option has no single numeric value) |
| `{name}` | First word of the source text, sanitized | `brennen`, `cinnamon`, … or `untitled` |

### Name Derivation

`{name}` is resolved in this order:

1. **First word of the source text.** Manual placement scans `line1`…`lineN` for the first
   non-empty line; auto placement uses the Auto Placement Text box.
2. **Back-translated braille.** When the user pasted braille into the Braille (Unicode)
   field and left the text boxes empty, the braille is back-translated through the liblouis
   worker (`backTranslate`) and the first word of the result is used. Without this a
   braille-only workflow — which the field explicitly supports — would produce nothing but
   `untitled` files.
3. **`untitled`.** Last resort: no text, no braille, or the worker is unavailable.

Counter plates use the same derivation as embossing plates. They are geometrically
universal, but naming them after the same text keeps a generated pair together.

### Sanitization Rules

```javascript
function sanitizeFilenameWord(word) {
    return (word || '')
        .substring(0, 30)              // Limit length
        .replace(/[^\w\s-]/g, '')      // Remove special characters
        .replace(/[-\s]+/g, '_')       // Replace spaces/hyphens with underscore
        .replace(/^_+|_+$/g, '');      // Trim leading/trailing underscores
}

async function buildStlFilename(plateType, doubleSided = false) {
    const prefix = doubleSided
        ? (plateType === 'positive' ? 'Cylinder_A' : 'Cylinder_B')
        : (plateType === 'positive' ? 'Embossing_Cylinder' : 'Counter_Cylinder');
    return `${prefix}_${getThicknessPresetSegment()}_${await deriveStlNameSegment()}.stl`;
}
```

`doubleSided` receives the generate handler's `doubleSidedOn` flag (toggle checked AND
shape cylinder), so a card generated with the checkbox stuck on can never pick up an A/B
name.

### Examples

| Plate | Preset | Input | Filename |
|-------|--------|-------|----------|
| Embossing | 0.4 | "Hello World" | `Embossing_Cylinder_0.4_Hello.stl` |
| Counter | 0.4 | "Hello World" | `Counter_Cylinder_0.4_Hello.stl` |
| Embossing | 0.3 | "cinnamon jar" | `Embossing_Cylinder_0.3_cinnamon.stl` |
| Embossing | Custom | "amoxicillin" | `Embossing_Cylinder_Custom_amoxicillin.stl` |
| Embossing | 0.4 | ⠓⠑⠇⠇⠕ pasted, no text | `Embossing_Cylinder_0.4_hello.stl` (back-translated) |
| Counter | 0.4 | nothing entered | `Counter_Cylinder_0.4_untitled.stl` |
| Cylinder A (double-sided) | 0.4 | front "abc", back "def" | `Cylinder_A_0.4_abc.stl` |
| Cylinder B (double-sided) | 0.4 | front "abc", back "def" | `Cylinder_B_0.4_abc.stl` (named from the front text, keeping the pair together) |

---

## 8. Download Button State Machine

### States

> **Changed 2026-08-18 — the button no longer becomes the download control.**
> `#action-btn` now keeps its name and role for its whole life, and the file is
> offered by a **separate `#download-stl-btn`** that appears beside it. See
> *Why the state machine was split* below.

| Control | State | Text | CSS Class | Enabled | Action |
|---|---|---|---|---|---|
| `#action-btn` | **Generate** | "Generate STL" | `generate-state` | Yes | Start generation |
| `#action-btn` | **Generating** | "Generating..." | `generate-state`, opacity 0.7 | No | — |
| `#action-btn` | **Error** | "Generate STL" | `generate-state` | Yes | Retry |
| `#download-stl-btn` | **Hidden** | — | — | — | Not in the tab order |
| `#download-stl-btn` | **Offered** | "Download STL" | — | Yes | Download the built file |

`#action-btn` never carries `data-state="download"` any more. The `download-state`
class survives only on the historical `#action-btn.download-state` rules; the new
button styles itself under its own id.

### State Transitions

> In the diagram below, **DOWNLOAD is a separate control** (`#download-stl-btn`)
> as of 2026-08-18, not a state `#action-btn` enters. `#action-btn` returns to
> GENERATE on success and the download button appears alongside it; "any input
> changes" hides that button again.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                        ┌───────────────┐                              │
│  ┌─────────────────────►  GENERATE     │◄────────────────────────────┐│
│  │                     │               │                              ││
│  │                     └───────┬───────┘                              ││
│  │                             │                                      ││
│  │                     [User clicks]                                  ││
│  │                             │                                      ││
│  │                             ▼                                      ││
│  │                     ┌───────────────┐                              ││
│  │                     │  GENERATING   │                              ││
│  │                     │  (disabled)   │                              ││
│  │                     └───────┬───────┘                              ││
│  │                             │                                      ││
│  │              ┌──────────────┴──────────────┐                       ││
│  │              │                             │                       ││
│  │       [Success]                      [Error]                       ││
│  │              │                             │                       ││
│  │              ▼                             └───────────────────────┘│
│  │      ┌───────────────┐                                             │
│  │      │   DOWNLOAD    │                                             │
│  │      │               │                                             │
│  │      └───────┬───────┘                                             │
│  │              │                                                     │
│  │       [User clicks                                                 │
│  │        Download]                                                   │
│  │              │                                                     │
│  │              ▼                                                     │
│  │      File downloaded                                               │
│  │              │                                                     │
│  │       [Any input                                                   │
│  │        changes]                                                    │
│  │              │                                                     │
│  └──────────────┘                                                     │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### Implementation

```javascript
const actionBtn = document.getElementById('action-btn');

function resetToGenerateState() {
    actionBtn.textContent = 'Generate STL';
    actionBtn.className = 'generate-state';
    actionBtn.setAttribute('data-state', 'generate');
    actionBtn.setAttribute('aria-label', 'Generate STL file from entered text');
    actionBtn.disabled = false;
    actionBtn.style.opacity = '1';
}

function setToGeneratingState() {
    actionBtn.textContent = 'Generating...';
    actionBtn.className = 'generating-state';
    actionBtn.setAttribute('data-state', 'generating');
    actionBtn.setAttribute('aria-label', 'STL file is being generated');
    actionBtn.disabled = true;
    actionBtn.style.opacity = '0.6';
}

// Reveals the separate button; #action-btn goes back to being idle and keeps
// its own name. Returns early during a pair run, which reports its own progress
// through #pair-status and must not offer a single-plate download.
function setToDownloadState() {
    actionBtn.textContent = 'Generate STL';
    actionBtn.className = 'generate-state';
    actionBtn.setAttribute('data-state', 'generate');
    actionBtn.setAttribute('aria-label', 'Generate STL file from entered text');
    actionBtn.disabled = false;
    actionBtn.style.opacity = '1';
    if (pairRunInFlight) return;
    downloadStlBtn.style.display = '';
    announceStatus('stl-ready',
        'Your STL file is ready. Use the Download STL button to save it.');
}

// hideDownloadButton() runs at the TOP of resetToGenerateState(), before its
// idempotence guard: a successful run now leaves #action-btn idle, so the guard
// can return early where it never used to, and the download button would
// survive - still offering a file built from settings the user has changed.

// Any input change resets to Generate state
document.querySelectorAll('input, select, textarea').forEach(el => {
    el.addEventListener('input', resetToGenerateState);
});
```

### Why the state machine was split (2026-08-18)

A single control that renames itself is invisible as a defect on screen and
disqualifying with a screen reader. An NVDA run found the failure in one press:

- Nothing announced that generation had started, finished, or failed.
- The button's accessible name changed from "Generate STL file from entered text"
  to "Download generated STL file" **while the user's focus was on it**, with no
  announcement. The control under their finger silently became a different
  control.

Both are now fixed, and the second is fixed structurally rather than by
announcing the mutation: nothing renames itself, so there is nothing to announce.
The pattern copies the double-sided pair buttons, which the same NVDA run showed
working well.

Two further defects were found and fixed in the same pass:

**Progress messages had never been shown to anyone.** The `#error-message` box is
emptied at the start of each run but was never *declassed*, so a stale
`error-message` class outlived its message. The progress notice is guarded by "is
a blocking error already showing?", read from that class — and
`restoreThicknessPreset()` leaves exactly that state on every page load
("Card thickness preset applied", classed `error-message` with no `info`). The
guard therefore suppressed `Translating text to braille...` and
`Generating 3D model (client-side CSG)...` permanently, for sighted users too.
`runGenerateForCurrentPlate()` now clears the class along with the text. A
blocking error raised by the current run is set further down and still guards
correctly.

**Nothing in the single-plate flow could announce at all.** `#error-message` is
`display:none` between messages, so it is outside the accessibility tree at the
moment its text is written and can never fire (see UI Interface Core
Specifications §4.10). A blind user who overran a line was shown
"Line 1 exceeds 13 cells" and heard **silence**, with no way to discover why
generation refused — **WCAG 2.1 SC 4.1.3 Status Messages, Level AA**. Its
`role="alert"`/`aria-live` are removed and the box is mirrored to the shared
`#a11y-status` region by one MutationObserver, which covers all ~20 call sites at
once and cannot drift out of step with what is on screen.

**Signed-off wording (2026-08-18).** Reword only with Brennen's sign-off:

- Completion announcement: `Your STL file is ready. Use the Download STL button to save it.`
- Pair completion: `Both cylinders are ready. Use the Download Cylinder A and Download Cylinder B buttons below to save them.`
- The download button's accessible name is its visible text, `Download STL`.

**Label in Name.** The old pairing — visible "Download STL", accessible name
"Download generated STL file" — failed **SC 2.5.3 (Level A)**, because the
visible label was not contained in the accessible name, so speech-input users
could not activate it by reading it aloud. The new button takes its visible text
as its accessible name.

Verified 2026-08-18: `#action-btn` never leaves `data-state="generate"`; the
validation error, the progress notice and the completion message are all spoken;
one file per press; editing the form retracts the download; and the button
measures 310 × 44 px with text contrast 7.25:1 light, 8.35:1 dark, 15.18:1 high
contrast.

### High Contrast Button Colors

| State | Background | Text | Border |
|-------|------------|------|--------|
| Generate | `#0201fe` (Blue) | `#fdfe00` (Yellow) | `2px solid #fdfe00` |
| Generating | `#666666` (Gray) | `#cccccc` (Light Gray) | `2px solid #999999` |
| Download (`#download-stl-btn`) | `#02fe05` (Green) | `#000000` (Black) | `2px solid #000000` |

---

## 9. Fallback Mechanisms (DISABLED)

> **Updated 2024-12-08:** Server-side fallback has been intentionally disabled. All errors are surfaced to the user.

### Error Conditions (No Fallback)

| Condition | Cause | Action |
|-----------|-------|--------|
| Worker initialization fails | Browser doesn't support module workers | **Show error message** |
| `/geometry_spec` fails | Network error, server error | **Show error message** |
| CSG worker throws error | Boolean operation failure | **Show error message** |
| Worker timeout (2 min) | Very complex model | **Show error message** |

### Rationale for Disabling Fallback

1. **Bug Discovery:** The original fallback hid a critical bug where the CSG worker was never integrated
2. **Consistency:** All users get the same behavior regardless of edge cases
3. **Debugging:** Errors are immediately visible, not silently handled
4. **Simplicity:** Single code path is easier to maintain and test

### Error Handling Implementation

```javascript
// From public/index.html - NO FALLBACK
try {
    const stlData = await generateSTLClientSide({...});
    // Success path
} catch (csgError) {
    log.error('Client-side CSG generation failed:', csgError);

    // Show error - NO FALLBACK TO SERVER
    errorText.textContent = 'STL generation failed: ' + csgError.message;
    errorDiv.style.display = 'flex';
    errorDiv.className = 'error-message';

    // Re-enable button and reset to generate state
    resetToGenerateState();
}
```

### Legacy Endpoints (Still Available)

The `/generate_braille_stl` endpoint still exists in `backend.py` but is **not called by the frontend**. It may be useful for:
- Direct API testing
- Future integrations
- Emergency manual generation (via curl/Postman)

---

## 10. Counter Plate Caching

> **⚠️ ARCHIVED (2026-01-05):** This caching system has been **REMOVED**. Counter plates are now generated client-side along with all other STL files. The content below is preserved for historical reference only. See [CACHING_SYSTEM_CORE_SPECIFICATIONS.md](./CACHING_SYSTEM_CORE_SPECIFICATIONS.md) for full details.

### Historical Cache Strategy

Counter plates (negative) were deterministic based on grid settings only, not text content. This enabled aggressive caching:

1. **Cache Key:** Hash of grid settings (rows, columns, spacing, dot shape)
2. **Storage:** Vercel Blob storage (REMOVED)
3. **Response:** Redirect to cached Blob URL (REMOVED)

### Cache Key Generation

**Source:** `backend.py`

```python
def compute_counter_plate_cache_key(params: CardSettings, shape_type: str, cylinder_params: dict = None) -> str:
    """Generate a deterministic cache key for counter plate geometry."""

    key_parts = [
        f'shape:{shape_type}',
        f'rows:{params.grid_rows}',
        f'cols:{params.grid_columns}',
        f'cell_spacing:{params.cell_spacing}',
        f'line_spacing:{params.line_spacing}',
        f'dot_spacing:{params.dot_spacing}',
        f'recess_shape:{params.recess_shape}',
    ]

    if shape_type == 'cylinder' and cylinder_params:
        key_parts.extend([
            f'diameter:{cylinder_params.get("diameter_mm", 30.75)}',
            f'height:{cylinder_params.get("height_mm", 52)}',
            f'polygon_radius:{cylinder_params.get("polygonal_cutout_radius_mm", 13)}',
            f'polygon_sides:{cylinder_params.get("polygonal_cutout_sides", 12)}',
        ])

    key_string = '|'.join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]
```

### Cache Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    POST /generate_braille_stl (negative plate)              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  Compute cache key   │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  Check Blob storage  │
                           └──────────┬───────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
              [Cache HIT]                         [Cache MISS]
                    │                                   │
                    ▼                                   ▼
           ┌───────────────┐                   ┌───────────────┐
           │  Return 302   │                   │  Generate STL │
           │  Redirect to  │                   │  Upload to    │
           │  Blob URL     │                   │  Blob storage │
           └───────────────┘                   └───────┬───────┘
                                                       │
                                                       ▼
                                               ┌───────────────┐
                                               │  Return 302   │
                                               │  Redirect to  │
                                               │  Blob URL     │
                                               └───────────────┘
```

### Cache Headers

```python
# Response for cached counter plate
return redirect(blob_url, code=302)

# Cache control on Blob URL (set by Vercel Blob)
# Cache-Control: public, max-age=31536000, immutable
```

---

## 11. Server Endpoints

### POST /geometry_spec

**Purpose:** Extract geometry specification without performing boolean operations.

**Request:**

```json
{
    "lines": ["⠚⠕⠓⠝", "⠎⠍⠊⠞⠓"],
    "original_lines": ["John", "Smith"],
    "placement_mode": "manual",
    "plate_type": "positive",
    "shape_type": "card",
    "settings": {
        "grid_columns": 13,
        "grid_rows": 4,
        "cell_spacing": 6.5,
        "line_spacing": 10.0,
        "dot_spacing": 2.5
    }
}
```

**Response (200 OK):**

```json
{
    "shape_type": "card",
    "plate_type": "positive",
    "plate": { ... },
    "dots": [ ... ],
    "markers": [ ... ]
}
```

**Response (400 Bad Request):**

```json
{
    "error": "Validation error message"
}
```

### POST /generate_braille_stl

**Purpose:** Full server-side STL generation (LEGACY - endpoint exists but is NOT used by frontend).

**Request:**

```json
{
    "lines": ["⠚⠕⠓⠝", "⠎⠍⠊⠞⠓"],
    "original_lines": ["John", "Smith"],
    "placement_mode": "manual",
    "plate_type": "positive",
    "shape_type": "card",
    "settings": { ... },
    "cylinder_params": { ... }
}
```

**Response (200 OK):**

```
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="braille_john_card_emboss.stl"

[Binary STL data]
```

**Response (302 Redirect - Cached counter plate):**

```
Location: https://[blob-url]/counter_plate_[hash].stl
```

**Response (500 Error):**

```json
{
    "error": "Generation failed: [error message]"
}
```

---

## 12. Error Handling

### Error Categories

| Category | Source | Handling |
|----------|--------|----------|
| Validation Error | Invalid input | Display message, stay in Generate state |
| Network Error | Fetch failed | Display error, allow retry |
| Worker Error | CSG operation failed | Display error message (NO fallback) |
| Server Error | Backend exception | Display error message |
| Timeout | Operation took too long | Display error message (NO fallback) |

### User-Facing Error Messages

```javascript
const errorMessages = {
    'validation': 'Please check your input. ',
    'network': 'Network error. Please check your connection and try again.',
    'worker': 'Client-side generation failed. Trying server...',
    'server': 'Server error. Please try again later.',
    'timeout': 'Generation is taking too long. Please try a simpler design.',
    'unknown': 'An unexpected error occurred. Please refresh and try again.'
};

function showError(type, details = '') {
    const errorDiv = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');

    errorText.textContent = errorMessages[type] + details;
    errorDiv.style.display = 'flex';

    // Announce to screen readers
    errorDiv.setAttribute('role', 'alert');
}
```

### Error Recovery

```javascript
// NO FALLBACK - errors are displayed to the user
async function handleGenerationError(error) {
    console.error('Generation error:', error);

    // Show error message - NO fallback to server or alternative worker
    showError(error.type || 'unknown', error.message);
    resetToGenerateState();
    return null;
}
```

---

## 13. Performance Characteristics

### Client-Side Generation Times

| Model Size | Dots | Markers | Typical Time | Memory Usage |
|------------|------|---------|--------------|--------------|
| Small | 10-30 | 4-8 | 2-5 seconds | ~50-100 MB |
| Medium | 50-100 | 8-12 | 5-15 seconds | ~100-200 MB |
| Large | 150-250 | 12-16 | 15-30 seconds | ~200-350 MB |
| Very Large | 300+ | 16+ | 30-60 seconds | ~350-500 MB |

### Server-Side Generation Times (Historical)

> **Note:** Server-side STL generation was **removed in v2.0.0**. All generation now happens client-side.

~~| Model Size | Time (Cold Start) | Time (Warm) |~~
~~|------------|-------------------|-------------|~~
~~| Small | 5-10 seconds | 2-3 seconds |~~
~~| Medium | 10-20 seconds | 5-10 seconds |~~
~~| Large | 20-40 seconds | 10-20 seconds |~~
~~| Very Large | May timeout | 20-40 seconds |~~

### Bundle Sizes

| Component | Size (minified) | Size (gzipped) |
|-----------|-----------------|----------------|
| three.module.js | ~650 KB | ~150 KB |
| three-bvh-csg | ~120 KB | ~35 KB |
| three-mesh-bvh | ~95 KB | ~25 KB |
| STLExporter | ~5 KB | ~2 KB |
| csg-worker.js | ~50 KB | ~15 KB |
| **Total** | **~920 KB** | **~227 KB** |

### Manifold WASM (Optional)

| Component | Size | Notes |
|-----------|------|-------|
| manifold.js | ~2.5 MB | Vendored under `/static/vendor/manifold-3d/` (same-origin) |
| WASM module | ~1.5 MB | Part of above |
| Runtime memory | ~10-20 MB | During repair |

---

## 14. Cross-Implementation Consistency

### Geometry Spec Consistency

All generation methods must produce geometrically identical results:

| Aspect | geometry_spec.py | csg-worker.js | backend.py |
|--------|-----------------|---------------|------------|
| Plate center | `(w/2, h/2, t/2)` | Same | Same |
| Dot positions | `dot_positions` array | Same | Same |
| Angular direction | `apply_seam()` | Same | Same |
| Counter plate: all dots | Yes | Yes | Yes |
| Counter plate: rect only | Yes | Yes | Yes |

### Verification Tests

```javascript
// Verify geometry spec produces valid STL
async function test_geometry_consistency() {
    // Generate geometry spec
    const spec = await fetch('/geometry_spec', {
        method: 'POST',
        body: JSON.stringify(settings)
    }).then(r => r.json());

    // Send to appropriate worker
    const worker = spec.shape_type === 'cylinder' ? manifoldWorker : standardWorker;
    const stl = await worker.generate(spec);

    // Verify STL is valid
    assert(stl.byteLength > 0, 'STL has content');
    assert(validateSTLHeader(stl), 'Valid STL header');
    assert(getTriangleCount(stl) > 0, 'Has triangles');
}
```

### Worker Differences

| Aspect | Standard Worker (Cards) | Manifold Worker (Cylinders) |
|--------|------------------------|----------------------------|
| Library | three-bvh-csg | Manifold WASM |
| Triangle count | May vary | Optimized |
| Manifold guarantee | No | Yes |
| Bundle size | ~200 KB | ~2.5 MB (vendored same-origin) |
| Best for | Flat geometry | Curved surfaces |

---

## 15. Paired Generation — Generate Both Cylinders (Double-Sided Beta)

Added 2026-08-17. Applies **only** while the Double-Sided Card beta is on (checkbox
checked AND shape `cylinder`). With the beta off, nothing in this section exists on the
page and the single-plate flow of Sections 7 and 8 is unchanged.

### Why it exists

A double-sided pair only works if both cylinders come from **one** set of settings. In the
two-step flow the user generates Cylinder A, switches the plate radio, and generates
Cylinder B — and anything they touch in between produces a pair that cannot emboss the
same card. Generate Both removes that window: one press runs the whole pipeline twice with
nothing editable between the runs.

### The control

| Element | Id | Shown | Notes |
|---|---|---|---|
| Generate Both Cylinders (A and B) | `#generate-both-btn` | Beta on only | `<button type="button">` in the pinned `.action-footer`, min 44 × 44 px, named by its visible text |
| Pair status line | `#pair-status` | While a run is in flight and after it ends | `role="status" aria-live="polite"`, visible text — sighted and screen-reader users get the same progress |
| Download Cylinder A / B | `#download-cylinder-a-btn`, `#download-cylinder-b-btn` | After both cylinders are built | Inside `#pair-downloads`; each saves its own file on click |

While the beta is on, the plate radios are relabelled **Cylinder A — Embossing Plate** and
**Cylinder B — Universal Counter Plate**. The radio `value`s (`positive` / `negative`) and
the `aria-describedby` descriptions are untouched, and the off-state label text is captured
from the markup at load, so turning the beta off restores the single-sided labels character
for character.

### Run sequence

1. Remember the user's plate selection and the Number of Available Braille Cells value.
2. Select the **positive** radio with a real `change` event, so persistence, the cell dial,
   and the shape settings react exactly as they do to a click. A radio that is already
   checked fires nothing, matching a real click on an already-selected option.
3. Restore the cell dial (see *Identical settings* below), lock both generate controls,
   announce `Generating Cylinder A (1 of 2)...`.
4. Run `runGenerateForCurrentPlate()` to completion and keep the resulting blob.
5. Repeat steps 2–4 for **negative** with `Generating Cylinder B (2 of 2)...`.
6. Reveal both download controls and announce
   `Both cylinders are ready. Use the Download Cylinder A and Download Cylinder B buttons below to save them.`
   **Nothing downloads on its own** — see *Downloads* below.
7. In a `finally` block: restore the user's plate selection and cell dial, unlock the
   controls, reset the action button, and return focus to Generate Both if the run was
   started from the keyboard.

`runGenerateForCurrentPlate()` is the former `form.onsubmit` body, extracted unchanged so
the single-plate path and the paired path are the same code in the same order. It returns
`true` only when an STL was built; **every** early exit returns `false`.

### Identical settings — the safety contract

Both runs read the same DOM, so all settings match by construction, with one exception
that had to be handled explicitly:

> Changing the plate type re-fills `#grid_columns` with the recommended value unless the
> user has typed in that field this session (`updateGridColumnsForPlateType`). Left alone,
> a mid-run plate switch could hand Cylinder B a different column count from Cylinder A.
> The pair runner captures the dial before the run and restores it after every switch,
> including the final restore.

Verified in Chromium and Firefox: the two `/geometry_spec` request bodies of a pair run
differ in **exactly one key**, `plate_type` (`positive` vs `negative`). `settings`,
`lines`, `back_lines`, `cylinder_params`, `original_lines`, `per_line_language_tables`,
`placement_mode`, `grade`, and `shape_type` are byte-identical. Both bodies carry the front
braille in `lines` and the back braille in `back_lines`, as Section 3 requires.

### Failure behaviour

A failure on Cylinder A aborts the run and downloads nothing — a Cylinder B with no
matching A embosses the two sides of a card out of register, which is worse than no file.
The status line reads `Cylinder A could not be generated, so nothing was downloaded. Fix
the problem shown in the error message, then press Generate Both Cylinders again.` (same
sentence with `Cylinder B` for a second-plate failure), and the underlying reason is in the
existing `#error-message` overlay, unchanged.

### Downloads

**Nothing downloads automatically. Each file is saved by pressing its own button** —
`Download Cylinder A` and `Download Cylinder B` — which appear when the run finishes.
Names follow Section 7 exactly: `Cylinder_A_{preset}_{name}.stl` and
`Cylinder_B_{preset}_{name}.stl`.

**Why, changed 2026-08-18.** The original design started both downloads itself and kept
the buttons as a fallback. Two programmatic downloads from a single user gesture is
precisely what Chrome treats as *"wants to: Download multiple files"*, and the 2026-08-17
measurement that found Chromium, Firefox and headed Chrome all accepting the second
download silently was taken **without a screen reader running**, which is what made this
look safe.

An NVDA run on 2026-08-18 hit the prompt and could not get past it. The bubble is Chrome's
own UI and cannot be relabelled by the page: it names no file, gives no reason, and `Tab`
cycles Close → Allow → Block indefinitely with no statement of what is being decided. That
run ended in **"Download blocked"** with neither cylinder saved. Worse, the status line
that existed to rescue exactly this situation — *"If your browser blocked a download, use
the buttons below"* — was itself never announced, because the Save As dialog opened by the
first automatic download had taken focus off the page before the message was written.

One download per user gesture never triggers the prompt, so the failure mode is removed
rather than mitigated. This costs one extra keypress and is the only path that works
unaided for a blind user. Verified 2026-08-18: a full `Generate Both` run fires **0**
automatic downloads, both buttons appear, focus stays on `Generate Both Cylinders`, and
pressing `Download Cylinder A` yields exactly one file.

Any edit to the form clears the pair download controls, for the same reason the action
button reverts to Generate: the cylinders behind those buttons were built to settings that
are no longer on screen.

### Interaction with the button state machine (Section 8)

The pair run drives the shipped state machine rather than replacing it. Each plate switch
and each finished plate re-enables `#action-btn` on the way past, so the runner re-asserts
the lock (disabled, "Generating...") immediately afterwards — with no `await` between, so
no click can land in the gap. `resetToGenerateState()` is called at the end **before** the
button is re-enabled, because it skips its work entirely when the button already looks
idle. After a pair run the action button always reads "Generate STL".

### Accessibility notes

- Keyboard: Tab reaches Generate Both from the action button; both Enter and Space run it;
  focus is returned to the button after the run instead of being dropped to `<body>` by the
  disable.
- `#pair-status` is the only progress channel that persists across both runs; the
  `#error-message` overlay continues to carry the per-plate progress and errors.
- The new controls reuse `--btn-primary-bg` and `--btn-success-bg`, the tokens the shipped
  action button already uses. **Known pre-existing issue, not introduced here:** white text
  on `--btn-success-bg` measures 3.76:1 (dark) / 2.54:1 (light) and white on the
  `--btn-primary-bg` gradient measures 4.06:1 falling to 2.28:1 across the gradient — both
  under the 4.5:1 text threshold. axe-core flags the shipped "Download STL" button with the
  same 3.76:1 finding, and misses the gradient buttons entirely because a `background-image`
  defeats its sampling (which is why Lighthouse still reports 100). Fixing it means changing
  shared design tokens app-wide; that decision belongs to the accessibility phase, not here.

---

## Appendix A: Worker File Locations

| File | Path | Purpose |
|------|------|---------|
| Standard CSG Worker | `static/workers/csg-worker.js` | CSG for flat cards (three-bvh-csg) |
| Manifold CSG Worker | `static/workers/csg-worker-manifold.js` | CSG for cylinders (Manifold WASM, guarantees manifold) |
| Three.js | `static/three.module.js` | 3D library |
| BVH CSG | `static/vendor/three-bvh-csg/index.module.js` | Boolean operations for standard worker |
| Mesh BVH | `static/vendor/three-mesh-bvh/index.module.js` | BVH acceleration |
| STL Exporter | `static/examples/STLExporter.js` | Binary export |

---

## Appendix B: Troubleshooting Guide

### STL Won't Generate

1. Check browser console for errors
2. Verify worker initialized: `console.log(workerReady)` or `console.log(manifoldWorkerReady)`
3. Check network tab for `/geometry_spec` failures
4. Try hard refresh (Ctrl+Shift+R)

### Generated STL is Invalid

1. Import into slicer, check for errors
2. For cylinders, verify Manifold worker is being used (guaranteed manifold output)
3. Check for non-manifold edges in slicer
4. Try a different browser

### Generation is Slow

1. Check model complexity (dot count)
2. Close other browser tabs
3. Check browser memory usage
4. For first cylinder generation, WASM loading adds 2-3 seconds

### Worker Fails to Initialize

1. Check browser supports module workers (Chrome 80+, Firefox 114+, Safari 15+)
2. Verify all files exist in `/static/`
3. Check for CORS errors
4. Try hard refresh (Ctrl+Shift+R)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-06 | Initial specification document |
| 1.1 | 2024-12-08 | **BUG FIX:** CSG worker integration. Frontend now properly initializes CSG worker and uses client-side generation exclusively. Server-side fallback disabled. Updated Sections 1, 2, and 9. |
| 1.2 | 2024-12-08 | **BUG FIX:** Manifold worker integration. Cylinders now use `csg-worker-manifold.js` for guaranteed manifold output. Added dual-worker architecture with automatic shape-based routing. |
| 1.3 | 2024-12-08 | **NO FALLBACK ENFORCEMENT:** Removed fallback from Manifold to standard worker for cylinders. Cylinder generation now requires Manifold worker; displays error if unavailable. Updated Sections 9 and 12. |
| 1.4 | 2026-07-30 | **FILE NAMING:** Replaced `Embossing_Plate_{word}` / `Universal_Counter_Plate_{counter}` with `Embossing_Cylinder_{preset}_{name}` / `Counter_Cylinder_{preset}_{name}`. The session counter is gone; counter plates are named from the same text, and braille-only input is back-translated for the name. Rewrote Section 7. |
| 1.6 | 2026-08-17 | **PAIRED GENERATION (Phase 04):** Added Section 15 — the Generate Both Cylinders control, the two-run sequence, the identical-settings contract (including the `#grid_columns` re-fill that had to be restored around each plate switch), the abort-on-first-failure rule, the dual automatic/manual download design and the browsers it was measured in, and how the pair run drives the Section 8 state machine. The former `form.onsubmit` body is now `runGenerateForCurrentPlate()`, shared by both paths. |
| 1.7 | 2026-08-18 | **Paired download is no longer automatic (accessibility).** An NVDA run hit Chrome's "wants to: Download multiple files" prompt, which the page cannot relabel - it names no file, gives no reason, and Tab cycles Close/Allow/Block indefinitely - and the run ended in "Download blocked" with neither cylinder saved. The status line meant to rescue that case was never announced either, because the Save As dialog from the first automatic download had already taken focus off the page. Both automatic `downloadPairFile()` calls removed; each cylinder is now saved by pressing its own button, so one gesture never produces more than one download. The 2026-08-17 measurement that found this safe was taken without a screen reader running. Section 15 step 6 and the Downloads subsection rewritten; completion wording replaced, **signed off by Brennen 2026-08-18**. Verified: 0 automatic downloads, both buttons shown, focus retained on Generate Both, one file per button press |
| 1.8 | 2026-08-18 | **Generate and Download split into two controls (accessibility).** Section 8 rewritten. `#action-btn` no longer renames itself into a download control while the user's focus sits on it; a separate `#download-stl-btn` appears beside it, matching the pair buttons. Also fixed in the same pass: (a) progress messages had never displayed for ANYONE - the `#error-message` box was emptied between runs but never declassed, and `restoreThicknessPreset()` leaves an `error-message` class on every page load, which the "is a blocking error showing?" guard read as real, so `runGenerateForCurrentPlate()` now clears the class too; (b) nothing in the single-plate flow could announce at all (WCAG 4.1.3) - the box is now mirrored to `#a11y-status` by one MutationObserver covering all ~20 call sites, and its `role="alert"`/`aria-live` removed to prevent double-speak; (c) the old visible "Download STL" vs spoken "Download generated STL file" failed WCAG 2.5.3 Label in Name. New completion announcement and the new button name both **signed off by Brennen 2026-08-18**. Verified: action button never leaves data-state=generate, validation/progress/completion all spoken, one file per press, form edits retract the download, 310x44px, contrast 7.25/8.35/15.18:1 |
| 1.5 | 2026-08-16 | **DOUBLE-SIDED NAMING (Phase 09):** When the Double-Sided Card beta is on, downloads are named `Cylinder_A_{preset}_{name}` (positive) / `Cylinder_B_{preset}_{name}` (negative); both take `{name}` from the front text. Single-sided names unchanged. Updated Section 7; covered by tests/e2e/doubleSided.spec.ts. |
| 1.9 | 2026-08-21 | **Documentation only — no behavior change.** Removed the last `templates/index.html` citations (that folder is empty and deprecated). The Source Priority list now names one frontend file; the two `// From templates/index.html - NO FALLBACK` code comments now name `public/index.html`; and Section 4's Worker Initialization source now points at the CSG worker setup inside the `window` `load` handler, flagging the `initCSGWorker()` snippet as illustrative because no function of that name exists in the real code. Part of the templates/ reference sweep (Phase 07b). |

---

## Related Specifications

- [UI_INTERFACE_CORE_SPECIFICATIONS.md](./UI_INTERFACE_CORE_SPECIFICATIONS.md) — Button styling and states
- [BRAILLE_DOT_SHAPE_SPECIFICATIONS.md](./BRAILLE_DOT_SHAPE_SPECIFICATIONS.md) — Dot geometry details
- [RECESS_INDICATOR_SPECIFICATIONS.md](./RECESS_INDICATOR_SPECIFICATIONS.md) — Marker specifications
- [BRAILLE_SPACING_SPECIFICATIONS.md](./BRAILLE_SPACING_SPECIFICATIONS.md) — Layout calculations
- [LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md](./LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md) — Translation system
