# NVDA Walkthrough — The Three Front-of-Card Live Warnings

**Purpose:** a screen-reader pass over the three warnings that were wired to the
shared announcement channel on 2026-08-21. Until that day these three were shown
on screen and spoken **nowhere** — a shipped WCAG 2.1 SC 4.1.3 (Status Messages,
Level AA) failure. A blind user who overran a line saw the warning and heard
silence.

The automated checks already prove each region *can* announce, and that the
accessibility tree still holds exactly six `role="status"` nodes. **Only
listening proves it announces usefully**, which is what this walkthrough is for.

**Who runs this:** Brennen, or anyone with NVDA installed.
**How long:** about 10 minutes.
**Created:** 2026-08-21 (post-initiative accessibility hygiene bundle).

This is a sibling of the
[NVDA Double-Sided Walkthrough](./NVDA_DOUBLE_SIDED_WALKTHROUGH.md); the setup
notes, the key list, and the "what expected announcement means" rules there all
apply here unchanged, including that **role/name order varies and is not a
fail**.

---

## Before you start

1. Start the app:

   ```powershell
   python backend.py
   ```

   Then open <http://localhost:5001/> in Chrome or Firefox.
2. Start NVDA, and open the speech viewer so you can read back what was said:
   NVDA menu (`NVDA key` + `N`) → **Tools** → **Speech Viewer**.
3. **Leave the speech viewer open for the whole run.** The thing being tested is
   *how many times* something is said, so a scrollback you can count matters more
   than usual here.

### The one rule that matters most

Each of these three warnings should be spoken **once, when it appears** — not
once per keystroke. If you hear the same warning repeating while you are still
typing, that is a **fail**, even though the words are correct. Talking over
someone who is still typing is the defect these gates exist to prevent.

---

## Part 1 — Auto Placement overflow (the one users hit most)

This is the front-of-card overflow warning. Auto Placement is the mode the page
opens in, so no setup is needed.

**Step 1.** Load the page fresh. Tab to the **Auto Placement Text** box (or click
into it), and type this, slowly enough that you would notice chatter:

```
alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima
```

**Expected:** shortly after you stop typing, NVDA says **once**:

> Warning: Line 1 ("alpha bravo charlie delta echo foxtrot golf hotel india
> juliet kilo lima") needs 68 cells but 13 are available. Your text needs more
> than 4 rows but the plate has 4.

**How many times:** exactly **one**. The check is debounced by 250 ms, so it
lands after you pause, not on each letter.

**Fail if:** you hear nothing at all; or you hear it repeatedly while typing.

**Step 2.** Now clear the box (`Ctrl+A`, then `Delete`).

**Expected:** the warning disappears from the screen, and NVDA says **nothing
new**. Silence is the correct result here — the channel is released quietly.

**Fail if:** NVDA reads the warning again as it clears.

**Step 3.** Type the same long text a second time.

**Expected:** the warning is announced **once** again — it re-arms each time the
condition genuinely returns.

---

## Part 2 — Manual-mode cylinder overflow

**Step 4.** Switch **Placement** to **Manual**. Then open **Expert Mode** and its
**Dimensions** submenu — the warning box lives inside that panel, so it can only
be seen (and only matters) when that panel is open.

**Step 5.** Put the cursor in **Line 1** and type sixteen letters with no spaces:

```
qqqqqqqqqqqqqqqq
```

**Expected:** once you pause, NVDA says **once**:

> Warning: Line 1 ("qqqqqqqqqqqqqqqq") needs 16 cells but 13 are available.
> Shorten the text or raise the number of braille cells in Expert Mode.

**How many times:** exactly **one**.

**Step 6.** Delete back down to two letters (`hi`).

**Expected:** the warning goes off screen; NVDA says **nothing new**.

---

## Part 3 — The capitalization note

This one is different in kind: its text never changes, and unlike the two
overflow warnings it is **not** debounced — it re-runs on every single keystroke.
That is exactly why it was the noisiest of the three before the fix (measured: 11
announcements over 11 keystrokes).

**Step 7.** Still in Manual mode, open **Expert Mode → Translation Options** and
set **Capitalized Letters** to **Disabled**.

**Step 8.** In **Line 1**, clear the box and type, letter by letter:

```
Hello WORLD
```

**Expected:** NVDA says, **once**, as soon as the first capital lands:

> Note: Capital letters in your text will not be translated because "Capitalized
> Letters" is disabled. Enable it above if you need capitals in braille.

**How many times:** exactly **one**, across all eleven keystrokes.

**Fail if:** you hear that sentence more than once — that is the pre-fix
behaviour returning, and it is the single most likely regression on this page.

**Step 9.** Set **Capitalized Letters** back to **Enabled**.

**Expected:** the note disappears; NVDA says **nothing new** about capitals (it
will of course announce the radio button you just changed).

---

## Part 4 — One warning does not swallow another

**Step 10.** Leave capitals disabled and type `Hello` in Line 1 (the capital note
appears and is announced once). Now extend Line 1 past thirteen cells, e.g.:

```
Hello qqqqqqqqqqqqqq
```

**Expected:** the overflow warning is announced once. **Both boxes stay visible
on screen.** The announcement channel is scoped by owner, so the overflow
warning taking the channel does not delete the capital note from the page.

**Step 11.** Shorten Line 1 back to `Hello`.

**Expected:** the overflow warning goes; the capital note stays on screen. NVDA
says nothing new.

**Fail if:** clearing one warning also clears the other from the screen.

---

## Results template

Copy this into `00_PROJECT_MEMORY.md` under the Phase log, fill in what you
actually heard, and mark each row Pass or Fail. Where a step is about a **count**,
write the number you heard, not just "yes".

```text
NVDA WALKTHROUGH RESULTS — three front-of-card live warnings
Run by: Brennen
Date:
NVDA version:            Browser + version:

Step | What I heard | Times heard | Matched expected? | Pass/Fail
-----|--------------|-------------|-------------------|----------
  1  |              |             |                   |
  2  |              |             |                   |
  3  |              |             |                   |
  4  |     (setup)  |     n/a     |        n/a        |
  5  |              |             |                   |
  6  |              |             |                   |
  7  |     (setup)  |     n/a     |        n/a        |
  8  |              |             |                   |
  9  |              |             |                   |
 10  |              |             |                   |
 11  |              |             |                   |

Overall verdict:            /9 listening steps passed
Did anything talk over you while you were still typing?

Anything NVDA said that I did not expect at all:
```

---

## Related documents

- [NVDA Double-Sided Walkthrough](./NVDA_DOUBLE_SIDED_WALKTHROUGH.md) — the beta flow's own pass; setup and conventions are shared
- [ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) — section 6.5 is the requirement this satisfies
- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md) — §4.10 is the rule these three now follow
- [Interpoint Double-Sided Specifications](../specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md) — §7.6 documents `#a11y-status` and `announceStatus()`

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-21 | Created with the accessibility hygiene bundle, when `#auto-overflow-warning`, `#cylinder-overflow-warning` and `#caps-warning` were wired to `#a11y-status`. Expected wording is the boxes' own on-screen text — no new strings were authored. Counts come from measured runs: 1 announcement per episode for all three, against 11 per 11 keystrokes for the capitalization note before its gate was added. |
