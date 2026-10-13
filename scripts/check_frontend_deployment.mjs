// Read-only business smoke of the compiled frontend and its real same-origin proxy.
import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium, expect } = require('@playwright/test');
const origin = process.env.JRN_FRONTEND_URL || 'http://127.0.0.1:5173';
const reportDirectory = new URL('../docs/reports/', import.meta.url);
const reportPrefix = process.env.JRN_DEPLOYMENT_REPORT_PREFIX || 'frontend';
if (!/^[a-z0-9-]{1,40}$/.test(reportPrefix)) throw new Error('Invalid deployment report prefix');
const browser = await chromium.launch({ channel: process.env.JRN_E2E_BROWSER || 'chromium' });
try {
  const page = await browser.newPage({ baseURL: origin, viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const health = await page.request.get('/healthz');
  expect(health.status()).toBe(200);
  const response = await page.goto('/jobs/demo_backend/paths');
  expect(response.status()).toBe(200); // SPA deep link served by Nginx.
  expect(response.headers()['content-security-policy']).toContain("script-src 'self'");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true })).toBeVisible();
  const denied = await page.request.get('/api/v1/jobs?q=Backend');
  expect(denied.status()).toBe(401);
  expect((await denied.json()).error.code).toBe('unauthenticated');
  const explorePage = await page.goto('/explore/graph');
  expect(explorePage.status()).toBe(200);
  await expect(page).toHaveURL(/\/login$/);
  const exploreDenied = await page.request.get('/api/v1/exploration/catalog');
  expect(exploreDenied.status()).toBe(401);
  const rawPage = await page.goto('/explore/data');
  expect(rawPage.status()).toBe(200);
  await expect(page).toHaveURL(/\/login$/);
  const rawDenied = await page.request.get('/api/v1/exploration/raw/profile');
  expect(rawDenied.status()).toBe(401);
  const deniedLogin = page.waitForResponse(result => result.url().endsWith('/api/v1/auth/login'));
  await page.getByLabel('Email', { exact: true }).fill(`unregistered-${crypto.randomUUID()}@example.com`);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(crypto.randomUUID());
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click();
  expect((await deniedLogin).status()).toBe(401);
  await expect(page.getByRole('alert')).toContainText('Thông tin đăng nhập');
  await page.getByLabel('Email', { exact: true }).fill('');
  await page.getByLabel('Mật khẩu', { exact: true }).fill('');
  await expect(page.getByRole('link', { name: 'Tạo tài khoản', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
  await mkdir(reportDirectory, { recursive: true });
  await page.screenshot({ path: fileURLToPath(new URL(`${reportPrefix}-login-production.png`, reportDirectory)), fullPage: true });
  await writeFile(new URL(`${reportPrefix}-deployment.json`, reportDirectory), JSON.stringify({
    origin, compiled_assets: true, nginx_spa_deep_link: 200, same_origin_protected_api: 401,
    invalid_login_real_backend: 401, exploration_deep_link: 200, exploration_protected_api: 401,
    raw_deep_link: 200, raw_protected_api: 401,
    csp: true, uncaught_browser_errors: errors,
    checked_at: new Date().toISOString(),
  }, null, 2) + '\n');
  console.log('Compiled frontend / SPA routing / CSP / real API proxy / auth error: passed');
} finally { await browser.close(); }
