# Liblouis Translation Core Specifications

## Document Purpose

This document specifies the core translation process that converts user input text to braille using the **Liblouis** open-source braille translation library. It serves as an authoritative reference for future development by documenting:

1. **Translation Architecture** — Client-side translation via Web Worker with WASM backend
2. **Liblouis Integration** — Library initialization, table loading, and translation execution
3. **Table Chain System** — How translation tables are combined and resolved
4. **Unicode Braille Output** — Ensuring consistent U+2800–U+28FF output
5. **Validation Pipeline** — Frontend and backend validation of braille characters
6. **Table Discovery** — Dynamic discovery and metadata extraction from table files
7. **Error Handling** — Graceful degradation and detailed error reporting

**Source Priority (Order of Correctness):**
1. `backend.py` — Primary authoritative source (table scanning, request validation, braille validation)
2. `wsgi.py` — Entry point configuration and environment detection
3. `static/workers/csg-worker.js` — Client-side geometry processing (consumes translated braille)
4. Manifold WASM — Mesh repair operations (no direct translation involvement)

**Additional Critical Sources:**
- `static/liblouis-module-worker.js` — the translation worker (a module worker)
- `static/liblouis-engine.js` — the liblouis 3.39.0 engine module the worker runs
- `app/validation.py` — Backend validation module for braille Unicode
- `app/utils.py` — Utility functions including `braille_to_dots()` conversion

---

## Table of Contents

1. [Translation Architecture Overview](#1-translation-architecture-overview)
2. [Liblouis Library Integration](#2-liblouis-library-integration)
3. [Web Worker Implementation](#3-web-worker-implementation)
4. [Translation Table System](#4-translation-table-system)
5. [Table Chain Construction](#5-table-chain-construction)
6. [Unicode Braille Output Standard](#6-unicode-braille-output-standard)
7. [Frontend Translation Pipeline](#7-frontend-translation-pipeline)
8. [Backend Validation Pipeline](#8-backend-validation-pipeline)
9. [Braille-to-Dots Conversion](#9-braille-to-dots-conversion)
10. [Table Discovery and Metadata](#10-table-discovery-and-metadata)
11. [Error Handling and Recovery](#11-error-handling-and-recovery)
12. [Cross-Implementation Consistency](#12-cross-implementation-consistency)
13. [Implementation Verification Report](#13-implementation-verification-report)

---

## 1. Translation Architecture Overview

### Design Philosophy

The translation system follows a **client-side translation** architecture where:

1. **All text-to-braille translation happens in the browser** using a Web Worker
2. **Backend receives pre-translated braille Unicode** and validates it
3. **Backend never performs translation** — it only validates and processes braille

This design choice provides:
- Reduced server load and compute costs
- Faster user feedback (no network round-trip for translation)
- Offline-capable translation after initial page load
- Scalability without server-side Liblouis installation

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                         │
│  ┌─────────────────────┐    ┌─────────────────┐                             │
│  │ Text Input          │    │ Language Table  │                             │
│  │ (e.g., "Hello")     │    │ (en-ueb-g1.ctb) │                             │
│  └──────────┬──────────┘    └────────┬────────┘                             │
│             │                        │                                       │
│             ▼                        ▼                                       │
│  ┌──────────────────────────────────────────────┐                           │
│  │         FRONTEND (index.html)                 │                           │
│  │  • Collects text from input fields           │                           │
│  │  • Determines language table per line        │                           │
│  │  • Sends translation request to worker       │                           │
│  └───────────────────────┬──────────────────────┘                           │
│                          │                                                   │
│                          ▼                                                   │
│  ┌──────────────────────────────────────────────┐                           │
│  │      LIBLOUIS WEB WORKER                      │                           │
│  │  (static/liblouis-module-worker.js)           │                           │
│  │                                               │                           │
│  │  1. Load liblouis 3.39.0 (WebAssembly)        │                           │
│  │  2. Fetch the table + includes via HTTP       │                           │
│  │  3. Construct table chain (unicode.dis + X)   │                           │
│  │  4. Call lou_translate()                      │                           │
│  │  5. Validate output has U+2800–U+28FF chars   │                           │
│  │  6. Return braille + input positions          │                           │
│  └───────────────────────┬──────────────────────┘                           │
│                          │                                                   │
│                          ▼                                                   │
│  ┌──────────────────────────────────────────────┐                           │
│  │       FRONTEND RECEIVES BRAILLE               │                           │
│  │  • Displays in preview (with shorthand)       │                           │
│  │  • Stores for form submission                 │                           │
│  └───────────────────────┬──────────────────────┘                           │
│                          │ (On Generate STL)                                 │
│                          ▼                                                   │
│  ┌──────────────────────────────────────────────┐                           │
│  │        BACKEND (backend.py)                   │                           │
│  │                                               │                           │
│  │  1. Receive lines[] as braille Unicode        │                           │
│  │  2. Validate all chars are U+2800–U+28FF      │                           │
│  │  3. Convert each char to dot pattern          │                           │
│  │  4. Generate 3D geometry from patterns        │                           │
│  └──────────────────────────────────────────────┘                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principle: Frontend-Only Translation

**Source:** `backend.py` (lines 745-756)

```python
# Check if input contains proper braille Unicode (U+2800 to U+28FF)
has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)

if has_braille_chars:
    braille_text = line_text  # Use directly
else:
    # Error: frontend must translate before sending
    error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters. ' \
                'Frontend must translate text to braille before sending.'
    raise RuntimeError(error_msg)
```

---

## 2. Liblouis Library Integration

### Library Components

The engine is **liblouis 3.39.0 compiled to WebAssembly**, vendored in `static/vendor/liblouis-3.39.0/` and copied byte for byte from openscad-assistive-forge `4355e8a` (decision E3). Its `README.txt` records the source, the build flags, the checksums and the licences, and `tests/test_vendored_liblouis.py` checks every byte.

| Component | File | Purpose |
|-----------|------|---------|
| Engine | `static/vendor/liblouis-3.39.0/liblouis.wasm` | liblouis 3.39.0, built with 32-bit characters (`--enable-ucs4`) and no `eval` (`DYNAMIC_EXECUTION=0`) |
| Loader | `static/vendor/liblouis-3.39.0/liblouis.js` | The emscripten ES module that instantiates the wasm |
| Tables | `static/vendor/liblouis-3.39.0/tables/` | The release's 478 table files: 323 translation tables and the files they include |
| Table index | `static/vendor/liblouis-3.39.0/tables.json` | Each file's size and SHA-256, and each table's include closure; written only by `scripts/build_liblouis_tables_index.py` |
| Engine module | `static/liblouis-engine.js` | Loads the wasm once, installs tables in its file system, translates and back-translates |
| Worker | `static/liblouis-module-worker.js` | The module worker the page talks to |

### Static File Directory Structure

```
static/
├── liblouis-engine.js
├── liblouis-module-worker.js
└── vendor/
    └── liblouis-3.39.0/
        ├── liblouis.wasm
        ├── liblouis.js
        ├── README.txt                # source, build, checksums, licences
        ├── COPYING.LESSER.liblouis
        ├── tables.json               # sizes, checksums, include closures
        └── tables/                   # 478 files
            ├── unicode.dis           # Unicode display table (CRITICAL)
            ├── en-ueb-g1.ctb
            ├── en-ueb-g2.ctb
            └── ...
```

The release is in the folder name so that the 24-hour `immutable` cache `serve_static()` in `backend.py` sets on `.js`, `.wasm`, `.json` and table files can never mix two releases.

### Library Version Information

- liblouis 3.39.0: `version()` in `static/liblouis-engine.js` reads it from the engine, and the worker's `init` answer names it.
- Tables are not built into the wasm. Each is fetched over HTTP, with the files it includes, before its first use (Section 3).
- Text crosses into liblouis as code points (32-bit characters), so an emoji counts as one character, not two.
- Checked against native liblouis 3.39.0 (`lou_translate` from the official Windows release): the 145-row English corpus in both UEB grades, and three samples in each of the 323 translation tables, give the same cells (`tests/frontend/liblouis-engine.test.js`, decision E2).
- Until 2026-10-09 the app ran a 2017 asm.js build of liblouis 3.2.0 (npm `liblouis-build` with `easy-api.js`); the engine round removed it.

---

## 3. Web Worker Implementation

### Why a Web Worker?

The translation runs in a dedicated module worker (`new Worker('/static/liblouis-module-worker.js', { type: 'module' })`) because:

1. **Non-blocking UI** — compiling a table and translating never hold up the page
2. **Isolation** — a failure inside liblouis cannot take the page down with it
3. **Modules** — the worker imports `static/liblouis-engine.js` and the vendored loader as ES modules, as the Manifold worker does

### Worker Initialization Sequence

**Source:** `static/liblouis-module-worker.js` — `initialize()`

```javascript
async function initialize() {
    mod = await loadLiblouis(() => import(`${VENDOR}liblouis.js`));
    const response = await fetch(`${VENDOR}tables.json`);
    if (!response.ok) throw new Error(`Could not load the table index: HTTP ${response.status}`);
    index = await response.json();
    await ensureTable(DEFAULT_TABLE);
    // One translation proves the engine and the default table work end to end.
    translate(mod, DEFAULT_TABLE, 'test');
    return { success: true, message: `liblouis ${version(mod)} ready` };
}
```

### Initialization Steps Detail

| Step | Action | Purpose |
|------|--------|---------|
| 1 | The page fetches the worker file, then starts it as a module worker | A missing file fails before the worker exists |
| 2 | `loadLiblouis()` imports the loader and instantiates the wasm | Once per worker; a failed load does not block a later attempt |
| 3 | Fetch `tables.json` | Which files each table needs |
| 4 | `ensureTable('en-ueb-g2.ctb')` | Fetch the default table's closure, and `unicode.dis`'s, into the module's file system |
| 5 | Test translation | Proves the engine and the default table work end to end |

The page waits up to 30 s for `init`. Until it answers, a Translate press waits for start-up to end (`liblouisSettled`) instead of failing; if start-up fails, `#error-text` says so and translation stays off.

### Loading a Table

**Source:** `static/liblouis-module-worker.js` — `ensureTable()`

Before a table's first use the worker fetches each file of its closure (and of `unicode.dis`'s) that it does not have yet from `/static/vendor/liblouis-3.39.0/tables/`, and writes them into the module's file system under `/tables`, where liblouis finds a table's includes beside it. A table that `tables.json` does not list is refused ("Unknown liblouis table"), and a file that does not arrive fails the request with its HTTP status. A table nobody picks is never downloaded.

### Worker Message Protocol

**Request Types:**

| Type | Description | Data Fields |
|------|-------------|-------------|
| `init` | Initialize worker | (none) |
| `translate` | Translate text to braille | `text`, `grade`, `tableName` |
| `backTranslate` | Translate braille back to text | `braille`, `tableName` |

`ALLOWED_TYPES` in `static/liblouis-module-worker.js` is the allowlist; a type outside it is
rejected before any liblouis call, and each type validates its own required data field.

**Request Format:**

```javascript
{
    id: Number,           // Unique ID for response matching
    type: 'translate',    // Message type
    data: {
        text: String,     // Original text to translate
        grade: String,    // 'g1' or 'g2' (fallback if tableName is null)
        tableName: String // Liblouis table filename (e.g., 'en-ueb-g2.ctb'); a
                          // 'unicode.dis,<table>' chain from an older caller names the same table
    }
}
```

**Response Format:**

```javascript
{
    id: Number,           // Matches request ID
    type: 'translate',    // Message type
    result: {
        success: Boolean,
        translation: String,  // Unicode braille output (on success); a blank cell is the ASCII space
        inputPos: Number[],   // for each cell, the index in text of the character it came from
        error: String         // Error message (on failure)
    }
}
```

### Back-Translation (`backTranslate`)

Calls `backTranslate(mod, table, braille)` in `static/liblouis-engine.js`, which calls
`lou_backTranslateString` with the same table list as the forward pass, `unicode.dis` first,
because that is what makes liblouis read the U+2800 block as braille cells rather than as
literal characters.

```javascript
// Request
{ id: Number, type: 'backTranslate', data: { braille: String, tableName: String } }

// Response
{ id: Number, type: 'backTranslate', result: { success: Boolean, text: String, error: String } }
```

Two callers in `public/index.html`:

1. **"Translate to Text ↑"** — fills the text entry area from the Braille (Unicode) field so
   a reader can check pasted braille in English. The braille field is left untouched: it
   remains the authority for what gets embossed.
2. **STL file naming** — when braille was pasted with no source text, the first word of the
   back-translation supplies the `{name}` segment of the download filename. See
   `STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md` §7.

Back-translation is **never** part of the generation path. It is a convenience for reading
and naming only, so a lossy round-trip (contractions, capital indicators) can never change
the geometry that gets produced.

---

## 4. Translation Table System

### Table Types

| Extension | Type | Purpose |
|-----------|------|---------|
| `.ctb` | Contraction table | Full translation rules for a language |
| `.utb` | Translation table | Character mappings, usually uncontracted |
| `.tbl` | Translation table | The same, under an older naming |
| `.cti` / `.uti` | Include file | Part of other tables; never offered alone |
| `.dis` | Display table | Output character encoding |
| `.dic` | Hyphenation dictionary | Included by some tables |

The language list offers the `.ctb`, `.utb` and `.tbl` files (Section 10).

### Critical Tables

| Table | Purpose | Required |
|-------|---------|----------|
| `unicode.dis` | Forces Unicode braille output (U+2800–U+28FF) | **YES** |
| `en-ueb-g2.ctb` | English UEB contracted (grade 2) | **Default** — matches BANA's *Guidelines for Brailling Business Cards* (March 2024) |
| `en-ueb-g1.ctb` | English UEB uncontracted (grade 1) | Optional |

### Table File Format

A table opens with metadata lines; these are `en-ueb-g2.ctb`'s. Nothing in the app reads them today (Section 10).

```
#-display-name: Unified English contracted braille
#+language:en
#+type:literary
#+contraction:full
#+grade:2
#+system:ueb

# Translation rules follow...
include en-ueb-g1.ctb
```

### Backend Table List

The language dropdown's list of tables comes from `GET /liblouis/tables`; see Section 10.

---

## 5. Table Chain Construction

### The Unicode Display Table Requirement

**CRITICAL:** For proper braille Unicode output, `unicode.dis` must be the **first** table in the list liblouis is given.

**Source:** `static/liblouis-engine.js` — `tableList()`

```javascript
function tableList(table) {
  checkTableName(table);
  return `${TABLE_DIR}/${DISPLAY_TABLE},${TABLE_DIR}/${table}`;
}
```

The page sends one table file name. The worker's `tableOf()` drops a `unicode.dis` an older caller put first, so the list never names it twice, and refuses anything that is not exactly one table.

### Table Chain Examples

| User-Selected Table | Table list given to liblouis |
|--------------------|-------------------|
| `en-ueb-g1.ctb` | `/tables/unicode.dis,/tables/en-ueb-g1.ctb` |
| `en-ueb-g2.ctb` | `/tables/unicode.dis,/tables/en-ueb-g2.ctb` |
| `fr-bfu-g2.ctb` | `/tables/unicode.dis,/tables/fr-bfu-g2.ctb` |
| `unicode.dis,en-ueb-g2.ctb` | `/tables/unicode.dis,/tables/en-ueb-g2.ctb` |

### Why Table Chain Matters

Without `unicode.dis`:
- Output may be ASCII dot patterns (dots-123456 notation)
- Output may be empty
- Output encoding depends on table defaults

With `unicode.dis`:
- Output is always Unicode braille (U+2800–U+28FF)
- Consistent encoding across all language tables
- Compatible with browser rendering and backend validation

---

## 6. Unicode Braille Output Standard

### Braille Unicode Block

The Unicode braille block spans **U+2800 to U+28FF** (256 code points):

| Code Point | Character | Dots Present |
|------------|-----------|--------------|
| U+2800 | ⠀ | (none - blank) |
| U+2801 | ⠁ | 1 |
| U+2802 | ⠂ | 2 |
| U+2803 | ⠃ | 1, 2 |
| U+2804 | ⠄ | 3 |
| U+2805 | ⠅ | 1, 3 |
| ... | ... | ... |
| U+283F | ⠿ | 1, 2, 3, 4, 5, 6 |
| U+28FF | ⣿ | 1, 2, 3, 4, 5, 6, 7, 8 |

### Dot Encoding

Each Unicode braille character encodes dots as bits:

```
Dot positions:    Bit mapping:
  1 4              bit 0 = dot 1
  2 5              bit 1 = dot 2
  3 6              bit 2 = dot 3
  7 8              bit 3 = dot 4
                   bit 4 = dot 5
                   bit 5 = dot 6
                   bit 6 = dot 7
                   bit 7 = dot 8
```

**Formula:** `code_point = 0x2800 + dot_pattern`

Where `dot_pattern` is an 8-bit value with bit N set if dot (N+1) is raised.

### Constants Definition

**Source:** `app/utils.py` (lines 17-19)

```python
# Braille Unicode range
BRAILLE_UNICODE_START = 0x2800  # ⠀
BRAILLE_UNICODE_END = 0x28FF    # ⣿
```

**Source:** `app/validation.py` (lines 17-19)

```python
# Validation constants
BRAILLE_UNICODE_START = 0x2800
BRAILLE_UNICODE_END = 0x28FF
```

### Validation Function

**Source:** `app/utils.py` (lines 63-77)

```python
def is_braille_char(char: str) -> bool:
    """
    Check if a character is a braille Unicode character.

    Args:
        char: Single character to check

    Returns:
        True if character is in braille Unicode range
    """
    if not char or len(char) != 1:
        return False
    code = ord(char)
    return BRAILLE_UNICODE_START <= code <= BRAILLE_UNICODE_END
```

---

## 7. Frontend Translation Pipeline

### Translation Request Function

**Source:** `public/index.html` — the `translateWithLiblouis()` wrapper (simplified below)

```javascript
// Frontend wrapper for translation via web worker
async function translateWithLiblouis(text, grade, tableName) {
    return new Promise((resolve, reject) => {
        const id = Date.now() + Math.random();

        const handler = (e) => {
            if (e.data.id !== id) return;
            worker.removeEventListener('message', handler);

            if (e.data.result.success) {
                resolve(e.data.result.translation);
            } else {
                reject(new Error(e.data.result.error));
            }
        };

        worker.addEventListener('message', handler);
        worker.postMessage({
            id: id,
            type: 'translate',
            data: { text, grade, tableName }
        });
    });
}
```

### UI Post-Processing: Number Signs Radio Group (Non-Standard Option, Default Off)

`translateWithLiblouis()` in `public/index.html` applies one optional post-processing step to the worker's translation result before returning it: `applyNumberSignRepeat()`.

- Standard UEB (and liblouis with `en-ueb-g1.ctb`/`en-ueb-g2.ctb`) treats `.` and `,` as numeric-mode continuation characters (`numericmodechars .,`), so `206.616.7678` yields ONE number sign: `⠼⠃⠚⠋⠲⠋⠁⠋⠲⠛⠋⠛⠓` (13 cells).
- A **hyphen or parenthesis is not** a numeric-mode continuation character, so `206-543-4779` correctly yields THREE number signs: `⠼⠃⠚⠋⠤⠼⠑⠙⠉⠤⠼⠙⠛⠛⠊` (15 cells). This is unmodified liblouis output and no app setting changes it.
- When the user selects "Repeat the number sign after each period (non-standard)" (`input[name="repeat_number_sign"][value="on"]`, persisted as `braille_prefs_repeat_number_sign`), a `⠼` is re-inserted after every period/comma that is followed by a digit cell, matching some online translators at the cost of extra cells.
- The post-processing is centralized inside `translateWithLiblouis()` so the preview, computer shorthand, BANA auto-wrap length measurement, overflow detection, and STL generation all consume the identical string. The liblouis worker itself is never modified.

See `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md` section 6.2 for the full UI/behavior specification.

### Bypass: Editable Unicode Braille Field

Translation is **100% liblouis and stays that way**, but the user may opt out of translation entirely. When the Braille (Unicode) field (`#braille-unicode`) is non-empty, `form.onsubmit` uses its lines verbatim and never calls `translateWithLiblouis()`; `original_lines` still carries the English inputs when they are non-empty (they drive the per-row indicator letters) and is sent as `null` only when braille was pasted with the English inputs left empty. The field is populated by the Translate to Braille button (which runs the normal pipeline), by every Generate STL (since 2026-09-28 it writes the translation it embosses into the field), or by the user pasting braille directly. A field the user has not edited empties itself when the text or an effective translation setting changes; an edited one is never touched.

This is a bypass of translation, not an alternative translator: the app never rewrites braille the user typed, and it never guesses what English text produced it.

See `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md` section 6.3.

### Manual Mode Translation

For manual placement mode, each line is translated independently:

```javascript
// Per-line translation in manual mode
perLineLanguageTables = new Array(lines.length).fill(tableName);
for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line) {
        try {
            const perLineTable = (document.getElementById(`line_lang_${i+1}`)?.value) || tableName;
            perLineLanguageTables[i] = perLineTable;
            const brailleText = await translateWithLiblouis(line, 'g2', perLineTable);
            translatedLines.push(brailleText);
        } catch (error) {
            translationErrors.push({ line: i + 1, text: line, error: error.toString() });
            translatedLines.push('');
        }
    } else {
        translatedLines.push('');
    }
}
```

### Auto Mode Translation (BANA Wrapping)

For auto placement mode, translation happens during the wrapping process:

```javascript
// Translation during BANA auto-wrap
async function translateLen(text) {
    const b = await translateWithLiblouis(text, 'g2', tableName);
    return b.length;
}

async function translateText(text) {
    return await translateWithLiblouis(text, 'g2', tableName);
}
```

The whole-line layout (`layoutParagraph()`, `static/braille-wrap.js`) translates through `translateForLayout()`, which asks the worker for each cell's input position too (`translateWithLiblouisPositions()`); see `BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md` Section 9.

### Worker-Side Translation Execution

**Source:** `static/liblouis-module-worker.js` — `handle()`

```javascript
case 'translate': {
    requireReady();
    const table = tableOf(data.tableName, data.grade);
    await ensureTable(table);
    const { braille, inputPos } = translate(mod, table, data.text);
    if (braille.length === 0) throw new Error(`Translation failed for table ${table}: liblouis returned an empty result`);
    if (![...braille].some((ch) => ch.codePointAt(0) >= 0x2800 && ch.codePointAt(0) <= 0x28ff)) {
        throw new Error(`Translation failed for table ${table}: no braille in the output`);
    }
    return { success: true, translation: braille, inputPos };
}
```

With no table name, `grade` picks `en-ueb-g1.ctb` (`'g1'`) or `en-ueb-g2.ctb`. `translate()` in `static/liblouis-engine.js` sizes its output from the text and doubles it, up to three times, when liblouis stops short; a translation that did not consume the whole text is an error, never returned as if it were whole. A blank cell comes back as the ASCII space (project-facts invariant 4): `unicode.dis` writes it as U+2800 in 3.39.0 (and wrote a space in 3.2.0). `inputPos` gives, for each cell, the index in `text` of the character it came from, in JavaScript string units.

---

## 8. Backend Validation Pipeline

### Validation Order

When a request arrives at `/generate_braille_stl`:

```
1. Validate request is JSON
2. Extract request fields (lines, settings, etc.)
3. validate_lines(lines, rows) — Basic input validation (rows = the request's grid_rows)
4. validate_settings(settings_data) — Settings range validation
5. validate_braille_lines(lines, plate_type) — Braille Unicode validation
6. Validate plate_type, grade, shape_type
7. Process request
```

### Lines Validation

**Source:** `app/validation.py` (lines 30-71)

```python
def validate_lines(lines: Any, rows: int = 4) -> bool:
    """
    Validate the lines input for security and correctness.
    """
    if not isinstance(lines, list):
        raise ValidationError('Lines must be a list', {'type': type(lines).__name__})

    # MAX_LINES is 200, the Rows dial's ceiling (it was 4 until 2026-10-09).
    if len(lines) > MAX_LINES:
        raise ValidationError(
            f'Too many lines provided. Maximum is {MAX_LINES} lines.',
            {'provided': len(lines), 'max': MAX_LINES}
        )
    # A line past the request's Rows must be empty (see BRAILLE_SPACING §12);
    # the per-line checks below are unchanged.

    for i, line in enumerate(lines):
        if not isinstance(line, str):
            raise ValidationError(
                f'Line {i + 1} must be a string',
                {'line_number': i + 1, 'type': type(line).__name__}
            )

        # Check length
        if len(line) > MAX_LINE_LENGTH:
            raise ValidationError(
                f'Line {i + 1} is too long (max {MAX_LINE_LENGTH} characters)',
                {'line_number': i + 1, 'length': len(line), 'max': MAX_LINE_LENGTH}
            )

        # Check for harmful characters
        harmful_chars = ['<', '>', '&', '"', "'", '\x00']
        found_harmful = [char for char in harmful_chars if char in line]
        if found_harmful:
            raise ValidationError(
                f'Line {i + 1} contains invalid characters: {found_harmful}',
                {'line_number': i + 1, 'invalid_chars': found_harmful}
            )

    return True
```

### Braille Unicode Validation

**Source:** `app/validation.py` (lines 74-131)

```python
def validate_braille_lines(lines: List[str], plate_type: str = 'positive') -> bool:
    """
    Validate that lines contain valid braille Unicode characters.

    Only validates non-empty lines for positive plates (counter plates generate all dots).
    """
    if plate_type != 'positive':
        return True  # Counter plates don't need braille validation

    errors = []

    for i, line in enumerate(lines):
        if line.strip():  # Only validate non-empty lines
            for j, char in enumerate(line):
                # Allow standard ASCII space characters (represent blank cells)
                if char == ' ':
                    continue

                char_code = ord(char)
                if char_code < BRAILLE_UNICODE_START or char_code > BRAILLE_UNICODE_END:
                    errors.append({
                        'line': i + 1,
                        'position': j + 1,
                        'character': char,
                        'char_code': f'U+{char_code:04X}',
                        'expected': f'U+{BRAILLE_UNICODE_START:04X} to U+{BRAILLE_UNICODE_END:04X}'
                    })

    if errors:
        error_details = []
        for err in errors[:5]:  # Show first 5 errors
            error_details.append(
                f'Line {err["line"]}, position {err["position"]}: '
                f"'{err['character']}' ({err['char_code']}) is not a valid braille character"
            )

        if len(errors) > 5:
            error_details.append(f'... and {len(errors) - 5} more errors')

        raise ValidationError(
            'Invalid braille characters detected. Translation may have failed.\n'
            + '\n'.join(error_details)
            + '\n\nPlease ensure text is properly translated to braille before generating STL.',
            {'error_count': len(errors), 'errors': errors[:10]}
        )

    return True
```

### Inline Validation in Mesh Generation

**Source:** `backend.py` (lines 745-756)

```python
# Frontend must send proper braille Unicode characters
# Check if input contains proper braille Unicode (U+2800 to U+28FF)
has_braille_chars = any(ord(char) >= 0x2800 and ord(char) <= 0x28FF for char in line_text)

if has_braille_chars:
    # Input is proper braille Unicode, use it directly
    braille_text = line_text
else:
    # Input is not braille Unicode - this is an error
    error_msg = f'Line {row_num + 1} does not contain proper braille Unicode characters. ' \
                'Frontend must translate text to braille before sending.'
    logger.error(f'{error_msg}')
    raise RuntimeError(error_msg)
```

### Validation Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      REQUEST VALIDATION PIPELINE                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐                                                      │
│  │ POST Request   │                                                      │
│  │ /generate_stl  │                                                      │
│  └───────┬────────┘                                                      │
│          │                                                               │
│          ▼                                                               │
│  ┌────────────────┐   No   ┌─────────────────┐                          │
│  │ Is JSON?       │───────▶│ 400: Not JSON   │                          │
│  └───────┬────────┘        └─────────────────┘                          │
│          │ Yes                                                           │
│          ▼                                                               │
│  ┌────────────────┐   Fail  ┌─────────────────┐                         │
│  │ validate_lines │────────▶│ 400: Line Error │                         │
│  │ - Is list?     │         └─────────────────┘                         │
│  │ - ≤ Rows lines?│                                                     │
│  │ - All strings? │                                                     │
│  │ - ≤50 chars?   │                                                     │
│  │ - No XSS?      │                                                     │
│  └───────┬────────┘                                                     │
│          │ Pass                                                          │
│          ▼                                                               │
│  ┌────────────────────────┐   Fail  ┌─────────────────────────────┐     │
│  │ validate_braille_lines │────────▶│ 400: Invalid Braille Chars  │     │
│  │ (positive plates only) │         │ - Shows first 5 errors      │     │
│  │ - All chars U+2800–FF? │         │ - Lists invalid positions   │     │
│  │ - Spaces allowed       │         └─────────────────────────────┘     │
│  └───────┬────────────────┘                                             │
│          │ Pass                                                          │
│          ▼                                                               │
│  ┌────────────────┐                                                     │
│  │ Process Request │                                                    │
│  │ Generate STL    │                                                    │
│  └─────────────────┘                                                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Braille-to-Dots Conversion

### Conversion Function

**Source:** `app/utils.py` (lines 96-133)

```python
def braille_to_dots(braille_char: str) -> list:
    """
    Convert a braille character to dot pattern.

    Braille dots are arranged as:
    1 4
    2 5
    3 6

    Args:
        braille_char: Single braille Unicode character

    Returns:
        List of 6 integers (0 or 1) representing dot pattern
    """
    # Braille Unicode block starts at U+2800
    if not braille_char or braille_char == ' ':
        return [0, 0, 0, 0, 0, 0]  # Empty cell

    # Get the Unicode code point
    code_point = ord(braille_char)

    # Check if it's in the braille Unicode block
    if code_point < 0x2800 or code_point > 0x28FF:
        return [0, 0, 0, 0, 0, 0]  # Not a braille character

    # Extract the dot pattern (bits 0-7 for dots 1-8)
    dot_pattern = code_point - 0x2800

    # Convert to 6-dot pattern (dots 1-6)
    dots = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        if dot_pattern & (1 << i):
            dots[i] = 1

    return dots
```

### Dot Position Mapping

```
Standard 6-dot braille cell:      Array index mapping:

  ┌───┬───┐                        dots[0] = dot 1
  │ 1 │ 4 │                        dots[1] = dot 2
  ├───┼───┤                        dots[2] = dot 3
  │ 2 │ 5 │                        dots[3] = dot 4
  ├───┼───┤                        dots[4] = dot 5
  │ 3 │ 6 │                        dots[5] = dot 6
  └───┴───┘
```

### Example Conversions

| Character | Unicode | Binary Pattern | Dots Array |
|-----------|---------|----------------|------------|
| ⠁ (a) | U+2801 | 0b00000001 | [1,0,0,0,0,0] |
| ⠃ (b) | U+2803 | 0b00000011 | [1,1,0,0,0,0] |
| ⠇ (l) | U+2807 | 0b00000111 | [1,1,1,0,0,0] |
| ⠿ (all) | U+283F | 0b00111111 | [1,1,1,1,1,1] |
| ⠀ (blank) | U+2800 | 0b00000000 | [0,0,0,0,0,0] |

### Usage in Geometry Generation

**Source:** `backend.py` (lines 776-799)

```python
# Process each braille character in the line
for col_num, braille_char in enumerate(braille_text):
    if col_num >= available_columns:
        break

    dots = braille_to_dots(braille_char)

    # Calculate X position for this column
    x_pos = (
        settings.left_margin
        + ((col_num + (1 if getattr(settings, 'indicator_shapes', 1) else 0)) * settings.cell_spacing)
        + settings.braille_x_adjust
    )

    # Create dots for this cell
    for dot_idx, dot_val in enumerate(dots):
        if dot_val == 1:  # Only create raised dots
            dot_x, dot_y = get_dot_position(dot_idx, x_pos, y_pos, settings)
            z = settings.card_thickness + settings.active_dot_height / 2
            dot_mesh = create_braille_dot(dot_x, dot_y, z, settings)
            meshes.append(dot_mesh)
```

---

## 10. Table Discovery and Metadata

### Backend Table List

**Source:** `backend.py` — `list_liblouis_tables()`

`GET /liblouis/tables` lists the translation tables (`.ctb`, `.utb`, `.tbl`) named in `static/vendor/liblouis-3.39.0/tables.json`, the index the translation worker fetches tables by, so every table it offers can be loaded. They are the 323 tables compared with native liblouis 3.39.0 (decision E2); `tests/test_vendored_liblouis.py` pins the list to `tests/fixtures/liblouis-reference/table-samples-3.39.0.json`. Include files (`.cti`, `.uti`, `.dis`, `.dic`) are not offered. Until the engine round's phase 7 (2026-10-09) the list was scanned from `static/liblouis/tables`, `node_modules/liblouis-build/tables` and a native 3.34.0 copy in `third_party/liblouis`, and offered include files and tables the worker could not load.

### Table Entry

```json
{
    "file": "en-ueb-g2.ctb",
    "path": "en-ueb-g2.ctb",
    "locale": "en-ueb",
    "description": "en-ueb-g2.ctb"
}
```

`locale` is the file name's first two hyphen-separated parts, or `null` when the name has no hyphen. No metadata is read from the tables. The parser that read their `#+` lines (grade, type, contraction, dots) was removed with server-side generation on 2026-01-05 (`8939c2d`). `loadLanguageOptions()` still reads those fields, so without them it labels a table by its `locale` and offers only the first table of each `locale`.

### Frontend Table Loading

**Source:** `public/index.html` — `loadLanguageOptions()`

```javascript
async function loadLanguageOptions() {
    const select = document.getElementById('language-table');

    // Fetch available tables from backend
    const resp = await fetch('/liblouis/tables', { credentials: 'same-origin' });
    const data = await resp.json();

    // Sort: English first, then by locale
    data.tables.sort((a, b) => {
        const aEn = (a.locale || '').toLowerCase().startsWith('en') ? 0 : 1;
        const bEn = (b.locale || '').toLowerCase().startsWith('en') ? 0 : 1;
        if (aEn !== bEn) return aEn - bEn;
        return (a.locale || '').localeCompare(b.locale || '');
    });

    // Build optgroups and options...
}
```

A saved choice (`localStorage.braille_prefs_language_table`) that is not among the options, such as a 3.2.0 table name that 3.39.0 does not ship, falls back to `DEFAULT_LANGUAGE_TABLE` (`en-ueb-g2.ctb`).

---

## 11. Error Handling and Recovery

### Translation Error Scenarios

| Error | Cause | Recovery |
|-------|-------|----------|
| Worker not initialized | The worker, wasm or table index failed to load | Display error, suggest refresh |
| Table not found | A name `tables.json` does not list, or a file that did not arrive | Display the error; a saved choice the list no longer offers falls back to UEB (Section 10) |
| Empty result | Invalid input or table issue | Display error with liblouis logs |
| No braille output | Table misconfiguration | Include recent logs in error |

### Worker Error Handling

**Source:** `static/liblouis-engine.js` — `failure()`; `static/liblouis-module-worker.js` — `onmessage`

The engine keeps the last 20 lines liblouis writes to stderr, and an error from a failed call ends with the last three of them, e.g. `liblouis could not translate this text with xx.ctb (…)`. The worker answers every failure as `{ success: false, error }`, and the page rejects the waiting request with that message.

### Backend Validation Errors

**Source:** `app/validation.py` (lines 22-28)

```python
class ValidationError(ValueError):
    """Custom exception for validation errors with structured details."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}
```

### Error Response Format

```json
{
    "error": "Invalid braille characters detected. Translation may have failed.\n..."
        + "Line 1, position 3: 'H' (U+0048) is not a valid braille character\n..."
        + "Please ensure text is properly translated to braille before generating STL.",
    "details": {
        "error_count": 5,
        "errors": [
            {
                "line": 1,
                "position": 3,
                "character": "H",
                "char_code": "U+0048",
                "expected": "U+2800 to U+28FF"
            }
        ]
    }
}
```

### Graceful Degradation

1. **Worker initialization failure:** Application displays error, user can retry
2. **Table loading failure:** Falls back to preloaded core tables
3. **Translation failure:** Shows error with debugging information
4. **Backend validation failure:** Detailed error message with fix suggestions

---

## 12. Cross-Implementation Consistency

### Unicode Range Consistency

All implementations use identical Unicode braille range constants:

| Location | Start | End | Status |
|----------|-------|-----|--------|
| `app/utils.py` (line 18-19) | `0x2800` | `0x28FF` | ✅ Canonical |
| `app/validation.py` (line 18-19) | `0x2800` | `0x28FF` | ✅ Matches |
| `backend.py` (line 747) | `0x2800` | `0x28FF` | ✅ Matches |
| `backend.py` (line 937) | `0x2800` | `0x28FF` | ✅ Matches |
| `app/geometry/plates.py` (line 128) | `0x2800` | `0x28FF` | ✅ Matches |
| `app/geometry/plates.py` (line 318) | `0x2800` | `0x28FF` | ✅ Matches |
| `app/geometry/cylinder.py` (line 153) | `0x2800` | `0x28FF` | ✅ Matches |
| `geometry_spec.py` (line 594) | `0x2800` | `0x28FF` | ✅ Matches |
| `static/liblouis-module-worker.js` (`handle()`, translate) | `0x2800` | `0x28FF` | ✅ Matches |

**Total: 9 locations verified consistent**

### Table Chain Construction Consistency

All paths that invoke translation use the same chain construction:

| Location | Table Chain Logic |
|----------|------------------|
| `static/liblouis-engine.js` (`tableList()`) | `/tables/unicode.dis,/tables/` + the table; `tableOf()` drops a leading `unicode.dis` first |
| Frontend preview | Uses worker (same logic) |
| Form submission | Uses worker (same logic) |

### Space Character Handling

| Location | Space Handling |
|----------|---------------|
| `app/utils.py` braille_to_dots() | Returns `[0,0,0,0,0,0]` for space |
| `app/validation.py` | Explicitly allows ASCII space (`char == ' '`) |
| `backend.py` | Space passes Unicode range check (not validated as braille) |

### braille_to_dots Function Usage Consistency

All geometry generation modules use the canonical `braille_to_dots` function from `app/utils.py`:

| Location | Import/Usage | Status |
|----------|--------------|--------|
| `backend.py` (line 66) | `from app.utils import braille_to_dots` | ✅ |
| `backend.py` (line 780, 959) | Direct usage | ✅ |
| `app/geometry/plates.py` (line 24) | `from app.utils import braille_to_dots` | ✅ |
| `app/geometry/plates.py` (line 161, 340) | Direct usage | ✅ |
| `app/geometry/cylinder.py` (line 21) | `from app.utils import braille_to_dots` | ✅ |
| `app/geometry/cylinder.py` (line 827) | Direct usage | ✅ |
| `geometry_spec.py` (line 28, 347) | Passed as `braille_to_dots_func` parameter | ✅ |
| `geometry_spec.py` (line 217, 610) | Usage via passed function | ✅ |

---

## 13. Implementation Verification Report

> **Note added 2026-08-21:** `templates/index.html` was removed from the repository after this verification ran; `public/index.html` is now the only HTML build. The tables in this section are left exactly as recorded on the verification date and have not been re-checked against `public/index.html`. For current locations see Appendix C and Section 7.

> **Note added 2026-10-09:** the worker rows below name `static/liblouis-worker.js`, the liblouis 3.2.0 worker removed by the engine round. They are left as recorded; Sections 3, 5, 7 and 11 describe its successor.

### Verification Date

2024-12-06

### Components Verified

| Component | File | Status |
|-----------|------|--------|
| Worker Initialization | `static/liblouis-worker.js` lines 30-121 | ✅ VERIFIED |
| Table Chain Construction | `static/liblouis-worker.js` lines 155-157 | ✅ VERIFIED |
| Translation Execution | `static/liblouis-worker.js` lines 158-168 | ✅ VERIFIED |
| Output Validation | `static/liblouis-worker.js` lines 162-167 | ✅ VERIFIED |
| Backend Line Validation | `app/validation.py` lines 30-71 | ✅ VERIFIED |
| Backend Braille Validation | `app/validation.py` lines 74-131 | ✅ VERIFIED |
| Braille-to-Dots Conversion | `app/utils.py` lines 96-133 | ✅ VERIFIED |
| Table Discovery API | `backend.py` lines 2051-2078 | ✅ VERIFIED |
| Table Scanning | `backend.py` lines 1919-2048 | ✅ VERIFIED |
| Inline Validation | `backend.py` lines 745-756 | ✅ VERIFIED |
| Plates Module Validation | `app/geometry/plates.py` lines 126-137 | ✅ VERIFIED |
| Cylinder Module Validation | `app/geometry/cylinder.py` lines 152-155 | ✅ VERIFIED |
| Geometry Spec Validation | `geometry_spec.py` line 594 | ✅ VERIFIED |
| Frontend translateWithLiblouis | `templates/index.html` lines 5078-5096 | ✅ VERIFIED |

### Critical Path Verification

#### 1. Translation Request Flow ✅

```
User Input → Frontend → Worker Message → Liblouis translateString() →
Output Validation → Response to Frontend → Form Submission →
Backend Validation → Dot Conversion → Geometry Generation
```

**All steps verified as consistent across implementations.**

#### 2. Unicode Range Consistency ✅

All nine locations use identical range `0x2800` to `0x28FF`:
- `app/utils.py` (constant definitions)
- `app/validation.py` (constant definitions)
- `backend.py` (two inline checks)
- `app/geometry/plates.py` (two inline checks)
- `app/geometry/cylinder.py` (one inline check)
- `geometry_spec.py` (one inline check)
- `static/liblouis-worker.js` (output validation)

#### 3. Table Chain Construction ✅

Worker correctly prepends `unicode.dis` when not already present:

```javascript
const tableChain = selectedTable.indexOf('unicode.dis') !== -1
    ? selectedTable
    : ('unicode.dis,' + selectedTable);
```

#### 4. Error Message Propagation ✅

Errors include debugging context:
- Worker: Includes last 8 liblouis log entries
- Backend: Includes first 5 invalid character positions
- ValidationError: Includes structured `details` object

#### 5. braille_to_dots Usage ✅

All geometry modules correctly import and use the canonical function:
- Direct import from `app/utils` in server-side code
- Passed as parameter to `geometry_spec.py` for flexibility
- Consistent 6-element list output `[0,0,0,0,0,0]` to `[1,1,1,1,1,1]`

### Notes

1. **Translation happens exclusively client-side** — Backend never imports or calls liblouis directly.

2. **`unicode.dis` is mandatory** — Without it, translation may produce ASCII dots notation instead of Unicode braille.

3. **Spaces are valid in braille lines** — They represent blank cells and are explicitly allowed by validation.

4. **Counter plates skip braille validation** — `plate_type='negative'` bypasses character validation since all dots are generated regardless of text.

5. **Table preloading is optional but recommended** — Core tables are preloaded to reduce latency on first translation.

6. **Geometry spec uses dependency injection** — `geometry_spec.py` receives `braille_to_dots_func` as a parameter rather than importing directly, allowing for testing and flexibility.

---

## 14. Cross-System Compliance Verification

This section documents the cross-check of all systems that use the Liblouis translation process.

> **Note added 2026-10-09:** recorded with Section 13; its rows for `liblouis-worker.js` name the removed 3.2.0 worker (see the note there).

### Systems Using Braille Unicode Validation

| System | File | Line(s) | Validation Logic | Compliant |
|--------|------|---------|------------------|-----------|
| Backend Positive Plate | `backend.py` | 747 | `any(ord(char) >= 0x2800 and ord(char) <= 0x28FF ...)` | ✅ |
| Backend Counter Plate | `backend.py` | 937 | `any(ord(char) >= 0x2800 and ord(char) <= 0x28FF ...)` | ✅ |
| Plates Module Positive | `app/geometry/plates.py` | 128 | `any(ord(char) >= 0x2800 and ord(char) <= 0x28FF ...)` | ✅ |
| Plates Module Counter | `app/geometry/plates.py` | 318 | `any(ord(char) >= 0x2800 and ord(char) <= 0x28FF ...)` | ✅ |
| Cylinder Module | `app/geometry/cylinder.py` | 153 | `any(ord(char) >= 0x2800 and ord(char) <= 0x28FF ...)` | ✅ |
| Geometry Spec | `geometry_spec.py` | 594 | `any(0x2800 <= ord(c) <= 0x28FF ...)` | ✅ |
| Validation Module | `app/validation.py` | 104 | `char_code < BRAILLE_UNICODE_START or char_code > BRAILLE_UNICODE_END` | ✅ |
| Utils Module | `app/utils.py` | 120 | `code_point < 0x2800 or code_point > 0x28FF` | ✅ |
| Liblouis Worker | `static/liblouis-worker.js` | 164 | `code >= 0x2800 && code <= 0x28FF` | ✅ |

**Result: 9/9 systems compliant with Unicode range specification**

### Systems Using braille_to_dots Conversion

| System | File | Line(s) | Import Source | Compliant |
|--------|------|---------|---------------|-----------|
| Backend | `backend.py` | 66, 780, 959 | `from app.utils import braille_to_dots` | ✅ |
| Plates Module | `app/geometry/plates.py` | 24, 161, 340 | `from app.utils import braille_to_dots` | ✅ |
| Cylinder Module | `app/geometry/cylinder.py` | 21, 827 | `from app.utils import braille_to_dots` | ✅ |
| Geometry Spec | `geometry_spec.py` | 28, 217, 610 | Parameter injection | ✅ |
| Backend → Geometry Spec | `backend.py` | 2535, 2545 | Passes `braille_to_dots` to spec functions | ✅ |

**Result: 5/5 systems compliant with braille_to_dots specification**

### Frontend Translation Pipeline Compliance

| Component | File | Line(s) | Behavior | Compliant |
|-----------|------|---------|----------|-----------|
| Worker Init | `liblouis-worker.js` | 30-121 | Creates LiblouisEasyApi, enables on-demand loading | ✅ |
| Table Chain | `liblouis-worker.js` | 155-157 | Prepends `unicode.dis` if not present | ✅ |
| Translation | `liblouis-worker.js` | 158 | Calls `translateString(tableChain, text)` | ✅ |
| Output Check | `liblouis-worker.js` | 162-167 | Validates output contains U+2800–U+28FF | ✅ |
| Error Handling | `liblouis-worker.js` | 170-179 | Includes recent logs in error message | ✅ |
| Frontend Wrapper | `templates/index.html` | 5078-5096 | Async wrapper with worker communication | ✅ |
| Preview Usage | `templates/index.html` | 4191 | Calls `translateWithLiblouis` for preview | ✅ |
| Form Submission | `templates/index.html` | 4399 | Calls `translateWithLiblouis` for STL generation | ✅ |
| BANA Wrapping | `templates/index.html` | 3437, 3442 | Uses `translateWithLiblouis` for length calculation | ✅ |
| Overflow Check | `templates/index.html` | 3322, 3595 | Uses `translateWithLiblouis` for overflow detection | ✅ |

**Result: 10/10 components compliant with frontend translation specification**

### Backend Validation Pipeline Compliance

| Component | File | Function | Behavior | Compliant |
|-----------|------|----------|----------|-----------|
| Lines Validation | `app/validation.py` | `validate_lines()` | Type, length, harmful chars | ✅ |
| Braille Validation | `app/validation.py` | `validate_braille_lines()` | Unicode range check | ✅ |
| Settings Validation | `app/validation.py` | `validate_settings()` | Type and range checks | ✅ |
| Request Handler | `backend.py` | `generate_braille_stl()` | Calls all validators | ✅ |

**Result: 4/4 validators compliant with validation specification**

### Compliance Summary

| Category | Components | Compliant | Status |
|----------|------------|-----------|--------|
| Unicode Range Validation | 9 | 9 | ✅ **100%** |
| braille_to_dots Usage | 5 | 5 | ✅ **100%** |
| Frontend Translation | 10 | 10 | ✅ **100%** |
| Backend Validation | 4 | 4 | ✅ **100%** |
| **Total** | **28** | **28** | ✅ **100%** |

### Potential Risk Areas (Monitored)

1. **Duplicate Constant Definitions** — `BRAILLE_UNICODE_START`/`END` are defined in both `app/utils.py` and `app/validation.py`. These must be kept in sync. Consider centralizing.

2. **Inline Range Checks** — Several files use inline `0x2800`/`0x28FF` checks rather than importing constants. Any future range changes require updating multiple files.

3. **Geometry Spec Dependency Injection** — `geometry_spec.py` receives `braille_to_dots_func` as a parameter. Callers must ensure they pass the correct function.

### Recommendations

1. **Centralize Constants** — Consider importing `BRAILLE_UNICODE_START`/`END` from `app/utils.py` in all files that need Unicode range validation.

2. **Replace Inline Checks** — Replace inline `0x2800 <= ... <= 0x28FF` with `is_braille_char()` from `app/utils.py` where appropriate.

3. **Add Integration Tests** — Create tests that verify the complete translation pipeline from frontend input to geometry output.

---

## Appendix A: Liblouis API Reference

### Engine Functions Used

**Source:** `static/liblouis-engine.js`

| Function | Purpose | liblouis call |
|----------|---------|---------------|
| `loadLiblouis(loader)` | Instantiate the wasm, once per worker | — |
| `installTables(mod, files)` | Write table files into the module's file system under `/tables` | — |
| `translate(mod, table, text)` | Text to braille, with each cell's input position | `lou_translate` |
| `backTranslate(mod, table, braille)` | Braille to text | `lou_backTranslateString` |
| `version(mod)` | The liblouis release | `lou_version` |

### Table Chain Format

```
tableList = "/tables/unicode.dis,/tables/en-ueb-g2.ctb"
```

Tables are processed left-to-right:
1. First tables define output encoding (`unicode.dis`)
2. Later tables define translation rules (`en-ueb-g2.ctb`)
3. Included tables are resolved transitively

---

## Appendix B: Troubleshooting Guide

### Worker Fails to Initialize

**Symptoms:**
- "Liblouis not initialized" error
- Translation button shows error

**Possible Causes:**
1. `liblouis.js`, `liblouis.wasm` or `tables.json` not found at `/static/vendor/liblouis-3.39.0/`
2. A Content Security Policy without 'wasm-unsafe-eval' in script-src
3. Browser doesn't support Web Workers with modules

**Solutions:**
1. Verify those files and `static/liblouis-module-worker.js`, `static/liblouis-engine.js` exist
2. Check browser console for 404 errors
3. Ensure server sets proper CORS headers

### Translation Returns Empty

**Symptoms:**
- Empty braille string returned
- "Liblouis returned empty result" error

**Possible Causes:**
1. Table file missing or corrupt
2. Input text is empty
3. Table doesn't support input characters

**Solutions:**
1. Check that `tables.json` lists the table and its files load from `/static/vendor/liblouis-3.39.0/tables/`
2. Verify non-empty input
3. Try different language table

### Backend Rejects Valid Braille

**Symptoms:**
- "Invalid braille characters detected" error
- Error shows unexpected character codes

**Possible Causes:**
1. Frontend translation failed silently
2. Character encoding issue (not UTF-16)
3. Different Unicode normalization

**Solutions:**
1. Check browser console for worker errors
2. Verify Content-Type is `application/json; charset=utf-8`
3. Log the actual character codes being sent

---

## Appendix C: File Reference Index

### Files That Perform Braille Unicode Validation

| File | Purpose |
|------|---------|
| `static/liblouis-module-worker.js` | Validates translation output |
| `app/validation.py` | Backend request validation |
| `app/utils.py` | `is_braille_char()` helper |
| `backend.py` | Inline validation in mesh generation |
| `app/geometry/plates.py` | Card plate geometry validation |
| `app/geometry/cylinder.py` | Cylinder geometry validation |
| `geometry_spec.py` | Geometry spec extraction validation |

### Files That Use braille_to_dots Conversion

| File | Purpose |
|------|---------|
| `app/utils.py` | Canonical definition |
| `backend.py` | Import and usage for mesh generation |
| `app/geometry/plates.py` | Card plate dot positioning |
| `app/geometry/cylinder.py` | Cylinder dot positioning |
| `geometry_spec.py` | Client-side CSG specification |

### Files That Perform Translation

| File | Purpose |
|------|---------|
| `static/liblouis-module-worker.js` | The translation worker |
| `static/liblouis-engine.js` | The liblouis 3.39.0 engine module |
| `public/index.html` | `translateWithLiblouis()` wrapper |

### Files That Discover/Scan Tables

| File | Purpose |
|------|---------|
| `backend.py` | `list_liblouis_tables()`, the `/liblouis/tables` API (reads `static/vendor/liblouis-3.39.0/tables.json`) |

---

*Document Version: 1.8*
*Last Updated: 2026-10-09 — the engine round's phase 8: the liblouis 3.2.0 engine is removed, and Sections 1-5, 7, 11 and 12 and Appendices A-C describe liblouis 3.39.0 (the module worker, the engine module, the vendored build and tables); the engine status note is gone; Sections 13-14 stay as recorded, with notes.*
*Previous: 1.7, 2026-10-09 — Section 10: the table list is the translation tables of the vendored 3.39.0 index (the engine round's phase 7); the old folder scan, and Section 4's copy of it, are gone.*
*Previous: 1.6, 2026-10-09 — the engine status note: translation runs on liblouis 3.39.0 (WebAssembly) in a module worker; the 3.2.0 sections are rewritten in the engine round's part 3.*
*Previous: 1.5, 2026-10-09 — the line count follows the request's own Rows (a line past it must be empty; 200 at most) instead of a fixed four, which refused Rows 5+; the fit of those rows is checked separately (BRAILLE_SPACING_SPECIFICATIONS.md §12).*
*Previous: 1.4, 2026-09-30 — documentation review: the Braille (Unicode) field is also filled by every Generate STL (2026-09-28) and an unedited one empties when the text or a translation setting changes*
*Previous: 1.3, 2026-07-30 — added the `backTranslate` worker message (braille → text) used by the "Translate to Text" button and by STL file naming*
*Revised 2026-08-21 (v1.3) — `templates/index.html` reference sweep (Phase 07b). Section 7 and Appendix C now cite `public/index.html` by function name (`translateWithLiblouis()`, `loadLanguageOptions()`) instead of a deleted file with stale line numbers. Section 13's dated verification tables are left exactly as recorded, with a note that `templates/index.html` has since been removed.*
*Cross-System Compliance Verification Completed: 2024-12-06*
*Total Components Verified: 28*
*Compliance Rate: 100%*
*Source Priority: backend.py > wsgi.py > csg-worker.js > Manifold WASM*
