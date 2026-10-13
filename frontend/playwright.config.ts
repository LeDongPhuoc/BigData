import { defineConfig } from "@playwright/test";

const reportPrefix = process.env.JRN_E2E_REPORT_PREFIX || "frontend";
if (!/^[a-z0-9-]{1,40}$/.test(reportPrefix)) {
  throw new Error(
    "JRN_E2E_REPORT_PREFIX must use 1-40 lowercase letters, digits or hyphens.",
  );
}

if (
  process.env.JRN_E2E !== "1" ||
  !process.env.JRN_E2E_PASSWORD ||
  !process.env.JRN_E2E_BASE
) {
  throw new Error(
    "Run .venv\\Scripts\\python.exe scripts/check_frontend.py from repository root. Real isolated ArangoDB is required.",
  );
}
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  expect: { timeout: 10000 },
  outputDir: "./test-results/browser",
  reporter: [
    ["list"],
    ["junit", { outputFile: `../docs/reports/${reportPrefix}-playwright.xml` }],
    ["json", { outputFile: `../docs/reports/${reportPrefix}-playwright.json` }],
  ],
  use: {
    baseURL: process.env.JRN_E2E_BASE,
    browserName: "chromium",
    channel: process.env.JRN_E2E_BROWSER || "chromium",
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "off",
    video: "off",
  },
});
