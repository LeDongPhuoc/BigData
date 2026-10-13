# Khảo sát raw VietJobs và đối chiếu database — 14/10/2026

Đã đọc toàn bộ CSV và khảo sát database hiện có trước khi chỉnh backend/frontend. Đợt này triển khai đọc raw và xem dữ liệu để kiểm tra; chưa chạy pipeline Spark hoặc nhập VietJobs vào ArangoDB.

## 1. Nguồn và phạm vi

- File: `DATA_/vietjobs-network/data/raw/vietjobs/VietJobs.csv`.
- Kích thước: 103.110.903 byte; 48.092 bản ghi CSV, 18 cột. Một bản ghi có thể chứa nhiều dòng văn bản.
- SHA-256: `85862b06fda4e814fe0c1d8622f173d189c92758345f77df16d1232d0c49d477`.
- Kết quả chính thức của lần khảo sát: [profile v2](reports/vietjobs-raw-profile-2026-10-14-v2.json). Báo cáo đầu tiên vẫn được giữ để đối chiếu; nó đã phân loại sai định dạng `languages_required` là list. V2 sửa nhận diện trường này sang chuỗi phân cách bằng dấu phẩy, không coi 12.296 giá trị ngôn ngữ có nội dung là lỗi list.
- [Snapshot database trước thay đổi](reports/database-audit-before-raw-2026-10-14.json) chỉ chứa số lượng, cấu trúc và fingerprint seed; không có dữ liệu đăng nhập hay nội dung hồ sơ.

Thống kê dưới đây lấy từ file local, không thay bằng số liệu trên trang giới thiệu dataset.

## 2. Database hiện có đang chứa gì?

Database `job_referral` có 21 collection và graph `jobReferralGraph`. Tại thời điểm snapshot:

| Nhóm | Collection/số lượng | Ý nghĩa |
|---|---|---|
| Việc làm và công ty | 6 jobs, 3 companies, 6 job_at_company | 5 tin mở trong catalog, cả 5 đều là seed; 1 tin đóng |
| Kỹ năng và yêu cầu | 4 skills, 7 job_requires_skill, 7 has_skill | Dictionary kỹ năng hiện có còn nhỏ, chủ yếu phục vụ demo phần mềm |
| Người dùng và mạng lưới | 27 users, 18 connections, 12 works_at | Có tài khoản sử dụng hệ thống ngoài seed; số lượng có thể thay đổi khi người dùng thao tác |
| Nghiệp vụ | 7 referral_requests, 1 applications, 7 notifications | Dữ liệu workflow đang có được giữ lại |
| Hạ tầng | Collection auth, audit, migrations, rate limits… | Chi tiết số lượng trong snapshot; không gộp vào thống kê tuyển dụng |

VietJobs không có company/candidate/employee/referral ID, do đó chưa thể tự nối CSV vào `job_at_company`, `works_at` hay mạng lưới người dùng. Adapter raw được tách riêng; không tạo công ty hoặc quan hệ nhân viên giả để thỏa schema cũ.

## 3. Kết quả raw đáng chú ý

| Chỉ tiêu | Kết quả/diễn giải |
|---|---|
| Nhóm nghề | 16; công nghệ thông tin/kỹ thuật số có 1.906 dòng, không phải toàn dataset |
| Trùng hoàn toàn | 385 lần lặp sau bản đầu tiên; 47.707 bản ghi duy nhất theo đủ 18 trường |
| Bản ghi sai số cột | 0 |
| Thiếu technical_skills | 6.437 ô rỗng; 6.558 dòng không có item sau parse, gồm cả `[]` |
| Thiếu soft_skills | 2.641 ô rỗng; 2.799 dòng không có item sau parse |
| Thiếu languages_required | 35.796 ô rỗng; thêm 344 dòng có token `UNK`, chưa xác định ngôn ngữ |
| Thiếu working_hours | 4.982 ô rỗng |
| Thiếu requirements_text | 9 ô rỗng |
| Lương 0/0 | 13.730 dòng; không coi là thu nhập bằng 0 |
| Lương chữ/số khác nhau | 1.355 dòng theo phép đối chiếu chặt với chuỗi có nhãn `triệu` |
| Lương thiếu cận dương | 47 dòng; các cờ lương có thể chồng nhau, không cộng số cờ để lấy số dòng lỗi |
| Địa điểm có dấu phẩy | 2.903 dòng; sau bỏ token lặp còn 2.766 dòng thực sự có nhiều địa điểm |
| Kinh nghiệm | Chuyển được các giá trị hiện có sang số năm; 6 tháng = 0,5 năm, 2 tháng = 2/12 năm |
| Quốc gia | 47.957 dòng Việt Nam, 135 dòng ngoài Việt Nam; không tự lọc bỏ 135 dòng |
| Tiêu đề dài nhất | 216 ký tự; preview giữ đủ, không cắt xuống giới hạn 200 của payload tạo job cũ |

Ví dụ bản ghi #3: `salary = 9.4 - 12.0 triệu`, `salary_min = 9`, `salary_max = 12`. Bản raw được giữ nguyên và gắn cờ; chưa tự chọn một giá trị để sửa nguồn.

Theo [bài báo VietJobs, mục 3.3](https://aclanthology.org/2026.lrec-1.501.pdf), các trường lương định lượng được diễn giải theo triệu VND/tháng. Database seed hiện có dùng VND. Hai adapter giữ đơn vị rõ ràng; không đưa trực tiếp số `15` từ CSV vào formatter đang hiểu `15 VND`.

## 4. Quy tắc xử lý ở bản khảo sát

| Trường | Xử lý/hiển thị hiện tại | Quy tắc khi chuyển sang Spark/Silver |
|---|---|---|
| job_title | Giữ nguyên, tìm theo tên | Chuẩn hóa Unicode/khoảng trắng; chọn schema đủ dài, không cắt mất nội dung |
| category | Dùng đủ nhãn nguồn, UI đổi `_` thành khoảng trắng để đọc | Dictionary 16 nhóm nghề có ID ổn định |
| location, country | Giữ chuỗi gốc và token địa điểm tách dấu phẩy, bỏ token lặp | Giữ raw + danh sách địa điểm; ánh xạ địa danh có version, xử lý địa điểm nước ngoài riêng |
| qualifications, technical_skills, soft_skills, benefits | Parse list bằng `ast.literal_eval`, kiểm tra list gồm chuỗi; không dùng `eval` | Parse an toàn, quarantine lỗi và lưu trạng thái thiếu; không gộp kỹ năng mềm vào chuyên môn |
| languages_required | Tách dấu phẩy, bỏ token lặp; `UNK` là chưa xác định | Dictionary ngôn ngữ và cờ unknown, không suy ra không cần ngoại ngữ từ ô rỗng |
| experience_required | Giữ chữ; đổi tháng /12, “Không yêu cầu” = 0, chưa parse được = null | Lưu tháng/năm và cách parse; không suy ra seniority từ số năm |
| salary, salary_min/max/avg | Giữ chữ và số gốc, gắn cờ 0/0, thiếu cận, mâu thuẫn | Dùng Decimal, thống nhất đơn vị; quy tắc giải quyết mâu thuẫn có provenance; không dùng salary_avg dạng chuỗi như số mặc định |
| contract_type | Bộ lọc riêng trên nhãn nguyên gốc, gồm cả nhãn nhiều loại | Quan hệ hợp đồng có thể nhiều giá trị; không map sang onsite/remote/hybrid |
| working_hours | Giữ văn bản | Chưa có quy tắc suy ra hình thức làm việc; không mặc định onsite |
| description, requirements_text | Chi tiết đọc đúng bản ghi đa dòng, giữ xuống dòng | Làm sạch có kiểm soát, giữ văn bản nguồn và cờ thiếu |
| company/job_url/published_at/work_mode/level | Không có trong CSV; UI thông báo thiếu | Nullable/không xác định, không tạo giá trị giả |

Parse an toàn và biến đổi tối thiểu trong adapter preview không được gọi là pipeline Spark đã hoàn thành. File CSV không bị thay đổi; byte offset chỉ giúp đọc lại bản ghi chi tiết khi cần.

## 5. Backend/frontend đã điều chỉnh theo khảo sát

- Thêm tab `/explore/data`: tổng quan toàn CSV, độ thiếu dữ liệu, nhóm nghề, hợp đồng, cờ chất lượng, số lượng database hiện có và nguồn có hash.
- Tìm/lọc/phân trang server trên toàn file: tên/nhóm nghề/kỹ năng, nhóm nghề, quốc gia, token địa điểm, nhãn hợp đồng, kinh nghiệm tối đa. Không dùng giới hạn 1.000 tin của catalog seed cho raw.
- Mặc định ẩn bản sao trùng đủ 18 trường; người dùng có thể bật lại để xem đầy đủ 48.092 dòng. Không xóa bản trùng trong CSV.
- Chi tiết cho đọc đủ 18 trường, tách kỹ năng chuyên môn/mềm/ngôn ngữ, hiện lương chữ và số cạnh nhau và chỉ rõ tin lịch sử chưa xác minh còn tuyển.
- ID preview gồm prefix hash file + thứ tự bản ghi, để không trả nhầm chi tiết khi nguồn được thay bằng phiên bản khác. ID này chưa phải ID nghiệp vụ cuối cùng của Silver/ArangoDB.
- Gợi ý catalog hiện có có Top-K 5/10/20/50, giới hạn backend 50. Trọng số được lấy từ API policy, thống nhất với backend; vẫn là baseline chưa được hiệu chỉnh bằng bộ đánh giá.
- Địa điểm trong gợi ý chuyển từ so chuỗi con sang so token chính xác, hỗ trợ alias HCM/Hanoi; tránh kết luận `Nam` khớp `Việt Nam`.
- Ô năm kinh nghiệm cho phép số thập phân phù hợp phép chuyển từ tháng; thiếu yêu cầu vẫn không được coi là khớp.
- Giữ các chức năng cũ, nguồn seed và các route hiện có.

API bổ sung: `GET /api/v1/exploration/policy`, `GET /api/v1/exploration/raw/profile`, `GET /api/v1/exploration/raw/jobs`, `GET /api/v1/exploration/raw/jobs/{job_id}`. Tất cả yêu cầu đăng nhập. Docker mount CSV tại `/data/vietjobs/VietJobs.csv` với quyền chỉ đọc; host có thể dùng `VIETJOBS_RAW_PATH` hoặc đường dẫn mặc định của repository.

## 6. Thống kê lương và hiệu năng có giới hạn rõ

Median midpoint = 13,5 triệu trên 33.000 dòng raw có hai cận dương, đúng thứ tự và không có cờ lương; loại 15.092 dòng theo chính sách này. Mẫu số vẫn gồm dòng trùng; đây là thống kê kiểm tra dữ liệu, chưa phải kết luận lương thị trường. Cờ ngôn ngữ không làm một khoảng lương bị loại.

Đọc và dựng index toàn file trong Docker giới hạn 1 CPU/512 MiB ghi nhận khoảng 64,19 giây, peak RSS 159,06 MiB trong [lượt đo v2](reports/vietjobs-raw-runtime-2026-10-14-v2.json). Index được cache trong bộ nhớ và kiểm tra size/mtime khi truy cập; lần đầu hoặc sau thay nguồn/restart phải đọc lại. Timeout raw profile/UI/proxy được đặt 90 giây, các API nghiệp vụ cũ giữ timeout hiện có. Hiệu năng này cần được cải thiện bằng các bảng/dictionary/index chuẩn bị từ pipeline Spark ở giai đoạn tiếp theo.

## 7. Tái lập và công việc tiếp theo

Profiling Python độc lập, không cần kết nối database:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/profile_vietjobs_raw.py --output docs/reports/vietjobs-raw-profile-new.json
```

Chọn tên output mới: script từ chối ghi đè báo cáo đã có. Database audit chạy bằng operator, không in secrets:

```powershell
python -m scripts.audit_database_snapshot --output docs/reports/database-audit-new.json
```

Script Spark `DATA_/vietjobs-network/src/spark/01_profile_dataset.py` đã có trong workspace và được giữ nguyên; chưa chạy nó trong đợt này. Tiếp theo cần profiling Spark với schema rõ, làm sạch/dedup có provenance, dictionary/alias, salary/experience/location rules, thiết kế graph dataset tách nghiệp vụ xã hội, import có kiểm tra và đánh giá ranking/similarity. Quy tắc tự bổ sung nhật ký qua các phiên nằm trong [AGENTS.md](../AGENTS.md).
