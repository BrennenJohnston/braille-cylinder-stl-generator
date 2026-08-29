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

// Signed 2026-08-28 by Brennen at the Phase 05 gate. Reword only with his sign-off.
const S_V1_LEGEND = 'Embosser version';
const S_V3_NOTE =
  'Choose Version 2 only if you are building the Version 2 embosser, which uses keyed gear pegs. Version 1 stays supported.';
const S_V4_PROTOTYPE =
  'Version 2 is a work-in-progress prototype. Its cylinder size, cutouts and fit may change as testing continues. It fits only gears with R14 pegs; earlier pegs do not enter the holes.';
const S_V5_SIZE_START = 'The Version 2 embosser expects a 30.1 mm x 52 mm cylinder.';
const S_V8_READY = 'Cylinder generated for the Version 2 embosser (prototype).';
const S_V10_ON = 'Version 2 selected: keyed gear-peg cutouts, 30.1 mm cylinder.';
const S_V10_OFF = 'Version 1 selected.';

// The Version 2 preset barrel (D-V4), owned by app/geometry/version2.py.
const V2_DIAMETER = '30.1';
const V2_HEIGHT = '52';

// Same transient failures the other beta specs tolerate: both workers signal
// readiness asynchronously and Firefox is slower to spin them up.
const TRANSIENT_ERRORS =
  /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

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

test.describe('Embosser Version 2 (prototype)', () => {
  test('the selector is in the header, defaults to Version 1, and is keyboard-operable', async ({
    page,
  }) => {
    await openApp(page);

    // In the banner landmark, not buried in the form.
    expect(
      await page.evaluate(
        () => !!document.querySelector('header.site-header #embosser-version-selection'),
      ),
    ).toBe(true);

    await expect(page.locator('#embosser_version_1')).toBeChecked();
    await expect(page.locator('#embosser_version_2')).not.toBeChecked();

    // S-V1 is the group's accessible name; S-V3 is its description.
    await expect(page.locator('#embosser-version-selection legend')).toHaveText(S_V1_LEGEND);
    await expect(page.locator('#embosser-version-note')).toHaveText(S_V3_NOTE);
    expect(
      await page.evaluate(() =>
        document
          .querySelector('#embosser-version-selection fieldset')
          ?.getAttribute('aria-describedby'),
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

    await expect(page.locator('#v2-prototype-note')).toBeHidden();
    await expect(page.locator('#v2-keyed-cutouts-selection')).toBeHidden();
    await expect(page.locator('#gear-rollers-selection')).toBeVisible();
    await expect(page.locator('#cylinder-seam-offset-row')).toBeVisible();

    await selectVersion2(page);

    await expect(page.locator('#a11y-status')).toHaveText(S_V10_ON);
    await expect(page.locator('#v2-prototype-note')).toBeVisible();
    await expect(page.locator('#v2-prototype-note')).toContainText(S_V4_PROTOTYPE);
    await expect(page.locator('#v2-keyed-cutouts-selection')).toBeVisible();
    await expect(page.locator('#v2_key_clearance_mm')).toHaveValue('0.15');

    // The gears BETA is Version 1 only (D-V6): hidden AND unchecked, because a
    // hidden checkbox that stayed on would still be read at generate time.
    await expect(page.locator('#gear-rollers-selection')).toBeHidden();
    await expect(page.locator('#gear_rollers_enabled')).not.toBeChecked();

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
    // useful output and the signed A/B labels are reused.
    await expect(page.locator('#generate-both-btn')).toBeVisible();
  });

  test('going back to Version 1 restores the dials the user had', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    const before = await page.locator('#cylinder_diameter_mm').inputValue();

    await selectVersion2(page);
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(V2_DIAMETER);

    await page.locator('#embosser_version_1').check();
    await expect(page.locator('#a11y-status')).toHaveText(S_V10_OFF);
    await expect(page.locator('#cylinder_diameter_mm')).toHaveValue(before);
    await expect(page.locator('#gear-rollers-selection')).toBeVisible();
    await expect(page.locator('#cylinder-seam-offset-row')).toBeVisible();
    await expect(page.locator('#v2-prototype-note')).toBeHidden();
  });

  test('the size note appears off-size and clears at the preset size', async ({ page }) => {
    await openApp(page);
    await openExpertDimensions(page);
    await selectVersion2(page);

    await expect(page.locator('#v2-size-warning')).toBeHidden();

    await setDial(page, 'cylinder_diameter_mm', '30.8');
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
    expect(await dial.getAttribute('step')).toBe('0.01');

    // 0.5 is legal; 0.51 is not. The bound lives on the input, so the browser
    // itself refuses it — no hand-rolled check to drift out of step.
    await setDial(page, 'v2_key_clearance_mm', '0.5');
    expect(await dial.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(true);
    await expect(page.locator('#action-btn')).toBeEnabled();

    await setDial(page, 'v2_key_clearance_mm', '0.51');
    expect(await dial.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(false);

    // And the shipped default must be a whole number of steps, or the dial
    // would be :invalid on load and kill Generate silently.
    await setDial(page, 'v2_key_clearance_mm', '0.15');
    expect(await dial.evaluate((el: HTMLInputElement) => el.checkValidity())).toBe(true);
  });

  test('the visual cell recommendation drops by one, and nothing warns on load', async ({
    page,
  }) => {
    await openApp(page);
    const before = await page.locator('#grid_columns').inputValue();

    await selectVersion2(page);

    // A 30.1 mm barrel is 2.2 mm less circumference than 30.8 — in visual mode
    // exactly one braille cell. Without this the page recommended a layout that
    // checkPhysicalFit() warns against on the same screen.
    expect(Number(await page.locator('#grid_columns').inputValue())).toBe(Number(before) - 1);

    // And the seam-collision warning must not fire at the recommended layout.
    await expect(page.locator('#cylinder-overflow-warning')).toBeHidden();
    await expect(page.locator('#a11y-status')).toHaveText(S_V10_ON);
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
    expect(on.v2_key_clearance_mm).toBe(0.15);

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

    await page.locator('input[name="plate_type"][value="negative"]').check();
    await generate(page, state, 2);
    await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });
    expect(await downloadName(page)).toBe('Counter_Cylinder_V2_0.4_abc.stl');
  });

  test('a Version 2 pair run names the combined file with the V2 segment', async ({ page }) => {
    test.slow();
    await openApp(page);
    await page.locator('#auto-text').fill('abc');
    await selectVersion2(page);

    const status = page.locator('#pair-status');
    let ready = false;
    for (let attempt = 0; attempt < 8 && !ready; attempt++) {
      await page.locator('#generate-both-btn').click();
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

    await expect(page.locator('#pair-downloads')).toBeVisible();
    expect(await downloadName(page, '#download-pair-btn')).toBe('Cylinder_Pair_V2_0.4_abc.stl');
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
    // A load restore is not a user action and must announce nothing.
    await expect(page.locator('#a11y-status')).toHaveText('');

    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#embosser_version_1')).toBeChecked();
    await expect(page.locator('#v2_key_clearance_mm')).toHaveValue('0.15');
    expect(
      await page.evaluate(
        () => (document.getElementById('cylinder-seam-offset-row') as HTMLElement).hidden,
      ),
    ).toBe(false);
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
});
