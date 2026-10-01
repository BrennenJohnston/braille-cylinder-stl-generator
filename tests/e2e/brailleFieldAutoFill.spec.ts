/**
 * E2E tests for the Braille (Unicode) field filling on Generate (Brennen,
 * 2026-09-28) and emptying when a translation setting changes.
 *
 * Before this date the field stayed empty unless Translate to Braille was
 * pressed, so a user who went straight to Generate never saw the cells that
 * went onto the cylinder. Now every Generate writes the translation it is
 * about to emboss into the field as its pristine mirror - front and, on a
 * double-sided run, back - announced from the field's own live region, as the
 * button's fill is (Brennen's choice, 2026-09-28). The field keeps
 * its authority: the next Generate embosses the mirror exactly as written,
 * and its request is padded to the row count so consecutive requests are
 * byte-identical. So that the mirror is always the translation that would
 * be embossed, it is emptied when an EFFECTIVE translation setting changes
 * (the cells a row holds, rows, language and per-row tables, capitals,
 * number signs, placement mode - a fingerprint, not "which control fired"),
 * exactly as it is when the text changes; a hand-edited field is never
 * touched, and a control that changes nothing effective leaves it alone.
 *
 * @see docs/specifications/BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md section 6.3
 */

import { expect, test, type Page } from '@playwright/test';
import { selectCylinders } from './helpers/cylinders';

// S-BF1, signed by Brennen 2026-09-28 (as drafted).
const S_BF1_SETTING_CLEARED = 'Cleared because a translation setting changed — press Translate to Braille to refresh';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
  await selectCylinders(page, 'positive');
}

/** Capture the /geometry_spec request body and abort it: no CSG run needed. */
async function interceptGeometrySpec(page: Page) {
  const state: { bodies: Array<Record<string, unknown>>; called: number } = { bodies: [], called: 0 };
  await page.route('**/geometry_spec', async (route) => {
    state.called += 1;
    try {
      state.bodies.push(route.request().postDataJSON());
    } catch {
      state.bodies.push({});
    }
    await route.abort();
  });
  return state;
}

// What Generate reports while a worker is still starting. A Generate pressed
// before the liblouis worker is up fails its translation and says "Translation
// failed for the following lines", not "not initialized" - reliably on Firefox,
// whose workers start slower. The other generate helpers (doubleSided,
// gearRollers, cylindersToGenerate) already retry on it; this one did not, so
// it failed 2 to 6 of its 6 tests per Firefox run on Windows (2026-09-30).
const TRANSIENT_ERRORS = /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

async function generate(page: Page, state: { called: number }, n: number) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 3000 && state.called < n; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.called >= n) return;
    const notice = await page.locator('#error-message').getAttribute('class');
    const isInfo = notice?.includes('info') ?? false;
    const error = await page.locator('#error-text').textContent();
    if (error && !isInfo && !TRANSIENT_ERRORS.test(error)) {
      throw new Error(`Generation was blocked before reaching /geometry_spec: ${error}`);
    }
    lastError = error || lastError;
    await page.waitForTimeout(1000);
  }
  throw new Error(`Generation never reached /geometry_spec; last error: ${lastError}`);
}

function trimTrailingEmpty(lines: string[]) {
  const out = [...lines];
  while (out.length && !out[out.length - 1].trim()) out.pop();
  return out;
}

test.describe('Braille field fills on Generate', () => {
  test.describe.configure({ timeout: 120_000 });

  test('Generate shows the translated rows in the field without Translate to Braille, and says so', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('hello world');
    await expect(page.locator('#braille-unicode')).toHaveValue('');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);

    const sent = spec.bodies[0].lines as string[];
    expect(sent.some((l) => l.trim())).toBe(true);
    await expect(page.locator('#braille-unicode')).toHaveValue(trimTrailingEmpty(sent).join('\n'));
    await expect(page.locator('#braille-unicode-status')).toContainText('Filled from translation');
    // Announced from the field's own live region, with the button's sentence.
    await expect(page.locator('#braille-unicode-live')).toHaveText('Braille field updated from translation.');
  });

  test('manual placement fills one row per line', async ({ page }) => {
    await openApp(page);
    await page.locator('input[name="placement_mode"][value="manual"]').check();
    await page.locator('#line1').fill('hello');
    await page.locator('#line2').fill('world');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);

    const sent = spec.bodies[0].lines as string[];
    expect(sent[0].trim()).not.toBe('');
    expect(sent[1].trim()).not.toBe('');
    await expect(page.locator('#braille-unicode')).toHaveValue(`${sent[0]}\n${sent[1]}`);
  });

  test('a double-sided run fills the back field too', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await page.locator('#auto-text').fill('abc');
    await page.locator('#back-text').fill('def');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);

    const backSent = spec.bodies[0].back_lines as string[];
    expect(backSent.some((l) => l.trim())).toBe(true);
    await expect(page.locator('#back-braille-unicode')).toHaveValue(trimTrailingEmpty(backSent).join('\n'));
    await expect(page.locator('#back-braille-unicode-status')).toContainText('Filled from translation');
  });

  test('a translation setting change empties a pristine field and says why; a hand-edited field stays', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('hello world');
    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    const field = page.locator('#braille-unicode');
    await expect(field).not.toHaveValue('');

    // A different language table changes what the text translates to.
    const table = page.locator('#language-table');
    const options = await table.locator('option').evaluateAll((els) => els.map((o) => (o as HTMLOptionElement).value));
    const current = await table.inputValue();
    const other = options.find((v) => v && v !== current);
    expect(other, 'a second language table to switch to').toBeTruthy();
    await table.selectOption(other!);
    await expect(field).toHaveValue('');
    await expect(page.locator('#braille-unicode-status')).toHaveText(S_BF1_SETTING_CLEARED);

    // Refilled by the next Generate, then emptied again by a cell-count change.
    await generate(page, spec, 2);
    await expect(field).not.toHaveValue('');
    await page.evaluate(() => {
      const el = document.getElementById('grid_columns') as HTMLInputElement;
      el.value = '12';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await expect(field).toHaveValue('');

    // A hand-edited field outranks every setting change.
    await field.fill('⠓⠑');
    await expect(page.locator('#braille-unicode-status')).toContainText('Edited');
    await table.selectOption(current);
    await expect(field).toHaveValue('⠓⠑');
  });

  test('a second Generate sends the same request as the first: the mirror is embossed as written, padded to the rows', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('hello world');
    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    await expect(page.locator('#braille-unicode')).not.toHaveValue('');
    await generate(page, spec, 2);
    expect(spec.bodies[1]).toEqual(spec.bodies[0]);
    // ...while a hand-edited field IS the request.
    await page.locator('#braille-unicode').fill('⠓⠑');
    await generate(page, spec, 3);
    expect((spec.bodies[2].lines as string[])[0]).toBe('⠓⠑');
  });

  test('a control that changes nothing effective leaves the filled field alone', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('hello');
    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    const before = await page.locator('#braille-unicode').inputValue();
    expect(before).not.toBe('');
    // A dial that does not change the translation...
    await page.evaluate(() => {
      const el = document.getElementById('braille_x_adjust') as HTMLInputElement;
      el.value = '-1';
      el.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await expect(page.locator('#braille-unicode')).toHaveValue(before);
    // ...and the double-sided lock moving the style to tactile at the same
    // cell count (Brennen's translate-then-choose-double-sided flow).
    await page.locator('#card_sides_double').check();
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();
    await expect(page.locator('#braille-unicode')).toHaveValue(before);
  });
});
