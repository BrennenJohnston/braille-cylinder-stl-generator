/**
 * E2E tests for "Cylinders to Generate" and the one-Generate / one-Download
 * footer (2026-09-20 programme, sub-plan E; decisions D-8, D-9, D-10).
 *
 * Since 2026-09-21 Generate STL builds BOTH cylinders by default and Download
 * STL saves one combined file with both spaced for one print plate. Which
 * cylinders to build is an Expert Mode choice - the first submenu, "Cylinders
 * to Generate" - so a single cylinder is still one press away for anyone who
 * wants it. The filenames never changed (D-10): the training videos show them.
 *
 * Strings S-E1..S-E6 were signed by Brennen on 2026-09-21; the pins here move only with
 * his sign-off.
 *
 * @see docs/specifications/STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import { selectCylinders, selectedCylinders } from './helpers/cylinders';

// S-E5 (signed 2026-09-21; 2026-09-20 programme, sub-plan E).
const BOTH_READY =
  'Both cylinders are ready. Use the Download STL button to save one file with both cylinders spaced for printing on one plate.';
const SINGLE_READY = 'Your STL file is ready. Use the Download STL button to save it.';

const TRANSIENT_ERRORS = /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
}

/** Record every /geometry_spec REQUEST body without interfering with the run. */
function watchGeometrySpecRequests(page: Page) {
  const state: { bodies: Array<Record<string, unknown> | null> } = { bodies: [] };
  page.on('request', (request) => {
    if (!request.url().includes('/geometry_spec')) return;
    try {
      state.bodies.push(request.postDataJSON());
    } catch {
      state.bodies.push(null);
    }
  });
  return state;
}

/**
 * Press Generate and wait for the pair to finish. The first press can land
 * before liblouis or the Manifold worker is ready, which aborts the run and
 * says so in #pair-status - pressing again once they are up is what that
 * message tells the user to do. Anything else is rethrown.
 */
async function generateBoth(page: Page) {
  const status = page.locator('#pair-status');
  for (let attempt = 0; attempt < 8; attempt++) {
    await page.locator('#action-btn').click();
    try {
      await expect(status).toContainText('Both cylinders are ready', { timeout: 120_000 });
      return;
    } catch (error) {
      const text = (await status.textContent()) ?? '';
      if (!/could not be generated/.test(text)) throw error;
    }
    await page.waitForTimeout(1500);
  }
  throw new Error('Generate never reported a finished pair');
}

/** Press Generate for a single cylinder and wait for its download control. */
async function generateSingle(page: Page, state: { bodies: unknown[] }, n: number) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 4000 && state.bodies.length < n; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.bodies.length >= n) {
      await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });
      return;
    }
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

/** Click Download STL and return the offered filename plus the file's triangle count. */
async function download(page: Page) {
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#download-stl-btn').click();
  const dl = await downloadPromise;
  const buf = fs.readFileSync((await dl.path())!);
  const triangles = buf.readUInt32LE(80);
  expect(buf.byteLength).toBe(84 + triangles * 50);
  return { name: dl.suggestedFilename(), triangles };
}

test.describe('Cylinders to Generate', () => {
  test.describe.configure({ timeout: 300_000 });

  test('is the first Expert Mode submenu, defaults to both, and is keyboard-operable', async ({ page }) => {
    await openApp(page);

    // First submenu, headed h3 like the others, its panel closed by default.
    expect(
      await page.evaluate(() => {
        const first = document.querySelector('#expert-settings .expert-submenu');
        return {
          id: first?.id,
          heading: first?.querySelector('h3 .expert-submenu-title')?.textContent?.trim(),
          expanded: first?.querySelector('.expert-submenu-toggle')?.getAttribute('aria-expanded'),
          controls: first?.querySelector('.expert-submenu-toggle')?.getAttribute('aria-controls'),
        };
      }),
    ).toEqual({
      id: 'cylinders-to-generate-submenu',
      heading: 'Cylinders to Generate',
      expanded: 'false',
      controls: 'expert-panel-cylinders',
    });

    // Both is the default (D-9); the plate selector left the main form.
    expect(await selectedCylinders(page)).toBe('both');
    expect(await page.locator('input[name="plate_type"]').count()).toBe(0);
    expect(await page.locator('h2', { hasText: 'Select Plate to Generate' }).count()).toBe(0);

    // The old pair buttons are gone: one Generate, one Download.
    for (const id of ['generate-both-btn', 'pair-downloads', 'download-pair-btn', 'download-cylinder-a-btn', 'download-cylinder-b-btn']) {
      expect(await page.locator(`#${id}`).count(), id).toBe(0);
    }

    // Open Expert Mode and the submenu through their own toggles, then arrow
    // through the group: three radios, the signed A/B names, both first.
    await page.locator('#expert-toggle').click();
    await page.locator('[aria-controls="expert-panel-cylinders"]').click();
    await expect(page.locator('[aria-controls="expert-panel-cylinders"]')).toHaveAttribute('aria-expanded', 'true');
    const labels = await page.locator('#expert-panel-cylinders .radio-text').allTextContents();
    expect(labels).toEqual(['Both Cylinder A and B', 'Cylinder A — Embossing Plate', 'Cylinder B — Universal Counter Plate']);

    // Opening a submenu moves focus to its first control after a short delay;
    // wait for that landing rather than racing it with a focus() of our own.
    await expect(page.locator('input[name="plate_selection"][value="both"]')).toBeFocused();
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('input[name="plate_selection"][value="positive"]')).toBeChecked();
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('input[name="plate_selection"][value="negative"]')).toBeChecked();
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('ArrowUp');
    await expect(page.locator('input[name="plate_selection"][value="both"]')).toBeChecked();
  });

  test('Generate builds A then B, restores the choice, and Download saves the combined file', async ({ page }) => {
    await openApp(page);
    const requests = watchGeometrySpecRequests(page);
    const unattended: string[] = [];
    page.on('download', (dl) => unattended.push(dl.suggestedFilename()));
    await page.locator('#auto-text').fill('abc');

    await generateBoth(page);

    // Two request bodies, A then B, built from ONE set of settings. (Single-
    // sided, the universal counter plate carries no text of its own, so only
    // the settings and the cylinder are compared here; doubleSided.spec.ts
    // pins the whole-body identity for the paired case.)
    const [aBody, bBody] = requests.bodies.slice(-2) as Array<Record<string, unknown>>;
    expect(aBody.plate_type).toBe('positive');
    expect(bBody.plate_type).toBe('negative');
    expect(aBody.settings).toEqual(bBody.settings);
    expect(aBody.cylinder_params).toEqual(bBody.cylinder_params);

    // Nothing downloaded by itself, the choice is back on both, and the ONE
    // Download button offers the combined file under its frozen name (D-10).
    expect(unattended).toEqual([]);
    expect(await selectedCylinders(page)).toBe('both');
    await expect(page.locator('#pair-status')).toHaveText(BOTH_READY);
    await expect(page.locator('#download-stl-btn')).toBeVisible();
    const pair = await download(page);
    expect(pair.name).toBe('Cylinder_Pair_0.4_abc.stl');
    expect(pair.triangles).toBeGreaterThan(0);
  });

  test('choosing one cylinder generates one body under the single-cylinder name', async ({ page }) => {
    await openApp(page);
    const requests = watchGeometrySpecRequests(page);
    await page.locator('#auto-text').fill('abc');

    await selectCylinders(page, 'positive');
    await generateSingle(page, requests, 1);
    expect(requests.bodies.length).toBe(1);
    expect(requests.bodies[0]?.plate_type).toBe('positive');
    await expect(page.locator('#a11y-status')).toContainText(SINGLE_READY);
    expect((await download(page)).name).toBe('Embossing_Cylinder_0.4_abc.stl');

    await selectCylinders(page, 'negative');
    await generateSingle(page, requests, 2);
    expect(requests.bodies.length).toBe(2);
    expect(requests.bodies[1]?.plate_type).toBe('negative');
    expect((await download(page)).name).toBe('Counter_Cylinder_0.4_abc.stl');
  });

  test('the choice survives a reload and Reset restores both', async ({ page }) => {
    await openApp(page);
    await selectCylinders(page, 'negative');
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_plate_type'))).toBe('negative');

    await page.reload();
    await page.waitForSelector('#embosser-setup-selection');
    expect(await selectedCylinders(page)).toBe('negative');

    await page.locator('#reset-defaults-btn').click();
    expect(await selectedCylinders(page)).toBe('both');
  });

  test('the help text sends a single-cylinder user to Cylinders to Generate', async ({ page }) => {
    await openApp(page);
    // textContent, not innerText: the panel is hidden until its tab is chosen.
    const help = (await page.locator('#helpPanelHowToUse').textContent()) ?? '';
    expect(help).toContain('Cylinders to Generate');
    expect(help).not.toContain('Select Plate to Generate');
  });
});
