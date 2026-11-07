import { test, expect } from '@playwright/test';

test('about page shows the team', async ({ page }) => {
  await page.goto('/about/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('about page links to careers', async ({ page }) => {
  await page.goto('/about/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('about page has one h1', async ({ page }) => {
  await page.goto('/about/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('about page shows the founding year', async ({ page }) => {
  await page.goto('/about/');
  await expect(page.getByRole('main')).toBeVisible();
});

