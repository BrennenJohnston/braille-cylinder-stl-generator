# Screen-Reader UX Research and Flow Audit

**Status:** research and audit — **the fixes are now under way.** All eight decision
points were put to Brennen on 2026-08-22 and **all eight are answered** (§2.4); he
chose the recommended option in every case, so §2.6 is an approved plan rather than a
proposal. As of 2026-08-22, follow-up items **A, B and C have landed** (each recorded
in place in §2.2 and in the Document History below) and **item D has adopted the §1.5
verbosity rule and the §1.6 flow criteria into the ADA SOP**; items E, F and G are
still open. Every wording change still returns to Brennen as a draft before it ships
(accessibility rule 12).

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

## 1.5 The verbosity rule (ADOPTED 2026-08-22)

**Status: adopted, and it now lives somewhere it will actually be run.** Brennen
approved the rule as written (FD-21, D7) and item D copied it into
[ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) **Step
6.8**, where it is a required check after any change to `aria-describedby`,
`aria-label` or `sr-only` text — including on the quick-validation path. The numbers
did not change: **15-word target, 25-word hard ceiling.** The §1.6 criteria below went
into the same SOP as **Section 12**, a periodic review rather than a per-commit gate.
**If the SOP and this section ever disagree, the SOP is the one that governs** — this
document is the record of how the rule was derived, not the copy anyone runs.

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

Ten criteria, each one checkable. Part 2 walks the app against them. **Adopted
2026-08-22 as Section 12 of the ADA SOP** — a periodic review aid, explicitly not a
gate on every commit.

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
| Visible headings in the live page | **1** (the `<h1>`) → **6** on load after item C, 2026-08-22 (11 with Expert Mode open) |
| Tab stops on load | **33** |
| Tab stops before the first control that does the app's actual job | **15** |
| Focusable controls the skip link skips | **0** |
| Description words in one full read of the default page | **574** (→ **430** after item A, 2026-08-22) |
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
| **F-A** | High | C1 | ~~**The live page has exactly one heading.** Everything below the `<h1>` is `<fieldset>`/`<legend>` or bare buttons. The 40+ well-structured headings in the app all sit inside the help modal, which is `class="modal hidden"` and out of the tree until opened. So the method 71.6% of users reach for first finds nothing.~~ **FIXED 2026-08-22** (item C, D1, UI_INTERFACE_CORE v1.22 §4.11), in two commits. Part 1: the six accordion buttons are each now the sole child of an `<h3>`, per APG and GOV.UK — which also closes **C2**. Part 2: Enter Text, Double-Sided Card, Row Indicator Style, Card Thickness and Select Plate each gained an `<h2>` **inside** the existing `<legend>`, so the fieldset grouping is untouched. **Visible headings 1 → 6 on load, 11 with Expert Mode open, 12 with the beta on too; no skipped level in any state.** W3C Nu 0 errors / 0 warnings proves heading-in-legend is legal. Not yet heard under NVDA. | Probe: `TOTAL VISIBLE HEADINGS: 1` → **6**. Log: "heading level 1" spoken twice in 34 min, both on page load. |
| **F-B** | High | C2, C10 | ~~**Six accordion headers are bare buttons, and each leaks its `▼` glyph into its own name.** NVDA says "Shape Selection▼ button collapsed". The Expert Mode toggle one line away *does* have `aria-hidden="true"` on its icon, so this is an inconsistency, not a house style.~~ **GLYPH LEAK FIXED 2026-08-22** (item A, UI_INTERFACE_CORE v1.20 §4.5): all six `.expert-submenu-icon` spans gained `aria-hidden="true"`; probe re-run shows **5 of 5 exposed accordion names leaked a triangle before, 0 after**, and the attribute survives the ▼→▲→▼ swap. **The "bare buttons" half of this finding is still OPEN** — wrapping the six toggles in `<h3>` is D1 and belongs to item C. | `public/index.html:3516, 3589, 3637, 3727, 3789, 3830` (no `aria-hidden`) vs `:3493` (has it). Log: "Shape Selection▼" ×17, "Braille Spacing▼" ×15, "Translation Options▲" ×12. |
| **F-C** | High | C6, C5 | ~~**One 72-word paragraph is wired to three separate controls and accounts for 31% of all speech.** `#braille-unicode-help` describes the braille textarea *and* both Translate buttons. It is already visible on screen directly under the field — so the text is not the problem; forcing it into speech three times per pass is.~~ **FIXED 2026-08-22** (item A, D2 step 1, UI_INTERFACE_CORE v1.20 §4.7): `aria-describedby` dropped from `#translate-to-braille-btn` and `#translate-to-text-btn`; the textarea keeps it. Probe re-run: hosts **3 → 1**, total description words in one full read **574 → 430** (−144, the predicted 72 × 2). The paragraph is unchanged and still visible under the field. **Shortening it is D2 step 2 and remains OPEN** (item F). | Probe: `72 w × 2 hosts` + `80 w × 1 host`. Log: 59 exposures, 4,913 words. Hosts at `public/index.html:3264` (Translate to Braille), `:3273` (the textarea) and `:3278` (Translate to Text); the paragraph itself is `:3282`. |
| **F-D** | High | C6 | **The two other long descriptions are far over any defensible limit** — 96 words on the double-sided checkbox, 72 on the language combo. Both are reference material (how interpoint works; BANA business-card guidelines) that belongs in the help guide, which already has a section for each. | Probe + log, table in §2.1. |
| **F-E** | Medium | C3, C4 | **The skip link skips nothing.** Between `<body>` and `<main>` there is only the link itself and a hidden live region. All page chrome — font size, theme, GitHub, help — sits *inside* `<main>`, so "Skip to main content" lands the user immediately before the font-size buttons. There is no `banner` landmark. | Probe: `focusableBeforeTarget: 0`, `firstInsideTarget: font-decrease`. Source `:3043–3058`. |
| **F-F** | Medium | C5 | **~~15 of 33~~ 14 of 32 tab stops come before the first control that does the app's job.** Font size ×3, theme, GitHub, help, ~~the 3D viewer,~~ brightness ×2, contrast ×2, edges, a *second* GitHub link, and "Help me choose what to include" — all before Placement Mode at stop ~~16~~ 15. **Re-measured 2026-08-22** after item B removed the viewer from the ring (F-G / D4); the rest of this finding is unchanged and still OPEN — it is D3 / item G. | Probe: real tab ring, stops 1–15 (now 1–14). |
| **F-G** | Medium | C8 | ~~**The 3D preview is a focusable element with no keyboard operation.** `#viewer` has `tabindex="0"` and `role="img"`, and there is no `keydown` listener on it anywhere in the file. Its own label says it "requires mouse or touch to rotate and zoom" — so a keyboard user spends ~65 words of speech arriving at a dead stop that tells them they cannot use it.~~ **FIXED 2026-08-22** (item B, D4, commit `847ea09`): `tabindex="0"` removed. Checked first that nothing depended on it — no test references `#viewer` focus and no script focuses it; the `#viewer:focus-within, #viewer:active` rule still applies on pointer use. `role="img"`, the `aria-label` and `aria-describedby` all stay, so it is unchanged in browse mode. Probe: `tabindex` `"0" → null`, `inTabRing` `true → false`, **real tab ring on load 33 → 32**, and a diff of the two rings shows exactly one removal, `<div id=viewer>` — nothing else moved. This also moves F-F's figure: **14 of 32** stops now precede Placement Mode, not 15 of 33. Keyboard controls for the preview remain a deferred feature (FD-21 D4). | Probe: `{"tabindex":"0","role":"img","hasOnKeyDown":false}`. Only `keydown` listeners in the file are the modal focus trap and the help tabs (`:9763, 9770, 9775`). |
| **F-H** | Medium | C1 | ~~**The product's own name is mangled on first impression.** NVDA reads the `<h1>` as "Custom Braille**STL** Generator", twice per session, at the moment of first contact. **The cause is subtle and worth stating precisely:** Chrome's computed name is correct — "Custom Braille STL Generator" — and the `<form>` that borrows the same heading via `aria-labelledby` reads correctly too. The `<h1>` contains two `display:block` spans, and NVDA's browse-mode buffer joins those two rendered lines with no space. So the same element yields two different strings by two different paths, and an `aria-label` "fix" would paper over the wrong one.~~ **FIXED 2026-08-22** (item B, D5, commit `8b8f532`): `.title-section h1` is no longer `display: flex` — which was what blockified the two spans — and the spans are now `display: inline`, joined by the ordinary word space already in the source. Probe: `innerText` `"Custom Braille\nSTL Generator"` → **`"Custom Braille STL Generator"`**; span display `block, block` → `inline, inline`; the AX name and the form landmark's borrowed name were correct before and stay correct. No `aria-label` was added. **D5's prescription was not followed literally, with Brennen's agreement.** It called for a single text node with the two-line look coming from CSS. Rendering the page showed there is no two-line look to move — the title is **one line at 1440 px and at 320 px, at 100% and 200%** — and a single text node would have flattened the two-tone, because CSS cannot colour half a text node ("Custom Braille" is `--text-primary` at weight 700, "STL Generator" `--text-secondary` at 600). Brennen was shown both renderings and chose to keep the spans. Evidence: `build/a11yverify/post15_7b/title_{before,after}_*.png`, h1 box height identical in all four cases (29/29/20/20 px), all three themes re-checked, SOP reflow 0 failures of 6. | Log 13:05:01 and 13:06:12 vs 13:16:02. Probe: AX name correct, `innerText` = `"Custom Braille\nSTL Generator"`, both spans `display: block`. |
| **F-I** | Medium | C9 | **One keystroke produces three utterances.** Typing the first capital `H` with capitals disabled: character echo, then "Braille field cleared because the text changed…", then the capitalisation note — all inside 32 ms, all ahead of the user's next keystroke. Each message is individually correct and correctly gated; nothing here is a regression. The gap is that no policy decides what happens when two independent live regions fire on the same action. | Log 13:27:44.997–13:27:45.029. |
| **F-J** | Low | C7 | **The capitalisation note duplicates the radio it points at.** Focusing the "Disabled" radio speaks the note and then the radio's own description 20 ms later — two ways of saying the same thing, back to back. | Log 13:30:50.693 / 13:37:10.260. |
| **F-K** | Low | C7 | ~~**Four screen-reader-only descriptions restate their own labels.** Each manual-placement row has `<span class="sr-only">Select translation language for line N</span>` attached to a select already labelled "Line N Translation". Invisible to any sighted review; audible on every pass.~~ **FIXED 2026-08-22** (item B, commit `23575ab`): `aria-describedby` removed from the four `line_lang_N` selects and the orphan `line{N}-lang-help` spans deleted from the generated markup. Probe re-run in manual placement mode: descriptions on the four selects **4 → 0** (24 words), sr-only spans in the DOM **4 → 0**, the selects keep their names "Line 1–4 Translation". **One correction to this row's own premise:** these rows are `display:none` in the DEFAULT (auto) placement mode, so they never appeared in the default AX tree at all — the finding is real but only reachable after the user switches to Manual, which is the mode the NVDA log below was recorded in. That is why the default-state description budget is unchanged at 430 words. The sibling `#line{N}-help` was left untouched, as §2.3 requires. | `public/index.html:5422–5424`. Log 13:20:35–13:20:37. |
| **F-L** | Low | C3 | **The Generate button is outside the form it drives.** `</form>` closes at `:3879`; the button is at `:3884`. NVDA announces "out of form" immediately before the app's primary action. | Source `:3879, 3884`. Log 13:13:17.845. |
| **F-M** | Medium | C8 | ~~**13 of the 33 numeric dials expose no minimum or maximum.**~~ **CLOSED 2026-08-22 (item E).** They are native `input type="number"` with no `min`/`max` attribute, so nothing maps to `aria-valuemin`/`aria-valuemax` and a screen-reader user is told the current value with no sense of the allowed range — on exactly the tactile parameters that have documented safe ranges (`dot_spacing`, `cell_spacing`, `line_spacing`, `emboss_dot_base_diameter`, `braille_x_adjust`, `braille_y_adjust`, `grid_rows`, `grid_columns` among them). **This is an announcement gap, not a safety hole:** the ranges do exist and are enforced server-side — they are simply not on the control. **Correction, 2026-08-22 (v1.2):** the source is `app/validation.py`, **not** `settings.schema.json`. Checked field by field after this audit was first written: only 7 of the 13 appear in the schema under a matching name at all, and **none of those 7 carries a `maximum`** — just a `minimum` of 0 or 1, which is a not-negative guard rather than a range. All thirteen do have real (min, max) pairs in `app/validation.py`. That is a schema-vs-code drift in its own right and is flagged, not fixed, in §2.5. **Closure, 2026-08-22:** all 13 now declare `min`/`max`, copied verbatim from `app/validation.py` (Brennen chose that source over the schema — FD-22 Q1). Measured over CDP before and after: dials announcing a REAL range **19 → 29**, and the finding understated the defect — Chrome does not leave a bare spinbutton blank, it synthesises `valuemin=0, valuemax=0`, so a screen reader was told the range was "0 to 0" while the value read 2.5. Three of the 13 (`card_width`, `card_height`, `card_thickness`) sit in a `<div hidden>` and were measured as absent from the AX tree both before and after, so the real announcement gain is **10 dials, not 13**. The constraint-validation side-effect check that D8 required found a genuine behaviour change and is recorded as **F-O** below. | Probe over `public/index.html`: 33 `input type=number`, 13 with `min` or `max` absent. Closure probe: `build/a11yverify/post15_7/axprobe_ranges.cjs`. |
| **F-O** | **High** | C8 | **An out-of-range dial silently kills the Generate button, and the bad value survives a reload.** `public/index.html:5095` calls `form.requestSubmit()`, which runs interactive constraint validation, so any `:invalid` control aborts the submit and generation never starts. When the dial is visible the browser focuses it and speaks its message, which is fine. When it is not reachable — typed, then persisted to `localStorage` as `braille_prefs_*`, then restored on a later load with Expert Mode collapsed — the browser cannot focus it, logs `An invalid form control … is not focusable`, and the user gets **nothing at all**: no error, no message, a dead button, on every subsequent load. **This is PRE-EXISTING, not caused by item E:** measured on untouched `develop`, **20 of the 20 dials that already carried `min`/`max` block generation this way today.** Item E widens the exposure from 20 dials to 30. Brennen chose to ship item E as-is and track this separately rather than suppress it with a form-wide `novalidate` (which was built and measured — it restores generation and keeps all 29 ranges announced — but would strip native validation from the 20 controls that have it today). The 122-test e2e suite is green throughout and does not cover this. | `build/a11yverify/post15_7/constraint_sideeffect.cjs` (0 → 10 of 10 blocked), `constraint_existing_20.cjs` (20 of 20 blocked on develop today), `constraint_visible_path.cjs` (visible dial: focused, "Value must be less than or equal to 5."), `constraint_collapse_trap.cjs` (survives reload, dead button, "not focusable"). |
| **F-N** | Low | C7 | ~~**Card Thickness announces two group names for one set of radios.** A `<legend>Card Thickness</legend>` wraps a `role="radiogroup" aria-label="Select card thickness preset"`, so the user hears "Card Thickness grouping" and then "Select card thickness preset grouping required" before the first option. The other radio groups nest an *unlabelled* `role="radiogroup"` inside their fieldset, which NVDA does not announce separately — so this is a one-off, not the house pattern.~~ **FIXED 2026-08-22** (item B, commit `63d5778`): the redundant `aria-label` dropped; `role="radiogroup"` and `aria-required` kept. **The premise was verified on the live AX tree before editing, not taken on trust:** the thickness div really did expose `radiogroup name="Select card thickness preset"` nested inside `group name="Card Thickness"`, while both siblings — Select Plate to Generate and Row Indicator Style — exposed `radiogroup name=""`. After: the thickness radiogroup's name is `""` too, and named grouping nodes on the page fall **16 → 15**. | Source `:3431–3432`. Log 13:11:59.315–13:11:59.334 vs 13:12:53.971 (single group). |

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

## 2.4 Decision points — ALL EIGHT ANSWERED (Brennen, 2026-08-22)

Wording and structure are his calls, not mine (accessibility rules 11 and 12). He was
asked all eight at the close of this audit and **chose the recommended option in every
case**. Nothing has been implemented yet — each answer below becomes work in a
follow-on item, and every wording change still comes back to him as a draft before it
ships.

**D1 — Headings (F-A, F-B). ANSWERED: accordions *and* section legends.** Wrap the six
Expert Mode accordion buttons in `<h3>` per APG and GOV.UK, **and** promote the major
fieldset legends — Enter Text, Double-Sided Card, Card Thickness, Row Indicator Style,
Select Plate — to real headings. Styled to inherit, so nothing needs to look different.
This is the change that turns the page from one heading into a navigable map.
— **D1: LANDED IN FULL 2026-08-22, item C**, two commits, exactly as answered — six
`<h3>` accordion wrappers and five `<h2>`s promoted from the section legends. Visible
headings **1 → 6** on load, **11** with Expert Mode open, **12** with the beta on as
well; **no skipped level in any state**. The `<h2>` goes *inside* the `<legend>`, which
keeps the fieldset grouping — W3C Nu returns **0 errors / 0 warnings** on both the
source file and the rendered DOM, so the technique is proved, not assumed. Two things
would have broken silently and did not: `initExpertSubmenus()` found its panel with
`toggle.nextElementSibling` (now `null` — it reads `aria-controls`), and
`updateDoubleSidedUI()` assigned `legend.textContent`, which would have deleted the new
heading (it writes to `#front-entry-heading`). Nothing moved on screen: header
screenshots byte-identical. **The outline is proven by probe; that it helps is not
proven until Brennen presses H in NVDA — item G's closing step.**

**D2 — The three long descriptions (F-C, F-D). ANSWERED: unwire the extras, then
shorten.** Two steps, in order. (1) Drop `aria-describedby` from the two Translate
buttons — no wording change, removes roughly a fifth of all speech. (2) Shorten all
three paragraphs to one sentence each, with the **full text staying visible on the page
where it already is** — nothing is deleted, it just stops being forced into speech on
every pass. Wording drafts come back for approval before anything ships.

**D3 — Page chrome and the skip link (F-E, F-F). ANSWERED: move chrome into a banner.**
Put the font-size, theme, GitHub and help controls into a `<header role="banner">`
above `<main>`. This makes the skip link real, cuts the 15 pre-task tab stops to a
handful, and adds a proper banner landmark. Structural edit to a file with a lot of
history — it wants its own careful pass, not a fold-in.

**D4 — The 3D preview (F-G). ANSWERED: remove it from the tab ring.** Drop
`tabindex="0"`. It stays fully readable in browse mode with its label intact; it just
stops being a stop that leads nowhere. Keyboard controls for the preview were
considered and set aside as a separate feature, not part of this cleanup.
— **LANDED 2026-08-22, item B** (`847ea09`). Tab ring 33 → 32. The deferred keyboard
controls are still deferred.

**D5 — The `<h1>` (F-H). ANSWERED: one text node, wrap in CSS.** Confirmed that the
intent is one product name that happens to wrap onto two lines. Make the heading a
single text node and get the two-line look from CSS width/centering instead of two
`display:block` spans — correct in every mode and every screen reader, and no
duplicate `aria-label`.
— **LANDED 2026-08-22, item B** (`8b8f532`) — **but by the second of two routes, on
Brennen's call.** Implementation found the premise wrong in one respect: the title
does not wrap onto two lines anywhere. It is one line at 1440 px and 320 px, at 100%
and 200% font size; the two spans sit side by side with a 0.4 em gap, in different
colours and weights. The blockification came from `display: flex` on the h1, not from
a wrap. Both candidate fixes were rendered and measured, and both produced exactly
`"Custom Braille STL Generator"`; the single text node would additionally have
flattened the two-tone, since CSS cannot colour half a text node. Shown both,
**Brennen chose to keep the two spans and make them `display: inline`** — same
defect closed, no visual change. The rest of D5 stands as answered: no duplicate
`aria-label`, and the fix is at the cause rather than over it.

**D6 — Announcement stacking (F-I, F-J). ANSWERED: fix the duplicate only.** Stop the
capitalisation note repeating what the "Disabled" radio's own description already says
(F-J). **The keystroke stacking in F-I is deliberately left alone** — it is two
individually correct messages landing before the user's next keypress, and a general
"one message per action" policy would be guesswork without a real user test to justify
it. Revisit if a screen-reader user reports it.

**D7 — Verbosity rule adoption (§1.5). ANSWERED: adopt into the SOP as written.** The
rule goes into `ADA_ACCESSIBILITY_VALIDATION_SOP.md` as a check, at the 15-word target
and 25-word ceiling stated here, so future work is measured against a number rather
than re-arguing each paragraph. `axprobe.cjs` re-measures it in one command.

**D8 — Dial ranges (F-M). ANSWERED: add from the schema, check side-effects first
— but the named source turned out not to hold the data.** The principle he set
stands and is not in doubt: the numbers are **copied from a source, never chosen by
an assistant**, since several are tactile parameters governed by accessibility rule
11. **What changed is only WHERE they come from.** `settings.schema.json` was checked
field by field after this answer was given and cannot supply them — 6 of the 13
fields are absent from it under any matching name, and none of the other 7 carries a
`maximum`. `app/validation.py` has all thirteen with real ranges. **Because
project-facts rule 7 makes the schema the single source of truth, switching sources
is not an assistant's call**: `POST15_7E_DIAL_RANGES_PROMPT.txt` opens by putting
that question back to Brennen before any edit. Before committing,
confirm that adding them changes no existing behaviour: browser-level constraint
validation would begin marking out-of-range entry invalid, where today only the server
rejects it. That check gets reported before the change ships.

## 2.5 Spec contradiction — flagged, not fixed

Two findings contradict a shipped specification. Per the project rule, the code is
authoritative and each mismatch is reported rather than silently corrected on either
side.

**Contradiction 2 — `settings.schema.json` vs `app/validation.py` (F-M, D8). STATUS
2026-08-22: RECORDED, NOT CLOSED — now its own tracked item.** Brennen was asked
directly whether the schema should gain the missing maximums as part of item E and
answered no: it is a separate item, because editing the declared source of truth
changes backend validation and absent-field fallbacks and deserves its own
verification pass (FD-22, Q2). Item E therefore took its numbers from
`app/validation.py` and left the schema untouched. The drift below still stands
exactly as written. One correction of detail from the item E measurement: the six
fields called "absent from the schema" are not missing, they are **renamed** —
`card/plate_width_mm`, `plate_height_mm`, `plate_thickness_mm` and
`dots/cone/diameter_mm`, `height_mm`, `flat_hat_diameter_mm`. The conclusion is
unchanged: not one of the 13 carries a `maximum`.

**Contradiction 2 — `settings.schema.json` vs `app/validation.py` (F-M, D8).** The
schema is the project's declared single source of truth for settings and validation
(project-facts rules 7 and 8), yet `app/validation.py` enforces minimum/maximum
ranges for all 13 bare dials that the schema does not state — 6 of the fields are
absent from the schema entirely under those names, and not one of the remaining 7
carries a `maximum`. The code is authoritative and the ranges it enforces are real;
what is wrong is the claim that the schema is complete. Flagged only — closing it
means either adding the maxima to the schema or amending rules 7/8, and both are
Brennen's call.

**Contradiction 1 — `UI_INTERFACE_CORE_SPECIFICATIONS.md` §4.1 (line 1550)** states:

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

## 2.6 Approved implementation order

All eight decisions are answered, so this is the agreed sequence — cheapest and safest
first, each step independently shippable. **Steps 1 and 2 are DONE (2026-08-22, item A),
step 3 (item B) and step 4 (item C) are DONE the same day; steps 5–8 have not been
started.**

1. ~~**F-B icons** — six `aria-hidden="true"` attributes; no visible change, no wording
   change, immediately removes a glyph from six accessible names.~~ **DONE 2026-08-22.**
   Triangles in accordion names 5 → 0.
2. ~~**F-C partial** — drop the shared description from the two Translate buttons.
   Roughly a fifth of all speech, one attribute per button, no wording change.~~
   **DONE 2026-08-22.** Hosts 3 → 1; description words 574 → 430 (−25.1%).
3. ~~**F-K**, **F-N**, **F-H**, **F-G** — small, self-contained, no wording changes.~~
   **DONE 2026-08-22** (item B), four separate commits. Tab ring 33 → 32; named
   groups 16 → 15; the four duplicate line descriptions gone; the h1 reads as one
   name. No user-visible sentence and no pixel changed.
4. ~~**F-A / D1 headings** — the big win; needs D1 answered first.~~ **DONE 2026-08-22**
   (item C), two commits. Visible headings 1 → 6 on load, 11 with Expert Mode open; no
   skipped level in any state; W3C Nu 0 errors / 0 warnings; no pixel changed. This also
   closes criterion **C2** (accordion headers wrapped in headings).
5. ~~**F-M** dial ranges — needs D8, and the numbers come from the schema.~~ **DONE 2026-08-22**
   (item E), one commit plus docs. The source was `app/validation.py`, not the schema (FD-22).
   Real ranges announced 19 → 29. Spun out **two tracked items**: the schema's missing `maximum`
   values (§2.5 Contradiction 2), and the new **F-O** silent-Generate defect.
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
- [ADA Accessibility Validation SOP](./ADA_ACCESSIBILITY_VALIDATION_SOP.md) — where the §1.5 verbosity rule now lives (Step 6.8) and the §1.6 flow criteria now live (Section 12), adopted 2026-08-22 under D7
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
| 1.6 | 2026-08-22 | **The rule leaves this document and becomes a procedure (item D, D7).** §1.5 and §1.6 were adopted into `ADA_ACCESSIBILITY_VALIDATION_SOP.md` v1.2 — the six-clause verbosity rule as **Step 6.8**, a required check after any change to `aria-describedby`, `aria-label` or `sr-only` text including on the quick path, and the C1–C10 flow criteria as **Section 12**, explicitly a periodic review aid rather than a per-commit gate. **The numbers are unchanged: 15-word target, 25-word hard ceiling.** Documentation only; no application code, no wording, no measurement in this document changed. §1.5's heading and §1.6's lead now say adopted rather than proposed and name the SOP sections; the Related Documents line that read "where the rule would live if adopted" now says where it lives. **§1.5 also states that the SOP governs if the two ever disagree** — this document is the derivation, not the copy anyone runs. The SOP's Step 6.8 is runnable and was run to write it: `axprobe.cjs` against a live `python backend.py`, giving the worked FAIL (96 / 80 / 71 words) and the worked PASS (13 words) it now documents, `TOTAL` **430**, unchanged from item A's figure. A minimal rebuild listing is in SOP §6.8.4 because `build/` is gitignored, and it was verified the same day to reproduce this document's instrument 2 exactly. **One stale line corrected while here:** the Status header still read "nothing in this document has been implemented", which items A, B and C had already falsified; it now names what has landed and what is still open. Suite unmoved: ruff clean, 140 pytest, 2 vitest, 122 e2e |
| 1.5 | 2026-08-22 | **F-A closed — the finding this audit called the highest-value change in it.** F-A struck through and fixed in place (with criterion **C2** closed alongside it, since the six accordion headers are what C2 measures); §2.1's headline heading count, §2.4's D1 answer and §2.6's step 4 all annotated with what landed. Two commits, item C: six `<h3>` wrappers round the accordion buttons (APG/GOV.UK), then `<h2>`s inside the five major section legends. **Visible headings 1 → 6 on load, 11 with Expert Mode open, 12 with the double-sided beta on as well; no skipped level in any state.** Levels chosen h2/h3 and the reasoning recorded in UI_INTERFACE_CORE v1.22 §4.11, along with the one thing left open — the Expert Mode disclosure button still carries no heading, so a strict outline nests the h3s under *Select Plate to Generate*. Validated: W3C Nu **0 errors / 0 warnings on source AND rendered DOM**, Lighthouse **100/100 desktop and mobile**, reflow **0 of 6**, tab ring **unchanged at 32**, description budget **unchanged at 430 words / 18 nodes**, every `role=group` name unchanged, header screenshots **byte-identical**, suite **140 pytest / 2 vitest / 122 e2e** unchanged. **Still unheard: nobody has run NVDA against this.** |
| 1.4 | 2026-08-22 | **Four more findings closed — the small self-contained batch (item B), four separate commits, no user-visible sentence and no pixel changed.** F-K, F-N, F-G and F-H struck through and marked fixed in place; F-F's count re-measured because F-G moved it; §2.6 step 3 and the D4/D5 answers annotated. **F-K** (`23575ab`): `aria-describedby` dropped from the four `line_lang_N` selects and the orphan `line{N}-lang-help` spans deleted — descriptions on those selects **4 → 0**, spans in the DOM **4 → 0**, `#line{N}-help` untouched. **F-N** (`63d5778`): the redundant `aria-label` off the Card Thickness radiogroup — named grouping nodes **16 → 15**, and the group now matches its two siblings. **F-G / D4** (`847ea09`): `tabindex="0"` off `#viewer` — **tab ring 33 → 32**, a ring diff showing exactly one removal. **F-H / D5** (`8b8f532`): the h1 stops being a flex container and its spans go inline — `innerText` **`"Custom Braille\nSTL Generator"` → `"Custom Braille STL Generator"`**. **Two premises in this document were checked against the live page before editing, and one was wrong.** F-N's was right, and is now recorded with the measurement that proves it. F-H's was wrong about the *look*: the title does not wrap onto two lines at any tested width or font size, so D5's "get the two-line look from CSS" had nothing to move, and its single text node would have flattened the two-tone that CSS cannot reproduce on half a text node. Brennen was shown both renderings and chose the span-preserving route. A third premise needed a correction of scope rather than fact: F-K's four rows are `display:none` in the default auto placement mode, so they only reach a screen reader in Manual — which is where the original NVDA log caught them, and why the default-state description budget stays at **430 words**. Evidence: `axprobe.cjs`, `axprobe2.cjs` and a new `axprobe4.cjs` (grouping nodes, per-line descriptions, ring membership), plus before/after title screenshots at 1440 px and 320 px × 100% and 200%. Suite unchanged before and after: ruff clean, 140 pytest, 2 vitest, 122 e2e. W3C Nu: 0 errors, 0 warnings. **Still measured by probe, not by ear** — the re-listen remains item G's closing step. |
| 1.3 | 2026-08-22 | **First fixes land — the two free wins (item A).** F-B's glyph leak and F-C are struck through and marked fixed in place, in the POST15_4 pattern; neither is deleted, and the parts of each that remain open are named where they stand. Six `.expert-submenu-icon` spans gained `aria-hidden="true"` and both Translate buttons lost `aria-describedby`. Re-measured with the same instrument that produced the original numbers, plus a third probe (`axprobe3.cjs`) written for this item because `axprobe.cjs` prints names only for nodes that carry a description and the accordion toggles carry none: **accordion names leaking a triangle 5 → 0**, **`#braille-unicode-help` hosts 3 → 1**, **description words in one full read 574 → 430**, a drop of exactly the predicted 144. §2.1 and §2.6 annotated with the new figures. **Two things deliberately NOT done:** no paragraph was reworded (D2 step 2, item F), and the six toggles are still bare buttons rather than headings (D1, item C) — so F-B is only half closed. Two spec documents updated alongside: `UI_INTERFACE_CORE_SPECIFICATIONS.md` v1.20 (§4.5 and §4.7, the latter having documented the exact wiring that was removed) and `SURFACE_DIMENSIONS_SPECIFICATIONS.md` v1.3, whose HTML sample would otherwise have taught the pre-fix chevron markup to the next submenu. Suite unchanged before and after: ruff clean, 140 pytest, 2 vitest, 122 e2e. **Measured by probe, not yet confirmed by ear** — the re-listen is item G's closing step. |
| 1.2 | 2026-08-22 | **A correction, found while writing the follow-up prompt files.** D8's approved instruction — copy `min`/`max` verbatim from `settings.schema.json` — **cannot be carried out as written**, and neither could F-M's claim that the ranges are enforced there. Checked field by field: 6 of the 13 fields are absent from the schema under any matching name, and none of the other 7 carries a `maximum` (only a `minimum` of 0 or 1). All thirteen ranges do exist in `app/validation.py`. F-M and D8 corrected in place, and a **second spec contradiction** added to §2.5 — the schema is the declared single source of truth yet is the incomplete one. Switching sources is not an assistant's call, so `POST15_7E` opens by putting it back to Brennen. Brennen's *principle* (numbers copied, never chosen) is unchanged; only the source is in question. **Also recorded:** the seven follow-up prompt files `POST15_7A`–`POST15_7G` were written into the planning folder, one per item in §2.6. No measurement or finding severity changed. |
| 1.3 | 2026-08-22 | **Item E ran and closed F-M.** All 13 bare dials now declare `min`/`max`, taken from `app/validation.py` after Brennen was asked which source to use — the v1.2 correction had established the schema could not supply them, and switching sources was his call, not an assistant's (FD-22, Q1). Measured over CDP: dials announcing a real range **19 → 29**; the placeholder pair Chrome synthesises for a bare spinbutton (`valuemin=0, valuemax=0`) is gone. Two corrections of fact to this document, both from measurement rather than reading: the six "absent" schema fields are **renamed, not missing**, and three of the 13 (`card_width`/`_height`/`_thickness`) are in a `<div hidden>` and reach no screen reader at all, so the announcement gain is **10 dials, not 13**. The side-effect check D8 required found a genuine behaviour change and is recorded as a new finding **F-O** — it is pre-existing for the 20 already-bounded dials, and Brennen chose to ship item E as-is and track it rather than mask it with `novalidate`. §2.5 Contradiction 2 is now an explicitly tracked item (FD-22, Q2). Suite green throughout: ruff clean, 140 pytest, 2 vitest, 122 e2e, unchanged before and after. |
| 1.1 | 2026-08-22 | **All eight decision points answered by Brennen the same day** — he chose the recommended option in every case. §2.4 rewritten from open questions into recorded answers, with the reasoning for the two deliberate *non*-changes preserved: F-I's keystroke stacking is left alone as two individually correct messages (only F-J's duplication is fixed), and 3D-preview keyboard controls are set aside as a separate feature rather than folded into D4's one-line fix. §2.6 promoted from "suggested order" to the approved implementation sequence. **Still nothing implemented**, and every wording change returns as a draft first. No finding, measurement or count changed. |
| 1.0 | 2026-08-22 | Created for POST-15 item 7 (FD-20d), in a fresh session after POST15_6 closed. Part 1 researched from the sources listed above; Part 2 measured from the archived NVDA speech log (1,010 utterances / 15,881 words, windowed to the browser-focused segment) and from two new live accessibility-tree probes (`build/a11yverify/post15_7/`). Fourteen findings, four of them High, plus four items checked and confirmed correct so a later pass does not re-open them. Seven decision points recorded for Brennen, and one spec contradiction flagged (UI_INTERFACE_CORE §4.1); no code, wording or structure changed. Suite bar unmoved: ruff clean, 140 pytest, 2 vitest, 122 e2e. |
