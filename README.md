# Job Referral Network

React/TypeScript frontend theo feature, FastAPI modular monolith, Python ≥3.10,
ArangoDB 3.12.12. Đăng nhập, hồ sơ, tìm việc, mạng lưới, đường giới thiệu và
workflow giới thiệu kết nối API/database thật.

Đã bổ sung [khám phá việc làm](http://localhost:5173/explore): tìm kiếm/chi tiết,
gợi ý bằng hồ sơ thử nghiệm, kỹ năng còn thiếu, việc tương tự, graph kỹ năng và
thống kê catalog hiện có. Giữ các chức năng cũ và seed; chưa nhập VietJobs/chạy
Spark trong đợt xây UI này. Xem [task và cách thử](docs/tasks-chuc-nang-loi-ui.md).

Tab [Dữ liệu VietJobs](http://localhost:5173/explore/data) đọc CSV local chỉ để
khảo sát và xem bản ghi gốc: chất lượng dữ liệu, lọc/phân trang toàn file và chi
tiết 18 trường. Nguồn này tách khỏi catalog seed; chưa import ArangoDB hoặc xử lý
Spark. Lần đọc đầu có thể mất khoảng một phút. Xem
[phân tích raw](docs/phan-tich-raw-vietjobs-2026-10-14.md) và
[nhật ký bổ sung](docs/nhat-ky-chinh-sua.md). Hướng dẫn cho phiên làm việc tiếp theo
nằm trong [AGENTS.md](AGENTS.md).

Chạy từ thư mục repository bằng PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
.venv\Scripts\python.exe scripts/init_env.py
docker compose up -d --wait arangodb
.venv\Scripts\python.exe -m database.cli bootstrap
.venv\Scripts\python.exe -m database.cli seed
.venv\Scripts\python.exe scripts/provision_runtime.py
docker compose --profile api up -d --build backend
```

Chờ ArangoDB healthy trước khi bootstrap. Compose giữ database bằng named volume;
bootstrap lặp lại giữ dữ liệu. `.env` lưu secrets ngẫu nhiên và bị loại khỏi Git/image.
`ARANGO_*` phục vụ migrations/operator; `APP_ARANGO_*` phục vụ HTTP runtime với
quyền collection và không có quyền DDL. Có thể chạy backend trên host:

```powershell
.venv\Scripts\uvicorn.exe backend.app:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

API docs: http://127.0.0.1:8000/docs. Readiness: `/health/ready`.
Chạy frontend cùng backend bằng `docker compose --profile web up -d --build --wait`.
Mở http://127.0.0.1:5173 và đăng ký tài khoản trong giao diện. Xem
[frontend/features/kiểm thử](docs/frontend.md) để chạy Vite hoặc browser tests.
Tạo admin bằng operator CLI; password nhập ẩn, không truyền qua command line:

```powershell
.venv\Scripts\python.exe -m backend.cli create-admin --email admin@example.com
```

Đăng ký tài khoản qua `/api/v1/auth/register`, đăng nhập qua `/auth/login`.
Các tài khoản graph demo không có password seed. Tạo company mới sẽ có owner chưa
verify; admin phải xác minh tại `/admin/companies/{company_id}/members/{user_id}/verification`
trước khi owner đăng jobs, thêm recruiters hoặc xác nhận employment.

Repository có catalog nguồn tuyển dụng công khai: KMS Technology,
Bosch Group, Grab và tài liệu kỹ năng chính thức; mỗi tin có link nguồn/thời điểm
ghi nhận. Có file catalog không đồng nghĩa database đang chạy đã import dữ liệu.
Đợt xây UI này giữ nguyên seed và chưa import VietJobs; xem nhãn nguồn trong UI.
Xem [nguồn dữ liệu và cách import](docs/public-data.md).

Giải thích kiến trúc, công nghệ và demo có bằng chứng:
[hướng dẫn demo](docs/demo-guide.md).
Chứng minh từng đóng góp của database bằng AQL, thay đổi graph và transaction:
[hướng dẫn chứng minh ArangoDB](docs/arango-proof-guide.md).

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=docs/reports/backend-integration.xml
.venv\Scripts\ruff.exe check .
```

Tests tạo database `jrn_test_<uuid>` riêng, kết nối ArangoDB thật, rồi dọn đúng
database đã tạo. Không skip khi mất database; không có repository/auth mocks.
Xem [hợp đồng API](docs/api.md), [module và acceptance](docs/backend.md),
[security](docs/security.md), [kiểm thử](docs/testing.md) và
[deployment/backup](docs/deployment.md).

Kiểm toán source/database/API/frontend/Docker:
[security review và bằng chứng thực tế](docs/reports/security-review-2026-10-11.md).
