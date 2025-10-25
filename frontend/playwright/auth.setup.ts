/**
 * Playwright Authentication Setup
 *
 * This setup script runs before all tests to establish an authenticated session.
 * It leverages the app's demo mode to create a realistic authenticated state
 * without requiring actual OAuth flows.
 */

import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth', 'user.json');

setup('authenticate', async ({ page }) => {
  // Navigate to the app
  await page.goto('/');

  // Wait for the sign-in page to load
  await page.waitForLoadState('networkidle');

  // The app should show the sign-in page
  await expect(page.getByText(/Welcome to lift-sys/i)).toBeVisible({ timeout: 10000 });

  // Set up demo mode authentication by injecting the demo user into localStorage
  // This simulates what happens when clicking "Continue with Google" in demo mode
  await page.evaluate(() => {
    const demoUser = {
      id: 'demo:e2e-test-user',
      provider: 'google',
      email: 'e2e-test@playwright.dev',
      name: 'E2E Test User',
      avatarUrl: null,
    };
    localStorage.setItem('demo_user', JSON.stringify(demoUser));
  });

  // Reload the page to trigger the auth state refresh
  await page.reload();

  // Wait for the app to recognize the authenticated state
  await page.waitForLoadState('networkidle');

  // Verify we're authenticated by checking for main app UI elements
  // (The sidebar with navigation should be visible)
  await expect(page.getByRole('button', { name: /Configuration/i })).toBeVisible({ timeout: 10000 });

  // Verify user info is displayed
  await expect(page.getByText(/Signed in as/i)).toBeVisible();

  // Save the authenticated state
  await page.context().storageState({ path: authFile });

  console.log('✅ Authentication setup complete');
  console.log('   User: E2E Test User (e2e-test@playwright.dev)');
  console.log('   Auth state saved to:', authFile);
});
