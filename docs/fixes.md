# Fix Log

Entries follow the debug workflow (Cline/Workflows/debug.md, step 9): one paragraph on the bug, one on the fix, and the done-condition check that passed.

## 2026-09-28 — The seam-channel note went silent in visual mode

**Bug.** Introduced by the X Adjust fix of 2026-09-27 (`7056115`, on the development build for one day, never on main): `updateSeamChannelUI()` gained a last-cell room check for tactile mode and initialised it to `Infinity` for visual mode, and the guard that keeps the box quiet while a dial is mid-edit tests `Number.isFinite()` on it - so in visual mode the note never showed. The server still reported the omission at Generate; only the live note was lost. Found by the full Chromium e2e run (`seamChannel.spec.ts:298`), which had not been run after that change.

**Fix.** The two visual-mode initialisers are `0`, so the guard passes and `0 < 0` never trips the tactile-only rule.

**Done-condition check that passed.** `tests/e2e/seamChannel.spec.ts` on Chromium, all tests, after the fix.

## 2026-09-28 — The Back of Card text came back on the next visit

**Bug.** Brennen's user testing found that the Back of Card text field remembered the previously entered text after leaving and returning to the app, while the front text field did not. The cause was an asymmetry in persistence: `braille_prefs_back_text` was written on every keystroke into the back text box (and by Translate to Text on the back) and restored on load, and no front field was ever persisted. His rule: no text or braille input may be stored at all, not even locally, because it gives the impression that the app collects what people write; only 3D design settings may persist, and only in the user's browser.

**Fix.** The two writes and the restore are gone; the key is removed from `localStorage` on every load so a value saved by an earlier version disappears, and it stays in the Reset list so Reset scrubs it too. The other five boxes (front text, front and back manual rows, both braille fields) were already unpersisted and are now pinned that way.

**Done-condition check that passed.** `tests/test_text_privacy.py` (no persistence call names a text or braille key; the scrub line exists) and `tests/e2e/textPrivacy.spec.ts` on Chromium: a pre-seeded `braille_prefs_back_text` is gone after load and the box is empty; text typed into all six boxes appears in neither `localStorage` nor `sessionStorage` and none of it survives a reload while the double-sided and placement settings do.

## 2026-09-28 — The X Adjust dial did nothing on cylinders

**Bug.** Brennen's print of the development build (2026-09-27) showed the front text starting too far from the alignment arrow and losing its last cell past the card's end, with the back losing its first cells. He turned the X Adjust dial (Expert Mode → Braille Spacing → Braille Line Positioning on the Cylinder Surface) and nothing changed; Y Adjust worked. Cause: `extract_cylinder_geometry_spec` in `app/geometry_spec.py` applied `braille_y_adjust` in every row loop but never read `braille_x_adjust` — the field had only ever existed in the card path — so the dial was sent, validated, stored and ignored. Earlier attempts had been reported fixed on the strength of the spec alone, so the proof this time was made on the real browser worker before any code changed: exports at X 0 and X −3 were byte-identical (STL, geometry spec and preview screenshot), with the request differing only in the dial.

**Fix** (web develop `7056115`, pushed 2026-09-28). `x_shift_angle = braille_x_adjust / radius` is added inside `apply_seam` (`-(angle + shift)`) and `apply_seam_mirrored` (`angle + shift`) — the card frame both plates share, after the double-sided back mirror — so front dots, back dots and their paired recesses all move by the dial's millimetres of arc together and a pair still meets at theta and −theta. The tactile arrows, the tactile groove and the Version 2 keys do not move. Direction as requested: a negative X moves Cylinder A's dots and recesses left and Cylinder B's right as the preview's default camera shows them, which on both brings the first cell toward the arrow. The seam-channel, arrow-gap and card-fit rules read the shift, and their live UI mirrors do too. At 0 nothing changes (all eight golden pairs byte-identical; the real export at 0 byte-identical to the pre-fix export). Brennen confirmed the fix in print on 2026-09-28 ("Testing has been completed") and set −2 as the Version 2 tactile default.

**Done-condition check that passed.** On the real Chromium worker's exports at X −3, measured per feature by trimesh surface sampling: Cylinder A raised dots −3.000 mm of arc, A recesses −2.979, Cylinder B raised dots +2.994, B recesses +3.026, arrows 0.00 (±0.09 sampling noise); `tests/e2e/xAdjust.spec.ts` 3/3 (Chromium), `tests/test_x_adjust_cylinder.py` 12/12, full suite 727 passed / 4 skipped, W3C 0 errors. No DEBUG-TEMP lines were added, so the cleanup sweep found none. Files changed: `app/geometry_spec.py`, `public/index.html`, `tests/test_x_adjust_cylinder.py`, `tests/e2e/xAdjust.spec.ts`, `docs/specifications/BRAILLE_SPACING_SPECIFICATIONS.md`, `docs/specifications/SURFACE_DIMENSIONS_SPECIFICATIONS.md`, `docs/specifications/RECESS_INDICATOR_SPECIFICATIONS.md`, `CHANGELOG.md`, `.clinerules/project-facts.md`.
