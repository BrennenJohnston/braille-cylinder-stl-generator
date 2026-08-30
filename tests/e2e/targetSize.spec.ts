/**
 * E2E regression test for the hit-target floor on the numeric dials.
 *
 * Every numeric dial in this app is a bare `input[type="number"]`, styled by one
 * CSS rule. That rule set `padding: 0.8em` and no height, which on desktop
 * computed to **41.75 px** - 2.25 px under the 44 x 44 floor this project holds
 * itself to, and under WCAG 2.5.5. All 29 of them, not one: the finding was
 * first recorded against the Version 2 key-clearance dial in 2026-08-28's
 * closeout, with the note that "so is every other Expert Mode number input" and
 * that fixing it meant touching them all. It was fixed on 2026-08-30 by adding
 * `min-height: 44px` to that single rule.
 *
 * The mobile block already carried `min-height: 48px`, so only the desktop path
 * was ever short - which is exactly why no manual pass on a phone-sized window
 * would have caught it, and why this file measures at a desktop viewport.
 *
 * What this pins, and why it is measured rather than asserted on the CSS text:
 * a `min-height` is only as good as the box model around it. `box-sizing:
 * border-box` is set globally here, so 44 px is the real outer height; if that
 * ever changed, or a later rule re-set `height`, the declaration would still be
 * present and the target would still shrink. So the assertion reads the laid-out
 * box, the way a finger meets it.
 *
 * @see docs/development/ADA_ACCESSIBILITY_VALIDATION_SOP.md section 5.4
 * @see .clinerules/project-facts.md - accessibility rule 4, "never shrink an
 *      existing target"
 */

import { test, expect, type Page } from '@playwright/test';

/** The project's floor, and WCAG 2.5.5 Target Size (Enhanced). */
const MIN_TARGET_PX = 44;

const EXPERT_PANELS = [
  'expert-panel-dimensions',
  'expert-panel-dots',
  'expert-panel-shapes',
  'expert-panel-spacing',
  'expert-panel-tactile',
  'expert-panel-translation',
];

async function openEveryDial(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#auto-text');

  await page.locator('#expert-toggle').click();
  await expect(page.locator('#expert-toggle')).toHaveAttribute('aria-expanded', 'true');

  // State-aware, not a blind click: the submenus open with Expert Mode, so
  // clicking unconditionally would close the ones already showing their dials.
  for (const panel of EXPERT_PANELS) {
    const toggle = page.locator(`[aria-controls="${panel}"]`).first();
    if (!(await toggle.count())) continue;
    // Tactile Indicator Dimensions is only shown when the tactile arrow is the
    // selected row indicator. A panel the user cannot reach holds no target to
    // measure, so skip it rather than force it open.
    if (!(await toggle.isVisible())) continue;
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') {
      await toggle.click();
    }
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  }
}

/** Every rendered number input, with the box a pointer actually has to hit. */
async function measureNumberInputs(page: Page) {
  return page.evaluate(() => {
    const out: { id: string; w: number; h: number }[] = [];
    document.querySelectorAll('input[type="number"]').forEach((el) => {
      const box = el.getBoundingClientRect();
      if (box.width === 0 && box.height === 0) return;
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') return;
      out.push({
        id: (el as HTMLInputElement).id || (el as HTMLInputElement).name || '(unnamed)',
        w: box.width,
        h: box.height,
      });
    });
    return out;
  });
}

test.describe('numeric dial hit targets', () => {
  test('every visible number input meets the 44 x 44 floor', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await openEveryDial(page);

    const dials = await measureNumberInputs(page);

    // If this drops to nothing the test has stopped measuring anything and must
    // not pass by vacancy.
    expect(dials.length).toBeGreaterThan(20);

    const short = dials.filter((d) => d.h < MIN_TARGET_PX || d.w < MIN_TARGET_PX);
    expect(
      short,
      `dials under ${MIN_TARGET_PX}px: ${short.map((d) => `${d.id} ${d.w}x${d.h}`).join(', ')}`,
    ).toEqual([]);
  });

  test('the floor survives a 200% font size', async ({ page }) => {
    // Growing the text must never be what pushes a control back under the floor,
    // and `min-height` in px against `em` padding is exactly where that could go
    // wrong. SOP step 6.7 tests reflow at this size; this tests the target.
    await page.setViewportSize({ width: 1440, height: 1000 });
    await openEveryDial(page);
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '200%';
    });
    await page.waitForTimeout(500);

    const dials = await measureNumberInputs(page);
    expect(dials.length).toBeGreaterThan(20);

    const short = dials.filter((d) => d.h < MIN_TARGET_PX || d.w < MIN_TARGET_PX);
    expect(
      short,
      `dials under ${MIN_TARGET_PX}px at 200% font: ${short.map((d) => `${d.id} ${d.w}x${d.h}`).join(', ')}`,
    ).toEqual([]);
  });
});
