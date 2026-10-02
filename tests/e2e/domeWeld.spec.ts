/**
 * E2E tests for the rounded-dot dome weld (2026-10-01).
 *
 * A rounded dot is a frustum base with a spherical-cap dome on top, and the cap
 * used to be cut at exactly the frustum's top plane. A half-sphere dome (both
 * card-stock presets, both double-sided packages) shares that plane's ring with
 * the frustum and fuses; any other dome only touched it, so the export held one
 * loose dome per raised dot. The worker now lets such a cap continue 0.005 mm
 * below the plane (DOT_DOME_WELD_MM, as in the OpenSCAD file) and builds
 * half-sphere domes exactly as before, so preset exports keep their bytes.
 *
 * Each test exports Cylinder A with "hello world" (21 raised dots) and counts
 * the connected bodies in the file:
 *   1. a shallow custom dome (1.5 x 0.6 mm on a 2.0 x 0.2 mm base): one body
 *      (22 before the weld: the cylinder and 21 domes);
 *   2. a tall custom dome (1.0 x 0.7 mm on 1.5 x 0.5 mm), which never split:
 *      still one body;
 *   3. the 0.4 preset: still one body.
 * tests/test_smoke.py pins that every shipped package is a half-sphere.
 *
 * @see docs/specifications/BRAILLE_DOT_SHAPE_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import { selectCylinders } from './helpers/cylinders';

const TEXT = 'hello world';

const TRANSIENT_ERRORS = /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

const DOT_DIALS = [
  'rounded_dot_base_diameter',
  'rounded_dot_base_height',
  'rounded_dot_dome_diameter',
  'rounded_dot_dome_height',
] as const;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
  await selectCylinders(page, 'positive');
}

async function setDial(page: Page, id: string, value: string) {
  await page.evaluate(([dialId, dialValue]) => {
    const el = document.getElementById(dialId) as HTMLInputElement | null;
    if (!el) throw new Error(`dial ${dialId} not found`);
    el.value = dialValue;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, [id, value]);
}

/** Base diameter, base height, dome diameter, dome height, in mm. */
async function setRoundedDot(page: Page, sizes: [string, string, string, string]) {
  for (let i = 0; i < DOT_DIALS.length; i++) await setDial(page, DOT_DIALS[i], sizes[i]);
}

/** The rounded-dot sizes a /geometry_spec request carried (the page sends dial values as strings). */
function requestedDot(body: Record<string, any> | null | undefined): number[] {
  const settings = body?.settings ?? {};
  return [Number(settings.use_rounded_dots), ...DOT_DIALS.map((dial) => Number(settings[dial]))];
}

function watchGeometrySpecRequests(page: Page) {
  const state: { bodies: Array<Record<string, any> | null> } = { bodies: [] };
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
 * Connected bodies of a binary STL (80-byte header, uint32 triangle count,
 * 50-byte records with the vertices at +12/+24/+36): vertices keyed by their
 * coordinates rounded to 0.0001 mm, joined through every triangle.
 */
function countBodies(buf: Buffer): number {
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const triangles = view.getUint32(80, true);
  expect(buf.byteLength).toBe(84 + triangles * 50);
  const ids = new Map<string, number>();
  const parent: number[] = [];
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const vertexId = (offset: number): number => {
    const key = [0, 4, 8].map((d) => Math.round(view.getFloat32(offset + d, true) * 1e4)).join(',');
    let id = ids.get(key);
    if (id === undefined) {
      id = parent.length;
      parent.push(id);
      ids.set(key, id);
    }
    return id;
  };
  for (let t = 0; t < triangles; t++) {
    const record = 84 + t * 50;
    const [a, b, c] = [12, 24, 36].map((off) => vertexId(record + off));
    const root = find(a);
    for (const other of [b, c]) {
      const r = find(other);
      if (r !== root) parent[r] = root;
    }
  }
  return new Set(parent.map((_, i) => find(i))).size;
}

test.describe('Rounded-dot dome weld', () => {
  test.describe.configure({ timeout: 300_000 });

  test('a shallow custom dome is one body with its base', async ({ page }) => {
    await openApp(page);
    await setRoundedDot(page, ['2.0', '0.2', '1.5', '0.6']);
    await page.locator('#auto-text').fill(TEXT);
    const state = watchGeometrySpecRequests(page);
    const stl = await generateAndDownload(page, state, 1);
    expect(requestedDot(state.bodies[0])).toEqual([1, 2.0, 0.2, 1.5, 0.6]);
    expect(countBodies(stl)).toBe(1);
  });

  test('a tall custom dome stays one body', async ({ page }) => {
    await openApp(page);
    await setRoundedDot(page, ['1.5', '0.5', '1.0', '0.7']);
    await page.locator('#auto-text').fill(TEXT);
    const state = watchGeometrySpecRequests(page);
    const stl = await generateAndDownload(page, state, 1);
    expect(requestedDot(state.bodies[0])).toEqual([1, 1.5, 0.5, 1.0, 0.7]);
    expect(countBodies(stl)).toBe(1);
  });

  test('the 0.4 preset stays one body', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill(TEXT);
    const state = watchGeometrySpecRequests(page);
    const stl = await generateAndDownload(page, state, 1);
    expect(requestedDot(state.bodies[0])).toEqual([1, 1.5, 0.5, 1.0, 0.5]);
    expect(countBodies(stl)).toBe(1);
  });
});
