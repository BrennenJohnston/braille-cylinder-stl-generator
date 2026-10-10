/**
 * E2E tests for the preview's Display settings drawer (2026-09-29).
 *
 * Brennen's finding from testing on a phone: the preview's Brightness /
 * Contrast / Edges toolbar is an overlay at the bottom of the 3D viewer, and
 * on a phone it stacked into three rows over a 200 px viewer - measured at
 * 390 x 844 it covered 67 % of the viewer, and with the label on top only a
 * sliver of the model was left. On compact layouts the controls are now
 * stowed behind a "Display settings" disclosure button:
 *
 *  - portrait (the stacked layout, up to 768 px wide): the button sits under
 *    the viewer at the right and the controls open BELOW it, in the page flow,
 *    so the model stays in full view while it is adjusted;
 *  - landscape phones (the two-column layout at 500 px tall or less): the
 *    button is a 44 px gear in the viewer's bottom-right corner (the words
 *    stay its accessible name) and the controls open along the bottom beside
 *    it, so the upper part of the model stays in view;
 *  - a wide screen is unchanged: no button, the overlay as before.
 *
 * Measured, not asserted on the CSS: every claim here reads laid-out boxes.
 * The button's words are S-PD1, signed off by Brennen 2026-10-01.
 *
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md section 3.8
 */

import { test, expect, type Page } from '@playwright/test';

const S_PD1_TOGGLE = 'Display settings';
const CONTROLS = ['brightness-decrease', 'brightness-increase', 'contrast-decrease', 'contrast-increase', 'edges-toggle'];
const MIN_TARGET_PX = 44;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#action-btn');
}

async function box(page: Page, selector: string) {
  const b = await page.locator(selector).boundingBox();
  expect(b, `${selector} has no box`).not.toBeNull();
  return b!;
}

const toHundredthPx = (value: number) => Math.round(value * 100) / 100;

async function expectTargetsAtFloor(page: Page) {
  for (const id of CONTROLS) {
    const b = await box(page, `#${id}`);
    expect.soft(toHundredthPx(b.width), `#${id} width`).toBeGreaterThanOrEqual(MIN_TARGET_PX);
    expect.soft(toHundredthPx(b.height), `#${id} height`).toBeGreaterThanOrEqual(MIN_TARGET_PX);
  }
}

/**
 * Diagnostics for the narrowing test below (R1-Q-40, 2026-10-05). It has
 * failed once and passed on retry in five CI runs, all on Linux, and never in
 * 70 local trials on Windows under seven conditions (R1-Q-38). The page opens
 * the drawer when the compact layout's change event finds focus inside the
 * controls, so these record, from the first byte, the order of focus moves,
 * resizes and that change event, and a failure prints the record.
 */
const COMPACT_QUERY = '(max-width: 768px), (min-width: 769px) and (max-height: 500px)';

async function recordFocusTimeline(page: Page) {
  await page.addInitScript((query) => {
    const timeline: unknown[] = [];
    (window as unknown as { __focusTimeline: unknown[] }).__focusTimeline = timeline;
    const name = (target: EventTarget | null) => (target instanceof Element ? target.id || target.tagName : null);
    const log = (...entry: unknown[]) => timeline.push([Math.round(performance.now()), ...entry]);
    document.addEventListener('focusin', (event) => log('focusin', name(event.target)), true);
    document.addEventListener('focusout', (event) => log('focusout', name(event.target), name(event.relatedTarget)), true);
    window.addEventListener('resize', () => log('resize', window.innerWidth, window.innerHeight));
    // Registered before the page's own listener, so it sees what the page's handler sees.
    window.matchMedia(query).addEventListener('change', (event) => {
      log('compact-change', event.matches, 'focus=' + name(document.activeElement));
    });
  }, COMPACT_QUERY);
}

async function withFocusTimeline(page: Page, check: () => Promise<void>) {
  try {
    await check();
  } catch (error) {
    const state = await page
      .evaluate(() => ({
        focus: document.activeElement ? document.activeElement.id || document.activeElement.tagName : null,
        expanded: document.getElementById('preview-display-toggle')?.getAttribute('aria-expanded') ?? null,
        size: [window.innerWidth, window.innerHeight],
        timeline: (window as unknown as { __focusTimeline?: unknown[] }).__focusTimeline ?? [],
      }))
      .catch((readError: unknown) => ({ unavailable: String(readError) }));
    if (error instanceof Error) error.message += `

Focus timeline (R1-Q-38): ${JSON.stringify(state)}`;
    throw error;
  }
}

test.describe('Preview Display settings drawer', () => {
  test('on a wide screen the controls stay the overlay and there is no button', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await openApp(page);

    await expect(page.locator('#preview-display-toggle')).toBeHidden();
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeVisible();

    // Still the bottom overlay inside the viewer.
    const viewer = await box(page, '#viewer');
    const controls = await box(page, '#preview-display-controls');
    expect(controls.y).toBeGreaterThan(viewer.y + viewer.height / 2);
    expect(controls.y + controls.height).toBeLessThanOrEqual(viewer.y + viewer.height + 1);
  });

  test('on a phone the controls are stowed behind the button and open below the viewer', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openApp(page);

    const toggle = page.getByRole('button', { name: S_PD1_TOGGLE });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveId('preview-display-toggle');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(toggle).toHaveAttribute('aria-controls', 'preview-display-controls');
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeHidden();

    // Under the viewer, at its right edge, never over it.
    const viewer = await box(page, '#viewer');
    const t = await box(page, '#preview-display-toggle');
    expect(t.y).toBeGreaterThanOrEqual(viewer.y + viewer.height);
    expect(Math.abs((t.x + t.width) - (viewer.x + viewer.width))).toBeLessThanOrEqual(2);
    expect.soft(toHundredthPx(t.height)).toBeGreaterThanOrEqual(MIN_TARGET_PX);

    // The chevron is decoration (aria-hidden); aria-expanded carries the state.
    const chevron = page.locator('#preview-display-toggle-chevron');
    await expect(chevron).toHaveText('▼');
    await expect(chevron).toHaveAttribute('aria-hidden', 'true');

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(chevron).toHaveText('▲');
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeVisible();
    const controls = await box(page, '#preview-display-controls');
    const viewerAfter = await box(page, '#viewer');
    expect(controls.y).toBeGreaterThanOrEqual(viewerAfter.y + viewerAfter.height);
    expect(controls.y).toBeGreaterThanOrEqual(t.y + t.height - 1);
    await expectTargetsAtFloor(page);

    // The controls still work from inside the drawer.
    await page.locator('#edges-toggle').click();
    await expect(page.locator('#edges-toggle')).toHaveAttribute('aria-pressed', 'false');

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeHidden();
  });

  test('the keyboard opens it, Tab reaches the controls, and Escape closes it back onto the button', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openApp(page);

    const toggle = page.locator('#preview-display-toggle');
    await toggle.focus();
    await page.keyboard.press('Enter');
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await page.keyboard.press('Tab');
    await expect(page.locator('#brightness-decrease')).toBeFocused();

    await page.keyboard.press('Escape');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(toggle).toBeFocused();
    await expect(page.locator('#brightness-decrease')).toBeHidden();

    await page.keyboard.press('Space');
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  test('in phone landscape the button is a gear in the viewer corner and the panel opens beside it', async ({ page }) => {
    await page.setViewportSize({ width: 844, height: 390 });
    await openApp(page);

    // The words are visually hidden here and stay the accessible name.
    const toggle = page.getByRole('button', { name: S_PD1_TOGGLE });
    await expect(toggle).toBeVisible();
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeHidden();

    const viewer = await box(page, '#viewer');
    const t = await box(page, '#preview-display-toggle');
    expect.soft(toHundredthPx(t.width)).toBeGreaterThanOrEqual(MIN_TARGET_PX);
    expect.soft(toHundredthPx(t.height)).toBeGreaterThanOrEqual(MIN_TARGET_PX);
    // Inside the viewer, in its bottom-right corner.
    expect(t.x).toBeGreaterThan(viewer.x + viewer.width / 2);
    expect(t.y).toBeGreaterThan(viewer.y + viewer.height / 2);
    expect(t.x + t.width).toBeLessThanOrEqual(viewer.x + viewer.width);
    expect(t.y + t.height).toBeLessThanOrEqual(viewer.y + viewer.height);

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeVisible();
    // Off the button first: the shared .font-size-btn hover lifts it 1 px.
    await page.mouse.move(0, 0);
    const controls = await box(page, '#preview-display-controls');
    // Beside the gear, not over it, and the upper half of the model in view.
    expect(controls.x + controls.width).toBeLessThanOrEqual(t.x);
    expect(controls.y).toBeGreaterThan(viewer.y + viewer.height / 2);
    // The gear did not move when the panel appeared. Polled, because the
    // hover lift eases back over 0.2 s once the pointer has left.
    await expect.poll(async () => Math.round((await box(page, '#preview-display-toggle')).y)).toBe(Math.round(t.y));
    expect((await box(page, '#preview-display-toggle')).x).toBeCloseTo(t.x, 0);
    await expectTargetsAtFloor(page);
  });

  test('in phone landscape at a large text size the old overlay comes back, and the gear returns at normal size', async ({ page }) => {
    // At 150 % app text the controls no longer fit beside the gear, and the
    // column is too short for a panel anywhere else - measured 2026-09-29 -
    // so the page keeps exactly the overlay it had before the drawer.
    // The size watcher must settle, never loop: no "ResizeObserver loop" report.
    const errors: string[] = [];
    page.on('console', (message) => {
      if (/ResizeObserver/.test(message.text())) errors.push(message.text());
    });
    page.on('pageerror', (error) => {
      if (/ResizeObserver/.test(error.message)) errors.push(error.message);
    });
    await page.setViewportSize({ width: 844, height: 390 });
    await openApp(page);
    const toggle = page.locator('#preview-display-toggle');
    await expect(toggle).toBeVisible();

    // Root only, the way applyFontSize() scales the app; the drawer is closed.
    await page.evaluate(() => { document.documentElement.style.fontSize = '150%'; });
    await expect(toggle).toBeHidden();
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeVisible();
    const viewer = await box(page, '#viewer');
    const controls = await box(page, '#preview-display-controls');
    expect(Math.abs(controls.width - viewer.width)).toBeLessThanOrEqual(2);

    await page.evaluate(() => { document.documentElement.style.fontSize = '100%'; });
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    for (const id of CONTROLS) await expect(page.locator(`#${id}`)).toBeHidden();
    expect(errors).toEqual([]);
  });

  test('narrowing the window while a control has focus opens the drawer instead of hiding it', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await recordFocusTimeline(page);
    await openApp(page);

    await page.locator('#brightness-increase').focus();
    await page.setViewportSize({ width: 390, height: 844 });

    await withFocusTimeline(page, async () => {
      await expect(page.locator('#preview-display-toggle')).toHaveAttribute('aria-expanded', 'true');
      await expect(page.locator('#brightness-increase')).toBeVisible();
      await expect(page.locator('#brightness-increase')).toBeFocused();
    });
  });
});
