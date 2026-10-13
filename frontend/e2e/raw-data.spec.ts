import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("raw VietJobs đầy đủ: chất lượng, lọc toàn file, chi tiết, seed và Top-K", async ({
  page,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill("demo-a@example.test");
  await page
    .getByLabel("Mật khẩu", { exact: true })
    .fill(process.env.JRN_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/explore/data");
  await expect(
    page.getByRole("heading", {
      name: "Khảo sát dữ liệu gốc VietJobs",
      exact: true,
    }),
  ).toBeVisible({ timeout: 90000 });
  await expect(
    page.getByText("Đang kiểm tra CSV VietJobs gốc.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "47.707 bản ghi phù hợp", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".raw-results .raw-job")).toHaveCount(12);
  await page
    .getByRole("button", { name: "Trang raw sau", exact: true })
    .click();
  await expect(page).toHaveURL(/offset=12/);
  await expect(page.locator(".raw-results .raw-job")).toHaveCount(12);
  await page
    .getByRole("button", { name: "Xóa bộ lọc raw", exact: true })
    .click();
  await page.getByLabel("Ẩn dòng trùng hoàn toàn", { exact: true }).uncheck();
  await expect(
    page.getByRole("heading", { name: "48.092 bản ghi phù hợp", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Ẩn dòng trùng hoàn toàn", { exact: true }).check();
  await page
    .getByLabel("Nhóm nghề raw", { exact: true })
    .selectOption("công_nghệ_thông_tin_kỹ_thuật_số");
  await page
    .getByLabel("Quốc gia raw", { exact: true })
    .selectOption("Việt Nam");
  await page
    .getByLabel("Loại hợp đồng raw", { exact: true })
    .selectOption("Thực tập");
  await page
    .getByLabel("Kinh nghiệm tối đa đáp ứng", { exact: true })
    .selectOption("0.5");
  await expect(page.locator(".raw-title-link").first()).toBeVisible();
  await page.locator(".raw-title-link").first().click();
  await expect(
    page.getByRole("heading", { name: "Mô tả theo nguồn", exact: true }),
  ).toBeVisible();
  await page.locator(".raw-original summary").click();
  await expect(page.locator(".raw-original dt")).toHaveCount(18);
  await expect(
    page.getByText("Nguồn không có công ty/URL/ngày đăng", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Về khảo sát CSV", exact: true })
    .click();
  await expect(page.getByLabel("Loại hợp đồng raw")).toHaveValue("Thực tập");
  await page
    .getByRole("button", { name: "Xóa bộ lọc raw", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "47.707 bản ghi phù hợp", exact: true }),
  ).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact || ""),
    ),
  ).toEqual([]);
  const prefix = process.env.JRN_E2E_REPORT_PREFIX!;
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `../docs/reports/${prefix}-raw-desktop.png`,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect
    .poll(() =>
      page
        .locator(".sidebar")
        .evaluate((element) => element.getBoundingClientRect().right),
    )
    .toBeLessThanOrEqual(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: `../docs/reports/${prefix}-raw-mobile.png`,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/explore/recommendations");
  await page.getByRole("checkbox", { name: "python", exact: true }).check();
  await page.getByLabel("Số gợi ý tối đa (Top-K)").selectOption("5");
  await page
    .getByRole("button", { name: "Xem gợi ý phù hợp", exact: true })
    .click();
  await expect(page.locator(".explore-rank")).toHaveCount(5);
  expect(errors).toEqual([]);
});
