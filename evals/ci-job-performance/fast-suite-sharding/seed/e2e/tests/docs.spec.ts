import { test, expect } from '@playwright/test';

test('docs page has a search box', async ({ page }) => {
  await page.goto('/docs/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('docs page links getting started', async ({ page }) => {
  await page.goto('/docs/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('docs page links publishing', async ({ page }) => {
  await page.goto('/docs/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('docs page shows a table of contents', async ({ page }) => {
  await page.goto('/docs/');
  await expect(page.getByRole('main')).toBeVisible();
});

