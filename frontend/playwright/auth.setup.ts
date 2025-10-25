/**
 * Playwright Authentication Setup
 *
 * This setup script runs before all tests to establish an authenticated session.
 * It leverages the app's demo mode to create a realistic authenticated state
 * without requiring actual OAuth flows.
 */

import { test as setup, expect } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const authFile = join(__dirname, '.auth', 'user.json');

setup('authenticate', async ({ page }) => {
  // Navigate to the app
  await page.goto('/');

  // Wait for the sign-in page to load
  await page.waitForLoadState('networkidle');

  // The app should show the sign-in page
  await expect(page.getByText(/Welcome to lift-sys/i)).toBeVisible({ timeout: 10000 });

  // Click "Continue with Google" button to trigger demo mode authentication
  // This is the most realistic approach - actually clicking the button like a user would
  const googleButton = page.getByRole('button', { name: /Continue with Google/i });
  await expect(googleButton).toBeVisible();
  await googleButton.click();

  // Wait for authentication to complete and app to load
  await page.waitForLoadState('networkidle');

  // Verify we're authenticated by checking for main app UI elements
  // (The sidebar with navigation should be visible)
  // Use nav#navigation to avoid ambiguity with "Save Configuration" button in content
  await expect(page.locator('nav#navigation').getByRole('button', { name: /Configuration/i })).toBeVisible({ timeout: 10000 });

  // Verify user info is displayed
  await expect(page.getByText(/Signed in as/i)).toBeVisible();

  // Save the authenticated state (includes localStorage with demo_user)
  await page.context().storageState({ path: authFile });

  console.log('✅ Authentication setup complete');
  console.log('   Method: Clicked "Continue with Google" (demo mode)');
  console.log('   Auth state saved to:', authFile);
});
