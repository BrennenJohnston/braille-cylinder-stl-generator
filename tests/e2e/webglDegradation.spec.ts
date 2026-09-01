/**
 * WebGL Graceful Degradation E2E Test
 *
 * Regression gate for the bug where WebGL2 context-creation failure (Firefox
 * `AllowWebgl2:false`, RDP/VM sessions, blocklisted GPUs) would cascade into
 * an uncaught error that aborted the rest of page setup, leaving the form
 * non-interactive and breaking the STL download flow even though STL
 * generation is fully independent of WebGL.
 *
 * The fix routes WebGL failure into the existing `.webgl-error` block and
 * makes `loadSTL()` / `onWindowResize()` defensive against a null renderer.
 * This test locks that behavior in by stubbing
 * `HTMLCanvasElement.prototype.getContext` to refuse webgl/webgl2 contexts.
 *
 * Runs against chromium, firefox, and webkit (see playwright.config.ts).
 */

import { test, expect } from '@playwright/test';

test.describe('WebGL graceful degradation', () => {
  // WebKit on Windows (Playwright's bundled build) enforces the
  // Strict-Transport-Security + upgrade-insecure-requests headers that the
  // Flask dev server sends, so every module / worker / WASM request gets
  // upgraded to https://localhost:5001 and fails with "SSL connect error".
  // This blocks the page's <script type="module"> from ever executing — no
  // amount of code in init3D() or showWebGLUnavailableNotice() can run.
  // This is an environmental, pre-existing limitation of the WebKit-on-
  // Windows test harness and is unrelated to the WebGL degradation logic
  // (which is engine-agnostic). The corresponding manual verification on
  // Safari is left to a real Safari install, where HTTPS is the norm.
  test.skip(({ browserName }) => browserName === 'webkit',
    'WebKit-on-Windows + dev HTTP server + HSTS/upgrade-insecure-requests blocks all script loads; out of scope for this plan.');

  test.beforeEach(async ({ page }) => {
    // Stub WebGL context creation BEFORE any page script runs. We refuse
    // webgl/webgl2/experimental-webgl while leaving 2d and bitmaprenderer
    // alone (some code paths still need 2D canvas). Use a string literal
    // passed to addInitScript so the function body is shipped verbatim
    // to the browser (no TypeScript transpilation surprises across the
    // three test engines).
    await page.addInitScript(`
      (function () {
        var proto = HTMLCanvasElement.prototype;
        var orig = proto.getContext;
        proto.getContext = function (type) {
          if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') {
            return null;
          }
          return orig.apply(this, arguments);
        };
        if (typeof OffscreenCanvas !== 'undefined' && OffscreenCanvas.prototype && OffscreenCanvas.prototype.getContext) {
          var origOff = OffscreenCanvas.prototype.getContext;
          OffscreenCanvas.prototype.getContext = function (type) {
            if (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl') {
              return null;
            }
            return origOff.apply(this, arguments);
          };
        }
      })();
    `);
  });

  test('shows .webgl-error block when WebGL contexts are unavailable', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#language-table');

    // The viewer pane must surface the degraded-mode notice rather than
    // a 3D canvas or a broken/blank panel.
    const webglError = page.locator('.webgl-error');
    await expect(webglError).toBeVisible({ timeout: 15000 });
    await expect(webglError).toContainText(/WebGL/i);
  });

  test('form remains interactive when WebGL is blocked', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#language-table');

    // Auto-placement mode is the default; the auto-text textarea must be
    // editable even though the 3D preview is disabled.
    const autoText = page.locator('#auto-text');
    await expect(autoText).toBeVisible();
    await autoText.fill('Hi');
    await expect(autoText).toHaveValue('Hi');

    // Generate button must be enabled and clickable.
    const generateButton = page.locator('#action-btn');
    await expect(generateButton).toBeVisible();
    await expect(generateButton).toBeEnabled();
    await expect(generateButton).toHaveAttribute('data-state', 'generate');
  });

  test('STL generation completes and Download STL button appears with no WebGL', async ({ page }) => {
    // Collect uncaught errors and page errors. Console.warn from the new
    // try/catch is expected and should not fail the test.
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });

    await page.goto('/');
    await page.waitForSelector('#language-table');

    // Confirm degraded-mode is in effect before exercising the generate flow.
    await expect(page.locator('.webgl-error')).toBeVisible({ timeout: 10000 });

    // Fill a short text that fits in the default 4x11 grid.
    const autoText = page.locator('#auto-text');
    await autoText.fill('Hi');

    // Click Generate and wait for the download control to be offered.
    const generateButton = page.locator('#action-btn');
    const downloadButton = page.locator('#download-stl-btn');
    await generateButton.click();

    // The fix's core assertion: setToDownloadState() runs even though
    // init3D() bailed out, so the file is offered. Since 2026-08-18 that is a
    // SEPARATE #download-stl-btn rather than #action-btn renaming itself — a
    // control must never change identity under a screen-reader user's focus.
    await expect(downloadButton).toBeVisible({ timeout: 45000 });
    await expect(downloadButton).toHaveText(/Download STL/i);
    await expect(downloadButton).toBeEnabled();

    // And the generate button is still itself: same state, same name.
    await expect(generateButton).toHaveAttribute('data-state', 'generate');
    await expect(generateButton).toHaveAttribute('aria-label', 'Generate STL file from entered text');
    await expect(generateButton).toBeEnabled();

    // No uncaught page errors (the WebGL ctor failure must be swallowed by
    // the try/catch and surfaced only as a console.warn).
    expect(pageErrors, `Unexpected page errors: ${pageErrors.join('\n')}`).toEqual([]);

    // Filter out errors that are unrelated to this regression test. We allow
    // the known pre-existing CSP style-src warning and any STL-loader noise
    // that does not block the download flow.
    const unrelatedPatterns = [
      /Content[- ]Security[- ]Policy/i,
      /fonts\.googleapis\.com/i,
      /favicon/i,
    ];
    const blockingErrors = consoleErrors.filter(
      (msg) => !unrelatedPatterns.some((re) => re.test(msg)),
    );
    expect(
      blockingErrors,
      `Unexpected console errors: ${blockingErrors.join('\n')}`,
    ).toEqual([]);
  });

  test('Download STL click triggers a download with no WebGL', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#language-table');
    await expect(page.locator('.webgl-error')).toBeVisible({ timeout: 10000 });

    await page.locator('#auto-text').fill('Hi');
    const generateButton = page.locator('#action-btn');
    const downloadButton = page.locator('#download-stl-btn');
    await generateButton.click();

    // Wait for the separate download control to appear before clicking it.
    await expect(downloadButton).toBeVisible({ timeout: 30000 });

    // Clicking it triggers a real browser download — one file, one gesture.
    const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
    await downloadButton.click();
    const download = await downloadPromise;

    // The suggested filename should be an STL file.
    expect(download.suggestedFilename()).toMatch(/\.stl$/i);
  });
});
