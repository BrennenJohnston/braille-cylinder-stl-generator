/**
 * E2E tests for the editable Unicode braille field.
 *
 * The field's contract is the safety-critical part: whenever it holds content,
 * those exact cells are what get embossed - no liblouis pass, no re-wrapping.
 * These tests pin that contract by intercepting the /geometry_spec request and
 * asserting on the braille lines actually sent.
 *
 * The phone-number case is the one that prompted the feature: 206-543-4779 is
 * correctly 15 cells with three number signs under UEB (a hyphen ends numeric
 * mode), which does not fit any row at the defaults. Editing it down to the 13
 * cells that fit a default row must be honoured verbatim.
 *
 * @see docs/specifications/BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

const NUMBER_SIGN = '\u283C';
// 206.543.4779 in UEB: one number sign, periods keeping numeric mode. 13 cells.
// Cells: ⠼ 2 0 6 . 5 4 3 . 4 7 7 9
const PHONE_13_CELLS =
  '\u283C\u2803\u281A\u280B\u2832\u2811\u2819\u2809\u2832\u2819\u281B\u281B\u280A';

/** Load the app and wait for the inline init script and liblouis worker to settle. */
async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#braille-unicode');
  // Manual placement exposes the per-row English inputs. Selected explicitly
  // because the markup ships with Auto checked.
  await page.locator('input[name="placement_mode"][value="manual"]').check();
  await expect(page.locator('#line1')).toBeVisible();
}

/**
 * Capture the braille lines and indicator source lines sent to /geometry_spec.
 * The request is aborted so the test never waits on Manifold WASM or a full
 * CSG run.
 */
async function interceptGeometrySpec(page: Page) {
  const state: { lines: string[] | null; originalLines: string[] | null; called: boolean } =
    { lines: null, originalLines: null, called: false };
  await page.route('**/geometry_spec', async (route) => {
    state.called = true;
    try {
      const body = route.request().postDataJSON();
      state.lines = body?.lines ?? null;
      state.originalLines = body?.original_lines ?? null;
    } catch {
      state.lines = null;
      state.originalLines = null;
    }
    await route.abort();
  });
  return state;
}

/**
 * Press Translate to Braille and wait for the field to fill.
 *
 * The liblouis worker also loads asynchronously and the button reports
 * "Liblouis worker not initialized" if pressed too early — again reliably on
 * Firefox. Retry rather than assume a fixed warm-up time.
 */
async function translateToBraille(page: Page) {
  const field = page.locator('#braille-unicode');
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#translate-to-braille-btn').click();
    for (let waited = 0; waited < 4000; waited += 200) {
      if ((await field.inputValue()) !== '') return;
      await page.waitForTimeout(200);
    }
    const status = await page.locator('#braille-unicode-status').textContent();
    if (status && !/[Ll]iblouis|not initialized|unavailable/.test(status)) {
      throw new Error(`Translate to Braille reported: ${status}`);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('The liblouis worker never became ready');
}

/**
 * Click Generate and wait for the request to reach /geometry_spec.
 *
 * The Manifold worker signals readiness asynchronously and cylinder generation
 * fails fast with "requires the Manifold 3D engine" when it is not ready yet —
 * reliably so on Firefox, which is slower to spin up the module worker. The app
 * tells the user to try again in exactly that case, so the test does the same.
 * Any other error is a real failure and is surfaced immediately.
 */
async function generate(page: Page, state: { called: boolean }) {
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 3000 && !state.called; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.called) return;

    // #error-text is also where the app puts INFORMATIONAL notices - the card
    // thickness preset's "All parameters updated." lands there when a preset is clicked (before 2026-08-22, also on load), with
    // class `info` on the wrapper. Treating that as a blocking error turns a
    // notice into a spurious failure, so only fail when it is not marked info.
    const notice = await page.locator('#error-message').getAttribute('class');
    const isInfo = notice?.includes('info') ?? false;
    const error = await page.locator('#error-text').textContent();
    if (error && !isInfo && !/Manifold 3D engine/.test(error)) {
      throw new Error(`Generation was blocked before reaching /geometry_spec: ${error}`);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('The Manifold worker never became ready');
}

/**
 * Fill the Braille (Unicode) field and prove the text landed.
 *
 * Under full-suite parallelism a single fill() on this textarea does not always
 * take - measured as an intermittent "Please enter text in at least one line"
 * from generate(). It is NOT the app clearing the field: instrumenting the
 * element's value setter to record every write and its stack caught a run that
 * ended empty with ZERO writes recorded, so nothing in page script touched it.
 * The value simply never arrived.
 *
 * Re-filling is therefore input reliability, not a retry of anything under
 * test; every assertion in these specs stays strict, and a field that refuses
 * the text fails with a named message instead of a confusing downstream one.
 */
async function fillBraille(page: Page, text: string) {
  const field = page.locator('#braille-unicode');
  for (let attempt = 0; attempt < 5; attempt++) {
    await field.fill(text);
    if ((await field.inputValue()) === text) return;
  }
  throw new Error('the Braille (Unicode) field never accepted its text after 5 fills');
}

test.describe('Editable Unicode braille field', () => {
  // Same rationale as silentTruncation.spec.ts: WebKit on Linux CI parses this
  // page (large inline script plus vendored workers) noticeably slower.
  test.describe.configure({ timeout: 120_000 });

  test('translates a hyphenated phone number to 15 cells with three number signs', async ({ page }) => {
    await openApp(page);

    await page.locator('#line1').fill('206-543-4779');
    await translateToBraille(page);

    // Correct UEB, not a bug: a hyphen ends numeric mode, so the sign repeats
    // for each group and the number no longer fits a 13-cell row.
    const translated = (await page.locator('#braille-unicode').inputValue()).split('\n')[0];
    expect(translated.length).toBe(15);
    expect([...translated].filter((c) => c === NUMBER_SIGN)).toHaveLength(3);
  });

  test('sends hand-edited cells verbatim to /geometry_spec', async ({ page }) => {
    await openApp(page);

    // The default visual row holds 13 text cells, which is exactly what the
    // hand-edited phone number needs.
    await expect(page.locator('#grid_columns')).toHaveValue('13');

    await page.locator('#line1').fill('206-543-4779');
    await translateToBraille(page);

    // Edit the 15-cell result down to the 13 cells that fit a default row.
    const field = page.locator('#braille-unicode');
    await fillBraille(page, PHONE_13_CELLS);
    await expect(page.locator('#braille-unicode-status')).toContainText('Edited');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);

    expect(spec.lines?.[0]).toBe(PHONE_13_CELLS);
  });

  test('uses pasted braille verbatim with the English inputs left empty', async ({ page }) => {
    await openApp(page);

    const pasted = '\u2813\u2811\u2807\u2807\u2815';  // hello
    await fillBraille(page, pasted);

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);

    expect(spec.lines?.[0]).toBe(pasted);
    // No English source: the backend must get null so it falls back to the
    // square placeholder instead of inventing an indicator letter.
    expect(spec.originalLines).toBeNull();
  });

  test('keeps the English lines for indicator letters when the braille field is filled', async ({ page }) => {
    await openApp(page);

    // The guided workflow: type English, press Translate to Braille, generate.
    // The braille field wins for the embossed cells, but the indicator letter
    // for each row must still come from the English source — this used to be
    // nulled out, degrading every row's letter to a blank rectangle.
    await page.locator('#line1').fill('hello');
    await translateToBraille(page);

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);

    expect(await page.locator('#braille-unicode').inputValue()).not.toBe('');
    expect(spec.originalLines?.[0]).toBe('hello');
  });

  test('blocks generation when the field contains non-braille characters', async ({ page }) => {
    await openApp(page);

    const spec = await interceptGeometrySpec(page);
    await fillBraille(page, 'hello');
    await page.locator('#action-btn').click();

    await expect(page.locator('#error-text')).toContainText('not a braille character', { timeout: 15_000 });
    expect(spec.called).toBe(false);
  });

  test('blocks generation when a field line is longer than the available cells', async ({ page }) => {
    await openApp(page);

    const spec = await interceptGeometrySpec(page);
    // 14 cells against the default 13-text-cell row
    await fillBraille(page, '\u2801'.repeat(14));
    await page.locator('#action-btn').click();

    await expect(page.locator('#error-text')).toContainText('the maximum is 13', { timeout: 15_000 });
    expect(spec.called).toBe(false);
  });

  test('clears a pristine field when the English text changes, but keeps hand-edits', async ({ page }) => {
    await openApp(page);

    await page.locator('#line1').fill('hello');
    await translateToBraille(page);

    const field = page.locator('#braille-unicode');

    // Pristine: the field only mirrors the translation, so it must not go stale
    await page.locator('#line1').fill('world');
    await expect(field).toHaveValue('');

    // Dirty: a hand-edit outranks the English inputs
    await fillBraille(page, '\u2801\u2803');
    await page.locator('#line1').fill('something else entirely');
    await expect(field).toHaveValue('\u2801\u2803');
  });

  test('back-translates pasted braille into the English inputs', async ({ page }) => {
    await openApp(page);

    // hello, in uncontracted UEB: h e l l o
    await fillBraille(page, '\u2813\u2811\u2807\u2807\u2815');

    // Same warm-up problem as Translate to Braille: the worker loads async.
    const line1 = page.locator('#line1');
    for (let attempt = 0; attempt < 15; attempt++) {
      await page.locator('#translate-to-text-btn').click();
      for (let waited = 0; waited < 4000; waited += 200) {
        if ((await line1.inputValue()) !== '') break;
        await page.waitForTimeout(200);
      }
      if ((await line1.inputValue()) !== '') break;
      await page.waitForTimeout(1000);
    }

    await expect(line1).toHaveValue('hello');
    // The braille stays untouched: it is still what gets embossed
    await expect(page.locator('#braille-unicode')).toHaveValue('\u2813\u2811\u2807\u2807\u2815');
  });
});
