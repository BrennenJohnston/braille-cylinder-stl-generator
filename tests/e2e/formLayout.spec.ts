/**
 * E2E tests for the form column layout and the Generate/Download button state.
 *
 * Two behaviours are pinned here because both were bugs users hit directly:
 *  - the action button must be reachable without scrolling, which means the
 *    form column scrolls in .form-scroll and the button lives in .action-footer
 *    outside it (and nothing nests a second scrollbar inside the first);
 *  - every settings change must drop the button back to "Generate STL", so a
 *    stale STL can never be downloaded under new settings.
 *
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md
 */

import { test, expect, type Page } from '@playwright/test';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#action-btn');
}

/** Elements whose content box overflows and that are set to scroll it. */
async function scrollableDescendants(page: Page, selector: string) {
  return page.evaluate((root) => {
    const host = document.querySelector(root);
    if (!host) return ['<missing>'];
    return [host, ...host.querySelectorAll('*')]
      .filter((el) => {
        const style = getComputedStyle(el);
        const scrolls = /(auto|scroll)/.test(style.overflowY);
        return scrolls && el.scrollHeight > el.clientHeight + 1;
      })
      .map((el) => el.tagName.toLowerCase() + (el.className ? `.${String(el.className).split(' ')[0]}` : ''));
  }, selector);
}

test.describe('Form column layout', () => {
  test.describe.configure({ timeout: 120_000 });

  test('keeps the action button visible without scrolling the form', async ({ page }) => {
    await openApp(page);

    const button = page.locator('#action-btn');
    await expect(button).toBeVisible();
    await expect(button).toBeInViewport();

    // Scroll the form body to the bottom; the footer must not move out of view
    await page.locator('.form-scroll').evaluate((el) => { el.scrollTop = el.scrollHeight; });
    await expect(button).toBeInViewport();

    // The button is a sibling of the scroll area, not inside it
    const insideScroll = await button.evaluate((el) => Boolean(el.closest('.form-scroll')));
    expect(insideScroll).toBe(false);
  });

  test('has exactly one scrollbar in the form column', async ({ page, browserName }) => {
    // The locked-viewport desktop layout only applies above 768px
    test.skip(browserName === 'webkit', 'WebKit reports overflow metrics inconsistently in headless mode');
    await page.setViewportSize({ width: 1280, height: 800 });
    await openApp(page);

    expect(await scrollableDescendants(page, '.form-section')).toEqual(['div.form-scroll']);
  });

  test('keeps the action button stuck to the viewport bottom on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 412, height: 840 });
    await openApp(page);

    const button = page.locator('#action-btn');

    // Sticky breaks silently if any ancestor becomes a scroll container, and the
    // failure looks like "the button is simply at the end of the page"
    for (const scrollTo of [0, 400, 900, 1400]) {
      await page.evaluate((top) => window.scrollTo(0, top), scrollTo);
      await page.waitForTimeout(150);
      await expect(button).toBeInViewport();
    }

    const noHorizontalScroll = await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    );
    expect(noHorizontalScroll).toBe(true);
  });

  test('resets Download back to Generate when a tactile dial changes', async ({ page }) => {
    await openApp(page);

    const button = page.locator('#action-btn');

    // Fake a completed generation: the reset path is what is under test, and
    // driving a real CSG run here would make the test depend on Manifold WASM.
    await page.evaluate(() => {
      const btn = document.getElementById('action-btn');
      if (!btn) return;
      btn.textContent = 'Download STL';
      btn.className = 'download-state';
      btn.setAttribute('data-state', 'download');
    });
    await expect(button).toHaveAttribute('data-state', 'download');

    // The tactile dials were the controls the old per-input listener list missed
    await page.locator('input[name="indicator_mode"][value="tactile"]').check();
    await page.evaluate(() => {
      const panel = document.getElementById('expert-settings');
      if (panel) panel.style.display = 'block';
      const tactile = document.getElementById('expert-panel-tactile');
      if (tactile) { tactile.style.display = 'block'; tactile.hidden = false; }
    });
    await page.evaluate(() => {
      const btn = document.getElementById('action-btn');
      if (!btn) return;
      btn.textContent = 'Download STL';
      btn.className = 'download-state';
      btn.setAttribute('data-state', 'download');
    });

    await page.locator('#tactile_indicator_raise').fill('0.6');
    await expect(button).toHaveAttribute('data-state', 'generate');
    await expect(button).toHaveText('Generate STL');
  });

  test('acts on the first click even when a text field still has focus', async ({ page }) => {
    await openApp(page);

    const submitted = page.evaluate(() => new Promise<boolean>((resolve) => {
      const form = document.getElementById('braille-form');
      form?.addEventListener('submit', () => resolve(true), { once: true, capture: true });
      setTimeout(() => resolve(false), 8000);
    }));

    // Typing here leaves the textarea focused, so pressing the button fires the
    // textarea's change event on the same mousedown. WebKit dispatches no click
    // at all if that handler rewrites the button, which made the primary action
    // silently do nothing on Safari.
    await page.locator('#braille-unicode').fill('\u2801\u2803');
    await page.locator('#action-btn').click();

    expect(await submitted).toBe(true);
  });

  test('exposes the edge outline toggle as a pressable button', async ({ page }) => {
    await openApp(page);

    // The overlay is the low-vision escape hatch from lighting-dependent shading
    // (WCAG G174), so its pressed state has to be readable by assistive tech.
    const edges = page.locator('#edges-toggle');
    await expect(edges).toBeVisible();
    await expect(edges).toHaveAttribute('aria-pressed', 'false');

    await edges.click();
    await expect(edges).toHaveAttribute('aria-pressed', 'true');
    await expect(edges).toHaveClass(/active/);

    await edges.click();
    await expect(edges).toHaveAttribute('aria-pressed', 'false');
    await expect(edges).not.toHaveClass(/active/);
  });

  test('lets the user set their own braille cell count without it being overwritten', async ({ page }) => {
    await openApp(page);

    await page.evaluate(() => {
      const panel = document.getElementById('expert-settings');
      if (panel) panel.style.display = 'block';
      const spacing = document.getElementById('expert-panel-spacing');
      if (spacing) { spacing.style.display = 'block'; spacing.hidden = false; }
    });

    const cells = page.locator('#grid_columns');
    await expect(cells).toHaveValue('13');

    await cells.fill('9');
    // Switching plate type used to normalize the dial straight back to 13
    await page.locator('input[name="plate_type"][value="negative"]').check();
    await expect(cells).toHaveValue('9');
    // ...but the recommendation is still surfaced in the note
    await expect(page.locator('#grid_columns_note')).toContainText('Recommended value: 13');
  });
});
