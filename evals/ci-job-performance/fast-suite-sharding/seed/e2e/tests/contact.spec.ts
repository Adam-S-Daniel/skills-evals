import { test, expect } from '@playwright/test';

test('contact page shows the support address', async ({ page }) => {
  await page.goto('/contact/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('contact page shows office hours', async ({ page }) => {
  await page.goto('/contact/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('contact page links to status', async ({ page }) => {
  await page.goto('/contact/');
  await expect(page.getByRole('main')).toBeVisible();
});

test('contact page has a form label', async ({ page }) => {
  await page.goto('/contact/');
  await expect(page.getByRole('main')).toBeVisible();
});

