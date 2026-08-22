/**
 * E2E tests for the Double-Sided Card (interpoint) beta.
 *
 * When the beta toggle is ON, the app generates a paired set: Cylinder A
 * (plate_type "positive") carries the front's raised dots plus 1:1 recesses
 * for the back text, and Cylinder B (plate_type "negative") carries the back's
 * raised dots plus 1:1 recesses paired to the front — no universal counter
 * grid. When the toggle is OFF the app must behave exactly as before the
 * feature existed (public training videos depend on the single-sided flow),
 * so the off-state payload is pinned to a pre-feature snapshot.
 *
 * The beta ships with FIXED footprints — no dials (decided 2026-08-16;
 * preset keying added 2026-08-20): the wire carries the ds package for the
 * selected card-stock preset (0.3 → Option B, dot ⌀1.2 + bowl ⌀1.3; 0.4 →
 * the Q2 print-matrix winner, dot ⌀1.2 × 1.0 mm tall + bowl ⌀1.4). The
 * offsets (1.25/1.25 mm) stay adjustable by design, so the live gap warning
 * is exercised by injecting the offset dial inputs checkDoubleSidedGap()
 * reads, and the offset range is asserted at the backend via direct POSTs.
 *
 * @see docs/specifications/STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Pre-feature payload snapshots
// ---------------------------------------------------------------------------
// Captured from the live UI at commit 330df8f's parent chain BEFORE the
// Phase 07 wire change (auto text "abc", tactile mode, default cylinder,
// fresh profile) and proven byte-identical to the post-feature off-state by
// fc /b in Phases 07 and 08. The toggle-off payload must deep-equal these:
// any added key (double_sided_enabled, back_lines, ds_*) is a regression.
const BASELINE_SETTINGS = {
  grid_columns: '14',
  grid_rows: '4',
  cell_spacing: '6.5',
  line_spacing: '10',
  dot_spacing: '2.5',
  emboss_dot_base_diameter: '1.5',
  emboss_dot_height: '0.8',
  emboss_dot_flat_hat: '0.4',
  hemi_counter_dot_base_diameter: '1.6',
  bowl_counter_dot_base_diameter: '1.8',
  counter_dot_base_diameter: '1.8',
  counter_dot_depth: '0.8',
  use_bowl_recess: 1,
  recess_shape: 1,
  cone_counter_dot_base_diameter: '1.9',
  cone_counter_dot_height: '0.7',
  cone_counter_dot_flat_hat: '1',
  card_width: '90',
  card_height: '52',
  card_thickness: '2',
  braille_x_adjust: '0',
  braille_y_adjust: '0',
  use_rounded_dots: 1,
  dot_shape: 'rounded',
  rounded_dot_diameter: '1',
  rounded_dot_height: '0.5',
  rounded_dot_base_diameter: '1.5',
  rounded_dot_base_height: '0.5',
  rounded_dot_cylinder_height: '0.5',
  rounded_dot_dome_diameter: '1',
  rounded_dot_dome_height: '0.5',
  indicator_shapes: 1,
  indicator_mode: 'tactile',
  tactile_indicator_width: '4',
  tactile_indicator_length: '10',
  tactile_indicator_raise: '0.5',
  tactile_recess_clearance: '0.2',
  tactile_recess_extra_depth: '0.2',
};

const BASELINE_CYLINDER_PARAMS = {
  diameter_mm: '30.8',
  height_mm: '52',
  polygonal_cutout_radius_mm: '13',
  polygonal_cutout_sides: '12',
  seam_offset_deg: '0',
};

const BASELINE_POSITIVE = {
  lines: ['⠁⠃⠉', '', '', ''],
  original_lines: ['a', '', '', ''],
  placement_mode: 'auto',
  grade: 'g2',
  plate_type: 'positive',
  shape_type: 'cylinder',
  cylinder_params: BASELINE_CYLINDER_PARAMS,
  per_line_language_tables: ['en-ueb-g2.ctb', 'en-ueb-g2.ctb', 'en-ueb-g2.ctb', 'en-ueb-g2.ctb'],
  settings: BASELINE_SETTINGS,
};

const BASELINE_NEGATIVE = {
  lines: ['', '', '', ''],
  original_lines: ['a', '', '', ''],
  placement_mode: 'auto',
  grade: 'g2',
  plate_type: 'negative',
  shape_type: 'cylinder',
  cylinder_params: BASELINE_CYLINDER_PARAMS,
  per_line_language_tables: [],
  settings: BASELINE_SETTINGS,
};

// The Phase 04 fixture pair: front "abc" → 5 dots, back "def" → 8 dots.
const FRONT_BRAILLE = '⠁⠃⠉';
const BACK_BRAILLE = '⠙⠑⠋';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#indicator-mode-selection');
}

/** Capture /geometry_spec payloads, aborting each request so no CSG runs. */
async function interceptGeometrySpec(page: Page) {
  const state: { bodies: Array<Record<string, unknown> | null> } = { bodies: [] };
  await page.route('**/geometry_spec', async (route) => {
    try {
      state.bodies.push(route.request().postDataJSON());
    } catch {
      state.bodies.push(null);
    }
    await route.abort();
  });
  return state;
}

// Errors the click-and-retry loops tolerate: the Manifold and liblouis
// workers both signal readiness asynchronously (Firefox is slower to spin
// them up, so the first clicks fail fast with "requires the Manifold 3D
// engine" or a translation failure that succeeds on retry), #error-text
// doubles as an info-progress region, and an intercepted (aborted) request
// leaves a stale "STL generation failed" behind. The inputs here ('abc',
// 'def') always translate, so a persistent translation failure still
// surfaces once the retries are exhausted.
const TRANSIENT_ERRORS = /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

/** Click Generate and wait until the n-th payload has been captured. */
async function generate(page: Page, state: { bodies: unknown[] }, n: number) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 3000 && state.bodies.length < n; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.bodies.length >= n) return;

    // #error-text is also where the app puts INFORMATIONAL notices - the card
    // thickness preset's "All parameters updated." lands there when a preset is clicked (before 2026-08-22, also on load), with
    // class `info` on the wrapper. Treating that as a blocking error turns a
    // notice into a spurious failure, so only fail when it is not marked info.
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

/** Record every /geometry_spec response (status + parsed spec) without interfering. */
function watchGeometrySpec(page: Page) {
  const state: { responses: Array<{ status: number; spec: Record<string, unknown> | null }> } = { responses: [] };
  page.on('response', async (response) => {
    if (!response.url().includes('/geometry_spec')) return;
    let spec: Record<string, unknown> | null = null;
    try {
      spec = await response.json();
    } catch {
      spec = null;
    }
    state.responses.push({ status: response.status(), spec });
  });
  return state;
}

/**
 * Record every /geometry_spec REQUEST body without interfering with the run.
 * interceptGeometrySpec() aborts the request, which is right for payload-shape
 * assertions but stops the pair run dead; this watches a real run instead.
 */
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

/**
 * Run a full generation (request + client-side CSG) and wait for the button
 * to reach its download state, returning the n-th /geometry_spec response.
 */
async function generateFully(
  page: Page,
  state: { responses: Array<{ status: number; spec: Record<string, unknown> | null }> },
  n: number,
) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 8000 && state.responses.length < n; waited += 200) {
      await page.waitForTimeout(200);
    }
    if (state.responses.length >= n) {
      // Since 2026-08-18 #action-btn never becomes the download control — a
      // separate #download-stl-btn appears instead, so a control never changes
      // identity under a screen-reader user's focus. Waiting on that button is
      // the same signal the old data-state="download" wait gave, and the
      // generate button is additionally pinned to staying itself.
      await expect(page.locator('#download-stl-btn')).toBeVisible({ timeout: 90_000 });
      await expect(page.locator('#action-btn')).toHaveAttribute('data-state', 'generate');
      return state.responses[n - 1];
    }
    // #error-text is also where the app puts INFORMATIONAL notices - the card
    // thickness preset's "All parameters updated." lands there when a preset is clicked (before 2026-08-22, also on load), with
    // class `info` on the wrapper. Treating that as a blocking error turns a
    // notice into a spurious failure, so only fail when it is not marked info.
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

/** Click the Download STL button and return the filename the browser was offered. */
async function downloadName(page: Page): Promise<string> {
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#download-stl-btn').click();
  const download = await downloadPromise;
  return download.suggestedFilename();
}

/** Click one of the double-sided pair buttons and return the offered filename. */
async function pairDownloadName(page: Page, which: 'a' | 'b'): Promise<string> {
  const downloadPromise = page.waitForEvent('download');
  await page.locator(`#download-cylinder-${which}-btn`).click();
  const download = await downloadPromise;
  return download.suggestedFilename();
}

/**
 * Fill the back text and wait for the overflow warning to appear. Under
 * parallel load Firefox can still be starting liblouis, and
 * computeBackOverflow() deliberately bails out rather than guess when the
 * translation is unavailable — so the warning simply never arrives from that
 * first fill. Re-filling dispatches a fresh input event and re-runs the
 * debounced check once the worker is up.
 */
async function fillBackUntilOverflow(page: Page, text: string) {
  const warning = page.locator('#ds-back-overflow-warning');
  let lastError: unknown = null;
  for (let attempt = 0; attempt < 12; attempt++) {
    await page.locator('#back-text').fill('');
    await page.locator('#back-text').fill(text);
    try {
      await expect(warning).toBeVisible({ timeout: 3000 });
      return;
    } catch (error) {
      lastError = error;
    }
  }
  throw new Error(`#ds-back-overflow-warning never appeared: ${lastError}`);
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

/**
 * Press Preview Braille Translation and wait for the expected braille to show.
 *
 * The preview calls liblouis directly, so a press landing before the worker is
 * up renders "Liblouis worker not initialized" into #preview-content instead of
 * braille. Every other worker-dependent press in this suite already guards for
 * that; this one did not, and lost the race on Firefox under parallel load.
 * Only that documented not-ready text is retried — anything else is a real
 * failure and is rethrown.
 */
async function previewBraille(page: Page, settled: () => Promise<void>) {
  const preview = page.locator('#preview-content');
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#preview-braille-btn').click();
    try {
      await settled();
      return;
    } catch (error) {
      const text = (await preview.textContent()) ?? '';
      if (!/not initialized|unavailable on this deployment/.test(text)) throw error;
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('The liblouis worker never became ready for the braille preview');
}

/** Turn the beta on through the real UI and fill both sides of the card. */
async function enableBeta(page: Page, frontText: string, backText: string) {
  await page.locator('#auto-text').fill(frontText);
  await page.locator('#double_sided_enabled').check();
  await page.locator('#back-text').fill(backText);
}

test.describe('Double-Sided Card beta', () => {
  test.describe.configure({ timeout: 120_000 });

  test('toggle off sends the pre-feature payload for both plates', async ({ page }) => {
    await openApp(page);
    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    await page.locator('#auto-text').fill('abc');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    // Deep equality both ways: a missing key fails, and so does any added
    // key — no double_sided_enabled, no back_lines, no ds_* anywhere.
    expect(spec.bodies[0]).toEqual(BASELINE_POSITIVE);

    await page.locator('input[name="plate_type"][value="negative"]').check();
    await generate(page, spec, 2);
    expect(spec.bodies[1]).toEqual(BASELINE_NEGATIVE);
  });

  test('toggle on locks the Row Indicator Style to tactile and restores it off', async ({ page }) => {
    await openApp(page);
    const toggle = page.locator('#double_sided_enabled');
    const visual = page.locator('input[name="indicator_mode"][value="visual"]');
    const tactile = page.locator('input[name="indicator_mode"][value="tactile"]');

    await expect(visual).toBeChecked();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('#front-entry-legend')).toHaveText('Enter Text for Braille Translation');

    await toggle.check();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('#double-sided-section')).toBeVisible();
    await expect(tactile).toBeChecked();
    await expect(visual).toBeDisabled();
    await expect(page.locator('#indicator-mode-lock-note')).toBeVisible();
    await expect(page.locator('#front-entry-legend')).toHaveText('Front of Card — Enter Text for Braille Translation');

    await toggle.uncheck();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('#double-sided-section')).toBeHidden();
    await expect(visual).toBeEnabled();
    await expect(page.locator('#indicator-mode-lock-note')).toBeHidden();
    // The tactile selection is deliberately kept (no surprise snap-back).
    await expect(tactile).toBeChecked();
    await expect(page.locator('#front-entry-legend')).toHaveText('Enter Text for Braille Translation');
  });

  test('Cylinder A payload carries translated back_lines and the flat double-sided settings', async ({ page }) => {
    await openApp(page);
    await enableBeta(page, 'abc', 'def');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    const body = spec.bodies[0] as Record<string, unknown>;

    // back_lines is a TOP-LEVEL key beside lines (the request body has no
    // `text` object — text.back_lines is the saved-settings spelling), both
    // padded to grid_rows, both pure braille U+2800–U+28FF.
    expect(body.lines).toEqual([FRONT_BRAILLE, '', '', '']);
    expect(body.back_lines).toEqual([BACK_BRAILLE, '', '', '']);
    for (const line of body.back_lines as string[]) {
      expect(line).toMatch(/^[⠀-⣿]*$/);
    }

    // The settings object carries the FLAT CardSettings spellings — the
    // grouped double_sided.*_mm schema names would be silently ignored. The
    // footprints are the preset package: the default 0.4 preset sends the
    // Q2 print-matrix winner (decided 2026-08-20).
    const settings = body.settings as Record<string, unknown>;
    expect(settings.indicator_mode).toBe('tactile');
    expect(settings.double_sided_enabled).toBe(1);
    expect(Number(settings.interpoint_offset_x)).toBe(1.25);
    expect(Number(settings.interpoint_offset_y)).toBe(1.25);
    expect(Number(settings.ds_dot_base_diameter)).toBe(1.2);
    expect(Number(settings.ds_dot_base_height)).toBe(0.5);
    expect(Number(settings.ds_dot_dome_diameter)).toBe(1.0);
    expect(Number(settings.ds_dot_dome_height)).toBe(0.5);
    expect(Number(settings.ds_bowl_base_diameter)).toBe(1.4);
    expect(Number(settings.ds_bowl_depth)).toBe(0.5);

    // The 0.3 preset switches the wire to the Option B package (validated
    // 2026-08-17) without any ds dials existing. The preset toast lands in
    // #error-text, which generate() reads on slow runs, so clear it first.
    await page.locator('input[name="card_thickness_preset"][value="0.3"]').check();
    await page.evaluate(() => { const t = document.getElementById('error-text'); if (t) t.textContent = ''; });
    await generate(page, spec, 2);
    const settings03 = (spec.bodies[1] as Record<string, unknown>).settings as Record<string, unknown>;
    expect(Number(settings03.ds_dot_base_diameter)).toBe(1.2);
    expect(Number(settings03.ds_dot_base_height)).toBe(0.4);
    expect(Number(settings03.ds_dot_dome_diameter)).toBe(0.8);
    expect(Number(settings03.ds_dot_dome_height)).toBe(0.4);
    expect(Number(settings03.ds_bowl_base_diameter)).toBe(1.3);
    expect(Number(settings03.ds_bowl_depth)).toBe(0.5);
  });

  test('Cylinder B payload keeps the front braille for its 1:1 paired recesses', async ({ page }) => {
    await openApp(page);
    await enableBeta(page, 'abc', 'def');
    await page.locator('input[name="plate_type"][value="negative"]').check();

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    const body = spec.bodies[0] as Record<string, unknown>;

    // Single-sided negative sends empty lines; the double-sided counter
    // plate needs the front braille to place its paired recesses.
    expect(body.lines).toEqual([FRONT_BRAILLE, '', '', '']);
    expect(body.back_lines).toEqual([BACK_BRAILLE, '', '', '']);
    expect((body.settings as Record<string, unknown>).double_sided_enabled).toBe(1);
  });

  test('both cylinders generate paired raised+recessed specs and Cylinder A/B filenames', async ({ page }) => {
    await openApp(page);
    const responses = watchGeometrySpec(page);
    await enableBeta(page, 'abc', 'def');

    // Cylinder A: front ⠁⠃⠉ raised (5 dots) + back ⠙⠑⠋ recessed (8 dots),
    // raised seam arrows. No universal rows × columns × 6 grid.
    const a = await generateFully(page, responses, 1);
    expect(a.status).toBe(200);
    const aDots = (a.spec?.dots ?? []) as Array<{ is_recess: boolean }>;
    expect(aDots.filter((d) => d.is_recess === false).length).toBe(5);
    expect(aDots.filter((d) => d.is_recess === true).length).toBe(8);
    const aMarkers = (a.spec?.markers ?? []) as Array<{ is_recess: boolean }>;
    expect(aMarkers.length).toBe(4);
    expect(aMarkers.every((m) => m.is_recess === false)).toBe(true);
    expect(await downloadName(page)).toBe('Cylinder_A_0.4_abc.stl');

    // Cylinder B: the reverse — back raised, front recessed, recessed arrows.
    await page.locator('input[name="plate_type"][value="negative"]').check();
    const b = await generateFully(page, responses, 2);
    expect(b.status).toBe(200);
    const bDots = (b.spec?.dots ?? []) as Array<{ is_recess: boolean }>;
    expect(bDots.filter((d) => d.is_recess === false).length).toBe(8);
    expect(bDots.filter((d) => d.is_recess === true).length).toBe(5);
    const bMarkers = (b.spec?.markers ?? []) as Array<{ is_recess: boolean }>;
    expect(bMarkers.length).toBe(4);
    expect(bMarkers.every((m) => m.is_recess === true)).toBe(true);
    expect(await downloadName(page)).toBe('Cylinder_B_0.4_abc.stl');
  });

  test('single-sided downloads keep the existing filename', async ({ page }) => {
    await openApp(page);
    const responses = watchGeometrySpec(page);
    await page.locator('#auto-text').fill('abc');

    const result = await generateFully(page, responses, 1);
    expect(result.status).toBe(200);
    // The A/B naming applies to the double-sided flow only — the training
    // videos depend on the single-sided names staying exactly as they are.
    expect(await downloadName(page)).toBe('Embossing_Cylinder_0.4_abc.stl');
  });

  test('the live gap warning follows the card-stock preset package and the offsets', async ({ page }) => {
    await openApp(page);
    await page.locator('#double_sided_enabled').check();

    const warning = page.locator('#ds-gap-warning');
    const message = page.locator('#ds-gap-message');
    // The default 0.4 preset carries the Q2 package (dot 1.2 + bowl 1.4):
    // nominal gap 0.468 mm, below the 0.50 mm reliable line BY DESIGN (the
    // printed 0.428 mm ridge was measured printing clean on 2026-08-20), so
    // the warning is visible at the shipped defaults whenever the beta is on.
    await expect(warning).toBeVisible();
    await expect(message).toContainText('0.468 mm');
    await expect(message).toContainText('may come out thin or merged');

    // The 0.3 preset switches to Option B (dot 1.2 + bowl 1.3): gap 0.518 mm,
    // above the reliable line - quiet.
    await page.locator('input[name="card_thickness_preset"][value="0.3"]').check();
    await expect(warning).toBeHidden();

    // The offsets stay adjustable by design (D1), but their dials arrive with
    // a later phase, so inject the inputs checkDoubleSidedGap() reads (flat
    // CardSettings ids); page.fill() then dispatches real input events that
    // re-run the check through the form's input/change delegation.
    await page.evaluate(() => {
      const form = document.getElementById('braille-form');
      for (const [id, value] of [
        ['interpoint_offset_x', '1.25'],
        ['interpoint_offset_y', '1.25'],
      ]) {
        const input = document.createElement('input');
        input.type = 'number';
        input.step = '0.01';
        input.id = id;
        input.value = value;
        form?.appendChild(input);
      }
    });

    // Offset x 1.15 (y 1.25) on Option B: gap 0.449 mm - marginal, printable
    // but thin.
    await page.locator('#interpoint_offset_x').fill('1.15');
    await expect(warning).toBeVisible();
    await expect(message).toContainText('0.449 mm');
    await expect(message).toContainText('may come out thin or merged');

    // Both offsets 1.15: gap 0.376 mm - still the marginal variant.
    await page.locator('#interpoint_offset_y').fill('1.15');
    await expect(message).toContainText('0.376 mm');

    // Back to the shipped 1.25/1.25: gap 0.518 mm, quiet again.
    await page.locator('#interpoint_offset_x').fill('1.25');
    await page.locator('#interpoint_offset_y').fill('1.25');
    await expect(warning).toBeHidden();

    // The Q2 package at both offsets 1.15: gap 0.326 mm - under the 0.34 mm
    // nozzle floor, the "generation will be blocked" variant.
    await page.locator('#interpoint_offset_x').fill('1.15');
    await page.locator('#interpoint_offset_y').fill('1.15');
    await page.locator('input[name="card_thickness_preset"][value="0.4"]').check();
    await expect(warning).toBeVisible();
    await expect(message).toContainText('0.326 mm');
    await expect(message).toContainText('generation will be blocked');

    // Q2 at both offsets 1.17. The QUOTED gap is the nominal 0.355 mm, which
    // sits in the marginal band - but the printed ridge is 0.315 mm and the
    // backend rejects, so the box must say blocked (Brennen, 2026-08-21).
    // Before that decision this row read "may come out thin or merged" and the
    // user was then refused at generate time.
    await page.locator('#interpoint_offset_x').fill('1.17');
    await page.locator('#interpoint_offset_y').fill('1.17');
    await expect(message).toContainText('0.355 mm');
    await expect(message).toContainText('generation will be blocked');

    // And 1.19, one step further in: printed 0.343 mm clears the floor, so the
    // milder tail is correct there. The two rows bracket the band edge.
    await page.locator('#interpoint_offset_x').fill('1.19');
    await page.locator('#interpoint_offset_y').fill('1.19');
    await expect(message).toContainText('0.383 mm');
    await expect(message).toContainText('may come out thin or merged');
  });

  test('the backend rejects out-of-range double-sided payloads with HTTP 400', async ({ request }) => {
    // Mirror of tests/test_double_sided_validation.py at the Playwright layer:
    // the UI cannot send these (no dials), but saved-settings JSON or direct
    // callers can, so the gates must hold on the wire.
    const payload = (settingsOverrides: Record<string, unknown> = {}) => ({
      lines: [FRONT_BRAILLE, '', '', ''],
      back_lines: [BACK_BRAILLE, '', '', ''],
      plate_type: 'positive',
      shape_type: 'cylinder',
      grade: 'g1',
      settings: {
        double_sided_enabled: 1,
        indicator_mode: 'tactile',
        grid_columns: 14,
        grid_rows: 4,
        ...settingsOverrides,
      },
    });
    const post = (body: Record<string, unknown>) => request.post('/geometry_spec', { data: body });

    // Sanity: the Option B baseline itself is accepted.
    expect((await post(payload())).status()).toBe(200);
    // Gate 1: tactile lock.
    expect((await post(payload({ indicator_mode: 'visual' }))).status()).toBe(400);
    // Gate 2: interpoint offsets outside [1.15, 1.35] mm.
    expect((await post(payload({ interpoint_offset_x: 1.05 }))).status()).toBe(400);
    expect((await post(payload({ interpoint_offset_y: 1.4 }))).status()).toBe(400);
    // Gate 3: a ds_* value outside its settings.schema.json range.
    expect((await post(payload({ ds_bowl_depth: 9 }))).status()).toBe(400);
    // Gate 4: the printed ridge, -0.042 mm, is under the 0.34 mm floor. Since
    // 2026-08-21 this gate measures the recess's printed mouth (the 1.8 mm bowl
    // is cut as a hemisphere and comes out 2.12 mm across), so the nominal
    // 0.118 mm this used to quote is no longer the figure being compared.
    expect((await post(payload({ ds_dot_base_diameter: 1.5, ds_bowl_base_diameter: 1.8 }))).status()).toBe(400);
  });

  test('the beta toggle is reachable and operable by keyboard only', async ({ page }) => {
    await openApp(page);

    // Walk the tab order from the top of the document: the toggle must be
    // reachable without a pointer.
    let reached = false;
    for (let i = 0; i < 80; i++) {
      await page.keyboard.press('Tab');
      const id = await page.evaluate(() => document.activeElement?.id ?? '');
      if (id === 'double_sided_enabled') {
        reached = true;
        break;
      }
    }
    expect(reached, 'Tab never reached #double_sided_enabled').toBe(true);

    await page.keyboard.press('Space');
    await expect(page.locator('#double_sided_enabled')).toBeChecked();
    await expect(page.locator('#double_sided_enabled')).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('#double-sided-section')).toBeVisible();

    // The revealed section is next in the tab order and typeable.
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => document.activeElement?.id ?? '')).toBe('back-text');
    await page.keyboard.type('def');
    await expect(page.locator('#back-text')).toHaveValue('def');

    // Back to the toggle; Space turns the beta off again.
    await page.keyboard.press('Shift+Tab');
    expect(await page.evaluate(() => document.activeElement?.id ?? '')).toBe('double_sided_enabled');
    await page.keyboard.press('Space');
    await expect(page.locator('#double_sided_enabled')).not.toBeChecked();
    await expect(page.locator('#double-sided-section')).toBeHidden();
  });

  // -------------------------------------------------------------------------
  // Phase 06: coverage of everything Phases 02-04 added
  // -------------------------------------------------------------------------

  test('back text is BANA-wrapped across the rows on the wire', async ({ page }) => {
    await openApp(page);
    // Three rows of at most 11 cells at the default 14-column dial, so this
    // exercises wrapping without tripping the overflow warning.
    await enableBeta(page, 'abc', 'alpha bravo charlie delta echo');
    await expect(page.locator('#ds-back-overflow-warning')).toBeHidden();

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec, 1);
    const body = spec.bodies[0] as Record<string, unknown>;
    const settings = body.settings as Record<string, unknown>;
    const back = body.back_lines as string[];
    const rows = Number(settings.grid_rows);
    const columns = Number(settings.grid_columns);

    // back_lines is padded to exactly grid_rows, and nothing overruns the row.
    expect(back.length).toBe(rows);
    for (const line of back) {
      expect(line.length).toBeLessThanOrEqual(columns);
      // Runs of braille cells separated by single ASCII spaces. The word
      // separator really is U+0020, not the braille blank U+2800 — measured on
      // the wire 2026-08-18, on the FRONT lines too. That is deliberate:
      // braille_to_dots() in app/utils.py handles ' ' as an empty cell, so it
      // occupies one cell exactly as U+2800 would, and every other non-braille
      // character raises ValueError. Invariant 4 in
      // .clinerules/project-facts.md carries this as its one documented
      // exception (confirmed by Brennen 2026-08-18). Asserting the space is the
      // ONLY non-braille character keeps that exception from widening.
      expect(line).toMatch(/^(?:[⠀-⣿]+(?: [⠀-⣿]+)*)?$/);
    }
    // More than one row carries text, which is the wrap actually happening
    // rather than the whole string being dropped onto row 1.
    expect(back.filter((line) => line !== '').length).toBeGreaterThan(1);
    // Words are kept whole: no row ends mid-word by starting with a space.
    for (const line of back.filter((l) => l !== '')) {
      expect(line.startsWith(' ')).toBe(false);
    }
  });

  test('the back-of-card overflow warning appears, clears, and goes with the toggle', async ({ page }) => {
    await openApp(page);
    await enableBeta(page, 'abc', 'def');
    const warning = page.locator('#ds-back-overflow-warning');
    const message = page.locator('#ds-back-overflow-message');
    const tooLong =
      'This back of card text is far too long to fit on the rows that are available on a business card';

    await expect(warning).toBeHidden();

    await fillBackUntilOverflow(page, tooLong);
    await expect(message).toContainText('Back line 1');
    await expect(message).toContainText('are available');

    // The warning must also reach a screen reader. It is announced through the
    // shared #a11y-status region, never from the warning box itself: that box
    // is hidden between messages, so a live region on it is inserted into the
    // accessibility tree already holding its text, and an insertion is not a
    // change. See UI Interface Core Specifications section 4.10.
    await expect(page.locator('#a11y-status')).toContainText('Back line 1');

    // Fixing the text clears it.
    await page.locator('#back-text').fill('def');
    await expect(warning).toBeHidden();

    // And turning the beta off takes it away even while it is showing.
    await fillBackUntilOverflow(page, tooLong);
    await page.locator('#double_sided_enabled').uncheck();
    await expect(warning).toBeHidden();
  });

  test('the preview shows both sides with the beta on and neither heading with it off', async ({ page }) => {
    await openApp(page);
    await enableBeta(page, 'abc', 'def');
    await page.locator('#expert-toggle').click();

    const preview = page.locator('#preview-content');
    const headings = preview.locator('h3.preview-section-heading');

    await previewBraille(page, async () => {
      await expect(preview).toContainText(FRONT_BRAILLE, { timeout: 4000 });
    });
    await expect(preview).toContainText(BACK_BRAILLE);
    // h3 under the panel's h2 keeps the outline valid, and heading semantics
    // are what let a screen-reader user jump between the sides with the H key.
    await expect(headings).toHaveText(['Front of Card', 'Back of Card']);

    await page.locator('#double_sided_enabled').uncheck();
    // The panel still holds the two-sided render, so "contains the front
    // braille" would pass on stale content. The headings vanishing is what
    // proves this press re-rendered with the beta off.
    await previewBraille(page, async () => {
      await expect(headings).toHaveCount(0, { timeout: 4000 });
    });
    await expect(preview).toContainText(FRONT_BRAILLE);
    await expect(preview).not.toContainText(BACK_BRAILLE);
    await expect(headings).toHaveCount(0);
  });

  test('the plate radios take the Cylinder A/B names only while the beta is on', async ({ page }) => {
    await openApp(page);

    const original = await plateLabels(page);
    expect(original).toEqual(['Embossing Plate', 'Universal Counter Plate']);

    await page.locator('#double_sided_enabled').check();
    expect(await plateLabels(page)).toEqual([
      'Cylinder A — Embossing Plate',
      'Cylinder B — Universal Counter Plate',
    ]);

    // Byte-identical on the way back: the training videos show these names.
    await page.locator('#double_sided_enabled').uncheck();
    expect(await plateLabels(page)).toEqual(original);
  });

  test('Generate Both builds the pair, downloads nothing on its own, and restores the plate', async ({ page }) => {
    test.setTimeout(300_000);
    await openApp(page);
    const requests = watchGeometrySpecRequests(page);
    const unattendedDownloads: string[] = [];
    page.on('download', (download) => unattendedDownloads.push(download.suggestedFilename()));

    await enableBeta(page, 'abc', 'def');
    // A deliberate non-default choice, to prove the run puts it back.
    await page.locator('input[name="plate_type"][value="negative"]').check();

    await generateBoth(page);

    // NOTHING may download by itself. Two programmatic downloads from a single
    // gesture is exactly what makes Chrome ask "wants to: Download multiple
    // files" — a prompt the page cannot relabel, which names no file and cycles
    // Close/Allow/Block on every Tab. An NVDA run on 2026-08-18 hit it and
    // ended in "Download blocked" with neither cylinder saved.
    expect(unattendedDownloads).toEqual([]);

    // Each file comes from its own deliberate press.
    await expect(page.locator('#pair-downloads')).toBeVisible();
    expect(await pairDownloadName(page, 'a')).toBe('Cylinder_A_0.4_abc.stl');
    expect(await pairDownloadName(page, 'b')).toBe('Cylinder_B_0.4_abc.stl');

    // Identical settings contract: the two bodies differ ONLY in plate_type.
    // Both carry the same lines and back_lines, because Cylinder B needs the
    // front braille to place its 1:1 paired recesses.
    const [aBody, bBody] = requests.bodies.slice(-2) as Array<Record<string, unknown>>;
    expect(aBody.plate_type).toBe('positive');
    expect(bBody.plate_type).toBe('negative');
    const withoutPlate = (body: Record<string, unknown>) => {
      const copy = { ...body };
      delete copy.plate_type;
      return copy;
    };
    expect(withoutPlate(aBody)).toEqual(withoutPlate(bBody));

    // The user's own plate selection survives the run.
    await expect(page.locator('input[name="plate_type"][value="negative"]')).toBeChecked();
  });

  test('the generate button keeps its identity and the download is a separate control', async ({ page }) => {
    await openApp(page);
    const responses = watchGeometrySpec(page);
    await page.locator('#auto-text').fill('abc');

    const action = page.locator('#action-btn');
    const download = page.locator('#download-stl-btn');
    await expect(download).toBeHidden();

    await generateFully(page, responses, 1);

    // Before 2026-08-18 #action-btn renamed itself into the download control
    // while a screen-reader user's focus sat on it, announcing nothing. It must
    // now stay itself, and the file must be offered by its own button.
    await expect(download).toBeVisible();
    await expect(action).toHaveAttribute('data-state', 'generate');
    await expect(action).toHaveAttribute('aria-label', 'Generate STL file from entered text');
    await expect(page.locator('#a11y-status')).toContainText('Your STL file is ready');

    // Any settings change invalidates the built STL, so its download has to go
    // with it — otherwise the button hands out a file built to settings that
    // are no longer on screen.
    await page.locator('#auto-text').fill('abcd');
    await expect(download).toBeHidden();
  });

  test('the shared announcement region is always present and never hidden', async ({ page }) => {
    await openApp(page);
    const live = page.locator('#a11y-status');

    // It must never be display:none. A region that is hidden when its text is
    // written is inserted into the accessibility tree already holding that
    // text, and an insertion is not a change, so nothing is announced — the
    // defect that made the first pair message, the lock note and every
    // single-plate validation error silent.
    await expect(live).toHaveCount(1);
    await expect(live).toHaveAttribute('role', 'status');
    await expect(live).toHaveAttribute('aria-live', 'polite');
    expect(
      await live.evaluate((el) => getComputedStyle(el).display),
      '#a11y-status must never be display:none',
    ).not.toBe('none');

    await page.locator('#double_sided_enabled').check();
    await expect(live).toContainText('Locked: Double-Sided Card is on');
  });
});
