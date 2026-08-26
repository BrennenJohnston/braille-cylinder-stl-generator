# NVDA Walkthrough — Page Structure, the Skip Links, and the Closing Re-Listen

**Purpose:** the listening pass that closes the whole POST15_7 follow-up
programme. Items A–I changed what this page *is* structurally — its headings, its
landmarks, its descriptions, its tab ring — and every one of them was signed off
on **probe numbers**. The probes prove the tree is correct. They cannot prove the
page got easier to use.

That distinction is the entire reason POST15_7 exists. The item before it passed
all of its counts and still failed the user. **So do not read this document as a
formality.** If something here sounds worse than the numbers say it should, the
numbers are what is wrong.

**Who runs this:** Brennen, or anyone with NVDA installed.
**How long:** about 25 minutes for Parts 1–5, plus however long Part 6's generate
flow takes — Part 6 is *timed on purpose* and there is no target to beat.
**Created:** 2026-08-23 (POST15_7 item G, the closing re-listen).

This is a sibling of the
[NVDA Live Warnings Walkthrough](./NVDA_LIVE_WARNINGS_WALKTHROUGH.md) and the
[NVDA Double-Sided Walkthrough](./NVDA_DOUBLE_SIDED_WALKTHROUGH.md). The setup
notes, the key list, and the **"role and name order varies and is not a fail"**
rule in those two apply here unchanged.

---

## Before you start

1. Start the app:

   ```powershell
   python backend.py
   ```

   Then open <http://localhost:5001/> in Chrome or Firefox.

2. **Turn NVDA's speech log on and capture from it — not by ear.** This is not
   optional here: most of what follows is a **count**, and counts transcribed by
   ear were wrong twice in this project already.

   NVDA menu (`NVDA` + `N`) → **Preferences** → **Settings** → **General** →
   Logging level → **Input/Output**. Restart NVDA. The log is `%TEMP%\nvda.log`,
   and NVDA menu → **Tools** → **Log Viewer** shows it live.

3. **Window the log before counting anything.** This trap has now bitten twice.
   NVDA also reads the terminal or editor showing *this document*, which quotes
   the very strings you are counting — in the 2026-08-22 capture, **2,206 of
   3,302 utterances fell outside the browser-focused segment**. Use the tool
   written for it:

   ```powershell
   python build\a11yverify\post15_6\nvdaspeech.py mark      # before each Part
   python build\a11yverify\post15_6\nvdaspeech.py since     # after each Part
   ```

   Mark before a Part, read back after it, and only count what comes out.

4. **Put the page in a known state, then reload.** The app remembers Placement
   Mode, Shape and the Capitalized Letters setting in this browser, so "a fresh
   load" is not automatically "what a new user sees".

   | Control | Must be | Why it matters here |
   |---|---|---|
   | Placement Mode | **Auto Placement** | Part 5 types into the Auto Placement box, and Part 2's heading count assumes the default |
   | Shape | **Cylinder** | Part 6 generates a cylinder |
   | Double-Sided Card (BETA) | **off** | Part 2 counts headings with it off, then turns it on deliberately |
   | Expert Mode | **closed** | Part 2 opens it as a step |

   To start completely clean, clear site data for `localhost:5001` and reload.

5. **Then reload once more and leave the page alone**, because Part 1 is about
   what the page sounds like before you have touched it.

### What changed since you last listened

The 2026-08-22 run heard the page as it was **before items A–I**. Since then:
the chrome moved into a real banner; a second skip link appeared; six headings
exist where one did; roughly 60% of the spoken description text went away
without a word being deleted from the screen; the Generate button stopped dying
silently; and it now sits inside the form it drives. **This is the first time any
of that has been heard by a person.**

---

## Part 1 — Landmarks (`D`)

Press `D` repeatedly from the top of the page. NVDA moves through landmarks.

**Expected: five, in this order.**

| # | You should hear | Note |
|---|---|---|
| 1 | **banner** | this did not exist before item G |
| 2 | **main** | |
| 3 | **region, 3D STL Preview** | |
| 4 | **region, Braille Cylinder Configuration** | |
| 5 | **form, Custom Braille STL Generator** | |

**Count to write down: how many landmarks `D` reached, and whether "banner" was
among them.**

**Fail if:** there is no banner; or the chrome (font size, theme, GitHub, help)
is announced *inside* `main` rather than inside the banner. That was audit
finding F-E and it is what item G moved.

**Judgement call worth recording, not a pass/fail:** the banner and main are both
unlabelled. That is normal for a page with one of each. Say whether it felt like
enough.

---

## Part 2 — The heading outline (`H`)

This is the highest-value listen in the document. Item C proved the outline
**exists**. It proved nothing about whether it *describes the page*.

### 2a — As loaded

Press `H` repeatedly from the top.

**Expected: six, in this order.**

```
h1  Custom Braille STL Generator
h2  Enter Text for Braille Translation
h2  Double-Sided Card (BETA — for testing)
h2  Row Indicator Style
h2  Card Thickness
h2  Select Plate to Generate
```

### 2b — With Expert Mode open

Open Expert Mode, then press `H` from the top again.

**Expected: eleven** — the six above plus five at level 3: *Shape Selection*,
*Braille Spacing*, *Braille Dot Adjustments*, *Surface Dimensions*,
*Translation Options*.

### 2c — With the double-sided beta on

Turn on **Emboss both sides of the card**, leave Expert Mode open, press `H`.

**Expected: twelve.** The beta forces tactile mode, which reveals a sixth level-3
header, *Tactile Indicator Dimensions*. The first `h2` also relabels itself to
**"Front of Card — Enter Text for Braille Translation"**.

### The rule for all three

**No level may be skipped in any state** — never an h1 followed by an h3.
Verified by probe on 2026-08-23 in all three states: `SKIPPED LEVELS: none`.

**Counts to write down: 6 / 11 / 12, or whatever you actually reach.**

> **If your run differs from these numbers, that is a finding. Report it — do not
> adjust the numbers to match.** They came from
> `build/a11yverify/post15_7c/headings.cjs`, re-run after item G moved the
> markup.

**The question only you can answer:** having pressed `H` six times, did you know
what this page is and where things are? Or is it six labels that happen to be
correctly nested? Write a sentence either way.

---

## Part 3 — The two skip links

There are two now. Both are invisible until focused.

1. Reload. Press `Tab` **once**. You should hear **"Skip to main content, link"**.
2. Press `Enter`. **You should land on `main`** — NVDA should say something, not
   nothing. Then press `Tab` once: expected next stop is **Decrease brightness,
   button**.
3. Reload. Press `Tab` **twice**. Second stop: **"Skip to braille text entry,
   link"**.
4. Press `Enter`. **Expected: "Enter Text for Braille Translation, heading level
   2"**. Then `Tab` once: expected **Auto Placement, radio button, checked**.

**Counts to write down: keystrokes from page load to the braille text entry
using link 2. Expected: three (Tab, Tab, Enter).**

**Fail if:** pressing `Enter` on either link announces nothing and leaves you
where you were. That was the state of link 1 until 2026-08-23 — a fragment link
to a non-focusable element moves the *tab start point* but not focus, so
`activeElement` stayed on `<body>`. Both targets now carry `tabindex="-1"`.

**Also check:** switch to **Manual Placement**, then try link 2 again. It must
still work. It targets the section heading rather than the Auto Placement
textarea precisely because Manual hides that textarea.

---

## Part 4 — Tab from the top, and count

Reload. `Tab` from the top, counting, until you reach **Auto Placement** (the
first control that does the app's job).

**Expected: it is stop 15 — fourteen stops come first.** In order: two skip
links, three font-size buttons, theme, GitHub, help, brightness −/+, contrast
−/+, Edges, "Help me choose what to include".

> **This number did not improve, and the honest expectation is that it will
> sound no better than last time.** Audit finding F-F opened at *14 of 32*, and
> it is still 14 of 32. Item G added a skip link (+1) and removed a duplicate
> GitHub link (−1), and they cancelled exactly. What changed is that a keyboard
> user no longer has to walk the ring — Part 3 is the fix, not this. Reordering
> the columns to shorten the ring was offered and declined, because it would put
> DOM order out of step with visual order for sighted keyboard users (WCAG
> 2.4.3, FD-27b).

**Count to write down: stops before Auto Placement. Then answer the real
question: with the skip links there, does the ring length still matter to you?**
If it does, that reopens F-F and the column reorder goes back on the table.

**One thing to listen for specifically:** you should hear **one** GitHub link on
the way through, not two.

---

## Part 5 — How much is spoken around the text fields

This is where item A, item F and the verbosity rule are heard for the first time.
Before those, one 72-word paragraph was read out three times per pass and
accounted for **31% of all speech on the page**.

1. `Tab` to **Auto Placement Text** and stop. Note everything spoken.
2. `Tab` once to **Translate to Braille**. **Expected: the button's name and role
   only — no paragraph.** Item A unwired the description from both Translate
   buttons.
3. `Tab` once to the **Braille (Unicode)** field. **Expected: roughly 13 words of
   description**, opening *"Accepts braille characters only (U+2800–U+28FF)"* and
   ending with the field's status. Not 72, and not 80.
4. `Tab` once to **Translate to Text**. **Expected again: name and role only.**
5. Now type something into Auto Placement Text, press **Translate to Braille**,
   and `Tab` back onto the Braille (Unicode) field. The description should still
   be short — the status half changes, the sentence does not.

**Counts to write down: words spoken on each of the four stops.** The whole page
budget measured **226 words** on 2026-08-23, down from 574 before item A.

**The question only you can answer:** at 13 words, is the braille field's
description still *useful*, or did shortening it take something you needed? The
other three sentences are still on screen underneath the field, unchanged —
check that you can find them there.

**Two open questions to answer while you are on these four stops.**

1. **The arrow glyphs.** Both Translate buttons end in an arrow — "Translate to
   Braille ↓", "Translate to Text ↑" — and those arrows *are* part of the visible
   text, so they are deliberately **not** hidden from the accessible name
   (hiding them would put the spoken name out of step with the printed label,
   WCAG 2.5.3). **Write down exactly what NVDA says.** If it reads "down arrow"
   and that is noise to you, say so — it becomes a finding worth a decision. If
   it is silent or helpful, that closes the question. The same applies to "Help
   me choose what to include →" and the banner's "Change Theme to →".
2. **The three font-size buttons in the banner.** Tab to **Decrease font size**.
   **Expected: the name once, and nothing after it** — *"Decrease font size,
   button."* If you hear the words a second time as a description, that is a
   regression worth reporting. This was finding **F-P** and it is **fixed**
   (`255f725`, 2026-08-23): the redundant `title` came off all three buttons.
   Worth knowing while you listen — your own 1,799-utterance run showed NVDA
   never spoke the duplicate anyway, because it suppresses a description
   identical to the name; the attribute went because JAWS and VoiceOver are not
   obliged to do the same. The accepted cost is that hovering these three
   buttons with a mouse no longer shows a tooltip.

**Known and deliberate, not a finding:** three descriptions are still over the
25-word ceiling — Tactile seam arrow (43 w), the 3D preview (38 w), Visual
markers (26 w). Brennen decided to leave them (FD-25d). Say if any of them
grated; do not treat them as a fail.

---

## Part 6 — A full generate flow, timed

Do a complete pass, start to finish, using only the keyboard: load the page,
reach the text entry, enter text, translate, generate, download.

**Start a timer.** The reference point is the first NVDA run of this project
(2026-08-22), which took **about 34 minutes** against an estimate of 12 — for a
*different and shorter* walkthrough, so this is not a like-for-like target. What
matters is the shape of where the time goes, not beating a number.

Things to note as you go:

- Where did you stall? Not "what was wrong" — where did you stop and think.
- Did the **Generate STL** button announce as being inside the form? It should
  no longer say **"out of form"** immediately before it. That was audit finding
  F-L, and item G is the first time it has been heard fixed.
- Did anything speak over you while you were typing?
- After pressing Generate, did you know it had worked?
- Anything you had to *see* to do.

**Write down: total minutes, and the single worst moment.**

---

## Results template

Copy this into `00_PROJECT_MEMORY.md` under the Phase log.

```text
NVDA WALKTHROUGH RESULTS — page structure, skip links, closing re-listen
Run by: Brennen
Date:
NVDA version:            Browser + version:
Speech log windowed with nvdaspeech.py?   yes / no

Part | What I heard | Count | Expected | Pass/Fail
-----|--------------|-------|----------|----------
  1  landmarks      |      | 5 incl. banner |
  2a headings load  |      | 6              |
  2b + expert mode  |      | 11             |
  2c + double-sided |      | 12             |
  2  any skipped levels?  |      | none      |
  3  link 1 lands on      |      | main      |
  3  link 2 lands on      |      | the h2    |
  3  keystrokes to task   |      | 3         |
  3  link 2 in Manual mode|      | works     |
  4  stops before task    |      | 14        |
  4  GitHub links heard   |      | 1         |
  5  words on Translate to Braille |  | name+role only |
  5  words on Braille (Unicode)    |  | ~13            |
  5  words on Translate to Text    |  | name+role only |
  5  arrows: what NVDA said for "Translate to Braille down-arrow" |  | (open question) |
  5  font-size button said its name twice? |  | NO - F-P is fixed |
  6  full flow minutes    |      | (no target) |
  6  "out of form" before Generate? |  | NO      |

Did the six headings tell me what this page is?          yes / no — why:

Does the tab-ring length still matter now the skip links exist?   yes / no
  (yes reopens F-F and puts the column reorder back on the table)

Is the braille field's 13-word description still useful?  yes / no — why:

Where did I stall, and what was the worst moment?

Anything NVDA said that I did not expect at all:
```

---

## Related documents

- [NVDA Live Warnings Walkthrough](./NVDA_LIVE_WARNINGS_WALKTHROUGH.md) — the three front-of-card warnings; shared setup and conventions
- [NVDA Double-Sided Walkthrough](./NVDA_DOUBLE_SIDED_WALKTHROUGH.md) — the beta flow's own pass
- [Screen Reader UX Research and Flow Audit](./SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md) — findings F-E, F-F and F-L, and criteria C3/C4/C5
- [ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) — Step 6.8 (description verbosity) and Section 12 (the C1–C10 flow review)
- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md) — §4.1 documents the banner, both skip links and the `tabindex="-1"` targets; §4.13 the sentence-span pattern

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.2 | 2026-08-23 | **The three questions no probe can answer are ANSWERED, and two are wins.** The six headings **do** tell him what the page is (item C vindicated by ear). The braille field's ~13-word description is **still useful** — nothing he needed was lost going from 72 words. And the tab ring's length **no longer matters** now the skip links work, which CLOSES F-F as addressed by other means; the count never moved and C5 still reads FAIL on its own terms. Also closed since v1.1: **F-P fixed** (`255f725`) for JAWS/VoiceOver despite being inert in NVDA, and **`lang="und-Brai"` KEPT** after investigation — 17 announcements per 30-minute session, but the tag is correct, nothing reads it, the noise is a user-switchable NVDA setting, and removing it risks braille-display users. |
| 1.1 | 2026-08-23 | **RUN by Brennen** (NVDA 2026.1.1, Chrome Guest, 1,799 utterances captured). Items A-I confirmed audibly: the banner is heard, the six headings read with no chevron glyph, skip link 2 lands on the `h2`, and the braille field's description is down to ~13 words from a 72-word paragraph. **Three defects found that every automated count had passed** - F-Q the Help dialog leaking focus into Chrome's toolbar (fixed, `e62a2bd`), F-R generating and downloading a plate missing the tail of the text under a cheerful "Both cylinders are ready" (fixed, `b642e7a`), and F-S the standing crowding warning on the shipped default (threshold lowered to a provisional 0.45, `ddd7bd8`). **Part 5's F-P prediction was WRONG**: NVDA suppresses a description identical to the accessible name, so the font buttons never said their name twice - the defect is real in the AX tree but inert in NVDA. Part 4's ring-length question and the three judgement questions are **not yet answered in Brennen's words**; F-F stays open. |
| 1.0 | 2026-08-23 | Created as POST15_7 item G Part 5 — the closing re-listen for the whole A–I programme. Expected counts are measured, not predicted: landmarks **5** and heading outline **6 / 11 / 12 with no skipped levels** from `axprobe.cjs` and `build/a11yverify/post15_7c/headings.cjs` re-run on 2026-08-23 after the banner move; description budget **226 w** from `axprobe.cjs`; tab ring **32** with the first task control at stop **15**. Part 4 states plainly that F-F's number did **not** improve and says what would reopen it. Part 6 is timed but deliberately has no target. |
