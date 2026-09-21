/**
 * E2E tests for the slicer seam channel (2026-09-20 programme, sub-plan A).
 *
 * Every cylinder carries a shallow V-groove beside the row markers so a slicer's
 * default "aligned" seam mode hides each layer's seam in it instead of in a
 * dot. It is ON by default; an Expert Mode switch turns it off. What this file
 * pins:
 *
 *   1. The switch exists, is on by default, and its description is inside the
 *      ADA SOP Step 6.8 ceiling.
 *   2. The wire: ON adds NOTHING to the request body (byte-identical to the
 *      body captured before the channel existed), OFF adds exactly one key.
 *   3. The bytes: OFF reproduces the pre-channel browser export exactly; ON
 *      puts a groove at the spec's angle and nowhere else.
 *   4. The live note when the groove does not fit, persistence, and reset.
 *
 * The sentences quoted here are DRAFT (S-C1, S-C2). FLAGGED FOR BRENNEN.
 *
 * @see docs/specifications/SURFACE_DIMENSIONS_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { selectCylinders } from './helpers/cylinders';

const FIXTURES = path.resolve(__dirname, 'fixtures');
const BARREL_RADIUS_MM = 15.4;
const CHANNEL_DEPTH_MM = 0.5;
// From the spike and app/geometry_spec.py: 15 columns visual on the 0.4 preset
// puts the groove 0.45 mm toward column 0, spec theta 178.33 degrees on the
// embossing plate; the worker places it at -theta, so 181.67 in the file.
const EMBOSS_CHANNEL_DEG = 181.67;

// DRAFT S-C2 and S-C3 (phase A2). Byte-for-byte the server's sentences.
const GAP_NOTE = 'The seam channel was left out: the seam gap is too narrow for it at this cell count and diameter.';
const WALL_NOTE = 'The seam channel was left out: the cylinder wall would be thinner than 1.2 mm under it.';

const TRANSIENT_ERRORS = /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#indicator-mode-selection');
  // Since 2026-09-21 Generate builds both cylinders by default; this spec
  // exercises one cylinder at a time, so choose Cylinder A (the old default)
  // under Cylinders to Generate. Pair tests choose 'both' themselves.
  await selectCylinders(page, 'positive');
}

/** Reveal Expert Mode and the Surface Dimensions submenu (setup, not the feature under test). */
async function revealDimensions(page: Page) {
  await page.evaluate(() => {
    const expert = document.getElementById('expert-settings');
    if (expert) expert.style.display = 'block';
    const panel = document.getElementById('expert-panel-dimensions');
    if (panel) {
      panel.style.display = 'block';
      panel.hidden = false;
    }
  });
  await page.waitForSelector('#expert-panel-dimensions', { state: 'visible' });
}

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

async function generate(page: Page, state: { bodies: unknown[] }, n: number) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 4000 && state.bodies.length < n; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.bodies.length >= n) return;
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

async function generateAndDownload(page: Page, state: { bodies: unknown[] }, n: number): Promise<Buffer> {
  await generate(page, state, n);
  await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#download-stl-btn').click();
  const download = await downloadPromise;
  return fs.readFileSync((await download.path())!);
}

/**
 * Binary STL: 80-byte header, uint32 triangle count, then 50-byte records with
 * the three vertices at +12/+24/+36 (X, Y, Z float32, little-endian).
 */
function stlVertices(buf: Buffer): Array<[number, number, number]> {
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const triangles = view.getUint32(80, true);
  expect(buf.byteLength).toBe(84 + triangles * 50);
  const out: Array<[number, number, number]> = [];
  for (let i = 0; i < triangles; i++) {
    const base = 84 + i * 50;
    for (const off of [12, 24, 36]) {
      out.push([
        view.getFloat32(base + off, true),
        view.getFloat32(base + off + 4, true),
        view.getFloat32(base + off + 8, true),
      ]);
    }
  }
  return out;
}

/** Angles (degrees, 0..360) of the vertices on the end caps at the groove's apex radius. */
function channelApexAngles(buf: Buffer): number[] {
  const vertices = stlVertices(buf);
  let zMin = Infinity;
  let zMax = -Infinity;
  for (const [, , z] of vertices) {
    if (z < zMin) zMin = z;
    if (z > zMax) zMax = z;
  }
  const halfHeight = (zMax - zMin) / 2;
  const zMid = (zMax + zMin) / 2;
  const angles = new Set<number>();
  for (const [x, y, z] of vertices) {
    if (Math.abs(Math.abs(z - zMid) - halfHeight) > 0.05) continue;
    const r = Math.hypot(x, y);
    if (Math.abs(r - (BARREL_RADIUS_MM - CHANNEL_DEPTH_MM)) > 0.05) continue;
    angles.add(Math.round((((Math.atan2(y, x) * 180) / Math.PI + 360) % 360) * 100) / 100);
  }
  return Array.from(angles).sort((a, b) => a - b);
}

test.describe('Slicer seam channel', () => {
  test.describe.configure({ timeout: 300_000 });

  test('the switch is on by default and describes itself within the ceiling', async ({ page }) => {
    await openApp(page);
    await revealDimensions(page);

    const toggle = page.locator('#seam_channel_enabled');
    await expect(toggle).toBeVisible();
    await expect(toggle).toBeChecked();
    // DRAFT S-C1 - FLAGGED FOR BRENNEN.
    await expect(toggle).toHaveAccessibleName('Slicer seam channel');
    await expect(toggle).toHaveAccessibleDescription(
      'A shallow groove beside the row markers where the slicer hides its layer seam, keeping it off the dots.',
    );
    const words = (await page.locator('#seam-channel-note').innerText()).trim().split(/\s+/).length;
    expect(words).toBeLessThanOrEqual(25);

    // 44 px touch target (WCAG 2.5.8), the same convention as the other toggles.
    const box = await page.locator('label[for="seam_channel_enabled"]').boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);

    // Keyboard: focus lands on the checkbox and Space toggles it.
    await toggle.focus();
    await page.keyboard.press('Space');
    await expect(toggle).not.toBeChecked();
    await page.keyboard.press('Space');
    await expect(toggle).toBeChecked();

    // The note about a groove that does not fit is silent on untouched dials.
    await expect(page.locator('#seam-channel-warning')).toBeHidden();
  });

  test('on adds nothing to the request, off adds exactly one key', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    const state = watchGeometrySpecRequests(page);

    await generate(page, state, 1);
    const onBody = state.bodies[0] as Record<string, unknown>;
    const settings = onBody.settings as Record<string, unknown>;
    expect(settings).not.toHaveProperty('seam_channel_enabled');
    // Byte-identical to the body the browser sent before the channel existed.
    const captured = JSON.parse(fs.readFileSync(path.join(FIXTURES, 'embossing_0.4_abc_before_seam_channel.request.json'), 'utf8'));
    expect(onBody).toEqual(captured);

    await revealDimensions(page);
    await page.locator('#seam_channel_enabled').uncheck();
    await generate(page, state, 2);
    const offBody = state.bodies[1] as Record<string, unknown>;
    expect((offBody.settings as Record<string, unknown>).seam_channel_enabled).toBe(0);
    const offWithoutFlag = JSON.parse(JSON.stringify(offBody));
    delete offWithoutFlag.settings.seam_channel_enabled;
    expect(offWithoutFlag).toEqual(onBody);
  });

  test('off reproduces the pre-channel export byte for byte, on cuts the groove at the spec angle', async ({ page, browserName }) => {
    // The fixtures were captured in Chromium; the Manifold WASM output is the
    // same everywhere, but this byte comparison is pinned to the browser that
    // made them so a float-formatting difference elsewhere cannot masquerade
    // as a geometry change.
    test.skip(browserName !== 'chromium', 'byte fixtures were captured in Chromium');
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    const state = watchGeometrySpecRequests(page);

    const withChannel = await generateAndDownload(page, state, 1);
    const apex = channelApexAngles(withChannel);
    expect(apex).toHaveLength(1);
    expect(apex[0]).toBeCloseTo(EMBOSS_CHANNEL_DEG, 1);

    await revealDimensions(page);
    await page.locator('#seam_channel_enabled').uncheck();
    const plain = await generateAndDownload(page, state, 2);
    expect(channelApexAngles(plain)).toHaveLength(0);
    const fixture = fs.readFileSync(path.join(FIXTURES, 'embossing_0.4_abc_before_seam_channel.stl'));
    expect(plain.equals(fixture)).toBe(true);

    // The counter plate too: mirror angle, and the pre-channel bytes when off.
    await selectCylinders(page, 'negative');
    const plainCounter = await generateAndDownload(page, state, 3);
    const counterFixture = fs.readFileSync(path.join(FIXTURES, 'counter_0.4_abc_before_seam_channel.stl'));
    expect(plainCounter.equals(counterFixture)).toBe(true);

    await page.locator('#seam_channel_enabled').check();
    const counterWithChannel = await generateAndDownload(page, state, 4);
    const counterApex = channelApexAngles(counterWithChannel);
    expect(counterApex).toHaveLength(1);
    expect(counterApex[0]).toBeCloseTo(360 - EMBOSS_CHANNEL_DEG, 1);
  });

  test('a layout with no room says so before Generate, and the note clears', async ({ page }) => {
    await openApp(page);
    await revealDimensions(page);
    await page.evaluate(() => {
      const spacing = document.getElementById('expert-panel-spacing');
      if (spacing) {
        spacing.style.display = 'block';
        spacing.hidden = false;
      }
    });

    // Tactile mode at 15 cells leaves a 5.8 mm seam gap: the arrow recess and
    // the first cell's dots already overlap, so the groove is left out.
    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    await expect(page.locator('#grid_columns')).toHaveValue('14');
    await expect(page.locator('#seam-channel-warning')).toBeHidden();

    await page.locator('#grid_columns').fill('15');
    await page.locator('#grid_columns').dispatchEvent('input');
    await expect(page.locator('#seam-channel-warning')).toBeVisible();
    await expect(page.locator('#seam-channel-message')).toHaveText(GAP_NOTE);
    // The same edit also raises the signed tactile-gap warning, and the page
    // has ONE live region: that older, debounced sentence is the one left in
    // it. The note stays visible in its box; the region is asserted below on
    // a case where only the channel note fires.
    await expect(page.locator('#a11y-status')).toContainText('seam gap');

    await page.locator('#grid_columns').fill('14');
    await page.locator('#grid_columns').dispatchEvent('input');
    await expect(page.locator('#seam-channel-warning')).toBeHidden();

    // A cutout that leaves under 1.2 mm of wall under the groove raises the
    // channel note ALONE, so it is what the live region carries.
    await page.locator('#cylinder_polygonal_cutout_radius_mm').fill('13.5');
    await page.locator('#cylinder_polygonal_cutout_radius_mm').dispatchEvent('input');
    await expect(page.locator('#seam-channel-warning')).toBeVisible();
    await expect(page.locator('#seam-channel-message')).toHaveText(WALL_NOTE);
    await expect(page.locator('#a11y-status')).toHaveText(WALL_NOTE);

    // Switching the channel off silences the note whatever the layout.
    await page.locator('#seam_channel_enabled').uncheck();
    await expect(page.locator('#seam-channel-warning')).toBeHidden();
    await expect(page.locator('#a11y-status')).toHaveText('');
  });

  test('the choice survives a reload and reset restores the default', async ({ page }) => {
    await openApp(page);
    await revealDimensions(page);
    await page.locator('#seam_channel_enabled').uncheck();
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_seam_channel_enabled'))).toBe('0');

    await page.reload();
    await page.waitForLoadState('networkidle');
    await revealDimensions(page);
    await expect(page.locator('#seam_channel_enabled')).not.toBeChecked();

    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#seam_channel_enabled')).toBeChecked();
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_seam_channel_enabled'))).toBeNull();
  });
});
