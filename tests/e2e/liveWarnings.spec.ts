/**
 * E2E regression tests for live warning refresh.
 *
 * Every warning on the page used to be wired to its own hand-picked list of
 * inputs, and the lists had gaps: raising the braille cell dial never re-ran the
 * manual-mode overflow check, and the blocking notice over the 3D preview was
 * only ever cleared by the next Generate. A user who corrected the problem was
 * left staring at the complaint, with no signal that the fix had landed.
 *
 * The contract pinned here: a warning describes the settings as they are right
 * now, so any change to the form re-evaluates it.
 *
 * @see docs/specifications/BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

// No contraction in any braille code covers a run of q, so this is 16 cells in
// every table the app ships - well past the default 13-cell row.
const SIXTEEN_CELLS_OF_TEXT = 'qqqqqqqqqqqqqqqq';
// 14 braille cells against the same 13-cell row.
const FOURTEEN_BRAILLE_CELLS = '\u2801'.repeat(14);

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#braille-unicode');
  await page.locator('input[name="placement_mode"][value="manual"]').check();
  await expect(page.locator('#line1')).toBeVisible();
}

/** Reveal Expert Mode and one of its submenus (setup, not the feature under test). */
async function revealExpertPanel(page: Page, panelId: string) {
  await page.evaluate((id) => {
    const expert = document.getElementById('expert-settings');
    if (expert) expert.style.display = 'block';
    const panel = document.getElementById(id);
    if (panel) {
      panel.style.display = 'block';
      panel.hidden = false;
    }
  }, panelId);
  await page.waitForSelector(`#${panelId}`, { state: 'visible' });
}

/**
 * Wait for the manual-mode overflow warning. The check is a series of async
 * liblouis calls that fail silently while the worker warms up (reliably slow on
 * Firefox), so re-trigger the debounced check until it lands.
 */
async function waitForCylinderOverflowWarning(page: Page) {
  const warning = page.locator('#cylinder-overflow-warning');
  for (let attempt = 0; attempt < 20; attempt++) {
    await page.locator('#line1').dispatchEvent('input');
    try {
      await expect(warning).toBeVisible({ timeout: 3000 });
      return;
    } catch {
      // Worker likely not ready yet; retry
    }
  }
  throw new Error('The cylinder overflow warning never appeared');
}

test.describe('Live warning refresh', () => {
  // Same rationale as brailleField.spec.ts: WebKit on Linux CI parses this page
  // (large inline script plus vendored workers) noticeably slower.
  test.describe.configure({ timeout: 120_000 });

  test('raising the cell dial clears the overflow warning without touching the text', async ({ page }) => {
    await openApp(page);
    await revealExpertPanel(page, 'expert-panel-dimensions');
    await revealExpertPanel(page, 'expert-panel-spacing');

    await expect(page.locator('#grid_columns')).toHaveValue('13');
    await page.locator('#line1').fill(SIXTEEN_CELLS_OF_TEXT);
    await waitForCylinderOverflowWarning(page);

    // The dial is the other half of the comparison, so raising it has to retire
    // the warning. It used to update only the seam-gap check.
    await page.locator('#grid_columns').fill('20');
    await expect(page.locator('#cylinder-overflow-warning')).toBeHidden({ timeout: 10_000 });
    await expect(page.locator('#line1')).toHaveValue(SIXTEEN_CELLS_OF_TEXT);
  });

  test('the braille field reports an over-long row while typing, and the dial clears it', async ({ page }) => {
    await openApp(page);
    await revealExpertPanel(page, 'expert-panel-spacing');

    const status = page.locator('#braille-unicode-status');
    await page.locator('#braille-unicode').fill(FOURTEEN_BRAILLE_CELLS);
    await expect(status).toContainText('the maximum is 13');

    await page.locator('#grid_columns').fill('14');
    await expect(status).toContainText('Edited');
    await expect(status).not.toContainText('the maximum is');
  });

  test('a blocking generate error clears as soon as the form changes', async ({ page }) => {
    await openApp(page);

    // Plain letters in the braille field block generation without needing
    // liblouis or the Manifold worker, so this is the error the test can rely on.
    const field = page.locator('#braille-unicode');
    await field.fill('hello');
    await page.locator('#action-btn').click();

    const errorText = page.locator('#error-text');
    await expect(errorText).toContainText('not a braille character', { timeout: 15_000 });

    // The complaint stops being true the moment the field changes. Asserted on
    // the text rather than the container: a browser missing WebGL keeps the
    // overlay on screen for its own capability warning, which is not stale.
    await field.fill('\u2813\u2811\u2807\u2807\u2815');
    await expect(errorText).toHaveText('');
  });
});
