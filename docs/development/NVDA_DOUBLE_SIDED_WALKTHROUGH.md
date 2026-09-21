# NVDA Walkthrough — Double-Sided Card

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

> **Rewritten 2026-09-20 (programme phase C4, NOT yet run):** double-sided is no
> longer a BETA checkbox inside a collapsible menu. It is the **Card sides**
> radio group (Single-sided / Double-sided) inside the **Embosser setup** item
> at the top of the form, and the Back of Card section is always on the page —
> greyed out and unavailable until Double-sided is chosen. Steps 1–5 and 23–24
> describe the new controls; the expected words in them are DRAFT strings
> awaiting Brennen's sign-off. Steps 6–22 are unchanged.

## Part 1 — Finding the choice while single-sided

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

**Step 2.** Keep pressing `Tab` until you reach the **Card sides** radio group
inside the Embosser setup item (it comes after the Embosser version and Gears
radio groups, before the front text box).

> **Expect:** "Card sides, grouping" (or "group") with its description
> "Double-sided embosses both faces of the card in one pass and uses the tactile
> row markers." — then "Single-sided, radio button, checked, 1 of 2".
>
> Three things must be in there: the group **name**, the description, and
> "checked" on Single-sided.

**Step 3.** Do **not** press an arrow key yet. Press `Tab` on through the front
text box until you reach the Back of Card heading area.

> **Expect:** you go straight from the front entry controls to the Select
> Language combo box. You must **not** land on "Back of Card Text" — while the
> card is single-sided, the Back of Card controls are **unavailable** (disabled)
> and Tab skips them. If you read the
> page with the arrow keys instead, you will find the "Back of Card — Enter Text
> for Braille Translation" heading and its controls announced as "unavailable".

---

## Part 2 — Choosing Double-sided

**Step 4.** `Shift+Tab` back to the Card sides radio group and press the
`Down arrow` to select Double-sided.

> **Expect:** "Double-sided, radio button, checked, 2 of 2" — and then, a moment
> later, ONE announcement read out on its own without you moving:
> "Double-sided card selected. The Back of Card section is now active. Locked:
> Double-sided is on, so the Row Indicator Style stays on the tactile seam arrow
> — both cylinders of a double-sided pair need it. Choose Single-sided to pick
> visual markers."
>
> That second announcement is a **polite live region**. It may arrive a second
> or two late, and NVDA will wait until it has finished saying "checked" first.
> If you hear nothing at all, that is a fail.

**Step 5.** Press `Shift+Tab` once, then `Tab` once, to land back on the
radio group and hear its state again.

> **Expect:** "Double-sided, radio button, checked, 2 of 2"
>
> The selection must have moved from Single-sided (step 2) to Double-sided.

---

## Part 3 — The Back of Card text box

**Step 6.** Press `Tab` once from the radio group.

> **Expect (since 2026-09-21):** "Auto Placement, radio button, checked, 1 of 2" —
> the back's own placement toggle, the same pair the front has. Press `Down
> arrow` once: "Manual Placement, radio button, checked, 2 of 2", and `Tab`
> then lands on "Back Line 1 Translation, combo box" followed by "Back Line 1,
> edit" with the help "Maximum 50 characters for back line 1" — one such pair
> per row. Press `Shift+Tab` back to the toggle and `Up arrow` to return to
> Auto Placement. Write down whether the rows were announced with their
> "Back Line" names (the front's rows say "Line 1").

**Step 6a.** With Auto Placement selected, press `Tab` once.

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
> "Locked: Double-sided is on…" note. The lock reason must travel with the
> disabled option, so a blind user learns *why* it is unavailable.

---

## Part 5 — Cylinders to Generate (Expert Mode)

Since 2026-09-21 there is no plate selector in the main form: Generate STL builds
**both** cylinders unless you choose one under Expert Mode. This part checks that
choice reads correctly; Part 6 runs the default.

**Step 13.** `Tab` forward past the Card Thickness radio group and Reset to the
"Show Expert Mode" button, press `Enter`, then `Tab` to the first submenu button and
press `Enter`.

> **Expect:** "Show Expert Mode, button, collapsed" → "expanded"; then
> "Cylinders to Generate, button, collapsed" → after `Enter`, "expanded", and
> a moment later focus lands on the first radio:
> "Cylinders to Generate, grouping" … "Both Cylinder A and B, radio button,
> checked, 1 of 3" with the description "Builds both cylinders and downloads
> them as one file, spaced for one print plate."
>
> On `Down arrow`: "Cylinder A — Embossing Plate, radio button, checked, 2 of 3";
> again: "Cylinder B — Universal Counter Plate, radio button, checked, 3 of 3".
> The names must say **Cylinder A** and **Cylinder B** whatever the card-sides
> choice — they are fixed now.

**Step 14.** Press `Up arrow` twice to put the selection back on "Both Cylinder A
and B", then `Shift+Tab` back to "Show Expert Mode" and press `Enter` to close it.

---

## Part 6 — Generate (both cylinders)

**Step 15.** Press `Tab` repeatedly until you reach the bottom action button.

> **Expect:** "Generate STL file from entered text, button" — and nothing else.
> There is no "Generate Both Cylinders" button any more (2026-09-21): this one
> button builds the pair. A **"Download STL"** button exists only after a
> successful run; if you have not generated yet, it must not be in the tab
> order at all.

**Step 16.** With focus on "Generate STL file from entered text", press `Space`.

> **Expect,** as the run proceeds, each announced on its own without you moving:
> - "Generating Cylinder A (1 of 2)..."
> - "Generating Cylinder B (2 of 2)..."
> - "Both cylinders are ready. Use the Download STL button to save one file with
>   both cylinders spaced for printing on one plate." (DRAFT S-E5, 2026-09-21)
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

> **Expect:** still on "Generate STL file from entered text, button". Focus must
> not have jumped to the top of the page — losing your place after a long
> operation is the single most disorienting thing a screen-reader user can hit.

**Step 18.** Press `Tab` once.

> **Expect:** "Download STL, button" — one button, and it was not there before
> the run.

**Step 19.** Press `Enter` on "Download STL".

> **Expect:** your browser's normal download announcement — **one file, named
> `Cylinder_Pair_…`, for one press**, and no "Download multiple files" prompt at
> any point. The button stays where it is and keeps its name.
>
> If instead you hear "The combined file could not be built. Download STL now
> saves Cylinder A; press it again for Cylinder B." (DRAFT S-E6), press it twice
> and expect one file each time. Write down which of the two you heard.

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

## Part 8 — Choosing Single-sided again

**Step 23.** `Shift+Tab` back to the Card sides radio group and press the
`Up arrow` to select Single-sided.

> **Expect:** "Single-sided, radio button, checked, 1 of 2", then a moment
> later, on its own: "Single-sided card selected."

**Step 24.** `Tab` forward through the front entry controls and on past the
Back of Card section.

> **Expect:** the Back of Card controls are **unavailable** again and Tab skips
> them: you go from the front entry controls to the Select Language combo box.
> The "Back of Card" heading itself is still on the page for arrow-key reading.

**Step 25.** `Tab` to the Row Indicator Style group.

> **Expect:** "Visual markers, radio button, checked, 1 of 2" — selectable again,
> **not** "unavailable", and the "Locked:" note is no longer read with it.

**Step 26.** `Tab` on past Card Thickness and Reset.

> **Expect:** no plate radio group anywhere in the main form (it lives under
> Expert Mode → Cylinders to Generate since 2026-09-21, and its names are
> Cylinder A / Cylinder B whatever the card-sides choice).

**Step 27.** `Tab` to the bottom buttons.

> **Expect:** only "Generate STL file from entered text, button". No "Download
> STL" button: choosing Single-sided changed a setting, and that hides the file
> from the previous run. Generate again if you want to hear it come back.

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
| 1.2 | 2026-08-19 | Step 13 back to "Card Thickness": the 2026-08-18 rename was itself the error, and the sr-only descriptions v1.1 called "already correct" were the original source of it. **The expected announcements DO change this time** — the group is announced as "Card thickness preset" and each option as "Preset settings optimized for embossing 0.Xmm card stock". Re-run step 13 against the new text. |
| 1.2 | 2026-08-18 | Corrected step 1 after the first real run: NVDA announces the skip link role-first ("same page link, Skip to main content"), not "Skip to main content, link" as v1.0 predicted, and the link is invisible until focused. Added a general note that role/name order varies and is not a fail. Step 16 now calls out message 1 as the regression-sensitive one, after the live-region defect it exposed was fixed (see UI Interface Core Specifications §4.10). |
| 1.3 | 2026-08-18 | Updated after the first run of Parts 2-3. Step 16's third message reworded and a check added that **nothing downloads by itself**: the old automatic pair download made Chrome ask "wants to: Download multiple files", a prompt that names no file and cycles Close/Allow/Block on every Tab, and the run ended in "Download blocked" with neither cylinder saved. Step 19 now presses both download buttons, since that is the only way files are saved. Steps 4 and 8 confirmed passing - the lock note and the back-of-card warning both spoke for the first time. |
| 1.4 | 2026-08-18 | Steps 15 and 27 note the new single-plate "Download STL" button, which is separate from the pair's Download Cylinder A/B and only exists after a single-plate generation. `#action-btn` no longer renames itself into a download control mid-focus. |
| 1.6 | 2026-09-21 | **Back of Card parity (programme sub-plan D, 2026-09-21; NOT yet run).** Part 3 gains the back placement toggle and the Manual rows (step 6, new step 6a for the text box). |
| 1.5 | 2026-09-21 | **One Generate, one Download (programme sub-plan E, 2026-09-21; NOT yet run).** Part 5 now checks the "Cylinders to Generate" radios inside Expert Mode (three options, both first, fixed A/B names); Part 6 runs the pair from the one Generate STL button and saves the combined file from the one Download STL button (DRAFT S-E5 / S-E6 expected wording); step 3 and steps 26–27 no longer expect the removed buttons or the main-form plate group. The "(Beta)" left in the title on 2026-09-20 dropped (D-7). |
