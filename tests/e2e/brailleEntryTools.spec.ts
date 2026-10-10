/**
 * E2E tests for the transcriber tools on the Braille (Unicode) field: six-key
 * entry and braille ASCII conversion (2026-10-09 plan, ported from the
 * OpenSCAD Assistive Forge's 5.2.0 build).
 *
 * What is pinned: a chord of f, d, s, j, k, l types one cell at the caret and
 * the keys themselves type nothing; each cell is announced once, as its dots,
 * from the field's own live region - a repeated cell too, which needs the
 * region emptied and rewritten (NVDA says nothing for identical words); the
 * box is off on every load, turned off by Reset, and toggling it never reaches
 * the form-wide delegate that invalidates a built STL; braille ASCII converts
 * in place and is embossed verbatim, and anything else is refused with the
 * field left exactly as it was.
 *
 * @see docs/specifications/BRAILLE_TEXT_INPUT_AND_LANGUAGE_SPECIFICATIONS.md section 6.3
 */

import { test, expect, type Page } from '@playwright/test';

/** h>ry@a" in braille ASCII: "harry@" and the dot-5 line continuation sign. */
const BRAILLE_ASCII_SAMPLE = 'h>ry@a"';
const BRAILLE_ASCII_CELLS = '⠓⠜⠗⠽⠈⠁⠐';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#braille-unicode');
}

/** Hold the keys down in order, then let them go in reverse order. */
async function chord(page: Page, keys: string[]) {
  for (const key of keys) await page.keyboard.down(key);
  for (const key of [...keys].reverse()) await page.keyboard.up(key);
}

async function turnSixKeyOn(page: Page, boxId = 'braille_six_key') {
  await page.locator(`#${boxId}`).check();
  await expect(page.locator(`#${boxId}`)).toBeChecked();
}

/**
 * Record every settled text of a live region from now on: one entry per
 * mutation batch, so an emptied region shows as '' between two writes.
 */
async function recordRegion(page: Page, regionId: string) {
  await page.evaluate((id) => {
    const region = document.getElementById(id)!;
    const seen: string[] = [];
    (window as unknown as Record<string, string[]>)[`__seen_${id}`] = seen;
    new MutationObserver(() => seen.push(region.textContent || '')).observe(region, {
      childList: true, characterData: true, subtree: true,
    });
  }, regionId);
  return () => page.evaluate(
    (id) => (window as unknown as Record<string, string[]>)[`__seen_${id}`],
    regionId,
  );
}

/** The front and back braille lines of the first /geometry_spec request; aborted. */
async function interceptGeometrySpec(page: Page) {
  const state: { lines: string[] | null; backLines: string[] | null; called: boolean } =
    { lines: null, backLines: null, called: false };
  await page.route('**/geometry_spec', async (route) => {
    if (!state.called) {
      const body = route.request().postDataJSON();
      state.lines = body?.lines ?? null;
      state.backLines = body?.back_lines ?? null;
    }
    state.called = true;
    await route.abort();
  });
  return state;
}

/**
 * Click Generate until the request reaches /geometry_spec. The Manifold worker
 * starts asynchronously and the app asks for another try until it is ready
 * (slowest on Firefox); any other message is a real failure.
 */
async function generate(page: Page, state: { called: boolean }) {
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#action-btn').click();
    for (let waited = 0; waited < 3000 && !state.called; waited += 100) {
      await page.waitForTimeout(100);
    }
    if (state.called) return;
    const notice = await page.locator('#error-message').getAttribute('class');
    const error = await page.locator('#error-text').textContent();
    if (error && !notice?.includes('info') && !/Manifold 3D engine/.test(error)) {
      throw new Error(`Generation was blocked before reaching /geometry_spec: ${error}`);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('The Manifold worker never became ready');
}

test.describe('Six-key entry on the Braille (Unicode) field', () => {
  test.describe.configure({ timeout: 120_000 });

  test('is off on load, and Space on the box turns it on and says so', async ({ page }) => {
    await openApp(page);
    const box = page.locator('#braille_six_key');
    await expect(box).not.toBeChecked();

    await box.focus();
    await page.keyboard.press('Space');
    await expect(box).toBeChecked();
    await expect(page.locator('#braille-unicode-status')).toHaveText('Six-key entry is on.');
    await expect(page.locator('#braille-unicode-live')).toHaveText('Six-key entry is on.');

    await page.keyboard.press('Space');
    await expect(page.locator('#braille-unicode-status')).toHaveText('Six-key entry is off.');
  });

  test('holding f, d and k types dots 1 2 5 at the caret, and the field counts as edited', async ({ page }) => {
    await openApp(page);
    await turnSixKeyOn(page);
    const field = page.locator('#braille-unicode');
    await field.focus();

    await chord(page, ['f', 'd', 'k']);
    await expect(field).toHaveValue('⠓');
    await expect(page.locator('#braille-unicode-status')).toContainText('Edited');

    // At the caret, not at the end: move into the middle and type a blank cell.
    await chord(page, ['f']);
    await page.keyboard.press('ArrowLeft');
    await chord(page, ['Space']);
    await expect(field).toHaveValue('⠓⠀⠁');
  });

  test('announces each cell once, as its dots, in order', async ({ page }) => {
    await openApp(page);
    await turnSixKeyOn(page);
    await page.locator('#braille-unicode').focus();
    const seen = await recordRegion(page, 'braille-unicode-live');

    await chord(page, ['f', 'd', 'k']);
    await page.waitForTimeout(150);
    await chord(page, ['f', 's']);
    await page.waitForTimeout(150);
    await chord(page, ['d', 'k']);

    await expect.poll(async () => (await seen()).filter(Boolean))
      .toEqual(['dots 1 2 5', 'dots 1 3', 'dots 2 5']);
  });

  test('announces a repeated cell again', async ({ page }) => {
    await openApp(page);
    await turnSixKeyOn(page);
    await page.locator('#braille-unicode').focus();
    const seen = await recordRegion(page, 'braille-unicode-live');

    await chord(page, ['f', 'd', 'k']);
    await page.waitForTimeout(1200);
    await chord(page, ['f', 'd', 'k']);

    // Emptied, then the same words written again after a gap.
    await expect.poll(seen).toEqual(['dots 1 2 5', '', 'dots 1 2 5']);
  });

  test('leaves Tab alone, so the keyboard can still leave the field', async ({ page }) => {
    await openApp(page);
    await turnSixKeyOn(page);
    await page.locator('#braille-unicode').focus();
    await page.keyboard.press('Tab');
    await expect.poll(() => page.evaluate(() => document.activeElement?.id))
      .toBe('translate-to-text-btn');
  });

  test('off, the keys type letters and the field says how to convert them', async ({ page }) => {
    await openApp(page);
    await page.locator('#braille-unicode').focus();
    await page.keyboard.press('f');
    await expect(page.locator('#braille-unicode')).toHaveValue('f');
    await expect(page.locator('#braille-unicode-status')).toContainText('"f", which is not a braille character');
    await expect(page.locator('#braille-unicode-status')).toContainText('Convert braille ASCII');
  });

  test('toggling the box never reaches the form, so a built STL stays valid', async ({ page }) => {
    await openApp(page);
    await page.evaluate(() => {
      const events: string[] = [];
      (window as unknown as { __formEvents: string[] }).__formEvents = events;
      const form = document.getElementById('braille_six_key')!.closest('form')!;
      form.addEventListener('input', () => events.push('input'));
      form.addEventListener('change', () => events.push('change'));
    });
    await turnSixKeyOn(page);
    await page.locator('#braille_six_key').uncheck();
    expect(await page.evaluate(() => (window as unknown as { __formEvents: string[] }).__formEvents))
      .toEqual([]);
  });

  test('Reset turns it off', async ({ page }) => {
    await openApp(page);
    await turnSixKeyOn(page);
    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#braille_six_key')).not.toBeChecked();
    await page.locator('#braille-unicode').focus();
    await page.keyboard.press('f');
    await expect(page.locator('#braille-unicode')).toHaveValue('f');
  });
});

test.describe('Convert braille ASCII on the Braille (Unicode) field', () => {
  test.describe.configure({ timeout: 120_000 });

  test('converts in place, keeps focus on the button, and the cells are embossed verbatim', async ({ page }) => {
    await openApp(page);
    const field = page.locator('#braille-unicode');
    await field.fill(BRAILLE_ASCII_SAMPLE);
    await expect(page.locator('#braille-unicode-status')).toContainText('not a braille character');

    await page.locator('#convert-braille-ascii-btn').focus();
    await page.keyboard.press('Enter');
    await expect(field).toHaveValue(BRAILLE_ASCII_CELLS);
    await expect(page.locator('#braille-unicode-status'))
      .toHaveText('Converted 1 line of braille ASCII to braille cells.');
    await expect(page.locator('#braille-unicode-live'))
      .toHaveText('Converted 1 line of braille ASCII to braille cells.');
    await expect.poll(() => page.evaluate(() => document.activeElement?.id))
      .toBe('convert-braille-ascii-btn');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);
    expect(spec.lines?.[0]).toBe(BRAILLE_ASCII_CELLS);
  });

  test('counts the lines it converted', async ({ page }) => {
    await openApp(page);
    await page.locator('#braille-unicode').fill('ab\ncd');
    await page.locator('#convert-braille-ascii-btn').click();
    await expect(page.locator('#braille-unicode')).toHaveValue('⠁⠃\n⠉⠙');
    await expect(page.locator('#braille-unicode-status'))
      .toHaveText('Converted 2 lines of braille ASCII to braille cells.');
  });

  test('reads the lowercase NABCC forms ` { | } ~ as @ [ \\ ] ^', async ({ page }) => {
    await openApp(page);
    await page.locator('#braille-unicode').fill('`{|}~');
    await page.locator('#convert-braille-ascii-btn').click();
    await expect(page.locator('#braille-unicode')).toHaveValue('⠈⠪⠳⠻⠘');
  });

  test('refuses a character that is not braille ASCII and leaves the field as it was', async ({ page }) => {
    await openApp(page);
    await page.locator('#braille-unicode').fill('abé');
    await page.locator('#convert-braille-ascii-btn').click();
    await expect(page.locator('#braille-unicode')).toHaveValue('abé');
    await expect(page.locator('#braille-unicode-status'))
      .toHaveText('Line 1 contains "é", which is not a braille ASCII character.');
    await expect(page.locator('#braille-unicode-live'))
      .toHaveText('Line 1 contains "é", which is not a braille ASCII character.');
  });

  test('on an empty field, says what to paste first', async ({ page }) => {
    await openApp(page);
    await page.locator('#convert-braille-ascii-btn').click();
    await expect(page.locator('#braille-unicode-status'))
      .toHaveText('Paste braille ASCII in the Braille (Unicode) field first, then press Convert braille ASCII.');
  });
});

test.describe('The same tools on the Back of Card braille field', () => {
  test.describe.configure({ timeout: 120_000 });

  test('are unavailable while the card is single-sided', async ({ page }) => {
    await openApp(page);
    await expect(page.locator('#back_braille_six_key')).toBeDisabled();
    await expect(page.locator('#back-convert-braille-ascii-btn')).toBeDisabled();
  });

  test('six-key entry types into the back field only and speaks from its own region', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await turnSixKeyOn(page, 'back_braille_six_key');
    await expect(page.locator('#back-braille-unicode-status')).toHaveText('Six-key entry is on.');
    const seen = await recordRegion(page, 'back-braille-unicode-live');

    await page.locator('#back-braille-unicode').focus();
    await chord(page, ['f', 'd', 'k']);
    await expect(page.locator('#back-braille-unicode')).toHaveValue('⠓');
    await expect.poll(async () => (await seen()).filter(Boolean)).toEqual(['dots 1 2 5']);
    // The front is untouched, and its box was never turned on.
    await expect(page.locator('#braille-unicode')).toHaveValue('');
    await expect(page.locator('#braille_six_key')).not.toBeChecked();
    await page.locator('#braille-unicode').focus();
    await page.keyboard.press('f');
    await expect(page.locator('#braille-unicode')).toHaveValue('f');
  });

  test('converted braille ASCII on the back is sent as the back lines', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await page.locator('#braille-unicode').fill('⠁');
    await page.locator('#back-braille-unicode').fill(BRAILLE_ASCII_SAMPLE);
    await page.locator('#back-convert-braille-ascii-btn').click();
    await expect(page.locator('#back-braille-unicode')).toHaveValue(BRAILLE_ASCII_CELLS);
    await expect(page.locator('#back-braille-unicode-status'))
      .toHaveText('Converted 1 line of braille ASCII to braille cells.');
    // The front field's status is not the one that answered.
    await expect(page.locator('#braille-unicode-status')).not.toContainText('Converted');

    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);
    expect(spec.backLines?.[0]).toBe(BRAILLE_ASCII_CELLS);
  });

  test('a refusal on the back leaves the back field as it was', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await page.locator('#back-braille-unicode').fill('ab€');
    await page.locator('#back-convert-braille-ascii-btn').click();
    await expect(page.locator('#back-braille-unicode')).toHaveValue('ab€');
    await expect(page.locator('#back-braille-unicode-status'))
      .toHaveText('Line 1 contains "€", which is not a braille ASCII character.');
  });

  test('Reset turns the back box off too', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await turnSixKeyOn(page, 'back_braille_six_key');
    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#back_braille_six_key')).not.toBeChecked();
  });
});

/**
 * Press Translate to Braille until the field fills: the liblouis worker
 * starts asynchronously and reports "not initialized" until it is ready
 * (reliably on Firefox). Any other status is a real failure.
 */
async function translateToBraille(page: Page) {
  const field = page.locator('#braille-unicode');
  for (let attempt = 0; attempt < 15; attempt++) {
    await page.locator('#translate-to-braille-btn').click();
    for (let waited = 0; waited < 4000; waited += 200) {
      if ((await field.inputValue()) !== '') return;
      await page.waitForTimeout(200);
    }
    const status = await page.locator('#braille-unicode-status').textContent();
    if (status && !/[Ll]iblouis|not initialized|unavailable/.test(status)) {
      throw new Error(`Translate to Braille reported: ${status}`);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('The liblouis worker never became ready');
}

test.describe('Auto Placement translates each typed line whole', () => {
  test.describe.configure({ timeout: 120_000 });

  // The default row: 13 text cells, contracted UEB, capitals on.
  test('a capital passage over two rows keeps one indicator and one terminator', async ({ page }) => {
    await openApp(page);
    await expect(page.locator('#grid_columns')).toHaveValue('13');
    await page.locator('#auto-text').fill('ROOM ROOM ROOM ROOM');
    await translateToBraille(page);
    await expect(page.locator('#braille-unicode')).toHaveValue('⠠⠠⠠⠗⠕⠕⠍ ⠗⠕⠕⠍\n⠗⠕⠕⠍ ⠗⠕⠕⠍⠠⠄');
  });

  test('an e-mail address divides with the line continuation sign, noted in the field status', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('first.last@example.com');
    await translateToBraille(page);
    await expect(page.locator('#braille-unicode')).toHaveValue('⠋⠊⠗⠌⠲⠇⠁⠌⠈⠁⠐\n⠑⠭⠁⠍⠏⠇⠑⠲⠉⠕⠍');
    await expect(page.locator('#braille-unicode-status')).toContainText(
      '"first.last@example.com" is divided across rows. Each row but the last ends with the line continuation sign (dot 5).',
    );
  });

  test('Generate sends the divided address and shows the note in the field, not as an error', async ({ page }) => {
    await openApp(page);
    await page.locator('#auto-text').fill('first.last@example.com');
    const spec = await interceptGeometrySpec(page);
    await generate(page, spec);
    expect(spec.lines?.slice(0, 2)).toEqual(['⠋⠊⠗⠌⠲⠇⠁⠌⠈⠁⠐', '⠑⠭⠁⠍⠏⠇⠑⠲⠉⠕⠍']);
    await expect(page.locator('#braille-unicode-status')).toContainText('line continuation sign (dot 5)');
    await expect(page.locator('#error-text')).not.toContainText('line continuation sign');
  });

  test('with the repeated number sign chosen, each continued row starts with its own sign', async ({ page }) => {
    await openApp(page);
    // Expert Mode, Translation Options: the non-standard option, set at its
    // source with the change event a click sends (the panel is collapsed).
    await page.evaluate(() => {
      const radio = document.querySelector('input[name="repeat_number_sign"][value="on"]') as HTMLInputElement;
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await page.locator('#auto-text').fill('1,000,000,000,000');
    await translateToBraille(page);
    const rows = (await page.locator('#braille-unicode').inputValue()).split('\n');
    expect(rows).toEqual(['⠼⠁⠂⠼⠚⠚⠚⠂⠐', '⠼⠚⠚⠚⠂⠼⠚⠚⠚⠂⠐', '⠼⠚⠚⠚']);
  });

  test('a divided number keeps one number sign', async ({ page }) => {
    await openApp(page);
    // 13 cells: the 13-cell number fits whole, so a longer one is needed.
    await page.locator('#auto-text').fill('1,000,000,000,000');
    await translateToBraille(page);
    const rows = (await page.locator('#braille-unicode').inputValue()).split('\n');
    expect(rows.length).toBe(2);
    expect(rows[0].endsWith('⠐')).toBe(true);
    expect([...rows.join('')].filter((cell) => cell === '⠼')).toHaveLength(1);
  });
});
