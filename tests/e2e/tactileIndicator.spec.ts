/**
 * E2E tests for the Row Indicator Style control (tactile seam arrow).
 *
 * Tactile mode is the blind-user alignment feature ported from the OpenSCAD
 * version: one raised arrow per row on the embossing plate, a matching recess on
 * the counter plate, both centred in the seam gap. It removes the marker cells,
 * which changes text capacity - so the payload sent to /geometry_spec is what
 * these tests assert on.
 *
 * @see docs/specifications/RECESS_INDICATOR_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#indicator-mode-selection');
}

/** Capture the /geometry_spec payload, aborting the request so no CSG runs. */
async function interceptGeometrySpec(page: Page) {
  const state: { body: Record<string, unknown> | null; called: boolean } = { body: null, called: false };
  await page.route('**/geometry_spec', async (route) => {
    state.called = true;
    try {
      state.body = route.request().postDataJSON();
    } catch {
      state.body = null;
    }
    await route.abort();
  });
  return state;
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

    const error = await page.locator('#error-text').textContent();
    if (error && !/Manifold 3D engine/.test(error)) {
      throw new Error(`Generation was blocked before reaching /geometry_spec: ${error}`);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('The Manifold worker never became ready');
}

test.describe('Row Indicator Style', () => {
  test.describe.configure({ timeout: 120_000 });

  test('defaults to visual markers and reserves two marker columns', async ({ page }) => {
    await openApp(page);

    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeChecked();
    await expect(page.locator('#grid_columns')).toHaveValue('13');

    const spec = await interceptGeometrySpec(page);
    await page.locator('#braille-unicode').fill('\u2801\u2803');
    await generate(page, spec);

    const settings = spec.body?.settings as Record<string, unknown>;
    expect(settings.indicator_mode).toBe('visual');
    // Dial shows 13 text cells; +2 marker columns for the letter and triangle
    expect(settings.grid_columns).toBe('15');
  });

  test('tactile mode frees the marker columns and sends the tactile parameters', async ({ page }) => {
    await openApp(page);

    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    // The dial normalizes to the recommended tactile capacity
    await expect(page.locator('#grid_columns')).toHaveValue('13');

    const spec = await interceptGeometrySpec(page);
    await page.locator('#braille-unicode').fill('\u2801'.repeat(13));
    await generate(page, spec);

    const settings = spec.body?.settings as Record<string, unknown>;
    expect(settings.indicator_mode).toBe('tactile');
    // No marker columns: the dial value passes through untouched
    expect(settings.grid_columns).toBe('13');
    // Compared numerically: the Card Thickness preset owns these dials, so the
    // string the input happens to hold ("4" vs "4.0") is not part of the contract.
    expect(Number(settings.tactile_indicator_width)).toBe(4.0);
    expect(Number(settings.tactile_indicator_length)).toBe(10.0);
    expect(Number(settings.tactile_indicator_raise)).toBe(0.5);
    expect(Number(settings.tactile_recess_clearance)).toBe(0.2);
    expect(Number(settings.tactile_recess_extra_depth)).toBe(0.2);
  });

  test('tactile mode accepts a 14-cell row that visual mode rejects', async ({ page }) => {
    await openApp(page);

    const fourteenCells = '\u2801'.repeat(14);

    // Visual mode: 13 cells available, so 14 is blocked
    await page.locator('#braille-unicode').fill(fourteenCells);
    await page.locator('#action-btn').click();
    await expect(page.locator('#error-text')).toContainText('the maximum is 13', { timeout: 15_000 });

    // Tactile mode recommends 13, but 14 still fits the seam-gap arithmetic, so
    // raising the dial by hand is allowed and every column is then text.
    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    await page.evaluate(() => {
      const panel = document.getElementById('expert-settings');
      if (panel) panel.style.display = 'block';
      const spacing = document.getElementById('expert-panel-spacing');
      if (spacing) { spacing.style.display = 'block'; spacing.hidden = false; }
    });
    await page.locator('#grid_columns').fill('14');
    await expect(page.locator('#tactile-gap-warning')).toBeHidden();

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);

    expect((spec.body?.lines as string[])[0]).toBe(fourteenCells);
    expect((spec.body?.settings as Record<string, unknown>).grid_columns).toBe('14');
  });

  test('warns when the seam gap can no longer hold the indicator', async ({ page }) => {
    await openApp(page);

    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    const warning = page.locator('#tactile-gap-warning');
    await expect(warning).toBeHidden();

    // Reveal Expert Mode so the braille cell dial is reachable
    await page.evaluate(() => {
      const panel = document.getElementById('expert-settings');
      if (panel) panel.style.display = 'block';
      const spacing = document.getElementById('expert-panel-spacing');
      if (spacing) { spacing.style.display = 'block'; spacing.hidden = false; }
    });

    // 16 cells at 6.5 mm leaves no gap at all on the default 30.75 mm cylinder
    await page.locator('#grid_columns').fill('16');
    await expect(warning).toBeVisible();
    await expect(page.locator('#tactile-gap-message')).toContainText('seam gap');

    // Back to a layout that fits
    await page.locator('#grid_columns').fill('13');
    await expect(warning).toBeHidden();
  });

  test('tactile dimensions are hidden until tactile mode is selected', async ({ page }) => {
    await openApp(page);

    // The dials live in their own Expert Mode submenu, whose whole accordion is
    // hidden while the visual markers are selected.
    await page.evaluate(() => {
      const panel = document.getElementById('expert-settings');
      if (panel) panel.style.display = 'block';
      const tactile = document.getElementById('expert-panel-tactile');
      if (tactile) { tactile.style.display = 'block'; tactile.hidden = false; }
    });

    const dimensions = page.locator('#tactile-indicator-dimensions');
    await expect(dimensions).toBeHidden();

    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    await expect(dimensions).toBeVisible();

    await page.locator('input[name="indicator_mode"][value="visual"]').check();
    await expect(dimensions).toBeHidden();
  });
});
