/**
 * E2E tests for the text-input privacy rule (Brennen, 2026-09-28).
 *
 * No text or braille input is ever stored - not the front text, the manual
 * rows, the back text, nor either Braille (Unicode) field. Even a value kept
 * only in this browser would look like the app collecting what people write.
 * Only 3D design settings persist. Before this date the Back of Card text was
 * saved under `braille_prefs_back_text` and came back on the next visit while
 * the front did not; that key is scrubbed on every load now.
 *
 * @see docs/specifications/BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md section 11
 */

import { expect, test, type Page } from '@playwright/test';

const SECRET = 'zebra-quilt-7741';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
}

async function reload(page: Page) {
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
}

/** Every localStorage entry whose value mentions the marker text. */
async function storageEntriesMentioning(page: Page, marker: string) {
  return page.evaluate((m) => {
    const hits: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)!;
      if ((localStorage.getItem(key) || '').includes(m)) hits.push(key);
    }
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i)!;
      if ((sessionStorage.getItem(key) || '').includes(m)) hits.push('session:' + key);
    }
    return hits;
  }, marker);
}

test.describe('Text input privacy', () => {
  test('a back text saved before 2026-09-28 is scrubbed on load and never restored', async ({ page }) => {
    await openApp(page);
    await page.evaluate((s) => localStorage.setItem('braille_prefs_back_text', s), SECRET);
    await reload(page);
    await expect(page.locator('#back-text')).toHaveValue('');
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_back_text'))).toBeNull();
  });

  test('nothing typed into any text or braille box is stored, and none of it survives a reload', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();

    // Auto placement, front and back, and both braille fields.
    await page.locator('#auto-text').fill(`front ${SECRET}`);
    await page.locator('#back-text').fill(`back ${SECRET}`);
    await page.locator('#braille-unicode').fill('⠓⠑');
    await page.locator('#back-braille-unicode').fill('⠃⠁');
    // Manual placement rows, front and back.
    await page.locator('input[name="placement_mode"][value="manual"]').check();
    await page.locator('#line1').fill(`row ${SECRET}`);
    await page.locator('#back_placement_mode_manual').check();
    await page.locator('#back_line1').fill(`backrow ${SECRET}`);

    expect(await storageEntriesMentioning(page, SECRET)).toEqual([]);
    expect(await storageEntriesMentioning(page, '⠓⠑')).toEqual([]);
    expect(await storageEntriesMentioning(page, '⠃⠁')).toEqual([]);

    await reload(page);
    // The settings came back (double-sided, manual placement on both sides)...
    await expect(page.locator('#card_sides_double')).toBeChecked();
    await expect(page.locator('input[name="placement_mode"][value="manual"]')).toBeChecked();
    await expect(page.locator('#back_placement_mode_manual')).toBeChecked();
    // ...and every text and braille box is empty.
    await expect(page.locator('#line1')).toHaveValue('');
    await expect(page.locator('#back_line1')).toHaveValue('');
    await expect(page.locator('#back-text')).toHaveValue('');
    await expect(page.locator('#braille-unicode')).toHaveValue('');
    await expect(page.locator('#back-braille-unicode')).toHaveValue('');
    await page.locator('input[name="placement_mode"][value="auto"]').check();
    await expect(page.locator('#auto-text')).toHaveValue('');
  });
});
