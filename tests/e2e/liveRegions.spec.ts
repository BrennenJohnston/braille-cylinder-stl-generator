/**
 * E2E regression tests for the shared announcement channel, `#a11y-status`.
 *
 * This defect class has now recurred five times (Phases 05c-05f, then the three
 * front-of-card warnings on 2026-08-21) and no test guarded any of it. Both
 * halves of it are invisible to Lighthouse and axe-core, which score the markup
 * and never the runtime sequence - all three scored 100/100 while broken.
 *
 * The two contracts pinned here:
 *
 *  1. **No warning box may carry its own live region.** A box that is
 *     `display:none` between messages is inserted into the accessibility tree
 *     already holding its text, and an insertion is not a change, so a
 *     `role="status"` on it can never fire - while still letting some assistive
 *     tech speak the message a second time. Every warning announces through the
 *     one always-present `#a11y-status` region instead, so the number of
 *     `role=status` nodes exposed to the tree must stay constant no matter which
 *     warnings are up.
 *
 *  2. **One announcement per episode, not one per keystroke.** `announceStatus()`
 *     assigns `textContent` unconditionally, and assigning an *identical* string
 *     still replaces the text node - it does NOT deduplicate. Callers that
 *     recompute per keystroke must gate themselves, or they talk over the user
 *     while they are still typing. `#caps-warning` is the sharp case: its text
 *     never changes and it has no debounce, and it announced 11 times over 11
 *     keystrokes before its gate was added.
 *
 * Each box must also announce its OWN visible text (so what is heard matches
 * what is shown) and release the channel when its condition clears.
 *
 * @see docs/specifications/UI_INTERFACE_CORE_SPECIFICATIONS.md section 4.10
 * @see docs/specifications/INTERPOINT_DOUBLE_SIDED_SPECIFICATIONS.md section 7.6
 * @see docs/development/NVDA_LIVE_WARNINGS_WALKTHROUGH.md
 */

import { test, expect, type Page } from '@playwright/test';

/**
 * The one region that is allowed to announce, plus the six permanently-present
 * status nodes that ship in the markup. Nine sources share `#a11y-status`; none
 * of them adds a node of its own, so this number must not move. 6 became 7 on
 * 2026-08-31: the Back of Card braille field gained its own sr-only announcer
 * (`#back-braille-unicode-live`), the exact mirror of the front field's - a
 * deliberate field announcer, not a warning box growing a region.
 *
 * Read it with `settledStatusNodes()`, never a bare count: `applyTheme()` and
 * `applyFontSize()` each append a THROWAWAY `role=status` div and remove it a
 * second later, and both run at init - so for the first second after load the
 * page legitimately holds 9. Firefox reaches an immediate assertion inside that
 * window and Chromium usually does not, which is exactly the kind of difference
 * that makes a suite flaky rather than useful.
 */
const EXPOSED_STATUS_NODES = 7;

/** The three boxes this file exists for. */
const WARNING_BOXES = ['auto-overflow-warning', 'cylinder-overflow-warning', 'caps-warning'];

/** 16 cells of an uncontracted run against the default 13-cell row. */
const OVER_LONG = 'qqqqqqqqqqqqqqqq';

async function openApp(page: Page) {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('#auto-text');
}

/** Reveal Expert Mode and one submenu (setup, not the feature under test). */
async function revealExpertPanel(page: Page, panelId: string) {
  await page.evaluate((id) => {
    const expert = document.getElementById('expert-settings');
    if (expert) expert.style.display = 'block';
    const panel = document.getElementById(id);
    if (panel) { panel.style.display = 'block'; panel.hidden = false; }
  }, panelId);
  await page.waitForSelector(`#${panelId}`, { state: 'visible' });
}

/**
 * Manual mode, with the Dimensions submenu open - `#cylinder-overflow-warning`
 * lives inside it, so it cannot be "visible" until that panel is.
 */
async function goManual(page: Page) {
  await page.locator('input[name="placement_mode"][value="manual"]').check();
  await expect(page.locator('#line1')).toBeVisible();
  await revealExpertPanel(page, 'expert-panel-dimensions');
}

/** Nodes the accessibility tree actually exposes as `role=status` right now. */
function exposedStatusNodes(page: Page): Promise<number> {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('[role="status"]')).filter((el) => {
      const style = getComputedStyle(el as HTMLElement);
      if (style.display === 'none' || style.visibility === 'hidden') return false;
      if ((el as HTMLElement).hidden) return false;
      return !el.closest('[hidden]');
    }).length,
  );
}

/** Record every value `#a11y-status` takes from here on. */
async function recordAnnouncements(page: Page) {
  await page.evaluate(() => {
    const store = (window as unknown as { __announcements: string[] });
    store.__announcements = [];
    const region = document.getElementById('a11y-status');
    if (!region) return;
    new MutationObserver(() => {
      const text = (region.textContent || '').trim();
      if (text) store.__announcements.push(text);
    }).observe(region, { childList: true, characterData: true, subtree: true });
  });
}

function announcements(page: Page): Promise<string[]> {
  return page.evaluate(() => (window as unknown as { __announcements: string[] }).__announcements);
}

/** The box's own visible text, whitespace-collapsed the way the mirror sends it. */
async function visibleText(page: Page, id: string): Promise<string> {
  return ((await page.locator(`#${id}`).textContent()) || '').replace(/\s+/g, ' ').trim();
}

/**
 * Re-trigger the debounced check until liblouis is warm and the warning lands.
 * The translation calls fail silently while the worker starts (reliably slow on
 * Firefox), so this retries rather than assuming a warm-up time - the same
 * pattern autoWrapCapacity.spec.ts and liveWarnings.spec.ts already use.
 */
async function waitForWarning(page: Page, warningId: string, inputId: string) {
  const warning = page.locator(`#${warningId}`);
  for (let attempt = 0; attempt < 25; attempt++) {
    await page.locator(`#${inputId}`).dispatchEvent('input');
    try {
      await expect(warning).toBeVisible({ timeout: 3000 });
      return;
    } catch {
      // Worker not ready yet; try again.
    }
  }
  throw new Error(`#${warningId} never appeared`);
}

test.describe('Live region announcements', () => {
  // Same rationale as liveWarnings.spec.ts: this page is a large inline script
  // plus vendored workers, and Firefox parses it noticeably more slowly.
  test.describe.configure({ timeout: 120_000 });

  test('the warning boxes carry no live region of their own', async ({ page }) => {
    await openApp(page);

    // The structural half of the contract, and the one that regresses: someone
    // "fixes" a silent warning by putting role="status" back on the box, which
    // cannot fire from a hidden box and lets some assistive tech speak the
    // message twice once the mirror is also announcing it.
    for (const id of WARNING_BOXES) {
      // Short timeout on purpose: these attributes are static markup, so there is
      // nothing to wait for, and the default 10s x 6 assertions turns a failure
      // into a minute of retrying something that will never change.
      const box = page.locator(`#${id}`);
      await expect(box).toHaveCount(1);
      await expect.soft(box, `#${id} must not carry role`)
        .not.toHaveAttribute('role', /.*/, { timeout: 2000 });
      await expect.soft(box, `#${id} must not carry aria-live`)
        .not.toHaveAttribute('aria-live', /.*/, { timeout: 2000 });
    }
  });

  test('showing a warning does not add a live region to the tree', async ({ page }) => {
    await openApp(page);
    // Polled, not read once: the init-time throwaway announcers take a second to
    // clear (see EXPOSED_STATUS_NODES).
    await expect.poll(() => exposedStatusNodes(page), { message: 'baseline never settled' })
      .toBe(EXPOSED_STATUS_NODES);

    // Auto-placement overflow (front of card - the one users hit most).
    await page.locator('#auto-text').fill(OVER_LONG);
    await waitForWarning(page, 'auto-overflow-warning', 'auto-text');
    expect(await exposedStatusNodes(page)).toBe(EXPOSED_STATUS_NODES);

    // Manual-mode cylinder overflow.
    await goManual(page);
    await page.locator('#line1').fill(OVER_LONG);
    await waitForWarning(page, 'cylinder-overflow-warning', 'line1');
    expect(await exposedStatusNodes(page)).toBe(EXPOSED_STATUS_NODES);

    // The capitalization note.
    await revealExpertPanel(page, 'expert-panel-translation');
    await page.locator('#capitalize_disabled').check();
    await page.locator('#line1').fill('Hello World');
    await expect(page.locator('#caps-warning')).toBeVisible();
    expect(await exposedStatusNodes(page)).toBe(EXPOSED_STATUS_NODES);
  });

  test('auto-placement overflow announces its own text once, then releases the channel', async ({ page }) => {
    await openApp(page);
    // Warm liblouis before recording, so the count covers typing and not startup.
    await page.locator('#auto-text').fill(OVER_LONG);
    await waitForWarning(page, 'auto-overflow-warning', 'auto-text');
    await page.locator('#auto-text').fill('');
    await expect(page.locator('#auto-overflow-warning')).toBeHidden();

    await recordAnnouncements(page);
    await page.locator('#auto-text').fill(OVER_LONG);
    await expect(page.locator('#auto-overflow-warning')).toBeVisible();

    const heard = await announcements(page);
    expect(heard).toHaveLength(1);
    // What is heard is the box's own text, "Warning:" included.
    expect(heard[0]).toBe(await visibleText(page, 'auto-overflow-warning'));

    await page.locator('#auto-text').fill('hi');
    await expect(page.locator('#auto-overflow-warning')).toBeHidden();
    await expect(page.locator('#a11y-status')).toHaveText('');
  });

  test('cylinder overflow announces its own text once, then releases the channel', async ({ page }) => {
    await openApp(page);
    await goManual(page);
    await page.locator('#line1').fill(OVER_LONG);
    await waitForWarning(page, 'cylinder-overflow-warning', 'line1');
    await page.locator('#line1').fill('hi');
    await expect(page.locator('#cylinder-overflow-warning')).toBeHidden();

    await recordAnnouncements(page);
    await page.locator('#line1').fill(OVER_LONG);
    await expect(page.locator('#cylinder-overflow-warning')).toBeVisible();

    const heard = (await announcements(page)).filter((text) => text.includes('cells but'));
    expect(heard).toHaveLength(1);
    expect(heard[0]).toBe(await visibleText(page, 'cylinder-overflow-warning'));

    await page.locator('#line1').fill('hi');
    await expect(page.locator('#cylinder-overflow-warning')).toBeHidden();
    await expect(page.locator('#a11y-status')).toHaveText('');
  });

  test('the capitalization note is announced once, not once per keystroke', async ({ page }) => {
    await openApp(page);
    await goManual(page);
    await revealExpertPanel(page, 'expert-panel-translation');
    await page.locator('#capitalize_disabled').check();

    await recordAnnouncements(page);

    // One input event per character, exactly as typing produces. This box has no
    // debounce, so every one of these re-runs updateCapsWarning(); without its
    // hidden-to-shown gate that measured 11 announcements for these 11 keystrokes.
    const typed = 'Hello WORLD';
    for (let i = 1; i <= typed.length; i++) {
      await page.locator('#line1').fill(typed.slice(0, i));
    }
    await expect(page.locator('#caps-warning')).toBeVisible();

    const heard = (await announcements(page)).filter((text) => text.includes('Capital letters'));
    expect(heard).toHaveLength(1);
    expect(heard[0]).toBe(await visibleText(page, 'caps-warning'));

    // Re-enabling capitals clears the condition and releases the channel.
    await page.locator('#capitalize_enabled').check();
    await expect(page.locator('#caps-warning')).toBeHidden();
    await expect(page.locator('#a11y-status')).toHaveText('');
  });

  test('one warning taking the channel does not clear another from the screen', async ({ page }) => {
    await openApp(page);
    await goManual(page);
    await revealExpertPanel(page, 'expert-panel-translation');
    await page.locator('#capitalize_disabled').check();

    await page.locator('#line1').fill('Hello');
    await expect(page.locator('#caps-warning')).toBeVisible();

    // The overflow warning takes the announcement channel; the capital note is a
    // different condition and must stay on screen. announceStatus() is scoped by
    // source precisely so one box clearing cannot wipe another's message.
    await page.locator('#line1').fill(`Hello ${OVER_LONG}`);
    await waitForWarning(page, 'cylinder-overflow-warning', 'line1');
    await expect(page.locator('#caps-warning')).toBeVisible();

    await page.locator('#line1').fill('Hello');
    await expect(page.locator('#cylinder-overflow-warning')).toBeHidden();
    await expect(page.locator('#caps-warning')).toBeVisible();
  });
});
