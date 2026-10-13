# Nhật ký chỉnh sửa và cập nhật hệ thống

Tài liệu này ghi lại các thay đổi đã thực hiện, lý do thay đổi, kết quả kiểm tra và phần còn chờ triển khai. [Danh sách task chức năng lõi](tasks-chuc-nang-loi-ui.md) tiếp tục được giữ riêng để theo dõi tiến độ.

**Cách cập nhật:** bổ sung mục mới ở cuối tài liệu, ghi ngày theo múi giờ Việt Nam (`Asia/Saigon`). Không xóa hoặc ghi đè các mục đã ghi. Nếu cần đính chính, thêm mục đính chính và dẫn tới nội dung cũ; phân biệt công việc đã hoàn thành với kế hoạch chưa thực hiện. Không ghi mật khẩu, token hoặc nội dung bí mật trong nhật ký.

## 2026-10-13 — Rà soát dữ liệu, lập kế hoạch và xây chức năng lõi trên seed

### 1. Yêu cầu và phạm vi đã thống nhất

- Thời gian triển khai dự kiến của đồ án: 3 ngày.
- Ưu tiên xây và xem UI các chức năng lõi trước, xử lý VietJobs bằng Spark sau.
- Giữ dữ liệu seed và các chức năng backend/frontend hiện có đang hoạt động ổn.
- Có danh sách task, hướng dẫn thử và bằng chứng kiểm tra; không đánh dấu hoàn thành chỉ vì đã có màn hình.

### 2. Rà soát dữ liệu và tài liệu đề tài

- Đã xem dữ liệu VietJobs có sẵn tại `DATA_/vietjobs-network/data/raw/vietjobs/VietJobs.csv`: 48.092 dòng, 18 cột; kiểm tra trùng lặp, dữ liệu kỹ năng bị thiếu, địa điểm và trường lương cần chuẩn hóa. Đây là khảo sát dữ liệu, chưa phải pipeline ETL đã triển khai.
- Đã đối chiếu đề cương trong `DATA_/De_cuong_trien_khai_BigData.docx` với hệ thống hiện có. Hướng khai thác Job–Skill–Category–Location bằng Spark/ArangoDB cần được bổ sung bên cạnh nghiệp vụ mạng lưới giới thiệu đang có.
- Đã phân biệt dữ liệu seed trong database, catalog nguồn công khai trong repository và bộ VietJobs. Việc có file dữ liệu không đồng nghĩa hệ thống đã import hoặc đang sử dụng dữ liệu đó.
- Đã soạn [kế hoạch tổng thể](ke-hoach-vietjobs-spark-arangodb.md), [kế hoạch triển khai v2](ke-hoach-trien-khai-vietjobs-v2.md) và [kế hoạch 3 ngày](ke-hoach-vietjobs-3-ngay.md). Các bước Spark/ETL trong tài liệu vẫn là kế hoạch, chưa được thực hiện trong đợt xây UI.

### 3. Môi trường và khởi động hệ thống

- Đã khởi động Docker Desktop và hệ thống Docker Compose gồm ArangoDB, backend, frontend.
- Trong quá trình khởi động trước đó, đã xử lý lỗi cache BuildKit/bbolt sau khi sao lưu dữ liệu Docker; giữ các volume ArangoDB.
- Đã phục hồi tài khoản database runtime theo cấu hình hiện có để backend kết nối được; không đặt mật khẩu đăng nhập cho các tài khoản seed.
- Sau khi bổ sung chức năng, đã build và cập nhật bản local bằng `docker compose --profile web up -d --build --wait`. Frontend, backend và ArangoDB đạt trạng thái healthy tại thời điểm kiểm tra.

### 4. Các chức năng hiện có được giữ lại

Giữ các API và đường dẫn nghiệp vụ cũ cho tài khoản/phiên đăng nhập, hồ sơ/kỹ năng/quyền riêng tư, catalog việc làm, gợi ý theo hồ sơ đã lưu, kết nối người dùng, tìm đường giới thiệu, yêu cầu giới thiệu và thông báo. Các module công ty, ứng tuyển, audit và quản trị cũng được giữ lại; chưa xây thêm trang quản trị riêng trong đợt này.

Không chạy seed lại hoặc thay schema nghiệp vụ của database đang dùng trong đợt bổ sung UI. Form hồ sơ thử nghiệm mới không ghi đè hồ sơ đã lưu và không thay thuật toán gợi ý cũ.

### 5. Backend được bổ sung

Tạo module `backend/modules/exploration` và đăng ký router trong `backend/app.py`.

| Endpoint mới | Chức năng |
|---|---|
| `GET /api/v1/exploration/catalog` | Đọc tin đang mở, công ty đang hoạt động, kỹ năng và metadata nguồn; trả nhãn seed/công khai/nội bộ |
| `GET /api/v1/exploration/jobs/{job_id}/similar` | Tìm việc có kỹ năng chung theo Jaccard; trả điểm và kỹ năng chung |
| `POST /api/v1/exploration/recommendations` | Đối chiếu hồ sơ tạm thời; trả xếp hạng, điểm thành phần, coverage, kỹ năng khớp và kỹ năng chưa khai báo |

- Các endpoint mới yêu cầu xác thực. POST gợi ý chỉ tính kết quả, không lưu hồ sơ hoặc sửa database.
- Catalog giới hạn 1.000 tin theo key; có cờ `truncated` để UI thông báo phạm vi thực sự đã tải.
- Gợi ý sử dụng trọng số kỹ năng 50%, kinh nghiệm 20%, địa điểm 20%, hình thức 10%; tiêu chí chưa chọn được bỏ khỏi tổng trọng số.
- Dữ liệu thiếu không được coi là khớp yêu cầu. Điểm trên dữ liệu đã biết và tỷ lệ trọng số đủ dữ liệu (`coverage`) được trả riêng; điểm không phải xác suất được tuyển.
- Có validation hồ sơ đầu vào và schema đầu ra. OpenAPI đã được xuất lại; frontend dùng kiểu sinh từ hợp đồng API.

### 6. Frontend được bổ sung

Tạo khu **Khám phá việc làm** trong `frontend/src/features/exploration`, thêm liên kết trên sidebar và dashboard.

| Đường dẫn | Nội dung mới |
|---|---|
| `/explore` | Tổng quan số tin, kỹ năng, địa điểm, số tin seed và trạng thái nguồn dữ liệu |
| `/explore/jobs` | Tìm theo từ khóa; lọc địa điểm, kỹ năng, hình thức; phân trang và xóa bộ lọc |
| `/explore/jobs/:jobId` | Nội dung công việc, yêu cầu kỹ năng, nguồn dữ liệu, lương/kinh nghiệm và việc tương tự |
| `/explore/recommendations` | Form hồ sơ thử nghiệm; điểm thành phần, coverage, kỹ năng khớp/còn thiếu |
| `/explore/graph` | Graph công việc–kỹ năng–địa điểm; chọn công việc trung tâm, kéo node, zoom/pan và mở việc liên quan |
| `/explore/analytics` | Thống kê kỹ năng, địa điểm, hình thức, kinh nghiệm và khoảng lương theo phạm vi địa điểm |

Có trạng thái loading, lỗi, thử lại và dữ liệu rỗng. UI hiển thị rõ đang dùng catalog hiện có, VietJobs chưa nhập và kết quả chưa đến từ Spark.

### 7. Các chỉnh sửa trong quá trình hoàn thiện

- Đồng bộ ô từ khóa với query trên URL khi điều hướng; lấy số trang nguyên và giới hạn trong phạm vi kết quả.
- Khóa các trường hồ sơ thử nghiệm khi đang tính gợi ý để tránh hiển thị kết quả cho một bộ tiêu chí vừa bị thay đổi.
- Dùng trạng thái node/edge mặc định của React Flow để kéo node hoạt động; dựng lại graph khi đổi công việc trung tâm.
- Điều chỉnh số cột thẻ việc làm theo kích thước màn hình, bố cục kết quả tìm kiếm và cách căn icon địa điểm.
- Sửa bộ chọn trong kiểm thử để phân biệt liên kết cùng tên trên sidebar và dashboard.
- Bổ sung kiểm tra menu trên mobile: mở menu, đóng bằng Escape, đợi chuyển động hoàn tất trước khi chụp ảnh.
- Thêm cấu hình `JRN_E2E_BROWSER` để dùng Edge có sẵn khi Chromium của Playwright chưa được cài; mặc định vẫn là Chromium.
- Bổ sung smoke test route `/explore/graph` và API catalog qua proxy của bản frontend đóng gói trong Docker.
- Chỉnh README: có file catalog công khai trong repository không có nghĩa database đang chạy đã nhập catalog đó; thêm liên kết khu khám phá và task.

### 8. Các file chính được tạo hoặc cập nhật

| Nhóm | File/thư mục | Thay đổi |
|---|---|---|
| Backend mới | `backend/modules/exploration/__init__.py`, `api.py`, `schemas.py`, `service.py` | Tạo module catalog, similarity và gợi ý tạm |
| Đăng ký API | `backend/app.py` | Bổ sung exploration router |
| UI mới | `frontend/src/features/exploration/ExplorePage.tsx`, `SkillGraph.tsx`, `exploration.css`, `types.ts` | Tạo các màn hình khám phá và kiểu dữ liệu |
| Điều hướng | `frontend/src/main.tsx`, `components/Shell.tsx`, `features/dashboard/DashboardPage.tsx` | Thêm route và lối vào khu khám phá; các đường dẫn dưới `frontend/src` |
| Hợp đồng API | `docs/api.openapi.json`, `frontend/src/lib/api.generated.ts` | Xuất lại schema, sinh kiểu TypeScript và chuẩn hóa định dạng |
| Kiểm thử | `tests/backend/test_exploration.py`, `frontend/e2e/exploration.spec.ts` | Tạo kiểm thử API và luồng UI mới |
| Cấu hình kiểm thử | `frontend/playwright.config.ts`, `scripts/check_frontend_deployment.mjs` | Chọn browser và bổ sung kiểm tra bản Docker |
| Tài liệu | `README.md`, `docs/tasks-chuc-nang-loi-ui.md`, `docs/reports/exploration-ui-validation.md` | Cập nhật hướng dẫn, task và kết quả kiểm tra |
| Bằng chứng | `docs/reports/exploration-*`, `docs/reports/frontend-deployment.json` | Báo cáo browser, ảnh giao diện và kết quả kiểm tra deployment local |
| Nhật ký | `docs/nhat-ky-chinh-sua.md` | Tạo mới để ghi lịch sử bổ sung; giữ nguyên file task trong lần cập nhật nhật ký này |

### 9. Kết quả kiểm tra đã ghi nhận hôm nay

| Kiểm tra | Kết quả |
|---|---|
| Hồi quy backend `tests/backend` | 92 kiểm thử đạt trên ArangoDB thật |
| Kiểm tra lại API mới sau khi thêm response schema | 4 kiểm thử đạt; đây là lượt chạy lại, không cộng thêm vào số kiểm thử duy nhất |
| Hồi quy trình duyệt | 21 kiểm thử đạt, 0 bỏ qua, 0 thất bại; bao gồm các luồng cũ và mới |
| TypeScript/Vite production build | Đạt trên host và Docker |
| Ruff cho phần Python thay đổi | Đạt |
| Prettier toàn frontend | Đạt |
| Accessibility màn hình phân tích mới | Không có lỗi serious/critical trong lượt Axe đã chạy |
| Responsive/menu mobile | Kiểm tra 390px đạt; UI cũ tiếp tục đạt ở 1440/768/390px |
| Bản Docker local | Các dịch vụ healthy; deep link, CSP, proxy API và yêu cầu đăng nhập đạt |

Các kiểm thử ghi dữ liệu chạy trên database tạm có prefix `jrn_test_`/`jrn_e2e_`, sau đó dọn database và runtime user đã tạo. Bằng chứng nằm trong [báo cáo kiểm tra](reports/exploration-ui-validation.md), [tóm tắt browser](reports/exploration-summary.json) và [smoke test Docker](reports/frontend-deployment.json).

### 10. Trạng thái dữ liệu và giới hạn còn lại

- Tại thời điểm đọc catalog database local hôm nay: có **5 tin mở, đều là seed**; `truncated=false`, `vietjobs_loaded=false`. Đây là ghi nhận tại thời điểm kiểm tra, không phải bộ đếm cập nhật tự động trong nhật ký.
- Ảnh kiểm thử có 22 tin mở vì fixture riêng gồm seed, một phần catalog công khai và tin kiểm thử phân trang; không đại diện database local hoặc bộ VietJobs.
- Chưa import VietJobs, chưa chạy ETL/analytics/similarity bằng Spark. Chưa bổ sung category, loại hợp đồng và ngôn ngữ theo dataset.
- Tìm kiếm/thống kê hiện chạy trên phần catalog đã tải. Graph giới hạn 10 kỹ năng và 5 việc liên quan; gợi ý chưa đánh giá mức thành thạo kỹ năng và chưa phân biệt trọng số kỹ năng bắt buộc/ưu tiên.
- Lương thống kê lấy trung điểm các khoảng có hai cận dương hợp lệ của catalog hiện có; không suy ra mức lương thị trường từ seed.
- `.venv` còn lỗi native extension do môi trường chuyển từ Python 3.10 sang 3.13. Backend được kiểm thử/chạy bằng Docker; browser dùng Python tương thích có sẵn và adapter QA tạm trong thư mục test-results. Chưa coi môi trường `.venv` đã sửa hoàn toàn.
- Chưa đồng bộ lại nội dung Word/PPT theo chức năng và pipeline hoàn chỉnh.

### 11. Công việc tiếp theo

Tiếp tục các task D01–D04 trong [danh sách task](tasks-chuc-nang-loi-ui.md): thiết lập Spark; profiling/tiền xử lý/chuẩn hóa VietJobs; nhập dữ liệu và graph riêng; nối UI với API dataset; tạo analytics/similarity batch, đánh giá kết quả và cập nhật Word/PPT. Các task này vẫn ở trạng thái chưa hoàn thành.

UI đã cập nhật có thể xem tại `http://localhost:5173/explore` sau khi đăng nhập.


## 2026-10-14 — Lưu quy tắc qua phiên, khảo sát raw/database và chỉnh backend/frontend

### Yêu cầu bổ sung

Người dùng yêu cầu các phiên sau, khi bắt đầu việc tiếp theo, tự ghi thêm cập nhật vào nhật ký; khảo sát database và CSV tại `DATA_/vietjobs-network/data/raw/vietjobs` trước khi chỉnh thông số/chức năng. Giữ nguyên lịch sử, seed và raw.

### Quy tắc đã lưu cho phiên tiếp theo

Tạo [AGENTS.md](../AGENTS.md) tại gốc repository: đọc nhật ký/task trước khi làm, tự bổ sung mục vào cuối nhật ký sau mỗi đợt, đính chính bằng mục mới, không ghi đè lịch sử hay secrets. Quy tắc khảo sát database/raw trước khi điều chỉnh thông số và phân biệt seed/raw/Spark cũng được ghi vào file này.

### Khảo sát và phát hiện

- Đã audit chỉ đọc 21 collection và graph hiện có; database có 6 jobs, trong đó catalog có 5 tin mở đều là seed. Snapshot có số lượng và fingerprint, không xuất nội dung hồ sơ/credentials.
- Đã đọc toàn CSV: 48.092 bản ghi, 18 cột, 16 nhóm nghề; 385 bản sao trùng đủ 18 trường sau bản đầu, còn 47.707 bản ghi duy nhất.
- `technical_skills`, `soft_skills`, `qualifications`, `benefits` là list dạng chuỗi. `languages_required` là chuỗi tách dấu phẩy; có 35.796 ô rỗng và 344 dòng mang token UNK, chưa xác định.
- 13.730 dòng lương 0/0; 1.355 dòng lương chữ khác cột số, ví dụ bản ghi #3 `9.4 - 12.0 triệu` nhưng cột số `9–12`; giữ giá trị gốc và gắn cờ.
- 2.903 dòng địa điểm có dấu phẩy; sau bỏ token lặp có 2.766 dòng thực sự nhiều địa điểm. Kinh nghiệm theo tháng được đổi bằng /12, không suy ra cấp bậc nghề nghiệp.
- CSV không cung cấp company/job_url/published_at/work_mode/level hay quan hệ người dùng/nhân viên/giới thiệu. Loại hợp đồng khác onsite/remote/hybrid.
- Đính chính báo cáo sơ bộ trong chính đợt này: profile JSON đầu tiên phân loại sai trường ngôn ngữ như list. Đã sửa parser; [profile v2](reports/vietjobs-raw-profile-2026-10-14-v2.json) là kết quả sử dụng. Báo cáo đầu được giữ, không xóa hoặc thay bằng kết quả v2.

Chi tiết quy tắc, mẫu số và kế hoạch schema ở [phân tích raw/database](phan-tich-raw-vietjobs-2026-10-14.md).

### Backend/frontend đã bổ sung và sửa

- Tạo `database/raw_vietjobs.py`: reader CSV đa dòng, hash phiên bản nguồn, index/cache trong bộ nhớ, byte offset đọc chi tiết, parse list an toàn, tách ngôn ngữ/địa điểm, gắn cờ lương và lọc/phân trang toàn file. Không ghi CSV hay import database.
- Tạo `scripts/profile_vietjobs_raw.py` và `scripts/audit_database_snapshot.py`; script báo cáo từ chối ghi đè output đã có.
- Tạo `backend/modules/exploration/raw_api.py`, `raw_schemas.py`, đăng ký router trong `backend/app.py`.
- Bổ sung các GET có xác thực: `/api/v1/exploration/raw/profile`, `/raw/jobs`, `/raw/jobs/{job_id}` và `/api/v1/exploration/policy`.
- Tạo `frontend/src/features/exploration/RawDataPage.tsx`; thêm tab `/explore/data`, thông tin nguồn/hash, chất lượng raw, bộ lọc nhóm nghề/quốc gia/địa điểm/hợp đồng/kinh nghiệm, ẩn trùng và xem đủ 18 trường.
- Chỉnh `ExplorePage.tsx`, `exploration.css`, `service.py`, `api.py`: Top-K 5/10/20/50 với giới hạn backend 50, trọng số từ policy, năm kinh nghiệm thập phân, so địa điểm bằng token chính xác và alias HCM/Hanoi. Trọng số vẫn là baseline chưa được hiệu chỉnh trên bộ đánh giá.
- Sửa checkbox và cập nhật nhiều filter liên tiếp bằng state/URL chung, giữ filter khi mở chi tiết/quay về; sửa bố cục bảng trên mobile. Cập nhật `frontend/src/lib/api.ts` cho thông báo raw unavailable và timeout riêng cho profile.
- Xuất lại `docs/api.openapi.json`/`frontend/src/lib/api.generated.ts`; thêm `tests/backend/test_raw_vietjobs.py`, kiểm tra policy/địa điểm trong `test_exploration.py`, và `frontend/e2e/raw-data.spec.ts`.
- Cập nhật `README.md`, danh sách task R01–R08 và tài liệu/bằng chứng mới. Các mục D01–D04 về Spark/import/evaluation/Word/PPT vẫn chưa hoàn thành.

### Docker và xử lý lỗi triển khai

- `compose.yaml` mount CSV ở `/data/vietjobs/VietJobs.csv` với quyền chỉ đọc; kiểm tra mount trả `RW=false`.
- Lần đọc/index đầu trong giới hạn 1 CPU/512 MiB ghi nhận 64,19 giây, peak RSS 159,06 MiB; đặt timeout riêng cho raw profile/proxy 90 giây trong UI và `frontend/nginx.conf`. Index được cache; chưa benchmark tải đồng thời.
- Build backend ban đầu timeout tải setuptools. Đã tải wheel 84.0.0 qua host, khớp checksum chính thức PyPI, lưu tại `docker/build-wheels` và sửa Dockerfile kiểm tra hash/cài build dependency offline rồi đóng gói bằng `--no-build-isolation`. Runtime dependencies vẫn theo `requirements.lock`.
- Một lượt test UI v4 đạt chức năng nhưng hậu xử lý artifact lỗi do log build PowerShell UTF-16. Đã chuyển log hỗ trợ sang UTF-8; lượt v5 chạy và dọn database/user thành công.
- Build Compose cuối đã đạt; frontend/backend/ArangoDB healthy, Nginx cấu hình hợp lệ và smoke test route/proxy/auth mới đạt. Báo cáo deployment có tên riêng, không thay báo cáo cũ.

### Kiểm tra và bảo toàn dữ liệu/lịch sử

- 9 kiểm thử backend phần thay đổi đạt, chạy lại bằng image mới cũng đạt; không cộng lượt chạy lại thành số kiểm thử duy nhất mới.
- Hồi quy toàn trình duyệt v5: 22 passed, 0 skipped, 0 flaky; gồm các luồng cũ, raw đầy đủ, bộ lọc/chi tiết, Top-K, accessibility và mobile.
- Build host/Docker, Ruff và Prettier đạt. Test ghi dữ liệu sử dụng database/user tạm đã được dọn.
- Fingerprint key/revision của 13 collection có seed khớp trước/sau. Hash CSV trong container vẫn là `85862b06fda4e814fe0c1d8622f173d189c92758345f77df16d1232d0c49d477`.
- Mục này được thêm bằng append; 12.990 byte lịch sử có trước giữ SHA-256 `6b3016faf6ce4820aa1cbd88017bf734e60d8f994dc4fa77c99041461a31cb52`. Kiểm tra prefix để bảo đảm không ghi đè phần cũ.

Bằng chứng: [báo cáo kiểm tra đợt raw](reports/raw-review-validation-2026-10-14.md), [browser v5](reports/raw-review-2026-10-14-v5-summary.json), [snapshot trước](reports/database-audit-before-raw-2026-10-14.json), [snapshot sau](reports/database-audit-after-raw-2026-10-14.json).

### Trạng thái còn lại và cách xem

UI mới: `http://localhost:5173/explore/data`, cần đăng nhập. Raw được đọc để khảo sát; gợi ý/graph nghiệp vụ cũ vẫn dùng ArangoDB/seed. Chưa chạy Spark, chưa nhập VietJobs vào ArangoDB, chưa đồng bộ Word/PPT, chưa sửa hoàn toàn `.venv` đã chuyển phiên bản Python.

Tiếp theo: chạy profiling Spark với schema rõ, chuẩn hóa/dedup có provenance, dictionary/alias, quy tắc lương/kinh nghiệm/địa điểm, graph dataset, import kiểm tra chất lượng và đánh giá ranking/similarity. Khi tiếp tục, đọc báo cáo và nhật ký này, tự append các kết quả mới.

### Ghi chú kiểm tra tài liệu cuối đợt 14/10

Khi kiểm tra liên kết cuối đợt, file ke-hoach-vietjobs-3-ngay.md được nhắc trong mục 13/10 không còn tìm thấy ở đường dẫn cũ. Giữ nguyên mục lịch sử; chưa xác định nguyên nhân file thiếu và không khôi phục thay đổi ngoài phạm vi. Các tài liệu kế hoạch tổng thể/v2 và danh sách task hiện vẫn có trong docs. Các liên kết mới của đợt raw đã được kiểm tra riêng.


## 2026-10-14 ? Qu?t nhanh dung l??ng workspace

Y?u c?u: x?c ??nh v? sao folder g?n 1 GB v? file/th? m?c l?n n?o kh?ng thu?c source nghi?p v?. Ch? kh?o s?t, kh?ng x?a.

- Qu?t file th??ng trong workspace m?t kho?ng 1 gi?y, 24.927 file, kh?ng c? l?i truy c?p; t?ng 1.055.218.362 byte (~1,06 GB, 1.006,33 MiB). ??y l? dung l??ng n?i dung file, kh?ng ph?i allocated size tr?n ? ??a; kh?ng t?nh Docker storage ho?c ???ng d?n b?n ngo?i.
- L?n nh?t: .audit-venv 430,89 MiB, .venv 253,98 MiB, frontend/node_modules 196,90 MiB, raw VietJobs.csv 98,33 MiB, docs 20,99 MiB.
- B?n file export image trong .audit-venv chi?m 387,17 MiB: arango-image.tar 263,54; backend-image.tar 65,03; frontend-patched-image.tar 33,56; frontend-image.tar 25,04. Kh?ng t?m th?y tham chi?u c?c archive n?y trong source/Compose hi?n t?i; ?ng vi?n d?n n?u kh?ng c?n l?u image c? ?? ki?m to?n/kh?i ph?c.
- Hai venv v? node_modules chi?m 87,62% t?ng. ??y l? m?i tr??ng/dependency v? artifact ph? tr?, kh?ng ph?i code nghi?p v?; node_modules c?n cho build/test frontend, .venv c?n ???c QA d?ng m?t ph?n. C?c th? vi?n PDF/plot trong .venv ph?c v? script l?m b?o c?o, kh?ng k?t lu?n l? file r?c.
- N?u lo?i hai venv v? node_modules kh?i g?i chia s?, ph?n c?n l?i kho?ng 124,57 MiB, ch? y?u CSV v? t?i li?u. Gi? raw/seed/t?i li?u; kh?ng d?n backup ho?c Docker volume.
- DATA_/vietjobs-network/.venv l? junction t?i D:/vietjobs_env. Kh?ng ?i theo junction trong l??t qu?t ?? tr?nh ??m ngo?i workspace; kh?ng s?a junction ho?c m?i tr??ng ??ch.

B?ng ch?ng: [b?o c?o dung l??ng](reports/workspace-size-2026-10-14.json). Kh?ng thay backend/frontend ho?c d? li?u, kh?ng ch?y l?i ki?m th? v? ch? qu?t metadata file v? ghi b?o c?o. M?c n?y ???c append v? x?c nh?n ph?n nh?t k? tr??c gi? nguy?n.


## 2026-10-14 — Đính chính cách hiển thị nhật ký dung lượng và tạo gói chia sẻ

Yêu cầu: thư mục dự án quá lớn nên không gửi được qua Zalo. Tạo bản ZIP gọn để
chia sẻ source, CSV và tài liệu, giữ nguyên các file/môi trường gốc trên máy.

### Đính chính mục quét dung lượng ngay phía trên

Mục quét dung lượng ngày 14/10 bị mất dấu tiếng Việt khi ghi qua pipeline shell.
Giữ nguyên mục cũ; bổ sung lại kết luận: tổng file trong workspace lúc quét là
1.055.218.362 byte (1.006,33 MiB). `.audit-venv` 430,89 MiB, `.venv` 253,98 MiB,
`frontend/node_modules` 196,90 MiB; bốn archive image Docker trong `.audit-venv`
chiếm 387,17 MiB. CSV raw 98,33 MiB và tài liệu 20,99 MiB là nội dung dự án cần
giữ. Junction `DATA_/vietjobs-network/.venv` trỏ ngoài workspace được bỏ qua.
Không xóa file, không dọn volume hoặc môi trường đích của junction. Báo cáo
`docs/reports/workspace-size-2026-10-14.json` giữ số liệu kiểm tra ban đầu.

### Bổ sung và kiểm tra gói chia sẻ

- Thêm `scripts/package_project.py`: đóng gói source/raw/docs, loại venv,
  `node_modules`, cache/build, backup, archive Docker, metadata riêng và `.env`
  thật; không đi theo junction. Giữ `.env.example`, lockfile và wheel setuptools
  phục vụ Docker build. Không sửa backend/frontend, seed hoặc CSV.
- Thêm `docs/huong-dan-chay-ban-chia-se.md`: giải nén, cài dependencies, sinh
  secrets mới, khởi động ArangoDB, bootstrap/seed chỉ trên máy mới, provision API
  và chạy frontend/backend. Nêu rõ bản source không chuyển database/tài khoản/
  volume hiện có; Word/PPT ngoài workspace không nằm trong gói.
- Đã chạy đóng gói lần đầu: 461 file, ZIP 38.676.064 byte (36,88 MiB), so với
  workspace ban đầu khoảng 1,06 GB. Gói cuối được tạo lại sau khi thêm mục nhật
  ký này; dung lượng/hash chính xác của gói cuối nằm trong báo cáo cạnh ZIP.
- Đã kiểm tra CRC toàn ZIP, CSV trong ZIP khớp nguồn với SHA-256
  `85862b06fda4e814fe0c1d8622f173d189c92758345f77df16d1232d0c49d477`.
  Đã đối chiếu giá trị password/secret/token hiện có trong `.env` với các file
  văn bản được đóng gói, không phát hiện giá trị trùng; không ghi giá trị ra log.
- ZIP và báo cáo nằm tại `dist/share/bigdata-source-vietjobs-2026-10-14.zip`
  và file `.json` cùng tên. Script không đưa chính thư mục output vào ZIP.
  Nhật ký được append và kiểm tra nội dung cũ là tiền tố nguyên vẹn.

Giới hạn: chưa cài lại toàn hệ thống trên máy người nhận, chưa gửi/upload lên
Zalo và chưa kiểm chứng giới hạn file của tài khoản Zalo. Không cần chạy lại
kiểm thử nghiệp vụ vì không thay đổi app/database. Các mục Spark/import/
evaluation/Word/PPT vẫn còn chờ theo danh sách task.


## 2026-10-14 — Chuẩn bị đưa dự án lên GitHub BigData

Yêu cầu: chuyển sang chia sẻ qua GitHub, repository đích do người dùng cung cấp
là `https://github.com/LeDongPhuoc/BigData.git`.

- Đã kiểm tra remote chưa có refs/commit, khởi tạo Git trong workspace với
  nhánh `main` và remote `origin`; chưa ghi nhận push thành công ở mục này.
- Bổ sung `.gitignore` để loại `.env.*` thật, metadata riêng, archive image và
  private-key files, giữ `.env.example`. Các venv, node_modules, backup, output
  ZIP và cache vốn đã bị loại. Không xóa những file này trên máy.
- Thêm `.gitattributes` giữ CSV raw ở dạng byte nguyên vẹn; đặt cấu hình Git
  `core.autocrlf=false` riêng repository. Khác biệt ownership giữa sandbox và
  tài khoản Windows được xử lý bằng `safe.directory` chỉ trong từng lệnh Git,
  không thay đổi danh sách tin cậy toàn hệ thống.
- Đã kiểm tra 462 file được stage, tổng 127.306.639 byte trước mục nhật ký này:
  không có thư mục bị loại, không phát hiện giá trị secrets hiện có trong
  `.env` ở các file được stage, working files khớp index. Không ghi secrets.
- CSV 103.110.903 byte (98,33 MiB), dưới giới hạn 100 MiB/file của GitHub đã
  tra tài liệu chính thức; đưa CSV trực tiếp vào Git trong lần đầu này.
  SHA-256 CSV trong index và raw nguồn cùng là
  `85862b06fda4e814fe0c1d8622f173d189c92758345f77df16d1232d0c49d477`.
- Giữ source, seed/migration, cấu hình Docker/lockfile, raw, tài liệu và
  hướng dẫn cài lại. Không đưa database/volume/tài khoản đang chạy lên Git.

Bằng chứng chuẩn bị: `dist/share/github-prepush-2026-10-14.json` (local, không
commit). Tài liệu giới hạn file:
https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

Giới hạn: chưa ghi nhận hoàn tất push tại thời điểm thêm mục này; sẽ bổ sung
kết quả sau khi GitHub nhận commit. Không sửa app/database, không chạy lại
kiểm thử nghiệp vụ; các việc Spark/import/Word/PPT theo task vẫn còn chờ.
