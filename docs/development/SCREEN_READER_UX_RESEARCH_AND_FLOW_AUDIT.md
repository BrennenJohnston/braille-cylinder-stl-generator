# Screen-Reader UX Research and Flow Audit

**Status:** research and audit only — nothing in this document has been implemented.
It ends with a prioritised list and a set of decisions for Brennen. Fixes get their
own work items once he has chosen among the options.

**Why this exists.** The first real NVDA run of the app (2026-08-22, recorded in
`NVDA_LIVE_WARNINGS_WALKTHROUGH.md` v1.2 and `00_PROJECT_MEMORY.md` FD-20) *passed*
every count it was checking, and still took about 34 minutes instead of the estimated
12, with a lot of wandering. Passing the checks and being usable turned out to be two
different things. This document asks the bigger question that run raised: how does the
app's organisation and logic flow compare with screen-reader gold-standard practice?

Part 1 is research — what the standards and the evidence actually say, and a
verbosity rule we can defend. Part 2 measures this app against it.

---

## How the numbers here were measured

Three instruments, so that nothing below rests on reading markup and guessing:

1. **NVDA's own speech log** from the 2026-08-22 run
   (`POST15_6_NVDA_SPEECH_2026-08-22.txt`, beside `00_PROJECT_MEMORY.md`). This
   records what was actually *spoken*. It was windowed to the browser-focused
   segment, 13:05:19–13:39:39 — **1,010 utterances, 15,881 words**. Two
   window-switch bleed utterances were excluded. Everything outside that window is
   NVDA reading the terminal, which quoted the very sentences being counted.
2. **A live accessibility-tree probe** — `build/a11yverify/post15_7/axprobe.cjs` and
   `axprobe2.cjs`. These read Chrome's computed accessibility tree (names and
   descriptions as the screen reader receives them) and walk the real tab ring in
   the running app. Static HTML parsing cannot do this: descriptions are computed,
   and several containers here are shown or hidden by script after load.
3. **The source**, for cause — `public/index.html`.

Where a number below is a count, it came from instrument 1 or 2, not from an estimate.

---

# PART 1 — RESEARCH

## 1.1 How screen-reader users actually navigate

The single most useful fact for this app, from WebAIM's Screen Reader User Survey #10
(the field's standard reference): asked how they find information on a **lengthy web
page**, respondents said —

| Method | Share |
|---|---|
| **Navigate through the headings** | **71.6%** |
| Use the Find feature | 13.6% |
| Read through the page | 6.4% |
| Navigate through the links | 4.8% |
| Navigate through the landmarks/regions | 3.7% |

88.8% rate heading levels as very or somewhat useful. Landmarks, by contrast, are the
*primary* method for only 3.7% — though about a third use them regularly when present.

**The consequence for us is blunt.** Headings are how roughly seven in ten users find
anything on a long page. This app's page is long, and — measured, not assumed — it has
**one heading**. That is the largest single finding in Part 2.

## 1.2 NVDA's interaction model, in plain terms

- **Browse mode vs focus mode.** In browse mode NVDA reads a *virtual copy* of the
  page and single letters jump around it. The moment focus enters a text field it
  switches to focus mode, where keys go to the app. Users cross this boundary
  constantly while filling a form.
- **Single-letter navigation:** `h` next heading, `1`–`6` heading by level, `f` next
  form field, `b` next button, `d` next landmark.
- **The Elements List** (`NVDA+F7`) shows the page's links, headings and other
  elements as a jump-to list.
- **Descriptions are spoken.** NVDA reports object descriptions by default, and the
  2026-08-22 log confirms it: every `aria-describedby` paragraph on this page was
  read out in full, every time its control was reached.

The practical reading: **anything you put in `aria-describedby` is a toll the user
pays on every single pass**, and heading structure is the map they use to avoid
paying it.

## 1.3 What the standards require

**WAI-ARIA Authoring Practices — Accordion.** "Each accordion header `button` is
wrapped in an element with role `heading` that has a value set for `aria-level` that
is appropriate for the information architecture of the page." Native `<h2>`–`<h4>`
are the expected way to do it, with the button as the heading's sole child. The
pattern also warns against `role="region"` on six or more panels, to avoid landmark
proliferation.

**WAI-ARIA APG — Providing Accessible Names and Descriptions.** Descriptions "are
usually significantly longer than names" and are "presented last, sometimes after a
slight delay." The governing principle: descriptions **supplement, not duplicate**,
what the name already conveys. And a telling note — "to reduce verbosity, some screen
readers do not announce descriptions by default but instead inform users of their
presence." NVDA is *not* one of those; here, everything is spoken.

**GOV.UK Design System** is the most directly quotable, because it states a hard limit
rather than a principle:

> "Keep hint text to a single short sentence, without any full stops."
>
> "Do not use hint text to explain anything that's longer than a short, simple
> sentence. **Screen readers read out the entire text when users interact with the
> form element.**"

GOV.UK's accordion likewise uses a real `<h2>` per section, and warns that "users of
screen readers might find it difficult to navigate the accordion if the button text is
too long."

**WAI-ARIA APG — Radio Group.** The group needs a visible label referenced by
`aria-labelledby`, or an `aria-label`. Keyboard behaviour is the important part and it
is the *native* behaviour this app already gets from `<fieldset>` + `<input
type="radio">`: **Tab enters the group once**, landing on the checked button, and
arrow keys move within it. That matters for the verbosity arithmetic below — a Tab
pass hears only the *checked* radio's description, not all of them.

**WAI-ARIA APG — Spin Button.** Up/Down arrows change the value, Home/End go to the
minimum and maximum, and the control must expose `aria-valuenow`, `aria-valuemin` and
`aria-valuemax` (plus `aria-invalid` when out of range). A native `input
type="number"` satisfies this **only if `min` and `max` are actually present** — the
browser maps those attributes to `aria-valuemin`/`aria-valuemax`, and with no
attributes there is nothing to map.

**Live regions.** The APG's live-region guidance and WCAG SC 4.1.3 (Status Messages)
require that a status change reach assistive technology without moving focus. This
app's `#a11y-status` channel does exactly that and was verified correct in POST15_2
and POST15_6 — it is listed in §2.3 as confirmed-good. What no standard settles is
what should happen when *two* live messages fire on the same keystroke; that is
finding F-I.

## 1.4 What good applications do about verbosity

Two published comparison points, both application-scale rather than component-scale:

- **Slack** publishes explicit screen-reader support (NVDA, JAWS, VoiceOver), and —
  the relevant part — ships **user-controllable verbosity**: customisable message
  readouts, a "Simplified Layout Mode" aimed at screen-reader and eye-tracking users,
  and screen-reader-specific shortcuts. The lesson is not "add a settings panel"; it
  is that at that tier, *how much gets spoken is treated as a user preference, not a
  fixed authorial choice*.
- **GitHub** treats accessibility as governance: a named "GitHub Fundamental",
  published Accessibility Conformance Reports, internal scorecards, accessibility
  champions embedded in teams. The lesson for a one-person project is the cheap half —
  **a written standard plus a repeatable measurement**, which is what §1.5 and §1.6
  below are meant to be.

Neither ships 96-word descriptions on a checkbox.

## 1.5 The verbosity rule (proposed)

Derived from GOV.UK's hard limit, the APG's supplement-don't-duplicate principle, and
what the log shows NVDA actually does with this page. **The 86-word BANA paragraph
spoken 18 times is the test case this rule has to answer, and it fails it at the first
line.**

> ### The rule
>
> **1. `aria-describedby` gets one short sentence — a target of 15 words, a hard
> ceiling of 25.** It is spoken in full on every visit, so it must carry only what the
> user needs *at that control, at that moment*, and that the name does not already say.
>
> **2. Anything longer stays on the page as ordinary visible text, adjacent to the
> control, and is NOT wired to `aria-describedby`.** It is still fully available: a
> browse-mode user reads it with arrow keys, in their own time, by choice. Making it a
> description does not add information — it removes the user's *choice* about when to
> hear it.
>
> **3. Reference material — standards, guidelines, worked examples — belongs in the
> help guide**, which this app already has and which is already well structured
> (40+ headings). Not on a control.
>
> **4. A description must never restate the label.** If the name says it, delete it.
>
> **5. One description, one host.** If the same text is wired to several controls, the
> user pays for it several times per pass. Attach it to the one control it is really
> about.
>
> **6. Screen-reader-only text (`sr-only`) gets the same scrutiny as visible text —
> more, because no sighted review will ever catch it.**

**Why a word count rather than "use judgement":** because judgement is what produced
the current page, and every paragraph on it looked reasonable in isolation. A number
is checkable, and can be re-measured by the probe in one command.

**What the rule is not.** It is not an instruction to delete explanations. Every
paragraph flagged in Part 2 is genuinely useful text, some of it hard-won and
signed-off. The rule only governs *how it is delivered* — visible and browseable
versus forced into speech on every pass.

## 1.6 Flow criteria — the checklist this app should meet

Ten criteria, each one checkable. Part 2 walks the app against them.

| # | Criterion | Source |
|---|---|---|
| C1 | Every major section of the page is reachable by a real heading, in a sensible level order | WebAIM 71.6%; WCAG 2.4.10 |
| C2 | Accordion/disclosure headers are wrapped in headings, not bare buttons | APG Accordion; GOV.UK |
| C3 | Landmarks divide the page into meaningful, labelled areas — and page chrome is not inside `main` | APG; HTML spec |
| C4 | The skip link actually skips a meaningful number of controls | WCAG 2.4.1 |
| C5 | The task's own controls come before, or close after, the page's decorative and utility controls | Flow |
| C6 | Every description obeys the §1.5 verbosity rule | GOV.UK; APG |
| C7 | No description restates its label; no `sr-only` text duplicates visible text | APG |
| C8 | Every element in the tab ring can be operated from the keyboard, and every value control announces its allowed range | WCAG 2.1.1; APG Spin Button; project rules 3 and 10 |
| C9 | One user action produces one coherent announcement, in a useful order | WCAG 4.1.3 |
| C10 | Decorative glyphs and icons never reach the accessible name | Project rule 7 |

---

# PART 2 — AUDIT

Measured against the §1.6 checklist. **No fixes have been applied.** "Direction" is a
proposal, not an implementation — and every item that changes user-facing wording or
structure is listed again in §2.4 as a decision for Brennen (accessibility rules 11
and 12).

## 2.1 Headline numbers

| Measurement | Value |
|---|---|
| Words spoken in the 34-minute session (browser-focused window) | **15,881** |
| Visible headings in the live page | **1** (the `<h1>`) |
| Tab stops on load | **33** |
| Tab stops before the first control that does the app's actual job | **15** |
| Focusable controls the skip link skips | **0** |
| Description words in one full read of the default page | **574** |
| Share of all speech taken by just three descriptions | **54%** |

**The three descriptions, measured over the session:**

| Description | Length | Times spoken | Words | Share of all speech |
|---|---|---|---|---|
| `#braille-unicode-help` (braille field) | 72–80 w | **59** | 4,913 | **30.9%** |
| `#double-sided-note` (BETA checkbox) | 96 w | 19 | 2,121 | 13.4% |
| `#language-help` (BANA paragraph) | 72 w | 18 | 1,548 | 9.7% |
| **Combined** | | **96** | **8,582** | **54.0%** |

More than half of everything NVDA said in 34 minutes was three paragraphs, repeated.
The BANA paragraph that prompted this investigation is the *smallest* of the three.

## 2.2 Findings

Severity: **High** = a primary navigation or comprehension barrier; **Medium** =
significant friction or a standards deviation with a clear user cost; **Low** = real
but narrow.

| # | Sev | Criterion | Finding | Evidence |
|---|---|---|---|---|
| **F-A** | High | C1 | **The live page has exactly one heading.** Everything below the `<h1>` is `<fieldset>`/`<legend>` or bare buttons. The 40+ well-structured headings in the app all sit inside the help modal, which is `class="modal hidden"` and out of the tree until opened. So the method 71.6% of users reach for first finds nothing. | Probe: `TOTAL VISIBLE HEADINGS: 1`. Log: "heading level 1" spoken twice in 34 min, both on page load. |
| **F-B** | High | C2, C10 | **Six accordion headers are bare buttons, and each leaks its `▼` glyph into its own name.** NVDA says "Shape Selection▼ button collapsed". The Expert Mode toggle one line away *does* have `aria-hidden="true"` on its icon, so this is an inconsistency, not a house style. | `public/index.html:3516, 3589, 3637, 3727, 3789, 3830` (no `aria-hidden`) vs `:3493` (has it). Log: "Shape Selection▼" ×17, "Braille Spacing▼" ×15, "Translation Options▲" ×12. |
| **F-C** | High | C6, C5 | **One 72-word paragraph is wired to three separate controls and accounts for 31% of all speech.** `#braille-unicode-help` describes the braille textarea *and* both Translate buttons. It is already visible on screen directly under the field — so the text is not the problem; forcing it into speech three times per pass is. | Probe: `72 w × 2 hosts` + `80 w × 1 host`. Log: 59 exposures, 4,913 words. Hosts at `public/index.html:3264` (Translate to Braille), `:3273` (the textarea) and `:3278` (Translate to Text); the paragraph itself is `:3282`. |
| **F-D** | High | C6 | **The two other long descriptions are far over any defensible limit** — 96 words on the double-sided checkbox, 72 on the language combo. Both are reference material (how interpoint works; BANA business-card guidelines) that belongs in the help guide, which already has a section for each. | Probe + log, table in §2.1. |
| **F-E** | Medium | C3, C4 | **The skip link skips nothing.** Between `<body>` and `<main>` there is only the link itself and a hidden live region. All page chrome — font size, theme, GitHub, help — sits *inside* `<main>`, so "Skip to main content" lands the user immediately before the font-size buttons. There is no `banner` landmark. | Probe: `focusableBeforeTarget: 0`, `firstInsideTarget: font-decrease`. Source `:3043–3058`. |
| **F-F** | Medium | C5 | **15 of 33 tab stops come before the first control that does the app's job.** Font size ×3, theme, GitHub, help, the 3D viewer, brightness ×2, contrast ×2, edges, a *second* GitHub link, and "Help me choose what to include" — all before Placement Mode at stop 16. | Probe: real tab ring, stops 1–15. |
| **F-G** | Medium | C8 | **The 3D preview is a focusable element with no keyboard operation.** `#viewer` has `tabindex="0"` and `role="img"`, and there is no `keydown` listener on it anywhere in the file. Its own label says it "requires mouse or touch to rotate and zoom" — so a keyboard user spends ~65 words of speech arriving at a dead stop that tells them they cannot use it. | Probe: `{"tabindex":"0","role":"img","hasOnKeyDown":false}`. Only `keydown` listeners in the file are the modal focus trap and the help tabs (`:9763, 9770, 9775`). |
| **F-H** | Medium | C1 | **The product's own name is mangled on first impression.** NVDA reads the `<h1>` as "Custom Braille**STL** Generator", twice per session, at the moment of first contact. **The cause is subtle and worth stating precisely:** Chrome's computed name is correct — "Custom Braille STL Generator" — and the `<form>` that borrows the same heading via `aria-labelledby` reads correctly too. The `<h1>` contains two `display:block` spans, and NVDA's browse-mode buffer joins those two rendered lines with no space. So the same element yields two different strings by two different paths, and an `aria-label` "fix" would paper over the wrong one. | Log 13:05:01 and 13:06:12 vs 13:16:02. Probe: AX name correct, `innerText` = `"Custom Braille\nSTL Generator"`, both spans `display: block`. |
| **F-I** | Medium | C9 | **One keystroke produces three utterances.** Typing the first capital `H` with capitals disabled: character echo, then "Braille field cleared because the text changed…", then the capitalisation note — all inside 32 ms, all ahead of the user's next keystroke. Each message is individually correct and correctly gated; nothing here is a regression. The gap is that no policy decides what happens when two independent live regions fire on the same action. | Log 13:27:44.997–13:27:45.029. |
| **F-J** | Low | C7 | **The capitalisation note duplicates the radio it points at.** Focusing the "Disabled" radio speaks the note and then the radio's own description 20 ms later — two ways of saying the same thing, back to back. | Log 13:30:50.693 / 13:37:10.260. |
| **F-K** | Low | C7 | **Four screen-reader-only descriptions restate their own labels.** Each manual-placement row has `<span class="sr-only">Select translation language for line N</span>` attached to a select already labelled "Line N Translation". Invisible to any sighted review; audible on every pass. | `public/index.html:5422–5424`. Log 13:20:35–13:20:37. |
| **F-L** | Low | C3 | **The Generate button is outside the form it drives.** `</form>` closes at `:3879`; the button is at `:3884`. NVDA announces "out of form" immediately before the app's primary action. | Source `:3879, 3884`. Log 13:13:17.845. |
| **F-M** | Medium | C8 | **13 of the 33 numeric dials expose no minimum or maximum.** They are native `input type="number"` with no `min`/`max` attribute, so nothing maps to `aria-valuemin`/`aria-valuemax` and a screen-reader user is told the current value with no sense of the allowed range — on exactly the tactile parameters that have documented safe ranges (`dot_spacing`, `cell_spacing`, `line_spacing`, `emboss_dot_base_diameter`, `braille_x_adjust`, `braille_y_adjust`, `grid_rows`, `grid_columns` among them). **This is an announcement gap, not a safety hole:** the ranges do exist and are enforced in `settings.schema.json` and server-side validation — they are simply not on the control. | Probe over `public/index.html`: 33 `input type=number`, 13 with `min` or `max` absent. |
| **F-N** | Low | C7 | **Card Thickness announces two group names for one set of radios.** A `<legend>Card Thickness</legend>` wraps a `role="radiogroup" aria-label="Select card thickness preset"`, so the user hears "Card Thickness grouping" and then "Select card thickness preset grouping required" before the first option. The other radio groups nest an *unlabelled* `role="radiogroup"` inside their fieldset, which NVDA does not announce separately — so this is a one-off, not the house pattern. | Source `:3431–3432`. Log 13:11:59.315–13:11:59.334 vs 13:12:53.971 (single group). |

## 2.3 Checked and found correct — do not "fix" these

Recording these so a later pass does not re-litigate them:

- **The live-warning gates are right.** `#auto-overflow-warning` and `#caps-warning`
  both use the hidden→shown gate, and the repeated warnings in the log are genuine
  hide/show boundaries as text was edited back and forth — not per-keystroke chatter.
  The FD-20 fixes hold. (`public/index.html:6633–6641, 5832–5845`.)
- **Several long notes are already delivered the way §1.5 recommends** — the
  contracted-braille note, the tactile-arrow tip, and the capital-letters note are
  visible `.grade-note` text, browseable, and *not* wired to `aria-describedby`. The
  right pattern is already in the file; F-C and F-D are the places that departed
  from it.
- **Landmarks and their labels are sound** — `main`, two labelled `region`s, a
  labelled `form`. F-E is about what is *inside* `main`, not about the landmarks.
- **`#line{i}-help` ("Maximum 50 characters for line N") earns its place** — it adds
  the limit, which the label does not carry. Only its sibling F-K is duplication.

## 2.4 Decision points for Brennen

Wording and structure are his calls, not mine (accessibility rules 11 and 12). Nothing
below has been changed.

**D1 — Headings (F-A, F-B).** Adding real headings is the highest-value change in this
document, and it is also the one most likely to shift the visual design. Options:
(a) wrap the six accordion buttons in `<h3>`, per APG and GOV.UK — no visible change
if the heading is styled to inherit; (b) also promote the major fieldset legends to
headings; (c) headings only inside Expert Mode. **Recommendation: (a) plus (b).**

**D2 — The three long descriptions (F-C, F-D).** For each of the three, choose:
keep as-is / shorten to one sentence and move the rest to visible text / move to the
help guide. The braille-field paragraph (F-C) has a cheap partial fix available with
no wording change at all: drop `aria-describedby` from the two Translate buttons and
leave it on the textarea, which alone removes about 20% of all speech.

**D3 — Page chrome and the skip link (F-E, F-F).** Whether to move the accessibility
controls, theme, help and GitHub links into a `<header role="banner">` above `<main>`.
This makes the skip link real and cuts 15 pre-task tab stops to a handful. It is a
structural change to a file with a lot of history, so it is worth deciding
deliberately rather than folding into a wording pass.

**D4 — The 3D preview (F-G).** Either remove `tabindex="0"` so it stops being a dead
tab stop, or give it real keyboard controls (arrows to rotate, +/− to zoom). Removing
it is a one-line change; adding controls is a feature. Which?

**D5 — The `<h1>` (F-H).** Confirm the intent is one product name that *wraps* onto
two lines, and fix it in CSS rather than with a duplicate `aria-label`.

**D6 — Announcement policy (F-I, F-J).** Do we want a rule such as "at most one
live-region message per user action, most urgent first"? That is a design decision
with follow-on work, not a bug fix.

**D7 — Verbosity rule adoption (§1.5).** Adopt as the project's written standard? If
so it belongs in `ADA_ACCESSIBILITY_VALIDATION_SOP.md` as a check, so future work is
measured against it rather than re-arguing each paragraph.

**D8 — Dial ranges (F-M).** Whether to put `min`/`max` on the 13 numeric inputs that
lack them, so the allowed range is announced. **The numbers must be copied from
`settings.schema.json`, never chosen here** — several of these are tactile parameters
governed by accessibility rule 11, and this audit deliberately proposes no values. The
open question is whether exposing the range on the control could change any existing
behaviour (browser-level constraint validation would begin rejecting out-of-range
entry, where today only the server rejects it), which is a functional change worth
deciding rather than assuming.

## 2.5 Spec contradiction — flagged, not fixed

One finding contradicts a shipped specification. Per the project rule, the code is
authoritative and the mismatch is reported rather than silently corrected on either
side.

**`UI_INTERFACE_CORE_SPECIFICATIONS.md` §4.1 (line 1550)** states:

> "A skip link is provided for keyboard users to bypass the header and jump directly
> to the main content"

**What the page actually does (F-E):** there is no `header` or `banner` landmark, and
the link bypasses **zero** focusable controls — the first focusable element inside
`#main-content` is `#font-decrease`, one of the controls a user would reasonably
expect a skip link to skip. The section's CSS, which the same passage documents, is
accurate and was correctly fixed in v1.17; only the sentence describing *what the link
achieves* is wrong.

Nothing has been changed. If D3 is approved, the fix and this sentence should move
together; if D3 is declined, the sentence still needs correcting to describe what the
link really does.

## 2.6 Suggested order, if all are approved

1. **F-B icons** — six `aria-hidden="true"` attributes; no visible change, no wording
   change, immediately removes a glyph from six accessible names.
2. **F-C partial** — drop the shared description from the two Translate buttons.
   Roughly a fifth of all speech, one attribute per button, no wording change.
3. **F-K**, **F-N**, **F-H**, **F-G** — small, self-contained, no wording changes.
4. **F-A / D1 headings** — the big win; needs D1 answered first.
5. **F-M** dial ranges — needs D8, and the numbers come from the schema.
6. **F-D** wording moves — needs D2 answered; touches signed-off text.
7. **F-E / F-F** structure — needs D3; largest blast radius.
8. **F-I / F-J** — needs the D6 policy decision.

---

## What this audit did not cover

- **Fixes.** Deliberately none. This document ends at an approved list.
- **The braille geometry pipeline.** Tactile output is audited by print, not by NVDA.
- **Re-running the live-warnings walkthrough.** POST15_6 closed it; its Part 5
  regression listen happens whenever that document is next run.
- **JAWS, VoiceOver, and mobile screen readers.** Every measurement here is NVDA on
  Chrome. The heading and verbosity findings are model-independent; the specific
  browse-mode behaviour in F-H is not.
- **A second listening run.** Everything in Part 2 is measured from the existing log
  and from the live accessibility tree. Confirming the *experience* of a fix will
  need Brennen at the keyboard again.

## Verification

Research and audit only — no application code was changed, so the suite bar must not
move. Established at the start of this work and unchanged at the end:

```
python -m ruff check .                                        -> All checks passed!
python -m pytest tests/ -v                                    -> 140 passed
npm test                                                      -> 2 passed
npx playwright test tests/e2e/ --project=chromium --project=firefox -> 122 passed (3.7m)
```

Old -> new: ruff clean -> clean; 140 -> 140 pytest; 2 -> 2 vitest; 122 -> 122 e2e.

## Related documents

- [NVDA Live Warnings Walkthrough](./NVDA_LIVE_WARNINGS_WALKTHROUGH.md) — the run that produced the evidence for this audit
- [NVDA Double-Sided Walkthrough](./NVDA_DOUBLE_SIDED_WALKTHROUGH.md) — the beta flow's own listening pass
- [ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) — where the §1.5 verbosity rule would live if adopted (D7)
- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md) — §4.10 governs the live-region behaviour confirmed correct in §2.3

## Sources

- [WebAIM Screen Reader User Survey #10](https://webaim.org/projects/screenreadersurvey10/) — navigation-method statistics (§1.1)
- [WAI-ARIA Authoring Practices — Accordion Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/accordion/) — heading-wrapped headers (§1.3)
- [WAI-ARIA APG — Providing Accessible Names and Descriptions](https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/) — descriptions supplement, not duplicate (§1.3)
- [GOV.UK Design System — Text input (hint text)](https://design-system.service.gov.uk/components/text-input/) — the one-short-sentence limit (§1.3, §1.5)
- [GOV.UK Design System — Accordion](https://design-system.service.gov.uk/components/accordion/) — real `<h2>` section headings (§1.3)
- [NVDA User Guide](https://download.nvaccess.org/documentation/userGuide.html) — browse/focus mode, single-letter navigation, Elements List (§1.2)
- [Slack Accessibility](https://slack.com/accessibility) — user-controllable verbosity as a product feature (§1.4)
- [GitHub Accessibility](https://accessibility.github.com/) — accessibility as governance (§1.4)

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-22 | Created for POST-15 item 7 (FD-20d), in a fresh session after POST15_6 closed. Part 1 researched from the sources listed above; Part 2 measured from the archived NVDA speech log (1,010 utterances / 15,881 words, windowed to the browser-focused segment) and from two new live accessibility-tree probes (`build/a11yverify/post15_7/`). Fourteen findings, four of them High, plus four items checked and confirmed correct so a later pass does not re-open them. Seven decision points recorded for Brennen, and one spec contradiction flagged (UI_INTERFACE_CORE §4.1); no code, wording or structure changed. Suite bar unmoved: ruff clean, 140 pytest, 2 vitest, 122 e2e. |
