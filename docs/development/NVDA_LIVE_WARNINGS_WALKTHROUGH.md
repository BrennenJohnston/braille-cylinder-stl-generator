# NVDA Walkthrough — The Three Front-of-Card Live Warnings

**Purpose:** a screen-reader pass over the three warnings that were wired to the
shared announcement channel on 2026-08-21. Until that day these three were shown
on screen and spoken **nowhere** — a shipped WCAG 2.1 SC 4.1.3 (Status Messages,
Level AA) failure. A blind user who overran a line saw the warning and heard
silence.

The automated checks already prove each region *can* announce, and that the
accessibility tree still holds exactly seven `role="status"` nodes. **Only
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
the third that the load-time restore is showing its notice again. NVDA's own
reading of the page from the top (its automatic say-all on page load) is not an
announcement. Since 2026-10-04 (round R1, phase F3) a load no longer says
"Normal, Normal" either (the 3D preview's brightness and contrast values); hearing
that again is a regression too.

**Control step — keep it, it is the fix's positive proof.** Open **Show Expert
Mode** → **Card Thickness** (the preset radios moved there on 2026-09-24) and click the
card-thickness preset that is **already selected**. Clicking it again re-applies
it, which is a real user action, so the notice must appear on screen AND be
spoken **once**. (Both presets pin the same 4 rows and 13 text cells, so this
cannot move any number quoted later in this walkthrough.) From the keyboard,
`Space` does nothing on a radio that is already selected (Chrome sends no click
for it): press `Escape` to leave focus mode, then `Enter`, and NVDA clicks the
preset (measured 2026-10-04).

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
lands after you pause, not on each letter. If you type slower than about four keys
a second, the pause between two keys is enough: the warning then comes once, as
soon as the text first overflows, while you are still typing, and its numbers are
for the text so far (at "india": 50 cells and 5 rows, measured 2026-10-04). The
same holds in Steps 3, 5 and 10. Once is still the rule.

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

**Step 10.** Set **Capitalized Letters** to **Disabled** again (Step 9 turned it
back on) and type `Hello` in Line 1 (the capital note
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

**Expected (re-measured 2026-10-02):** **two** announcements, both when the value
first becomes too big to fit (at the second 9), and nothing for the third and
fourth digits — not one per digit. First, at once, the seam-channel note "The
seam channel was left out: the seam gap is too narrow for it at this cell count
and diameter." (it joined this part on 2026-09-20 with the slicer seam channel);
then, a quarter of a second later, the warning, which begins "Warning: This
layout does not fit around the cylinder: 99 braille cells …" — 99, because the
announcement lands when the value FIRST fails, and the gate then stays quiet
while the later digits change the number in it to 999 and 9999. The count is the
thing under test: write down whether you heard both, and in which order.

**Step 13.** Clear the dial and type `13` without pausing between the digits: a
pause after the `1` lets the check run on the in-between value 1 and announce that
Line 1 "needs 5 cells but 1 are available" (measured 2026-10-04).

**Expected:** the warning clears (its box sits in the Row Indicator Style submenu
since 2026-09-24, so you see it only while that submenu is open); NVDA says
**nothing new**.

**Fail if:** you hear an announcement per digit — that is the pre-fix behaviour
returning.

---

## Part 6 — The loading notice (added for 2.2.0)

Since round R1 (2026-10-01), pressing **Generate STL** while the page is still
starting no longer fails. The page waits for the braille translator and the 3D
engine, then generates by itself, and while it waits it shows and speaks one
sentence (S-L1 and S-L2, signed by Brennen at Gate B, 2026-10-02):

> The braille translator is still loading. This starts as soon as it is ready.

> The 3D engine is still loading. Generation starts as soon as it is ready.

**Before this step,** set **Placement Mode** back to **Auto Placement** and close
Expert Mode (**Hide Expert Mode**). Both are remembered across a reload, and the
keys below assume them.

**Step 14.** Hard-reload the page (`Ctrl+F5`) and press `Ctrl+Home`. As fast as
you can: `Tab`, `Enter` (with NVDA the first `Tab` is already the second skip link;
see the page-structure walkthrough, Before you start, item 6), then `Tab`, `Tab` to
the **Auto Placement Text** box, type `hi`, then `Tab` seven times to **Generate STL
file from entered text** and press `Space`.

**Expected:** NVDA says, each **once**: "Generating Cylinder A (1 of 2)..." and
the translator sentence (both are written at the same moment, so either may come
first); when the translator is ready, "Braille field updated from translation."
and, if the 3D engine is still starting, the 3D engine sentence (these two also in
either order); then the usual
generation messages, ending with "Both cylinders are ready. Use the Download STL
button to save one file with both cylinders spaced for printing on one plate."
No red error appears, and neither loading sentence is said twice (the progress
line "Generating 3D model (client-side CSG)..." is written once for each cylinder,
and NVDA says it once; measured 2026-10-04).

**On a fast computer the notice may never appear, and that is a pass.** On a
local build the translator was ready about 0.6 seconds after the page loaded and
the 3D engine about 0.9 seconds (measured 2026-10-02), long before anyone can
type and press Generate. To hear it on purpose: open the browser's developer
tools (`F12`), **Network** tab, tick **Disable cache**, choose a slow setting in
the throttling list (Slow 4G, or Slow 3G if your browser lists that), keep the
developer tools open (throttling stops when they close), click once inside the
page, and repeat the step. The page then takes about 20 seconds to appear, and
both sentences are shown (measured with similar throttling). Set throttling back
to **No throttling** afterwards.

**Fail if:** a red error says the translation failed or that the 3D engine
"failed to load"; or you hear either loading sentence more than once.

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
 14  |              |             |                   |

Overall verdict:            /13 listening steps passed
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

- [NVDA Double-Sided Walkthrough](./NVDA_DOUBLE_SIDED_WALKTHROUGH.md) — the double-sided flow's own pass; setup and conventions are shared
- [NVDA Page Structure Walkthrough](./NVDA_PAGE_STRUCTURE_WALKTHROUGH.md) — headings, landmarks, the two skip links and a timed keyboard generate flow; the closing pass for the POST15_7 programme
- [ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) — section 6.5 is the requirement this satisfies
- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md) — §4.10 is the rule these three now follow
- [Interpoint Double-Sided Specifications](../specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md) — §7.6 documents `#a11y-status` and `announceStatus()`

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.9 | 2026-10-04 | **Run with NVDA (round R1, walk F: the session drove NVDA 2026.2 and Chrome 150 at Brennen's request, reading NVDA's own speech log), then corrected (phase F6).** 12 of 13 listening steps passed their counts; every warning was said once per episode. Changed: Step 0 adds that NVDA's own say-all is not an announcement and that the load no longer says "Normal, Normal" (fixed that day, F3); the control step gains the keyboard route (`Escape`, then `Enter`; `Space` does nothing on a selected radio); Step 1 notes that a slow typist hears the warning at the first overflow, with that moment's numbers (Steps 3, 5, 10 too); Step 10 sets capitals to Disabled again; Step 13 is typed without a pause (a pause announced the in-between value 1); Step 14 presses `Ctrl+Home` and `Tab`, `Enter` for the second skip link, and its progress line is said once. Step 12's two announcements were judged acceptable by Brennen (R1-Q-29). Results: `WALK_F_RESULTS_2026-10-04.md` in the round folder. |
| 1.8 | 2026-10-02 | **Round R1, phase F2 (NOT yet run with NVDA).** The Auto Placement warning is no longer repeated after a switch to Manual Placement (Brennen's decision R1-Q-27; found in F1 and listed in v1.7); no step changes, since Step 4 never expected an announcement. The introduction counts seven `role="status"` nodes (seven since 2026-08-31), and Step 14 says the two sentences are shown, which is what was measured. |
| 1.7 | 2026-10-02 | **Re-measured for 2.2.0 in Chromium, and the loading notice added (round R1, phase F1; NOT yet run with NVDA).** Every step replayed at `553f830` by keyboard, with every live-region change recorded: each quoted sentence is the page's own text character for character, the load is still silent, and each warning is still written once per episode. Changed: Step 12 now hears two announcements at the second 9, the seam-channel note (since 2026-09-20) and then the warning; Step 13 says where the warning box sits since 2026-09-24. New Part 6 (Step 14): the loading notice, S-L1 and S-L2 (signed 2026-10-02), with the throttling recipe; the results template gains row 14 (13 listening steps). Found and left for Gate F: clicking Manual Placement straight from the Auto Placement Text box (or pressing Shift+Tab and Down together) re-announces the Part 1 warning about 270 ms later, from a check still pending; the introduction's six status nodes are seven since 2026-08-31. |
| 1.6 | 2026-09-30 | **Documentation review:** the control step opens Expert Mode → Card Thickness first, where the preset radios live since 2026-09-24 (D-5); the related-documents line says "double-sided flow". |
| 1.5 | 2026-08-22 | **Part 3 gains the F-J change** (item F, D6): the **Disabled** capitals radio no longer carries its own `aria-describedby` description, so selecting it now speaks one utterance fewer. Its sr-only text duplicated both the note this walkthrough already quotes AND the visible `.grade-note` beneath the radios, which is unchanged and still on screen. **No quoted sentence in this document changed** - the caps note's wording and its once-per-episode gate are untouched - so every existing step, count and fail condition still stands; Step 9 simply gained a new fail condition for the duplicate returning. Nothing else in the app was changed by that item that this walkthrough covers. |
| 1.0 | 2026-08-21 | Created with the accessibility hygiene bundle, when `#auto-overflow-warning`, `#cylinder-overflow-warning` and `#caps-warning` were wired to `#a11y-status`. Expected wording is the boxes' own on-screen text — no new strings were authored. Counts come from measured runs: 1 announcement per episode for all three, against 11 per 11 keystrokes for the capitalization note before its gate was added. |
| 1.4 | 2026-08-22 | **The FD-20(c) wording landed** (same closeout, approved by Brennen): the seam-fit warning now counts text cells only — Part 5's expected opening updated to "This layout does not fit around the cylinder: …". No counts, gates, or steps changed. |
| 1.3 | 2026-08-22 | **Both fixes from the first run landed the same day** (approved by Brennen, FD-20 in `00_PROJECT_MEMORY.md`). (1) The load-time preset restore no longer shows or announces its confirmation — Part 0 rewritten from an open question into a regression check, keeping the deliberate-click control as the fix's positive proof. (2) `checkPhysicalFit()` gained the 250 ms debounce and hidden→shown gate its three siblings had — new **Part 5** (steps 12–13) listens for it, because the dial race (POST15_4) means no automated test can. Both fixes verified by probe on Chromium and Firefox: typing 9-9-9-9 into the dial now announces once (was three); the load-time `#a11y-status` write is gone. Run estimate 12 → 14 minutes; results template gained rows 12–13. |
| 1.2 | 2026-08-22 | **First real run** (Brennen; NVDA 2026.1.1, Chrome 150.0.7871.125, ~34 min against the ~12 estimated). Counts were read from NVDA's own Input/Output speech log, archived beside `00_PROJECT_MEMORY.md` as `POST15_6_NVDA_SPEECH_2026-08-22.txt` — a far better record than transcription by ear, and recommended for every future run (NVDA menu → Tools → Log Viewer, or `%TEMP%\nvda.log`, at log level Input/Output). One capture caveat learned: NVDA also reads whatever terminal or document displays this walkthrough, and that text QUOTES the expected sentences — window the log to the browser segment before counting. Results: the three warnings PASSED the once-per-episode rule (caps note: five announcements in ten minutes, every one a genuine hide→show boundary, no per-keystroke cluster — the 11-in-11 regression did not return); steps 3 and 10–11 were not reached. Part 0 RESOLVED: the theme and font-size announcers are inaudible in practice; the preset notice IS spoken on a focused load or reload — fix pending decision. The run also found this walkthrough's defect class alive in a warning it never covered: `checkPhysicalFit()` announced four times in 5.3 s while a dial was being typed into, ungated (finding F1), and confirmed the cells-vs-columns unit mixing in warning text (finding F3). Full results and findings: `00_PROJECT_MEMORY.md`, Phase log 2026-08-22. |
| 1.1 | 2026-08-22 | Re-read against the code before the listening run (POST15_6 preparation), and all eleven steps replayed in Chromium and Firefox. **One expected string was wrong and is corrected**: Step 1's second sentence is "Your text needs **6 rows** but the plate has 4", not "more than 4 rows" — `git log -S` shows the code producing it last changed in `7b10145`, *before* this document was created, so the v1.0 wording was predicted rather than measured, the same failure the double-sided walkthrough's v1.2 row records. All other quoted wording and all four counts re-confirmed unchanged (1 per episode; 0 on clear; caps note 1 across 11 keystrokes). Step 4 renamed the submenu to its real on-screen title, **Surface Dimensions**. Added a "known state" table to *Before you start* — Placement Mode, Shape and Capitalized Letters are all remembered in `localStorage`, so a fresh load is not necessarily a fresh page. Added **Part 0**, an open question about three announcements written into live regions during load itself, one of which (`Card thickness preset "0.4mm" applied.`) lands in the permanent `#a11y-status` channel and was not previously known. Nothing in the app was changed. |
