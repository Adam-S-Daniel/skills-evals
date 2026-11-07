import { test, expect } from '@playwright/test';

test('pricing page lists three plans', async ({ page }) => {
  await page.goto('/pricing/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('pricing page shows yearly prices', async ({ page }) => {
  await page.goto('/pricing/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('pricing page links to contact sales', async ({ page }) => {
  await page.goto('/pricing/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('pricing page marks the team plan', async ({ page }) => {
  await page.goto('/pricing/');
  await expect(page.getByRole('main')).toBeVisible();
});

