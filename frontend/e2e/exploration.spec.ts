import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const reportPrefix = process.env.JRN_E2E_REPORT_PREFIX || "exploration";

test("khám phá seed: tìm việc, gợi ý gap, graph và analytics", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill("demo-a@example.test");
  await page
    .getByLabel("Mật khẩu", { exact: true })
    .fill(process.env.JRN_E2E_PASSWORD!);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page
    .getByRole("complementary", { name: "Điều hướng chính" })
    .getByRole("link", { name: "Khám phá việc làm", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Hiểu kỹ năng",
  );
  await expect(
    page.getByText("Đang dùng catalog hiện có, gồm dữ liệu seed."),
  ).toBeVisible();
  await page.getByRole("link", { name: "Tìm việc", exact: true }).click();
  await page.getByLabel("Từ khóa tìm kiếm").fill("Backend Developer (demo)");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "1 công việc", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Backend Developer (demo)", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Kỹ năng được khai báo", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("33% kỹ năng tương tự", { exact: false }).first(),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Gợi ý & kỹ năng", exact: true })
    .click();
  await page.getByRole("checkbox", { name: "python", exact: true }).check();
  await page
    .getByRole("button", { name: "Xem gợi ý phù hợp", exact: true })
    .click();
  await expect(page.getByText("Coverage: 100% trọng số").first()).toBeVisible();
  await expect(
    page
      .getByRole("heading", { name: "Kỹ năng chưa khai báo", exact: true })
      .first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Khám phá graph", exact: true }).click();
  await page.getByLabel("Công việc trung tâm").selectOption("demo_backend");
  await expect(page.locator(".react-flow__node")).toHaveCount(7);
  await page.screenshot({
    path: `../docs/reports/${reportPrefix}-graph.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("link", { name: "Phân tích", exact: true }).click();
  await page.getByLabel("Phạm vi địa điểm").selectOption("hcm");
  await expect(
    page.getByRole("heading", { name: "Kỹ năng được đề cập", exact: true }),
  ).toBeVisible();
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((v) =>
      ["critical", "serious"].includes(v.impact || ""),
    ),
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Mở menu", exact: true }),
  ).toBeVisible();
  await expect
    .poll(async () =>
      page
        .locator(".sidebar")
        .evaluate((el) => el.getBoundingClientRect().right),
    )
    .toBeLessThanOrEqual(0);
  await page.getByRole("button", { name: "Mở menu", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "Điều hướng chính" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect
    .poll(async () =>
      page
        .locator(".sidebar")
        .evaluate((el) => el.getBoundingClientRect().right),
    )
    .toBeLessThanOrEqual(0);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: `../docs/reports/${reportPrefix}-mobile.png`,
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/explore");
  await expect(
    page.getByRole("heading", {
      name: "Bắt đầu từ một công việc",
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: `../docs/reports/${reportPrefix}-overview.png`,
    fullPage: true,
  });
  expect(errors).toEqual([]);
});
