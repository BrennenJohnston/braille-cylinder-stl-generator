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
    // It starts on, and the static markup has to say so: the button is styled
    // pressed before any script runs.
    const edges = page.locator('#edges-toggle');
    await expect(edges).toBeVisible();
    await expect(edges).toHaveAttribute('aria-pressed', 'true');
    await expect(edges).toHaveClass(/active/);

    await edges.click();
    await expect(edges).toHaveAttribute('aria-pressed', 'false');
    await expect(edges).not.toHaveClass(/active/);

    await edges.click();
    await expect(edges).toHaveAttribute('aria-pressed', 'true');
    await expect(edges).toHaveClass(/active/);
  });

  const toHundredthPx = (value: number) => Math.round(value * 100) / 100;

  test('keeps every preview overlay control at the 44x44 px floor', async ({ page }) => {
    await openApp(page);

    // These five shared the .font-size-btn class with the header controls, and
    // the 2026-08-18 fix was scoped to .font-size-controls - so the steppers sat
    // at 20x22 px and #edges-toggle at 49x20 px for three more days, under the
    // WCAG 2.5.5 floor. The floor is spelled out in px on purpose: an em-based
    // size drops back under it as soon as the app font size is reduced, which is
    // why 75% is checked here and not just the default.
    const controls = ['brightness-decrease', 'brightness-increase',
                      'contrast-decrease', 'contrast-increase', 'edges-toggle'];

    for (const fontSize of ['100%', '75%']) {
      // applyFontSize() scales the ROOT only; scaling body as well compounds and
      // measures a layout no user can produce.
      await page.evaluate((size) => { document.documentElement.style.fontSize = size; }, fontSize);

      for (const id of controls) {
        const box = await page.locator(`#${id}`).boundingBox();
        expect(box, `#${id} at ${fontSize} has no box`).not.toBeNull();
        // Firefox multiplies a px min-width by the app's own font step in
        // floating point, so a control that IS 44 px can measure
        // 43.99998474121094 - 1.5e-5 px under the floor, and only at 75%.
        // Round to the nearest hundredth of a pixel: no display can resolve
        // finer, and a control that is genuinely 43 px still rounds to 43
        // and still fails. Do not lower the floor instead - it caught real
        // 20x22 px buttons.
        expect.soft(toHundredthPx(box!.width), `#${id} width at ${fontSize}`).toBeGreaterThanOrEqual(44);
        expect.soft(toHundredthPx(box!.height), `#${id} height at ${fontSize}`).toBeGreaterThanOrEqual(44);
      }
    }
  });

  test('keeps the skip link fully off screen at every app font size', async ({ page }) => {
    await openApp(page);

    // The link was hidden by a hardcoded top: -40px, which cannot cover an
    // element whose height scales with the font size - it left 19 px of itself
    // sitting over the header at 200%. transform: translateY(-100%) is always
    // exactly one link-height, so this has to hold at every step of the scale.
    const link = page.locator('.skip-link');

    for (const fontSize of ['100%', '125%', '150%', '175%', '200%']) {
      await page.evaluate((size) => { document.documentElement.style.fontSize = size; }, fontSize);
      const box = await link.boundingBox();
      expect(box, `skip link at ${fontSize} has no box`).not.toBeNull();
      expect.soft(box!.y + box!.height, `skip link visible height at ${fontSize}`).toBeLessThanOrEqual(1);
    }

    // ...and it must still come fully on screen when focused, at the largest size.
    // Polled rather than read once: the reveal is a 0.3s transform transition, so
    // an immediate read catches the link mid-slide and not where it lands.
    await link.focus();
    await expect(link).toBeFocused();
    await expect.poll(
      async () => (await link.boundingBox())!.y,
      { message: 'skip link never slid fully on screen when focused' },
    ).toBeGreaterThanOrEqual(-1);
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
    // Switching plate type used to normalize the dial straight back to the recommendation
    await page.locator('input[name="plate_type"][value="negative"]').check();
    await expect(cells).toHaveValue('9');
    // ...but the recommendation is still surfaced in the note
    await expect(page.locator('#grid_columns_note')).toContainText('Recommended value: 13');
  });
});
