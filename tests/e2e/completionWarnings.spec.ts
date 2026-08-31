import { test, expect, type Page } from '@playwright/test';

/**
 * E2E regression tests for warnings named in the completion message (finding F-R).
 *
 * Found by Brennen's NVDA page-structure walkthrough on 2026-08-23. The live
 * warnings fired correctly while he typed - at 17:22:21 NVDA said *"Warning:
 * Line 1 needs 53 cells but 13 are available. Your text needs 5 rows but the
 * plate has 4"* - and then nothing between 17:23:44 and 17:24:13 mentioned any
 * problem. He heard *"Both cylinders are ready"*, saved `Cylinder_A_0.4_This
 * (2).stl` and `Cylinder_B_0.4_This.stl`, and the overflow was never resolved.
 *
 * The cause was structural, not a missed case: the live warning boxes are
 * display-only and NO generate or download path consulted any of them. The app
 * reports hard failures fine - the same run heard *"Cylinder A could not be
 * generated, so nothing was downloaded"* at 17:14:08 - but it had no concept of
 * "succeeded, and you were already warned".
 *
 * Brennen's decision (2026-08-23): **announce, do not block.** Generation still
 * proceeds; the completion message names what was outstanding. Nothing is taken
 * away from the user, and nobody downloads blind.
 *
 * Contracts pinned:
 *   1. A clean run's completion message is unchanged - byte for byte the
 *      signed-off sentence, with nothing appended.
 *   2. A run with an outstanding warning names it, in both the single-cylinder
 *      and the pair flow.
 *   3. `ds-gap-warning` is NEVER named, and this is deliberate rather than an
 *      oversight. When this file was written the shipped 0.4 preset tripped it
 *      permanently (nominal 0.4678 mm against a 0.50 mm reliable line) about a
 *      package recorded embossing clean, so naming it would have appended a
 *      caveat to every single double-sided run - which is how a warning becomes
 *      noise. The line is a provisional 0.45 as of 2026-08-23 and the default is
 *      quiet, so that reason has gone; the exclusion stays anyway, because
 *      Brennen's condition for adding it was a threshold that "fires only when
 *      something is actually wrong", and a provisional unmeasured number does
 *      not meet that bar. It joins the list when a print test sets the line from
 *      a measured failure. This test is what makes that a decision, not a drift.
 *
 * KNOWN LOCAL FLAKE, measured rather than assumed (2026-08-23). Every test here
 * drives a real STL build through two WASM workers, so under the ten parallel
 * workers a local `playwright test` uses, Firefox intermittently fails one of
 * them - the Manifold engine or liblouis not loading, or the debounced overflow
 * warning not rendering inside the assertion timeout. Two consecutive full-suite
 * runs failed one test each, with a different test and a different cause each
 * time. The same file run with `--workers=1 --repeat-each=2` passed **24 of 24**
 * across chromium, firefox and webkit. `playwright.config.ts` sets
 * `workers: process.env.CI ? 1 : undefined`, so CI already runs the stable
 * configuration; if you are running locally and see one of these fail, re-run
 * this file with `--workers=1` before believing it.
 */

/** The signed-off sentences. Neither may change; the suffix is appended after them. */
const SINGLE_READY = 'Your STL file is ready. Use the Download STL button to save it.';
// Signed off by Brennen 2026-08-25, replacing his 2026-08-18 sentence when the
// combined download became the primary offer.
const PAIR_READY = 'Both cylinders are ready. Use the Download Combined STL '
  + 'button below to save one file with both cylinders spaced for printing on '
  + 'one plate, or use the Download Cylinder A and Download Cylinder B buttons '
  + 'to save them separately.';

/** Long enough to overflow the default 13-cell row and 4-row plate several times over. */
const OVERFLOWING = "This a test of Front Side 1 I'll keep going until an error . noa";

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#indicator-mode-selection');
}

/**
 * The Manifold WASM engine sometimes fails to load under ten parallel workers -
 * a known flake class in this suite, and the reason
 * `tactileIndicator.spec.ts:152` failed once during item G. The page reports
 * *"Cylinder generation requires the Manifold 3D engine which failed to load"*
 * and generation is then terminally over, so a longer wait cannot help: the
 * page has to be reloaded. Both helpers below re-run `setUp` after a reload
 * rather than retrying a click into a dead engine.
 */
const MANIFOLD_MISSING = /Manifold 3D engine which failed to load|never became ready/;

/**
 * Press Translate to Braille and wait for the field to fill.
 *
 * Lifted from brailleField.spec.ts, for the same reason it exists there: the
 * liblouis worker loads asynchronously and the button reports "Liblouis worker
 * not initialized" if pressed too early - reliably on Firefox under load. A
 * full-suite run on 2026-08-23 got one row instead of four for exactly this,
 * which broke the truncation premise rather than the behaviour under test.
 */
/**
 * The Double-Sided item is a collapsible menu since 2026-08-31, so the toggle
 * inside is hidden until the disclosure opens it. State-aware: re-running a
 * setUp closure must never click an already-open menu shut.
 */
async function openDoubleSidedMenu(page: Page) {
  const toggle = page.locator('#double-sided-menu-toggle');
  if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
    await toggle.click();
  }
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
}

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

async function statusText(page: Page) {
  return (await page.locator('#a11y-status').textContent())?.trim() ?? '';
}

/** Generate one cylinder, recovering from a dead Manifold engine. */
async function generateSingle(page: Page, setUp: () => Promise<void>) {
  for (let attempt = 0; attempt < 4; attempt++) {
    if (attempt > 0) {
      await openApp(page);
      await setUp();
    }
    await page.locator('#action-btn').click();
    try {
      await page.waitForSelector('#download-stl-btn', { state: 'visible', timeout: 120_000 });
      return;
    } catch (error) {
      if (!MANIFOLD_MISSING.test(await statusText(page))) throw error;
    }
  }
  throw new Error('Manifold never loaded across four attempts');
}

/**
 * Mirrors doubleSided.spec.ts: the pair run can report a recoverable miss and
 * want another press. Extended here to reload when the engine itself is gone.
 */
async function generateBoth(page: Page, setUp: () => Promise<void>) {
  const status = page.locator('#pair-status');
  for (let attempt = 0; attempt < 6; attempt++) {
    if (attempt > 0 && MANIFOLD_MISSING.test(await statusText(page))) {
      await openApp(page);
      await setUp();
    }
    await page.locator('#generate-both-btn').click();
    try {
      await expect(status).toContainText('Both cylinders are ready', { timeout: 120_000 });
      return;
    } catch (error) {
      const text = ((await status.textContent()) ?? '') + ' ' + (await statusText(page));
      if (!/could not be generated/.test(text) && !MANIFOLD_MISSING.test(text)) throw error;
    }
    await page.waitForTimeout(1500);
  }
  throw new Error('Generate Both never reported a finished pair');
}

const visibleWarningIds = () => ['auto-overflow-warning', 'cylinder-overflow-warning',
  'ds-back-overflow-warning', 'tactile-gap-warning', 'ds-gap-warning']
  .filter((id) => {
    const box = document.getElementById(id);
    return !!box && box.getClientRects().length > 0;
  });

test.describe('Completion messages name outstanding warnings (F-R)', () => {
  // Every test here drives a real STL build. Under ten parallel workers a
  // Firefox generate can exceed two minutes - measured 2026-08-23, where all
  // three failed in the full suite and passed 3 of 3 in isolation at under 7
  // seconds each. Slow is not broken, so the wait is widened rather than the
  // assertion weakened. Matches doubleSided.spec.ts's heaviest test.
  test.describe.configure({ timeout: 300_000 });

  test('a clean run says exactly the signed-off sentence and nothing more', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);

    const setUp = async () => {
      await page.locator('#auto-text').fill('hi');
      await translateToBraille(page);
    };
    await setUp();

    // Nothing outstanding is the precondition, not an assumption.
    expect(await page.evaluate(visibleWarningIds)).toEqual([]);

    await generateSingle(page, setUp);

    await expect(page.locator('#a11y-status')).toHaveText(SINGLE_READY);
  });

  test('a single run with text that does not fit says so', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);

    const setUp = async () => {
      await page.locator('#auto-text').fill(OVERFLOWING);
      await page.waitForTimeout(900);
      await translateToBraille(page);
    };
    await setUp();

    // Auto-waiting: the warning is recomputed on a debounce, so a one-shot read
    // races it under load - that is what failed the full suite on 2026-08-23.
    await expect(page.locator('#auto-overflow-warning')).toBeVisible();

    await generateSingle(page, setUp);

    await expect(page.locator('#a11y-status')).toHaveText(
      `${SINGLE_READY} Warning still showing: your text does not fit the plate.`);
  });

  /**
   * The precise sequence Brennen ran, and the reason his files downloaded at all.
   *
   * Raw overflowing text does NOT reach a download - `silentTruncation.spec.ts`
   * guards that, and the pair run answers *"Cylinder A could not be generated, so
   * nothing was downloaded"*. He pressed **Translate to Braille** first (17:22:34),
   * and that path behaves differently: the translation is truncated to what fits -
   * measured here as 4 rows of 10/12/13/12 cells, with the fifth row's content
   * simply gone - and a filled braille field is then used exactly as written, so
   * generation is legitimate and succeeds. The source text's overflow warning stays
   * on screen throughout.
   *
   * So the plate embossed fine and was missing the tail of his text, and the only
   * thing that ever said otherwise was a warning box he had scrolled past.
   */
  test('the pair run names it too, and never names the crowding warning', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);

    const setUp = async () => {
      await page.locator('#auto-text').fill(OVERFLOWING);
      await page.waitForTimeout(900);
      await translateToBraille(page);
      await openDoubleSidedMenu(page);
      await page.locator('#double_sided_enabled').check();
      await page.locator('#back-text').fill('def');
      await page.waitForTimeout(900);
    };
    await setUp();

    // The truncation itself, asserted so the premise of this test cannot rot.
    const rows = await page.locator('#braille-unicode').inputValue();
    expect(rows.split('\n').length).toBe(4);

    await expect(page.locator('#auto-overflow-warning')).toBeVisible();
    // The crowding warning used to be permanently up here: the 0.4 preset sits
    // at 0.4678 mm nominal against what was a 0.50 mm reliable line, so every
    // double-sided run carried a printability caveat about a package recorded
    // embossing clean. That line is a provisional 0.45 since 2026-08-23, so the
    // default is quiet - which is the whole point of the change, and is pinned
    // here rather than left to be noticed.
    await expect(page.locator('#ds-gap-warning')).not.toBeVisible();

    await generateBoth(page, setUp);

    const status = (await page.locator('#pair-status').textContent())?.trim() ?? '';
    expect(status).toBe(`${PAIR_READY} Warning still showing: your text does not fit the plate.`);
    expect(status).not.toContain('too close');
    expect(status).not.toContain('crowd');
  });

  /**
   * The other half of the same story, pinned so the change above cannot be read
   * as having relaxed anything: untranslated overflowing text still refuses to
   * build. Announcing outstanding warnings is additive - it does not soften a
   * single existing gate.
   */
  test('untranslated overflowing text still refuses to build the pair', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);

    await page.locator('#auto-text').fill(OVERFLOWING);
    await openDoubleSidedMenu(page);
    await page.locator('#double_sided_enabled').check();
    await page.locator('#back-text').fill('def');
    await page.waitForTimeout(900);

    await page.locator('#generate-both-btn').click();
    await expect(page.locator('#pair-status'))
      .toContainText('could not be generated', { timeout: 240_000 });
    await expect(page.locator('#pair-downloads')).not.toBeVisible();
  });
});
