/**
 * E2E tests for X Adjust on cylinders (2026-09-27).
 *
 * Until this date the cylinder spec builder ignored the X Adjust dial (Y Adjust
 * worked), and a build was once reported fixed on the strength of the spec
 * alone. So this file checks the BYTES the real worker exports: it generates
 * Cylinder A and Cylinder B at X 0 and X -3 and measures where the raised dots
 * and the arrows sit round each barrel.
 *
 * Frame: the exported STL is Z-up with the barrel on the Z axis and the tactile
 * arrow column at world angle 180 degrees. `s` is the signed arc from that
 * column, positive toward world angle > 180 degrees (y < 0), which the
 * preview's default camera (on -X, up +Z) shows to the RIGHT of the screen.
 *
 * What is pinned: a negative X moves every raised dot on Cylinder A LEFT by the
 * dial's value in mm of arc and every raised dot on Cylinder B RIGHT by the
 * same arc (Brennen's 2026-09-27 request), the arrows do not move, and the two
 * live room notes follow the dial.
 *
 * @see docs/specifications/BRAILLE_SPACING_SPECIFICATIONS.md section 5
 */

import * as fs from 'node:fs';
import { expect, test, type Page } from '@playwright/test';
import { selectCylinders } from './helpers/cylinders';

const BARREL_RADIUS_MM = 15.4;
const DOME_CAP_RADIUS_MM = 16.25; // the 0.4 double-sided dot tops out at 16.4; the arrows stay under 16.0

const TRANSIENT_ERRORS =
  /Manifold 3D engine|not initialized|Translating|Generating|STL generation failed|Translation failed/;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
}

async function generate(page: Page) {
  let lastError = '';
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    try {
      await page.locator('#download-stl-btn').waitFor({ state: 'visible', timeout: 240_000 });
      return;
    } catch {
      const notice = await page.locator('#error-message').getAttribute('class');
      const isInfo = notice?.includes('info') ?? false;
      const error = await page.locator('#error-text').textContent();
      if (error && !isInfo && !TRANSIENT_ERRORS.test(error)) {
        throw new Error(`Generation was blocked: ${error}`);
      }
      lastError = error || lastError;
      await page.waitForTimeout(1000);
    }
  }
  throw new Error(`Generation never produced a download; last error: ${lastError}`);
}

async function download(page: Page): Promise<Buffer> {
  const downloadPromise = page.waitForEvent('download');
  await page.locator('#download-stl-btn').click();
  const item = await downloadPromise;
  return fs.readFileSync((await item.path())!);
}

/** The dial lives in a collapsed Expert Mode panel; set it at the source and fire the events the form listens for. */
async function setXAdjust(page: Page, value: string) {
  await page.evaluate((v) => {
    const el = document.getElementById('braille_x_adjust') as HTMLInputElement;
    el.value = v;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
  await expect(page.locator('#braille_x_adjust')).toHaveValue(value);
}

async function versionTwoDoubleSidedPair(page: Page) {
  await page.locator('#embosser_version_2').check();
  await page.locator('#card_sides_double').check();
  await page.locator('#auto-text').fill('abc');
  await page.locator('#back-text').fill('xyz');
}

/** Binary STL vertices (see seamChannel.spec.ts). */
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

function arcFromArrowColumn(x: number, y: number): number {
  const world = Math.atan2(y, x);
  let d = world - Math.PI;
  while (d <= -Math.PI) d += 2 * Math.PI;
  while (d > Math.PI) d -= 2 * Math.PI;
  return d * BARREL_RADIUS_MM;
}

/**
 * Mean arc of the dome caps (every raised dot) and of the arrows, from the
 * arrow column. The arrows are RAISED on Cylinder A (where the groove steps
 * round them on the first-cell side, so recessed vertices near the column are
 * NOT symmetric there) and RECESSED on Cylinder B (with the straight groove
 * through them, symmetric about the column). So: raised vertices within
 * 2.2 mm of the column where there are any (A), else recessed ones (B). No
 * dot can be that close at the shifts used (the nearest dot edge is 4.5 mm
 * out at -3).
 */
function meanArcs(buf: Buffer): { dots: number; dotCount: number; arrows: number } {
  const dots: number[] = [];
  const raisedOnColumn: number[] = [];
  const recessedOnColumn: number[] = [];
  for (const [x, y, z] of stlVertices(buf)) {
    if (Math.abs(z) > 22) continue; // the keyed ends and the nub
    const r = Math.hypot(x, y);
    const s = arcFromArrowColumn(x, y);
    if (r > DOME_CAP_RADIUS_MM) {
      dots.push(s);
    } else if (Math.abs(s) < 2.2 && r > BARREL_RADIUS_MM + 0.05) {
      raisedOnColumn.push(s);
    } else if (Math.abs(s) < 2.2 && r < BARREL_RADIUS_MM - 0.05 && r > 14.0) {
      recessedOnColumn.push(s);
    }
  }
  const arrows = raisedOnColumn.length ? raisedOnColumn : recessedOnColumn;
  expect(dots.length).toBeGreaterThan(0);
  expect(arrows.length).toBeGreaterThan(0);
  const mean = (values: number[]) => values.reduce((a, b) => a + b, 0) / values.length;
  return { dots: mean(dots), dotCount: dots.length, arrows: mean(arrows) };
}

test.describe('X Adjust on cylinders', () => {
  test.describe.configure({ timeout: 600_000 });

  for (const [plate, direction, expectedShift] of [
    ['positive', 'left', -3.0],
    ['negative', 'right', +3.0],
  ] as const) {
    test(`a negative X moves Cylinder ${plate === 'positive' ? 'A' : 'B'}'s raised dots ${direction} by the dial and leaves the arrows`, async ({ page }) => {
      await openApp(page);
      await selectCylinders(page, plate);
      await versionTwoDoubleSidedPair(page);

      await setXAdjust(page, '0');
      await generate(page);
      const before = meanArcs(await download(page));

      await setXAdjust(page, '-3');
      await generate(page);
      const after = meanArcs(await download(page));

      expect(after.dotCount).toBe(before.dotCount);
      // Every raised dot moved by the same arc, so their mean moved by it too.
      expect(after.dots - before.dots).toBeCloseTo(expectedShift, 1);
      // The alignment arrows are the fixed reference and did not move.
      expect(Math.abs(before.arrows)).toBeLessThan(0.1);
      expect(Math.abs(after.arrows)).toBeLessThan(0.1);
    });
  }

  test('the live seam-channel and card-fit notes follow the dial', async ({ page }) => {
    await openApp(page);
    await versionTwoDoubleSidedPair(page);
    const seamNote = page.locator('#seam-channel-warning');
    const cardNote = page.locator('#card-fit-warning');
    const shown = (box: typeof seamNote) => box.evaluate((el) => (el as HTMLElement).style.display === 'block');

    // 13 tactile cells at 30.8: the detour has 4.23 mm of room at -3 (needs
    // 3.5) and 3.23 at -4, so the S-C5 note appears at -4 and goes at -3.
    await setXAdjust(page, '-4');
    await expect.poll(() => shown(seamNote)).toBe(true);
    await expect(page.locator('#seam-channel-message')).toHaveText(
      'The seam channel was left out: there is not enough room for it beside the alignment arrows. Reduce the number of braille cells, increase the cylinder diameter, or narrow the indicator.',
    );
    await setXAdjust(page, '-3');
    await expect.poll(() => shown(seamNote)).toBe(false);

    // 14 tactile cells need 92.6 mm of a 90 mm card at 0 (S-T1; the
    // double-sided package's footprint is 1.95 mm, against the 0.4 preset's
    // 2.15 single-sided) and 89.6 at -3. The cells dial sits in the same
    // collapsed panel, so it is set the same way.
    await page.evaluate(() => {
      const el = document.getElementById('grid_columns') as HTMLInputElement;
      el.value = '14';
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await expect(page.locator('#grid_columns')).toHaveValue('14');
    await setXAdjust(page, '0');
    await expect.poll(() => shown(cardNote)).toBe(true);
    await expect(page.locator('#card-fit-message')).toContainText('this layout needs 92.6 mm of card');
    await setXAdjust(page, '-3');
    await expect.poll(() => shown(cardNote)).toBe(false);
  });
});
