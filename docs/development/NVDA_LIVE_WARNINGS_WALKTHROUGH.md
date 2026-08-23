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
**How long:** about 14 minutes.
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
4. **Put the page in a known state, then reload before Part 0.** The app
   remembers your last Placement Mode, Shape, and Capitalized Letters setting in
   this browser, so "load the page fresh" does not by itself mean "opens the way
   a new user sees it". Check these three by eye and set them if they differ:

   | Control | Must be | Why it matters |
   |---|---|---|
   | Placement Mode | **Auto Placement** | Part 1 types into the Auto Placement Text box, which only exists in this mode |
   | Shape | **Cylinder** | the Part 2 warning returns early and never appears on a card |
   | Capitalized Letters (Expert Mode → Translation Options) | **Enabled** | Part 3 starts by turning it *off*; if it is already off, Step 8 has nothing to reveal |

   If you would rather start completely clean, clear site data for
   `localhost:5001` in the browser's settings and reload — that resets all three
   along with the card-thickness preset.

   **Then reload the page once more and leave it alone**, because Part 0 is about
   what a load sounds like when you have touched nothing.

### The one rule that matters most

Each of these three warnings should be spoken **once, when it appears** — not
once per keystroke. If you hear the same warning repeating while you are still
typing, that is a **fail**, even though the words are correct. Talking over
someone who is still typing is the defect these gates exist to prevent.

---

## Part 0 — What you hear before you touch anything

**Expected now: silence.** This part was an open question in v1.1, and the first
run (2026-08-22) answered it — so it is now a regression check.

What that run measured, and what changed because of it:

| Announcement written during load | First run | Now |
|---|---|---|
| "Theme changed to *your theme*" | written at init, **never spoken** | unchanged — a throwaway `role="status"` div, measured inaudible |
| "Font size changed to 100%" | written at init, **never spoken** | unchanged — same throwaway pattern, measured inaudible |
| "Card thickness preset "0.4mm" applied. All parameters updated." | **spoken once on every focused load or reload**, before the user touched anything | **fixed 2026-08-22**: the silent load-time restore no longer shows or announces the notice; clicking a preset still does both |

**Step 0.** With NVDA running and the speech viewer open, load
<http://localhost:5001/> and **do nothing at all** for about ten seconds.

**Expected:** none of the three sentences above. Hearing any of them is a
regression — the first two would mean the throwaway announcers became audible,
the third that the load-time restore is showing its notice again.

**Control step — keep it, it is the fix's positive proof.** Click the
card-thickness preset that is **already selected**. Clicking it again re-applies
it, which is a real user action, so the notice must appear on screen AND be
spoken **once**. (Both presets pin the same 4 rows and 13 text cells, so this
cannot move any number quoted later in this walkthrough.)

**Fail if:** Step 0 speaks the preset sentence (the load leak returned), or the
control click is silent (the deliberate path broke — the fix was meant to skip
the load restore only, never the click).

---

## Part 1 — Auto Placement overflow (the one users hit most)

This is the front-of-card overflow warning. Auto Placement is the mode a *new*
user's page opens in, so with the known-state check above done there is no
further setup.

**Step 1.** Carry straight on from Part 0 — same load, nothing reloaded. Tab to
the **Auto Placement Text** box (or click into it), and type this, slowly enough
that you would notice chatter:

```
alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima
```

**Expected:** shortly after you stop typing, NVDA says **once**:

> Warning: Line 1 ("alpha bravo charlie delta echo foxtrot golf hotel india
> juliet kilo lima") needs 68 cells but 13 are available. Your text needs 6 rows
> but the plate has 4.

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

**Step 4.** Switch **Placement Mode** to **Manual Placement**. Then press **Show
Expert Mode** and open its **Surface Dimensions** submenu — the warning box lives
inside that panel, so it can only be seen (and only matters) when that panel is
open.

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

**Changed 2026-08-22 (item F, finding F-J) - one utterance fewer here.** The
**Disabled** radio no longer carries an `aria-describedby` description of its own.
Before this change, selecting it produced two utterances 20 ms apart that said the
same thing: the note quoted above, then "Convert text to lowercase before
translation to save space on braille cells: one cell per capital letter, two per
fully capitalized word". You should now hear the note, plus the radio's own name
and state, and nothing else. **The note's wording and its once-per-episode gate are
unchanged** - only the duplicate was removed, and the same sentence is still on
screen as visible text beneath the radios.

**Fail if:** you hear the "Convert text to lowercase..." sentence at all.

---

## Part 4 — One warning does not swallow another

**Step 10.** Leave capitals disabled and type `Hello` in Line 1 (the capital note
appears and is announced once). Now extend Line 1 past thirteen cells, e.g.:

```
Hello qqqqqqqqqqqqqq
```

**Expected:** the overflow warning is announced **once**:

> Warning: Line 1 ("Hello qqqqqqqqqqqqqq") needs 20 cells but 13 are available.
> Shorten the text or raise the number of braille cells in Expert Mode.

**Both boxes stay visible on screen.** The announcement channel is scoped by
owner, so the overflow warning taking the channel does not delete the capital
note from the page.

**Step 11.** Shorten Line 1 back to `Hello`.

**Expected:** the overflow warning goes; the capital note stays on screen. NVDA
says nothing new.

**Fail if:** clearing one warning also clears the other from the screen.

---

## Part 5 — The seam-fit warning and the cells dial (added v1.3)

The first run found this walkthrough's defect class alive in a warning it never
covered: the physical seam-fit warning announced **four times in 5.3 seconds**
while a value was being typed into the cells dial, reading out garbage
intermediate arithmetic ("needs 1415 columns … leaves -9094.2 mm"). It has since
been debounced and gated like the three boxes above. This part keeps it that
way — and it has to be listened for, because every input feeding this warning is
preset-owned, so no automated test can type into the dial reliably.

**Step 12.** Open **Expert Mode → Braille Spacing** and click into **Number of
Available Braille Cells**. Clear it, then type `9999` one digit at a time,
pausing about half a second between digits.

**Expected:** **one** warning announcement, shortly after the value first becomes
too big to fit (at the second 9) — not one per digit. It begins "Warning: This
layout does not fit around the cylinder: 99 braille cells …" — 99, because the
announcement lands when the value FIRST fails, and the gate then stays quiet
while the later digits change the on-screen number to 999 and 9999. The count is
the thing under test.

**Step 13.** Clear the dial and type `13`.

**Expected:** the warning leaves the screen; NVDA says **nothing new**.

**Fail if:** you hear an announcement per digit — that is the pre-fix behaviour
returning.

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
  0  |              |             |                   |
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
 12  |              |             |                   |
 13  |              |             |                   |

Overall verdict:            /12 listening steps passed
Did anything talk over you while you were still typing?

Step 0 - on a fresh load, before touching anything, did I hear:
  "Theme changed to ..."                              yes / no
  "Font size changed to 100%"                         yes / no
  "Card thickness preset "0.4mm" applied. ..."        yes / no
  Everything else NVDA said on load, in order:

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
| 1.5 | 2026-08-22 | **Part 3 gains the F-J change** (item F, D6): the **Disabled** capitals radio no longer carries its own `aria-describedby` description, so selecting it now speaks one utterance fewer. Its sr-only text duplicated both the note this walkthrough already quotes AND the visible `.grade-note` beneath the radios, which is unchanged and still on screen. **No quoted sentence in this document changed** - the caps note's wording and its once-per-episode gate are untouched - so every existing step, count and fail condition still stands; Step 9 simply gained a new fail condition for the duplicate returning. Nothing else in the app was changed by that item that this walkthrough covers. |
| 1.0 | 2026-08-21 | Created with the accessibility hygiene bundle, when `#auto-overflow-warning`, `#cylinder-overflow-warning` and `#caps-warning` were wired to `#a11y-status`. Expected wording is the boxes' own on-screen text — no new strings were authored. Counts come from measured runs: 1 announcement per episode for all three, against 11 per 11 keystrokes for the capitalization note before its gate was added. |
| 1.4 | 2026-08-22 | **The FD-20(c) wording landed** (same closeout, approved by Brennen): the seam-fit warning now counts text cells only — Part 5's expected opening updated to "This layout does not fit around the cylinder: …". No counts, gates, or steps changed. |
| 1.3 | 2026-08-22 | **Both fixes from the first run landed the same day** (approved by Brennen, FD-20 in `00_PROJECT_MEMORY.md`). (1) The load-time preset restore no longer shows or announces its confirmation — Part 0 rewritten from an open question into a regression check, keeping the deliberate-click control as the fix's positive proof. (2) `checkPhysicalFit()` gained the 250 ms debounce and hidden→shown gate its three siblings had — new **Part 5** (steps 12–13) listens for it, because the dial race (POST15_4) means no automated test can. Both fixes verified by probe on Chromium and Firefox: typing 9-9-9-9 into the dial now announces once (was three); the load-time `#a11y-status` write is gone. Run estimate 12 → 14 minutes; results template gained rows 12–13. |
| 1.2 | 2026-08-22 | **First real run** (Brennen; NVDA 2026.1.1, Chrome 150.0.7871.125, ~34 min against the ~12 estimated). Counts were read from NVDA's own Input/Output speech log, archived beside `00_PROJECT_MEMORY.md` as `POST15_6_NVDA_SPEECH_2026-08-22.txt` — a far better record than transcription by ear, and recommended for every future run (NVDA menu → Tools → Log Viewer, or `%TEMP%\nvda.log`, at log level Input/Output). One capture caveat learned: NVDA also reads whatever terminal or document displays this walkthrough, and that text QUOTES the expected sentences — window the log to the browser segment before counting. Results: the three warnings PASSED the once-per-episode rule (caps note: five announcements in ten minutes, every one a genuine hide→show boundary, no per-keystroke cluster — the 11-in-11 regression did not return); steps 3 and 10–11 were not reached. Part 0 RESOLVED: the theme and font-size announcers are inaudible in practice; the preset notice IS spoken on a focused load or reload — fix pending decision. The run also found this walkthrough's defect class alive in a warning it never covered: `checkPhysicalFit()` announced four times in 5.3 s while a dial was being typed into, ungated (finding F1), and confirmed the cells-vs-columns unit mixing in warning text (finding F3). Full results and findings: `00_PROJECT_MEMORY.md`, Phase log 2026-08-22. |
| 1.1 | 2026-08-22 | Re-read against the code before the listening run (POST15_6 preparation), and all eleven steps replayed in Chromium and Firefox. **One expected string was wrong and is corrected**: Step 1's second sentence is "Your text needs **6 rows** but the plate has 4", not "more than 4 rows" — `git log -S` shows the code producing it last changed in `7b10145`, *before* this document was created, so the v1.0 wording was predicted rather than measured, the same failure the double-sided walkthrough's v1.2 row records. All other quoted wording and all four counts re-confirmed unchanged (1 per episode; 0 on clear; caps note 1 across 11 keystrokes). Step 4 renamed the submenu to its real on-screen title, **Surface Dimensions**. Added a "known state" table to *Before you start* — Placement Mode, Shape and Capitalized Letters are all remembered in `localStorage`, so a fresh load is not necessarily a fresh page. Added **Part 0**, an open question about three announcements written into live regions during load itself, one of which (`Card thickness preset "0.4mm" applied.`) lands in the permanent `#a11y-status` channel and was not previously known. Nothing in the app was changed. |
