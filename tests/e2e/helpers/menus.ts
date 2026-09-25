/**
 * Card Thickness and Row Indicator Style live in Expert Mode since 2026-09-24
 * (programme decision D-5): submenus 2 and 3, collapsed by default. Playwright's
 * check() refuses a hidden radio, so these set the control at the source and
 * dispatch the change event a click would - the pattern selectCylinders uses -
 * and every listener (persistence, the preset system, the cell dial, the
 * tactile dials, the fit warnings) follows exactly as it follows a click.
 */
import type { Page } from '@playwright/test';

export type ThicknessPreset = '0.4' | '0.3' | 'custom';
export type IndicatorMode = 'visual' | 'tactile';

async function checkAtSource(page: Page, selector: string, label: string) {
  await page.evaluate(
    ([sel, name]) => {
      const radio = document.querySelector<HTMLInputElement>(sel);
      if (!radio) throw new Error(`${name} radio not found: ${sel}`);
      if (radio.disabled) throw new Error(`${name} radio is disabled: ${sel}`);
      if (radio.checked) return;
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
    },
    [selector, label],
  );
}

export async function selectThicknessPreset(page: Page, value: ThicknessPreset) {
  await checkAtSource(page, `input[name="card_thickness_preset"][value="${value}"]`, 'Card Thickness');
}

export async function selectIndicatorMode(page: Page, value: IndicatorMode) {
  await checkAtSource(page, `input[name="indicator_mode"][value="${value}"]`, 'Row Indicator Style');
}

/**
 * Open Expert Mode and the Row Indicator Style panel, so the notes and the
 * two warning boxes inside it can be asserted visible.
 */
export async function revealRowIndicatorPanel(page: Page) {
  await page.evaluate(() => {
    const expert = document.getElementById('expert-settings');
    if (expert) expert.style.display = 'block';
    const panel = document.getElementById('expert-panel-tactile');
    if (panel) {
      panel.style.display = 'block';
      panel.hidden = false;
    }
    const toggle = document.querySelector<HTMLButtonElement>('button[aria-controls="expert-panel-tactile"]');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
  });
}
