# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Edges toggle in the 3D preview.** A new button beside Brightness and Contrast outlines the model's feature edges over the shaded surface, the way slicers and CAD viewers expose structure independently of the lighting. It gives low-vision users a higher-contrast presentation of the same geometry (WCAG technique G174) and makes dot silhouettes readable at a glance. On by default — the outlines are what make the dot and marker shapes legible without relying on the shading — and not persisted, so every load starts from that default, matching the theme and font-size policies. Edges are drawn with `THREE.EdgesGeometry` at a 22° threshold rather than a full triangle wireframe, which on a plate of tens of thousands of facets would be unreadable noise.
- Per-theme `--stl-edge-color` CSS variable driving the edge overlay (`#020617` light, `#1a202c` dark, `#000000` high contrast). Edge lines render 1px wide, so they are held to the 4.5:1 text threshold against the mesh colour they sit on rather than the 3:1 non-text threshold.
- **Two-way translation between the text box and the braille box.** The Braille (Unicode) field now sits directly under the text entry area with a matching button under each: **Translate to Braille ↓** fills the braille from the text, and the new **Translate to Text ↑** back-translates pasted braille into English so a reader can check what they were given. Back-translation runs through a new `backTranslate` message in the liblouis worker (`lou_backTranslateString`) and never touches the braille field itself, which remains the authority for what gets embossed.
- **Generate STL button pinned below the form.** The right column now scrolls in an inner `.form-scroll` area with the button in a fixed `.action-footer` beneath it, so it is reachable without scrolling on desktop and stays sticky on mobile. The form column still has exactly one scrollbar.
- **Tactile Indicator Dimensions** and **Translation Options** submenus in Expert Mode. The five tactile dials moved out of Shape Selection into their own accordion, shown only when the tactile arrow is selected; Capitalized Letters and Number Signs moved out of the main form into Translation Options, with a pointer left where they used to be.
- `tests/e2e/formLayout.spec.ts` — pins the pinned-button layout, the single-scrollbar invariant, the Generate-button reset, and the braille cell dial staying under user control.
- **Editable Unicode braille field.** A new "Braille (Unicode)" textarea sits under the text inputs with a **Translate to Braille** button. Whenever it holds content, those exact cells are what get embossed — generation uses the lines verbatim and skips liblouis. Two uses: fixing a translation by hand (most often deleting the repeated number signs from a hyphenated phone number so it fits one row), and pasting braille directly with the English boxes left empty, which is the parity feature braille readers were missing versus the OpenSCAD version. Edits are locked against being overwritten by later English edits; only the Translate button replaces them, and every state change is announced through a polite live region. Non-braille characters and over-long lines block generation with the offending line number and cell count.
- **Tactile row indicator for cylinders**, ported from the OpenSCAD version. A new "Row Indicator Style" control under "Select Plate to Generate" offers *Visual markers* (default, unchanged) or *Tactile seam arrow*: one raised arrow per row on the embossing plate and a matching recess on the counter plate, both centred in the seam gap at 180° with the apex toward the cylinder top. A blind user can find the alignment point and tell which end is up by touch, and raised-versus-recessed identifies which cylinder they are holding. Tactile mode removes the marker cells entirely, so every cell in the row is available for text. The arrow is deliberately lower than the braille dots so the dots carry the rolling pressure. New settings `indicator_mode` plus five `tactile_*` dimensions, with defaults byte-for-byte identical to the OpenSCAD parameters, exposed in Expert Mode. The UI warns live when the seam gap can no longer hold the arrow.
- `tests/e2e/brailleField.spec.ts` and `tests/e2e/tactileIndicator.spec.ts` — end-to-end coverage asserting on the payload actually sent to `/geometry_spec`, so the "used verbatim" and column-arithmetic contracts cannot regress silently.

### Changed
- **The default translation is now English (UEB) contracted, grade 2.** BANA's *Guidelines for Brailling Business Cards* (approved March 2024) tells transcribers to "Follow *The Rules of Unified English Braille*" and transcribes all nine of its worked examples in contracted UEB, so uncontracted was never the BANA-aligned choice — and contractions buy back cells on a 13-cell row, which is the constraint the whole guide is about. `en-ueb-g2.ctb` is now the selected option, the value every fallback in `public/index.html` resolves to (via a single `DEFAULT_LANGUAGE_TABLE` constant), the per-line default in manual mode, the Reset-to-defaults value, the liblouis worker's fallback when no table is named, and the documented `text.default_language` default in `settings.schema.json`. The help text, the Business Card Guide, the Cylinder Guide, the in-app help panels, and the language/translation specifications were all rewritten to match, including the "what to type" example hints that used to be labelled Grade 1.
- **A saved language choice now survives a reload.** The page used to overwrite the restored `braille_prefs_language_table` value with the hard default on every load, so changing tables never stuck past a refresh. The default is now the first-run value only.
- **The 3D preview is matte instead of glossy.** Shininess drops from 200 to 30 (standard themes) and from 300 with a white specular to 60 with `#333333` (high contrast), matching how PrusaSlicer, Cura, and MeshLab present an STL. The old values threw broad highlights across the plate that swallowed the dot geometry the preview exists to show; the three-point lighting carries the form instead, and the high-contrast cyan-on-black look is unchanged apart from losing the blown-out mirror. The Contrast stepper's shininess offsets were rescaled from `-40 … +220` to `-15 … +60` to suit the new base, and the `Math.max(50, …)` floor that would have defeated it is gone. Brightness levels are untouched. The material is now defined once in `STL_MATERIAL_SETTINGS` rather than duplicated across three call sites.
- **Light-theme preview mesh darkened from `#6699cc` to `#5580b3`.** The old steel blue measured 2.7:1 against the `#f1f5f9` viewer background and failed WCAG 2.2 SC 1.4.11 (Non-text Contrast, 3:1); the new one measures 3.7:1 in the same hue. Dark (7.0:1) and high contrast (16.7:1) already passed and are unchanged.
- **Every row now holds at least 13 braille cells, so a phone number fits on one.** A phone number takes exactly 13 cells either way you get there: written with periods it translates to 13 under UEB (`206.616.7678` → `⠼⠃⠚⠋⠲⠋⠁⠋⠲⠛⠋⠛⠓`, one number sign), and the hyphenated form comes to 13 once its repeated number signs are edited out in the Braille (Unicode) field (`⠼⠑⠁⠚⠤⠃⠃⠊⠤⠛⠊⠁⠓`). The visual-marker recommendation of 12 text cells wrapped it onto a second row — the one thing a business card cannot afford. Visual mode now recommends **13 text cells** whichever way Indicator Letters is set: 15 total columns with them on (13 + 2 markers), 14 with them off (13 + 1). Tactile mode reserves no marker cells and recommends **14 text cells**, which is 14 total. The `grid_columns` default in `settings.schema.json` and `CardSettings` counts total columns and follows the visual default, so it moves from 14 to 15. Cylinder diameter, height, and the polygonal cutout are fixed by the housing the part mounts into and are untouched.
- **The visual-mode fit warning is measured against a cell's dots, not a whole cell.** It used to fire when the seam gap fell below one full cell spacing, which on the default 30.75 mm cylinder would have flagged the new 13-cell recommendation: 15 columns leave a 5.6 mm gap, and the old rule wanted 6.5 mm. The gap only has to keep the last cell's dots clear of the first cell's, and a cell's dots span `dot_spacing` plus one dot diameter — 4.5 mm at the default dot sizes — so that is the threshold now. In practice the warning starts at 16 total columns instead of 15, and as before it only warns: generation is never blocked. The tactile rule (indicator width plus a 5 mm clear zone) is unchanged, so 15 columns is still too many for the arrow.
- **STL downloads are named `Embossing_Cylinder_{preset}_{name}.stl` / `Counter_Cylinder_{preset}_{name}.stl`**, where `{preset}` is the selected Card Thickness (`0.4`, `0.3`, or `Custom`) and `{name}` is the first word of your text. Counter plates no longer use a session counter, so a generated pair sorts together and carries the print settings it was designed for. Braille pasted with no source text is back-translated for the name; `untitled` is the fallback.
- **Any settings change resets the button to Generate STL.** The old hand-maintained list of input IDs silently missed controls added later — the tactile indicator dials among them — so a stale STL could be downloaded under new settings. It is now event delegation on the form, which covers every current and future control.
- **The braille cell count is no longer overwritten while you type.** Changing the plate type or indicator style used to normalize `grid_columns` straight back to 13/14, which made the field look locked. It now auto-fills only until you edit it, and the recommended value is stated in the note instead.
- **Tactile indicator defaults**: length 5.0 → 10.0 mm and raise 0.8 → 0.5 mm. All five tactile dimensions are now part of both Card Thickness presets, so selecting a preset restores them.
- Removed the disabled "Flat Card" radio, the Plate Dimensions group (the cylinder has no flat plate; the schema fields are now carried by hidden inputs), and the "flat cards are temporarily disabled" notes. "Braille / Card Positioning" is now "Braille Line Positioning on the Cylinder Surface", and Row Indicator Style moved above Card Thickness.
- Expert Mode submenu toggles use the WCAG-AA contrast colours (`#1e4976` / `#1e5a8a`) the main Expert Mode toggle already used, instead of `--border-focus` at 3.7:1.
- **"Repeat number sign" checkbox is now a "Number Signs" radio group.** The single checkbox read as a *prevent repetition* switch, so users reported the app adding number signs it refused to remove. The two outcomes are now stated explicitly, and the help text names the real cause: under UEB a period keeps numeric mode but a **hyphen or parenthesis ends it**, so `206-543-4779` correctly needs three number signs (15 cells, wraps to two rows) while `206.543.4779` needs one (13 cells, fits). That is correct liblouis output, not a bug — the remedies are retyping with periods or editing cells in the new braille field. The stored preference values are unchanged, so existing settings still restore.
- BANA business card guidance is now reproduced verbatim from the *Business Cards Fact Sheet* (approved March 2024) in `docs/guides/BUSINESS_CARD_TRANSLATION_GUIDE.md`, the Directions dropdown in `templates/index.html`, and the "What to Include", "Formatting", and "Examples" help panels in `public/index.html`.
- The Business Card Guide now shows BANA's published Grade 2 braille (in Unicode U+2800–U+28FF) alongside the app-specific "what to type" hint for each of BANA's nine worked examples, so users can see the source cells directly without needing to open the PDF.
- The in-app Examples panel in `public/index.html` likewise shows the BANA Grade 2 braille verbatim for each of its three example cards, with an `aria-label` describing each rendering for screen readers.
- README pointer to the Business Card Guide now cites the BANA source year (March 2024).

### Added
- `docs/guides/_bana_business_cards_verified_source.md` — verified visual transcription of the BANA Fact Sheet with verbatim prose, Unicode-braille (U+2800–U+28FF) renderings of all nine worked examples, and a deviation report driving the rewrite above.
- `scripts/fetch_bana_business_cards.py` — one-shot script that downloads the BANA PDF and rasterizes each page to `docs/guides/_bana_source/page_NN.png` for future verification.
- `scripts/_extract_bana_text.py` — working tool that pairs each NABA-ASCII-encoded line in the PDF with its Unicode-braille equivalent.

### Fixed
- **Warnings now clear the moment you fix what they complain about.** Every warning on the page was wired to its own hand-picked list of inputs, and the lists had gaps: raising the braille cell dial never re-checked the manual-mode overflow warning, changing the language table never re-measured any line, and the dot-size fields never re-checked the seam gap. Worse, the blocking error over the 3D preview ("line 2 exceeds 13 cells", "generation blocked to prevent incorrect braille output") was only ever cleared by the next Generate, so a user who corrected the problem was still looking at the complaint. All live warnings are now re-evaluated together by `refreshLiveWarnings()` on any form change, using the same event delegation that already reset the Generate button, and a blocking validation notice is retired as soon as anything changes. Progress notices and the browser-capability warning are exempt: neither is something an edit can fix.
- **The Braille (Unicode) field is validated as you type.** A non-braille paste or a row longer than the plate allows was only reported when Generate was pressed. The same check now runs on every keystroke and on every change to the row and cell dials, so raising a dial retires the warning it caused.
- **The two overflow warnings were invisible to screen readers.** `#auto-overflow-warning` and `#cylinder-overflow-warning` had no live region, so they appeared and disappeared silently; both are now `role="status"` `aria-live="polite"`, matching the seam-gap and capitalization warnings.
- In-app help claimed Capitalized Letters defaults to Disabled; the default is Enabled.
- **CI has been red on `main` since the ruff 0.16.0 bump, because ruff now formats Python code blocks inside Markdown.** [#90](https://github.com/BrennenJohnston/braille-cylinder-stl-generator/pull/90) bumped ruff 0.15.2 → 0.16.0, where Markdown code-block formatting [became the default](https://docs.astral.sh/ruff/formatter/#markdown-code-formatting). `ruff format --check .` then wanted to restyle 15 Markdown files — 14 specs and guides of ours, plus `OpenSCAD/docs/WEB_TO_OPENSCAD_PORTING_GUIDE.md` — so `backend-tests` failed in 30 seconds and took `e2e-tests` and `accessibility-tests` down with it, the same cascade as the vendored-copy break below. Markdown and `OpenSCAD/` are now in `extend-exclude`, the opt-out ruff documents for this feature. Formatting the vendored file would have broken the per-file hash guard added below, and the code blocks in our docs quote OpenSCAD parameters, liblouis output, and prior implementations verbatim, so they are illustrations rather than code we own and restyle. Nothing about how the app's own Python is formatted changes: the same 24 files are checked as before, and `ruff check .` is untouched.
- **CI was red on develop for three pushes because the vendored OpenSCAD copy had been edited in place.** A revision to the tactile cell-count wording was also applied to `OpenSCAD/Braille_Cylinder_STL_Generator.scad` and two of its docs. `OpenSCAD/` is a verbatim copy of upstream v2.4.1, so the `.scad` stopped matching the SHA-256 in `VENDORED.json`, `backend-tests` failed, and `e2e-tests` and `accessibility-tests` — both of which `need` it — never ran at all on those three commits. All three files are back to their v2.4.1 bytes; the wording is tracked upstream in [#93](https://github.com/BrennenJohnston/braille-cylinder-stl-generator/issues/93).
- **The vendored-copy guard now hashes every file in `OpenSCAD/`, not just the `.scad`.** Only the `.scad` carried a `sha256`, which is why edits to `PARAMETER_MAPPING.md` and `docs/MAKERWORLD_QUICK_START.md` rode along with no check noticing — exactly the silent divergence the guard exists to prevent. `VENDORED.json` now records a hash per file, matching what it and `.gitattributes` already claimed it did, and `test_vendored_file_matches_recorded_hash` is parametrized so a failure names the file that drifted. For `PARAMETER_MAPPING.md`, which carries a documented one-sentence edit made on copy, the hash covers the adjusted copy rather than upstream's bytes, so it still catches later drift. A companion test keeps the `.scad` from being dropped from the folder and the record together, which the per-file checks alone would not catch.
- **Indicator letters no longer degrade to blank rectangles after using Translate to Braille.** Filling the Braille (Unicode) field — which the guided workflow recommends before generating — made the page send `original_lines: null` to `/geometry_spec`, so every row's embossed indicator letter fell back to the square placeholder. The English inputs are still on screen in that flow, so they are now sent for the indicator letters; `null` (and the square fallback) is reserved for braille pasted with the English inputs left empty, where there genuinely is no letter to derive.
- **The preview's Brightness and Contrast controls were clipped at 200% font size.** The overlay bar was `flex-wrap: nowrap`, so at the largest font setting the "Brightness:" label ran off the left edge of the viewer. The groups now wrap onto a second line; nothing changes at 150% or below, where the row still fits on one line.
- **Generate STL did nothing on the first press after typing, in Safari.** Resetting the button on every form change rewrote its text and class during the mousedown, because a textarea fires its change event as it loses focus. WebKit drops the click entirely when the pressed element is mutated mid-press. The reset is now a no-op when the button is already in the generate state, and the button's hover effect no longer moves it under the pointer.
- Removed prior paraphrased BANA rule statements that drifted from the source. The drift was caused by previous rewrites being derived from the PDF's hidden NABA-ASCII text layer (which renders as `,h>ry ,pott]` to any PDF-to-text tool) instead of the visual layer. Specific corrections:
  - Phone-number "Best/OK/Poor" table replaced by BANA's single prescriptive statement.
  - E-mail and web-address division priorities replaced by BANA's three-tier statement, including the dot-5 continuation indicator and its "as a last resort, omit" fallback that was previously absent.
  - "Common abbreviations" list trimmed to the three BANA names by example (`lib`, `amer`, `nat`); previously-invented entries (`Assoc`, `Univ`) removed.
  - Removed the claim that we adapt BANA's worked examples to Grade 1. The app now defaults to Grade 2, the same code BANA publishes; the docs say so, and note that liblouis will not always reproduce BANA's per-card cell-level judgement calls.
- Second-pass audit of the Directions dropdown in `templates/index.html` against the BANA PDF page images caught additional drift, all now corrected:
  - "Common fixes if text won't fit (BANA order)" was a single numbered list that conflated BANA's name fall-through (4 items, of which the last is BANA's parallel "if space is available" option, not a final fallback), BANA's organization-name strategies (presented in BANA as parallel options), and the app's own Grade 2 recommendation (not part of BANA's order at all). The list is now split into three clearly labeled sections.
  - The abridged Phone, E‑mail, and Web quotes have been replaced with the full verbatim paragraphs from page 3 of the Fact Sheet. The previous "E‑mail / web" combined bullet only quoted the e‑mail punctuation list ("at" sign, period, hyphen) and silently dropped the web-address punctuation list (colon, period, slash).
  - Restored BANA's "13 or 14 cells, depending on the equipment" cell-count caveat where the friendly intro had simplified to "about 13".
  - Lowercased the "amer" abbreviation example to match BANA's own spelling.
- `public/index.html` worked-example braille (`<pre>` blocks for BANA Examples 1, 4, and 7) now uses U+2800 BRAILLE PATTERN BLANK between words, matching the BANA PDF and the verified-source markdown, so the "verbatim from the Fact Sheet" label is honest at the codepoint level.
- `docs/guides/_bana_business_cards_verified_source.md` Example 6 heading had inadvertently duplicated Example 5's title ("Omission of capitals from name; division of surname; omission of company name (in e-mail)"). Replaced with BANA's actual Example 6 heading ("Division of hyphenated name (client agreed to a shortened first name); omission of capitals from post-nominal letters/credentials; omission of organization name (in e-mail)").
- Resynced the second "BANA-quoted blocks below — DO NOT EDIT" comment block in `public/index.html` (above the Formatting Rules panel) to match the propagation reminder in the first block, so future edits don't drift between the two panels.

## [2.1.0] - 2026-02-16

Documentation overhaul. Rewrote all project docs to remove AI-generated language and match the tone of a small, single-maintainer open-source project.

### Changed
- Rewrote README, CONTRIBUTING, SECURITY, CHANGELOG, PROJECT_STRUCTURE, and RELEASING
- Rewrote all docs in docs/security/, docs/deployment/, and docs/development/
- Trimmed ENVIRONMENT_VARIABLES.md, KNOWN_ISSUES.md, and the specifications index
- Cleaned up "comprehensive", "robust", and other AI patterns across specification files
- Cut MAJOR_FEATURE_IMPLEMENTATION_SOP from 1000+ lines to a practical 70-line checklist
- Updated bug report template and GitHub repository metadata

### Removed
- docs/development/IMPLEMENTATION_PROCESS_ANALYSIS.md (530-line AI self-review with no value for contributors)

---

## [2.0.0] - 2026-01-06

Major architecture change: removed all external service dependencies. The server is now a minimal Flask app that serves geometry specs — all STL generation happens in the browser.

### Why v2.0.0

- Removed Upstash Redis (free tier archives after 14 days of inactivity, breaking the app)
- Removed Vercel Blob storage (no longer needed)
- Moved all STL generation to client-side Web Workers
- Server now only needs Flask and Flask-CORS

### Added
- Python 3.13 support
- Health check loop in CI for stable Lighthouse audits
- Updated all GitHub Actions, npm, and pip packages to latest stable versions

### Changed
- Default braille dot shape is now cone (better print quality and tactile feel)
- Server only provides geometry specs; all CSG operations run client-side
- GitHub Actions updated to checkout@v6, setup-python@v6, setup-node@v6
- three-mesh-bvh updated to 0.9.4

### Removed
- Upstash Redis dependency
- Vercel Blob storage dependency
- Server-side STL generation
- Flask-Limiter (Vercel handles DDoS protection)
- requests library (was only used for blob upload)

### Fixed
- CI pipeline PORT variable for Flask server
- Replaced fixed sleep with health check loop in CI

---

## [1.3.0] - 2025-12-09

GitHub community infrastructure and license change.

### Changed
- License changed from MIT to PolyForm Noncommercial 1.0.0

### Added
- GitHub Actions CI (testing, linting, Lighthouse accessibility audits, W3C validation)
- Issue and PR templates
- Dependabot for pip and npm
- SECURITY.md, CODE_OF_CONDUCT.md
- lighthouserc.json, package.json, .vercelignore

### Fixed
- Various CI configuration issues (manifold3d deps, FLASK_ENV, ruff version sync, requirements filename, html5validator version)
- Reduced Vercel serverless function size under 250 MB limit

### Removed
- AI tool-specific plan files

---

## [1.2.0] - 2024-12-08

Documentation release.

### Added
- LICENSE (PolyForm Noncommercial 1.0.0)
- CHANGELOG.md
- CONTRIBUTING.md

### Changed
- README updated with badges and new sections
- .gitignore updated with OpenSCAD exclusion

---

## [1.1.0] - 2024-12-08

- Mobile compatibility improvements (lazy WASM loading)
- Dead code cleanup (~680 lines removed)
- WCAG 2.1 Level AA compliance verified

---

## [1.0.0] - 2024-09-27

First stable release.

### Features
- Braille text translation via liblouis (Grade 1 and Grade 2, 50+ language tables)
- Flat business card plates and cylindrical objects
- Real-time 3D preview with Three.js
- Client-side STL generation with three-bvh-csg and Manifold WASM
- Configurable dimensions, dot parameters, and embossing plate options
- Responsive UI with dark mode and WCAG 2.1 AA accessibility
- Vercel deployment with Flask backend

### Acknowledgments

Thanks to Tobi Weinberg for kick-starting the project. Based on [tobiwg/braile-card-generator](https://github.com/tobiwg/braile-card-generator).

---

## [Unreleased]

### Fixed
- **The vendored `OpenSCAD/` copy told contributors the wrong thing.** Its README
  claimed the standalone repo was "no longer the active home for this project"
  and asked for issues here. The opposite is true: the standalone repo holds the
  dual-file desktop build, the cross-platform fixture suite, and the CI. It also
  shipped a May-2026 snapshot named `Braille_Card_And_Cylinder_STL_Generator.scad`
  — a file that generates cylinders only.

### Changed
- **`OpenSCAD/` refreshed to upstream `v2.4.0` and documented as a vendored
  copy.** The vendored file is now the upstream MakerWorld single-file build
  (presets inlined, no `include`), renamed to
  `Braille_Cylinder_STL_Generator.scad` since this folder ships exactly one file.
  That build is self-contained, so the download works standalone *and* uploads
  directly to MakerWorld. Ships tactile indicator mode, the 13-cell default
  capacity, and the counted `TEXT TOO LONG` warning.
- **`OpenSCAD/VENDORED.json` records provenance** — upstream repo, tag, full
  commit sha, release date, copy date, and a SHA-256 per file, with each file's
  upstream path.
- **`tests/test_vendored_openscad.py` (4 tests) guards against silent drift** —
  the `.scad` must hash to what `VENDORED.json` records, every file in the folder
  must be accounted for, the provenance must name a resolvable tag and full sha,
  and the README must still state that upstream is canonical. Detecting a *newer*
  upstream release needs the network, so that is a release-checklist item in
  [docs/deployment/DEPLOYMENT_CHECKLIST.md](docs/deployment/DEPLOYMENT_CHECKLIST.md)
  instead.
- **Repository renamed to `braille-cylinder-stl-generator`.** The UI has
  generated cylinders only since v2.0.0, so "card-and-cylinder" no longer
  described the tool. GitHub redirects the old URLs, and the deployed Vercel
  URL is unchanged — existing links and QR codes keep working. `package.json`,
  the README title, badges, `PROJECT_STRUCTURE.md`, the in-app GitHub links,
  and the workspace file all follow the new name.
- **Flat business card plates are documented as parked, not "temporarily
  disabled".** They will not return in this repo; see
  [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md). Directly readable braille cards
  already ship as
  [braille-wedge-card-openscad](https://github.com/BrennenJohnston/braille-wedge-card-openscad).

### Planned
- Additional language support
- Custom dot shape options
- Batch processing
- OpenSCAD export option

[2.1.0]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v2.1.0
[2.0.0]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v2.0.0
[1.3.0]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v1.3.0
[1.2.0]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v1.2.0
[1.1.0]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v1.1.0
[1.0.0]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/releases/tag/v1.0.0
[Unreleased]: https://github.com/BrennenJohnston/braille-cylinder-stl-generator/compare/v2.1.0...HEAD
