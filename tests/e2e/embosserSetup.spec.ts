/**
 * E2E tests for the "Embosser setup" menu item (2026-09-20 programme, sub-plan C).
 *
 * One item at the top of the form holds three either/or choices - embosser
 * version, gears, card sides - that used to be three toggles in three places,
 * two of them labelled BETA. What this file pins:
 *
 *   1. Structure: first form item, an h2 for the item and an h3 per choice,
 *      native radio groups with the defaults Version 1 / Standard / Single-sided.
 *   2. Every group's description is inside the ADA SOP Step 6.8 ceiling.
 *   3. Keyboard: arrow keys move within each group and carry the selection.
 *   4. The "Which setup should I choose?" link opens the help modal on the
 *      Embosser Setup tab.
 *   5. Choices persist across a reload; Reset restores the defaults.
 *   6. No BETA or prototype tags remain anywhere on the page.
 *
 * The strings quoted here (S-M1..S-M11) were signed off by Brennen on 2026-09-21; reword only with his sign-off.
 *
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md
 */

import { expect, test, type Page } from '@playwright/test';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#indicator-mode-selection');
}

const GROUPS = [
  { fieldset: '#embosser-version-selection', heading: 'Embosser version', radios: ['#embosser_version_1', '#embosser_version_2'] },
  { fieldset: '#gear-rollers-selection', heading: 'Gears', radios: ['#gear_mode_standard', '#gear_mode_fixed'] },
  { fieldset: '#card-sides-selection', heading: 'Card sides', radios: ['#card_sides_single', '#card_sides_double'] },
];

test.describe('Embosser setup menu item', () => {
  test('is the first form item, headed h2 with an h3 per choice, defaults in place', async ({ page }) => {
    await openApp(page);

    const item = page.locator('#embosser-setup-selection');
    await expect(item).toBeVisible();
    expect(
      await page.evaluate(() => {
        const el = document.querySelector('#embosser-setup-selection');
        return el?.previousElementSibling?.classList.contains('info-panel') ?? false;
      }),
    ).toBe(true);
    await expect(item.locator('> fieldset > legend h2.legend-heading')).toHaveText('Embosser setup');

    for (const group of GROUPS) {
      await expect(page.locator(`${group.fieldset} > legend h3.legend-heading`)).toHaveText(group.heading);
      await expect(page.locator(group.radios[0])).toBeChecked();
      await expect(page.locator(group.radios[1])).not.toBeChecked();
    }

    // The old controls and tags are gone.
    await expect(page.locator('#double_sided_enabled, #gear_rollers_enabled, #double-sided-menu-toggle, #v2-prototype-note')).toHaveCount(0);
    expect(await page.evaluate(() => document.body.innerText.includes('BETA'))).toBe(false);
    expect(await page.evaluate(() => document.body.innerText.includes('(prototype)'))).toBe(false);
  });

  test('every choice describes itself within the 25-word ceiling', async ({ page }) => {
    await openApp(page);
    for (const group of GROUPS) {
      const describedBy = await page.locator(group.fieldset).getAttribute('aria-describedby');
      expect(describedBy, `${group.fieldset} has no aria-describedby`).toBeTruthy();
      const words = (await page.locator(`#${describedBy}`).innerText()).trim().split(/\s+/).length;
      expect(words, `${group.fieldset} description is ${words} words`).toBeLessThanOrEqual(25);
    }
  });

  test('arrow keys move within each group and carry the selection', async ({ page }) => {
    await openApp(page);
    for (const group of GROUPS) {
      const [first, second] = group.radios.map((id) => page.locator(id));
      await first.focus();
      await page.keyboard.press('ArrowDown');
      await expect(second).toBeFocused();
      await expect(second).toBeChecked();
      await page.keyboard.press('ArrowUp');
      await expect(first).toBeFocused();
      await expect(first).toBeChecked();
    }
  });

  test('the help link opens the Embosser Setup tab', async ({ page }) => {
    await openApp(page);
    await page.locator('#embosser-setup-selection button.btn-link', { hasText: 'Which setup should I choose?' }).click();

    const modal = page.locator('#helpModal');
    await expect(modal).not.toHaveClass(/hidden/);
    await expect(modal).toBeVisible();
    await expect(page.locator('#tab-setup')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('#helpPanelSetup')).toBeVisible();
    await expect(page.locator('#helpPanelSetup')).toContainText('Version 1, Standard gears');
    await expect(page.locator('#helpPanelSetup')).toContainText('Version 2, Simplified gears');
    await expect(page.locator('#helpPanelSetup a[href*="printables.com"]')).toHaveCount(1);
  });

  test('choices persist across a reload and Reset restores the defaults', async ({ page }) => {
    await openApp(page);
    await page.locator('#gear_mode_fixed').check();
    await page.locator('#card_sides_double').check();
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_gear_rollers_enabled'))).toBe('1');
    expect(await page.evaluate(() => localStorage.getItem('braille_prefs_double_sided_enabled'))).toBe('1');

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('#indicator-mode-selection');
    await expect(page.locator('#gear_mode_fixed')).toBeChecked();
    await expect(page.locator('#card_sides_double')).toBeChecked();
    await expect(page.locator('#back-entry-fieldset')).not.toHaveAttribute('disabled');

    await page.locator('#reset-defaults-btn').click();
    await expect(page.locator('#gear_mode_standard')).toBeChecked();
    await expect(page.locator('#card_sides_single')).toBeChecked();
    await expect(page.locator('#embosser_version_1')).toBeChecked();
    await expect(page.locator('#back-entry-fieldset')).toHaveAttribute('disabled', '');
  });

  test('each choice announces itself once', async ({ page }) => {
    await openApp(page);
    const live = page.locator('#a11y-status');

    // ONE composed write: the choice sentence plus the gear notes that apply -
    // on untouched dials the 13 mm polygonal cutout is set, so S3 rides along.
    await page.locator('#gear_mode_fixed').check();
    await expect(live).toHaveText(
      'Simplified fixed gears selected. The polygonal cutout is not used while integrated gears are on.',
    );
    await page.locator('#gear_mode_standard').check();
    await expect(live).toHaveText('Standard gears selected.');

    await page.locator('#card_sides_double').check();
    await expect(live).toContainText('Double-sided card selected. The Back of Card section is now active.');
    await page.locator('#card_sides_single').check();
    await expect(live).toHaveText('Single-sided card selected.');
  });
});
