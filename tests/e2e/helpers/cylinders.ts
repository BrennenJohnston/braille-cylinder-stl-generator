/**
 * "Cylinders to Generate" (Expert Mode, first submenu; 2026-09-20 programme,
 * sub-plan E, decision D-8). Since 2026-09-21 Generate builds BOTH cylinders by
 * default and Download saves the combined pair file; choosing one cylinder is
 * an Expert Mode choice.
 *
 * Most specs exercise one cylinder at a time - they count /geometry_spec
 * requests, wait for the single-plate ready sentence, or compare a single
 * export against a fixture - so their openApp() helpers choose Cylinder A (the
 * pre-2026-09-21 default) through this function, and the tests that prove the
 * pair choose 'both' explicitly.
 *
 * The radio sits inside the collapsed Expert panel, where Playwright's check()
 * refuses a hidden control, so it is checked at the source with the same change
 * event a click dispatches - persistence, the cell dial and the generate state
 * all follow it exactly as they follow a user's click (the app's own
 * selectPlateType() does the same).
 */
import type { Page } from '@playwright/test';

export type CylinderSelection = 'both' | 'positive' | 'negative';

export async function selectCylinders(page: Page, value: CylinderSelection) {
  await page.evaluate((selection) => {
    const radio = document.querySelector<HTMLInputElement>(
      `input[name="plate_selection"][value="${selection}"]`,
    );
    if (!radio) throw new Error(`Cylinders to Generate radio "${selection}" not found`);
    if (radio.checked) return;
    radio.checked = true;
    radio.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

/** The value the "Cylinders to Generate" group currently holds. */
export async function selectedCylinders(page: Page): Promise<CylinderSelection | null> {
  return page.evaluate(
    () =>
      (document.querySelector<HTMLInputElement>('input[name="plate_selection"]:checked')?.value ??
        null) as CylinderSelection | null,
  );
}
