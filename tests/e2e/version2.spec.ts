/**
 * Embosser Version 2 (keyed gear pegs) PROTOTYPE — end-to-end coverage.
 *
 * What this pins, in a real browser, that no unit test can:
 *   * the selector exists, defaults to Version 1, and is operable from the
 *     keyboard with the accessible name the sign-off promised;
 *   * choosing Version 2 changes exactly what it should — the preset dials, the
 *     hidden rows, the gears BETA, pair mode, the prototype notice — and
 *     announces itself ONCE;
 *   * the request body gains exactly two keys and loses none, so a Version 1
 *     body is unchanged;
 *   * every download name follows D-V12;
 *   * the choice survives a reload and Reset to defaults undoes it.
 *
 * Signed strings are constants at the top: the UI must quote them exactly, and
 * rewording is Brennen's call, not a test's.
 *
 * @see docs/specifications/EMBOSSER_VERSION_2_KEYED_CUTOUTS_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import { selectCylinders } from './helpers/cylinders';

// Signed 2026-08-28 by Brennen at the Phase 05 gate. Reword only with his sign-off.
const S_V1_LEGEND = 'Embosser version';
const S_V3_NOTE =
  'Choose Version 2 only if you are building the Version 2 embosser, which uses keyed gear pegs. Version 1 stays supported.';
// S-V4 (the prototype notice) was retired on 2026-09-20 (programme decision D-7).
const S_V5_SIZE_START = 'The Version 2 embosser expects a 30.8 mm x 54 mm cylinder.';
// S-V8', signed 2026-09-21 (D-7): the "(prototype)" tag is gone.
const S_V8_READY = 'Cylinder generated for the Version 2 embosser.';
// S-G1 and S-G2, signed 2026-09-21 (2026-09-20 programme, phase B6): the Version 2 fixed
// gears' size gate and the fused roller's ready prefix.
// S-M13 (the temporary C2 guard) was retired with this phase.
const S_G1_SIZE_START = 'Fixed gears for the Version 2 embosser fit only a 30.8 mm x 54 mm cylinder.';
const S_G2_READY = 'Cylinder generated with fixed gears for the Version 2 embosser.';
const S5_GEARS_READY = 'Cylinder generated with integrated gears.';
// S3, signed 2026-08-24: raised by the gear refresh while a cutout radius is dialled.
const S3_CUTOUT_NOTE = 'The polygonal cutout is not used while integrated gears are on.';
// S-M10, signed 2026-09-21: the gear choice, announced one tick after the click.
const S_M10_FIXED = 'Simplified fixed gears selected.';
const S_V10_ON = 'Version 2 selected: keyed gear-peg cutouts, 30.8 mm cylinder.';
const S_V10_OFF = 'Version 1 selected.';
// S-V16, DRAFT 2026-09-24 (awaiting Brennen's sign-off): the clause the version
// announcement gains when choosing Version 2 moved the Row Indicator Style to
// the tactile seam arrow, the Version 2 default (decision D-4).
const S_V16_STYLE_MOVED = 'Row Indicator Style set to the tactile seam arrow, the Version 2 default.';

// The Version 2 preset barrel (D-V4), owned by app/geometry/version2.py.
const V2_DIAMETER = '30.8';
const V2_HEIGHT = '54';

// Same transient failures the other beta specs tolerate: both workers signal
// readiness asynchronously and Firefox is slower to spin them up.
const TRANSIENT_ERRORS =
  /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

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
async function downloadName(page: Page, selector = '#download-stl-btn'): Promise<string> {
  const downloadPromise = page.waitForEvent('download');
  await page.locator(selector).click();
  return (await downloadPromise).suggestedFilename();
}

/**
 * Set a cylinder dial at the SOURCE rather than by typing into it.
 *
 * These dials live inside a collapsed Expert Mode panel, and editing them
 * through the UI races the card-thickness preset — a recorded, unfixable flake.
 * The live notes read the dial's value, so writing the value and dispatching
 * the input event the app already listens for exercises the same path a user's
 * edit would.
 */
async function setDial(page: Page, id: string, value: string) {
  await page.evaluate(([dialId, dialValue]) => {
    const el = document.getElementById(dialId) as HTMLInputElement | null;
    if (!el) throw new Error(`dial ${dialId} not found`);
    el.value = dialValue;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, [id, value]);
}

/** Open Expert Mode and the Surface Dimensions panel, so their rows are measurable. */
async function openExpertDimensions(page: Page) {
  await page.evaluate(() => {
    (document.getElementById('expert-settings') as HTMLElement).style.display = '';
    (document.getElementById('expert-panel-dimensions') as HTMLElement).style.display = '';
  });
}

async function selectVersion2(page: Page) {
  await page.locator('#embosser_version_2').check();
}

/** Triangle count and z extent of a downloaded binary STL, read from the stream. */
async function stlBounds(download: { createReadStream(): Promise<NodeJS.ReadableStream> }) {
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  const data = Buffer.concat(chunks);
  const triangles = data.readUInt32LE(80);
  let zMin = Infinity;
  let zMax = -Infinity;
  for (let i = 0; i < triangles; i++) {
    const base = 84 + i * 50 + 12;
    for (let v = 0; v < 3; v++) {
      const z = data.readFloatLE(base + v * 12 + 8);
      if (z < zMin) zMin = z;
      if (z > zMax) zMax = z;
    }
  }
  return { triangles, zMin, zMax };
}

test.describe('Embosser Version 2', () => {
  test('the selector is the first choice of the first menu item, defaults to Version 1, and is keyboard-operable', async ({
    page,
  }) => {
    await openApp(page);

    // Since 2026-09-20 the version choice is the first of three inside the
    // "Embosser setup" menu item, which sits in the form's selection menu
    // directly under "What Does This Program Do?" (never in the site header).
    expect(
      await page.evaluate(
        () => !!document.querySelector('header.site-header #embosser-setup-selection'),
      ),
    ).toBe(false);
    expect(
      await page.evaluate(
        () => !!document.querySelector('#braille-form #embosser-setup-selection #embosser-version-selection'),
      ),
    ).toBe(true);
    expect(
      await page.evaluate(() => {
        const item = document.querySelector('#embosser-setup-selection');
        return item?.previousElementSibling?.classList.contains('info-panel') ?? false;
      }),
    ).toBe(true);
    // It follows the menu-item rules: a real h2 inside the item's legend, and
    // an h3 inside each choice's legend.
    await expect(page.locator('#embosser-setup-selection > fieldset > legend h2.legend-heading')).toHaveText(
      'Embosser setup',
    );
    await expect(page.locator('#embosser-version-selection h3.legend-heading')).toHaveText(S_V1_LEGEND);

    await expect(page.locator('#embosser_version_1')).toBeChecked();
    await expect(page.locator('#embosser_version_2')).not.toBeChecked();

    // S-V1 is the group's accessible name; S-V3 is its description.
    await expect(page.locator('#embosser-version-selection > legend')).toHaveText(S_V1_LEGEND);
    await expect(page.locator('#embosser-version-note')).toHaveText(S_V3_NOTE);
    expect(
      await page.evaluate(() =>
        document.getElementById('embosser-version-selection')?.getAttribute('aria-describedby'),
      ),
    ).toBe('embosser-version-note');

    // Arrow keys move within the radio group, both ways, and carry the
    // selection with them — the native behaviour a roving-tabindex ARIA
    // reimplementation would have had to rebuild.
    await page.locator('#embosser_version_1').focus();
    await page.keyboard.press('ArrowDown');
    await expect(page.locator('#embosser_version_2')).toBeFocused();
    await expect(page.locator('#embosser_version_2')).toBeChecked();
    await page.keyboard.press('ArrowUp');
    await expect(page.locator('#embosser_version_1')).toBeFocused();
    await expect(page.locator('#embosser_version_1')).toBeChecked();
  });

  test('choosing Version 2 rearranges the form and announces itself once', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);

    await expect(page.locator('#v2-keyed-cutouts-selection')).toBeHidden();
    await expect(page.locator('#gear-rollers-selection')).toBeVisible();
    await expect(page.locator('#cylinder-seam-offset-row')).toBeVisible();
    // The prototype notice is gone (D-7, 2026-09-20).
    await expect(page.locator('#v2-prototype-note')).toHaveCount(0);

    await selectVersion2(page);

    // The tactile seam arrow is the Version 2 default (D-4, 2026-09-24): the
    // style moves with the version, the ONE announcement says so, and the
    // move persists like a click on the radio would.
    await expect(page.locator('#a11y-status')).toHaveText(`${S_V10_ON} ${S_V16_STYLE_MOVED}`);
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeEnabled();
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_indicator_mode'))).toBe('tactile');
    await expect(page.locator('#v2-keyed-cutouts-selection')).toBeVisible();
    await expect(page.locator('#v2_key_clearance_mm')).toHaveValue('0.110');

    // The gear choice stays visible - it is a menu item, not a beta toggle to
    // hide - and stays on Standard (the API still refuses gears with Version 2
    // until fixed Version 2 gears ship in phase B6).
    await expect(page.locator('#gear-rollers-selection')).toBeVisible();
    await expect(page.locator('#gear_mode_standard')).toBeChecked();

    // The polygonal cutout and the seam offset are inert when the keyed cutout
    // IS the hole.
    await expect(page.locator('#cylinder-cutout-radius-row')).toBeHidden();
    await expect(page.locator('#cylinder-cutout-sides-row')).toBeHidden();
    await expect(page.locator('#cylinder-seam-offset-row')).toBeHidden();

    // The preset barrel lands on top of whatever card stock is selected.
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(V2_DIAMETER);
    await expect(page.locator('#cylinder_height_mm')).toHaveValue(V2_HEIGHT);
    await expect(page.locator('#seam_offset_deg')).toHaveValue('0');

    // D-V10: A and B are a matched, differently keyed pair, so the pair is the
    // useful output - and since 2026-09-21 every run is the pair unless one
    // cylinder is chosen, so there is no Generate Both button to reveal.
    expect(await page.locator('#generate-both-btn').count()).toBe(0);
  });

  test('going back to Version 1 restores the dials the user had', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    const before = await page.locator('#cylinder_diameter_mm').inputValue();

    await selectVersion2(page);
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(V2_DIAMETER);
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();

    // The style the user had comes back with the dials (D-4), with no clause
    // added to the Version 1 sentence.
    await page.locator('#embosser_version_1').check();
    await expect(page.locator('#a11y-status')).toHaveText(S_V10_OFF);
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(before);
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeChecked();
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_indicator_mode'))).toBe('visual');
    await expect(page.locator('#gear-rollers-selection')).toBeVisible();
    await expect(page.locator('#cylinder-seam-offset-row')).toBeVisible();
  });

  test('choosing Version 2 leaves a fixed-gear choice alone and announces the version with the gear notes', async ({
    page,
  }) => {
    // Since phase B6 of the 2026-09-20 programme the Version 2 embosser has
    // its own fixed gears, so the C2 guard that reset the choice (S-M13) is
    // gone: the saved preference survives, and the ONE announcement is S-V10
    // with the notes the gear refresh raised (S3 on the default cutout dial),
    // composed and deferred exactly as the gear listener's own is.
    await openApp(page);
    await page.locator('#gear_mode_fixed').check();
    await expect(page.locator('#gear_mode_fixed')).toBeChecked();

    await selectVersion2(page);
    await expect(page.locator('#gear_mode_fixed')).toBeChecked();
    await expect(page.locator('#gear_mode_standard')).not.toBeChecked();
    await expect(page.locator('#a11y-status')).toHaveText(`${S_V10_ON} ${S_V16_STYLE_MOVED} ${S3_CUTOUT_NOTE}`);
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_gear_rollers_enabled'))).toBe('1');
    // The preset barrel is already the fixed gears' 30.8 x 54, so no size note.
    await expect(page.locator('#gear-size-warning')).toBeHidden();
  });

  test('the Version 2 gear size note uses the Version 2 barrel and its own sentence', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    await selectVersion2(page);
    await page.locator('#gear_mode_fixed').check();
    await expect(page.locator('#gear-size-warning')).toBeHidden();

    // S-M10 lands one tick after the click; a dial edited before then loses its S-V5 to it.
    await expect(page.locator('#a11y-status')).toContainText(S_M10_FIXED);

    // 52 is the VERSION 1 gear barrel: right for Version 1 gears, off-size here.
    await setDial(page, 'cylinder_height_mm', '52');
    await expect(page.locator('#gear-size-warning')).toBeVisible();
    await expect(page.locator('#gear-size-message')).toContainText(S_G1_SIZE_START);
    await expect(page.locator('#gear-size-message')).toContainText('Received 30.8 mm x 52 mm.');
    // S-V5 names the same limit and, written last, is what the live region holds.
    await expect(page.locator('#v2-size-warning')).toBeVisible();
    await expect(page.locator('#a11y-status')).toContainText(S_V5_SIZE_START);

    await setDial(page, 'cylinder_height_mm', V2_HEIGHT);
    await expect(page.locator('#gear-size-warning')).toBeHidden();
    await expect(page.locator('#v2-size-warning')).toBeHidden();
  });

  test('Version 2 with Simplified gears is accepted and exports one fused roller', async ({ page }) => {
    test.slow();
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await selectVersion2(page);
    await page.locator('#gear_mode_fixed').check();
    await expect(page.locator('#gear_mode_fixed')).toBeChecked();
    await expect(page.locator('#embosser_version_2')).toBeChecked();

    const state = watchGeometrySpecRequests(page);
    const statuses: number[] = [];
    page.on('response', (response) => {
      if (response.url().includes('/geometry_spec')) statuses.push(response.status());
    });
    await generate(page, state, 1);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });

    // Both keys on the wire, and the API accepts the pair (the S-V7 gate is retired).
    const settings = (state.bodies[0] as { settings: Record<string, unknown> }).settings;
    expect(settings.embosser_version).toBe(2);
    expect(settings.gear_rollers_enabled).toBe(1);
    expect(statuses[0]).toBe(200);

    // ONE prefix for the fused run, not the two single-feature sentences.
    const status = page.locator('#a11y-status');
    await expect(status).toContainText(S_G2_READY);
    await expect(status).not.toContainText(S5_GEARS_READY);
    await expect(status).not.toContainText(S_V8_READY);

    // Geared_ then V2_: the two segments compose without a new rule.
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#download-stl-btn').click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('Embossing_Cylinder_Geared_V2_0.4_abc.stl');

    // The fused roller: the 54 mm barrel plus a 10 mm gear at each end.
    const { triangles, zMin, zMax } = await stlBounds(download);
    expect(triangles).toBeGreaterThan(1000);
    expect(zMax - zMin).toBeCloseTo(74, 2);
  });

  test('the size note appears off-size and clears at the preset size', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    await selectVersion2(page);

    await expect(page.locator('#v2-size-warning')).toBeHidden();

    // 30.5 is the off-size value here because it is NOT the preset. It was
    // the preset until 2026-08-30 and 30.8 was the off-size example; they
    // swapped when the barrel walked back to Version 1's size.
    await setDial(page, 'cylinder_diameter_mm', '30.5');
    await expect(page.locator('#v2-size-warning')).toBeVisible();
    await expect(page.locator('#v2-size-message')).toContainText(S_V5_SIZE_START);
    // D-V15: a warning, never a rejection — Generate stays available.
    await expect(page.locator('#action-btn')).toBeEnabled();

    await setDial(page, 'cylinder_diameter_mm', V2_DIAMETER);
    await expect(page.locator('#v2-size-warning')).toBeHidden();
  });

  test('the clearance dial is bounded at the source and refuses 0.51', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    await selectVersion2(page);

    const dial = page.locator('#v2_key_clearance_mm');
    expect(await dial.getAttribute('min')).toBe('0');
    expect(await dial.getAttribute('max')).toBe('0.5');
    expect(await dial.getAttribute('step')).toBe('0.005');

    // 0.5 is legal; 0.51 is not. The bound lives on the input, so the browser
    // itself refuses it — no hand-rolled check to drift out of step.
    await setDial(page, 'v2_key_clearance_mm', '0.5');
    expect(await dial.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(true);
    await expect(page.locator('#action-btn')).toBeEnabled();

    await setDial(page, 'v2_key_clearance_mm', '0.51');
    expect(await dial.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(false);

    // And the shipped default must be a whole number of steps, or the dial
    // would be :invalid on load and kill Generate silently.
    await setDial(page, 'v2_key_clearance_mm', '0.110');
    expect(await dial.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(true);
  });

  test('the recommended cell count fits the barrel, and nothing warns on load', async ({
    page,
  }) => {
    await openApp(page);
    const before = await page.locator('#grid_columns').inputValue();

    await selectVersion2(page);

    // The invariant that outlived the barrel change: whatever count Version 2
    // recommends, the seam-collision check must not fire on it. At the
    // prototype's original 30.1 mm barrel that forced the recommendation one
    // cell BELOW Version 1's, because 15 columns left 3.6 mm where a cell's
    // dots need 4.0. The 30.5 mm barrel (2026-08-29) leaves 4.8 mm and the
    // 30.8 mm one (2026-08-30) leaves 5.76, so the two versions agree and the
    // special case was removed.
    expect(await page.locator('#grid_columns').inputValue()).toBe(before);

    // Neither the seam-collision warning nor the row-overflow one may fire.
    await expect(page.locator('#tactile-gap-warning')).toBeHidden();
    await expect(page.locator('#cylinder-overflow-warning')).toBeHidden();
    // From a visual start the style moved with the version (D-4), so the one
    // announcement carries S-V16; no size or gap note rides with it.
    await expect(page.locator('#a11y-status')).toHaveText(`${S_V10_ON} ${S_V16_STYLE_MOVED}`);
  });

  test('the request gains exactly the two Version 2 keys and loses none', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('abc');

    const state = watchGeometrySpecRequests(page);
    await generate(page, state, 1);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });

    await selectVersion2(page);
    await generate(page, state, 2);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });

    const off = (state.bodies[0] as { settings: Record<string, unknown> }).settings;
    const on = (state.bodies[1] as { settings: Record<string, unknown> }).settings;

    const added = Object.keys(on).filter((k) => !(k in off));
    const removed = Object.keys(off).filter((k) => !(k in on));
    expect(added.sort()).toEqual(['embosser_version', 'v2_key_clearance_mm']);
    expect(removed).toEqual([]);
    expect(on.embosser_version).toBe(2);
    expect(on.v2_key_clearance_mm).toBe(0.110);
    // Same key set, one changed value: Version 2 moved the style to tactile
    // (D-4), which rides in the key every body already carries.
    expect(off.indicator_mode).toBe('visual');
    expect(on.indicator_mode).toBe('tactile');

    // Version 2 is cylinders-only, and the gear flag must never ride along.
    expect((state.bodies[1] as { shape_type: string }).shape_type).toBe('cylinder');
    expect('gear_rollers_enabled' in on).toBe(false);
  });

  test('downloads carry the V2 segment and the ready message says so', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await selectVersion2(page);

    const state = watchGeometrySpecRequests(page);
    await generate(page, state, 1);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });

    // S-V8 rides in the ready announcement rather than as a second write: the
    // live region holds one message at a time.
    await expect(page.locator('#a11y-status')).toContainText(S_V8_READY);
    expect(await downloadName(page)).toBe('Embossing_Cylinder_V2_0.4_abc.stl');

    await selectCylinders(page, 'negative');
    await generate(page, state, 2);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });
    expect(await downloadName(page)).toBe('Counter_Cylinder_V2_0.4_abc.stl');
  });

  test('a Version 2 pair run names the combined file with the V2 segment', async ({ page }) => {
    test.slow();
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await selectVersion2(page);

    await selectCylinders(page, 'both');
    const status = page.locator('#pair-status');
    let ready = false;
    for (let attempt = 0; attempt < 8 && !ready; attempt++) {
      await page.locator('#action-btn').click();
      try {
        await expect(status).toContainText('Both cylinders are ready', { timeout: 120_000 });
        ready = true;
      } catch (error) {
        const text = (await status.textContent()) ?? '';
        if (!/could not be generated/.test(text)) throw error;
        await page.waitForTimeout(1500);
      }
    }
    expect(ready).toBe(true);

    await expect(page.locator('#download-stl-btn')).toBeVisible();
    expect(await downloadName(page)).toBe('Cylinder_Pair_V2_0.4_abc.stl');
  });

  test('the choice survives a reload and Reset to defaults undoes it', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    await selectVersion2(page);

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#indicator-mode-selection');

    await expect(page.locator('#embosser_version_2')).toBeChecked();
    // The card-thickness preset rewrites the diameter on every load, so this
    // also proves the Version 2 override is re-applied AFTER it.
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(V2_DIAMETER);
    // The tactile default persisted with the version (D-4).
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();
    // A load restore is not a user action and must announce nothing.
    await expect(page.locator('#a11y-status')).toHaveText('');

    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#embosser_version_1')).toBeChecked();
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeChecked();
    await expect(page.locator('#v2_key_clearance_mm')).toHaveValue('0.110');
    expect(
      await page.evaluate(
        () => (document.getElementById('cylinder-seam-offset-row') as HTMLElement).hidden,
      ),
    ).toBe(false);
  });

  test('a visual style chosen in Version 2 is kept, and a reload does not overrule it', async ({ page }) => {
    // D-4: a default, not a lock. The user may go back to visual markers in
    // Version 2, and the silent load restore must never move it again.
    await openApp(page);
    await selectVersion2(page);
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();

    await page.locator('input[name="indicator_mode"][value="visual"]').check();
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_indicator_mode'))).toBe('visual');

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#indicator-mode-selection');
    await expect(page.locator('#embosser_version_2')).toBeChecked();
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeChecked();
    await expect(page.locator('#a11y-status')).toHaveText('');

    // Going back to Version 1 gives back the style the user had on the way in
    // (visual) - which is also what they chose, so nothing moves.
    await page.locator('#embosser_version_1').check();
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeChecked();
  });

  test('with Double-sided on, a version change leaves the locked tactile style alone', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeDisabled();

    // Nothing moved, so the announcement is the bare version sentence.
    await selectVersion2(page);
    await expect(page.locator('#a11y-status')).toHaveText(S_V10_ON);
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();
    await expect(page.locator('#indicator-mode-lock-note')).toBeVisible();

    await page.locator('#embosser_version_1').check();
    await expect(page.locator('#a11y-status')).toHaveText(S_V10_OFF);
    await expect(page.locator('input[name="indicator_mode"][value="tactile"]')).toBeChecked();
    await expect(page.locator('input[name="indicator_mode"][value="visual"]')).toBeDisabled();
  });

  test('the card stock stays 0.4 in Version 2 rather than flipping to Custom', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    await selectVersion2(page);

    // Version 2's forced barrel matches no thickness preset, so before the fix
    // any dial edit re-detected "custom", renamed the downloads and persisted a
    // card stock the user never chose.
    await setDial(page, 'cylinder_height_mm', V2_HEIGHT);
    await expect(page.locator('input[name="card_thickness_preset"][value="0.4"]')).toBeChecked();
  });

  test('a card stock chosen after Version 2 keeps the 54 mm barrel on the dial and on the wire', async ({ page }) => {
    // Both card-stock presets carry the Version 1 barrel (30.8 x 52). Choosing
    // a preset AFTER Version 2 used to write that 52 back onto the dial, and
    // the size gate is a warning, not a rejection (D-V15) - so a 52 mm
    // Version 2 cylinder was printed from the live site on 2026-09-20. This is
    // the natural order for anyone working down the form: version first,
    // card stock later.
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await openExpertDimensions(page);
    await selectVersion2(page);
    await expect(page.locator('#cylinder_height_mm')).toHaveValue(V2_HEIGHT);

    // The preset toast lands in #error-text, which generate() reads on slow
    // runs, so clear it before generating.
    await page.locator('input[name="card_thickness_preset"][value="0.3"]').check();
    await page.evaluate(() => { const t = document.getElementById('error-text'); if (t) t.textContent = ''; });
    await expect(page.locator('#cylinder_height_mm')).toHaveValue(V2_HEIGHT);
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(V2_DIAMETER);
    await expect(page.locator('#v2-size-warning')).toBeHidden();

    const state = watchGeometrySpecRequests(page);
    await generate(page, state, 1);
    const cylinder = (state.bodies[0] as { cylinder_params: Record<string, string> }).cylinder_params;
    expect(Number(cylinder.height_mm)).toBe(54);
    expect(Number(cylinder.diameter_mm)).toBe(30.8);

    // And back to Version 1 still restores the dials the user had before
    // Version 2 (the snapshot, not the preset).
    await page.locator('#embosser_version_1').check();
    await expect(page.locator('#cylinder_height_mm')).toHaveValue('52');
  });
});
