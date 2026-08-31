# Embosser Version 2 — Keyed Gear-Peg Cutouts (PROTOTYPE) — Specifications

## Overview

Embosser **Version 2** is a new hardware design. Its drive gears are separate prints
again — not the one-piece rollers of the gear BETA — but each of the four gears carries
a **differently shaped peg**, and each end of each cylinder gets a **matching keyed
through-cutout**, so a gear physically cannot be seated in the wrong place. The
generator's job in Version 2 is the **cylinders only**: the gear files are assembly
reference, and nothing gear-shaped is generated.

Version 1 — today's app, the double-sided BETA and the integrated-gears BETA included —
stays reachable, byte-identical and supported indefinitely behind a selector that
defaults to Version 1.

Every number in this document was read back out of the merged code, not out of the
planning folder; where a number appears, the file that owns it is named. The single
owner of the geometry is `app/geometry/version2.py`, the way `app/geometry/gears.py`
owns the gear constants.

**Status:** 🧪 PROTOTYPE (Created 2026-08-28)
**Selector:** `embosser_version` (schema and runtime), integer enum `[1, 2]`, default `1`
**Scope:** cylinders only, single-sided and double-sided flows, pair mode included

> **This is a work-in-progress prototype.** The cylinder size, the cutout shapes and
> the fit may all change as testing continues — the barrel has moved twice, 30.1 mm →
> 30.5 mm → **30.8 mm**, and has now arrived at the size Version 1 has always used. The
> gear pegs have been cut to family R14 and measured; §11 records what that print found.

---

## 1. Rules

| Rule | Where it is enforced |
|---|---|
| Default Version 1 | `settings.schema.json` `embosser_version` default 1; `app/models.py` `'embosser_version': 1`; `#embosser_version_1` is `checked` in the markup |
| Version 1 is byte-identical to a build without the prototype | proved at five levels — see §9.3 |
| Cylinders only | `validate_embosser_version_settings()` in `app/validation.py` |
| The version is an exact integer | same function: `2.5` is refused, not rounded to Version 2 |
| The clearance stays inside 0.0–0.5 mm | same function, and the dial is bounded at the source |
| Integrated gears are Version 1 only | same function refuses the combination; the UI hides and unchecks the toggle |
| The barrel is solid while Version 2 is on | `app/geometry_spec.py` sets `cylinder.solid`; the worker's `keyed` branch forces it |
| The size is a WARNING, never a rejection | `version2.v2_size_message()`, carried in `spec['warnings']` |
| Existing golden fixtures never change | Phase 07 re-ran the double-sided and gear pairs; git reported them byte-identical |

With Version 1 selected, the request body gains no key, the geometry spec gains no
block, and every filename is exactly what the public training videos show.

### 1.1 The size is a soft preset

Version 2 sets the cylinder to **30.8 × 52.0 mm** (`V2_BARREL_DIAMETER_MM`,
`V2_BARREL_HEIGHT_MM`) with a tolerance of **0.001 mm** (`V2_SIZE_TOLERANCE_MM`). Off
that size the app shows S-V5 live and the spec carries the same sentence in
`warnings` — but the request is **accepted**. This is deliberately unlike the gear
BETA's hard size gate: the vendored gears cannot move with the barrel, whereas the
Version 2 barrel is still being found by printing.

It has moved twice, and the search is now over. The prototype shipped at 30.1 mm; the
first printed pair embossed with noticeably less pressure than Version 1, so on
2026-08-29 it went to **30.5 mm** — half way back toward Version 1's 30.8, so the next
print would change one variable by one known amount. On 2026-08-30 Brennen ran a 30.5
double-sided pair and reported the same two symptoms, weaker: the pair felt loose, and
the dots imprinted neither as deep nor as consistently. Two points on the same line, so
the stepping stopped and the value went to **30.8 mm**, the size Version 1 has always
used.

Both symptoms have one cause — too little interference between the pair — and the
diameter is the only dial that sets it. The larger barrel also **relaxes** the tightest
wall in the design rather than straining it: Cylinder A's anti-rotation socket leaves
1.4025 mm here against 1.2525 mm at 30.5. Nothing about the gear interface moves with
it; every key and every anti-rotation feature sits at a fixed radius from the axis.

That this preset is soft rather than a gate is what made each change a one-line edit
instead of a negotiation with a validator.

Because the golden-fixture generator refuses any spec carrying warnings, Version 2
fixtures can only ever exist at the preset size. That is intended.

---

## 2. The Four Profiles (family R14)

All four keys are **rounded rectangles** with a corner radius of **0.500 mm**
(`V2_KEY_CORNER_RADIUS_MM`), tessellated at **96 segments** per full circle
(`V2_ARC_SEGMENTS`). `V2_KEY_PROFILES` owns the dimensions:

| Key | Length × width (mm) | Where it sits | Section area at c = 0.110 (mm²) |
|---|---|---|---|
| `a1_square_14` | 14.0 × 14.0 | Cylinder A, **top** (the nub end) | 201.889 |
| `a2_rect_18x10` | 18.0 × 10.0 | Cylinder A, bottom | 185.889 |
| `b1_rect_16x12` | 16.0 × 12.0 | Cylinder B, **top** | 197.889 |
| `b2_rect_20x8` | 20.0 × 8.0 | Cylinder B, bottom | 165.889 |

`KEY_PROFILES_BY_PLATE` maps plate type to `(bottom, top)`:
`positive → ('a2_rect_18x10', 'a1_square_14')`, `negative → ('b2_rect_20x8',
'b1_rect_16x12')`. A plate type the map does not know raises rather than guessing a
side — guessing would silently print the wrong pair.

**The long dimension lies on 90/270°** and the short on 0/180° (`KEY_ROTATION_DEG` is
0.0), so a **flat always faces the tactile arrow column**. That is what makes the key
readable by hand as well as by machine.

### 2.1 Growing a key by the clearance

`grown_key_outline(name, delta)` builds the **exact parallel curve**: the sides grow by
`2 × delta` and the corner radius by `delta`, so at the default clearance the corner is
exactly 0.65 mm — the number the gear spec quotes.

It is **not** built by mitering an already-rounded outline. Mitering a *tessellated*
arc pushes each vertex out by `delta / cos(π / segments)`, i.e. 0.6500804 rather than
0.6500000 at the default. That is 0.08 µm — physically nothing — but it would
contradict the corner radius the gear side is cut to, so the exact construction is used
and `offset_polygon_miter()` is kept only for the nub, whose edges really are straight.

---

## 3. Orientation

The gears have **24 teeth**, so their tooth pitch is **15°**. A key's symmetry step
must be a whole multiple of that pitch, or seating a gear in an allowed rotation would
leave its teeth off the meshing grid. That admits symmetry orders {1, 2, 3, 4, 6, 8,
12, 24} and rules out pentagons and heptagons outright.

A rectangle has 2-fold symmetry (180°), which is 12 pitches — phase-safe. All four R14
keys therefore mesh identically in either of their two rotations, and **the nub alone**
fixes gear A1's orientation.

The nub's apex sits on `V2_ARROW_COLUMN_DEG` = **180°**, the same program angle the
tactile row indicators use, so the nub and the arrow column share a line. `seam_offset`
rotates the polygonal cutout only and **never turns the keys** — pinned by
`test_the_seam_offset_does_not_turn_the_keys`.

---

## 4. The Cutout

### 4.1 Two halves, one hole (D-V2)

Each peg profile is extruded to the **mid-plane**: the bottom key from the bottom face
to the centre, the top key from the centre to the top face. Together they are **one
through-hole**. The CAD's 15 mm blind pockets and mid-bore are not replicated.

Each half overshoots its own end by `V2_OVERLAP_MM` = **0.01 mm**, and the two overlap
across the centre by the same amount, so no two solids ever share an exact plane. The
z ranges are computed from **the request's own height**, not the preset's, so an
off-size barrel still gets a hole that meets in the middle.

### 4.2 The four mouths

Every mouth carries the **same** chamfer: the profile grown by
`V2_COUNTERSINK_OFFSET_MM` = **2.0 mm** at the face, tapering to the hole profile at
`V2_COUNTERSINK_DEPTH_MM` = **2.0 mm** deep — a true 45° flare, because the offset and
the depth match. D-V16 originally signed a second, scaled rule for the v7 six-scallop
star, whose tips would have swallowed the nub base; family R14 retired that star, so
`kind: 'hull'` is the only kind the spec emits and anything else is malformed.

**Slab placement is load-bearing.** A chamfer is the convex hull of two 0.01 mm slabs,
and *a hull's tapering face is supported by the FAR edge of each slab*. Each slab
therefore sits with its far edge exactly at the end of its own taper:

| End | Face slab | Inner slab |
|---|---|---|
| bottom | `face − 0.01 … face` | `face + depth − 0.01 … face + depth` |
| top | `face … face + 0.01` | `face − depth … face − depth + 0.01` |

Placed the other way round the 45° taper overshoots by the slab's own thickness.
Measured at six depth probes in `tests/test_version2_keyed.py::_countersink`.

The thinnest barrel wall under a mouth is **2.276 mm**, well over the 1.2 mm minimum.

### 4.3 The nub

Cylinder A's top face carries a triangular key nub that mates with gear A1's underside
notch. `V2_NUB` owns it: side **5.073158 mm**, base at r **9.754087 mm**, apex at r
**14.147487 mm**, **3.0 mm** tall, with a **0.5 mm** top chamfer and a **0.10 mm** base
flare. It is reproduced from Brennen's CAD as measured — including the fact that it is
**not exactly equilateral** (the flanks are 5.073086 against a 5.073158 base, 72 nm
apart, from six-decimal rounding). Any inradius arithmetic must use the real perimeter,
not `3 × side`.

**The nub is three parts unioned, never one hull.** It widens at the base and narrows
again at the top, so it is not a convex solid: a single hull over its slabs bridges
straight from the flare to the chamfer and bulges the body outward by 0.2 mm — measured
14.396 mm² of section where the profile is 11.144 mm². Gear A1's notch is this shape's
exact negative, so that bulge would have jammed the one gear that carries the handle
torque. The correct build is `hull(flare, body) + body + hull(body, chamfer)`.

**Both plates carry a nub since 2026-08-29** (D-R3-2). It rode on the positive plate
only while gear A1 was the only gear with a notch; every gear has an anti-rotation
feature now. The two shapes differ and the plate selector picks them — the builder
raises rather than letting a caller guess a side.

**The base flare was 0.5 mm until 2026-08-29, and could not fit** (D-R3-4). Probing
gear A1's notch by containment on a 10 µm grid showed its tangential half-width
**constant from the mating face to full depth** — the notch has no mouth relief at all.
A 0.5 mm flare therefore stood **0.49 mm proud per side** at the barrel face, so gear A1
cannot have been seating flush on either printed pair. Nobody reported it, because the
main profile fitted perfectly and the gear went on; it just stood off. At 0.10 mm the
flared nub still clears the notch wall by **0.05 mm** on every face.

The A-top mouth clears the nub at every clearance the dial allows: the mouth reaches
r 9.15 mm at the default and r 9.50 mm at the maximum, against the nub base at
r 9.754087 mm (`test_the_a_top_mouth_clears_the_nub`).

### 4.4 The anti-rotation features

Print round 2 (2026-08-29) added an anti-rotation feature to **every** gear, not only
A1. The top gears carry **notches** and the bottom gears carry solid **pins**, so each
cylinder stands a **nub** above its top face and sinks a **socket** into its bottom one.
All four sit on the arrow column and are 3.0 mm deep. `V2_GEAR_ANTIROT` records the four
gear features as measured; `ANTIROT_BY_PLATE` maps plate to feature.

The A triangle is **not** rebuilt from those measurements — it derives from `V2_NUB` by
an inset, so the shape has exactly one source. B's square is known only from the gear.

| Where | Kind | Construction | Inner r | Outer r | Half-width | Area (mm²) |
|---|---|---|---|---|---|---|
| A top | nub (union) | nominal triangle, **mitre** inset 0.30 | 10.054087 | 13.547487 | 2.016964 | 7.0461 |
| A bottom | socket (subtract) | the pin, **parallel curve** +0.15, arcs r 0.15, capped at r 14.00 | 9.754087 | 13.997487 | 2.426771 | 11.0980 |
| B top | nub (union) | 3.000 × 3.000, **sharp** corners | 9.9500 | 12.9500 | 1.5000 | 9.0000 |
| B bottom | socket (subtract) | 3.300 × 3.300, **parallel curve** +0.15, arcs r 0.15 | 9.9000 | 13.2000 | 1.6500 | 10.8707 |

**Nubs are mitred, sockets are parallel curves**, the same split the keys already use.
A socket is an internal corner in a vertically printed barrel and must be filleted; a
mitred socket corner would also sit 0.212 mm from the pin's corner instead of 0.150, and
would cost Cylinder A 0.15 mm of wall (**1.4025 → 1.2525 mm**). Until the 30.8 mm barrel
that second figure was the sharper argument — at 30.5 the same mitre went 1.2525 → 1.1025
and broke the 1.2 mm minimum outright. It no longer does, so **the stress riser is now
the whole reason**; the extra wall is not permission to mitre a socket.
`parallel_curve()` is a third construction beside `offset_polygon_miter()` and
`grown_key_outline()`, because neither of those can do it: the first is a mitre by
construction, and the second rebuilds a rounded rectangle rather than offsetting a ring.

Sockets are cut **V2_SOCKET_DEPTH_MM = 3.15 mm** deep — the pin's 3.0 plus one
clearance, so the pin cannot bottom out before the two faces meet — and carry no mouth
chamfer, because the gear's pin has its own 0.5 mm lead-in. Walls behind them, measured
to each socket's furthest point from the **axis**: A **1.4025 mm**, B **2.1141 mm**, both
≥ 1.2. For the square those differ from the reach along the column — its corner arc sits
at r 13.2859 where the column reach is 13.2000 — and the smaller figure is the real wall.
On the triangle the apex is on the column and the two agree.

`V2_SOCKET_MAX_RADIUS_MM = 14.00` caps Cylinder A's socket. **It trims exactly 0.0000 mm
today** and starts to bite above c = 0.1525; it exists so the wall guarantee survives
anyone raising the clearance or switching a socket to a mitre. It is a guard rail, not
dead code — do not remove it on the grounds that it does nothing.

**One interaction worth knowing.** Both the sockets and the tactile row arrows sit on
the 180° column, and from **five rows up** their axial bands overlap — the lowest arrow
reaches z −23.00 where the socket still reaches −22.85. It is safe, but only because of
which plate gets which: the plate that *recesses* its arrows is Cylinder B, whose socket
is the short square at r 13.20, leaving **1.35 mm**; the far-reaching triangle socket at
r 13.9975 is on Cylinder A, whose arrows stand *proud* and cut nothing into the barrel.
Swap either half of that pairing and the wall is 0.55 mm. Pinned by
`test_the_tactile_arrow_recess_clears_the_anti_rotation_socket`.

---

## 5. The Clearance

One dial, `version_2.key_clearance_mm` (schema) / `v2_key_clearance_mm` (runtime):
default **0.110 mm**, range **0.0–0.5 mm** (`V2_KEY_CLEARANCE_DEFAULT_MM`, `_MIN_MM`,
`_MAX_MM`). It is applied as an **outward** growth of each hole profile — the hole gets
bigger, the peg does not change.

**It governs the four holes and nothing else.** Two printed rounds bracketed it, both
on 2026-08-29: at **0.15** all four peg holes were too loose, at **0.075** they were too
tight, so the value lands between them at **0.110** (D-R3-1). The pegs measure exactly
nominal (§11), so a hole is its peg plus 2c.

Not the exact midpoint 0.1125: the dial's step is 0.005, and a default that is not a
whole number of steps above the minimum renders the input `:invalid` and disables
Generate with no message anyone can see. 0.110 / 0.005 = 22.

**The nub does NOT follow the dial** (D-V11, revised 2026-08-29). It is inset by
`V2_NUB_CLEARANCE_MM` = **0.30 mm**, which is **derived**, never retyped, as
`V2_GEAR_TRIANGLE_INSET_MM + V2_ANTIROT_CLEARANCE_MM` (D-R3-5) — the notch is already
inset from nominal by the first, so standing the nub off by one more of the second is
what leaves 0.15 mm perpendicular to each face. It was a hard 0.15 until 2026-08-29, and
at that value the nub was **line-to-line** in the notch: 5 µm of *interference* on the
base face, which no print reported. If a printed pair comes back rattling, the one-line
reversal is to hard-code 0.15 again. The dial used to shrink the nub by the same
`c` the holes grew by — one number, opposite directions — but gear A1's notch is a fixed
negative that is *already cut*, and it measures 3.943 × 4.553 mm: the nub at exactly
c = 0.15, to under half a micron. Under the old rule, tightening the holes would have
**grown** the nub into that notch by roughly 0.11 mm per face and stopped A1 seating.
Raise `V2_NUB_CLEARANCE_MM` only alongside a matching gear A1. Note that a miter inset
moves every *face* in by `c`, which on this triangle costs the base half-width
`√3 · c` = 1.732 c — the inradius is what drops by exactly `c`.

Raising the clearance eats into the error-proofing margins of §11: 0.890 mm at the
default, 0.500 mm at the maximum.

The dial is bounded **at the source** (`min="0" max="0.5" step="0.005"` on the input),
and 0.110 / 0.005 = 22 — a whole number of steps, so the shipped default is valid
against its own step. **The step moved from 0.01 on 2026-08-29**, and had to:
0.075 is not a multiple of 0.01, and a default that is invalid against its step makes
the input `:invalid` and kills the Generate button silently. This repo has been bitten
by that before, which is why `tests/test_smoke.py` divides one by the other.

---

## 6. The Wire Contract

With Version 2 on, `app/geometry_spec.py` sets `spec['cylinder']['solid'] = True` and
adds `spec['keyed_cutouts']`:

```jsonc
{
  "clearance_mm": 0.110,
  "halves": [
    { "end": "bottom", "profile": [ {"x": …, "y": …}, … 100 points ],
      "z_from": -26.01, "z_to": 0.01 },
    { "end": "top",    "profile": [ … 100 points ],
      "z_from": -0.01,  "z_to": 26.01 }
  ],
  "countersinks": [
    { "end": "bottom", "kind": "hull", "depth": 2.0,
      "face_profile":  [ … 100 points ],   // the profile grown by c + 2.0
      "inner_profile": [ … 100 points ] }, // the hole profile itself
    { "end": "top",    "kind": "hull", "depth": 2.0, "face_profile": […], "inner_profile": […] }
  ],
  "nub": {                                  // BOTH plates since 2026-08-29
    "profile":      [ … 3 points on A, 4 on B ],
    "top_chamfer":  { "depth": 0.5,  "profile": [ … ] },
    "base_flare":   { "depth": 0.10, "profile": [ … ] },
    "z_from": 25.99, "z_to": 29.0
  },
  "socket": {                               // BOTH plates; a plain prism
    "profile": [ … ],                       // no chamfer, no flare
    "z_from": -26.01, "z_to": -22.85
  }
}
```

Coordinates are rounded to 6 decimals (micron-cubed). Every profile is a simple loop
wound **counter-clockwise** — verified for all four keys, both mouth outlines and the
nub. That matters: the worker builds them with the `'NonNegative'` fill rule, and a
clockwise loop would have winding −1 and yield an **empty** cross-section with no error
at all.

A saved polygonal cutout is **dropped with a warning** (S-V14) rather than refusing the
request, so a stored cutout radius cannot lock a user out of the prototype.

---

## 7. CSG Order in the Worker

`static/workers/csg-worker-manifold.js`. The order is **unchanged** from Version 1;
Version 2 adds one cut and one union at points that cannot disturb it:

1. **Barrel** — `createCylinderShellManifold(cylinder, solid, keyed)`. A `keyed` block
   forces the barrel solid on its own, then subtracts the two key halves and the four
   mouth chamfers *while the barrel is still a bare cylinder and the boolean is
   cheapest*. `keyed` never falls through to wall-thickness hollowing: the keyed hole
   IS the bore, so a hollow barrel would open into the key pockets.
2. **Gears** — Version 1 only; refused in combination with Version 2.
3. **The nub** — `createNubManifold()`, unioned immediately after the base, inside the
   RAISED stage.
4. Raised dots (union) → raised markers (union) → recess dots (subtract) → markers
   (subtract).

Recesses still cut **last**, so nothing can be filled back in.

A malformed block throws with the key named — fewer than 3 points, a non-finite
coordinate, an unknown countersink kind, or a half whose `z_to` is not above `z_from`.
There are no silent skips.

---

## 8. User Interface (`public/index.html`)

The selector is a native `<fieldset>` in `<header class="site-header">`, **outside**
`<form id="braille-form">`. The group name, the arrow-key behaviour and the checked
state all come from the platform; the only ARIA is `aria-describedby`, which has no
native equivalent.

| Element | id | Carries |
|---|---|---|
| Fieldset | `embosser-version-selection` | legend S-V1 "Embosser version" |
| Radios | `embosser_version_1` (checked), `embosser_version_2` | S-V2 |
| Selector note | `embosser-version-note` | S-V3, the fieldset's `aria-describedby` |
| Prototype notice | `v2-prototype-note` | S-V4 |
| Size warning | `v2-size-warning` / `v2-size-message` | S-V5, the server's sentence verbatim |
| Clearance fieldset | `v2-keyed-cutouts-selection` | Expert Mode, hidden in Version 1 |
| Clearance dial | `v2_key_clearance_mm` | S-V9 label and help |
| Hidden rows | `cylinder-cutout-radius-row`, `cylinder-cutout-sides-row`, `cylinder-seam-offset-row` | inert in Version 2 |

**Selecting Version 2** snapshots five cylinder dials, applies `V2_PRESET_OVERRIDES`
(`cylinder_diameter_mm` 30.8, `cylinder_height_mm` 52, `seam_offset_deg` 0) on top of
the Card Thickness preset, hides the three inert rows, hides **and unchecks** the gears
toggle, reveals the clearance dial and the prototype notice, joins pair mode, and
announces S-V10 once. **Selecting Version 1** restores the snapshot exactly.

The Card Thickness presets themselves are untouched, but `checkPresetMatch()` **skips
the three dials Version 2 forces** while Version 2 is on. Without that skip the preset
re-detected "custom" the moment any dial was touched, which renamed downloads to
`…_V2_Custom_…` and persisted a card stock the user never chose. In Version 1 the skip
list is empty.

**Integrated gears are Version 1 only** (D-V6). The toggle is hidden *and* unchecked,
because a hidden checkbox that stayed on would still be read at generate time and turn
into a 400 the user cannot see the cause of.

### 8.1 One fewer braille cell in visual mode — RETIRED 2026-08-29

Version 2 recommended one cell fewer in visual mode for one day. At the prototype's
30.1 mm barrel, 13 text cells plus 2 marker columns left a seam gap of 3.6 mm where a
cell's dots need 4.0, so the recommendation named a layout the seam-fit check warned
against on the very same screen; dropping to 12 and 13 removed the contradiction.

**The 30.5 mm barrel ended it, and 30.8 widens the margin.** The same 15 columns leave
**5.76 mm** (π × 30.8 − 14 × 6.5 = 5.76; it was 4.82 at 30.5), clear by 1.76 mm, and
still clear against the widest 2.0 mm
dot any preset offers, which asks 4.5 mm. Recommending one cell fewer than fits is its
own defect, so the special case was removed rather than left standing. Version 2 now
recommends exactly what Version 1 does, in both modes.

The invariant that outlived the barrel change — and the one `tests/e2e/version2.spec.ts`
now pins — is not a count: **the recommended layout must never trip the seam-fit
warning.** Restore the drop in `updateGridColumnsForPlateType()`, gated on
`isVersion2() && !tactile`, if the barrel ever falls below **30.24 mm**, the diameter at
which π·d − 91 falls under 4.0. See RECESS_INDICATOR_SPECIFICATIONS.md v3.6.

### 8.2 Request, filenames, persistence

Only when Version 2 is on does `settings` gain `embosser_version: 2` and
`v2_key_clearance_mm`. The clearance is read from the bounded dial with **no fallback
literal** — an empty or unparseable value raises rather than quietly shipping geometry
at a clearance nobody asked for.

Filenames insert a `V2_` segment the way `Geared_` is inserted (D-V12):
`Embossing_Cylinder_V2_{preset}_{name}.stl`, `Counter_Cylinder_V2_…`,
`Cylinder_Pair_V2_…`, and `Cylinder_A_V2_…` / `Cylinder_B_V2_…` with double-sided on.
Version 1 names are byte-identical to today's.

Persistence stores `braille_prefs_embosser_version` (`'1'` or `'2'` only) and
`braille_prefs_v2_key_clearance_mm`. Both are restored **after** the Card Thickness
preset IIFE, not inside `applyPersistedSettings()`, because the preset rewrites
`cylinder_diameter_mm` on every load and an earlier restore would be silently
overwritten. Reset to defaults returns Version 1 and 0.110 mm, and **drops the
snapshot** — otherwise the restore would undo the reset it was called to finish.

Version 2 reveals **Generate Both Cylinders** and reuses the signed Cylinder A /
Cylinder B labels (D-V10): A and B are a matched, differently keyed pair, so the pair
is the useful output.

---

## 9. Acceptance Criteria and Regression Anchors

### 9.1 Tolerances

| Quantity | Tolerance |
|---|---|
| Barrel size match | 0.001 mm |
| Pocket outline vs analytic profile | 0.02 mm (browser STL), 1e-9 (analytic) |
| Fixture volume / area / bounds | 0.02 mm³ / 0.2 mm² / 1e-3 mm |
| Wrong-pair margin | ±0.001 mm against the pinned table |

### 9.2 Where each guarantee is tested

| Guarantee | Test |
|---|---|
| Profile maths, the fit matrix, the phase-safety orders | `tests/test_version2_profiles.py` |
| One watertight body, pockets, mouths, nub, minimum wall, as-built fit matrix, six mutations | `tests/test_version2_keyed.py` |
| Schema and models agree | `tests/test_smoke.py::test_schema_and_models_agree_on_embosser_version_fields` |
| The UI's numbers match the module | `tests/test_smoke.py::test_ui_version2_numbers_match_the_geometry_module` |
| Cylinders only, clearance bounds, gears refused | `tests/test_version2_validation.py` |
| The spec block, the warnings, z from the request's height | `tests/test_version2_spec.py` |
| The committed golden pair | `tests/test_golden.py` — `v2_cylinderA_golden`, `v2_cylinderB_golden` |
| The whole UI in three browsers | `tests/e2e/version2.spec.ts` |

224 Python tests and 33 end-to-end tests cover Version 2 as of 2026-08-28.

### 9.3 Version 1 byte-identity, proved at five levels

1. **Settings** — `vars(CardSettings)` for all eight fixture payloads plus an empty
   one, before and after: 78 → 80 attributes, every pre-existing one identical, and
   `git numstat` insertions-only.
2. **Geometry spec** — 60 comparisons (12 spec variants × 5 spellings of "off")
   deep-equal to `git show HEAD:app/geometry_spec.py`, with a 0.01 mm nudge proving the
   comparison is not vacuous.
3. **HTTP** — `test_golden_specs_ignore_an_absent_or_version_1_embosser_version` and
   `test_a_double_sided_request_is_unchanged_by_a_version_1_embosser_version`.
4. **Golden fixtures** — re-running `python -m tests.test_golden` regenerates the
   double-sided and gear pairs **byte-identical**; only the four new files appear.
5. **A real browser** — the `/geometry_spec` POST body *and* the exported STL for both
   plates, `fc /b` identical before and after the worker change and again before and
   after the UI change: "no differences encountered", eight comparisons.

---

## 10. What "One Solid" Actually Means

A Version 2 counter cylinder exports as exactly **one** watertight body. A Version 2
**embossing** cylinder exports as one watertight cylinder plus one small separate body
per raised braille dot — the dome of each dot. That is the long-standing tangency issue
in the dot geometry, present in Version 1 and with every beta off, and it is tracked
separately. It is the same exemption GEAR_INTEGRATED_ROLLERS_SPECIFICATIONS.md §7
records.

Body counting in the fixture tests is therefore never a bare `== 1`: exactly one body
is the cylinder, and every other body must look like one of those domes.

---

## 11. The Fit Matrix, and Why the Gears Must Be Re-Cut

The point of a keyed set is that **every peg enters its own hole and no other**, in
either rotation — the fit matrix is the identity.

**The v7 set did not achieve that.** Its A2 hexagon entered all four holes (only the
nub stopped it seating on A's top), and B1 entered B's bottom hole; just A1 and B2 were
exclusive. Brennen called this "a design error on my part" and asked for a redesign
judged on torque strength in PLA.

**Family R14 is the signed answer** (2026-08-28). Four size-ordered rounded rectangles
— see §2 — with 2-fold symmetry, which is phase-safe against the 15° tooth pitch. Its
fit matrix is the identity at **every** clearance the dial allows, and the smallest
wrong-pair protrusion is pinned in
`tests/test_version2_profiles.py::SMALLEST_WRONG_PAIR_PROTRUSION`:

| Clearance (mm) | Smallest wrong-pair margin (mm) |
|---|---|
| 0.00 | 1.000 |
| 0.075 | 0.925 |
| 0.110 (default) | 0.890 |
| 0.15 | 0.850 |
| 0.30 | 0.700 |
| 0.50 (maximum) | 0.500 |

**The gear pegs were re-cut to R14, and they now exist.** The v7 six-scallop star, the
hexagon and both 15 × 15 mm squares are retired, and none of them enters an R14 hole.
Brennen cut and printed the four replacements on 2026-08-29 (their files still carry
`v7` in the name — that is the gear body's version, not the peg's). Measured off those
STLs, every peg is exactly nominal:

| Gear | Measured peg (mm) | Profile | Corner radius (mm) |
|---|---|---|---|
| A1 | 14.000 × 14.000 | `a1_square_14` | 0.500 |
| A2 | 10.000 × 18.000 | `a2_rect_18x10` | 0.500 |
| B1 | 12.000 × 16.000 | `b1_rect_16x12` | 0.500 |
| B2 | 8.000 × 20.000 | `b2_rect_20x8` | 0.500 |

All four match `V2_KEY_PROFILES` and `V2_KEY_CORNER_RADIUS_MM` exactly. A2 was first
cut with a **2.000 mm** corner radius and re-cut to 0.500 the same day, on Brennen's
own catch. It would have fitted either way — a larger corner radius removes material,
so the peg still sits strictly inside a hole whose corners are 0.500 + c, and mutual
exclusion is decided by the rectangle sides, never the corners — but it now carries the
same corner bearing area as the other three.

---

## 12. OpenSCAD and MakerWorld

Version 2 gets **one self-contained OpenSCAD file** — presets inlined, no `include`, no
`import` — so the same bytes serve the desktop build and MakerWorld. This is possible
because all four profiles are simple primitives with exact numbers: **no DXF import is
needed anywhere**. The Version 1 `.scad` files are untouched.

The `.scad` must reproduce the two constructions §4 calls load-bearing — the far-edge
slab placement and the three-part nub — and must build its key outlines the way
`grown_key_outline` does (`offset(r = 0.5 + c)` around a square inset by that radius),
**not** `offset(delta = c)` on an already-rounded profile.

The file is not part of a released version yet and there is no MakerWorld listing for
it.

---

## Related Documentation

- `docs/KNOWN_ISSUES.md` — the user-facing prototype status (S-V13)
- `GEAR_INTEGRATED_ROLLERS_SPECIFICATIONS.md` — the Version 1 one-piece rollers
- `RECESS_INDICATOR_SPECIFICATIONS.md` §3, v3.5 — the arrow column and the Version 2
  cell recommendation
- `SURFACE_DIMENSIONS_SPECIFICATIONS.md` — cylinder size and the polygonal cutout
- `SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md` — the request schema

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-08-30 | 1.3 | **Third print test: the barrel walks back to 30.8 mm.** Brennen ran a 30.5 mm DOUBLE-SIDED pair and reported the pair felt loose and the dots imprinted neither as deep nor as consistently - the same two symptoms the 30.1 pair gave, weaker. Two points on one line, so the stepping stopped and the barrel took **Version 1's long-proven 30.8 mm** rather than another half step. Both symptoms have one cause, too little interference between the pair, and diameter is the only dial that sets it. Nothing about the gear interface moves with the barrel: every key and every anti-rotation feature is at a fixed radius from the axis, so the whole R14 and anti-rotation fit is unchanged. The larger barrel RELAXES the tightest wall - Cylinder A's socket goes **1.2525 -> 1.4025 mm**, B **1.9641 -> 2.1141** - and with it, a mitred socket would no longer break the 1.2 mm minimum (1.2525), so §5 now rests the parallel-curve rule on the stress riser alone. The seam gap widens to **5.76 mm**, so §8.1's retired one-fewer-cell rule stays retired. Version 2 and the gears BETA now share 30.8, so diameter no longer distinguishes them - the version does, and two tests that had silently relied on the sizes differing were made to set their own. The Version 2 golden pair was regenerated; every other fixture is md5-identical, and Version 1 is byte-identical at the geometry-spec level. |
| 2026-08-30 | 1.2 | **Second print test, and the anti-rotation keys.** Key clearance **0.075 → 0.110 mm**: the holes were too loose at 0.15 and too tight at 0.075, so the value lands between them; 0.110 and not the midpoint 0.1125, because the step is 0.005 and an off-step default kills Generate silently. Every gear gained an anti-rotation feature, so **both plates now carry a nub above the top face and a socket in the bottom one** (new §4.4) and the “positive plate only” rule is retired. The nub's base flare drops **0.5 → 0.10 mm**: gear A1's notch has no mouth relief, so the old flare stood 0.49 mm proud per side and A1 cannot have been seating flush on either printed pair. `V2_NUB_CLEARANCE_MM` **0.15 → 0.30**, now derived from its two parts rather than retyped. §11's margin table gains the 0.110 → 0.890 row. Both Version 2 goldens were regenerated; every other fixture is byte-identical. |
| 2026-08-29 | 1.1 | **First print test, and what it moved.** Barrel **30.1 → 30.5 mm**: the 30.1 pair embossed with noticeably less pressure than Version 1, and 30.5 is half way back to Version 1's 30.8. Key clearance **0.15 → 0.075 mm**, with the input step 0.01 → 0.005 because 0.075 is not a whole number of 0.01 steps: all four peg holes printed too loose, and the pegs measure exactly nominal. **The nub is decoupled from the dial** and pinned at `V2_NUB_CLEARANCE_MM` = 0.15 — gear A1's notch is already cut to that size, so under the old shared-dial rule tightening the holes would have grown the nub into it. §8.1's one-fewer-braille-cell rule is **retired**: at 30.5 mm the seam gap is 4.8 mm against the 4.0 needed. §11 gains the measured R14 pegs. The Version 2 golden pair was regenerated; the double-sided and gear pairs re-ran byte-identical. |
| 2026-08-28 | 1.0 | Initial specification. Family R14 keyed cutouts, the 45° mouths, the key nub, the clearance dial, the wire contract, the worker's CSG order, the user interface, the acceptance anchors, the fit matrix and the re-cut requirement, and the OpenSCAD packaging. Every number read back out of the merged code. |
