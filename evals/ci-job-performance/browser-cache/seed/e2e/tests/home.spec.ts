import { test, expect } from '@playwright/test';

test('home page shows the main heading', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Example');
});

test('home page links to pricing', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Pricing' }).click();
  await expect(page).toHaveURL(/\/pricing\/$/);
});
