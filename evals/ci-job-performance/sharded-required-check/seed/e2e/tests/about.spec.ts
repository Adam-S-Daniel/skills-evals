import { test, expect } from '@playwright/test';

test('about page names the team', async ({ page }) => {
  await page.goto('/about/');
  await expect(page.getByRole('heading', { name: 'About us' })).toBeVisible();
});

test('footer links back home', async ({ page }) => {
  await page.goto('/about/');
  await page.getByRole('contentinfo').getByRole('link', { name: 'Home' }).click();
  await expect(page).toHaveURL(/\/$/);
});
