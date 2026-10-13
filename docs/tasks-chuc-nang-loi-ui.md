# Task xây dựng chức năng lõi — UI trước, Spark sau

Phạm vi được yêu cầu: giữ seed/database/nghiệp vụ cũ; xây trải nghiệm khai thác việc làm có thao tác thực trên dữ liệu hiện có. Chưa tải/import VietJobs hoặc chạy Spark trong giai đoạn này.

## Chức năng hiện có được giữ lại

Không thay seed, collection, API hoặc đường dẫn nghiệp vụ cũ. Các chức năng sau tiếp tục sử dụng backend và giao diện hiện có:

| Nghiệp vụ | Backend hiện có | Giao diện |
|---|---|---|
| Tài khoản, đăng nhập, đăng xuất, refresh phiên | `backend/modules/auth` | `/login`, `/register` |
| Hồ sơ, kỹ năng và quyền riêng tư | `profiles`, `users`, `skills` | `/profile`, `/profile/privacy`, `/people/:userId` |
| Catalog việc làm, lọc, chi tiết, đối chiếu hồ sơ đã lưu | `jobs`, `matching` | `/jobs`, `/jobs/:jobId`, dashboard |
| Kết nối và mạng lưới người dùng | `connections`, `graph` | `/network` |
| Tìm đường giới thiệu tới công ty tuyển dụng | `graph` | `/jobs/:jobId/paths` |
| Tạo, xử lý và theo dõi yêu cầu giới thiệu | `referrals` | `/referrals`, `/referrals/:referralId`, `/jobs/:jobId/referral` |
| Thông báo | `notifications` | `/notifications` |
| Công ty, tuyển dụng, ứng tuyển và audit theo quyền hiện có | `companies`, `applications`, `audit`, `admin` | Giữ các thao tác đã có; chưa xây thêm trang quản trị riêng |

Tên module viết ngắn trong bảng nằm dưới `backend/modules/`. Gợi ý theo hồ sơ đã lưu vẫn nằm trong nghiệp vụ cũ. Form hồ sơ thử nghiệm mới dùng kỹ năng tự chọn để xem cách đối chiếu; không thay thuật toán hoặc hồ sơ đã lưu của luồng cũ.

## Danh sách công việc bổ sung

- [x] T01 — Không gian khám phá riêng, điều hướng tới tổng quan/tìm kiếm/gợi ý/graph/analytics; giữ route cũ.
- [x] T02 — API đọc catalog đang hoạt động có kỹ năng và metadata nguồn, không ghi database.
- [x] T03 — Tổng quan với số liệu thực và nhãn nguồn seed/công khai/nội bộ; trạng thái VietJobs chưa nhập.
- [x] T04 — Tìm việc và chi tiết: từ khóa, địa điểm, kỹ năng, hình thức; reset và empty/error/loading.
- [x] T05 — Form hồ sơ thử nghiệm; Top-K có điểm thành phần, độ đầy đủ dữ liệu và Skill Gap, không lưu đè hồ sơ.
- [x] T06 — Việc tương tự theo Jaccard kỹ năng, có điểm/kỹ năng chung và empty state.
- [x] T07 — Graph việc làm–kỹ năng–địa điểm từ catalog API, chọn job và điều hướng chi tiết.
- [x] T08 — Analytics trên dữ liệu hiện có: kỹ năng, địa điểm, hình thức, kinh nghiệm và lương; mẫu số rõ.
- [x] T09 — Responsive UI, keyboard/form labels; giữ đăng nhập/quyền runtime hiện có.
- [x] T10 — Kiểm thử API với database riêng, build TypeScript, browser flows; khởi động bản mới trên Docker local.

Kết quả: 92 kiểm thử backend đạt; 21 kiểm thử trình duyệt đạt; TypeScript/Vite build, Ruff và Prettier đạt. Docker frontend/backend/ArangoDB healthy; route mới và proxy đã kiểm tra trên bản đóng gói. Catalog thực đang có 5 tin mở, đều là seed. Chi tiết bằng chứng và giới hạn ở [báo cáo kiểm tra](reports/exploration-ui-validation.md).

## Ranh giới dữ liệu

Giai đoạn này dùng API/database hiện có, chủ yếu seed. Không gọi đây là kết quả Spark hay số liệu VietJobs. Không tạo company/category/employee giả. Các endpoint mới có xác thực như ứng dụng hiện tại. Hồ sơ thử nghiệm chỉ phục vụ tính điểm tạm thời.

## Cách xem và thử giao diện

1. Mở `http://localhost:5173`, đăng nhập bằng tài khoản của bạn.
2. Chọn **Khám phá việc làm** trên thanh điều hướng hoặc mở `http://localhost:5173/explore`.
3. Trong **Tìm việc**, thử từ khóa `Backend`, lọc kỹ năng `python`, mở một tin seed.
4. Xem kỹ năng yêu cầu và các việc tương tự; điểm Jaccard = số kỹ năng chung / số kỹ năng khác nhau của hai tin.
5. Trong **Gợi ý & kỹ năng**, chọn `python`, bấm **Xem gợi ý phù hợp**, xem điểm thành phần và các kỹ năng chưa khai báo. Form này không lưu hồ sơ.
6. Trong **Khám phá graph**, chọn công việc trung tâm, kéo node, zoom/pan và mở việc liên quan.
7. Trong **Phân tích**, đổi phạm vi địa điểm và xem mẫu số tính lương, số tin có/thiếu kỹ năng.
8. Các chức năng mạng lưới/giới thiệu/hồ sơ cũ vẫn nằm trên cùng thanh điều hướng.

## Luồng dữ liệu và giới hạn bản UI

`ArangoDB hiện có → API catalog có xác thực → React Query → tìm kiếm/chi tiết/graph/thống kê`.

`Form kỹ năng tạm thời → POST recommendations → tính điểm trong backend → điểm thành phần + coverage + kỹ năng khớp/còn thiếu`.

API mới nằm trong `backend/modules/exploration`; UI nằm trong `frontend/src/features/exploration`. Ba endpoint được ghi trong OpenAPI và frontend dùng kiểu sinh từ OpenAPI:

- `GET /api/v1/exploration/catalog`.
- `GET /api/v1/exploration/jobs/{job_id}/similar`.
- `POST /api/v1/exploration/recommendations`.

Catalog gồm tin `open` có công ty `active` và kỹ năng `active`. Giới hạn 1.000 tin theo key; nếu vượt giới hạn, UI thông báo phạm vi đã tải. Bộ lọc/thống kê/graph chạy trên phạm vi này, không tuyên bố đã tối ưu cho 48.092 tin VietJobs.

Gợi ý tạm dùng trọng số kỹ năng 50%, kinh nghiệm 20%, địa điểm 20%, hình thức 10%; chỉ đưa tiêu chí người dùng chọn vào mẫu số. Dữ liệu thiếu không được coi là đạt yêu cầu. `Coverage` là tỷ lệ trọng số có dữ liệu để đối chiếu. Điểm xếp hạng là tổng đóng góp / tổng trọng số được chọn; điểm đã biết là tổng đóng góp / trọng số có dữ liệu. Điểm không phải xác suất được tuyển. Chưa đánh giá mức thành thạo hay suy luận kỹ năng từ CV.

Kỹ năng yêu cầu và kỹ năng ưu tiên đều tham gia đối chiếu như nhau trong bản thử này; chưa phân biệt mức độ quan trọng. Graph giới hạn 10 kỹ năng và 5 việc liên quan. Lương trung bình là trung bình trung điểm của các khoảng có hai cận dương hợp lệ trong database hiện có, đơn vị VND; không suy ra lương thị trường từ seed.

## Giai đoạn tiếp theo, sau review UI

- [ ] D01 — Thiết lập và chạy Spark profiling/ETL VietJobs.
- [ ] D02 — Nhập dataset/graph riêng, thêm category/contract/language filters theo schema nguồn.
- [ ] D03 — Thay adapter seed bằng dataset API; giữ cùng các luồng UI.
- [ ] D04 — Analytics/similarity batch Spark, đo recall/ranking và đồng bộ Word/PPT.

Các trạng thái được cập nhật sau khi chức năng được xây và kiểm tra, không đánh dấu hoàn thành chỉ vì có màn hình.

## Bổ sung 14/10/2026 — Đối chiếu database và khảo sát raw

Phạm vi bổ sung theo yêu cầu mới: xem toàn bộ database/CSV trước khi điều chỉnh chức năng; tự ghi thêm nhật ký qua các phiên làm việc. Các mục D01–D04 về Spark/import/evaluation/Word/PPT ở trên vẫn chưa hoàn thành.

- [x] R01 — Lưu hướng dẫn tiếp tục công việc và tự bổ sung nhật ký trong `AGENTS.md`.
- [x] R02 — Snapshot chỉ đọc 21 collection/graph, lưu số lượng và fingerprint seed.
- [x] R03 — Profiling toàn bộ raw 48.092 dòng/18 cột; hash, trùng, thiếu, dạng list/ngôn ngữ, lương và kinh nghiệm.
- [x] R04 — API raw có xác thực: profile, bộ lọc/phân trang toàn file, đọc chi tiết đủ 18 trường; không import database.
- [x] R05 — Tab `/explore/data`: thống kê raw, quality flags, bộ lọc đúng category/contract/country/location/experience, ẩn trùng và xem bản ghi nguồn.
- [x] R06 — Đồng bộ policy gợi ý, Top-K 5/10/20/50, năm kinh nghiệm thập phân và so khớp token địa điểm.
- [x] R07 — Hoàn tất kiểm tra hồi quy UI, build/format và cập nhật bằng chứng kiểm tra đợt raw.
- [x] R08 — Cập nhật Docker với CSV mount chỉ đọc; kiểm tra seed/hash raw không đổi và bổ sung nhật ký.

Đã có [báo cáo raw và điều chỉnh chức năng](phan-tich-raw-vietjobs-2026-10-14.md). Tab raw tách khỏi catalog seed, chưa có pipeline Spark; gợi ý/graph nghiệp vụ cũ vẫn dùng ArangoDB hiện có. Script Spark đã có trong `DATA_` được giữ nguyên, chưa chạy trong đợt này.

Bằng chứng đợt raw: 9 kiểm thử backend cho phần thay đổi và 22 kiểm thử UI đạt, build/lint/format đạt; Docker healthy, CSV mount `RW=false`, hash raw không đổi và fingerprint seed của 13 collection giữ nguyên. Xem [kiểm tra raw/UI](reports/raw-review-validation-2026-10-14.md). Nhật ký được bổ sung ở cuối và kiểm tra prefix lịch sử nguyên vẹn.
