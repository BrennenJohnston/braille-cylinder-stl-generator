# Cylinder Braille Guide

This guide helps you create braille labels for cylindrical surfaces using the Braille STL Generator.

## First: Decide What to Include

> **The most important decision:** Braille takes far more space than print. You cannot include everything — you must prioritize.

Before measuring your container or adjusting settings, answer this question:

**"What is the minimum information someone needs to identify this item or contact me?"**

### Space Reality

A typical cylinder (75mm diameter) fits approximately **4 rows with 13-14 cells each**. This is much less than you might expect.

### Content Priority (BANA Guidelines)

| Information | Priority | Guidance |
|-------------|----------|----------|
| **Primary identifier** | Essential | What this item IS (e.g., "Cinnamon", "Jane Smith") |
| **One contact method** | Essential | Phone OR email — pick one |
| Organization | High | Include only if it identifies you; omit if in email |
| Secondary details | Low | Usually omit — won't fit |

### If It Doesn't Fit

1. **Disable capitalization** — Saves ~1 cell per capital (default in this app)
2. **Abbreviate** — "Nat" for National, "Lib" for Library
3. **Remove redundant info** — If organization is in email, omit it
4. **Simplify** — "J. Smith" instead of "Jane Smith"

---

## Common Use Cases

Braille cylinders are commonly used for:

- **Container labels:** Spice jars, medicine bottles, storage containers
- **Identification:** Water bottles, travel mugs, personal items
- **Educational tools:** Learning aids, classroom materials

## Cylinder Parameters

| Parameter | What It Controls |
|-----------|------------------|
| Outer Diameter | The diameter of the object you're labeling (in mm) |
| Cylinder Height | How tall the braille surface will be |
| Wall Thickness | Thickness of the cylinder wall |
| Polygon Cutout | Number of flat sides for the inner shape |
| Seam Offset | Rotates where the seam (gap) appears |

## Measuring Your Container

### Outer Diameter

1. Wrap a piece of string or flexible tape around the container at the widest point where the label will go
2. Mark where the string meets itself
3. Measure the length of the string
4. Divide by π (3.14159) to get the diameter

**Example:** String length of 235mm ÷ 3.14159 = 74.8mm diameter

### Height

1. Measure the flat area where braille will go
2. Leave margin at top and bottom for fit
3. Consider how many rows of braille you need

## Text Capacity

Each row holds a fixed number of braille cells in this app:

- **13 text cells per row** by default (2 additional cells are reserved for the indicator letter and the triangle alignment indicator, for 15 columns in total)
- **13 text cells per row** when Indicator Letters is turned off (the alignment triangle is always included, for 14 columns in total)
- **14 text cells per row** in Tactile indicator mode (no marker cells; the arrow sits in the seam gap)
- Cells are spaced 6.5mm center-to-center

The cylinder's circumference determines whether that layout fits physically. What matters is the seam gap the columns leave — the arc between the last cell of a row and the first, measured the long way round. On the default 30.75mm-diameter cylinder (~96.6mm circumference) that gap is 5.6mm at 15 columns and 12.1mm at 14. Visual mode needs the gap to clear one cell's dot footprint (4.5mm at the default dot sizes) so the last cell cannot touch the first; Tactile mode needs room for the arrow plus a 5mm clear zone, which is why 14 columns is its ceiling. A larger diameter adds margin around the seam rather than more cells per row. The app warns live when the dialed columns no longer leave enough gap.

**Phone number tip:** a 10-digit phone number formatted per BANA guidance (`206.616.7678`) translates to exactly 13 cells — one number sign, ten digits, two periods. UEB keeps numeric mode across the periods, so only one number sign is needed. That is why every mode's default row holds at least 13 cells, so the number fits on one line. A hyphenated number needs three number signs and runs to 15 cells, which does not fit — split it after a period and start the next row with the remaining digits; the translator adds a new number sign (`⠼`) automatically (e.g., `⠼⠃⠚⠋⠲⠋⠁⠋⠲` then `⠼⠛⠋⠛⠓`).

## Key Parameters Explained

### Polygon Cutout

The inner surface of the cylinder uses flat faces (a polygon) rather than a true curve. This makes the STL file smaller and more compatible with 3D printers.

- **Lower numbers (e.g., 12-24):** Visible flat faces, smaller file size
- **Higher numbers (e.g., 48-64):** Smoother curve, larger file size
- **Recommendation:** 32-48 provides a good balance

### Seam Offset

Cylinders have a "seam" — a gap where the cylinder opens. The seam offset rotates where this gap appears.

- **Default:** Seam appears at one side
- **Adjust:** Rotate so the seam doesn't interrupt your text
- **Tip:** Place the seam at the back or between words

### Wall Thickness

- **Thinner (1.5-2mm):** Lighter, flexible, less material
- **Thicker (2.5-3mm):** Sturdier, better for larger cylinders
- **Recommendation:** 2mm for most applications

## Tips for Best Results

### Print Orientation

- Print cylinders **standing upright** for best dot quality
- Layer lines will be horizontal, matching how the cylinder will be read

### Test Fit

- Print a small section first to verify the diameter matches your container
- Adjust diameter slightly if the fit is too tight or too loose

### Seam Placement

- Rotate the seam to the back
- If text wraps around completely, place seam between words

### Material Considerations

- PLA works well for most applications
- PETG for containers that may get wet
- Consider food-safe filament for kitchen containers

## Using the Application

### Quick Start

1. Type your text under **Enter Text for Braille Translation**
2. Set **Placement Mode** to **Auto Placement**
3. Click **Show Expert Mode**, then click **Preview Braille Translation**
4. In **Surface Dimensions**, adjust diameter and height for your container
5. Click **Generate STL**, review the 3D preview, then **Download STL**
6. Switch to **Universal Counter Plate** and download again

### Capitalized Letters Toggle

The **Capitalized Letters** toggle controls how capitals are handled:

- **Disabled (default):** Text is automatically converted to lowercase. You can type normally — capitals are converted for you.
- **Enabled:** Capital letters are preserved, adding indicator cells.

**Why disable capitals?** Saves approximately 1 braille cell per capital letter.

### Recommended Settings for Cylinders

| Setting | Typical Value | Notes |
|---------|--------------|-------|
| Placement Mode | Auto Placement | Handles wrapping automatically |
| Capitalized Letters | Disabled | Saves one cell per capital; the app default is Enabled |
| Language | English (UEB) — contracted (grade 2) | The app default, per BANA's *Guidelines for Brailling Business Cards* |
| Indicator Letters | On | Adds the first letter of each row in the indicator area so readers can identify rows |

### Expert Mode Settings

Access these by clicking **Show Expert Mode**:

| Submenu | Key Settings |
|---------|--------------|
| Shape Selection | Output shape (cylinder), dot shape (cone/rounded) |
| Braille Spacing | Cells per row, number of rows, spacing |
| Surface Dimensions | Diameter, height, wall thickness, polygon sides |

## Double-Sided Cards (BETA)

Normally the app makes one cylinder that embosses braille on one face of a card. With the
**Double-Sided Card** beta turned on it makes a matched **pair** of cylinders instead, and a
card run between them comes out with braille on **both** faces in a single pass.

This is a beta. It has been printed and used — see [Is it ready to
use?](#is-it-ready-to-use) below — but proofread both sides and feel every braille surface
before you give a card to anyone.

Double-sided works for cylinders only. It is not available for flat cards.

### Steps

1. **Turn on the toggle.** Under the text box, tick **Double-Sided Card (BETA — for
   testing)**. Two things happen straight away: a **Back of Card** section appears below,
   and the **Row Indicator Style** locks to the tactile seam arrow.

   The lock is deliberate. Visual row markers spend a braille cell per row on a printed
   letter, and on a pair each cylinder would need its own markers on a surface the other
   cylinder is pressing against. The tactile seam arrow sits in the seam gap instead, where
   both cylinders of a pair can carry it. To choose visual markers again, turn the beta off.

2. **Type the front text** as you normally would, in the main text box.

3. **Type the back text** into the **Back of Card Text** box. It is translated with the same
   language and grade as the front, and it wraps across the rows for you, keeping whole
   words together. Press Enter only where you want to force the start of a new row.

   The back holds exactly as much as the front: 14 cells per row and 4 rows in tactile mode,
   so 56 cells a side and 112 for the card. Turning the beta on does not shrink either side.
   If the back text runs past that, a warning appears under the box while you type and tells
   you how much is over.

4. **Preview both sides.** Press **Preview Braille Translation** and the panel shows two
   headings, **Front of Card** and **Back of Card**, with the braille for each. Read both
   before you generate anything.

5. **Press Generate Both Cylinders (A and B).** One press builds the whole pair from the
   settings you have dialled in — you do not switch plates and generate twice. A status line
   reports progress as each cylinder is built.

6. **Save each file with its own button.** When the pair is ready, two buttons appear:
   **Download Cylinder A** and **Download Cylinder B**. Press each one in turn.

   **Nothing downloads on its own.** Two automatic downloads from one press made Chrome
   raise a "wants to download multiple files" prompt that names no file and is very hard to
   get out of with a screen reader — so each cylinder now waits for you to ask for it.

7. **Print both cylinders**, the same way you would print a single one: standing upright,
   in the same material.

8. **Emboss in one pass.** Mount the pair in the machine so they counter-rotate against each
   other, and feed the card through once. Front dots and back dots are pressed at the same
   time.

### Which file is which

Both files are named from your **front** text.

| File | What it is | What it carries |
|------|-----------|-----------------|
| `Cylinder_A_*.stl` | The embossing plate | The **front's** raised dots, plus one recess for every dot on the back, plus raised seam arrows |
| `Cylinder_B_*.stl` | The counter plate | The **back's** raised dots, plus one recess for every dot on the front, plus recessed seam arrows |

Every recess on one cylinder is paired one-to-one with a real dot on the other. Single-sided
counter plates carry a recess at every possible dot position; a double-sided counter plate
does not, because those positions are needed for the back's own dots.

### The fixed sizes

Double-sided cards ship with these dimensions set, and there are no dials for them. They
were chosen and then confirmed by embossing real card stock, so treat them as final.

| What | Value |
|------|-------|
| Back grid offset from the front grid | 1.25 mm across **and** 1.25 mm down (a diagonal shift) |
| Dot across the base | 1.2 mm |
| Recess (bowl) across, and deep | 1.3 mm across, 0.5 mm deep |

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

It keeps the BETA label because it has been proven by one builder, on one printer, with one
paper stock — not because anything is known to be wrong with it.

One thing the app cannot do for you: **the two cylinders must stay within about 1.0 degree
of each other as they turn.** Further out of phase than that and a front dot can meet the
back of the card where its paired recess is not, and the emboss degrades. That is a job for
whoever builds and aligns the machine, not for the STL files.

---

## Troubleshooting

### Cylinder Doesn't Fit Container

- Verify your diameter measurement
- Remember diameter = circumference ÷ π
- Print a test ring first

### Text Too Long for Row

- Reduce text length or use abbreviations
- Increase cylinder diameter if container allows
- Use multiple rows instead

### Seam Interrupts Text

- Adjust **Seam Offset** in Expert Mode → Surface Dimensions
- Rotate until seam appears in a natural break point

### Dots Too Large/Small After Printing

- Adjust dot parameters in Expert Mode → Braille Dot Adjustments
- This is printer-specific calibration

## Worked Examples

These examples show **what to type** into the application for common cylinder use cases.

### Example 1: Spice Jar Label

**Goal:** Label a spice jar (diameter ~55mm) so it can be identified by touch.

**Container measurement:** Circumference ~173mm ÷ π ≈ 55mm diameter — comfortably fits the default rows (13–14 text cells).

**Decision:** A single word is all that's needed — just the spice name.

**What to type:**
```
cinnamon
```

**Settings:**
| Setting | Value |
|---------|-------|
| Outer Diameter | 55mm |
| Placement Mode | Auto Placement |
| Capitalized Letters | Disabled |

**Result:** 1 row, fits easily. For longer spice names (e.g., "cardamom"), abbreviate if needed.

---

### Example 2: Medicine Bottle

**Goal:** Label a prescription bottle (diameter ~40mm) with drug name and dosage.

**Container measurement:** Circumference ~126mm ÷ π ≈ 40mm diameter — fits the default rows (13–14 text cells).

**Decision:** Two key pieces — medication name and dosage.

**What to type:**
```
amoxicillin
500mg
```

**Settings:**
| Setting | Value |
|---------|-------|
| Outer Diameter | 40mm |
| Placement Mode | Auto Placement |
| Capitalized Letters | Disabled |

**Result:** 2 rows. "amoxicillin" is at most 11 braille cells (fewer once contracted), within the default row capacity (13–14 text cells); abbreviate to "amox" if you add more per-row content.

---

### Example 3: Water Bottle ID Tag

**Goal:** Identify a personal water bottle (diameter ~75mm) at a shared workplace.

**Container measurement:** Circumference ~235mm ÷ π ≈ 75mm diameter — fits the default rows (13–14 text cells) with generous seam margin.

**Decision:** Name plus one contact method. Omit organization — not needed to identify a personal item.

**What to type:**
```
j. smith
555.867.5309
```

**Settings:**
| Setting | Value |
|---------|-------|
| Outer Diameter | 75mm |
| Placement Mode | Auto Placement |
| Capitalized Letters | Disabled |

**Result:** 2 rows on a 75mm cylinder. Using initial "J." instead of full first name saves cells. Phone formatted with periods per BANA guidance — `555.867.5309` is exactly 13 cells (one number sign, ten digits, two periods), so it just fits a default row.

---

### Notes on These Examples

- **Capitalized Letters:** These examples disable the toggle, so the app converts text to lowercase before translating. The app default is Enabled.
- **Grade 2 contracted:** The app defaults to contracted UEB. The cell counts quoted above are the uncontracted worst case, so a contracted translation of the same text fits the same row or better.
- **Measure first, then type:** Always measure your container and check the Text Capacity section above before entering text.

---

## Resources & Credits

### Official Standards

- [BANA Position Statements and Fact Sheets](https://www.brailleauthority.org/bana-position-statements-and-fact-sheets) — includes the official Business Cards Fact Sheet
- [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters) — primary reference for cylinder dot dimensions and spacing
- [BANA Braille Signage Guidelines](https://www.brailleauthority.org/braille-signage-guidelines)
- [The Rules of Unified English Braille (ICEB)](https://iceb.org/ueb.html)

### Related Guides

- [BUSINESS_CARD_TRANSLATION_GUIDE.md](BUSINESS_CARD_TRANSLATION_GUIDE.md) — Guidance for flat cards (when re-enabled)

### Acknowledgments

Cylinder guidance follows [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters). Content selection guidance adapted from the [*Business Cards Fact Sheet*](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf) (approved March 2024).

Braille translation powered by [liblouis](https://liblouis.io/).

---

*Document Version: 1.2*
*Last Updated: August 2026*
