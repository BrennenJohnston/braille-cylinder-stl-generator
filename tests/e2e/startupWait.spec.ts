/**
 * E2E tests for pressing Generate or Translate while the page is still
 * starting (2026-10-01).
 *
 * The braille translator (liblouis) runs in a web worker that takes a few
 * seconds to start. Until 2026-10-01 a Generate STL or Translate to Braille
 * pressed in that window failed at once with "Translation failed for the
 * following lines" (or a "not initialized" status), as if the text were at
 * fault. The translator now reports a start-up state, and anything that needs
 * it waits until start-up has ended; when start-up fails for good, the old
 * message still appears.
 *
 * Each test holds the translator's script back with a route delay, so the
 * worker is still starting when the button is pressed, once.
 *
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import { selectCylinders } from './helpers/cylinders';

const TRANSLATOR_SCRIPT = '**/static/liblouis-worker.js';
const TRANSLATOR_DELAY_MS = 4000;
const BRAILLE = /[⠀-⣿]/;

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

/** Wait up to timeoutMs for a condition without failing, so the assertion after it can say what the page showed. */
async function waitUntil(condition: () => Promise<boolean> | boolean, timeoutMs: number): Promise<boolean> {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    if (await condition()) return true;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return condition();
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

  // The 3D engine starts only after the translator, so this press can still
  // find the engine starting; this test checks the translation step only.
  test('Generate pressed while the translator is starting waits for it and translates the text', async ({ page }) => {
    await delayTranslator(page);
    await captureGeometryRequests(page);
    await openApp(page);
    await selectCylinders(page, 'positive');
    await page.locator('#auto-text').fill('hello world');
    await recordErrorTexts(page);

    await page.locator('#action-btn').click();

    // Generate writes the braille it is about to emboss into the field.
    const field = page.locator('#braille-unicode');
    await waitUntil(async () => BRAILLE.test(await field.inputValue()), 20_000);
    const shown = await errorTexts(page);
    expect(await field.inputValue(), `#error-text showed: ${JSON.stringify(shown)}`).toMatch(BRAILLE);
    expect(shown.filter((text) => text.includes('Translation failed'))).toEqual([]);
  });

  test('Translate to Braille pressed while the translator is starting fills the field', async ({ page }) => {
    await delayTranslator(page);
    await openApp(page);
    await page.locator('#auto-text').fill('hello world');

    await page.locator('#translate-to-braille-btn').click();

    const field = page.locator('#braille-unicode');
    await waitUntil(async () => BRAILLE.test(await field.inputValue()), 20_000);
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
