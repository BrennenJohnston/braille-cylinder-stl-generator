# Gear-Integrated One-Piece Rollers — Specifications

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
cylinders**, S-M3a/b (signed 2026-09-21)) inside the **Embosser setup** menu item — see §8. The rules
are unchanged:

| Rule | Where it is enforced |
|---|---|
| Default Standard (the old OFF) | `settings.schema.json` `gear_rollers.enabled` default false; `app/models.py` `'gear_rollers_enabled': 0`; `#gear_mode_standard` checked in the markup |
| OFF is byte-identical to a build without the feature | proved at three levels — see §9 |
| Cylinders only | `validate_gear_rollers_settings()` in `app/validation.py` |
| The cylinder must be the reference roller FOR THE CHOSEN VERSION (30.8 × 52 in Version 1, 30.8 × 54 in Version 2) | same function, §5 and §11.4 |
| The barrel is solid while ON | `createCylinderShellManifold(spec, solid)` in `static/workers/csg-worker-manifold.js` |
| Existing golden fixtures never change | Phase 07 regenerated the DS pair and git reported it byte-identical |

With the toggle off, the request body gains no key, the geometry spec gains no block,
and the filenames are exactly what the public training videos show.

---

## 2. The Vendored Assets

`static/assets/gears/` holds three Version 1 files, and **only
`scripts/derive_gear_assets.py` may write them** (the three Version 2 files beside them,
`v2_gears_*`, belong to `scripts/derive_gear_assets_v2.py` alone — §11.1):

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
2. **The reference roller only — for the chosen version.** In Version 1 the cylinder
   must be `GEAR_BARREL_DIAMETER_MM` 30.8 mm × `GEAR_BARREL_HEIGHT_MM` 52.0 mm, within
   `GEAR_BARREL_TOLERANCE_MM` 0.001 (float slack only — about 250× a float32 ULP at
   32 mm). Otherwise S7: *"Integrated gears are matched to the reference roller and
   only fit a 30.8 mm x 52 mm cylinder. Received X mm x Y mm."* Since 2026-09-21 the
   gate reads `embosser_version` (absent or blank → 1) and in Version 2 compares
   against `gears.reference_barrel(2)` = `version2.V2_BARREL_*` (30.8 × 54) with S-G1 (signed 2026-09-21)
    (§11.4) — `reference_roller_message(diameter, height, version)`.

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
(`#embosser-setup-selection`, h2 "Embosser setup" — S-M1 (signed 2026-09-21); UI spec §4.8). The
old checkbox fieldset after the double-sided item is gone.

| Element | Id | String |
|---|---|---|
| Choice fieldset | `gear-rollers-selection` (nested, `aria-describedby="gear-rollers-note"`) | legend `<h3 class="legend-heading">Gears</h3>` |
| Radios `name="gear_mode"` | `gear_mode_standard` (`value="standard"`, checked) / `gear_mode_fixed` (`value="fixed"`) | S-M3a (signed 2026-09-21) *"Standard: print the gears separately"* / S-M3b *"Simplified: gears fixed to the cylinders"* |
| Description | `gear-rollers-note` | S-M4 (signed 2026-09-21) (20 words) *"Fixed gears save assembly time and parts, but each cylinder prints much longer and dots fail more often."* |
| Second note (visible only) | — | S2, signed 2026-08-24, kept whole: *"Adds the top and bottom drive gears to each generated cylinder as one solid piece, matched to the roller assembly. The barrel prints solid while this is on."* |
| Hardware note | `gear-hardware-note` / `-message` | S-M5 (signed 2026-09-21) (replaces S9′) *"Fixed gears fit only the fixed-gear housing for your version; the standard housing takes the standard cylinders. See Embosser Setup in Help."* ALWAYS visible; `#gear-hardware-link-slot` now holds a link that opens the help modal's Embosser Setup tab. Pinned loosely (contains "fixed-gear housing" / "standard housing") by `tests/e2e/gearRollers.spec.ts` |
| Cutout note | `gear-cutout-note` / `-message` | S3, unchanged |
| Size warning | `gear-size-warning` / `-message` | S7 in Version 1, S-G1 (signed 2026-09-21) in Version 2 (the gate follows `isVersion2()` and compares against `V2_BARREL_*`, phase B6) — the same sentence the server would return |

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
composes S-M10 (signed 2026-09-21) (*"Standard gears selected."* / *"Simplified fixed gears
selected."*) with whatever notes `updateGearRollersUI()` raised (S3, S7) into ONE write,
deferred by a tick so it lands after the form-wide live-warning refresh that bubbles
behind it. Likewise S5 (*"Cylinder generated with integrated gears."*) is prepended to
the ready message rather than announced separately.

**Version 2 (since 2026-09-21, phase B6).** The choice is left exactly as the user set
it: Version 2 + Simplified is the fused Version 2 roller (§11). The temporary C2 guard
and its S-M13 (signed 2026-09-21) sentence are retired. Because a fixed-gear choice now survives a
version change, the version listener makes the same ONE composed, deferred announcement
the gear listener does — S-V10 plus whatever notes `updateGearRollersUI()` returned (S3
on the default cutout dial; S-G1 if the barrel was edited off-size) — otherwise the
form-wide refresh that bubbles behind it re-announced the bare note over S-V10. A fused
run's ready message carries S-G2 (signed 2026-09-21) alone (§11.6).

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

**Pair mode (2026-08-25; universal since 2026-09-21).** From 2026-08-25 this toggle alone
revealed Generate Both Cylinders and relabelled the plate radios (`isPairModeOn()`); since
2026-09-21 (programme sub-plan E) every run builds both cylinders unless one is chosen
under Expert Mode → Cylinders to Generate, and the ONE Download STL button saves the
combined `Cylinder_Pair_Geared_{preset}_{name}.stl` (§7's two-body exemption applies) —
`isPairModeOn()` and the relabel are retired. The FILENAMES table above is unchanged: a
gears-on single-cylinder run downloads the frozen `Embossing_Cylinder_Geared_*` /
`Counter_Cylinder_Geared_*` names. Both request bodies of the pair run carry
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
| Version 2 assets: four distinct sources, peg outlines = the key profiles, features on the arrow column, manifest bytes | `tests/test_gear_rollers.py` (`test_v2_*`) |
| Notch fill outline, cap, per-version asset lookup and messages, fused spec shape, retired S-V7 gate | `tests/test_version2_fused.py`, `tests/test_version2_spec.py`, `tests/test_version2_validation.py` |
| Fused Version 2 geometry pinned over time — ONE body, no void (D-6) | `tests/fixtures/v2_gear_rollerA_golden.*`, `v2_gear_rollerB_golden.*` (`tests/test_golden.py`) |
| Version 2 + Simplified accepted (200), `_Geared_V2_` name, S-G2 ready text, 74 mm STL, S-G1 live note | `tests/e2e/version2.spec.ts` |

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

## 11. Version 2 Fixed Gears (the fused one-piece Version 2 roller)

Since 2026-09-21 (sub-plan B of the 2026-09-20 programme, phases B1-B7) the Gears
choice works for the Version 2 embosser too: **Version 2 + Simplified** generates ONE
solid roller carrying the Version 2 drive gears. `app/geometry/gears.py` still owns every
gear constant; `app/geometry/version2.py` owns the notch fill (§11.3), the way it owns
every other Version 2 number.

### 11.1 The assets

`static/assets/gears/v2_gears_a.bin`, `v2_gears_b.bin` and `v2_gears_manifest.json` are
written ONLY by `scripts/derive_gear_assets_v2.py` from Brennen's four **v8** Version 2
gear STLs (A1 Gear v8, A2 Gear v8, B1 Gear v8, B2 Gear v8 — four distinct files, a check
the script enforces after a duplicate-file mistake on 2026-09-20). Same binary format as
§2.1 (`BCGR1`, 14-byte header). The manifest's sha256s are pinned by
`tests/test_gear_rollers.py::test_vendored_asset_is_the_bytes_its_manifest_records`,
parametrized over all four assets; re-running the script is byte-idempotent.

| File | Contents |
|---|---|
| `v2_gears_a.bin` | Cylinder A's pair: A1 (top) + A2 (bottom), 16,698 vertices / 33,396 triangles, 601,142 bytes |
| `v2_gears_b.bin` | Cylinder B's pair: B1 (top) + B2 (bottom), 16,625 vertices / 33,250 triangles, 598,514 bytes |
| `v2_gears_manifest.json` | Provenance: the four source sha256s, the frame, the per-gear fitted axes and transforms, the measured notch / pin windows, the peg outlines, the output sha256s |

Measured, not designed (all four gears): 24 teeth, tip radius 16.1093702290795 — the
Version 1 value to the last digit — 10 mm thick, root radius 13.6613. Unlike Version 1,
**every axis is measured** by a least-squares circle fit on each gear's own tip band and
each gear is centred on its own fitted axis (A1 −15.045 / A2 −15.050; B1 15.0517 / B2
15.0498 in the source files): the two gears of a set differ by up to 0.005 mm, float
noise that is recorded rather than averaged away.

### 11.2 The transform and the frame

Source frame: the cylinder's own, barrel spanning z 0..54 (the Version 2 height). The
script applies the SAME rule as §4 — the A set is rotated `Rz(180°)`, the B set is left
as is — and shifts z by −27 so the barrel is centred on z 0. In the browser frame the gear
bodies sit at z −37..−27 and +27..+37, and each gear's 15 mm peg lies INSIDE the barrel
(|z| 12..27). After the transform every anti-rotation feature — A1's triangular notch,
A2's triangular pin, B1's square notch, B2's square pin — sits on the 180° arrow column
(measured 180.000 / 180.000 / 179.875 / 180.000), and the pegs' long side lies along y
(14×14, 10×18, 12×16, 8×20 measured 3 mm from the free end), exactly as
`version2.V2_KEY_PROFILES` says ("a flat always faces the arrow column").

### 11.3 The notch fill (decision D-6)

In fused mode the barrel is **solid** and the keyed holes, mouth chamfers, nub and socket
are NOT cut: a peg buried in solid material needs no key, and a nub has no notch to enter
because the gear is already there. But each TOP gear still carries its anti-rotation
notch in its barrel-facing face, and a solid barrel over an open notch would seal an
undrainable void. So `version2.notch_fill_block(plate_type, height)` emits ONE prism per
plate — the measured notch outline (`V2_GEAR_ANTIROT`) grown by
`V2_NOTCH_FILL_GROWTH_MM` 0.05 as an EXACT parallel curve (a mitre would push the
triangle's apex 0.10 mm further out), from `z = height/2 − 0.05` to
`z = height/2 + depth + 0.05` (26.95..30.20 for both plates). Its outer edge is capped at
`V2_NOTCH_FILL_MAX_RADIUS_MM` 13.95, and a module-level assertion keeps that below the
mating gear's tip circle at the Version 1 operating distance (32.0473 − 16.1094 = 15.938
mm), so the fill can never touch the other roller's teeth. **The Version 2 operating axis
distance is not known** — recorded as an open item; the fill sits inside the root circle's
neighbourhood either way.

The weld rings (§6.3, r 8.0–13.0 × 0.1 mm at ±height/2) are unchanged: containment
probes in the derive script prove all four v8 gears solid at r 8.0 and 9.5 at every
angle, and at r 10.0–13.0 everywhere outside the ±20° notch window.

### 11.4 Spec, gates and the worker

- `app/geometry_spec.py`: with Version 2 AND gears on — `cylinder.solid = True`, NO
  `keyed_cutouts` block, `spec['gears'] = {'asset': 'v2_gears_a' | 'v2_gears_b',
  'weld_rings': [...], 'notch_fills': [<one block: gear, shape, profile, z_from, z_to>]}`;
  the S-V14 cutout warning and the D-8a arrow weld apply as in Version 1 gear mode.
  Version 2 without gears and Version 1 gear mode are byte-identical to before
  (`notch_fills` is absent from Version 1).
- `app/validation.py`: the S-V7 refusal ("Integrated gears are not available in
  Version 2.") is **retired**; the size gate picks the reference barrel by version —
  30.8 × 52 in Version 1 (S7), **30.8 × 54 in Version 2** with S-G1 (signed 2026-09-21): *"Fixed
  gears for the Version 2 embosser fit only a 30.8 mm x 54 mm cylinder. Received {d} mm
  x {h} mm."* Still a REJECTION, for the §5.1 reason: the gears are baked at fixed z.
- `static/workers/csg-worker-manifold.js`: `loadGearAsset` accepts the four asset names;
  the gear stage unions the vendored set, the weld rings and then each `notch_fills[]`
  prism (`keyedPrismManifold`, the nub's helper — a simple CCW loop, `NonNegative`). CSG
  order unchanged: shell → gears (+rings +fills) → nub (absent in fused mode) → raised →
  recesses.

### 11.5 What was proved (2026-09-21)

From REAL browser exports of both plates (Version 2 + Simplified, 0.4 preset, "abc"):
one watertight body each, z −37..+37, the axis and the old keyed-hole region solid, the
top notch window solid (192/192 probes), 24 teeth at both ends, the vendored gear surface
preserved to 0.00000 mm (p99 and max, outside the buried interface planes and the filled
notch window), the Python golden pair's gear region matching the worker to 0.00000 mm,
and the seam channel's floor at 181.67° / 178.33° on the gear faces. The new golden pair
`tests/fixtures/v2_gear_roller{A,B}_golden.*` (36,034 / 88,970 faces; 51,214.159 /
52,491.334 mm³) pins it; `mesh.split(only_watertight=False)` returning ONE body is the
D-6 acceptance (a sealed void would be a second shell).

### 11.6 UI and naming

The Gears choice is the same radio group (§8) in both versions. While Version 2 is chosen
`updateGearRollersUI()` gates against `V2_BARREL_*` with the S-G1 sentence (a smoke test
pins the template against `gears.py`); the version change makes ONE composed, deferred
announcement (S-V10 plus the gear notes) like the gear listener's own. A fused run's ready
message carries ONE prefix, S-G2 (signed 2026-09-21) *"Cylinder generated with fixed gears for the
Version 2 embosser."*, in place of S5 and S-V8′ back to back. Filenames need no new rule:
`Geared_` then `V2_` compose — `Embossing_Cylinder_Geared_V2_{preset}_{name}.stl`,
`Counter_Cylinder_Geared_V2_…`, `Cylinder_Pair_Geared_V2_…`. Version 1 names, Version 2
standard-gear names and the double-sided names never change.

### 11.7 OpenSCAD

No Version 2 OpenSCAD counterpart yet: the fixed Version 2 gears (like the seam channel)
are in the follow-on OpenSCAD-parity plan (programme plan §11) — `assets/v2_gears_{a,b}.stl`
derived from the web `.bin`s for the desktop Version 2 file only; MakerWorld cannot ship
assets (§10).

---

## Document History

| Date | Change |
|---|---|
| 2026-09-21 | **Pair mode is universal (programme sub-plan E).** §8.1's pair paragraph: Generate STL builds both cylinders by default and Download STL saves the combined Geared pair file; `isPairModeOn()` and the relabel retired; the frozen single-cylinder names come from Cylinders to Generate. Nothing else changed. |
| 2026-09-21 | **Version 2 fixed gears — the fused one-piece Version 2 roller (programme sub-plan B, phases B1-B7; decisions D-5, D-6).** New §11: the v8-derived `v2_gears_*` assets and their per-gear fitted axes (§11.1), the transform and frame (§11.2), the D-6 notch fill as an exact 0.05 mm parallel curve capped at 13.95 mm (§11.3), the fused spec / per-version size gate with S-G1 (signed 2026-09-21) / the worker's notch-fill union (§11.4), what the browser exports and the new `v2_gear_roller*` golden pair proved (§11.5), the UI and the composed `_Geared_V2_` names with S-G2 (signed 2026-09-21) (§11.6), and the OpenSCAD follow-on (§11.7). §1, §2, §5, §8 and §9.2 updated to match; the temporary S-M13 guard paragraph in §8 replaced; the "(BETA)" left in the title since 2026-09-20 removed (D-7). Open item: the Version 2 operating axis distance. |
| 2026-09-20 | **Out of beta, into the Embosser setup menu (programme decisions D-7, D-8; phases C1-C4).** §1 retitled "Feature Rules" (the rules are unchanged). §8 rewritten: the checkbox fieldset is gone; the choice is the **Gears** radio group (`#gear_mode_standard` checked / `#gear_mode_fixed`, S-M3a/b (signed 2026-09-21), description S-M4 (signed 2026-09-21), S2 kept visible, S-M5 replacing S9′ with a link to the new help tab) inside `#embosser-setup-selection`, read only through `isGearRollersOn()`; one composed, deferred announcement per change (S-M10 (signed 2026-09-21) plus S3/S7); Version 2 no longer hides the choice — a temporary guard resets it to Standard and says so (S-M13 (signed 2026-09-21)) until phase B6 ships fixed Version 2 gears. Strings signed off by Brennen 2026-09-21. |
| 2026-08-31 | **§5 updated again the same day: the default barrel returns to the 52 mm reference size** (Brennen's deployment verdict — "Version 1 is the 52 mm standard with the previously provided gear models"). Enabling gears on untouched dials passes S7 again; the absent-height fallback `gears.DEFAULT_CYLINDER_HEIGHT_MM` follows (54 → 52, still decoupled from the card height). The 1 mm card-shelf barrel (54) is Embosser Version 2 only; the Version 1 `.scad` files keep the 52 mm barrel deliberately (Version 2's own OpenSCAD companion follows the 54 — see EMBOSSER_VERSION_2_KEYED_CUTOUTS_SPECIFICATIONS.md §12 — and the gears BETA remains the one feature with no Version 2 OpenSCAD counterpart, D-V6). No gear number, gate, asset, or signed string changed; the row below records the one-day 54 state it supersedes. |
| 2026-08-31 | **§5 notes the default barrel outgrowing the gears.** The app-wide default cylinder is now 30.8 × 54 mm (a 1 mm card shelf at each end), while the reference roller stays 30.8 × 52.0 — the gears are baked at fixed z and cannot follow. Enabling gears on untouched dials therefore shows S7 live, and a generate is rejected, until the height dial is set back to 52; height now tells the gears BETA apart from Embosser Version 2 (54) the way diameter no longer can. No gear number, gate, or asset changed. The absent-height fallback both S7 and the spec read moved with the default (52 → 54, now `gears.DEFAULT_CYLINDER_HEIGHT_MM`, no longer the card height), so an absent-height gear request is rejected rather than quietly passed. Gear golden fixtures re-ran byte-identical. |
| 2026-08-25 | **§10 rewritten from a tested result.** The MakerWorld exclusion (D-4) was justified here by reasoning about Customizer limits; probing the real product showed the blocker is one step earlier — PMM v1.1.0 accepts no mesh upload at all (no asset panel, no file input, picker refuses STLs, one file at a time). Records the two salvageable findings: our customizer syntax parses correctly there, and the combined-file crop delivery is proven locally (set A exact, set B within 3.8 nm) should uploads ever appear. |
| 2026-08-25 | **Pair mode, the combined file, and the S9 hardware note.** §8.1 records that the gears toggle alone now reveals Generate Both + the Cylinder A/B radio relabel (`isPairModeOn()`, label reuse confirmed by Brennen) while the download names stay the frozen Geared single-sided ones; §7 adds the combined `Cylinder_Pair_Geared_*` exemption from every one-body claim (two full-span rollers, 40.8 mm centres / 8.58 mm accepted tip gap — the barrel-based spacing decision); §8's string table gains S9, the always-visible version-1-vs-2 hardware warning (signed, with `#gear-hardware-link-slot` reserved for the v2 files link), and corrects S8 to signed per the authoritative code comment. |
| 2026-08-24 | Created. Documents the gear beta as merged: vendored assets and their format, the canonical transforms, the S6/S7 gates, the union and its solid-barrel requirement, D-8a, the UI, and the acceptance tolerances. Records that the emboss plate's loose dot domes predate this beta, and that the weld rings measure 0.000000 mm³. (This row also claimed S8 was unsigned; that was corrected on 2026-08-25 — see the row above and §8 — and the claim is struck here so the two do not contradict each other.) |
