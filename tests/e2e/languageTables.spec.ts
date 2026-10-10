/**
 * The language dropdown offers the liblouis 3.39.0 translation tables (the
 * engine round, plan 05_LIBLOUIS_3_39_UPGRADE_PLAN phase 7, 2026-10-09).
 *
 * /liblouis/tables lists the .ctb, .utb and .tbl names in
 * static/vendor/liblouis-3.39.0/tables.json, the index the translation worker
 * fetches tables by, so every option can be loaded. Before phase 7 it also
 * scanned the 3.2.0 tables and a native 3.34.0 copy: 27 of the options it
 * showed are not in 3.39.0 and stopped with "Unknown liblouis table".
 *
 * A saved choice the engine no longer has falls back to contracted UEB, the
 * first-run default; one it still has is kept.
 *
 * @see docs/specifications/LIBLOUIS_TRANSLATION_CORE_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const REFERENCE = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../fixtures/liblouis-reference/table-samples-3.39.0.json'), 'utf8')
);
const SAVED_TABLE_KEY = 'braille_prefs_language_table';

/** Load the app, optionally with a saved table choice, and wait for the dropdown's tables. */
async function openApp(page: Page, savedTable?: string) {
  if (savedTable) {
    await page.addInitScript(([key, value]) => localStorage.setItem(key, value), [SAVED_TABLE_KEY, savedTable]);
  }
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#language-table optgroup[label="Other"]', { state: 'attached' });
}

/** Press Translate to Braille and wait for the field to fill. */
async function translateToBraille(page: Page) {
  const field = page.locator('#braille-unicode');
  await page.locator('#translate-to-braille-btn').click();
  await expect(field).not.toHaveValue('', { timeout: 30_000 });
  return field.inputValue();
}

test.describe('Language tables', () => {
  test('every option is a liblouis 3.39.0 translation table', async ({ page }) => {
    await openApp(page);
    const offered = await page.evaluate(async () => {
      const index = await (await fetch('/static/vendor/liblouis-3.39.0/tables.json')).json();
      const values = Array.from(document.querySelectorAll<HTMLOptionElement>('#language-table option'), (o) => o.value);
      return { values, closures: Object.keys(index.closures) };
    });
    expect(offered.values.length).toBeGreaterThan(4);
    const outside = offered.values.filter(
      (value) => !offered.closures.includes(value) || !/\.(ctb|utb|tbl)$/.test(value)
    );
    expect(outside).toEqual([]);
  });

  test('a saved table that 3.39.0 does not ship falls back to contracted UEB', async ({ page }) => {
    await openApp(page, 'fr-fr-g1.utb');
    await expect(page.locator('#language-table')).toHaveValue('en-ueb-g2.ctb');
  });

  test('a saved table that 3.39.0 ships is kept, and translates as native liblouis does', async ({ page }) => {
    await openApp(page, 'de-g1.ctb');
    await expect(page.locator('#language-table')).toHaveValue('de-g1.ctb');
    // 12 cells, one row: the native 3.39.0 engine's braille for this sample.
    const sample = REFERENCE.samples.indexOf('café naïve');
    const expected = REFERENCE.tables['de-g1.ctb'][sample].split(String.fromCharCode(0x2800)).join(' ');
    await page.locator('#auto-text').fill('café naïve');
    expect(await translateToBraille(page)).toBe(expected);
  });
});
