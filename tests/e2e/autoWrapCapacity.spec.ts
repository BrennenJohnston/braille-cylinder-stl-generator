/**
 * E2E regression tests for auto-placement capacity and wrapping.
 *
 * Guards the bug where a 4-line business card was measured as one continuous
 * stream: the overflow warning translated the whole textarea as a single
 * string (counting the newline separators as space cells) and compared it to
 * rows x columns, reporting an overflow for text that actually fits row by
 * row. The wrap itself also collapsed user newlines, gluing independent lines
 * together.
 *
 * The contract pinned here:
 * - User newlines are hard row breaks (one input line starts a new row).
 * - The warning is per-row and wrap-based: it names the input lines that
 *   cannot fit a single row and the total rows needed, or stays silent when
 *   the text fits.
 * - Capitalization defaults to Enabled; disabling it in Expert Mode saves the
 *   capital-indicator cells, which is exactly what makes this sample fit.
 *
 * Sample text (tactile mode, 13 text cells, 4 rows):
 * - caps disabled: rows need 12/12/13/13 cells - fits, no warning
 * - caps enabled (default): lines 1-2 exceed 13 cells, 6 rows needed - warn
 *
 * @see docs/specifications/BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

const SAMPLE_TEXT = 'Joshua Miele\nCAOS Founder\njam@caos.org\n510.229.7918';

/** Load the app and wait for the inline init script to settle. */
async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#auto-text');
  // The markup ships with Auto Placement checked; assert rather than assume.
  await expect(page.locator('input[name="placement_mode"][value="auto"]')).toBeChecked();
}

/** Reveal Expert Mode and the Translation Options submenu (setup, not the feature under test). */
async function revealTranslationOptions(page: Page) {
  await page.evaluate(() => {
    const panel = document.getElementById('expert-settings');
    if (panel) panel.style.display = 'block';
    const translation = document.getElementById('expert-panel-translation');
    if (translation) {
      translation.style.display = 'block';
      translation.hidden = false;
    }
  });
  await page.waitForSelector('#expert-panel-translation', { state: 'visible' });
}

/**
 * Wait for the auto overflow warning to appear.
 *
 * The warning is computed by async liblouis calls that fail silently while
 * the worker is still warming up (reliably slow on Firefox), so re-trigger
 * the debounced check until it lands rather than assuming a warm-up time.
 */
async function waitForAutoOverflowWarning(page: Page) {
  const warning = page.locator('#auto-overflow-warning');
  for (let attempt = 0; attempt < 20; attempt++) {
    await page.locator('#auto-text').dispatchEvent('input');
    try {
      await expect(warning).toBeVisible({ timeout: 3000 });
      return;
    } catch {
      // Worker likely not ready yet; retry
    }
  }
  throw new Error('The auto overflow warning never appeared');
}

/**
 * Press Translate to Braille and wait for the field to fill. Same retry
 * rationale as above: the button reports "Liblouis worker not initialized"
 * when pressed too early.
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

test.describe('Auto-placement capacity and wrapping', () => {
  test.describe.configure({ timeout: 120_000 });

  test('capitalization defaults to Enabled', async ({ page }) => {
    await openApp(page);
    await expect(page.locator('#capitalize_enabled')).toBeChecked();
    await expect(page.locator('#capitalize_disabled')).not.toBeChecked();
  });

  test('business card sample: per-line warning with caps, fits without', async ({ page }) => {
    await openApp(page);

    // Tactile seam arrow: no marker columns, dial normalizes to 13 text cells
    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    await expect(page.locator('#grid_columns')).toHaveValue('13');

    await page.locator('#auto-text').fill(SAMPLE_TEXT);

    // Caps enabled (the default): the capital indicators push lines 1-2 past
    // 13 cells, so the text needs 6 rows on a 4-row plate. The warning must
    // name the specific lines instead of a flat whole-string cell count.
    await waitForAutoOverflowWarning(page);
    const message = page.locator('#auto-overflow-message');
    await expect(message).toContainText('Line 1 ("Joshua Miele")');
    await expect(message).toContainText('Line 2 ("CAOS Founder")');
    await expect(message).toContainText(/needs \d+ rows but the plate has 4/);

    // Disabling capitalization frees the indicator cells: 12/12/13/13 fits
    // 4 x 13 exactly, so the warning must clear - the original bug reported
    // "exceeds by 6" here because it counted the whole string plus newlines.
    await revealTranslationOptions(page);
    await page.locator('#capitalize_disabled').check();
    await expect(page.locator('#auto-overflow-warning')).toBeHidden({ timeout: 10_000 });

    // User newlines are hard row breaks: one braille row per input line
    await translateToBraille(page);
    const brailleLines = (await page.locator('#braille-unicode').inputValue()).split('\n');
    expect(brailleLines).toHaveLength(4);
    for (const line of brailleLines) {
      expect(line.length).toBeGreaterThan(0);
      expect(line.length).toBeLessThanOrEqual(13);
    }
  });
});
