# Gear-Integrated One-Piece Rollers (BETA) — Specifications

## Overview

A braille cylinder can be generated as ONE solid, watertight part with its top and
bottom drive gears already attached, instead of a bare barrel that separately printed
gears are pushed onto. Fewer separate objects means fewer assembly steps, and the
meshed gears are the mechanism that keeps a paired set rotationally synchronised — the
assembly risk the double-sided initiative recorded as about ±1.0°.

The gears are **not parametric**. They are a 1:1 replication of Brennen's reference
set, vendored as binary assets and never reconstructed. Everything in this document
was verified against the merged code on 2026-08-24; where a number appears, the file
that owns it is named.

**Status:** ✅ BETA (Created 2026-08-24)
**Toggle:** `gear_rollers.enabled` (schema) / `gear_rollers_enabled` (runtime), default
false
**Scope:** cylinders only, both the single-sided and double-sided flows

---

## 1. Feature Rules

Since 2026-09-20 (programme decision D-7) this is a released feature, not a beta: the
"(BETA — for testing)" tags are gone and the choice is the **Gears** radio group
(**Standard: print the gears separately** / **Simplified: gears fixed to the
cylinders**, DRAFT S-M3a/b) inside the **Embosser setup** menu item — see §8. The rules
are unchanged:

| Rule | Where it is enforced |
|---|---|
| Default Standard (the old OFF) | `settings.schema.json` `gear_rollers.enabled` default false; `app/models.py` `'gear_rollers_enabled': 0`; `#gear_mode_standard` checked in the markup |
| OFF is byte-identical to a build without the feature | proved at three levels — see §9 |
| Cylinders only | `validate_gear_rollers_settings()` in `app/validation.py` |
| The cylinder must be the reference roller | same function, §5 |
| The barrel is solid while ON | `createCylinderShellManifold(spec, solid)` in `static/workers/csg-worker-manifold.js` |
| Existing golden fixtures never change | Phase 07 regenerated the DS pair and git reported it byte-identical |

With the toggle off, the request body gains no key, the geometry spec gains no block,
and the filenames are exactly what the public training videos show.

---

## 2. The Vendored Assets

`static/assets/gears/` holds three files, and **only
`scripts/derive_gear_assets.py` may write them**:

| File | Contents |
|---|---|
| `gears_a.bin` | Cylinder A's pair: gear A1 (top) + A2 (bottom), 15,210 vertices / 30,412 triangles, 547,478 bytes |
| `gears_b.bin` | Cylinder B's pair: B1 + B2, 15,080 vertices / 30,152 triangles, 542,798 bytes |
| `gears_manifest.json` | Provenance: the four source STLs with their sha256s, the transform constants, per-asset counts, bounds, volumes and output sha256s |

### 2.1 Binary format

Little-endian throughout:

```
bytes 0..5              magic  b"BCGR1\0"
uint32                  vertCount
uint32                  triCount
float32[3 * vertCount]  vertProperties (x, y, z interleaved)
uint32[3 * triCount]    triVerts
```

**The header is 14 bytes, which is not a multiple of 4.** `numpy.frombuffer` accepts
that offset; a browser `Float32Array` view does not and throws `RangeError`. The worker
therefore copies the slice (`buffer.slice(...)`) before making a typed-array view.

### 2.2 Provenance

`gears_manifest.json` records the sha256 of each source STL and of each output.
`tests/test_gear_rollers.py::test_vendored_asset_is_the_bytes_its_manifest_records`
pins those hashes, so a silent re-derivation — a different transform, a different
source file — fails a test rather than reaching a printer. Re-running the derivation
script is byte-idempotent: the manifest's `derived` date is a constant in the script,
not today's date, so identical inputs give identical bytes.

---

## 3. Gear Geometry (measured, not designed)

Every figure below was measured from the reference STEP/STL files and is reproduced in
`app/geometry/gears.py` and `gears_manifest.json`.

| Fact | Value |
|---|---|
| Tooth count | 24 |
| Tooth pitch | exactly 15.0000° |
| Tip radius | 16.1093702290795 mm (diameter 32.2187 mm) |
| Root circle radius | 13.6613702290795 mm |
| Gear thickness | 10.000 mm |
| Tooth flanks | B-spline surfaces, axially crowned — a gear has a distinct top and bottom, and flipping one changes its geometry |
| Bores | BLIND pockets, not through-holes: A wall r 7.0 (opening r 5.2), B wall r 4.5 (opening r 2.7) |
| Gear/barrel interface face | a FULL SOLID DISK out to r 14.609 |
| Axis-to-axis distance of a meshed pair | 32.0473 mm |

A1 and A2 share one tooth clocking (0.0000° mismatch), as do B1 and B2, which is what
lets a pair mesh at both ends at once. A1 additionally carries the handle-connector
interface features.

**Consequence of the blind bores:** a one-piece roller has no through-path along its
axis. That is why the barrel is forced solid rather than cut (§6).

---

## 4. The Canonical Transforms

The assets are the sample meshes moved into the program's own frame, baked in at
derivation time. Rotations are proper rotations about +Z only — anything else would
mirror the braille or tilt the axis.

```
Cylinder A:  p_program = Rz(180°) · (p_sample − (−16.0000, 0.0000, 0)) − (0, 0, 26.0000)
Cylinder B:  p_program =            (p_sample − (+16.0473, −0.0079, 0)) − (0, 0, 26.0000)
```

That is the BROWSER frame: cylinder axis at x = y = 0, barrel centred on z = 0
(spanning z −26..+26), gears at z −36..−26 and +26..+36. The OpenSCAD frame seats the
barrel base at z = 0, so it is the same geometry translated +26.000 in z: gears at
z −10..0 and 52..62.

### 4.1 Why those rotations

Δ_A = 180° and Δ_B = 0° come from the orientation keys in the reference assembly. The
sample's A barrel carries the program's own four tactile row arrows, at z spans
6–16 / 16–26 / 26–36 / 36–46 — the web generator's row math to the millimetre — facing
Cylinder B. Measured residual after applying the map: **0.014°**. The B barrel carries
the matching recess column facing A: residual **0.030°**.

The registration identity closes independently. For the paired flow, a dot at program-A
angle θ must meet its recess at program-B angle −θ at the nip, which requires
Δ_A + Δ_B ≡ 180° (mod 360°) regardless of θ. The keys give 180.000° − 0.016°.

**B's axis is (+16.0473, −0.0079), not a round (+16, 0).** That is deliberate and
consistent across every B part in the reference set; it is never normalised. The
barrel-to-barrel surface gap at the nip follows from it: 32.0473 − 30.8000 =
**1.2473 mm** (decision D-6, confirmed by Brennen as the intended operating distance,
along with the resulting ~0.153 mm of dot-into-card engagement on 0.4 mm stock).

Research record: `01_SAMPLE_GEOMETRY_AUDIT.md` in the 2026-08-24 development folder.

---

## 5. The Size Gate (S7)

`validate_gear_rollers_settings(settings_data, shape_type, cylinder_params)` in
`app/validation.py` runs two gates, both skipped entirely when the flag is off, empty,
`None` or absent:

1. **Cylinders only.** Anything else raises with S6: *"Integrated gears are only
   available for cylinders."*
2. **The reference roller only.** The cylinder must be
   `GEAR_BARREL_DIAMETER_MM` 30.8 mm × `GEAR_BARREL_HEIGHT_MM` 52.0 mm, within
   `GEAR_BARREL_TOLERANCE_MM` 0.001 (float slack only — about 250× a float32 ULP at
   32 mm). Otherwise S7: *"Integrated gears are matched to the reference roller and
   only fit a 30.8 mm x 52 mm cylinder. Received X mm x Y mm."*

The default barrel spent part of 2026-08-31 at 30.8 × 54 mm (a 1 mm card
shelf at each end), which made gears on untouched dials warn and reject.
Brennen's deployment verdict the same day returned the default to the
**30.8 × 52 mm Version 1 standard** — the height every previously shipped V1
gear model pairs with — so **gear mode passes S7 on untouched dials again**.
The 54 mm card-shelf barrel is Embosser Version 2 only (forced by its preset
overrides). The gears themselves never moved: they are baked at fixed z (see
5.1). Height still tells the gears BETA (52) apart from Embosser Version 2
(54); both use the 30.8 diameter.

### 5.1 Why a rejection and not a warning

The gears are baked at fixed heights and do NOT move with the barrel. Measured on the
real assets, 2026-08-24:

| Barrel height | Result |
|---|---|
| 51.0 mm (1 mm short) | **THREE loose bodies** — the gears float free of the barrel. The mesh still reports `is_watertight` True, because each shell is closed; only a body count catches it. |
| 52.0 mm | one solid, correct |
| 62.0 mm | the barrel swallows 5 mm of each gear; the teeth at that end are gone |

Diameter never breaks the union, but it sets the nip: the surface gap is
32.0473 − diameter, so ⌀30.75 gives 1.2973 mm instead of 1.2473 mm and cuts
dot-into-card engagement from about 0.153 mm to about 0.103 mm. At ⌀32.2187 the barrel
reaches the tooth tips and the pair cannot mesh at all.

Note that ⌀30.75 is the Layer-1 schema default while ⌀30.8 is what the live UI sends —
so the shipped default path passes, and only a user who changed a dial meets the gate.
The UI shows the same sentence live, before a generate can fail (§8).

---

## 6. The Union

`app/geometry_spec.py` emits, when `gear_rollers_enabled == 1` on a cylinder spec:

```python
spec['gears'] = {
    'asset': 'gears_a' | 'gears_b',      # by plate_type, via a dict lookup that
                                          # raises rather than guessing a side
    'weld_rings': [                       # z computed as ±height/2, never hardcoded
        {'z_center': -26.0, 'r_in': 8.0, 'r_out': 13.0, 'height': 0.1},
        {'z_center':  26.0, 'r_in': 8.0, 'r_out': 13.0, 'height': 0.1},
    ],
}
```

Exactly two keys. D-8a's arrow weld is not among them — it rides on the markers'
`outline_delta` instead (§6.3), so the worker needs no gear-specific arrow code.

### 6.1 CSG order

`static/workers/csg-worker-manifold.js` unions the gears and their rings into the
RAISED stage, immediately after the base and well before any recess is cut. The
existing order — shell → raised dots → raised markers → subtract recess dots →
subtract markers — is unchanged. **No transform is applied to the asset**, and the
spec-frame theta negation that dots and markers receive does not apply to it: a gear
is not a spec-frame feature, and Phase 01 baked its placement into the bytes.

### 6.2 The barrel is solid — and an empty `polygon_points` is not enough

Decision D-2 forces the barrel solid while gears are on, because the blind bores mean a
cutout would seal a cavity nothing can reach or drain.

**Emitting `polygon_points: []` does NOT achieve that.** With no polygon,
`createCylinderShellManifold` falls through to hollowing by wall thickness. Measured in
Chromium before this was fixed: a geared cylinder came out with a 13.4 mm bore, the weld
rings floating loose inside it, and the cavity sealed at both ends by the ring bores — a
body of **−29,253 mm³**, and a negative volume IS an enclosed void.

The shell builder therefore takes an explicit `solid` argument, true whenever the spec
carries gears. A tidier alternative exists and was not taken: a `cylinder.solid` flag in
the spec itself, since "the barrel is solid" is a geometry decision and the spec is the
contract. Recorded here for whoever revisits it.

When the user had a nonzero cutout radius, the spec adds S3 to `spec['warnings']`:
*"The polygonal cutout is not used while integrated gears are on."*

### 6.3 The weld rings, and what they actually do

A hidden annulus straddles each gear/barrel contact plane: r 8.0–13.0, 0.1 mm tall,
centred on the plane. It is entirely buried — it clears both bore pockets and changes no
external surface — and it exists because the gear meets the barrel on an exactly
coincident face, which this project's printability rules forbid and float32 STL rounding
can turn into a pinch edge.

**Measured honestly: the rings contribute exactly 0.000000 mm³**, and manifold3d already
fuses the exactly-touching solids into one watertight body without them, before and after
a float32 round-trip. They stay per decision D-3 and the no-coincident-faces rule, but
nothing should claim they are what makes the roller solid.

### 6.4 D-8a: the raised-arrow weld

While gears are on, a RAISED tactile row arrow's `outline_delta` is
`GEAR_ARROW_WELD_MM` = 0.005 mm instead of 0.0. At the default 10 mm indicator length on
10 mm line spacing each arrow's apex touches the next arrow's base exactly, and float32
STL rounding welds that tangency into a non-manifold pinch edge — which would break the
watertight promise. 5 µm makes it a real overlap: 2.5% of the recess nesting clearance,
far below 0.1 mm print accuracy. Recess arrows are untouched; their 0.2 mm clearance
growth already overlaps. **With the toggle off the outline stays exactly 0.0**, so
existing exports keep the tangency they ship with today.

---

## 7. What "One Solid" Actually Means Today

On the **counter** plate a geared cylinder exports as exactly one watertight body
(measured in Chromium: 50,952.888 mm³, z −36.000..36.000).

On the **embossing** plate the roller body is one watertight solid (49,738.478 mm³, same
bounds) **plus one small separate body per raised braille dot** — the dome of each dot,
0.614 mm³ each. That is the long-standing second tangency inside every rounded dot: it is
present identically with gears off, it predates this beta, gears cannot fix it, and it is
tracked separately. Tests assert around it deliberately: exactly one body spans the full
72 mm, no body has negative volume, and every other body must look like a known dome
(under 1 mm³, watertight, entirely outside the barrel radius). A bare "one body" assertion
would be a test this generator cannot pass.

**The combined pair file is exempt from every one-body claim** (2026-08-25): a pair run
merges Cylinder A and Cylinder B into one `Cylinder_Pair_Geared_*` STL that deliberately
holds TWO full-span geared rollers 40.8 mm apart (centres; barrel surfaces 10 mm — the
gear tips ⌀32.2187 overhang, leaving an accepted 8.58 mm tip-to-tip gap, Brennen's
barrel-based spacing decision 2026-08-25). Assert `nPair = nA + nB` and B's X shift, never
body count or watertightness. Mechanics in STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md §6.

---

## 8. User Interface (`public/index.html`)

**Since 2026-09-20 (programme phases C1-C2):** the choice is the second of three
either/or radio groups inside the **Embosser setup** menu item at the top of the form
(`#embosser-setup-selection`, h2 "Embosser setup" — DRAFT S-M1; UI spec §4.8). The
old checkbox fieldset after the double-sided item is gone.

| Element | Id | String |
|---|---|---|
| Choice fieldset | `gear-rollers-selection` (nested, `aria-describedby="gear-rollers-note"`) | legend `<h3 class="legend-heading">Gears</h3>` |
| Radios `name="gear_mode"` | `gear_mode_standard` (`value="standard"`, checked) / `gear_mode_fixed` (`value="fixed"`) | DRAFT S-M3a *"Standard: print the gears separately"* / S-M3b *"Simplified: gears fixed to the cylinders"* |
| Description | `gear-rollers-note` | DRAFT S-M4 (20 words) *"Fixed gears save assembly time and parts, but each cylinder prints much longer and dots fail more often."* |
| Second note (visible only) | — | S2, signed 2026-08-24, kept whole: *"Adds the top and bottom drive gears to each generated cylinder as one solid piece, matched to the roller assembly. The barrel prints solid while this is on."* |
| Hardware note | `gear-hardware-note` / `-message` | DRAFT S-M5 (replaces S9′) *"Fixed gears fit only the fixed-gear housing for your version; the standard housing takes the standard cylinders. See Embosser Setup in Help."* ALWAYS visible; `#gear-hardware-link-slot` now holds a link that opens the help modal's Embosser Setup tab. Pinned loosely (contains "fixed-gear housing" / "standard housing") by `tests/e2e/gearRollers.spec.ts` |
| Cutout note | `gear-cutout-note` / `-message` | S3, unchanged |
| Size warning | `gear-size-warning` / `-message` | S7, unchanged, the same sentence the server would return |

`isGearRollersOn()` reads `#gear_mode_fixed.checked` and is the ONLY reader — the wire,
`updateGearRollersUI()`, pair mode and the filenames all go through it. Retired: the S8
legend *"Integrated Gears (BETA — for testing)"*, the S1 checkbox label, S9′, and the
Version 2 rule that hid and unchecked the toggle (§8.1).

**There is no card branch, on purpose.** Output Shape offers exactly one radio,
`value="cylinder"` — flat card plates have been parked since December 2025 — so a card
can never be selected here and a "disabled on card" state would be unreachable UI. The
cylinders-only rule is enforced by the API alone.

**Verbosity (ADA SOP Step 6.8).** The group's description is S-M4 alone (20 words). S2
stays on the page as a visible second note, not wired to `aria-describedby`.

**One action, one announcement (Section 12, C9).** The `gear_mode` change listener
composes DRAFT S-M10 (*"Standard gears selected."* / *"Simplified fixed gears
selected."*) with whatever notes `updateGearRollersUI()` raised (S3, S7) into ONE write,
deferred by a tick so it lands after the form-wide live-warning refresh that bubbles
behind it. Likewise S5 (*"Cylinder generated with integrated gears."*) is prepended to
the ready message rather than announced separately.

**Version 2 (temporary, until phase B6).** Choosing Version 2 while Simplified is
selected puts the choice back to Standard, persists `'0'` and appends DRAFT S-M13
(*"Fixed gears are not available for Version 2 yet, so Standard gears were selected."*)
to the version announcement — the API still refuses the combination. The gear choice
stays visible in Version 2; it is a menu item, not a beta toggle to hide.

### 8.1 Request assembly, filenames, persistence

Only one key is added, and only when the toggle is on:
`settings.gear_rollers_enabled = 1`. The gear geometry has no dials to send.

Filenames gain a `Geared_` segment (decision D-5), and only then:

| Flow | Toggle off | Toggle on |
|---|---|---|
| Single-sided | `Embossing_Cylinder_{preset}_{name}.stl` | `Embossing_Cylinder_Geared_{preset}_{name}.stl` |
| Single-sided counter | `Counter_Cylinder_{preset}_{name}.stl` | `Counter_Cylinder_Geared_{preset}_{name}.stl` |
| Double-sided | `Cylinder_A_{preset}_{name}.stl` | `Cylinder_A_Geared_{preset}_{name}.stl` |
| Double-sided counter | `Cylinder_B_{preset}_{name}.stl` | `Cylinder_B_Geared_{preset}_{name}.stl` |

Toggle-off names are byte-identical to today's, because public training videos show them.
Persistence uses `braille_prefs_gear_rollers_enabled`, and Reset to defaults clears it.

**Pair mode (2026-08-25).** This toggle alone now reveals Generate Both Cylinders and
relabels the plate radios to Cylinder A / Cylinder B (`isPairModeOn()` — reuse of the
signed labels confirmed by Brennen; a gear set only works meshed with its counterpart, so
the pair is the useful output). The FILENAMES table above is unchanged by that: a
gears-only pair run downloads the single-sided `Embossing_Cylinder_Geared_*` /
`Counter_Cylinder_Geared_*` names, plus the combined `Cylinder_Pair_Geared_{preset}_{name}.stl`
offered first (§7's two-body exemption applies). Both request bodies of the pair run carry
`gear_rollers_enabled: 1`, one per plate type — pinned by `tests/e2e/gearRollers.spec.ts`.

---

## 9. Acceptance Criteria and Regression Anchors

### 9.1 Tolerances

| Check | Tolerance | Why |
|---|---|---|
| Bounds | ± 0.001 mm | float32 ULP at 32 mm is 3.8e−6 mm, so this is ~250× the noise |
| Barrel rim radius | ± 0.005 mm | 4× below the 64-gon sagitta (0.0186 mm) the tessellation itself introduces |
| Gear surface agreement | ≤ 0.01 mm | measured against the vendored asset the union reproduces it exactly (0.000000); the smallest defect this must catch — a half-degree clocking slip — moves flank points 0.11 mm |
| Tooth phase | ± 0.01° | 0.0028 mm of arc at the tip radius |
| Volume | ± 0.5 mm³ | one raised braille dot is about 0.4 mm³ |
| Reference-roller comparison, gear zone | p99 ≤ 0.01 mm, max ≤ 0.02 mm | the residual is chord error between two tessellations of the same B-spline flanks: measured p99 0.0073, max 0.0129 over five seeds |
| Reference-roller comparison, barrel zone | ≤ 0.019 mm | the sagitta gap between the reference 180-gon barrel and the worker's 64-gon one |

### 9.2 Where each guarantee is tested

| Guarantee | Test |
|---|---|
| Assets are the bytes the manifest records | `tests/test_gear_rollers.py` |
| Barrel + gears + rings is one watertight body, survives a float32 round-trip | `tests/test_gear_rollers.py` |
| The union does not deform the gears | `tests/test_gear_rollers.py` |
| The assembled roller matches Brennen's own roller export | `tests/test_gear_rollers.py` (skipped when the reference folder is absent) |
| A browser-generated STL carries its gears | `tests/test_gear_rollers.py`, via `GEAR_ROLLER_BROWSER_STL_A` / `_B` |
| Spec block, D-2 force-solid, D-8a weld | `tests/test_gear_rollers.py` |
| Both validation gates, and that OFF adds none | `tests/test_gear_validation.py` |
| Geometry pinned over time | `tests/fixtures/gear_rollerA_golden.*`, `gear_rollerB_golden.*` |
| UI toggle, live notes, naming, persistence | `tests/e2e/gearRollers.spec.ts` |

**The transform itself can only be caught by the reference comparison.** A 24-tooth ring
is 15°-periodic, so a wrong rotation still lands teeth on teeth: comparing the union
against the asset it was built from cannot detect it (a 180° misrotation leaves the median
sampled distance at 0.0000). On a machine without the reference folder, the transform rests
on the manifest hash test.

### 9.3 Toggle-off byte-identity, proved at three levels

| Level | Method | Result |
|---|---|---|
| Geometry spec | 8 spec variants rendered from `git show HEAD:app/geometry_spec.py` and deep-compared — flag absent plus four spellings of off | zero mismatches; proved non-vacuous by a 0.01 mm nudge |
| Worker STL | the same specs through the worker at HEAD and as edited, in real Chromium, `fc /b` | "no differences encountered", both plates |
| Request body | captured from the real UI before and after the UI phase, `fc /b` | "no differences encountered" |

---

## 10. OpenSCAD

The desktop build gets integrated gears. The MakerWorld single-file variant does not
(decision D-4). **The reason was tested in the real product on 2026-08-25, and it is
simpler than the one originally reasoned here:** MakerWorld's Parametric Model Maker —
by then v1.1.0, redesigned 2025-10-27 — offers no way to upload a mesh at all. Its
editor has no asset panel, exposes no file input, and its native picker refuses STL
selection outright and accepts one file at a time. So the Customizer-limit question this
section used to cite never arises; the file simply cannot be delivered.

Two findings from the same session are worth keeping:

- **Our `.scad` is MakerWorld-valid.** Loading a probe file built its customizer group,
  dropdown and description text correctly from the `// [A, B]` annotation. Nothing about
  how this project writes parameters is the obstacle.
- **A single-file gear delivery is solved except for the upload.** Because `gears_a` and
  `gears_b` are genuinely different meshes (30,412 vs 30,152 triangles — not one rotated
  onto the other), one combined file with set B parked +100 mm in X, cropped per plate by
  `intersection()` with a box that touches no geometry, reproduces set A exactly and set
  B within 3.8 nm of float32 park-and-return noise (2.89 MB, ~0.2 s per crop, verified
  locally). If MakerWorld ever ships asset uploads, that is the design to reach for, and
  the 2026-08-23 re-vendor precedent (commit `4cc2914`) applies.

---

## Document History

| Date | Change |
|---|---|
| 2026-09-20 | **Out of beta, into the Embosser setup menu (programme decisions D-7, D-8; phases C1-C4).** §1 retitled "Feature Rules" (the rules are unchanged). §8 rewritten: the checkbox fieldset is gone; the choice is the **Gears** radio group (`#gear_mode_standard` checked / `#gear_mode_fixed`, DRAFT S-M3a/b, description DRAFT S-M4, S2 kept visible, S-M5 replacing S9′ with a link to the new help tab) inside `#embosser-setup-selection`, read only through `isGearRollersOn()`; one composed, deferred announcement per change (DRAFT S-M10 plus S3/S7); Version 2 no longer hides the choice — a temporary guard resets it to Standard and says so (DRAFT S-M13) until phase B6 ships fixed Version 2 gears. Strings await Brennen's sign-off. |
| 2026-08-31 | **§5 updated again the same day: the default barrel returns to the 52 mm reference size** (Brennen's deployment verdict — "Version 1 is the 52 mm standard with the previously provided gear models"). Enabling gears on untouched dials passes S7 again; the absent-height fallback `gears.DEFAULT_CYLINDER_HEIGHT_MM` follows (54 → 52, still decoupled from the card height). The 1 mm card-shelf barrel (54) is Embosser Version 2 only; the Version 1 `.scad` files keep the 52 mm barrel deliberately (Version 2's own OpenSCAD companion follows the 54 — see EMBOSSER_VERSION_2_KEYED_CUTOUTS_SPECIFICATIONS.md §12 — and the gears BETA remains the one feature with no Version 2 OpenSCAD counterpart, D-V6). No gear number, gate, asset, or signed string changed; the row below records the one-day 54 state it supersedes. |
| 2026-08-31 | **§5 notes the default barrel outgrowing the gears.** The app-wide default cylinder is now 30.8 × 54 mm (a 1 mm card shelf at each end), while the reference roller stays 30.8 × 52.0 — the gears are baked at fixed z and cannot follow. Enabling gears on untouched dials therefore shows S7 live, and a generate is rejected, until the height dial is set back to 52; height now tells the gears BETA apart from Embosser Version 2 (54) the way diameter no longer can. No gear number, gate, or asset changed. The absent-height fallback both S7 and the spec read moved with the default (52 → 54, now `gears.DEFAULT_CYLINDER_HEIGHT_MM`, no longer the card height), so an absent-height gear request is rejected rather than quietly passed. Gear golden fixtures re-ran byte-identical. |
| 2026-08-25 | **§10 rewritten from a tested result.** The MakerWorld exclusion (D-4) was justified here by reasoning about Customizer limits; probing the real product showed the blocker is one step earlier — PMM v1.1.0 accepts no mesh upload at all (no asset panel, no file input, picker refuses STLs, one file at a time). Records the two salvageable findings: our customizer syntax parses correctly there, and the combined-file crop delivery is proven locally (set A exact, set B within 3.8 nm) should uploads ever appear. |
| 2026-08-25 | **Pair mode, the combined file, and the S9 hardware note.** §8.1 records that the gears toggle alone now reveals Generate Both + the Cylinder A/B radio relabel (`isPairModeOn()`, label reuse confirmed by Brennen) while the download names stay the frozen Geared single-sided ones; §7 adds the combined `Cylinder_Pair_Geared_*` exemption from every one-body claim (two full-span rollers, 40.8 mm centres / 8.58 mm accepted tip gap — the barrel-based spacing decision); §8's string table gains S9, the always-visible version-1-vs-2 hardware warning (signed, with `#gear-hardware-link-slot` reserved for the v2 files link), and corrects S8 to signed per the authoritative code comment. |
| 2026-08-24 | Created. Documents the gear beta as merged: vendored assets and their format, the canonical transforms, the S6/S7 gates, the union and its solid-barrel requirement, D-8a, the UI, and the acceptance tolerances. Records that the emboss plate's loose dot domes predate this beta, and that the weld rings measure 0.000000 mm³. (This row also claimed S8 was unsigned; that was corrected on 2026-08-25 — see the row above and §8 — and the claim is struck here so the two do not contradict each other.) |
