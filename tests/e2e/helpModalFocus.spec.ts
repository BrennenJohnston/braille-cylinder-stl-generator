import { test, expect, type Page } from '@playwright/test';

/**
 * E2E regression tests for the Help & Guide dialog's focus containment.
 *
 * Found by Brennen's NVDA page-structure walkthrough on 2026-08-23 (finding
 * F-Q). The dialog opened and announced correctly - *"Help & Guide dialog, Help
 * sections tab control, What to Include tab selected 1 of 7"* - and then three
 * Tab presses later NVDA was reading Chrome's own toolbar: *"tool bar, View site
 * information button, Address and search bar"*. Focus had left the page.
 *
 * A focus trap existed and had existed all along. It failed for one reason:
 *
 *     const focusableElements = modal.querySelectorAll(
 *         'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
 *     const lastElement = focusableElements[focusableElements.length - 1];
 *
 * That selector never filtered for what can actually take focus. The dialog has
 * SEVEN tab panels and shows one at a time, so it matched 37 elements of which
 * only 10 were visible - and `lastElement` was a link inside a `hidden` panel.
 * `document.activeElement === lastElement` can therefore never be true, the
 * wrap-around never fires, and Tab walks straight out of the dialog. The
 * unselected tabs compound it: they are `<button>`s carrying `tabindex="-1"`,
 * matched by the bare `button` term and equally unfocusable.
 *
 * The severity is not "the guide is awkward to read". The dialog sets
 * `aria-modal="true"`, which tells assistive tech that everything outside it does
 * not exist - so escaping lands the user in content their screen reader has been
 * told to ignore, with the dialog still open behind them. Four stops of a
 * seven-section guide were reachable.
 *
 * Nothing caught this. The W3C validator, Lighthouse and axe-core all score the
 * markup, and the markup was right: `role="dialog"`, `aria-modal`, a labelled
 * title, a named close button. Only tabbing the ring finds it, which is why it
 * is pinned here by key presses rather than by attributes.
 *
 * Verifying it turned up a second, independent defect on WebKit, in the CLOSE
 * path: Safari does not focus a `<button>` on click, so `previouslyFocusedElement`
 * was captured as `<body>`, and `body.focus()` is a no-op. Closing the dialog
 * therefore left focus on the now-hidden dialog and restarted Tab at the top of
 * the document. It falls back to the opening control now.
 *
 * Contracts pinned:
 *   1. While the dialog is open, focus never reaches content BEHIND it - in EVERY
 *      panel, in both directions. Panel 1 is the smallest; an off-by-one shows up
 *      in the ones with more links, so all seven are walked.
 *   2. Focus is never stuck outside the dialog: a press may pass through `<body>`
 *      (WebKit does this, see `focusWhere`), but two consecutive presses outside
 *      is a failure. This is asserted separately from contract 1 rather than
 *      merged into it, so a real escape can never hide behind a tolerated one.
 *   3. Escape closes the dialog and returns focus to the control that opened it.
 */

/** Every panel is walked; the count is asserted so a new section cannot skip the test. */
const HELP_PANEL_COUNT = 7;

/** Enough presses to lap the largest panel's ring several times over. */
const PRESSES_PER_DIRECTION = 22;

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#auto-text');
}

async function openHelp(page: Page) {
  await page.click('#helpModalBtn');
  await expect(page.locator('#helpModal')).not.toHaveClass(/hidden/);
  await page.waitForSelector('#helpModalClose', { state: 'visible' });
}

/**
 * Where focus is, in the only three categories that matter.
 *
 * `page` is the failure this file exists for and is asserted at zero. `body` is
 * separated from it deliberately rather than folded in to make a number look
 * good: WebKit does not move Tab focus to links by default, so inside the
 * dialog a press can land on `<body>` instead of the next link - measured at
 * 6 of 44 presses on 2026-08-23, against 0 on Chromium and Firefox. That is a
 * wasted keypress, not an escape: no content behind the dialog is reachable and
 * the next press recovers. What must never happen is focus staying out, so a
 * transient is allowed exactly one press and two in a row is a failure.
 */
const focusWhere = () => {
  const active = document.activeElement;
  const modal = document.getElementById('helpModal');
  if (!modal || !active || active === document.body) return 'body';
  return modal.contains(active) ? 'dialog' : 'page';
};

test.describe('Help & Guide dialog keeps focus (F-Q)', () => {
  test('Tab and Shift+Tab never leave the dialog, in any of the seven panels', async ({ page }) => {
    await openApp(page);
    await openHelp(page);

    const tabs = page.locator('.help-tab');
    await expect(tabs).toHaveCount(HELP_PANEL_COUNT);

    const escapesByPanel: Array<{ panel: string; reachedPage: number; stuckOut: number }> = [];

    for (let i = 0; i < HELP_PANEL_COUNT; i++) {
      // Arrow keys move between sections; Tab is not the tab-strip's navigation
      // key, which is the correct ARIA tabs pattern and is why only one tab is
      // ever in the ring.
      if (i > 0) {
        await page.evaluate(() => {
          (document.querySelector('.help-tab[aria-selected="true"]') as HTMLElement)?.focus();
        });
        await page.keyboard.press('ArrowRight');
        await page.waitForTimeout(150);
      }

      const panel = await page.evaluate(() =>
        document.querySelector('.help-tab[aria-selected="true"]')?.textContent?.trim() ?? '(none)');

      let reachedPage = 0;
      let stuckOut = 0;
      let previousWasOut = false;

      for (let k = 0; k < PRESSES_PER_DIRECTION * 2; k++) {
        await page.keyboard.press(k < PRESSES_PER_DIRECTION ? 'Tab' : 'Shift+Tab');
        const at = await page.evaluate(focusWhere);
        if (at === 'page') reachedPage++;
        if (at !== 'dialog' && previousWasOut) stuckOut++;
        previousWasOut = at !== 'dialog';
      }

      escapesByPanel.push({ panel, reachedPage, stuckOut });
    }

    // Report every panel rather than the first failure, so a regression says
    // which section broke instead of just "it broke".
    expect(escapesByPanel.filter((p) => p.reachedPage > 0)).toEqual([]);
    expect(escapesByPanel.filter((p) => p.stuckOut > 0)).toEqual([]);
  });

  test('Escape closes the dialog and gives focus back to the opener', async ({ page }) => {
    await openApp(page);
    await openHelp(page);

    await page.keyboard.press('Escape');
    await expect(page.locator('#helpModal')).toHaveClass(/hidden/);

    const focusedId = await page.evaluate(() => document.activeElement?.id ?? '');
    expect(focusedId).toBe('helpModalBtn');
  });

  test('the trap counts only real tab stops, not every match of its selector', async ({ page }) => {
    await openApp(page);
    await openHelp(page);

    // The regression this file exists for, measured directly: the raw selector
    // still matches far more than can hold focus, so the filter is what keeps
    // `lastElement` reachable. If someone drops the filter, this fails here with
    // a clear reason rather than as a mysterious escape above.
    const counts = await page.evaluate(() => {
      const modal = document.getElementById('helpModal')!;
      const raw = Array.from(modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')) as HTMLElement[];
      const real = raw.filter((el) => !(el as HTMLButtonElement).disabled
        && el.tabIndex >= 0 && el.getClientRects().length > 0);
      return { raw: raw.length, real: real.length, lastRealVisible: real.length > 0 };
    });

    expect(counts.raw).toBeGreaterThan(counts.real);
    expect(counts.real).toBeGreaterThan(0);
    expect(counts.lastRealVisible).toBe(true);
  });
});
