/**
 * E2E tests for the Rows limit (Brennen's decisions, 2026-10-09; plan
 * 04_ROWS_LIMIT_FIX_PLAN).
 *
 * Rows 5+ used to fail at Generate on a fixed four-line cap. Now a request
 * may fill its own Rows, and rows that would run off the card or the barrel
 * are refused - with the same sentence the page shows live, before Generate,
 * in the Braille Spacing panel (S-R1 for the barrel, S-R2 for the card, both
 * signed 2026-10-09).
 */

import { test, expect, type Page } from '@playwright/test';
import { selectIndicatorMode } from './helpers/menus';

const S_R1_SIX_ROWS =
  "These 6 rows need 56.8 mm of the cylinder's 52 mm height, so the top and bottom rows would run off the ends. " +
  'Use fewer rows, a smaller line spacing, or a taller cylinder.';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
  await page.locator('#auto-text').fill('hello');
}

/** Set a dial at its source and fire what typing would: input, then change. */
async function setDial(page: Page, id: string, value: string) {
  await page.evaluate(
    ([dialId, dialValue]) => {
      const input = document.getElementById(dialId) as HTMLInputElement;
      input.value = dialValue;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    },
    [id, value],
  );
}

async function revealBrailleSpacingPanel(page: Page) {
  await page.evaluate(() => {
    const expert = document.getElementById('expert-settings');
    if (expert) expert.style.display = 'block';
    const panel = document.getElementById('expert-panel-spacing');
    if (panel) {
      panel.style.display = 'block';
      panel.hidden = false;
    }
  });
}

/**
 * Click Generate until /geometry_spec answers, and return that answer. The
 * request goes to the real server; its reply is read and the request then
 * aborted, so no CSG runs. The Manifold worker starts asynchronously, and the
 * page asks for another try until it is ready.
 */
async function generateAndReadReply(page: Page) {
  const reply: { status: number | null; error: string } = { status: null, error: '' };
  await page.route('**/geometry_spec', async (route) => {
    const response = await route.fetch();
    // The body first: the waiting loop below returns as soon as `status` is set.
    reply.error = (await response.json().catch(() => ({})))?.error ?? '';
    reply.status = response.status();
    await route.abort();
  });
  for (let attempt = 0; attempt < 15 && reply.status === null; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 3000 && reply.status === null; waited += 100) {
      await page.waitForTimeout(100);
    }
  }
  if (reply.status === null) throw new Error('Generate never reached /geometry_spec');
  return reply;
}

test.describe('Rows limit', () => {
  test.describe.configure({ timeout: 120_000 });

  test('five rows fit the 52 mm barrel, and the server takes five lines', async ({ page }) => {
    await openApp(page);
    await revealBrailleSpacingPanel(page);
    await setDial(page, 'grid_rows', '5');
    await expect(page.locator('#rows-fit-warning')).toBeHidden();
    const reply = await generateAndReadReply(page);
    expect(reply).toEqual({ status: 200, error: '' });
  });

  test('six rows show S-R1 live, announce it, and Generate is refused with the same words', async ({ page }) => {
    await openApp(page);
    await revealBrailleSpacingPanel(page);
    await setDial(page, 'grid_rows', '6');
    await expect(page.locator('#rows-fit-warning')).toBeVisible();
    await expect(page.locator('#rows-fit-message')).toHaveText(S_R1_SIX_ROWS);
    await expect(page.locator('#a11y-status')).toHaveText(S_R1_SIX_ROWS);

    const reply = await generateAndReadReply(page);
    expect(reply).toEqual({ status: 400, error: S_R1_SIX_ROWS });

    await setDial(page, 'grid_rows', '5');
    await expect(page.locator('#rows-fit-warning')).toBeHidden();
  });

  test('tactile arrows bound the rows on the barrel: four fit, five do not', async ({ page }) => {
    await openApp(page);
    await revealBrailleSpacingPanel(page);
    await selectIndicatorMode(page, 'tactile');
    await setDial(page, 'grid_rows', '4');
    await expect(page.locator('#rows-fit-warning')).toBeHidden();
    await setDial(page, 'grid_rows', '5');
    await expect(page.locator('#rows-fit-message')).toHaveText(
      "These 5 rows need 52.04 mm of the cylinder's 52 mm height, so the top and bottom rows would run off the ends. " +
        'Use fewer rows, a smaller line spacing, or a taller cylinder.',
    );
  });

  test('Y Adjust can push four rows off', async ({ page }) => {
    await openApp(page);
    await revealBrailleSpacingPanel(page);
    await setDial(page, 'braille_y_adjust', '10');
    await expect(page.locator('#rows-fit-message')).toHaveText(
      "These 4 rows need 56.8 mm of the cylinder's 52 mm height, so the top and bottom rows would run off the ends. " +
        'Use fewer rows, a smaller line spacing, or a taller cylinder.',
    );
  });

  test('on the 54 mm Version 2 barrel the 52 mm card is the limit (S-R2)', async ({ page }) => {
    await openApp(page);
    await page.evaluate(() => {
      const radio = document.getElementById('embosser_version_2') as HTMLInputElement;
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await expect(page.locator('#cylinder_height_mm')).toHaveValue('54');
    await revealBrailleSpacingPanel(page);
    await setDial(page, 'grid_rows', '5');
    await expect(page.locator('#rows-fit-warning')).toBeHidden();
    await setDial(page, 'grid_rows', '6');
    await expect(page.locator('#rows-fit-message')).toHaveText(
      "These 6 rows need 56.8 mm of the card's 52 mm height, so the top and bottom rows would run off the card. " +
        'Use fewer rows or a smaller line spacing.',
    );
    const reply = await generateAndReadReply(page);
    expect(reply.status).toBe(400);
    expect(reply.error).toBe(await page.locator('#rows-fit-message').textContent());
  });
});
