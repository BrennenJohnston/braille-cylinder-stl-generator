import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E tests.
 * 
 * SAFETY-CRITICAL: These tests guard against silent truncation bugs (S0 severity).
 * The silent truncation E2E test (tests/e2e/silentTruncation.spec.ts) MUST NOT
 * be skipped or quarantined without explicit approval.
 */
export default defineConfig({
  testDir: './tests/e2e',
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if test.only is accidentally left in
  forbidOnly: !!process.env.CI,
  
  // Retry failed tests on CI
  retries: process.env.CI ? 2 : 0,
  
  // Use 1 worker on CI for consistent results
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter configuration
  reporter: process.env.CI ? 'github' : 'html',
  
  // Shared settings for all projects
  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:5001',
    
    // Collect trace on failure for debugging
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
  },

  // Configure projects for different browsers.
  // Firefox and WebKit are first-class targets per the project's stated browser
  // minimums (Firefox 114+, Safari 15+). Keeping them in CI prevents regressions
  // on those engines from slipping through Chromium-only runs.
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  // Web server configuration
  // Starts the Flask backend automatically before tests
  webServer: {
    command: 'python backend.py',
    port: 5001,
    // NEVER reuse. With reuse on, any server already holding this port - a
    // leftover backend.py from another checkout, worktree, or an interrupted
    // run - is silently adopted, and the whole local suite then tests THAT
    // tree's code while your files look correct. Reproduced 2026-08-21: a
    // pre-fix server on 5001 reproduced tactileIndicator.spec.ts:123's
    // "Expected: 10, Received: 5" against a working tree that already had the
    // fix. CI never saw it because CI set this to false. A busy port must be a
    // loud error, not a silent substitution.
    reuseExistingServer: false,
    timeout: 120000, // 2 minutes for server startup
    env: {
      PORT: '5001',
      FLASK_ENV: 'development',
    },
  },
  
  // Test timeout
  timeout: 60000, // 1 minute per test
  
  // Expect timeout for assertions
  expect: {
    timeout: 10000, // 10 seconds for assertions
  },
});
