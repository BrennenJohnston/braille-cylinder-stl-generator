# NVDA Walkthrough — Double-Sided Card (Beta)

**Purpose:** a screen-reader pass over the whole double-sided beta flow, run by
hand. This is the one check in the
[ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md)
(section 6.5) that cannot be automated — automated tools read the markup, NVDA
reads what a blind user actually hears.

**Who runs this:** Brennen, or anyone with NVDA installed.
**How long:** about 20 minutes.
**Created:** 2026-08-17 (Phase 05).

---

## Before you start

1. Install NVDA if you do not have it: <https://www.nvaccess.org/download/> (free).
2. Start the app:

   ```powershell
   python backend.py
   ```

   Then open <http://localhost:5001/> in Chrome or Firefox.
3. Start NVDA. **NVDA key** is `Insert` (or `Caps Lock` if you set that up).
4. Turn on speech viewer so you can read back what was said:
   NVDA menu (`NVDA key` + `N`) → **Tools** → **Speech Viewer**.
   Everything NVDA says appears there as text you can copy into your results.

### The five keys this walkthrough uses

| Key | What it does |
|---|---|
| `Tab` / `Shift+Tab` | Move to the next / previous control |
| `Space` | Tick a checkbox, press a button |
| `Enter` | Press a button |
| `Up` / `Down` arrows | Move between radio buttons in a group |
| `NVDA key` + `Down arrow` | Read from here to the end (say-all) |

### What "expected announcement" means

NVDA says three things about a control: its **name** (what it is called), its
**role** (checkbox, button, radio button), and its **state** (checked, expanded,
unavailable). The wording below is what to listen for. NVDA may add or drop
small words depending on your verbosity setting and browser — **that is fine**.
What matters is that the name, the role, and the state are all there. If any one
of the three is missing or wrong, that is a fail worth writing down.

**Order varies, and that is not a fail.** NVDA often says the role *before* the
name — "same page link, Skip to main content" rather than "Skip to main content,
link" — and which order you get depends on the control and on your verbosity
setting. Judge each step on whether all three parts are present, never on the
order they arrive in.

---

## Part 1 — Finding the beta with the toggle off

**Step 1.** Load the page fresh, click once on an empty part of the page so focus
is inside it, then press `Tab` once.

> **Expect:** the skip link, which NVDA announces role-first:
> "same page link, Skip to main content"
>
> This one is easy to miss on a first run. The link is invisible until it takes
> focus and then slides into the **top-left corner** over 0.3 s, so watch that
> corner rather than the middle of the page. If you hear "Decrease font size"
> instead, you have gone one control too far — `Shift+Tab` back one and listen
> again.

**Step 2.** Keep pressing `Tab` until you reach the Double-Sided Card checkbox
(about 27 presses from the top of the page; it comes after the Row Indicator
Style radio buttons).

> **Expect:** "Emboss both sides of the card (interpoint), check box, not
> checked, collapsed" — followed by the long description beginning "Embosses
> both sides of the card in one pass: Cylinder A (the embossing plate) carries
> the front's raised dots…"
>
> Three things must be in there: the **name**, "not checked", and **"collapsed"**.
> "Collapsed" is how a blind user knows there is more to open.

**Step 3.** Do **not** press Space yet. Press `Tab` twice more.

> **Expect:** you go straight on to the Select Language combo box. You must
> **not** hear "Back of Card Text" or "Generate Both Cylinders" — while the beta
> is off, none of its controls exist for the screen reader.

---

## Part 2 — Turning the beta on

**Step 4.** `Shift+Tab` back to the Double-Sided Card checkbox and press `Space`.

> **Expect:** "checked" — and then, a moment later, the locked-style note read
> out on its own without you moving:
> "Locked: Double-Sided Card is on, so the Row Indicator Style stays on the
> tactile seam arrow — both cylinders of a double-sided pair need it. Turn the
> beta off to choose visual markers."
>
> That second announcement is a **polite live region**. It may arrive a second
> or two late, and NVDA will wait until it has finished saying "checked" first.
> If you hear nothing at all, that is a fail.

**Step 5.** Press `Shift+Tab` once, then `Tab` once, to land back on the
checkbox and hear its state again.

> **Expect:** "Emboss both sides of the card (interpoint), check box, checked,
> **expanded**"
>
> The word "expanded" must have changed from "collapsed" in step 2.

---

## Part 3 — The Back of Card text box

**Step 6.** Press `Tab` once from the checkbox.

> **Expect:** "Back of Card Text, edit, multi line, blank" — then the help text:
> "Your text is translated with the language selected below and wrapped across
> the braille rows for you, keeping whole words together. Press Enter only where
> you want to force the start of a new row. The back has the same number of rows
> and cells per row as the front."
>
> NVDA may also read the placeholder: "Type the text for the back of the card
> here. It wraps across the rows automatically."

**Step 7.** Type a short back text: `Brennen Johnston`

> **Expect:** your typing echoed back character by character (normal NVDA
> behaviour), and **no** warning announcement. Short text fits.

**Step 8.** Now select all (`Ctrl+A`) and type a deliberately over-long text:

```
This back of card text is far too long to fit on the rows that are available on a business card
```

Wait about two seconds without pressing any key.

> **Expect:** the overflow warning announced on its own, beginning:
> "Warning: Back line 1 …"
>
> This is the live warning added in Phase 02. It must arrive **without you
> moving focus** — a sighted user sees the red box appear, and a blind user has
> to be told. Note whether it interrupted your typing (it should not; it waits).

**Step 9.** Select all and shorten it back to `Second side`. Wait two seconds.

> **Expect:** no new warning. NVDA does not announce a live region disappearing,
> so silence here is correct.

---

## Part 4 — The Row Indicator Style lock

**Step 10.** `Tab` on to the Select Language combo box, then `Tab` again to
reach the Row Indicator Style radio group.

> **Expect:** "Tactile seam arrow, radio button, checked, 2 of 2" — plus its
> description "A raised arrow on the embossing plate and a matching recess on
> the counter plate…"

**Step 11.** Press the `Up arrow` and then the `Left arrow`, trying to move to
"Visual markers".

> **Expect:** **nothing moves.** You stay on "Tactile seam arrow, checked".
> The beta locks this choice, and the lock has to hold for keyboard users too.

**Step 12.** Use NVDA's object navigation or `Shift+Tab` to inspect the
"Visual markers" radio button if your NVDA settings let you reach disabled
controls (many do not — that is correct behaviour and not a fail).

> **Expect, if you can reach it:** "Visual markers, radio button, **unavailable**"
> plus **both** descriptions — the normal one about marker cells, *and* the
> "Locked: Double-Sided Card is on…" note. The lock reason must travel with the
> disabled option, so a blind user learns *why* it is unavailable.

---

## Part 5 — Cylinder A and Cylinder B

**Step 13.** `Tab` forward to the Print Layer Height radio group, then on to the
"Select Plate to Generate" radio group.

> **Expect:** "Cylinder A — Embossing Plate, radio button, checked, 1 of 2",
> then on `Down arrow`:
> "Cylinder B — Universal Counter Plate, radio button, checked, 2 of 2"
>
> The names must say **Cylinder A** and **Cylinder B**. With the beta off these
> same radios read "Embossing Plate" and "Universal Counter Plate" — you will
> check that again in Part 8.

**Step 14.** Press `Up arrow` to put the selection back on Cylinder A.

---

## Part 6 — Generate Both Cylinders

**Step 15.** Press `Tab` repeatedly until you reach the bottom action buttons.

> **Expect, in this order:**
> 1. "Generate STL file from entered text, button"
> 2. "Generate Both Cylinders (A and B), button"

**Step 16.** With focus on "Generate Both Cylinders (A and B)", press `Space`.

> **Expect,** as the run proceeds, each announced on its own without you moving:
> - "Generating Cylinder A (1 of 2)..."
> - "Generating Cylinder B (2 of 2)..."
> - "Both cylinders are ready. Use the Download Cylinder A and Download Cylinder
>   B buttons below to save them."
>
> **Nothing downloads by itself, and no Save As dialog should appear yet.** Until
> 2026-08-18 the run started both downloads on its own, which made Chrome ask
> "wants to: Download multiple files" — a prompt that names no file, gives no
> reason, and cycles Close/Allow/Block on every `Tab`. A real run ended in
> "Download blocked" with neither cylinder saved. If any Save As dialog or
> download prompt appears during this step, that regression is back.
>
> These come from a polite live region, so they queue up behind anything NVDA is
> already saying. The run takes a while — wait for the third message. **Write
> down whether you heard all three**, and whether the browser's own download
> notifications talked over them.
>
> **Listen hardest for the first one.** Until 2026-08-18 the region was hidden
> between messages, so message 1 arrived as a brand-new element rather than a
> change and was never spoken — messages 2 and 3 worked, which is exactly what
> makes this kind of bug easy to miss. If "Generating Cylinder A (1 of 2)..." is
> silent again, that fix has regressed.

**Step 17.** After the run finishes, check where your focus is.

> **Expect:** still on "Generate Both Cylinders (A and B), button". Focus must
> not have jumped to the top of the page — losing your place after a long
> operation is the single most disorienting thing a screen-reader user can hit.

**Step 18.** Press `Tab` twice.

> **Expect:**
> - "Download Cylinder A, button"
> - "Download Cylinder B, button"

**Step 19.** Press `Enter` on "Download Cylinder A", then `Tab` to "Download
Cylinder B" and press `Enter` there too.

> **Expect:** your browser's normal download announcement each time — **one file
> per press**, and no "Download multiple files" prompt at any point. Each button
> stays where it is and keeps its name.
>
> Both presses are needed: since 2026-08-18 this is the only way the files are
> saved, and a Cylinder A without its matching B cannot emboss a card.

---

## Part 7 — The braille preview, both sides

**Step 20.** `Shift+Tab` back up to the "Show Expert Mode" button and press
`Enter`.

> **Expect:** "Show Expert Mode, button, collapsed" before you press, and after
> pressing, the button reports **expanded**.

**Step 21.** `Tab` once to "Preview Braille Translation" and press `Enter`.

**Step 22.** Use `NVDA key` + `Down arrow` (say-all) to read the preview region.

> **Expect** to hear, in this order:
> - "Braille translation preview, region"
> - "Braille Translation Preview:, heading level 2"
> - **"Front of Card, heading level 3"**
> - the front rows: "Row 1:", "Row 2:", and so on
> - **"Back of Card, heading level 3"**
> - the back rows
>
> The two headings added in Phase 03 are what let a blind user jump straight to
> the side they care about with the `H` key. Try pressing `H` a few times to
> confirm you can hop between "Front of Card" and "Back of Card".

---

## Part 8 — Turning the beta off again

**Step 23.** `Shift+Tab` back to the Double-Sided Card checkbox and press
`Space`.

> **Expect:** "not checked", and the checkbox reports **collapsed** again.

**Step 24.** `Tab` forward through where the beta section used to be.

> **Expect:** "Back of Card Text" is gone entirely. You should go from the
> Double-Sided Card checkbox to the Select Language combo box.

**Step 25.** `Tab` to the Row Indicator Style group.

> **Expect:** "Visual markers, radio button, checked, 1 of 2" — selectable again,
> **not** "unavailable", and the "Locked:" note is no longer read with it.

**Step 26.** `Tab` to the "Select Plate to Generate" group.

> **Expect:** "Embossing Plate, radio button" and "Universal Counter Plate,
> radio button" — the Cylinder A / Cylinder B names must be **gone**.

**Step 27.** `Tab` to the bottom buttons.

> **Expect:** only "Generate STL file from entered text, button". The
> "Generate Both Cylinders" and both "Download Cylinder" buttons must have
> disappeared from the tab order completely.

---

## Results template

Copy this into `00_PROJECT_MEMORY.md` under the Phase log, fill in what you
actually heard, and mark each row Pass or Fail. Anything you are unsure about,
write "unsure" and quote what NVDA said — that is more useful than a guess.

```text
NVDA WALKTHROUGH RESULTS — double-sided beta
Run by: Brennen
Date:
NVDA version:            Browser + version:

Step | What I heard | Matched expected? | Pass/Fail
-----|--------------|-------------------|----------
 1   |              |                   |
 2   |              |                   |
 3   |              |                   |
 4   |              |                   |
 5   |              |                   |
 6   |              |                   |
 7   |              |                   |
 8   |              |                   |
 9   |              |                   |
10   |              |                   |
11   |              |                   |
12   |              |                   |
13   |              |                   |
14   |              |                   |
15   |              |                   |
16   |              |                   |
17   |              |                   |
18   |              |                   |
19   |              |                   |
20   |              |                   |
21   |              |                   |
22   |              |                   |
23   |              |                   |
24   |              |                   |
25   |              |                   |
26   |              |                   |
27   |              |                   |

Overall verdict:            /27 passed
Anything that felt confusing even though it technically passed:

Anything NVDA said that I did not expect at all:
```

---

## Related documents

- [ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) — section 6.5 is the requirement this satisfies
- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md) — section 4 accessibility features
- [Interpoint Double-Sided Specifications](../specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md) — what the beta does and why

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-17 | Created in Phase 05. Expected announcements taken from the live accessibility tree, not from the markup. |
| 1.1 | 2026-08-18 | Step 13 renamed "Card Thickness" to "Print Layer Height" to match the control's new label. No expected announcement changed — the group's sr-only descriptions were already correct and were not touched by that rename. |
| 1.2 | 2026-08-18 | Corrected step 1 after the first real run: NVDA announces the skip link role-first ("same page link, Skip to main content"), not "Skip to main content, link" as v1.0 predicted, and the link is invisible until focused. Added a general note that role/name order varies and is not a fail. Step 16 now calls out message 1 as the regression-sensitive one, after the live-region defect it exposed was fixed (see UI Interface Core Specifications §4.10). |
| 1.3 | 2026-08-18 | Updated after the first run of Parts 2-3. Step 16's third message reworded and a check added that **nothing downloads by itself**: the old automatic pair download made Chrome ask "wants to: Download multiple files", a prompt that names no file and cycles Close/Allow/Block on every Tab, and the run ended in "Download blocked" with neither cylinder saved. Step 19 now presses both download buttons, since that is the only way files are saved. Steps 4 and 8 confirmed passing - the lock note and the back-of-card warning both spoke for the first time. |
