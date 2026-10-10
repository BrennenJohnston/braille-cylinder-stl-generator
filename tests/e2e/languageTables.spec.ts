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
 * Since the dropdown plan (08_LANGUAGE_DROPDOWN_METADATA_PLAN, decisions M1-M3,
 * 2026-10-09) each table is offered once, under its liblouis display name, in a
 * group named by the first part of its liblouis index name; the 13 tables
 * liblouis does not describe are offered by file name under Other.
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
  await page.waitForSelector('#language-table optgroup[label="German"]', { state: 'attached' });
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

  test('every table the server lists is offered once, under its liblouis name and language', async ({ page }) => {
    await openApp(page);
    const { listed, options } = await page.evaluate(async () => {
      const response = await (await fetch('/liblouis/tables')).json();
      const options = Array.from(document.querySelectorAll<HTMLOptionElement>('#language-table option'), (o) => ({
        value: o.value,
        label: o.textContent,
        group: (o.parentElement as HTMLOptGroupElement).label,
      }));
      return { listed: response.tables, options };
    });
    const defaults = ['en-ueb-g2.ctb', 'en-ueb-g1.ctb', 'en-us-g2.ctb', 'en-us-g1.ctb'];
    const values = options.map((o) => o.value);
    expect(new Set(values).size).toBe(values.length);
    // en_US.tbl gives the same braille as the default en-us-g2.ctb, which it wraps.
    const expected = [...new Set([...defaults, ...listed.map((t: { file: string }) => t.file)])]
      .filter((file) => file !== 'en_US.tbl')
      .sort();
    expect([...values].sort()).toEqual(expected);
    const byValue = Object.fromEntries(options.map((o) => [o.value, o]));
    expect(byValue['en_GB.tbl']).toEqual({ value: 'en_GB.tbl', label: 'English contracted braille as used in the U.K.', group: 'English' });
    expect(byValue['de-g2.ctb']).toEqual({ value: 'de-g2.ctb', label: 'German contracted braille', group: 'German' });
    expect(byValue['sin.utb']).toEqual({ value: 'sin.utb', label: 'sin.utb', group: 'Other' });
    expect(byValue['en-ueb-g2.ctb'].group).toBe('Default');
    // A name liblouis gives two tables carries the file name.
    expect(byValue['ja-kantenji.utb'].label).toBe('Kantenji (ja-kantenji.utb)');
    const groups = [...new Set(options.map((o) => o.group))];
    expect(groups[0]).toBe('Default');
    expect(groups[groups.length - 1]).toBe('Other');
    const languages = groups.slice(1, -1);
    expect(languages).toEqual([...languages].sort((a, b) => a.localeCompare(b, 'en')));
  });

  test('the per-row language menus offer the same tables as the main one', async ({ page }) => {
    await openApp(page);
    const menus = await page.evaluate(() => {
      const describe = (select: HTMLSelectElement) =>
        Array.from(select.querySelectorAll('option'), (o) => `${(o.parentElement as HTMLOptGroupElement).label}|${o.value}|${o.textContent}`);
      return {
        main: describe(document.getElementById('language-table') as HTMLSelectElement),
        rows: Array.from(document.querySelectorAll<HTMLSelectElement>('.line-language-select'), describe),
      };
    });
    expect(menus.rows.length).toBeGreaterThan(0);
    for (const row of menus.rows) expect(row).toEqual(menus.main);
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
