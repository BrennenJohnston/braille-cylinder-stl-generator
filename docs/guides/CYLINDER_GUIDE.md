# Cylinder Braille Guide

This guide explains the two cylinders the Braille STL Generator makes. They are the
rollers of the hand-operated Custom Braille Embosser, which presses braille into business
cards: **Cylinder A** (the embossing plate) carries the raised dots and **Cylinder B** (the
counter plate) carries the matching recesses. A card fed between them comes out embossed.

## First: Decide What to Include

> **The most important decision:** Braille takes far more space than print. You cannot include everything — you must prioritize.

Before adjusting any settings, answer this question:

**"What is the minimum information someone needs to identify me or contact me?"**

### Space Reality

The default cylinders emboss **4 rows of 13 text cells** on a card. This is much less than you might expect.

### Content Priority (BANA Guidelines)

| Information | Priority | Guidance |
|-------------|----------|----------|
| **Name** | Essential | Who the card belongs to (e.g., "Jane Smith") |
| **One contact method** | Essential | Phone OR email — pick one |
| Organization | High | Include only if it identifies you; omit if in email |
| Secondary details | Low | Usually omit — won't fit |

### If It Doesn't Fit

1. **Disable capitalization** — Saves ~1 cell per capital (capitals are kept by default; the switch is under Translation Options in Expert Mode)
2. **Abbreviate** — "Nat" for National, "Lib" for Library
3. **Remove redundant info** — If organization is in email, omit it
4. **Simplify** — "J. Smith" instead of "Jane Smith"

---

## Cylinder Parameters

These dials are in Expert Mode → **Surface Dimensions**. The Card Thickness presets set
every one of them to the embosser's sizes.

| Parameter | What It Controls |
|-----------|------------------|
| Cylinder Diameter | The roller's outside diameter: 30.8 mm from the presets |
| Cylinder Height | The roller's length: 52 mm for Version 1, and 54 mm for Version 2, which adds a 1 mm card shelf at each end |
| Polygonal Cutout | Version 1 with Standard gears only: the shaped hole through the cylinder, set by its radius and number of points |
| Seam Offset | Version 1 only: turns the polygonal cutout around the cylinder's axis; the braille does not move |
| Slicer Seam Channel | The groove where your slicer hides its layer seam; on by default (see [Slicer Seam](#slicer-seam-the-layer-seam)) |

With Simplified gears the size is fixed: 30.8 × 52 mm for Version 1 and 30.8 × 54 mm for
Version 2. Version 2 adds four gear key clearance dials to this submenu.

## Text Capacity

Each row holds a fixed number of braille cells in this app:

- **13 text cells per row** by default (2 additional cells are reserved for the indicator letter and the triangle alignment indicator, for 15 columns in total)
- **14 text cells per row** when Indicator Letters is turned off (only the alignment triangle is reserved, for 15 columns in total)
- **13 text cells per row** in Tactile indicator mode (no marker cells; the arrow sits at the middle of the seam gap, and 13 is what a 90 mm card holds measured from it)
- Cells are spaced 6.5mm center-to-center

The cylinder's circumference determines whether that layout fits physically. What matters is the seam gap the columns leave — the arc between the last cell of a row and the first, measured the long way round. On the default 30.8mm-diameter cylinder (~96.8mm circumference) that gap is 5.8mm at 15 columns and 12.3mm at 14. Visual mode needs the gap to clear one cell's dot footprint (4.0mm with the 0.4mm preset's dots) so the last cell cannot touch the first; Tactile mode needs room for the arrow plus a 5mm clear zone, so 14 columns still fit the cylinder — but the card is the tighter limit: it is loaded with its leading edge at the alignment arrow, which sits at the middle of the seam gap, and 14 cells need about 93mm of a 90mm card, so the last cell would run off the end. That is why Tactile recommends 13, and the app warns when a layout would run off the card. A larger diameter adds margin around the seam rather than more cells per row. The app warns live when the dialed columns no longer leave enough gap.

**Phone number tip:** a 10-digit phone number formatted per BANA guidance (`206.616.7678`) translates to exactly 13 cells — one number sign, ten digits, two periods. UEB keeps numeric mode across the periods, so only one number sign is needed. That is why every mode's default row holds at least 13 cells, so the number fits on one line. A hyphenated number needs three number signs and runs to 15 cells, which does not fit — split it after a period and start the next row with the remaining digits; the translator adds a new number sign (`⠼`) automatically (e.g., `⠼⠃⠚⠋⠲⠋⠁⠋⠲` then `⠼⠛⠋⠛⠓`).

## Key Parameters Explained

### Polygonal Cutout

A Version 1 cylinder with Standard gears has a shaped hole along its middle, set by two
dials: the circumscribed radius (13 mm from the presets) and the number of points (12).
Keep the preset values. Version 2 cylinders have keyed holes instead, and Simplified-gear
rollers are solid apart from a 2 mm vent along the axis.

### Seam Offset

Seam Offset turns the polygonal cutout around the cylinder's axis, in degrees. The braille
does not move. Both presets set it to 0°. Version 2 hides the dial, because its keyed holes
never turn.

## Tips for Best Results

### Print Orientation

- Print cylinders **standing upright** for best dot quality
- Layer lines will be horizontal, matching how the cylinder will be read

### Simplified-Gear Rollers

- Print each roller with the bottom gear on the build plate and supports off
- A 2 mm vent runs along the axis, so the roller lifts off the embosser's peg without a vacuum

### Slicer Seam (the layer seam)

Every cylinder carries a shallow **seam channel**: a groove 1 mm wide and 0.5 mm deep running the full height of the outside on both cylinders: in the gap beside the row markers in Visual mode, or down the alignment-arrow column in Tactile mode, where on the embossing cylinder it steps around each raised arrow so the arrows stay whole. Your slicer's default seam mode ("Aligned" in Bambu Studio and PrusaSlicer) hides each layer's seam in that groove instead of in a braille dot, so **no seam painting is needed**.

- Leave the seam mode on **Aligned**. If your saved profile says **Back** or **Rear**, switch it to Aligned once: those modes put the seam at the rear-most point of every layer, which on the embossing cylinder lands on a raised dot no matter how the part is turned.
- The channel is on by default. To print a plain barrel instead, turn off **Slicer seam channel** under Expert Mode → Surface Dimensions.
- If the app says the channel was left out (a very narrow seam gap, or a cutout that would leave less than 1.2 mm of wall under the groove), paint the seam over the row markers as before.

### Material Considerations

- PLA works well for most applications

## Using the Application

### Quick Start

1. Under **Embosser setup** at the top of the page, choose your embosser version, gears and card sides
2. Type your text under **Enter Text for Braille Translation**
3. Set **Placement Mode** to **Auto Placement**
4. Click **Show Expert Mode**, check that **Card Thickness** matches the card stock you will emboss (0.4 mm is the default), then click **Preview Braille Translation**
5. Click **Generate STL** — it builds both cylinders — and review the 3D preview
6. Click **Download STL**: one file with both cylinders, spaced for one print plate.
   For a single cylinder, choose it under **Cylinders to Generate** (the first Expert
   Mode submenu) before you generate.

### Capitalized Letters Toggle

The **Capitalized Letters** toggle, under **Translation Options** in Expert Mode, controls how capitals are handled:

- **Enabled (default):** Capital letters are preserved, adding indicator cells.
- **Disabled:** Text is automatically converted to lowercase. You can type normally — capitals are converted for you.

**Why disable capitals?** Saves approximately 1 braille cell per capital letter.

### Recommended Settings for Cylinders

| Setting | Typical Value | Notes |
|---------|--------------|-------|
| Placement Mode | Auto Placement | Handles wrapping automatically |
| Capitalized Letters | Enabled (default) | Disable it only when a name will not fit: it saves one cell per capital, BANA's first suggestion |
| Language | English (UEB) — contracted (grade 2) | The app default, per BANA's *Guidelines for Brailling Business Cards* |
| Indicator Letters | On | Visual style only: adds the first letter of each row in the indicator area so readers can identify rows |

### Expert Mode Settings

Access these by clicking **Show Expert Mode**:

| Submenu | Key Settings |
|---------|--------------|
| Cylinders to Generate | Both cylinders (the default), or Cylinder A or Cylinder B on its own |
| Card Thickness | 0.4 mm or 0.3 mm card stock, or Custom; a preset sets every dot and surface dial |
| Row Indicator Style | Visual markers (the Version 1 default) or tactile seam arrows (the Version 2 default, and locked on for double-sided cards) |
| Shape Selection | Output shape (cylinder), dot shape (rounded/cone), indicator letters on/off |
| Braille Spacing | Cells per row, number of rows, spacing, and the X and Y position adjustments |
| Braille Dot Adjustments | Dot and recess dimensions |
| Surface Dimensions | Diameter, height, polygonal cutout, seam offset, the slicer seam channel and, in Version 2, the four gear key clearance dials |
| Translation Options | Capitalized Letters and Number Signs |

## Double-Sided Cards

Normally the two cylinders emboss braille on one face of a card: Cylinder A carries the
raised dots and Cylinder B the matching recesses. With **Double-sided** chosen, each
cylinder carries the raised dots for one face and the recesses for the other, and a card
run between them comes out with braille on **both** faces in a single pass.

It has been printed and used — see [Is it ready to use?](#is-it-ready-to-use) below — but
as with any braille, proofread both sides and feel every braille surface before you give a
card to anyone.

Double-sided works for cylinders only. It is not available for flat cards.

### Steps

1. **Choose Double-sided.** Under **Embosser setup** at the top of the page, in the
   **Card sides** choice, pick **Double-sided** (the page starts on Single-sided). Two
   things happen straight away: the **Back of Card** section below the front text becomes
   active (it is always on the page, greyed out until now), and the **Row Indicator
   Style** locks to the tactile seam arrow.

   The lock is deliberate. Visual row markers spend a braille cell per row on a printed
   letter, and on a pair each cylinder would need its own markers on a surface the other
   cylinder is pressing against. The tactile seam arrow sits in the seam gap instead, where
   both cylinders of a pair can carry it. To choose visual markers again, pick
   Single-sided. In Version 1 that gives back the visual markers Double-sided replaced;
   in Version 2, whose default is tactile, choose them under **Row Indicator Style** in
   Expert Mode.

2. **Type the front text** as you normally would, in the main text box.

3. **Type the back text** into the **Back of Card Text** box. It is translated with the same
   language and grade as the front, and it wraps across the rows for you, keeping whole
   words together. Press Enter only where you want to force the start of a new row.

   The back holds exactly as much as the front: 13 cells per row and 4 rows in tactile mode,
   so 52 cells a side and 104 for the card. Choosing Double-sided does not shrink either side.
   If the back text runs past that, a warning appears under the box while you type and tells
   you how much is over.

4. **Preview both sides.** Press **Preview Braille Translation** and the panel shows two
   headings, **Front of Card** and **Back of Card**, with the braille for each. Read both
   before you generate anything.

5. **Press Generate STL.** One press builds the whole pair from the settings you have
   dialled in — you do not switch plates and generate twice. A status line reports progress
   as each cylinder is built.

6. **Press Download STL.** It saves one file with both cylinders, spaced for one print
   plate (`Cylinder_Pair_*.stl`). To save a cylinder on its own, choose it under
   **Cylinders to Generate** in Expert Mode and generate again.

   **Nothing downloads on its own.** Two automatic downloads from one press made Chrome
   raise a "wants to download multiple files" prompt that names no file and is very hard to
   get out of with a screen reader — so every file waits for you to ask for it, one press
   each.

7. **Print both cylinders**, the same way you would print a single one: standing upright,
   in the same material.

8. **Emboss in one pass.** Mount the pair in the machine so they counter-rotate against each
   other, and feed the card through once. Front dots and back dots are pressed at the same
   time.

### Which file is which

Both files are named from your **front** text.

| File | What it is | What it carries |
|------|-----------|-----------------|
| `Cylinder_Pair_*.stl` | Both cylinders in one file (what Download STL saves by default) | Cylinder A and Cylinder B side by side, 10 mm apart, ready for one print plate |
| `Cylinder_A_*.stl` | The embossing plate (choose Cylinder A under Cylinders to Generate) | The **front's** raised dots, plus one recess for every dot on the back, plus raised seam arrows |
| `Cylinder_B_*.stl` | The counter plate (choose Cylinder B) | The **back's** raised dots, plus one recess for every dot on the front, plus recessed seam arrows |

Every recess on one cylinder is paired one-to-one with a real dot on the other. Single-sided
counter plates carry a recess at every possible dot position; a double-sided counter plate
does not, because those positions are needed for the back's own dots.

### The fixed sizes

Double-sided cards ship with these dimensions set, and there are no dials for them. They
follow the Card Thickness preset, and they were chosen and then confirmed by embossing real
card stock, so treat them as final.

| What | 0.4 mm card stock (default) | 0.3 mm card stock |
|------|-----------------------------|-------------------|
| Back grid offset from the front grid | 1.25 mm across **and** 1.25 mm down (a diagonal shift) | The same |
| Dot across the base | 1.2 mm | 1.2 mm |
| Recess (bowl) across, and deep | 1.4 mm across, 0.5 mm deep | 1.3 mm across, 0.5 mm deep |

The diagonal offset is the whole trick. If both sides used the same grid, a raised dot on
the front would sit exactly where a raised dot on the back needs to be, and the two would
flatten each other. Shifting the back grid diagonally means every dot on one face lands
opposite a recess on the other, with room to be pressed into.

The dots are a little smaller than the single-sided ones. That is what lets both faces be
embossed into one thickness of card without the two sides interfering.

### Is it ready to use?

It is **physically validated**: in August 2026 two rounds of Cylinder A / Cylinder B pairs
were printed on a Bambu Lab X1C with a 0.4 mm nozzle and used to emboss real card stock. The
braille came out legible on both faces. That is why the sizes above are final and have no
tuning dials.

It carried a BETA label until September 2026 because it had been proven by one builder, on
one printer, with one paper stock — not because anything was known to be wrong with it.

One thing the app cannot do for you: **the two cylinders must stay within about 1.0 degree
of each other as they turn.** Further out of phase than that and a front dot can meet the
back of the card where its paired recess is not, and the emboss degrades. That is a job for
whoever builds and aligns the machine, not for the STL files.

---

## Troubleshooting

### Cylinder Doesn't Fit the Embosser

- Check that **Embosser setup** names your embosser version and gears
- Use the Card Thickness preset's size: 30.8 × 52 mm for Version 1, 30.8 × 54 mm for Version 2
- Version 2: if a gear peg binds in its keyed hole, raise that gear's clearance dial under **Surface Dimensions**; lower it if the fit is loose

### Text Too Long for Row

- Reduce text length or use abbreviations
- Use multiple rows instead

### Dots Too Large/Small After Printing

- Adjust dot parameters in Expert Mode → Braille Dot Adjustments
- This is printer-specific calibration

## Worked Examples

The BANA business card examples, each with what to type into this app, are in the
[Business Card Translation Guide](BUSINESS_CARD_TRANSLATION_GUIDE.md#worked-examples--bana-braille--what-to-type).

---

## Resources & Credits

### Official Standards

- [BANA Position Statements and Fact Sheets](https://www.brailleauthority.org/bana-position-statements-and-fact-sheets) — includes the official Business Cards Fact Sheet
- [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters) — primary reference for cylinder dot dimensions and spacing
- [BANA Braille Signage Guidelines](https://www.brailleauthority.org/braille-signage-guidelines)
- [The Rules of Unified English Braille (ICEB)](https://iceb.org/ueb.html)

### Related Guides

- [BUSINESS_CARD_TRANSLATION_GUIDE.md](BUSINESS_CARD_TRANSLATION_GUIDE.md) — Choosing and formatting what goes on the card, with BANA's worked examples

### Acknowledgments

Cylinder guidance follows [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters). Content selection guidance adapted from the [*Business Cards Fact Sheet*](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf) (approved March 2024).

Braille translation powered by [liblouis](https://liblouis.io/).

---

*Document Version: 1.4*
*Last Updated: October 2026 (the cylinders described as the embosser's rollers only, with the jar and bottle label material removed; Simplified-gear printing; double-sided sizes per card stock)*
