/**
 * E2E regression tests for the silently dead Generate button (audit finding F-O).
 *
 * `#action-btn` generates through `form.requestSubmit()`, which is *native*
 * submission and therefore runs interactive constraint validation first. Any
 * `:invalid` control aborts the submit before the app's own handler ever runs.
 *
 * When the offending control is on screen the browser focuses it and states the
 * problem, and that is correct - this file pins it as unchanged. When it is NOT
 * on screen the browser cannot focus it, logs `An invalid form control ... is
 * not focusable` to a console no user reads, and abandons the press: no error,
 * no message, no visible change. A dead button.
 *
 * That is not a corner case. Every one of the 33 numeric dials lives inside
 * Expert Mode or a hidden block, so on a default load NONE of them is reachable.
 * And because a dial's value is persisted to `localStorage` exactly as typed, a
 * bad value came back on every subsequent load - the trap re-armed itself.
 *
 * **This defect survived all 122 e2e tests.** A green suite was not evidence,
 * because nothing here exercised a form-level constraint failure. That is what
 * this file is for.
 *
 * Two contracts are pinned:
 *
 *  1. **A constraint failure must always reach the user.** Whether or not the
 *     control is on screen, pressing Generate must produce a message naming the
 *     control and what is wrong with it - never silence.
 *  2. **An unusable saved value must not be restored.** It is refused, the field
 *     falls back to the value it ships with, and the user is told. Refused and
 *     reported - never clamped (that would pick a tactile dimension on the
 *     user's behalf) and never silently dropped.
 *
 * The message wording is approved text (Brennen, 2026-08-22, POST15_7H) and the
 * assertions below pin its SHAPE. The range numbers are read from the control's
 * own min/max rather than hardcoded, so retuning a range in `app/validation.py`
 * does not break these tests - only rewording does, which is the point.
 *
 * @see docs/development/SCREEN_READER_UX_RESEARCH_AND_FLOW_AUDIT.md finding F-O
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

/** A dial in the Spacing panel: collapsed on load, and inside Expert Mode. */
const DIAL = 'dot_spacing';
const DIAL_LABEL = 'Braille Dot Spacing';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#auto-text');
}

/**
 * Count submit events without letting a real generation run. Capture phase, so
 * it sees the event before the app's handler; a submit that fires at all is the
 * proof that constraint validation let the press through.
 */
async function armSubmitCounter(page: Page) {
  await page.evaluate(() => {
    const store = window as unknown as { __submits: number };
    store.__submits = 0;
    document.getElementById('braille-form')!.addEventListener('submit', (e) => {
      store.__submits += 1;
      e.preventDefault();
      e.stopImmediatePropagation();
    }, true);
  });
}

async function pressGenerate(page: Page): Promise<number> {
  return page.evaluate(async () => {
    const store = window as unknown as { __submits: number };
    store.__submits = 0;
    document.getElementById('action-btn')!.click();
    await new Promise((r) => setTimeout(r, 600));
    return store.__submits;
  });
}

/**
 * Set a dial directly rather than through `fill()`. Two reasons: `fill()` on
 * this form does not always land under full-suite parallelism, and these dials
 * are collapsed out of view, which is the very condition under test.
 */
async function setDial(page: Page, id: string, value: string) {
  await page.evaluate(([i, v]) => {
    (document.getElementById(i) as HTMLInputElement).value = v;
  }, [id, value]);
}

/** The overlay's own text, only when it is actually on screen. */
async function shownMessage(page: Page): Promise<string> {
  return page.evaluate(() => {
    const box = document.getElementById('error-message')!;
    if (getComputedStyle(box).display === 'none') return '';
    return (document.getElementById('error-text-container')!.textContent || '')
      .replace(/\s+/g, ' ').trim();
  });
}

async function announced(page: Page): Promise<string> {
  return page.evaluate(() =>
    (document.getElementById('a11y-status')!.textContent || '').replace(/\s+/g, ' ').trim());
}

async function focusedId(page: Page): Promise<string> {
  return page.evaluate(() => document.activeElement?.id || '');
}

/** min/max as the control itself declares them, so no range is hardcoded here. */
async function bounds(page: Page, id: string): Promise<{ min: string; max: string }> {
  return page.evaluate((i) => {
    const el = document.getElementById(i) as HTMLInputElement;
    return { min: el.getAttribute('min') || '', max: el.getAttribute('max') || '' };
  }, id);
}

test.describe('constraint failures must never be silent', () => {
  test('an out-of-range dial hidden in Expert Mode does not kill Generate silently', async ({ page }) => {
    await openApp(page);
    await armSubmitCounter(page);

    // Precondition: this is the trap. The dial is genuinely unreachable.
    await expect(page.locator(`#${DIAL}`)).toBeHidden();
    await setDial(page, DIAL, '99');

    expect(await pressGenerate(page)).toBe(0); // generation correctly refused

    // ...but the user must be told which control and what is wrong with it.
    const { min, max } = await bounds(page, DIAL);
    const expected = `${DIAL_LABEL} is 99. Enter a value between ${min} and ${max} to generate.`;
    expect(await shownMessage(page)).toBe(expected);
    expect(await announced(page)).toBe(expected);

    // ...and the control must have been brought into reach, with the accordions'
    // state kept truthful rather than the panels merely forced visible.
    await expect(page.locator(`#${DIAL}`)).toBeVisible();
    expect(await focusedId(page)).toBe(DIAL);
    await expect(page.locator('#expert-toggle')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('[aria-controls="expert-panel-spacing"]'))
      .toHaveAttribute('aria-expanded', 'true');
  });

  test('a value inside the range but off-step is caught too, with its own wording', async ({ page }) => {
    await openApp(page);
    await armSubmitCounter(page);

    // 2.55 is INSIDE the allowed range and still unusable - it is not a step of
    // 0.1. The range sentence would be actively wrong here, so it must not appear.
    await setDial(page, DIAL, '2.55');
    expect(await pressGenerate(page)).toBe(0);

    const message = await shownMessage(page);
    expect(message).toBe(`${DIAL_LABEL} is 2.55. The nearest values it accepts are 2.5 and 2.6.`);
    expect(message).not.toContain('between');
    expect(await focusedId(page)).toBe(DIAL);
  });

  test('several bad dials produce ONE message, not one per control', async ({ page }) => {
    await openApp(page);
    await armSubmitCounter(page);

    await setDial(page, 'dot_spacing', '99');
    await setDial(page, 'cell_spacing', '99');
    await setDial(page, 'line_spacing', '99');
    expect(await pressGenerate(page)).toBe(0);

    // One control is named and focused; the message does not enumerate all three.
    const message = await shownMessage(page);
    expect(message).not.toBe('');
    const named = ['Braille Dot Spacing', 'Braille Cell Spacing', 'Number of Braille Lines']
      .filter((label) => message.includes(label));
    expect(named).toHaveLength(1);
    expect(await focusedId(page)).not.toBe('');
  });

  test('a visible out-of-range dial is left to the browser, unchanged', async ({ page }) => {
    await openApp(page);
    await armSubmitCounter(page);

    // Open the panel the ordinary way, so the dial is reachable.
    await page.locator('#expert-toggle').click();
    await page.locator('[aria-controls="expert-panel-spacing"]').click();
    await expect(page.locator(`#${DIAL}`)).toBeVisible();
    // Opening a panel moves focus to its first field on a 100 ms timer. Wait for
    // that to land: press Generate inside the window and the timer fires
    // afterwards, moving focus off the dial the browser had just focused, and the
    // assertion below reads the accordion's doing rather than the browser's.
    await expect(page.locator('#grid_columns')).toBeFocused();
    await setDial(page, DIAL, '99');

    expect(await pressGenerate(page)).toBe(0);

    // The browser focuses it and speaks its own message. The app must NOT add a
    // second one on top - that is the announcement stacking the audit warns about.
    expect(await focusedId(page)).toBe(DIAL);
    expect(await shownMessage(page)).toBe('');
  });
});

test.describe('an unusable saved value must not be restored', () => {
  /**
   * Seed localStorage before any page script runs, reproducing what a previous
   * session would have left behind.
   *
   * `braille_prefs_thickness_preset: 'custom'` is not decoration - it is what
   * makes this the real trap. Editing any preset-controlled dial makes
   * `detectCurrentPreset()` return 'custom' and persists it, and on the next load
   * `restoreThicknessPreset()` then returns early WITHOUT re-applying the preset.
   * Seed only the dial and the 0.4 preset would overwrite it on load, so the test
   * would pass whether or not the restore guard exists - green for the wrong
   * reason, which is the failure mode this suite has been bitten by before.
   */
  async function seedSavedDial(page: Page, key: string, value: string) {
    await page.addInitScript(([k, v]) => {
      try {
        localStorage.setItem(k, v);
        localStorage.setItem('braille_prefs_thickness_preset', 'custom');
        // NOT tidiness - without this the tests below cannot isolate what they
        // are testing. `cylinder_diameter_mm` SHIPS at 30.75 with min="10" and
        // step="0.1", which puts the step base at 10, so 30.75 is not a valid
        // step and the control is invalid from the shipped default alone. A
        // normal load hides it because the 0.4 preset overwrites the dial with
        // 30.8; with the preset standing aside, it is exposed. Pre-existing and
        // reported separately - changing either attribute is a public-parameter
        // decision, not a test's to make. Remove this line once that is settled.
        localStorage.setItem('braille_prefs_cylinder_diameter_mm', '30.8');
      } catch { /* private mode */ }
    }, [key, value]);
  }

  test('an out-of-range saved value is refused, reported, and Generate still works', async ({ page }) => {
    await seedSavedDial(page, `braille_prefs_${DIAL}`, '99');
    await openApp(page);

    // Premise check: the preset really did stand aside, so anything observed
    // below is the restore guard's doing and not the preset overwriting.
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_thickness_preset')))
      .toBe('custom');

    // The bad value must not have been applied, and what replaced it must be usable.
    const state = await page.evaluate((i) => {
      const el = document.getElementById(i) as HTMLInputElement;
      return { value: el.value, valid: el.validity.valid };
    }, DIAL);
    expect(state.value).not.toBe('99');
    expect(state.valid).toBe(true);

    // Refused, never SILENTLY refused: the user is told what was discarded.
    const notice = await shownMessage(page);
    expect(notice).toMatch(
      new RegExp(`^${DIAL_LABEL} 99 was out of range; reset to [0-9.]+\\.$`),
    );
    expect(await announced(page)).toBe(notice);

    // And the trap is gone - the button that was dead on every load now works.
    await armSubmitCounter(page);
    expect(await pressGenerate(page)).toBe(1);
  });

  test('a valid saved value is still restored untouched', async ({ page }) => {
    // 2.6 is inside the range and on-step: a perfectly ordinary saved setting,
    // and deliberately not the 2.5 the field ships with, so "restored" cannot be
    // confused with "fell back to the default". The guard must only ever refuse
    // what the form cannot accept - a legitimate value surviving is the whole
    // reason this is a guard and not a reset.
    await seedSavedDial(page, `braille_prefs_${DIAL}`, '2.6');
    await openApp(page);

    await expect(page.locator(`#${DIAL}`)).toHaveValue('2.6');
    expect(await shownMessage(page)).toBe('');
  });
});
