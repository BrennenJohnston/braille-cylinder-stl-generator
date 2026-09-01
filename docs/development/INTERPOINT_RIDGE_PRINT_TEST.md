# Print Test — Where the Interpoint Ridge Actually Fails

**Purpose:** set `SAME_SURFACE_GAP_RELIABLE_MM` from a measured failure instead of
a guess. It is **0.45 mm and provisional** as of 2026-08-23, and the number it
replaced — 0.50 mm — turned out to have no stated basis anywhere in the code or
the specs. This test is the only thing that makes either number real.

**Who runs this:** Brennen. It needs a printer and a pair of eyes and fingers on
a real part.
**Created:** 2026-08-23, after the NVDA walkthrough found the 0.50 mm line
warning permanently about the shipped default (finding F-S).

---

## The question, and why it is not answered yet

The "ridge" is the strip of material left between a raised dot on one face and
the neighbouring recess that receives the other face's dot. Both sit on the same
cylinder surface. Too thin and it merges, tears, or never prints.

Two thresholds govern it:

| Constant | Value | Basis |
|---|---|---|
| `SAME_SURFACE_GAP_FLOOR_MM` | 0.34 mm | **Real.** Bambu X1C, 0.4 mm nozzle: Arachne force-widens paths from 0.1–0.34 mm up to 0.34 mm and drops anything below 0.1. This is a slicer limit and it blocks generation. |
| `SAME_SURFACE_GAP_RELIABLE_MM` | 0.45 mm | **Provisional and unmeasured.** Only warns; blocks nothing. |

**Why the existing data cannot settle it.** Two configurations have been printed
and recorded as embossing clean: printed ridges of **0.4953 mm** (0.3 package)
and **0.4278 mm** (0.4 package). *Both passed.* Two passing samples prove only
that the failure boundary lies somewhere below 0.4278 — they cannot say where.
Setting a threshold from them is exactly the mistake 0.50 already made.

**So this test needs a part that FAILS.** That is the whole point. A run where
everything prints beautifully at every rung still answers the question — it
just answers it differently (see *Reading the result*).

---

## Before you start

**Use the OpenSCAD generator, not the web app.** The web app has **no dial for
the interpoint offset** — it is fixed at 1.25/1.25 in the browser. The OpenSCAD
Customizer exposes `interpoint_offset_x_mm` and `interpoint_offset_y_mm` as
sliders over 1.15–1.35, which is what makes the ladder below reachable at all.

Repo: `braille-stl-generator-openscad`, on `develop`.

Set these and change **nothing else** between rungs:

| Parameter | Value |
|---|---|
| `double_sided` | **On** |
| `paper_thickness_preset` | per the rung (see the ladder) |
| `interpoint_offset_x_mm` | per the rung |
| `interpoint_offset_y_mm` | **same as x** |
| everything else | shipped defaults |

Print every rung on **the same printer, same filament, same nozzle, same profile,
same orientation**. A ridge that fails because you changed filament tells you
nothing about the threshold.

---

## The ladder

Every rung below **renders** — the hard assert (printed ridge ≥ 0.34 mm) does not
block any of them. Sorted by the printed ridge, which is what the printer has to
hold. "Nominal" is the number the app and the generator quote to the user.

| # | printed ridge | preset | offsets | nominal | note |
|---|---|---|---|---|---|
| 1 | **0.4953** | 0.3 | 1.25 / 1.25 | 0.5178 | known clean, shipped default for 0.3 |
| 2 | 0.4670 | 0.3 | 1.23 / 1.23 | 0.4895 | |
| 3 | 0.4387 | 0.3 | 1.21 / 1.21 | 0.4612 | |
| 4 | **0.4278** | 0.4 | 1.25 / 1.25 | 0.4678 | known clean, shipped default for 0.4 |
| 5 | 0.4104 | 0.3 | 1.19 / 1.19 | 0.4329 | |
| 6 | 0.3995 | 0.4 | 1.23 / 1.23 | 0.4395 | |
| 7 | 0.3821 | 0.3 | 1.17 / 1.17 | 0.4046 | |
| 8 | 0.3712 | 0.4 | 1.21 / 1.21 | 0.4112 | |
| 9 | 0.3538 | 0.3 | 1.15 / 1.15 | 0.3763 | |
| 10 | **0.3429** | 0.4 | 1.19 / 1.19 | 0.3829 | **lowest legal rung** — the assert blocks anything below |

Below rung 10 the generator refuses: 0.4 package at 1.17 would be 0.3146 mm
printed, under the 0.34 floor. That refusal is correct and is not part of this
test.

### Do not print all ten

**Start with rung 10 alone.** It is the lowest ridge the software will produce,
and it is the single most informative print:

- **If rung 10 prints clean**, every rung above it is clean too, and the failure
  boundary is *below the lowest value the software can even generate*. The
  reliable line then has no evidence for sitting anywhere above ~0.35, and 0.45
  is far too conservative — arguably the warning should sit just above the floor,
  or be retired in favour of the floor alone. **One print, question answered.**
- **If rung 10 fails**, bisect upward: rung 7 (0.3821), then halve again between
  the nearest pass and the nearest fail. Three or four pairs total.

Each rung is a **pair** — Cylinder A and Cylinder B — because the ridge only
exists where one face's dots meet the other face's recesses.

---

## What counts as failure

Judge the **ridge**, not the dots. Look at and feel the material *between* a
raised dot and its neighbouring recess.

**Fail** if any of these appear anywhere on the part:

- the ridge is **missing** — dot and recess run into one another
- the ridge is there but **torn, stringy, or intermittent** along its length
- the ridge is present but **collapses under a fingernail** with normal reading
  pressure
- the two cylinders **will not register** as a pair because the crowded features
  interfere

**Not a failure**, and do not record it as one:

- a ridge that is thin but continuous, intact, and survives handling
- surface roughness that matches the rest of the print
- anything that is also present at rung 1 or rung 4 — those are known-clean, so a
  defect appearing there is a printer or profile problem, not a threshold one

**Print rung 4 as a control** if anything ambiguous shows up. It is the shipped
default and is recorded as embossing clean; if the control looks the same as the
rung you are judging, the profile is the variable, not the gap.

---

## Reading the result

Write down, for each rung printed: **the printed-ridge figure, pass or fail, and
one sentence on what you saw.** Then:

| Outcome | What it means for the threshold |
|---|---|
| Rung 10 (0.3429) passes | No reachable configuration fails. The reliable line cannot be justified above ~0.35 from evidence. **Bring this back before changing anything** — it may mean retiring the soft warning rather than moving it. |
| Lowest pass is P, highest fail is F | The boundary is between F and P. The reliable line should sit **at or a little above P**, with the margin stated as a margin, not disguised as a measurement. |
| Everything fails, including rung 4 | Something is wrong with the printer, the profile, or the filament — rung 4 is known clean. Stop and diagnose that before drawing any conclusion about the gap. |

**Whatever the number turns out to be, it changes in four places and they must
move together:** `app/geometry/interpoint.py` (source of truth),
`DS_SAME_SURFACE_GAP_RELIABLE_MM` in `public/index.html`, `DS_GAP_RELIABLE` in
the OpenSCAD generator, and the MakerWorld variant. Four tests assert against it,
two specs document it, and the value is currently labelled **provisional** at
every one of those sites — that label comes off only when this test has run.

Also pending on this result: `ds-gap-warning` is deliberately excluded from the
generate-completion message (finding F-R), because Brennen's condition for
including it was a threshold that "fires only when something is actually wrong".
A provisional number does not meet that bar. **A measured one does**, and
`tests/e2e/completionWarnings.spec.ts` pins the exclusion so adding it back has
to be a decision.

---

## Related documents

- [Interpoint Double-Sided Specifications](../specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md) — §3 records the provisional 0.45 and why 0.50 had no basis; §10 the physical validation both known-clean points come from
- [NVDA Page Structure Walkthrough](./NVDA_PAGE_STRUCTURE_WALKTHROUGH.md) — the run that found the standing warning (F-S)
- [Screen Reader UX Research and Flow Audit](./SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md) — F-S in context

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-23 | Created after finding F-S. Every printed and nominal figure in the ladder is **computed from the shipped code** (`interpoint.same_surface_min_gap` and `printed_bowl_mouth_mm` at each offset), not estimated, and each rung was checked against the hard assert so the table contains no configuration the generator would refuse. The one-print-first design exists because two passing samples cannot locate a boundary and the lowest legal rung is the only print that can answer the question on its own. |
