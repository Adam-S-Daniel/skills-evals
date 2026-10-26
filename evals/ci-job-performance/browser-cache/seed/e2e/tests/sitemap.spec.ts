import { test, expect } from '@playwright/test';

test('sitemap lists the pricing page', async ({ request }) => {
  const response = await request.get('/sitemap.xml');
  expect(response.ok()).toBeTruthy();
  expect(await response.text()).toContain('/pricing/');
});
