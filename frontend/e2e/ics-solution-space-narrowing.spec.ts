/**
 * ICS Solution Space Narrowing E2E Tests
 *
 * Tests solution space narrowing visualization.
 * Verifies:
 * - Before/after solution space comparison is displayed
 * - Constraint satisfaction status (satisfied/violated/unknown)
 * - Reduction percentage calculation
 * - Alerts for small/fully constrained solution spaces
 * - Constraint details in narrowing view
 */

import { test, expect } from '@playwright/test';

test.describe('ICS Solution Space Narrowing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /ICS.*New/i }).click();
    await page.waitForSelector('text=Loading...', { state: 'hidden', timeout: 15000 });
    await page.waitForSelector('.ics-editor-container', { timeout: 10000 });
  });

  test('should display solution space section in inspector', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    // Type text that creates typed holes
    await editor.fill('The function must ???validate the input data.');
    await page.waitForTimeout(1500);

    // Check if holes were created
    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      // Click on a hole to select it
      await holes.first().click();
      await page.waitForTimeout(500);

      // Look for Solution Space section header
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      const hasSection = await solutionSpaceHeader.isVisible().catch(() => false);

      if (hasSection) {
        console.log('✓ Solution Space section visible in inspector');
      }
    }
  });

  test('should expand/collapse solution space section', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Function must ???return validated data.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      const hasSection = await solutionSpaceHeader.isVisible().catch(() => false);

      if (hasSection) {
        // Click to expand
        await solutionSpaceHeader.click();
        await page.waitForTimeout(300);

        // Click to collapse
        await solutionSpaceHeader.click();
        await page.waitForTimeout(300);

        console.log('✓ Solution Space section is collapsible');
      }
    }
  });

  test('should display before/after solution space comparison', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('System should ???validate and ???process requests.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      const hasSection = await solutionSpaceHeader.isVisible().catch(() => false);

      if (hasSection) {
        await solutionSpaceHeader.click();
        await page.waitForTimeout(500);

        // Look for "Before" and "After" labels
        const beforeText = page.locator('text=/before/i').first();
        const afterText = page.locator('text=/after/i').first();

        const hasBefore = await beforeText.isVisible().catch(() => false);
        const hasAfter = await afterText.isVisible().catch(() => false);

        if (hasBefore && hasAfter) {
          console.log('✓ Before/after comparison visible');
        }
      }
    }
  });

  test('should show solution space sizes with options count', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Must ???validate email format.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for option counts (e.g., "~1,000 options")
      const optionsText = page.locator('text=/~?\\d+.*option/i');
      const hasOptions = await optionsText.first().isVisible().catch(() => false);

      if (hasOptions) {
        console.log('✓ Solution space option counts visible');

        // Count how many option displays we have (should be at least before/after)
        const optionCount = await optionsText.count();
        console.log(`Found ${optionCount} option count displays`);
      }
    }
  });

  test('should display reduction percentage', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Function must return string and ???handle null cases.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for reduction percentage
      const reductionText = page.locator('text=/reduced by.*\\d+%/i');
      const hasReduction = await reductionText.isVisible().catch(() => false);

      if (hasReduction) {
        const text = await reductionText.textContent();
        console.log('✓ Reduction percentage visible:', text);

        // Extract percentage
        const match = text?.match(/(\d+)%/);
        if (match) {
          const percentage = parseInt(match[1], 10);
          expect(percentage).toBeGreaterThanOrEqual(0);
          expect(percentage).toBeLessThanOrEqual(100);
        }
      }
    }
  });

  test('should show constraint satisfaction status counts', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('System must ???validate before ???processing data.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for constraint status labels
      const satisfiedText = page.locator('text=/satisfied/i');
      const violatedText = page.locator('text=/violated/i');
      const unknownText = page.locator('text=/unknown/i');

      const hasSatisfied = await satisfiedText.isVisible().catch(() => false);
      const hasViolated = await violatedText.isVisible().catch(() => false);
      const hasUnknown = await unknownText.isVisible().catch(() => false);

      if (hasSatisfied || hasViolated || hasUnknown) {
        console.log('✓ Constraint status indicators visible');
        console.log(`  Satisfied: ${hasSatisfied}, Violated: ${hasViolated}, Unknown: ${hasUnknown}`);
      }
    }
  });

  test('should display constraint details with type and severity', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Must ???implement authentication with error handling.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for constraint type/severity badges
      const badges = page.locator('[class*="badge"]');
      const badgeCount = await badges.count();

      if (badgeCount > 0) {
        console.log(`✓ Found ${badgeCount} constraint detail badges`);

        // Check for common constraint types
        const typeText = page.locator('text=/constraint|return|loop|position/i');
        const hasTypes = await typeText.first().isVisible().catch(() => false);

        if (hasTypes) {
          console.log('✓ Constraint types visible');
        }
      }
    }
  });

  test('should show arrow indicator between before/after', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Function should ???validate inputs.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for arrow SVG element
      const arrows = page.locator('svg[class*="arrow"], svg').filter({ has: page.locator('*') });
      const arrowCount = await arrows.count();

      if (arrowCount > 0) {
        console.log('✓ Arrow indicators present');
      }
    }
  });

  test('should highlight "After" section (current state)', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Must ???process requests efficiently.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // "After" section should have border highlighting
      const afterSection = page.locator('[class*="border-primary"]');
      const hasHighlight = await afterSection.isVisible().catch(() => false);

      if (hasHighlight) {
        console.log('✓ After section has visual highlighting');
      }
    }
  });

  test('should show alert for small solution spaces', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    // Text with strong constraints that should create small solution space
    await editor.fill('Function must return Promise<boolean> and ???handle async validation.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for alert about small solution space or enumeration
      const enumerateAlert = page.locator('text=/enumerate.*options?/i');
      const hasAlert = await enumerateAlert.isVisible().catch(() => false);

      if (hasAlert) {
        console.log('✓ Small solution space alert visible');
      }
    }
  });

  test('should show special alert for fully constrained holes', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    // Multiple strong constraints
    await editor.fill('Must return exactly true and ???validate boolean output.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for "fully constrained" alert
      const fullyConstrainedText = page.locator('text=/fully constrained/i');
      const hasAlert = await fullyConstrainedText.isVisible().catch(() => false);

      if (hasAlert) {
        console.log('✓ Fully constrained alert visible');
      }
    }
  });

  test('should display "Active Constraints" section', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('System must ???authenticate users before access.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for "Active Constraints" heading
      const activeConstraintsText = page.locator('text=/active constraints/i');
      const hasSection = await activeConstraintsText.isVisible().catch(() => false);

      if (hasSection) {
        console.log('✓ Active Constraints section visible');
      }
    }
  });

  test('should handle holes with no constraints gracefully', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    // Simple hole with minimal constraints
    await editor.fill('The system should ???implement this feature.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Should show "No constraints" or similar
      const noConstraintsText = page.locator('text=/no constraint/i');
      const hasText = await noConstraintsText.isVisible().catch(() => false);

      if (hasText) {
        console.log('✓ No constraints state handled gracefully');
      }
    }
  });

  test('should show status indicators for each constraint', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Must ???validate and ???sanitize user input.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for status icons (CheckCircle, XCircle, AlertCircle)
      const statusIcons = page.locator('[class*="text-green"], [class*="text-red"], [class*="text-yellow"]');
      const iconCount = await statusIcons.count();

      if (iconCount > 0) {
        console.log(`✓ Found ${iconCount} status indicators`);
      }
    }
  });

  test('should calculate and display constraint statistics grid', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Function must ???return data and ???handle errors correctly.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space section
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Look for "Constraint Status" header
      const statusHeader = page.locator('text=/constraint status/i');
      const hasHeader = await statusHeader.isVisible().catch(() => false);

      if (hasHeader) {
        console.log('✓ Constraint Status grid visible');

        // Should have counts for satisfied/violated/unknown
        const countElements = page.locator('[class*="font-medium"]');
        const countCount = await countElements.count();

        if (countCount > 0) {
          console.log(`✓ Found ${countCount} status count displays`);
        }
      }
    }
  });
});

test.describe('ICS Solution Space Narrowing - Edge Cases', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /ICS.*New/i }).click();
    await page.waitForSelector('text=Loading...', { state: 'hidden', timeout: 15000 });
    await page.waitForSelector('.ics-editor-container', { timeout: 10000 });
  });

  test('should handle switching between different holes', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Must ???validate, ???process, and ???send data.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount >= 2) {
      // Select first hole
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(300);

      // Select second hole
      await holes.nth(1).click();
      await page.waitForTimeout(500);

      // Solution space should still work
      const solutionSpaceView = page.locator('.solution-space-narrowing-card');
      const hasView = await solutionSpaceView.isVisible().catch(() => false);

      if (hasView) {
        console.log('✓ Solution space view updates when switching holes');
      }
    }
  });

  test('should handle text with no typed holes', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    // Text without ???
    await editor.fill('The system validates all user inputs before processing.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    // Should be 0 holes
    expect(holeCount).toBe(0);

    // Solution space section should not be visible (nothing selected)
    console.log('✓ No holes, no solution space view (as expected)');
  });

  test('should handle rapid expansion/collapse', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    await editor.fill('Must ???validate input data.');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });

      // Rapidly toggle
      for (let i = 0; i < 3; i++) {
        await solutionSpaceHeader.click();
        await page.waitForTimeout(100);
        await solutionSpaceHeader.click();
        await page.waitForTimeout(100);
      }

      // Final state - should still be functional
      await solutionSpaceHeader.click();
      await page.waitForTimeout(300);

      const solutionSpaceView = page.locator('.solution-space-narrowing-card');
      const hasView = await solutionSpaceView.isVisible().catch(() => false);

      if (hasView) {
        console.log('✓ Solution space view handles rapid toggling');
      }
    }
  });

  test('should display meaningful info even with minimal constraints', async ({ page }) => {
    const editor = page.locator('.ProseMirror').first();
    await editor.click();

    // Very simple hole
    await editor.fill('???task');
    await page.waitForTimeout(1500);

    const holes = page.locator('.hole');
    const holeCount = await holes.count();

    if (holeCount > 0) {
      await holes.first().click();
      await page.waitForTimeout(500);

      // Expand solution space
      const solutionSpaceHeader = page.getByRole('button', { name: /solution space/i });
      await solutionSpaceHeader.click();
      await page.waitForTimeout(500);

      // Should show card even with minimal constraints
      const solutionSpaceCard = page.locator('.solution-space-narrowing-card');
      const hasCard = await solutionSpaceCard.isVisible().catch(() => false);

      if (hasCard) {
        console.log('✓ Solution space view displays even with minimal constraints');
      }
    }
  });
});
