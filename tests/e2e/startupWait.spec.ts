/**
 * E2E tests for pressing Generate or Translate while the page is still
 * starting (2026-10-01).
 *
 * The braille translator (liblouis) and the 3D engine (Manifold) run in web
 * workers that take a few seconds to start, the engine only after the
 * translator. Until 2026-10-01 a Generate STL or Translate to Braille pressed
 * in that window failed at once: "Translation failed for the following lines"
 * (or a "not initialized" status), as if the text were at fault, or "requires
 * the Manifold 3D engine which failed to load", as if it never would. Both
 * workers now report a start-up state, and anything that needs one waits
 * until its start-up has ended; when start-up fails for good, the old message
 * still appears.
 *
 * Each test holds a worker's script back with a route delay, so the worker is
 * still starting when the button is pressed, once.
 *
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import { selectCylinders } from './helpers/cylinders';

const TRANSLATOR_SCRIPT = '**/static/liblouis-worker.js';
const TRANSLATOR_DELAY_MS = 4000;
const ENGINE_SCRIPT = '**/static/workers/csg-worker-manifold.js';
const ENGINE_DELAY_MS = 6000;
// S-L1 and S-L2 (DRAFT 2026-10-01, awaiting Brennen's sign-off at Gate B).
const TRANSLATOR_NOTICE = 'The braille translator is still loading. This starts as soon as it is ready.';
const ENGINE_NOTICE = 'The 3D engine is still loading. Generation starts as soon as it is ready.';
const BRAILLE = /[\u2800-\u28FF]/;
// How long a test lets a delayed translator take: the page's own limit for its start is
// 30 s after the route delay, and under heavy local load a working start passes 20 s.
const TRANSLATOR_WAIT_MS = 45_000;

async function delayTranslator(page: Page) {
  await page.route(TRANSLATOR_SCRIPT, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, TRANSLATOR_DELAY_MS));
    await route.continue();
  });
}

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForSelector('#embosser-setup-selection');
}

/** Record every text #error-text shows, so a message that flashes by is still seen. */
async function recordErrorTexts(page: Page) {
  await page.evaluate(() => {
    const target = document.getElementById('error-text');
    const seen: string[] = [];
    (window as unknown as { __errorTexts: string[] }).__errorTexts = seen;
    if (!target) return;
    const note = () => {
      const text = (target.textContent || '').replace(/\s+/g, ' ').trim();
      if (text && seen[seen.length - 1] !== text) seen.push(text);
    };
    note();
    new MutationObserver(note).observe(target, { childList: true, subtree: true, characterData: true });
  });
}

async function errorTexts(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __errorTexts?: string[] }).__errorTexts ?? []);
}

/**
 * Record EVERY write to the page's one announcement region, #a11y-status, not
 * just changes: rewriting the same sentence is a mutation and can be spoken again.
 */
async function recordAnnouncements(page: Page) {
  await page.evaluate(() => {
    const region = document.getElementById('a11y-status');
    const writes: string[] = [];
    (window as unknown as { __announcements: string[] }).__announcements = writes;
    if (!region) return;
    new MutationObserver(() => {
      writes.push((region.textContent || '').replace(/\s+/g, ' ').trim());
    }).observe(region, { childList: true, subtree: true, characterData: true });
  });
}

async function announcements(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __announcements?: string[] }).__announcements ?? []);
}

/** Wait up to timeoutMs for a condition without failing, so the assertion after it can say what the page showed. */
async function waitUntil(condition: () => Promise<boolean> | boolean, timeoutMs: number): Promise<boolean> {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    if (await condition()) return true;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return condition();
}

/** Let the translator answer first, so the 3D engine is the only thing still starting. */
async function translateFirst(page: Page) {
  const field = page.locator('#braille-unicode');
  await page.locator('#translate-to-braille-btn').click();
  await waitUntil(async () => BRAILLE.test(await field.inputValue()), 20_000);
  expect(await field.inputValue()).toMatch(BRAILLE);
}

/** Capture each /geometry_spec request body and stop it there: these tests are about start-up, not geometry. */
async function captureGeometryRequests(page: Page) {
  const bodies: Array<Record<string, unknown> | null> = [];
  await page.route('**/geometry_spec', async (route) => {
    try {
      bodies.push(route.request().postDataJSON());
    } catch {
      bodies.push(null);
    }
    await route.abort();
  });
  return bodies;
}

test.describe('Pressing a button while the translator is starting', () => {
  test.describe.configure({ timeout: 90_000 });

  // The 3D engine starts only after the translator, so this press waits for
  // both, one after the other.
  test('Generate pressed while the translator is starting waits and then generates', async ({ page }) => {
    await delayTranslator(page);
    const bodies = await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await recordErrorTexts(page);

    await page.locator('#action-btn').click();

    await waitUntil(() => bodies.length >= 1, TRANSLATOR_WAIT_MS);
    await page.waitForTimeout(1000);
    expect(bodies, `#error-text showed: ${JSON.stringify(await errorTexts(page))}`).toHaveLength(1);
    const lines = (bodies[0]?.lines ?? []) as string[];
    expect(lines.some((line) => BRAILLE.test(line))).toBe(true);
    expect((await errorTexts(page)).filter((text) => text.includes('Translation failed'))).toEqual([]);
  });

  test('Translate to Braille pressed while the translator is starting fills the field', async ({ page }) => {
    await delayTranslator(page);
    await openApp(page);
    await page.locator('#auto-text').fill('hello world');

    await page.locator('#translate-to-braille-btn').click();

    const field = page.locator('#braille-unicode');
    await waitUntil(async () => BRAILLE.test(await field.inputValue()), TRANSLATOR_WAIT_MS);
    const status = (await page.locator('#braille-unicode-status').textContent()) || '';
    expect(await field.inputValue(), `the field's status line said: ${status.trim()}`).toMatch(BRAILLE);
  });

  test('a translator that cannot start still stops Generate with the translation message', async ({ page }) => {
    await page.route(TRANSLATOR_SCRIPT, (route) => route.abort());
    const bodies = await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await recordErrorTexts(page);

    await page.locator('#action-btn').click();

    await expect
      .poll(async () => (await errorTexts(page)).some((text) => text.includes('Translation failed for the following lines')), {
        timeout: 20_000,
      })
      .toBe(true);
    await page.waitForTimeout(1000);
    expect(bodies).toHaveLength(0);
  });
});

test.describe('Pressing Generate while the 3D engine is starting', () => {
  test.describe.configure({ timeout: 180_000 });

  test('Generate pressed while the 3D engine is starting waits and then offers the download', async ({ page }) => {
    await page.route(ENGINE_SCRIPT, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, ENGINE_DELAY_MS));
      await route.continue();
    });
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await translateFirst(page);
    await recordErrorTexts(page);

    await page.locator('#action-btn').click();

    const download = page.locator('#download-stl-btn');
    await waitUntil(() => download.isVisible(), 120_000);
    const shown = await errorTexts(page);
    expect(await download.isVisible(), `#error-text showed: ${JSON.stringify(shown)}`).toBe(true);
    expect(shown.filter((text) => text.includes('Manifold 3D engine'))).toEqual([]);
  });

  test('a 3D engine that cannot load still stops Generate with the engine message', async ({ page }) => {
    await page.route(ENGINE_SCRIPT, (route) => route.abort());
    const bodies = await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await translateFirst(page);
    await recordErrorTexts(page);

    await page.locator('#action-btn').click();

    const failedToLoad = 'Cylinder generation requires the Manifold 3D engine which failed to load.';
    await waitUntil(async () => (await errorTexts(page)).some((text) => text.includes(failedToLoad)), 20_000);
    expect(
      (await errorTexts(page)).some((text) => text.includes(failedToLoad)),
      `#error-text showed: ${JSON.stringify(await errorTexts(page))}`,
    ).toBe(true);
    await page.waitForTimeout(1000);
    expect(bodies).toHaveLength(0);
  });
});

test.describe('Saying that a worker is still loading', () => {
  test.describe.configure({ timeout: 180_000 });

  test('Generate pressed while the translator is starting says so once, and the sentence goes when it is ready', async ({ page }) => {
    await delayTranslator(page);
    await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await recordErrorTexts(page);
    await recordAnnouncements(page);

    await page.locator('#action-btn').click();

    await expect(page.locator('#error-text')).toHaveText(TRANSLATOR_NOTICE, { timeout: 2000 });
    await expect(page.locator('#error-message')).toHaveClass(/(^|\s)info(\s|$)/);
    await expect(page.locator('#a11y-status')).toHaveText(TRANSLATOR_NOTICE, { timeout: 2000 });

    await waitUntil(async () => !((await page.locator('#error-text').textContent()) || '').includes(TRANSLATOR_NOTICE), TRANSLATOR_WAIT_MS);
    expect(await page.locator('#error-text').textContent()).not.toContain(TRANSLATOR_NOTICE);
    expect((await announcements(page)).filter((text) => text === TRANSLATOR_NOTICE)).toHaveLength(1);
  });

  test('Generate pressed while the 3D engine is starting says so once, and the sentence goes when it is ready', async ({ page }) => {
    await page.route(ENGINE_SCRIPT, async (route) => {
      await new Promise((resolve) => setTimeout(resolve, ENGINE_DELAY_MS));
      await route.continue();
    });
    await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await translateFirst(page);
    await recordErrorTexts(page);
    await recordAnnouncements(page);

    await page.locator('#action-btn').click();

    await expect(page.locator('#error-text')).toHaveText(ENGINE_NOTICE, { timeout: 2000 });
    await expect(page.locator('#error-message')).toHaveClass(/(^|\s)info(\s|$)/);
    await expect(page.locator('#a11y-status')).toHaveText(ENGINE_NOTICE, { timeout: 2000 });

    await waitUntil(async () => !((await page.locator('#error-text').textContent()) || '').includes(ENGINE_NOTICE), 60_000);
    expect(await page.locator('#error-text').textContent()).not.toContain(ENGINE_NOTICE);
    expect((await announcements(page)).filter((text) => text === ENGINE_NOTICE)).toHaveLength(1);
  });

  test('with both workers ready, neither loading sentence ever appears', async ({ page }) => {
    await openApp(page);
    await page.waitForLoadState('networkidle');
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await translateFirst(page);
    await page.waitForTimeout(1000);
    await recordErrorTexts(page);
    await recordAnnouncements(page);

    await page.locator('#action-btn').click();

    const download = page.locator('#download-stl-btn');
    await waitUntil(() => download.isVisible(), 120_000);
    expect(await download.isVisible(), `#error-text showed: ${JSON.stringify(await errorTexts(page))}`).toBe(true);
    const seen = [...(await errorTexts(page)), ...(await announcements(page))];
    expect(seen.filter((text) => text === TRANSLATOR_NOTICE || text === ENGINE_NOTICE)).toEqual([]);
  });

  test('a second Generate press while the first waits for the translator starts no second run', async ({ page }) => {
    await delayTranslator(page);
    const bodies = await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');

    await page.locator('#action-btn').click();
    await page.waitForTimeout(500);
    await page.locator('#action-btn').click();

    await waitUntil(() => bodies.length >= 1, TRANSLATOR_WAIT_MS);
    await page.waitForTimeout(3000);
    expect(bodies).toHaveLength(1);
  });
});
