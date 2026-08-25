/**
 * E2E tests for the gear-integrated one-piece rollers (BETA).
 *
 * When the toggle is ON, a generated cylinder ships as ONE solid with its top
 * and bottom drive gears already attached, and the downloads gain a `Geared_`
 * segment. When it is OFF the app must behave exactly as before the feature
 * existed — the single-sided filenames appear in public training videos, and
 * the request payload must not gain a key.
 *
 * The gear geometry has no dials: it is vendored 1:1 replica data. What the UI
 * owns is the toggle, two live notes, and the naming — so that is what is
 * tested here. The geometry itself is proved in tests/test_gear_rollers.py and
 * pinned by the gear_roller*_golden fixtures.
 *
 * NO CARD-SHAPE TEST, deliberately: the phase prompt asked for one, but this UI
 * has no card shape. Output Shape offers exactly one radio, value="cylinder",
 * so the toggle can never be disabled by a card selection and building that
 * branch would mean shipping unreachable UI. The cylinders-only rule is proved
 * where it actually lives — tests/test_gear_validation.py drives a card + gears
 * request through the real route and asserts the 400 and its wording.
 *
 * @see docs/specifications/GEAR_INTEGRATED_ROLLERS_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';

// Signed strings. The UI must quote them exactly; rewording is Brennen's call.
const CUTOUT_NOTE = 'The polygonal cutout is not used while integrated gears are on.';
const SIZE_WARNING_START = 'Integrated gears are matched to the reference roller and only fit a';
const GEARS_READY = 'Cylinder generated with integrated gears.';

// The reference roller the vendored gears were measured against. Anything else
// is rejected by app/validation.py, so the UI warns before a generate.
const REFERENCE_DIAMETER_MM = '30.8';
const REFERENCE_HEIGHT_MM = '52';

// Same transient failures the double-sided spec tolerates: both workers signal
// readiness asynchronously and Firefox is slower to spin them up.
const TRANSIENT_ERRORS = /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#indicator-mode-selection');
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

/** Click Generate and wait until the n-th request has gone out. */
async function generate(page: Page, state: { bodies: unknown[] }, n: number) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 4000 && state.bodies.length < n; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.bodies.length >= n) return;

    // #error-text doubles as an informational region; only a non-info notice
    // is a real block.
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

/** Click Download STL and return the filename the browser was offered. */
async function downloadName(page: Page): Promise<string> {
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#download-stl-btn').click();
  const download = await downloadPromise;
  return download.suggestedFilename();
}

/**
 * Set a cylinder dial at the SOURCE rather than by typing into it.
 *
 * These dials live inside a collapsed Expert Mode panel, and editing them
 * through the UI races the card-thickness preset — a recorded, unfixable
 * flake. The live notes read the dial's value, so writing the value and
 * letting the toggle's own handler read it exercises the same code path a
 * user's edit would.
 */
async function setDial(page: Page, id: string, value: string) {
  await page.evaluate(([dialId, dialValue]) => {
    const el = document.getElementById(dialId) as HTMLInputElement | null;
    if (!el) throw new Error(`dial ${dialId} not found`);
    el.value = dialValue;
  }, [id, value]);
}

async function setGearToggle(page: Page, on: boolean) {
  const toggle = page.locator('#gear_rollers_enabled');
  if (on) {
    await toggle.check();
  } else {
    await toggle.uncheck();
  }
}

/** The plate radios' visible label text, in [positive, negative] order. */
function plateLabels(page: Page) {
  return page.evaluate(() =>
    ['positive', 'negative'].map(
      (value) =>
        document
          .querySelector(`input[name="plate_type"][value="${value}"]`)
          ?.closest('label')
          ?.querySelector('.radio-text')?.textContent ?? '',
    ),
  );
}

/** Click one of the pair download buttons and return the offered filename. */
async function pairDownloadName(page: Page, which: 'a' | 'b'): Promise<string> {
  const downloadPromise = page.waitForEvent('download');
  await page.locator(`#download-cylinder-${which}-btn`).click();
  const download = await downloadPromise;
  return download.suggestedFilename();
}

/**
 * Press Generate Both and wait for the pair to finish. The first press can land
 * before liblouis or the Manifold worker is ready, which aborts the run and
 * says so in #pair-status — pressing again once they are up is exactly what
 * that message tells the user to do. Anything that is NOT that transient
 * failure is rethrown rather than retried.
 */
async function generateBoth(page: Page) {
  const status = page.locator('#pair-status');
  for (let attempt = 0; attempt < 8; attempt++) {
    await page.locator('#generate-both-btn').click();
    try {
      await expect(status).toContainText('Both cylinders are ready', { timeout: 120_000 });
      return;
    } catch (error) {
      const text = (await status.textContent()) ?? '';
      if (!/could not be generated/.test(text)) throw error;
    }
    await page.waitForTimeout(1500);
  }
  throw new Error('Generate Both never reported a finished pair');
}

test.describe('Gear-integrated one-piece rollers (BETA)', () => {
  // Same rationale as the other generation specs: the Manifold worker plus a
  // 30,000-triangle gear asset makes a real run slow, and Firefox slower.
  test.describe.configure({ timeout: 300_000 });

  test('the toggle is present, off by default, and keyboard-operable', async ({ page }) => {
    await openApp(page);

    const toggle = page.locator('#gear_rollers_enabled');
    await expect(toggle).toHaveCount(1);
    await expect(toggle).not.toBeChecked();
    await expect(toggle).toBeEnabled();

    // Its accessible description is the note, and the note is visible text.
    await expect(toggle).toHaveAttribute('aria-describedby', 'gear-rollers-note');
    await expect(page.locator('#gear-rollers-note')).toBeVisible();

    await toggle.focus();
    await page.keyboard.press('Space');
    await expect(toggle).toBeChecked();
    await page.keyboard.press('Space');
    await expect(toggle).not.toBeChecked();
  });

  test('the cutout note appears only when a cutout is set AND the toggle is on', async ({ page }) => {
    await openApp(page);
    const note = page.locator('#gear-cutout-note');
    const status = page.locator('#a11y-status');

    // The shipped default cutout radius is 13, so turning the toggle on is
    // enough to earn the note.
    await expect(note).toBeHidden();
    await setGearToggle(page, true);
    await expect(note).toBeVisible();
    await expect(page.locator('#gear-cutout-message')).toHaveText(CUTOUT_NOTE);
    await expect(status).toContainText(CUTOUT_NOTE);

    // No cutout, no note - even with the toggle still on.
    await setDial(page, 'cylinder_polygonal_cutout_radius_mm', '0');
    await setGearToggle(page, false);
    await setGearToggle(page, true);
    await expect(note).toBeHidden();
    await expect(status).not.toContainText(CUTOUT_NOTE);

    // Toggle off with a cutout back in place: still no note.
    await setDial(page, 'cylinder_polygonal_cutout_radius_mm', '13');
    await setGearToggle(page, false);
    await expect(note).toBeHidden();
  });

  test('an off-size cylinder is warned about before the user can generate', async ({ page }) => {
    await openApp(page);
    const warning = page.locator('#gear-size-warning');

    // At the shipped defaults the cylinder IS the reference roller.
    await setGearToggle(page, true);
    await expect(warning).toBeHidden();

    // A cylinder the gears cannot fit: the gears sit at fixed heights, so a
    // 45 mm barrel would export as loose pieces. The server refuses it; the
    // UI has to say so first.
    await setDial(page, 'cylinder_height_mm', '45');
    await setGearToggle(page, false);
    await setGearToggle(page, true);
    await expect(warning).toBeVisible();
    await expect(page.locator('#gear-size-message')).toContainText(SIZE_WARNING_START);
    await expect(page.locator('#gear-size-message')).toContainText('45');
    await expect(page.locator('#a11y-status')).toContainText(SIZE_WARNING_START);

    // Back to the reference size and it clears.
    await setDial(page, 'cylinder_height_mm', REFERENCE_HEIGHT_MM);
    await setGearToggle(page, false);
    await setGearToggle(page, true);
    await expect(warning).toBeHidden();
  });

  test('the request gains exactly one key, and only when the toggle is on', async ({ page }) => {
    await openApp(page);
    const state = watchGeometrySpecRequests(page);
    await page.locator('#auto-text').fill('abc');

    await generate(page, state, 1);
    const off = (state.bodies[0]?.settings ?? {}) as Record<string, unknown>;
    expect('gear_rollers_enabled' in off).toBe(false);

    await setGearToggle(page, true);
    await generate(page, state, 2);
    const on = (state.bodies[1]?.settings ?? {}) as Record<string, unknown>;
    expect(on.gear_rollers_enabled).toBe(1);

    // Nothing else moved: the gear geometry has no dials to send.
    const added = Object.keys(on).filter((k) => !(k in off));
    const removed = Object.keys(off).filter((k) => !(k in on));
    expect(added).toEqual(['gear_rollers_enabled']);
    expect(removed).toEqual([]);
    // Both plates still ask for a cylinder.
    expect(state.bodies[1]?.shape_type).toBe('cylinder');
  });

  test('a geared download is named Geared, and announces itself', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await setGearToggle(page, true);

    const state = watchGeometrySpecRequests(page);
    await generate(page, state, 1);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });

    // S5 rides in the ready announcement rather than as a second write: the
    // live region holds one message at a time.
    await expect(page.locator('#a11y-status')).toContainText(GEARS_READY);

    expect(await downloadName(page)).toBe('Embossing_Cylinder_Geared_0.4_abc.stl');
  });

  test('toggle-off downloads keep the pre-beta filename', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('abc');

    const state = watchGeometrySpecRequests(page);
    await generate(page, state, 1);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });

    // Public training videos show this name. It must not move.
    expect(await downloadName(page)).toBe('Embossing_Cylinder_0.4_abc.stl');
    await expect(page.locator('#a11y-status')).not.toContainText(GEARS_READY);
  });

  test('the counter plate asks for the B gear set', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await setGearToggle(page, true);
    await page.locator('input[name="plate_type"][value="negative"]').check();

    const state = watchGeometrySpecRequests(page);
    await generate(page, state, 1);
    const settings = (state.bodies[0]?.settings ?? {}) as Record<string, unknown>;
    expect(settings.gear_rollers_enabled).toBe(1);
    expect(state.bodies[0]?.plate_type).toBe('negative');
  });

  test('the toggle survives a reload and is cleared by reset to defaults', async ({ page }) => {
    await openApp(page);
    await setGearToggle(page, true);
    await expect(page.locator('#gear_rollers_enabled')).toBeChecked();

    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('#gear_rollers_enabled')).toBeChecked();

    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#gear_rollers_enabled')).not.toBeChecked();
    await expect(page.locator('#gear-cutout-note')).toBeHidden();
  });

  test('gear mode alone reveals Generate Both and the Cylinder A/B names', async ({ page }) => {
    await openApp(page);

    const generateBothBtn = page.locator('#generate-both-btn');
    await expect(generateBothBtn).toBeHidden();
    const original = await plateLabels(page);
    expect(original).toEqual(['Embossing Plate', 'Universal Counter Plate']);

    // A geared roller only works as a meshed A/B pair, so the pair controls
    // follow this toggle exactly as they follow the double-sided one.
    await setGearToggle(page, true);
    await expect(generateBothBtn).toBeVisible();
    expect(await plateLabels(page)).toEqual([
      'Cylinder A — Embossing Plate',
      'Cylinder B — Universal Counter Plate',
    ]);

    // Byte-identical on the way back: the training videos show these names.
    await setGearToggle(page, false);
    await expect(generateBothBtn).toBeHidden();
    expect(await plateLabels(page)).toEqual(original);
  });

  test('Generate Both with gears only keeps the single-sided Geared names and pairs the gear sets', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);
    const state = watchGeometrySpecRequests(page);
    const unattendedDownloads: string[] = [];
    page.on('download', (download) => unattendedDownloads.push(download.suggestedFilename()));

    await page.locator('#auto-text').fill('abc');
    await setGearToggle(page, true);
    await generateBoth(page);

    // Same rule as the double-sided pair: nothing downloads by itself.
    expect(unattendedDownloads).toEqual([]);

    // Double-sided is OFF, so the single-sided filenames stand — the pair
    // buttons hand out the same files two solo generates would have produced.
    await expect(page.locator('#pair-downloads')).toBeVisible();
    expect(await pairDownloadName(page, 'a')).toBe('Embossing_Cylinder_Geared_0.4_abc.stl');
    expect(await pairDownloadName(page, 'b')).toBe('Counter_Cylinder_Geared_0.4_abc.stl');

    // The run asked for both plates with gears on — which is what makes the
    // backend hand Cylinder A the gears_a asset and Cylinder B gears_b.
    const [aBody, bBody] = state.bodies.slice(-2) as Array<Record<string, unknown>>;
    expect(aBody.plate_type).toBe('positive');
    expect(bBody.plate_type).toBe('negative');
    expect((aBody.settings as Record<string, unknown>).gear_rollers_enabled).toBe(1);
    expect((bBody.settings as Record<string, unknown>).gear_rollers_enabled).toBe(1);
  });

  test('the combined download carries the Geared pair name and every triangle', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await setGearToggle(page, true);
    await generateBoth(page);

    const triangleCount = async (buttonId: string) => {
      const downloadPromise = page.waitForEvent('download');
      await page.locator(`#${buttonId}`).click();
      const download = await downloadPromise;
      const buf = fs.readFileSync((await download.path())!);
      const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
      const triangles = view.getUint32(80, true);
      expect(buf.byteLength).toBe(84 + triangles * 50);
      return { name: download.suggestedFilename(), triangles };
    };

    const a = await triangleCount('download-cylinder-a-btn');
    const b = await triangleCount('download-cylinder-b-btn');
    const pair = await triangleCount('download-pair-btn');

    // DRAFT name pin - revisited at the sign-off gate.
    expect(pair.name).toBe('Cylinder_Pair_Geared_0.4_abc.stl');
    expect(pair.triangles).toBe(a.triangles + b.triangles);
  });
});
