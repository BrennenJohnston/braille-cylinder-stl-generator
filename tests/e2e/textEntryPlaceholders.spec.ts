/**
 * E2E tests for the text-entry placeholders (Brennen, 2026-09-28).
 *
 * A new user should see which box takes text and which shows braille before
 * typing anything: the text box carries a sample sentence and the Braille
 * (Unicode) box carries that sentence's own translation, both styled as hints
 * (muted colour, italic for text, upright for braille) that vanish on input.
 *
 * The braille placeholders are derived here, not typed from memory: the test
 * puts the sample through the real Translate to Braille and expects the field
 * to show exactly the placeholder. The braille field's placeholder must not be
 * read as its description (that comes from aria-describedby), which is checked
 * on the computed accessibility tree over CDP, since static markup cannot say.
 *
 * S-P3 (the front sample) and the shortened back sample were signed by Brennen
 * on 2026-09-28; the braille placeholders S-P4 and S-P5 follow them by rule.
 */

import { expect, test, type Page } from '@playwright/test';

const FRONT_SAMPLE = 'Type the text you want in braille here.';
const BACK_SAMPLE = 'Type the text for the back of the card here.';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#embosser-setup-selection');
}

async function translate(page: Page, buttonId: string, fieldId: string) {
  const field = page.locator(`#${fieldId}`);
  for (let attempt = 0; attempt < 20; attempt++) {
    await page.locator(`#${buttonId}`).click();
    for (let waited = 0; waited < 4000; waited += 200) {
      if ((await field.inputValue()) !== '') return;
      await page.waitForTimeout(200);
    }
    await page.waitForTimeout(1000);
  }
  throw new Error('the liblouis worker never became ready');
}

test.describe('Text entry placeholders', () => {
  test.describe.configure({ timeout: 120_000 });

  test('the front text box shows the sample and the braille box its exact translation', async ({ page }) => {
    await openApp(page);
    await expect(page.locator('#auto-text')).toHaveAttribute('placeholder', FRONT_SAMPLE);
    const braillePlaceholder = await page.locator('#braille-unicode').getAttribute('placeholder');
    expect(braillePlaceholder).toBeTruthy();

    await page.locator('#auto-text').fill(FRONT_SAMPLE);
    await translate(page, 'translate-to-braille-btn', 'braille-unicode');
    await expect(page.locator('#braille-unicode')).toHaveValue(braillePlaceholder!);
  });

  test('the back text box shows its sample and the back braille box its exact translation', async ({ page }) => {
    await openApp(page);
    await page.locator('#card_sides_double').check();
    await expect(page.locator('#back-text')).toHaveAttribute('placeholder', BACK_SAMPLE);
    const braillePlaceholder = await page.locator('#back-braille-unicode').getAttribute('placeholder');
    expect(braillePlaceholder).toBeTruthy();

    await page.locator('#back-text').fill(BACK_SAMPLE);
    await translate(page, 'back-translate-to-braille-btn', 'back-braille-unicode');
    await expect(page.locator('#back-braille-unicode')).toHaveValue(braillePlaceholder!);
  });

  test('placeholders read as hints in every theme', async ({ page }) => {
    await openApp(page);

    for (const theme of ['light', 'dark', 'high-contrast']) {
      await page.evaluate((t) => document.documentElement.setAttribute('data-theme', t), theme);
      const measured = await page.evaluate(() => {
        const token = getComputedStyle(document.documentElement).getPropertyValue('--text-placeholder').trim();
        const probe = document.createElement('span');
        probe.style.color = token;
        document.body.appendChild(probe);
        const tokenRgb = getComputedStyle(probe).color;
        probe.remove();
        const text = getComputedStyle(document.getElementById('auto-text')!, '::placeholder');
        const braille = getComputedStyle(document.getElementById('braille-unicode')!, '::placeholder');
        return {
          tokenRgb,
          textColor: text.color, textStyle: text.fontStyle, textOpacity: text.opacity,
          brailleColor: braille.color, brailleStyle: braille.fontStyle,
        };
      });
      expect(measured.textColor, theme).toBe(measured.tokenRgb);
      expect(measured.brailleColor, theme).toBe(measured.tokenRgb);
      expect(measured.textStyle, theme).toBe('italic');
      expect(measured.brailleStyle, theme).toBe('normal');
      expect(measured.textOpacity, theme).toBe('1');
    }
  });

  test('the braille placeholder is not the braille field\'s spoken description', async ({ page, browserName }) => {
    // Until 2026-09-30 this check closed the test above, so Firefox and WebKit
    // failed it in CI on the CDP call alone, after their theme checks passed.
    test.skip(browserName !== 'chromium', 'the computed accessibility tree is read over CDP, which only Chromium has');
    await openApp(page);

    // The computed accessibility tree: the braille field is described by its
    // help sentence and status, never by the braille placeholder.
    const client = await page.context().newCDPSession(page);
    await client.send('Accessibility.enable');
    const { root } = await client.send('DOM.getDocument', { depth: 0 });
    const { nodeId } = await client.send('DOM.querySelector', { nodeId: root.nodeId, selector: '#braille-unicode' });
    const { nodes } = await client.send('Accessibility.getPartialAXTree', { nodeId, fetchRelatives: false });
    const description = String(nodes[0]?.description?.value ?? '');
    expect(description).toContain('Accepts braille characters only');
    expect(description).not.toMatch(/[⠀-⣿]/);
  });
});
