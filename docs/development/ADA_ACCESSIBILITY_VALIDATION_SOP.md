# ADA Accessibility Validation SOP

## Standard Operating Procedure for Maintaining WCAG 2.1 Level AA Compliance

**Document Version:** 1.2
**Created:** December 8, 2025
**Last Updated:** August 22, 2026
**Standard:** WCAG 2.1 Level AA
**Compliance Deadline:** April 24, 2026 / April 26, 2027

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [When to Perform Validation](#3-when-to-perform-validation)
4. [Pre-Development Checklist](#4-pre-development-checklist)
5. [Development Guidelines](#5-development-guidelines)
6. [Post-Development Validation Procedure](#6-post-development-validation-procedure)
7. [Automated Testing Tools](#7-automated-testing-tools)
8. [Manual Testing Checklist](#8-manual-testing-checklist)
9. [Common Accessibility Issues and Fixes](#9-common-accessibility-issues-and-fixes)
10. [Documentation Requirements](#10-documentation-requirements)
11. [Quick Reference Card](#11-quick-reference-card)
12. [Periodic Screen-Reader Flow Review](#12-periodic-screen-reader-flow-review)

---

## 1. Purpose

This SOP ensures that the Braille Card and Cylinder STL Generator maintains WCAG 2.1 Level AA compliance throughout its development lifecycle. Following these procedures prevents accessibility regressions and ensures the application remains usable by people with disabilities.

---

## 2. Scope

This procedure applies to:
- All changes to `public/index.html` (the only page — the `templates/` folder is deprecated and empty)
- Any UI/UX modifications
- New feature implementations
- CSS styling changes
- JavaScript functionality changes affecting user interaction
- Third-party library updates

---

## 3. When to Perform Validation

### Full Validation Required (All Steps)

Perform **full validation** when:
- Adding new UI components (buttons, forms, panels, modals)
- Modifying existing interactive elements
- Changing color schemes or themes
- Adding or modifying accordion/toggle functionality
- Updating text content in significant amounts
- Modifying form controls or labels
- Adding new sections or reorganizing layout
- Updating third-party libraries (Three.js, etc.)

### Quick Validation Sufficient

Perform **quick validation** (Steps 6.1, 6.2, 6.3 only) when:
- Minor text corrections
- Bug fixes not affecting UI
- Backend-only changes
- Documentation updates

**One addition to the quick path.** If the change touches any `aria-describedby`
target, `aria-label`, or `sr-only` text — even a one-word correction — also run
**Step 6.8**. Description text is the one thing a "minor text correction" can make
worse without any other check in this SOP noticing.

---

## 4. Pre-Development Checklist

Before starting development on a new feature, review:

- [ ] **Consult UI Specifications**: Read `docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md`
- [ ] **Review Accessibility Section**: Section 4 covers all accessibility requirements
- [ ] **Check Color Contrast Requirements**:
  - Text: 4.5:1 minimum ratio
  - Large text (18pt+ or 14pt bold): 3:1 minimum ratio
  - UI components: 3:1 minimum ratio
- [ ] **Plan ARIA Attributes**: Determine what ARIA attributes new elements need
- [ ] **Keyboard Navigation**: Plan how users will navigate the new feature with keyboard only

---

## 5. Development Guidelines

### 5.1 HTML Structure

```html
<!-- ✅ GOOD: Semantic HTML with proper ARIA -->
<button type="button"
        id="my-toggle"
        class="toggle-btn"
        aria-expanded="false"
        aria-controls="my-content">
    <span id="toggle-text">Show Content</span>
    <span class="toggle-icon">▼</span>
</button>
<div id="my-content" style="display: none;">
    <!-- Content here -->
</div>

<!-- ❌ BAD: Missing ARIA attributes -->
<div class="clickable" onclick="toggle()">
    Show Content
</div>
```

### 5.2 JavaScript Event Handlers

```javascript
// ✅ GOOD: Updates aria-expanded dynamically
myToggleBtn.addEventListener('click', () => {
    const isVisible = myContent.style.display !== 'none';
    myContent.style.display = isVisible ? 'none' : 'block';
    myToggleBtn.setAttribute('aria-expanded', String(!isVisible));
    myToggleBtn.classList.toggle('active', !isVisible);
});

// ❌ BAD: Does not update ARIA state
myToggleBtn.addEventListener('click', () => {
    myContent.style.display = myContent.style.display === 'none' ? 'block' : 'none';
});
```

### 5.3 CSS Color Contrast

```css
/* ✅ GOOD: Meets WCAG AA contrast (4.5:1+) */
.toggle-btn.active {
    background: #1e4976; /* Dark blue: 6.1:1 with white */
    color: #fff;
}

/* ❌ BAD: Fails WCAG AA contrast */
.toggle-btn.active {
    background: #3182ce; /* Light blue: 3.7:1 with white - FAILS */
    color: #fff;
}
```

### 5.4 Form Controls

```html
<!-- ✅ GOOD: Proper label association -->
<label for="my-input">Input Label:</label>
<input type="text" id="my-input" name="my_input" aria-describedby="my-input-help">
<div id="my-input-help" class="help-text">Help text here</div>

<!-- ✅ GOOD: Screen-reader-only label for visual context -->
<label for="language-select" class="sr-only">Select braille language table</label>
<select id="language-select" name="language_table">...</select>

<!-- ❌ BAD: No label association -->
<span>Input Label:</span>
<input type="text" name="my_input">
```

### 5.5 Focus Management

```javascript
// ✅ GOOD: Move focus to first focusable element when panel opens
panelToggle.addEventListener('click', () => {
    const isOpen = panel.style.display !== 'none';
    panel.style.display = isOpen ? 'none' : 'block';

    if (!isOpen) {
        // Move focus to first focusable element
        const firstFocusable = panel.querySelector(
            'input, select, button, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 100);
        }
    }
});
```

---

## 6. Post-Development Validation Procedure

### 6.1 W3C HTML Validation (Required)

1. Start local server: `$env:FLASK_ENV="development"; python backend.py`
2. Open https://validator.w3.org/
3. Select "Validate by URI" or "Validate by Direct Input"
4. Enter `http://127.0.0.1:5001` or paste HTML content
5. Click "Check"
6. **Target**: 0 errors, 0 warnings

**Common Errors to Watch For:**
- Duplicate IDs
- Missing closing tags
- Invalid ARIA attributes on wrong element types
- Deprecated attributes

### 6.2 Lighthouse Accessibility Audit (Required)

1. Open application in Chrome/Edge
2. Press **F12** to open DevTools
3. Click **Lighthouse** tab
4. Uncheck all categories except **Accessibility**
5. Select **Desktop** mode, click "Analyze page load"
6. Record score and any issues
7. Select **Mobile** mode, repeat analysis
8. **Target**: 100/100 on both Desktop and Mobile

**A 100 is necessary, but it is not sufficient — do not stop here.** This page has
scored 100/100 desktop and mobile twice with real WCAG failures live: once with
**eleven contrast failures** (recorded in `../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md`
§4.9, v1.18, 2026-08-21 — an inline colour on a `display:none` box is never sampled,
and the page's background gradient defeats sampling outright), and once with **live
regions that announced nothing** (§4.10, found by the NVDA walkthrough on 2026-08-18
after three phases of clean 100/100 scores, because Lighthouse and axe-core do not
evaluate the runtime write-then-reveal sequence).

**If Score < 100:**
- Review each failing audit item
- Fix issues in order of impact (Critical → Moderate → Minor)
- Re-run Lighthouse until 100/100 achieved

### 6.3 Color Contrast Verification (Required for Style Changes)

**Option A: WebAIM Contrast Checker**
1. Go to https://webaim.org/resources/contrastchecker/
2. Enter foreground and background colors
3. Verify "WCAG AA" shows "Pass" for your use case

**Option B: Chrome DevTools**
1. Right-click element → Inspect
2. In Styles panel, click any color value
3. Look for contrast ratio in color picker
4. Green checkmark = passes, Red X = fails

**Required Ratios:**
| Content Type | Minimum Ratio |
|--------------|---------------|
| Normal text (<18pt) | 4.5:1 |
| Large text (18pt+ or 14pt bold) | 3:1 |
| UI components (buttons, icons) | 3:1 |

### 6.4 Keyboard Navigation Test (Required for Interactive Changes)

1. Refresh the page
2. Press **Tab** repeatedly through entire page
3. Verify:
   - [ ] All interactive elements are reachable
   - [ ] Focus order is logical (top-to-bottom, left-to-right)
   - [ ] Focus indicator is visible on all elements
   - [ ] Skip link appears on first Tab and works
4. Test all toggles/accordions with **Enter** and **Space** keys
5. Test form submission with **Enter** key

### 6.5 Screen Reader Test (Required for Major UI Changes)

**Using NVDA (Free):**
1. Download from https://www.nvaccess.org/
2. Start NVDA, open application
3. Navigate using Tab key
4. Verify:
   - [ ] All buttons announce their purpose
   - [ ] Toggle buttons announce expanded/collapsed state
   - [ ] Form fields announce their labels
   - [ ] Error messages are announced when they appear
   - [ ] Images have appropriate alt text or are marked decorative

### 6.6 Theme Testing (Required for Color/Style Changes)

Test all functionality in each theme:
1. **Dark Mode** (default)
2. **High Contrast Mode**
3. **Light Mode**

For each theme, verify:
- [ ] All text is readable
- [ ] Focus indicators are visible
- [ ] Button states are distinguishable
- [ ] No content disappears or becomes unreadable

### 6.7 Font Size Testing (Required for Layout Changes)

1. Use application font controls to set 200% size
2. Verify:
   - [ ] No content is cut off or hidden
   - [ ] No horizontal scrolling required
   - [ ] All functionality remains accessible
3. Test at 75% minimum size
4. Verify all content remains readable

### 6.8 Description Verbosity Check (Required whenever description text changes)

**Run this whenever a change adds, removes, or rewords an `aria-describedby` target,
an `aria-label`, or `sr-only` text** — including on the quick-validation path in
Section 3.

**Why this step exists.** The first full NVDA session on this app (2026-08-22, 34
minutes, 15,881 words spoken) found that **three `aria-describedby` paragraphs were
54% of everything the screen reader said** — one of them repeated 59 times. Each of
those paragraphs looked reasonable when it was written. Judgement is what produced
that page, so this step replaces judgement with a number anyone can re-measure in one
command.

#### 6.8.1 The rule

Adopted 2026-08-22, approved as written by Brennen (FD-21, D7). Copied from
[Screen-Reader UX Research and Flow Audit](./SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md)
§1.5, which records how it was derived. Six clauses:

1. **`aria-describedby` gets one short sentence — a target of 15 words, a hard
   ceiling of 25.** It is spoken in full on every visit, so it may carry only what the
   user needs *at that control, at that moment*, and that the name does not already
   say.
2. **Anything longer stays on the page as ordinary visible text, next to the control,
   and is NOT wired to `aria-describedby`.** It remains fully available: a browse-mode
   user reads it with the arrow keys, in their own time, by choice. Making it a
   description does not add information — it removes the user's *choice* about when to
   hear it.
3. **Reference material — standards, guidelines, worked examples — belongs in the
   help guide**, which this app already has and which is already well structured
   (40+ headings). Not on a control.
4. **A description must never restate the label.** If the name says it, delete it.
5. **One description, one host.** If the same text is wired to several controls, the
   user pays for it several times per pass. Attach it to the one control it is really
   about.
6. **Screen-reader-only text (`sr-only`) gets the same scrutiny as visible text —
   more, because no sighted review will ever catch it.**

#### 6.8.2 What this rule is NOT

> **This is not permission to delete explanations.** Every paragraph the rule has
> flagged so far is genuinely useful text, some of it hard-won and signed off. The
> rule governs **how text is delivered, not whether it exists**. A paragraph over the
> ceiling **stays on the page as visible, browseable text** and simply loses its
> `aria-describedby` wiring — the sighted reader loses nothing, and the screen-reader
> user gains the choice of when to read it.
>
> Taking the sentence off the page altogether is a **different change**. It needs its
> own reason, and because this is accessibility-critical text it needs Brennen's
> sign-off before it ships (accessibility rule 12). Never cite this rule as the reason
> for a deletion.

#### 6.8.3 How to run the check

The probe reads Chrome's computed accessibility tree — the names and descriptions as
a screen reader actually receives them. Parsing the HTML cannot do this: descriptions
are computed from several attributes, and parts of this page are shown or hidden by
script after load.

```bash
# Terminal 1 - the app under test. Port 5001 must be free.
# backend.py defaults to 5001 and its CORS allowlist accepts only 5001.
python backend.py

# Terminal 2 - the probe
node build/a11yverify/post15_7/axprobe.cjs
```

Read the block headed `=== COMPUTED DESCRIPTIONS IN THE AX TREE ===`. Each entry is:

```
  <words> w x <hosts> host(s) = <cost> w  "<first 88 characters>..."
         host: <role>:<accessible name of the control>
```

**It passes when all three of these are true:**

- every listed description is **25 words or fewer** (clause 1);
- every entry reads **`x 1 host(s)`** (clause 5);
- no description repeats the `host:` name printed under it (clause 4) — this one you
  read, the probe cannot judge it.

**A worked FAIL — the real output from this repo on 2026-08-22**, showing the first
three of the seven entries it listed (the ones after these were 43, 38, 26 and 13
words); the `TOTAL` is the real one for the whole page:

```
=== COMPUTED DESCRIPTIONS IN THE AX TREE (18 nodes carry one) ===
   96 w x 1 host(s) =   96 w  "Embosses both sides of the card in one pass: Cylinder A (the embossing plate) carries th..."
         host: checkbox:Emboss both sides of the card (interpoin
   80 w x 1 host(s) =   80 w  "Accepts braille characters only (U+2800–U+28FF). Press Translate to Braille to fill this..."
         host: textbox:Braille (Unicode) — one line per row
   71 w x 1 host(s) =   71 w  "Default: English (UEB), United States — contracted (grade 2). The BANA Guidelines for Br..."
         host: combobox:Select braille language table
  TOTAL description words reachable in one full read of the default page: 430
```

96, 80 and 71 words are all far over the 25-word ceiling, so all three fail clause 1.
The 96-word and 71-word entries are also reference material that the help guide
already covers, which is clause 3. **The fix is clause 2 — unwire them and leave the
words on the page** — not a rewrite that squeezes 96 words into 25.

**A worked PASS — from the same run:**

```
   13 w x 1 host(s) =   13 w  "Custom settings - automatically selected when any parameter is modified from preset valu..."
         host: radio:Custom
```

13 words, inside the 15-word target; one host; and it says something the name
"Custom" does not.

**Three things to know before you trust the output:**

- **It prints only descriptions of 10 words or more.** Shorter ones are counted in the
  `TOTAL` but not listed. That is safe for clause 1 — anything unlisted is already
  inside the target — but it means a *short* description wired to several controls
  will not appear. If you add an `aria-describedby`, check clause 5 by reading the
  source as well.
- **`TOTAL` is the whole budget**, printed entries and unlisted ones together,
  multiplied by their host counts. Quote it in the commit message; a rise with no new
  printed line is the short-description-many-hosts case above.
- **It measures the DEFAULT page state only.** Controls that are hidden at load —
  manual-placement rows, Expert Mode panels — are not in the accessibility tree, so
  their descriptions are not counted. If your change touches a hidden section, open
  that section in the probe before trusting the number. This is not hypothetical: four
  duplicate line-language descriptions fixed on 2026-08-22 never appeared in the
  default-state total at all.

#### 6.8.4 If the probe file is missing

`build/` is in `.gitignore`, so **the probe is not checked into the repository** and a
fresh clone will not have it. It was written for the POST15_7 screen-reader UX audit
on 2026-08-22 and is described in that audit under "How the numbers here were
measured" (instrument 2) and in its Document History v1.0.

If `build/a11yverify/post15_7/axprobe.cjs` is gone, recreate the part this step needs
from the listing below. It needs no setup beyond `@playwright/test`, which is already
a dev dependency. Save it anywhere under `build/` and run it the same way. Verified
2026-08-22: it reproduces the full probe's block exactly — same 18 nodes, same
entries, same `TOTAL` of 430.

```js
// Minimal rebuild of the ADA SOP Step 6.8 description probe.
const { chromium } = require('@playwright/test');
const words = (s) => (s || '').trim().split(/\s+/).filter(Boolean).length;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://localhost:5001/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(6000); // liblouis WASM + the thickness preset settle late

  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Accessibility.enable');
  const { nodes } = await cdp.send('Accessibility.getFullAXTree');

  const byDesc = new Map();
  let hostCount = 0;
  for (const n of nodes) {
    if (n.ignored) continue;
    const desc = n.description && n.description.value;
    if (!desc || words(desc) === 0) continue;
    hostCount++;
    if (!byDesc.has(desc)) byDesc.set(desc, { w: words(desc), hosts: [] });
    const role = (n.role && n.role.value) || '';
    const name = ((n.name && n.name.value) || '').slice(0, 40);
    byDesc.get(desc).hosts.push(role + ':' + name);
  }

  console.log('=== COMPUTED DESCRIPTIONS IN THE AX TREE (' + hostCount + ' nodes carry one) ===');
  let total = 0;
  const ranked = [...byDesc.entries()].sort((a, b) => b[1].w * b[1].hosts.length - a[1].w * a[1].hosts.length);
  for (const [text, info] of ranked) {
    const cost = info.w * info.hosts.length;
    total += cost;
    if (info.w >= 10) {
      console.log('  ' + String(info.w).padStart(3) + ' w x ' + info.hosts.length
        + ' host(s) = ' + String(cost).padStart(4) + ' w  "' + text.slice(0, 88) + '..."');
      info.hosts.forEach((h) => console.log('         host: ' + h));
    }
  }
  console.log('  TOTAL description words reachable in one full read of the default page: ' + total);

  await browser.close();
})().catch((e) => { console.error('PROBE FAILED:', e); process.exit(1); });
```

---

## 7. Automated Testing Tools

### Required Tools

| Tool | Purpose | URL |
|------|---------|-----|
| W3C HTML Validator | HTML syntax validation | https://validator.w3.org/ |
| Lighthouse | Accessibility scoring | Built into Chrome/Edge DevTools |
| WebAIM Contrast Checker | Color contrast verification | https://webaim.org/resources/contrastchecker/ |

### Recommended Tools

| Tool | Purpose | URL |
|------|---------|-----|
| WAVE | Visual accessibility evaluation | https://wave.webaim.org/extension/ |
| axe DevTools | Detailed accessibility testing | Chrome/Firefox extension |
| NVDA | Screen reader testing | https://www.nvaccess.org/ |
| Color Oracle | Color blindness simulation | https://colororacle.org/ |

---

## 8. Manual Testing Checklist

Use this checklist for each major feature release:

### HTML/Structure
- [ ] All interactive elements are semantic HTML (`<button>`, `<a>`, `<input>`)
- [ ] All form inputs have associated `<label>` elements
- [ ] Page has proper heading hierarchy (h1 → h2 → h3)
- [ ] Landmark regions are properly defined (`<main>`, `<nav>`, `<header>`)
- [ ] Skip link is present and functional

### ARIA
- [ ] All expandable elements have `aria-expanded`
- [ ] All expandable elements have `aria-controls` pointing to content ID
- [ ] Dynamic content updates use `aria-live` regions
- [ ] Decorative elements have `aria-hidden="true"`
- [ ] Icons have `aria-hidden="true"` with text alternatives

### Keyboard
- [ ] All functionality works with keyboard only
- [ ] Tab order follows visual layout
- [ ] Focus is never trapped
- [ ] Modal/dialogs trap focus appropriately
- [ ] Escape key closes modals/dropdowns

### Visual
- [ ] Focus indicators are visible in all themes
- [ ] Color is not the only means of conveying information
- [ ] Text contrast meets 4.5:1 minimum
- [ ] UI component contrast meets 3:1 minimum
- [ ] Content reflows at 400% zoom without horizontal scroll

### Screen-Reader Flow
- [ ] Every description is inside the Step 6.8 ceiling, re-measured with the probe
- [ ] The C1–C10 flow review in [Section 12](#12-periodic-screen-reader-flow-review) has been walked since the last major release

---

## 9. Common Accessibility Issues and Fixes

### Issue: Toggle Button Missing aria-expanded

**Symptom:** Screen reader doesn't announce expanded/collapsed state

**Fix:**
```html
<!-- Add to button element -->
<button aria-expanded="false" aria-controls="panel-id">Toggle</button>

<!-- Add to JavaScript handler -->
button.setAttribute('aria-expanded', String(isExpanded));
```

### Issue: Insufficient Color Contrast

**Symptom:** Lighthouse reports contrast error

**Fix:**
1. Use WebAIM Contrast Checker to find compliant color
2. For active button states, use darker variants:
   - Light mode: `#1e4976` (6.1:1 with white)
   - Dark mode: `#1e5a8a` (4.7:1 with white)

### Issue: Form Input Without Label

**Symptom:** Screen reader doesn't announce input purpose

**Fix:**
```html
<!-- Option 1: Visible label -->
<label for="input-id">Label Text</label>
<input id="input-id" type="text">

<!-- Option 2: Screen-reader-only label -->
<label for="input-id" class="sr-only">Label Text</label>
<input id="input-id" type="text">

<!-- Option 3: aria-label (less preferred) -->
<input id="input-id" type="text" aria-label="Label Text">
```

### Issue: Missing Focus Indicator

**Symptom:** Can't see which element is focused when tabbing

**Fix:**
```css
button:focus,
input:focus,
select:focus {
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}
```

### Issue: Decorative Icon Read by Screen Reader

**Symptom:** Screen reader announces emoji/icon characters

**Fix:**
```html
<span aria-hidden="true">▼</span>
```

---

## 10. Documentation Requirements

After completing accessibility validation, update the following:

### 10.1 Update Accessibility Documentation

Add a new entry to your accessibility tracking with:
- Date of validation
- Issues found (if any)
- Fixes applied
- Verification results (W3C, Lighthouse scores)

### 10.2 Update UI Specifications (if applicable)

Location: `docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md`

If new accessibility patterns were introduced, document them in Section 4 (Accessibility Features).

### 10.3 Commit Message Format

Use this format for accessibility-related commits:

```
fix: resolve [N] accessibility issues found in [feature] audit

- [Brief description of fix 1] (WCAG X.X.X)
- [Brief description of fix 2] (WCAG X.X.X)
- Sync changes to public/index.html
- Update ADA accessibility roadmap

Lighthouse score: [before] → [after]
```

---

## 11. Quick Reference Card

### Minimum Requirements for Any UI Change

| Check | Tool | Target |
|-------|------|--------|
| HTML Valid | W3C Validator | 0 errors |
| Accessibility Score | Lighthouse | 100/100 |
| Text Contrast | Contrast Checker | 4.5:1+ |
| Keyboard Navigation | Manual | All reachable |
| Description length | `axprobe.cjs` (Step 6.8) | ≤25 words, one host each |

**Lighthouse 100/100 is the minimum, not the finish line** — it has scored 100 here
twice with real failures live. See Step 6.2.

### Essential ARIA for Toggle Buttons

```html
<button aria-expanded="false" aria-controls="content-id">
```

```javascript
button.setAttribute('aria-expanded', String(!isCollapsed));
```

### Essential CSS for Focus

```css
:focus {
    outline: 3px solid var(--border-focus);
    outline-offset: 2px;
}
```

### Color Contrast Safe Values

| Use Case | Light Mode | Dark Mode | High Contrast |
|----------|------------|-----------|---------------|
| Active button bg | `#1e4976` | `#1e5a8a` | `#000000` |
| Active button text | `#ffffff` | `#ffffff` | `#02fe05` |
| Focus outline | `#3182ce` | `#63b3ed` | `#ff00ff` |

---

## 12. Periodic Screen-Reader Flow Review

**This is a review aid, not a gate on every commit.** Nothing in this section blocks
a merge, and no one should be asked to run it before a one-line fix. Run it when a
release, a large feature, or a screen-reader listening session is being planned — a
few times a year, not a few times a day.

It exists because a page can pass every per-change check in Section 6 and still be
tiring to use. The first full NVDA session on this app passed every count it was
checking and still took about 34 minutes instead of the estimated 12, with a lot of
wandering. Section 6 asks "is this control correct?"; this section asks "can someone
get through the whole page?"

The ten criteria are adopted from
[Screen-Reader UX Research and Flow Audit](./SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md)
§1.6. Each one is checkable rather than a matter of taste.

| # | Criterion | Source |
|---|---|---|
| C1 | Every major section of the page is reachable by a real heading, in a sensible level order | WebAIM 71.6%; WCAG 2.4.10 |
| C2 | Accordion/disclosure headers are wrapped in headings, not bare buttons | APG Accordion; GOV.UK |
| C3 | Landmarks divide the page into meaningful, labelled areas — and page chrome is not inside `main` | APG; HTML spec |
| C4 | The skip link actually skips a meaningful number of controls | WCAG 2.4.1 |
| C5 | The task's own controls come before, or close after, the page's decorative and utility controls | Flow |
| C6 | Every description obeys the verbosity rule in Step 6.8 | GOV.UK; APG |
| C7 | No description restates its label; no `sr-only` text duplicates visible text | APG |
| C8 | Every element in the tab ring can be operated from the keyboard, and every value control announces its allowed range | WCAG 2.1.1; APG Spin Button; project rules 3 and 10 |
| C9 | One user action produces one coherent announcement, in a useful order | WCAG 4.1.3 |
| C10 | Decorative glyphs and icons never reach the accessible name | Project rule 7 |

**How to use the result.** A criterion that fails is a finding to record and
schedule — not an emergency, and not something to fix in whatever commit happened to
notice it. Write it down with the measurement that shows it (the Step 6.8 probe
prints headings, landmarks and the real tab ring alongside the descriptions, which
covers C1–C6 and C10), then decide the order of work separately. That is exactly how
the fourteen findings in the audit above were handled.

**What this section cannot tell you.** Every criterion here is measured from markup
and from the accessibility tree. None of them proves the page is pleasant to listen
to. Only a person at the keyboard with a screen reader does that, and criteria C5 and
C9 in particular are judgement calls that a probe can only inform.

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial SOP created after re-audit session |
| 1.1 | 2026-08-18 | Section 2 scope now names `public/index.html` only (`templates/` is deprecated and empty). Section 6.1 corrected to `python backend.py` on port 5001 — `backend.py` defaults to 5001 and its CORS allowlist accepts only 5001, so the old `wsgi.py` / port 5000 instructions started a server the app could not talk to |
| 1.2 | 2026-08-22 | **The verbosity rule becomes a runnable check, and Lighthouse stops being presented as sufficient.** Added **Step 6.8, Description Verbosity Check** — the six-clause rule from `SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md` §1.5, adopted as written by Brennen (FD-21, D7): **15-word target, 25-word hard ceiling** on `aria-describedby`, plus one-description-one-host, never restate the label, reference material to the help guide, and `sr-only` text judged the same way. The step is runnable, not aspirational: it documents `python backend.py` + `node build/a11yverify/post15_7/axprobe.cjs`, how to read the `COMPUTED DESCRIPTIONS IN THE AX TREE` block, a worked FAIL and a worked PASS **taken from a real run of this repo on 2026-08-22** (96 / 80 / 71 words over the ceiling; a 13-word description passing; `TOTAL` 430), and the probe's three real limits — it lists only descriptions of 10+ words, `TOTAL` covers the unlisted ones too, and it measures the default page state only. §6.8.2 states in its own block that the rule governs **how text is delivered, not whether it exists**: anything over the ceiling stays on the page as visible text and only loses its `aria-describedby` wiring, and a deletion is a separate change needing Brennen's sign-off. §6.8.4 records that `build/` is gitignored so the probe is not in the repo, says where it came from, and carries a minimal rebuild listing **verified the same day to reproduce the full probe's block exactly** (18 nodes, `TOTAL` 430). Added **Section 12, Periodic Screen-Reader Flow Review** — the ten C1–C10 flow criteria from audit §1.6, marked in its first line as a review aid and **not a gate on every commit**. Section 6.2 gained the caveat that **Lighthouse 100 is necessary but not sufficient**, citing the eleven contrast failures it scored 100/100 through (`UI_INTERFACE_CORE_SPECIFICATIONS.md` §4.9, v1.18) and the live regions that announced nothing (§4.10, found by NVDA on 2026-08-18, not by any tool); the Lighthouse check itself is unchanged. Section 3's quick path now names Step 6.8 as an addition when description text changes; Section 11's card gained a description-length row and a pointer to the Lighthouse caveat. **Documentation only — no application code, wording, or existing check was changed.** Suite unmoved before and after: ruff clean, 140 pytest, 2 vitest, 122 e2e |

---

## Related Documents

- [UI Interface Core Specifications](../specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md)
- [Browser Compatibility Audit](./BROWSER_COMPATIBILITY_AUDIT.md)
- [Screen-Reader UX Research and Flow Audit](./SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md) — where Step 6.8's rule and Section 12's criteria were derived and measured
- [NVDA Live Warnings Walkthrough](./NVDA_LIVE_WARNINGS_WALKTHROUGH.md) — the listening pass that Section 12 is meant to prepare for
