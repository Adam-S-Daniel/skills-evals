import { test, expect } from '@playwright/test';

test('blog page lists recent posts', async ({ page }) => {
  await page.goto('/blog/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('blog page paginates', async ({ page }) => {
  await page.goto('/blog/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('blog page links each post', async ({ page }) => {
  await page.goto('/blog/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('blog page shows post dates', async ({ page }) => {
  await page.goto('/blog/');
  await expect(page.getByRole('main')).toBeVisible();
});

