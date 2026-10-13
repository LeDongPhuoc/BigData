# Frontend theo feature, kết nối backend thật

React/TypeScript/Vite, React Router, TanStack Query, React Hook Form/Zod,
Tailwind CSS và React Flow. Giao diện tiếng Việt, tổ chức theo feature trong
`frontend/src/features`. Graph acceptance của Phase 1–2 và backend integration
đã đạt trước khi triển khai frontend.

| Feature | Nghiệp vụ đã triển khai | API thật |
| --- | --- | --- |
| Auth | Đăng ký, đăng nhập, khôi phục phiên, refresh rotation, đăng xuất thu hồi phiên | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/users/me` |
| Profiles | Sửa tên, headline, địa điểm, kinh nghiệm, cấp độ, hình thức/lương mong muốn; thêm/cập nhật/xóa kỹ năng | `/users/me`, `/profiles/me`, `/users/me/skills/{id}`, `/skills` |
| Privacy | Lưu đủ bốn flags, phân biệt thông tin ẩn và chưa khai báo, hồ sơ công khai theo quyền | `/users/me/privacy`, `/users/{id}/profile` |
| Jobs | Tìm từ khóa/skills, địa điểm, hình thức, cấp độ, doanh nghiệp; gợi ý theo hồ sơ có kỹ năng khớp; phân trang; chi tiết và điểm phù hợp | `/jobs`, `/matching/jobs`, `/jobs/{id}`, `/jobs/{id}/matching`, `/companies` |
| Network | Graph kết nối trực tiếp, hồ sơ được chia sẻ, xem người nhận và gửi lời mời, chấp nhận/từ chối/thu hồi | `/graph/connections`, `/connections/requests/*`, `/connections/{id}/*` |
| Paths | Chọn đường, 1–3 hops, phân trang, giải thích điểm; người nhận hiện làm việc và đã xác minh | `/graph/referral-paths` với job/company/depth/offset |
| Referrals | Gửi, theo dõi, hủy; inbox người giới thiệu; chấp nhận/từ chối/gửi giới thiệu/hoàn tất và lịch sử | `/referral-requests/*` |
| Notifications | Xem thông báo của mình, đi tới nghiệp vụ liên quan, đánh dấu đã đọc | `/notifications/me`, `/notifications/{id}/read` |

Mỗi nút có thao tác thực: request API, điều hướng tài nguyên, thay đổi bộ lọc,
chọn đường graph hoặc điều khiển viewport. Không có fake success, mock repository,
đăng nhập giả, dữ liệu dự phòng hoặc nút upload không có storage.

## Chạy local

Backend/database được bootstrap theo [README](../README.md). Sau đó:

```powershell
docker compose --profile web up -d --build --wait
```

Frontend: http://127.0.0.1:5173. Nginx proxy `/api/` tới backend; browser chỉ gọi
cùng origin. Refresh token và database credentials không được nhúng vào build.
Hai images frontend Node/Nginx pin version và digest cho Linux amd64; Nginx
runtime chạy user `nginx`, port 8080, healthcheck `/healthz`. Các host ports
chỉ bind loopback. Đây là môi trường local; TLS/public hosting chưa triển khai.

Đăng ký trong giao diện để tạo tài khoản thật. Seed graph là dữ liệu giả lập
được ghi vào ArangoDB thật; các user demo không có mật khẩu mặc định. Browser
tests chỉ cấp credentials trong database test, không sửa tài khoản demo ở
database đang sử dụng. Vai trò referrer và việc làm được xác minh do backend/
operator quản lý, không cho client tự cấp quyền.

Phát triển với Node >=22.12, sau khi dừng frontend container để nhường port:

```powershell
docker compose stop frontend
cd frontend
npm ci
npm run dev
```

Vite proxy mặc định tới `http://127.0.0.1:8000`. Có thể đổi
`API_PROXY_TARGET` cho backend khác. `VITE_API_BASE` mặc định `/api/v1`;
chỉ đặt URL khác khi có cấu hình origin được backend cho phép.

## Quyền và tính nhất quán

- Các routes nghiệp vụ yêu cầu phiên thật; server xác nhận user hiện tại.
  Vai trò lấy từ `/users/me`, không từ field JWT do UI tự giải mã. UI ẩn
  thao tác theo actor/participant/status; backend vẫn kiểm tra từng request.
- Không hiển thị email, CV, roles hoặc privacy flags của người khác trong
  graph. Public profile `skills/employment = null` được ghi rõ là chưa chia sẻ.
  HTTP 404 hiển thị thông tin không khả dụng, không suy đoán người đó tồn tại.
- Token trong memory và `sessionStorage` của tab, không `localStorage`; không
  lưu dữ liệu hồ sơ/graph vào persistent storage. Một lần refresh dùng chung
  cho requests đồng thời, retry 401 tối đa một lần. Refresh response bị mất
  yêu cầu đăng nhập lại để tránh dùng lại refresh token đã xoay. Không log token.
  Token vẫn do JavaScript truy cập vì backend dùng bearer; CSP và kiểm soát XSS
  cần được duy trì. Khi nhân bản tab có phiên, nên đăng nhập lại trong tab mới.
- Đăng xuất chỉ báo hoàn tất khi server đã thu hồi phiên. Đổi phiên xóa và
  hủy queries cũ. Privacy save reset các queries chứa hồ sơ/graph; không giữ
  kết quả private cũ làm placeholder khi lỗi request mới.
  Phản hồi API đến trễ sau khi đổi phiên bị loại bỏ trước khi service/UI nhận
  kết quả, kể cả mutations; không đưa hồ sơ tài khoản trước vào cache tài khoản sau.
  Profile/graph riêng tư không giữ cache sau khi rời trang, được kiểm tra lại
  mỗi 15 giây khi tab hoạt động và khi quay lại tab; quyền actor mỗi 30 giây.
  Không có server push: thay đổi quyền từ phiên khác có độ trễ tối đa một
  chu kỳ đọc cộng thời gian request. Mutations luôn được backend kiểm tra lại.
- `If-Match` từ revision chống cập nhật đè. HTTP 412 giữ bản nháp; người dùng
  chủ động tải bản mới trước khi lưu tiếp. Hủy/từ chối/xóa kỹ năng/thu hồi có
  xác nhận, disabled khi pending. Workflow chỉ báo thành công sau API thành công.
- Connection/referral create giữ nguyên idempotency key khi thử lại cùng
  payload, đổi key khi payload thay đổi. Backend đảm bảo transaction và uniqueness.
- Graph lấy 24 direct connections mỗi trang, hoặc 12 đường tối đa 3 hops;
  không tải toàn mạng. Canvas direct tối đa 32 nodes, canvas đường tối đa 4 users.
  Quan hệ xã hội hiển thị không hướng; breadcrumb chỉ mô tả hành trình tiếp cận.
  Điểm xếp hạng không phải xác suất được tuyển/giới thiệu thành công.

## Tìm kiếm ở API

`GET /jobs` thêm `q` (<=160), `location` (<=120), `work_mode`, `level`,
`company_id`. Từ khóa không phân biệt hoa/thường trong title/description/company
và tên skill active qua `job_requires_skill`;
địa điểm dùng substring. Filter chạy ở ArangoDB trước sort/pagination, chỉ
open jobs tại active companies. AQL dùng bind variables, giữ index `status`
và edge `_from`. Đây là substring search MVP có giới hạn runtime/memory,
chưa có full-text/relevance index ArangoSearch; không lọc giả trên một UI page.

Dashboard có mục **Gợi ý theo hồ sơ của bạn**; danh sách `/jobs?view=recommended`
gọi `GET /matching/jobs?matched_only=true` và các filters tương tự `/jobs`. AQL
chỉ giữ các tin có ít nhất một kỹ năng thỏa proficiency/years của hồ sơ, rồi
xếp hạng theo trọng số matching trước phân trang. Không yêu cầu có đường referral
để gợi ý việc làm. Mỗi card hiển thị score và tên kỹ năng khớp; skill match không
khẳng định ứng viên đã đủ toàn bộ điều kiện. Chỉ candidate được đọc matching của
mình; actor lấy từ token/session, không từ query. Thêm/xóa skill hoặc sửa profile
invalidate matching cache. Headline không tự chuyển thành edges `has_skill`.
Mục Kỹ năng có link đi thẳng đến gợi ý. Có loading, retry khi lỗi và empty state
hướng dẫn cập nhật hồ sơ; bộ lọc và pagination chạy trên backend thật.

## Kiểm chứng

```powershell
# Từ repository root; database thật phải healthy, không skip khi mất kết nối
.venv\Scripts\python.exe -m pytest tests/backend/test_jobs.py -q
cd frontend
npm run build
npm run format:check
npx playwright install chromium
cd ..
.venv\Scripts\python.exe scripts/check_frontend.py
node scripts/check_frontend_deployment.mjs
```

Harness tạo `jrn_e2e_<uuid>`, chạy migrations 001–005 và seed trên ArangoDB
3.12, tạo DB runtime user không có DDL, khởi động backend HTTP/Vite trên ports
riêng. Credentials ngẫu nhiên chỉ qua environment. `finally` dừng đúng processes,
xóa đúng test database và user đã tạo; không thay đổi database `job_referral`.
Các tin public fixture giữ nguồn công khai và không tạo quan hệ employment giả.
Artifacts dạng text được thay mật khẩu kiểm thử ngẫu nhiên bằng marker sau khi chạy.
Test quotas login/register cao hơn mặc định để nhiều ca chạy chung IP; policy
quota mặc định vẫn có backend integration tests riêng.

Các ca Playwright kiểm tra đăng nhập và revoke ở server; cập nhật hồ sơ và stale
revision; search/pagination/empty; luồng đăng ký → skill → invitation → accept →
path → referral → accept → submit → complete; cancel/thu hồi; đọc notifications;
private profiles; roles/IDOR; refresh single-flight và đổi tài khoản. Test loading
trì hoãn request thật. Test lỗi kết nối abort request và retry về server thật;
test mất phản hồi create thực sự commit trước khi abort. Không trả JSON giả.

Responsive 390/768/1440px, kiểm tra không tràn ngang, menu mobile,
axe WCAG A/AA trên dashboard/jobs/paths/profile; chụp desktop/mobile thực tế.
Không coi axe là chứng nhận toàn bộ WCAG. Xem
[kết quả browser](reports/frontend-playwright.xml),
[tóm tắt](reports/frontend-summary.json),
[backend tìm việc](reports/frontend-backend-jobs.xml).
Smoke bản build Docker/Nginx tại [frontend-deployment.json](reports/frontend-deployment.json).

Frontend quản trị doanh nghiệp, đăng tin, applications/CV upload, password reset,
email verification và admin dashboard nằm ngoài phạm vi feature của đợt này.
API backend tương ứng đã có hoặc phần thiếu được ghi tại [backend.md](backend.md).

Nguồn API thư viện đã kiểm tra: [Vite](https://vite.dev/guide/),
[Tailwind Vite](https://tailwindcss.com/docs/installation/using-vite),
[TanStack Query retries](https://tanstack.com/query/latest/docs/framework/react/guides/query-retries),
[React Flow accessibility](https://reactflow.dev/learn/advanced-use/accessibility).
Versions exact trong package.json/package-lock.json. TypeScript 5.9.3 đáp ứng
peer dependency của openapi-typescript; types API sinh từ OpenAPI backend thực tế.
