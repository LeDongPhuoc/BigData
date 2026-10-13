# Chạy bản chia sẻ source và VietJobs

Bản ZIP ngày 14/10/2026 chứa source backend/frontend, seed, CSV VietJobs gốc,
lockfile, tài liệu và báo cáo kiểm tra trong workspace. Giải nén rồi mở thư mục
`bigdata` chứa `compose.yaml` và `README.md`.

Môi trường Python, `node_modules`, image Docker export, backup, file `.env` và
junction không được đóng gói. Gói này không chứa database đang chạy, các tài
khoản/mật khẩu của máy gửi hoặc named volume Docker. Dữ liệu phát sinh trên máy
gửi không tự chuyển sang máy nhận; seed là dữ liệu demo có thể tạo lại từ code.
Các Word/PPT đặt ngoài workspace không nằm trong ZIP này.

## Cài trên máy mới

Chuẩn bị Python từ 3.10, Docker Desktop đang chạy Linux containers và kết nối
mạng để tải package/image. Docker build frontend tự cài Node và thư viện;
không cần chép `node_modules` từ máy gửi.

Các lệnh dưới đây dành cho thư mục giải nén mới, chưa có database dự án cùng tên.
Nếu máy nhận đã chạy dự án với Compose project `job-referral`, hãy kiểm tra
database/volume và `.env` hiện có trước khi bootstrap/seed; không reset hoặc xóa
volume. Mở PowerShell tại thư mục `bigdata`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
.venv\Scripts\python.exe scripts/init_env.py
docker compose up -d --wait arangodb
.venv\Scripts\python.exe -m database.cli bootstrap
.venv\Scripts\python.exe -m database.cli seed
.venv\Scripts\python.exe scripts/provision_runtime.py
docker compose --profile web up -d --build --wait
docker compose --profile web ps
```

`init_env.py` sinh secrets riêng trên máy nhận; không sao chép `.env.example`
thành `.env` trước bước này vì mẫu có placeholder. `provision_runtime.py` tạo
tài khoản database giới hạn quyền cho API. Không dùng thông tin đăng nhập của
máy gửi. Mở http://localhost:5173 và đăng ký tài khoản mới. API docs ở
http://localhost:8000/docs.

Kiểm tra file raw còn đúng vị trí
`DATA_/vietjobs-network/data/raw/vietjobs/VietJobs.csv`. Tab `/explore/data`
đọc CSV trực tiếp, lần đọc đầu có thể mất khoảng một phút. Các chức năng graph/
giới thiệu/gợi ý hiện dùng catalog ArangoDB/seed; chưa chạy Spark hoặc import
VietJobs vào graph. Không coi màn hình raw là kết quả pipeline Spark.

Nếu cần sửa frontend trực tiếp trên host, xem `docs/frontend.md`, cài Node theo
`frontend/package.json` rồi chạy `npm.cmd ci` trong `frontend` để tạo lại thư viện.
Xem `README.md`, `docs/testing.md` và nhật ký cho trạng thái/giới hạn hiện tại.

## Tạo lại ZIP gọn

```powershell
python scripts/package_project.py
```

Script cần Python từ 3.11 cho bước hash; tạo ZIP và báo cáo kiểm tra tại
`dist/share`. Không sửa source/raw/database, không đi theo junction, không đóng
gói `.env` thật. Có kiểm tra CRC toàn ZIP, hash CSV và đối chiếu secrets hiện có
trong `.env` với các file văn bản được chọn. Đây không phải bản backup database.

Lượt đóng gói này chưa thử cài toàn bộ ứng dụng trên máy nhận; các bằng chứng
kiểm thử app trước đó nằm trong `docs/reports` và có phạm vi riêng.
