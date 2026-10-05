import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:3000';

test.describe('MailNexa AI — Authentication', () => {
  test('select-portal shows 3 portal cards', async ({ page }) => {
    await page.goto(`${BASE}/select-portal`);
    const links = page.locator('a[href*="login?role="]');
    await expect(links).toHaveCount(3);
  });

  test('user login page loads correctly', async ({ page }) => {
    await page.goto(`${BASE}/login?role=user`);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('demo credentials button fills form', async ({ page }) => {
    await page.goto(`${BASE}/login?role=user`);
    await page.locator('button:has-text("Fill Demo")').click();
    await expect(page.locator('input[type="email"]')).toHaveValue('user@example.com');
  });

  test('back button returns to select-portal', async ({ page }) => {
    await page.goto(`${BASE}/login?role=user`);
    await page.locator('a:has-text("Back to Portal")').click();
    await expect(page).toHaveURL(/select-portal/);
  });

  test('wrong password shows error', async ({ page }) => {
    await page.goto(`${BASE}/login?role=user`);
    await page.fill('input[type="email"]', 'wrong@example.com');
    await page.fill('input[type="password"]', 'badpassword');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=/Invalid|error|incorrect/i')).toBeVisible({ timeout: 10000 });
  });

  test('manager portal shows correct title', async ({ page }) => {
    await page.goto(`${BASE}/login?role=manager`);
    await expect(page.locator('text=Manager Portal Login')).toBeVisible();
  });

  test('admin portal shows correct title', async ({ page }) => {
    await page.goto(`${BASE}/login?role=admin`);
    await expect(page.locator('text=Admin Portal Login')).toBeVisible();
  });
});
