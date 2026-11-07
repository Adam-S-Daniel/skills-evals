import { test, expect } from '@playwright/test';

test('contact form requires an email address', async ({ page }) => {
  await page.goto('/contact/');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('Enter an email address')).toBeVisible();
});

test('contact form accepts a message', async ({ page }) => {
  await page.goto('/contact/');
  await page.getByLabel('Email').fill('reader@example.com');
  await page.getByLabel('Message').fill('Hello');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('Thanks')).toBeVisible();
});
