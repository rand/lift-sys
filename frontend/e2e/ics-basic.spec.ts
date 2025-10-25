/**
 * ICS Basic Layout E2E Tests
 *
 * Tests basic navigation and layout rendering for the Integrated Context Studio
 */

import { test, expect } from '@playwright/test';

test.describe('ICS Basic Layout', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app (authenticated via auth.setup.ts)
    await page.goto('/');
  });

  test('should navigate to ICS section', async ({ page }) => {
    // Click ICS navigation button
    const icsButton = page.getByRole('button', { name: /ICS.*New/i });
    await expect(icsButton).toBeVisible();
    await icsButton.click();

    // Verify ICS layout loads
    await expect(page.locator('.ics-editor-container')).toBeVisible({ timeout: 10000 });
  });

  test('should display all ICS panels', async ({ page }) => {
    // Navigate to ICS
    await page.getByRole('button', { name: /ICS.*New/i }).click();

    // Wait for ICS to load
    await page.waitForSelector('.ics-editor-container', { timeout: 10000 });

    // Check for main components
    // Note: Exact selectors depend on component implementation
    // These are best-effort based on the code we've seen

    // Editor should be visible
    const editor = page.locator('.ics-editor-container');
    await expect(editor).toBeVisible();

    // Toolbar should be visible
    const toolbar = page.locator('.ics-editor-toolbar');
    await expect(toolbar).toBeVisible();
  });

  test('should show character count in toolbar', async ({ page }) => {
    // Navigate to ICS
    await page.getByRole('button', { name: /ICS.*New/i }).click();

    // Wait for editor
    await page.waitForSelector('.ics-editor-container', { timeout: 10000 });

    // Check for character count (initially should be "0 characters")
    const toolbar = page.locator('.ics-editor-toolbar');
    await expect(toolbar).toContainText(/\d+ characters?/i);
  });
});
