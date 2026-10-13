import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const password = process.env.JRN_E2E_PASSWORD!;

test("tin công khai có nguồn, trường chưa chuẩn hóa và không giả quan hệ nhân viên", async ({
  page,
}) => {
  await login(page);
  const jobId = process.env.JRN_E2E_PUBLIC_JOB!;
  await page.goto(`/jobs/${jobId}`);
  await expect(
    page.getByRole("heading", { name: "Nguồn thông tin", exact: true }),
  ).toBeVisible();
  const source = page.getByRole("link", { name: "Xem tin tuyển dụng gốc" });
  await expect(source).toHaveAttribute(
    "href",
    process.env.JRN_E2E_PUBLIC_SOURCE!,
  );
  await expect(source).toHaveAttribute("rel", "noopener noreferrer");
  await expect(
    page.getByText("Chưa có thông tin lương", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Số năm kinh nghiệm chưa được chuẩn hóa từ nguồn", {
      exact: false,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Đánh giá theo dữ liệu đã chuẩn hóa", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Xem đường giới thiệu", exact: true })
    .click();
  await expect(
    page.getByText("Chưa tìm thấy đường giới thiệu", { exact: true }),
  ).toBeVisible();
});
let runtimeErrors: string[];
test.beforeEach(({ page }) => {
  runtimeErrors = [];
  page.on("pageerror", (error) => runtimeErrors.push(error.message));
});
test.afterEach(() => {
  expect(runtimeErrors, "Uncaught browser errors").toEqual([]);
});
async function login(page: Page, letter = "a", navigate = true) {
  if (navigate) await page.goto("/login");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`demo-${letter}@example.test`);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Chào");
}
async function authed(
  page: Page,
  path: string,
  method = "GET",
  body?: unknown,
  revision?: string,
) {
  const access = await page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("jrn.session.v1")!)
        .access_token as string,
  );
  return page.request.fetch("/api/v1" + path, {
    method,
    headers: {
      Authorization: `Bearer ${access}`,
      ...(revision ? { "If-Match": `"${revision}"` } : {}),
    },
    ...(body !== undefined ? { data: body } : {}),
  });
}
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
}

test("security: stored HTML stays text and another account cannot read salary preferences", async ({
  page,
}) => {
  await page.goto("/register");
  await page
    .getByLabel("Tên hiển thị", { exact: true })
    .fill("QA Security Review");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`qa-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Tạo tài khoản", exact: true })
    .click();
  await expect(page).toHaveURL(/\/$/);
  const owner = await (await authed(page, "/users/me")).json();
  const payload = '<img src="x-security" onerror="window.qaXssExecuted=true">';
  const saved = await authed(
    page,
    "/profiles/me",
    "PATCH",
    {
      ...owner.profile,
      headline: payload,
      salary_min: 12345678,
      salary_max: 23456789,
    },
    owner.revision,
  );
  expect(saved.status()).toBe(200);
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, "b", false);
  await page.goto(`/people/${owner.id}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "QA Security Review",
  );
  await expect(page.getByText(payload, { exact: true }).first()).toBeVisible();
  expect(await page.locator('img[src="x-security"]').count()).toBe(0);
  expect(
    await page.evaluate(
      () => (window as Window & { qaXssExecuted?: boolean }).qaXssExecuted,
    ),
  ).toBeUndefined();
  const shared = await (
    await authed(page, `/users/${owner.id}/profile`)
  ).json();
  expect(shared.profile.salary_min).toBeNull();
  expect(shared.profile.salary_max).toBeNull();
  expect(shared.email).toBeUndefined();
});

test("security: oversized body over real HTTP is rejected and server stays healthy", async ({
  page,
}) => {
  const denied = await page.request.post("/api/v1/auth/login", {
    headers: { "Content-Type": "application/json" },
    data: JSON.stringify({
      email: "qa@example.com",
      password: "x".repeat(131073),
    }),
  });
  expect(denied.status()).toBe(413);
  expect((await denied.json()).error.code).toBe("request_too_large");
  expect(denied.headers()["cache-control"]).toBe("no-store");
  expect((await page.request.get("/api/v1/jobs")).status()).toBe(401);
});

test("đăng nhập: validation, mật khẩu sai, phiên và đăng xuất được thu hồi ở server", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByText("Nhập địa chỉ email hợp lệ.")).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill("demo-a@example.test");
  await page
    .getByLabel("Mật khẩu", { exact: true })
    .fill("Wrong passphrase 2026!");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Thông tin đăng nhập");
  await login(page);
  const access = await page.evaluate(
    () =>
      JSON.parse(sessionStorage.getItem("jrn.session.v1")!)
        .access_token as string,
  );
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    (
      await page.request.get("/api/v1/users/me", {
        headers: { Authorization: `Bearer ${access}` },
      })
    ).status(),
  ).toBe(401);
  expect(
    await page.evaluate(() => sessionStorage.getItem("jrn.session.v1")),
  ).toBeNull();
  await page.goto("/profile");
  await expect(page).toHaveURL(/\/login$/);
});

test("hồ sơ: lưu thật, validation lương và xung đột phiên bản giữ bản nháp", async ({
  page,
}) => {
  await login(page);
  await page.goto("/profile");
  await page
    .getByLabel("Giới thiệu ngắn", { exact: true })
    .fill("ArangoDB engineer — lưu bằng API thật");
  await page.getByLabel("Lương tối thiểu (VND)").fill("50000000");
  await page.getByLabel("Lương tối đa (VND)").fill("20000000");
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  await expect(
    page.getByText("Lương tối đa phải lớn hơn hoặc bằng lương tối thiểu."),
  ).toBeVisible();
  await page.getByLabel("Lương tối thiểu (VND)").fill("20000000");
  await page.getByLabel("Lương tối đa (VND)").fill("40000000");
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  await expect(page.getByText("Đã lưu hồ sơ.", { exact: true })).toBeVisible();
  const saved = await (await authed(page, "/users/me")).json();
  expect(saved.profile.headline).toBe("ArangoDB engineer — lưu bằng API thật");
  expect(
    (
      await authed(
        page,
        "/users/me",
        "PATCH",
        { display_name: "Tên cập nhật ở phiên khác" },
        saved.revision,
      )
    ).status(),
  ).toBe(200);
  await page
    .getByLabel("Tên hiển thị", { exact: true })
    .fill("Bản nháp chưa ghi đè");
  await page.getByRole("button", { name: "Lưu hồ sơ", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Dữ liệu đã được cập nhật",
  );
  await expect(page.getByLabel("Tên hiển thị", { exact: true })).toHaveValue(
    "Bản nháp chưa ghi đè",
  );
  expect((await (await authed(page, "/users/me")).json()).display_name).toBe(
    "Tên cập nhật ở phiên khác",
  );
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Tải bản mới của hồ sơ" }).click();
  await expect(page.getByLabel("Tên hiển thị", { exact: true })).toHaveValue(
    "Tên cập nhật ở phiên khác",
  );
});

test("tìm việc: bộ lọc toàn bộ database, phân trang, empty state và chi tiết phù hợp", async ({
  page,
}) => {
  await login(page);
  await page.goto("/jobs");
  await page.getByLabel("Từ khóa tìm việc").fill("E2E Pagination");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(page.locator(".search-results .job-card")).toHaveCount(12);
  await page.getByRole("button", { name: "Trang sau" }).click();
  await expect(page.locator(".search-results .job-card")).toHaveCount(2);
  await expect(page).toHaveURL(/offset=12/);
  await page
    .getByLabel("Hình thức làm việc", { exact: true })
    .selectOption("remote");
  await expect(page.getByText("Chưa tìm thấy công việc phù hợp")).toBeVisible();
  await page.getByRole("button", { name: "Xóa điều kiện tìm kiếm" }).click();
  await page.getByLabel("Từ khóa tìm việc").fill("Backend Developer");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(page.locator(".job-card")).toHaveCount(1);
  await page.locator(".job-card h3 a").click();
  await expect(
    page.getByRole("heading", {
      name: "Backend Developer (demo)",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText("Đạt yêu cầu bắt buộc")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Xem đường giới thiệu" }),
  ).toBeVisible();
});

test("gợi ý theo hồ sơ: lưu Java PostgreSQL AWS, thấy kỹ năng khớp và cập nhật khi xóa", async ({
  page,
}) => {
  test.setTimeout(120000);
  await page.goto("/register");
  await page.getByLabel("Tên hiển thị").fill("Ứng viên kiểm thử gợi ý");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`recommend-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Tạo tài khoản", exact: true })
    .click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByText("Chưa có việc làm khớp kỹ năng", { exact: true }),
  ).toBeVisible();
  await page.goto("/profile");
  for (const [slug, name] of [
    ["java", "Java"],
    ["postgresql", "PostgreSQL"],
    ["aws", "AWS"],
  ]) {
    await page
      .getByLabel("Thêm hoặc cập nhật kỹ năng")
      .selectOption(`public_skill_${slug}`);
    await page.getByLabel("Mức thành thạo").selectOption("4");
    await page.getByLabel("Số năm sử dụng").fill("3");
    await page
      .getByRole("button", { name: "Lưu kỹ năng", exact: true })
      .click();
    await expect(
      page.locator(".skill-list").getByText(name, { exact: true }),
    ).toBeVisible();
  }
  await page.goto("/");
  const recommendations = page.getByRole("region", {
    name: "Gợi ý việc làm theo hồ sơ",
  });
  await expect(recommendations.locator(".job-card").first()).toBeVisible();
  await expect(recommendations.locator(".job-match")).toHaveCount(2);
  await expect(recommendations).toContainText("Java");
  await expect(recommendations).toContainText("PostgreSQL");
  await expect(recommendations).toContainText("AWS");
  await page.getByRole("link", { name: "Xem tất cả gợi ý" }).click();
  await expect(page).toHaveURL(/view=recommended/);
  await expect(page.locator(".recommendation-results .job-card")).toHaveCount(
    2,
  );
  await page.getByLabel("Từ khóa tìm việc").fill("PostgreSQL");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(page.locator(".recommendation-results .job-card")).toHaveCount(
    1,
  );
  await page.getByRole("button", { name: "Xóa bộ lọc", exact: true }).click();
  await expect(page).toHaveURL(/view=recommended/);
  await expect(page.locator(".recommendation-results .job-card")).toHaveCount(
    2,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await noOverflow(page);
  await page.goto("/profile");
  page.on("dialog", (dialog) => dialog.accept());
  for (const name of ["Java", "PostgreSQL", "AWS"]) {
    await page
      .getByRole("button", { name: `Xóa kỹ năng ${name}`, exact: true })
      .click();
    await expect(
      page.locator(".skill-list").getByText(name, { exact: true }),
    ).toHaveCount(0);
  }
  await page
    .getByRole("link", { name: "Xem việc làm theo kỹ năng đã lưu" })
    .click();
  await expect(
    page.getByText("Chưa có việc làm khớp kỹ năng", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".recommendation-results .job-card")).toHaveCount(
    0,
  );
});

test("gợi ý theo hồ sơ: loading lỗi kết nối và thử lại đọc API thật", async ({
  page,
}) => {
  await login(page);
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/matching/jobs?**", async (route) => {
    await pending;
    await route.continue();
  });
  await page.goto("/jobs?view=recommended");
  await expect(page.getByRole("status")).toContainText(
    "Đang tìm việc theo hồ sơ",
  );
  release();
  await expect(
    page.locator(".recommendation-results .job-card").first(),
  ).toBeVisible();
  await page.unroute("**/api/v1/matching/jobs?**");
  await page.route("**/api/v1/matching/jobs?**", (route) =>
    route.abort("connectionfailed"),
  );
  await page.getByLabel("Từ khóa tìm việc").fill("Python");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Không kết nối được máy chủ",
  );
  await expect(page.locator(".recommendation-results .job-card")).toHaveCount(
    0,
  );
  await page.unroute("**/api/v1/matching/jobs?**");
  await page.getByRole("button", { name: "Thử lại", exact: true }).click();
  await expect(
    page.locator(".recommendation-results .job-card").first(),
  ).toBeVisible();
});

test("đăng ký → kỹ năng → kết nối → đường giới thiệu → gửi lại sau mất phản hồi → hoàn tất", async ({
  page,
  browser,
}) => {
  test.setTimeout(120000);
  const bridge = await browser.newPage(),
    referrer = await browser.newPage();
  try {
    await page.goto("/register");
    await page.getByLabel("Tên hiển thị").fill("Ứng viên E2E");
    await page
      .getByLabel("Email", { exact: true })
      .fill(`candidate-${crypto.randomUUID()}@example.com`);
    await page.getByLabel("Mật khẩu", { exact: true }).fill(password);
    await page
      .getByRole("button", { name: "Tạo tài khoản", exact: true })
      .click();
    await expect(page).toHaveURL(/\/$/);
    await page.goto("/profile");
    for (const id of ["demo_python", "demo_sql"]) {
      await page.getByLabel("Thêm hoặc cập nhật kỹ năng").selectOption(id);
      await page.getByLabel("Mức thành thạo").selectOption("4");
      await page.getByLabel("Số năm sử dụng").fill("4");
      await page
        .getByRole("button", { name: "Lưu kỹ năng", exact: true })
        .click();
      await expect(
        page
          .locator(".skill-list")
          .getByText(id.replace("demo_", ""), { exact: true }),
      ).toBeVisible();
    }
    await page.goto("/network");
    await expect(
      page.getByText("Mạng lưới đang chờ kết nối đầu tiên"),
    ).toBeVisible();
    await page.getByLabel("Mã hồ sơ người nhận").fill("demo_b");
    await page.getByRole("button", { name: "Xem người nhận" }).click();
    await page.getByRole("button", { name: "Gửi lời mời kết nối" }).click();
    await expect(
      page.getByText("Đã gửi lời mời kết nối.", { exact: true }),
    ).toBeVisible();
    await login(bridge, "b");
    await bridge.goto("/network");
    await bridge
      .getByRole("button", { name: "Lời mời đến", exact: true })
      .click();
    await bridge
      .getByRole("button", { name: "Chấp nhận", exact: true })
      .click();
    await expect(
      bridge.getByText("Đã cập nhật lời mời kết nối.", { exact: true }),
    ).toBeVisible();
    await page.goto("/jobs/demo_backend/paths");
    await expect(
      page.getByRole("heading", { name: "Vì sao đường này được đề xuất?" }),
    ).toBeVisible();
    await expect(page.locator(".path-explanation .badge")).toHaveText(
      "2 kết nối",
    );
    await page
      .getByRole("link", { name: "Gửi yêu cầu giới thiệu", exact: true })
      .click();
    await page
      .getByLabel("Lời nhắn của bạn")
      .fill("Mình có kinh nghiệm Python và SQL, mong bạn cân nhắc giới thiệu.");
    let committedId = "",
      attempts = 0;
    const keys: string[] = [];
    await page.route("**/api/v1/referral-requests", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      attempts++;
      keys.push(route.request().headers()["idempotency-key"]);
      if (attempts === 1) {
        const response = await route.fetch();
        expect(response.status()).toBe(201);
        committedId = (await response.json()).id;
        await route.abort("connectionfailed"); // Server committed; its response is lost.
      } else await route.continue();
    });
    await page
      .getByRole("button", { name: "Gửi yêu cầu giới thiệu", exact: true })
      .click();
    await expect(page.getByRole("alert")).toContainText(
      "Không kết nối được máy chủ",
    );
    await page
      .getByRole("button", { name: "Gửi yêu cầu giới thiệu", exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`/referrals/${committedId}$`));
    expect(attempts).toBe(2);
    expect(keys[0]).toBeTruthy();
    expect(keys[0]).toBe(keys[1]);
    const own = await (await authed(page, "/referral-requests/me")).json();
    expect(own.items).toHaveLength(1);
    await login(referrer, "c");
    await referrer.goto(`/referrals/${committedId}`);
    await expect(
      referrer.getByRole("button", { name: "Hủy yêu cầu" }),
    ).toHaveCount(0);
    await referrer
      .getByRole("button", { name: "Chấp nhận yêu cầu", exact: true })
      .click();
    await expect(referrer.locator(".page-heading .badge")).toHaveText(
      "Đã chấp nhận",
    );
    await referrer
      .getByLabel("Mã bằng chứng giới thiệu", { exact: true })
      .fill("e2e/referral/ticket-1");
    await referrer
      .getByRole("button", { name: "Xác nhận đã giới thiệu" })
      .click();
    await expect(referrer.locator(".page-heading .badge")).toHaveText(
      "Đã giới thiệu",
    );
    await referrer
      .getByLabel("Kết quả giới thiệu")
      .fill("Đã trao đổi với đội tuyển dụng.");
    await referrer.getByRole("button", { name: "Hoàn tất giới thiệu" }).click();
    await expect(referrer.locator(".page-heading .badge")).toHaveText(
      "Hoàn tất",
    );
    await page.reload();
    await expect(page.locator(".page-heading .badge")).toHaveText("Hoàn tất");
    await expect(page.locator(".timeline li")).toHaveCount(4);
    await expect(page.getByRole("button", { name: "Hủy yêu cầu" })).toHaveCount(
      0,
    );
    expect(
      (await (await authed(page, `/referral-requests/${committedId}`)).json())
        .status,
    ).toBe("completed");
  } finally {
    await bridge.close();
    await referrer.close();
  }
});

test("hủy yêu cầu và thu hồi lời mời đều xác nhận và cập nhật database", async ({
  page,
}) => {
  await login(page);
  await page.goto("/referrals/demo_a_backend");
  page.once("dialog", (dialog) => dialog.dismiss());
  await page.getByRole("button", { name: "Hủy yêu cầu", exact: true }).click();
  await expect(page.locator(".page-heading .badge")).toHaveText("Đang chờ");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Hủy yêu cầu", exact: true }).click();
  await expect(page.locator(".page-heading .badge")).toHaveText("Đã hủy");
  expect(
    (await (await authed(page, "/referral-requests/demo_a_backend")).json())
      .status,
  ).toBe("cancelled");
  await page.goto("/network");
  await page
    .getByRole("button", { name: "Lời mời đã gửi", exact: true })
    .click();
  await expect(page.locator(".connection-request")).toHaveCount(1);
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Thu hồi", exact: true }).click();
  await expect(page.getByText("Chưa có lời mời đang chờ")).toBeVisible();
  expect(
    (await (await authed(page, "/connections/requests/outgoing")).json()).items,
  ).toHaveLength(0);
});

test("thông báo: đánh dấu đã đọc bằng API thật và empty state tài khoản chưa có hoạt động", async ({
  page,
  browser,
}) => {
  await login(page, "c");
  await page.goto("/notifications");
  const buttons = page.getByRole("button", {
    name: "Đánh dấu đã đọc",
    exact: true,
  });
  await expect(buttons.first()).toBeVisible();
  const count = await buttons.count();
  expect(count).toBeGreaterThan(0);
  await buttons.first().click();
  await expect(buttons).toHaveCount(count - 1);
  const stored = await (await authed(page, "/notifications/me")).json();
  expect(stored.items[0].read_at).not.toBeNull();
  const empty = await browser.newPage();
  try {
    await login(empty, "d");
    await empty.goto("/notifications");
    await expect(empty.getByText("Bạn đã xem hết cập nhật")).toBeVisible();
  } finally {
    await empty.close();
  }
});

test("mạng lưới: chọn đường, giới hạn độ sâu và ẩn tài khoản không được chia sẻ", async ({
  page,
}) => {
  await login(page);
  await page.goto("/jobs/demo_backend/paths");
  await expect(page.locator(".path-option")).toHaveCount(2);
  await page.locator(".path-option").nth(1).click();
  await expect(page.locator(".path-explanation .badge")).toHaveText(
    "3 kết nối",
  );
  await page.getByLabel("Số kết nối tối đa").selectOption("1");
  await expect(page.getByText("Chưa tìm thấy đường giới thiệu")).toBeVisible();
  await page.getByLabel("Số kết nối tối đa").selectOption("2");
  await expect(page.locator(".path-option")).toHaveCount(1);
  await page.goto("/network");
  await expect(page.locator('.person-card[href="/people/demo_g"]')).toHaveCount(
    0,
  );
  await expect(page.locator('.person-card[href="/people/demo_j"]')).toHaveCount(
    0,
  );
  await page.goto("/people/demo_g");
  await expect(page.getByRole("alert")).toContainText(
    "Thông tin không khả dụng",
  );
});

test("quyền riêng tư: phân biệt thông tin ẩn và rỗng, cập nhật thật chặn xem hồ sơ", async ({
  page,
  browser,
}) => {
  await login(page);
  await page.goto("/people/demo_t");
  await expect(
    page.getByText("Người này chưa chia sẻ kỹ năng với bạn."),
  ).toBeVisible();
  await expect(
    page.getByText("Người này chưa chia sẻ nơi làm việc với bạn."),
  ).toBeVisible();
  const owner = await browser.newPage();
  try {
    await login(owner, "t");
    await owner.goto("/profile/privacy");
    await owner
      .getByRole("switch", { name: "Cho phép tìm thấy hồ sơ" })
      .uncheck();
    await owner.getByRole("button", { name: "Lưu quyền riêng tư" }).click();
    await expect(
      owner.getByText("Đã lưu quyền riêng tư.", { exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toContainText(
      "Thông tin không khả dụng",
      { timeout: 20000 },
    );
    await owner.goto("/profile");
    await expect(
      owner.getByLabel("Tên hiển thị", { exact: true }),
    ).toBeVisible();
  } finally {
    await owner.close();
  }
});

test("phân quyền: admin không có thao tác ứng viên, request người khác bị từ chối", async ({
  page,
}) => {
  await login(page, "e");
  await expect(
    page.getByRole("heading", { name: "Gợi ý theo hồ sơ của bạn" }),
  ).toHaveCount(0);
  await page.goto("/jobs?view=recommended");
  await expect(
    page.getByRole("link", { name: "Gợi ý theo hồ sơ", exact: true }),
  ).toHaveCount(0);
  await page.goto("/jobs/demo_backend");
  await expect(
    page.getByRole("heading", { name: "Mức độ phù hợp" }),
  ).toHaveCount(0);
  await page.goto("/jobs/demo_backend/paths");
  await expect(
    page.getByRole("link", { name: "Gửi yêu cầu giới thiệu", exact: true }),
  ).toHaveCount(0);
  await page.goto("/jobs/demo_backend/referral?referrer=demo_c");
  await expect(page.getByRole("alert")).toContainText("vai trò ứng viên");
  await page.goto("/referrals/demo_a_backend");
  await expect(page.getByRole("alert")).toContainText(
    "Thông tin không khả dụng",
  );
  await expect(
    page.getByText("Yêu cầu giả lập cho kiểm thử trạng thái"),
  ).toHaveCount(0);
});

test("loading/error/retry dùng phản hồi API thật và lỗi kết nối được chèn có kiểm soát", async ({
  page,
}) => {
  await login(page);
  let release!: () => void;
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/jobs?**", async (route) => {
    await pending;
    await route.continue();
  });
  await page.goto("/jobs");
  await expect(page.getByRole("status")).toContainText("Đang tìm việc làm");
  release();
  await expect(page.locator(".job-card").first()).toBeVisible();
  await page.unroute("**/api/v1/jobs?**");
  await page.route("**/api/v1/jobs?**", (route) =>
    route.abort("connectionfailed"),
  );
  await page.getByLabel("Từ khóa tìm việc").fill("Remote Python");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Không kết nối được máy chủ",
  );
  await page.unroute("**/api/v1/jobs?**");
  await page.getByRole("button", { name: "Thử lại", exact: true }).click();
  await expect(page.locator(".job-card")).toHaveCount(1);
  await expect(page.locator(".job-card h3")).toContainText("Remote Python");
});

test("refresh đồng thời chỉ xoay token một lần; đổi tài khoản xóa dữ liệu người trước", async ({
  page,
}) => {
  await login(page);
  let refreshes = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/auth/refresh")) refreshes++;
  });
  const result = await page.evaluate(async () => {
    const apiSource = "/src/lib/api.ts",
      sessionSource = "/src/lib/session.ts";
    const client = await import(apiSource),
      store = await import(sessionSource);
    const before = store.session.get();
    store.session.set(
      { ...before, access_token: "invalid-expired-access" },
      false,
    );
    const rows = await Promise.all([
      client.api("/users/me"),
      client.api("/profiles/me"),
      client.api("/graph/connections?limit=12"),
    ]);
    return {
      count: rows.length,
      rotated: store.session.get().refresh_token !== before.refresh_token,
    };
  });
  expect(result).toEqual({ count: 3, rotated: true });
  expect(refreshes).toBe(1);
  await page.goto("/jobs/demo_backend/paths");
  await expect(page.locator(".path-option")).toHaveCount(2);
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  await login(page, "t");
  await page.goto("/jobs/demo_backend/paths");
  await expect(page.getByText("Chưa tìm thấy đường giới thiệu")).toBeVisible();
  await expect(page.locator(".path-option")).toHaveCount(0);
});

test("phản hồi cập nhật đến trễ sau khi đổi tài khoản không được đưa vào cache phiên mới", async ({
  page,
}) => {
  await login(page);
  const user = await (await authed(page, "/users/me")).json();
  let committed!: () => void, release!: () => void;
  const ready = new Promise<void>((resolve) => {
    committed = resolve;
  });
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/users/me", async (route) => {
    if (route.request().method() !== "PATCH") return route.continue();
    const result = await route.fetch();
    expect(result.status()).toBe(200);
    committed();
    await gate;
    await route.fulfill({ response: result });
  });
  const pending = page.evaluate(async (revision) => {
    const source = "/src/lib/api.ts",
      client = await import(source);
    try {
      await client.api("/users/me", {
        method: "PATCH",
        revision,
        body: { display_name: "Phản hồi tài khoản cũ" },
      });
      return { code: "unsafe-success" };
    } catch (error) {
      return { code: (error as { code: string }).code };
    }
  }, user.revision as string);
  try {
    await ready;
    await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
    await expect(page).toHaveURL(/\/login$/);
    await login(page, "b", false);
    release();
    expect(await pending).toEqual({ code: "session_changed" });
    await expect(page.locator(".user-link strong")).toHaveText(
      "Cầu nối B (demo)",
    );
    expect((await (await authed(page, "/users/me")).json()).id).toBe("demo_b");
  } finally {
    release();
  }
});

for (const viewport of [
  { width: 1440, height: 1000 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
]) {
  test(`responsive và accessibility ở ${viewport.width}px: tổng quan, việc làm, graph, hồ sơ`, async ({
    page,
  }) => {
    test.setTimeout(120000);
    await page.setViewportSize(viewport);
    await login(page);
    for (const [path, label] of [
      ["/", "dashboard"],
      ["/jobs", "jobs"],
      ["/jobs/demo_backend/paths", "paths"],
      ["/profile", "profile"],
    ]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      if (label === "jobs")
        await expect(page.locator(".job-card").first()).toBeVisible();
      if (label === "paths")
        await expect(page.locator(".path-option").first()).toBeVisible();
      if (label === "profile")
        await expect(
          page.getByLabel("Tên hiển thị", { exact: true }),
        ).toBeVisible();
      await noOverflow(page);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(
        results.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
      ).toEqual([]);
      if (
        (label === "dashboard" || label === "paths") &&
        viewport.width !== 768
      )
        await page.screenshot({
          path: `../docs/reports/frontend-${label}-${viewport.width}.png`,
          fullPage: true,
        });
    }
    if (viewport.width < 1000) {
      await page.getByRole("button", { name: "Mở menu" }).click();
      await expect(
        page.getByRole("button", { name: "Đăng xuất", exact: true }),
      ).toBeVisible();
      await page.getByRole("link", { name: "Mạng lưới", exact: true }).click();
      await expect(page).toHaveURL(/\/network$/);
      await expect(
        page.getByRole("button", { name: "Mở menu" }),
      ).toHaveAttribute("aria-expanded", "false");
    }
  });
}
