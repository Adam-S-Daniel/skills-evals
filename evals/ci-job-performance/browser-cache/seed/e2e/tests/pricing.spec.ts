import { test, expect } from '@playwright/test';

test('pricing page lists three plans', async ({ page }) => {
  await page.goto('/pricing/');
  await expect(page.getByRole('article')).toHaveCount(3);
});
