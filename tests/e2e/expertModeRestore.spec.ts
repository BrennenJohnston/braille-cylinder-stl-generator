/**
 * E2E regression test: the Expert Mode button reports its real state after a
 * reload.
 *
 * Found 2026-09-30 in the help and documentation review: the load-time restore
 * of `braille_prefs_expert_visible` re-opened the panel and relabelled the
 * button "Hide Expert Mode", but never set `aria-expanded`, so a screen reader
 * heard "Hide Expert Mode, button, collapsed" over an open panel. Fixed on
 * 2026-10-01 on Brennen's word. The checks read the attribute the accessibility
 * tree reads, in both directions, across a real reload.
 *
 * @see docs/development/ADA_ACCESSIBILITY_VALIDATION_SOP.md - accordions keep
 *      aria-expanded and aria-controls up to date
 */

import { test, expect, type Page } from '@playwright/test';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('#embosser-setup-selection');
}

async function reloadApp(page: Page) {
  await page.reload();
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector('#embosser-setup-selection');
}

test.describe('Expert Mode button after a reload', () => {
  test('a panel restored open is announced as expanded', async ({ page }) => {
    await openApp(page);
    const toggle = page.locator('#expert-toggle');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await reloadApp(page);
    await expect(page.locator('#expert-settings')).toBeVisible();
    await expect(toggle).toContainText('Hide Expert Mode');
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  test('a panel restored closed stays collapsed', async ({ page }) => {
    await openApp(page);
    const toggle = page.locator('#expert-toggle');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await reloadApp(page);
    await expect(page.locator('#expert-settings')).toBeHidden();
    await expect(toggle).toContainText('Show Expert Mode');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });
});
