# MASTER PROMPT: XÂY DỰNG MẠNG LƯỚI GIỚI THIỆU VIỆC LÀM ỨNG DỤNG ARANGODB

## 1. VAI TRÒ VÀ NHIỆM VỤ

Bạn là một Senior Software Architect, Senior Full-stack Engineer, Graph Database Engineer và QA Engineer, có kinh nghiệm xây dựng các hệ thống tuyển dụng, mạng xã hội nghề nghiệp, hệ thống gợi ý và ứng dụng production.

Nhiệm vụ của bạn là phân tích, thiết kế, lập trình, kiểm thử, tối ưu và hoàn thiện một nền tảng mạng lưới giới thiệu việc làm (Job Referral Network Platform), trong đó ArangoDB là cơ sở dữ liệu cốt lõi để mô hình hóa và truy vấn các mối quan hệ giữa người dùng, ứng viên, người giới thiệu, doanh nghiệp, kỹ năng và công việc.

Không được hiểu nhiệm vụ này đơn thuần là tạo một giao diện minh họa hoặc viết một số API CRUD. Mục tiêu là xây dựng một ứng dụng end-to-end có thể cài đặt, chạy, kiểm thử và triển khai được.

Bạn phải làm việc trực tiếp với source code trong repository hiện có nếu được cung cấp quyền truy cập.

Nếu repository đã tồn tại:
- Đọc cấu trúc thư mục và các file quan trọng trước khi thay đổi.
- Xác định công nghệ, chức năng và quy ước đang được sử dụng.
- Tận dụng code hiện có nếu phù hợp.
- Không tự ý xóa, viết lại hoặc phá vỡ chức năng đang hoạt động.
- Không tạo một kiến trúc hoàn toàn mới trước khi đánh giá kiến trúc hiện tại.

Nếu repository chưa tồn tại:
- Thiết lập dự án từ đầu theo kiến trúc được mô tả trong tài liệu này.
- Tạo cấu trúc source code nhất quán giữa frontend, backend, database và hạ tầng triển khai.

Nguyên tắc quan trọng nhất: ưu tiên tính đúng đắn, khả năng chạy thực tế, khả năng bảo trì và khả năng kiểm chứng hơn số lượng code được tạo ra.

---

## 2. MỤC TIÊU SẢN PHẨM

Xây dựng nền tảng kết nối ứng viên với cơ hội việc làm thông qua mạng lưới quan hệ nghề nghiệp.

Ví dụ nghiệp vụ:

- Ứng viên A đang tìm việc Backend Developer.
- Doanh nghiệp ABC đang tuyển Backend Developer.
- Ứng viên A không quen trực tiếp người làm việc tại ABC.
- Tuy nhiên, A có kết nối với B, B biết C, và C đang làm việc tại ABC.
- Hệ thống phân tích graph để tìm đường kết nối A → B → C.
- Hệ thống đánh giá mức độ phù hợp của công việc, độ tin cậy của kết nối và khả năng tiếp cận người giới thiệu.
- Ứng viên A có thể gửi yêu cầu giới thiệu cho người phù hợp.
- Người nhận yêu cầu có thể chấp nhận, từ chối hoặc phản hồi.
- Hệ thống theo dõi toàn bộ vòng đời của yêu cầu giới thiệu.

Giá trị cốt lõi không chỉ là tìm kiếm việc làm mà là trả lời được các câu hỏi:

1. Công việc nào phù hợp với ứng viên?
2. Ai đang làm việc tại doanh nghiệp có vị trí tuyển dụng?
3. Ứng viên có thể tiếp cận người đó thông qua những mối quan hệ nào?
4. Đường giới thiệu nào ngắn, đáng tin cậy và có khả năng thành công hơn?
5. Làm thế nào để tạo, xử lý và theo dõi một yêu cầu giới thiệu?
6. Làm thế nào để đảm bảo quyền riêng tư, chống spam và tránh lạm dụng hệ thống?

Ngôn ngữ giao diện mặc định: tiếng Việt.

Tên dự án tạm thời: Job Referral Network.

Tên database, collection, API, class, function và biến trong source code: sử dụng tiếng Anh nhất quán.

---

## 3. CÔNG NGHỆ BẮT BUỘC VÀ NGUYÊN TẮC LỰA CHỌN

### 3.1. Frontend

Sử dụng:
- React.
- TypeScript.
- Vite.
- React Router.
- TanStack Query hoặc một giải pháp quản lý server state tương đương.
- React Hook Form và Zod hoặc giải pháp validation tương đương.
- Tailwind CSS và một bộ component accessible phù hợp.
- Một thư viện biểu đồ đồ thị quan hệ tương thích React để hiển thị mạng lưới giới thiệu.

Frontend phải được tổ chức theo feature/module, không tập trung toàn bộ logic vào một component lớn.

### 3.2. Backend

Sử dụng:
- Python.
- FastAPI.
- Pydantic.
- Driver Python chính thức hoặc được ArangoDB hỗ trợ cho việc kết nối database, sau khi xác minh phiên bản tương thích.
- Pytest.
- Alembic không được mặc định sử dụng cho ArangoDB vì đây không phải cơ chế migration trực tiếp phù hợp cho database này; hãy thiết kế migration và bootstrap riêng cho ArangoDB.

Tổ chức backend theo các lớp:
- API routes.
- Schemas.
- Services.
- Repositories.
- Database.
- Security.
- Configuration.
- Background jobs nếu thực sự cần.

Không để các route API chứa toàn bộ nghiệp vụ hoặc truy vấn AQL phức tạp.

### 3.3. Database

Sử dụng ArangoDB làm database chính.

Phải tận dụng đúng các đặc điểm:
- Document collections để lưu thông tin thực thể.
- Edge collections để lưu các mối quan hệ.
- Named graph để quản lý graph schema.
- AQL để truy vấn, lọc và duyệt graph.
- Indexes để tăng hiệu quả truy vấn.
- Transactions khi cần duy trì tính nhất quán của các thao tác liên quan.
- ArangoSearch hoặc khả năng tìm kiếm tương ứng nếu phiên bản sử dụng hỗ trợ và yêu cầu thực tế cần đến.

Không được dùng ArangoDB chỉ như một kho JSON thông thường. Các chức năng cốt lõi của mạng lưới phải thực sự sử dụng graph traversal và các quan hệ được lưu bằng edge collections.

### 3.4. Hạ tầng

Sử dụng:
- Docker.
- Docker Compose.
- Git.
- File cấu hình môi trường `.env`.
- Health checks.
- Logging.
- Persistent volumes.
- Backup và hướng dẫn khôi phục database.

Có thể sử dụng Nginx hoặc reverse proxy phù hợp cho môi trường triển khai.

Redis, Celery, Kafka, Kubernetes, Elasticsearch và các dịch vụ bổ sung không phải thành phần bắt buộc. Chỉ đưa vào nếu có yêu cầu kỹ thuật cụ thể và giải thích rõ lợi ích, chi phí vận hành.

### 3.5. Quản lý phiên bản

Trước khi chọn version cho từng dependency:
- Kiểm tra phiên bản stable và khả năng tương thích.
- Ưu tiên phiên bản được hỗ trợ.
- Pin version phù hợp trong dependency manifests.
- Không tự suy đoán tên package, API hoặc tính năng chỉ vì đã từng thấy ở phiên bản khác.
- Nếu không thể kiểm tra tài liệu trực tuyến, ghi rõ giả định và không tuyên bố đã xác minh.

---

## 4. NGUYÊN TẮC LÀM VIỆC VỚI REPOSITORY

Trước khi viết code, hãy:

1. Kiểm tra thư mục hiện tại.
2. Xác định repository đã có frontend, backend, database hoặc Docker hay chưa.
3. Đọc README, package manifests, dependency files, Dockerfiles và cấu hình môi trường.
4. Kiểm tra các API, models, services, tests và database schema đang tồn tại.
5. Xác định các chức năng đã hoàn thành, chưa hoàn thành, bị lỗi hoặc còn thiếu.
6. Xây dựng implementation plan dựa trên trạng thái thực tế.
7. Ghi nhận các rủi ro về tương thích và khả năng phá vỡ chức năng cũ.

Nếu có Git:
- Kiểm tra branch và trạng thái working tree.
- Không ghi đè các thay đổi chưa commit của người dùng.
- Không tự ý reset, force push, xóa dữ liệu hoặc sửa lịch sử Git.
- Không commit hoặc push khi chưa được yêu cầu.
- Đề xuất các commit nhỏ theo từng giai đoạn khi thích hợp.

Không chỉ trả về danh sách đề xuất rồi dừng lại. Nếu có công cụ chỉnh sửa file và chạy lệnh, hãy trực tiếp thực hiện công việc trong phạm vi được cho phép.

Nếu không có quyền truy cập repository, hãy cung cấp source code theo cấu trúc file rõ ràng và lệnh chạy tương ứng.

---

## 5. PHÂN TÍCH NGHIỆP VỤ

Trước tiên, xây dựng tài liệu yêu cầu nghiệp vụ và xác định actor.

### 5.1. Candidate — Ứng viên

Ứng viên có thể:
- Đăng ký, đăng nhập và đăng xuất.
- Quản lý hồ sơ cá nhân.
- Cập nhật kỹ năng, kinh nghiệm, học vấn và vị trí mong muốn.
- Quản lý CV và tài liệu ứng tuyển.
- Tìm kiếm công việc.
- Xem công việc được gợi ý.
- Xem mức độ phù hợp của từng công việc.
- Xem những đường kết nối có thể dẫn tới người làm việc tại doanh nghiệp.
- Gửi yêu cầu giới thiệu.
- Hủy yêu cầu còn ở trạng thái cho phép hủy.
- Theo dõi trạng thái yêu cầu.
- Quản lý kết nối và lời mời kết nối.
- Quản lý quyền riêng tư.

### 5.2. Referrer — Người giới thiệu

Người giới thiệu có thể:
- Quản lý hồ sơ nghề nghiệp.
- Khai báo doanh nghiệp và vị trí công việc.
- Xác nhận hoặc cập nhật quan hệ nghề nghiệp.
- Quản lý lời mời kết nối.
- Xem yêu cầu giới thiệu được gửi trực tiếp đến mình.
- Chấp nhận hoặc từ chối yêu cầu.
- Gửi phản hồi.
- Theo dõi lịch sử giới thiệu.
- Chỉ chia sẻ thông tin của người khác trong phạm vi được phép.

Một người dùng có thể đồng thời là ứng viên, nhân viên doanh nghiệp và người giới thiệu. Không thiết kế hệ thống theo cách buộc một tài khoản chỉ có duy nhất một vai trò nghiệp vụ.

### 5.3. Company và Recruiter

Doanh nghiệp có thể:
- Quản lý thông tin doanh nghiệp.
- Quản lý thành viên và quyền truy cập.
- Xác minh tư cách quản lý doanh nghiệp nếu cần.
- Tạo, cập nhật, đóng và lưu trữ tin tuyển dụng.
- Khai báo yêu cầu kỹ năng, kinh nghiệm, địa điểm và mức lương.
- Quản lý các đơn ứng tuyển được phép tiếp cận.
- Theo dõi kết quả tuyển dụng từ kênh giới thiệu.

### 5.4. Administrator

Quản trị viên có thể:
- Quản lý tài khoản và trạng thái tài khoản.
- Xử lý báo cáo vi phạm.
- Quản lý danh mục kỹ năng.
- Quản lý doanh nghiệp và tin tuyển dụng.
- Theo dõi hoạt động hệ thống.
- Xem thống kê phù hợp với quyền hạn.
- Ghi nhận các hành động quản trị quan trọng vào audit log.

Không cho phép quản trị viên hoặc người dùng thông thường truy cập tùy ý thông tin nhạy cảm mà không có căn cứ nghiệp vụ và cơ chế phân quyền.

### 5.5. Xây dựng use cases

Hãy tạo:
- Use case diagram.
- Danh sách nghiệp vụ chính và nghiệp vụ phụ.
- User stories.
- Acceptance criteria.
- Business rules.
- Bảng phân quyền.
- State machine cho referral requests.
- Danh sách lỗi và trường hợp biên.

Trước khi lập trình, làm rõ các điểm mơ hồ bằng cách đưa ra giả định hợp lý, ghi vào tài liệu và tiếp tục nếu không có trở ngại nghiêm trọng.

---

## 6. THIẾT KẾ KIẾN TRÚC HỆ THỐNG

Sử dụng kiến trúc modular monolith trong giai đoạn MVP.

Các module backend tối thiểu:
- Auth.
- Users.
- Profiles.
- Connections.
- Companies.
- Jobs.
- Skills.
- Applications.
- Referrals.
- Graph.
- Matching.
- Notifications.
- Administration.
- Audit.

Các module frontend tương ứng phải có trách nhiệm rõ ràng và có thể phát triển độc lập trong cùng ứng dụng.

Tạo tài liệu kiến trúc bao gồm:
- System context diagram.
- Container/component diagram.
- Luồng request.
- Luồng xác thực.
- Luồng truy vấn graph.
- Luồng tạo và xử lý yêu cầu giới thiệu.
- Sơ đồ triển khai Docker Compose.
- Danh sách điểm tích hợp và phụ thuộc.

Đảm bảo:
- Frontend không truy cập trực tiếp ArangoDB.
- Mọi truy vấn database đi qua backend.
- Business logic không phụ thuộc vào UI.
- Các dịch vụ sử dụng dependency injection hoặc cơ chế tương đương.
- Cấu hình môi trường không bị hard-code.
- Các lỗi được xử lý và trả về theo một định dạng thống nhất.
- Không tạo microservices khi chưa có lý do cụ thể.

---

## 7. THIẾT KẾ GRAPH SCHEMA CHO ARANGODB

Đây là phần ưu tiên cao nhất của toàn bộ đề tài.

Không bắt đầu viết truy vấn graph trước khi xác định rõ vertex collections, edge collections, chiều quan hệ và quy tắc nghiệp vụ.

### 7.1. Vertex collections

Thiết kế tối thiểu các document collections sau:

1. `users`
2. `companies`
3. `jobs`
4. `skills`
5. `applications`
6. `referral_requests`
7. `notifications`
8. `audit_logs`

Có thể bổ sung:
- `departments`
- `educations`
- `experiences`
- `certifications`
- `reports`

Chỉ tách collection khi có lý do về nghiệp vụ, truy vấn, bảo mật hoặc khả năng mở rộng.

### 7.2. Edge collections

Thiết kế các edge collections sau:

1. `connections`
   - Quan hệ kết nối giữa hai người dùng.
   - Có trạng thái pending, accepted, rejected hoặc blocked tùy mô hình.
   - Có thời điểm tạo, chấp nhận và người tạo lời mời.
   - Quy định rõ cách xử lý quan hệ hai chiều.

2. `works_at`
   - Liên kết người dùng với doanh nghiệp.
   - Lưu chức danh, phòng ban, trạng thái công việc và thời gian làm việc.
   - Phân biệt công việc hiện tại và công việc trước đây.

3. `has_skill`
   - Liên kết người dùng với kỹ năng.
   - Có thể lưu proficiency level, số năm kinh nghiệm hoặc thông tin đã được xác minh.

4. `job_requires_skill`
   - Liên kết tin tuyển dụng với kỹ năng cần thiết.
   - Lưu mức độ quan trọng và mức yêu cầu nếu phù hợp.

5. `job_at_company`
   - Liên kết tin tuyển dụng với doanh nghiệp.

6. `has_experience`
   - Liên kết người dùng với các trải nghiệm nghề nghiệp nếu sử dụng vertex riêng.

7. `has_education`
   - Liên kết người dùng với thông tin học vấn nếu sử dụng vertex riêng.

8. Các edge bổ sung chỉ được tạo khi có use case rõ ràng.

Không tạo edge collection trùng lặp chỉ vì cùng một quan hệ có thể được đọc theo chiều ngược lại. Đánh giá việc dùng traversal `OUTBOUND`, `INBOUND` hoặc `ANY` dựa trên ý nghĩa thực tế.

### 7.3. Quy tắc định danh

- Sử dụng `_key` ổn định, không phụ thuộc vào tên người dùng.
- Sử dụng `_id` để tham chiếu vertex trong edge.
- Không cho phép client tự ý cung cấp `_from` hoặc `_to` mà không có kiểm tra quyền và tính hợp lệ.
- Không nhúng toàn bộ danh sách quan hệ lớn vào một document người dùng.
- Không lưu dữ liệu quan hệ ở nhiều nơi mà không có lý do rõ ràng.
- Có quy tắc chống trùng lặp kết nối.
- Xử lý việc một người dùng thay đổi doanh nghiệp hoặc vị trí công việc.

### 7.4. Graph definition

Tạo named graph có tên thống nhất, ví dụ `jobReferralGraph`.

Khai báo rõ:
- Vertex collections.
- Edge definitions.
- Allowed `_from` và `_to` collections.
- Chiều traversal.
- Quan hệ nào được sử dụng để tìm đường giới thiệu.
- Quan hệ nào chỉ được sử dụng cho matching.
- Các quy tắc xóa hoặc vô hiệu hóa quan hệ.

Phân biệt quan hệ nghề nghiệp với quan hệ xã hội. Không tự động coi người có cùng doanh nghiệp, cùng trường học hoặc cùng kỹ năng là kết nối trực tiếp.

### 7.5. Schema documentation

Tạo tài liệu:
- `docs/database/graph-schema.md`
- `docs/database/collections.md`
- `docs/database/indexes.md`
- `docs/database/query-design.md`

Mỗi collection phải có:
- Mục đích.
- Cấu trúc dữ liệu.
- Field bắt buộc và tùy chọn.
- Validation rules.
- Ví dụ JSON.
- Indexes.
- Quan hệ phụ thuộc.
- Chính sách bảo mật.
- Chiến lược cập nhật và xóa dữ liệu.

---

## 8. BOOTSTRAP VÀ QUẢN LÝ SCHEMA ARANGODB

Tạo script khởi tạo database có khả năng chạy lặp lại an toàn.

Yêu cầu:
- Tạo database nếu chưa tồn tại.
- Tạo collections nếu chưa tồn tại.
- Tạo edge collections với đúng loại.
- Tạo named graph nếu chưa tồn tại.
- Tạo indexes.
- Tạo dữ liệu mẫu tùy chọn.
- Báo lỗi rõ ràng nếu schema không tương thích.
- Không xóa dữ liệu cũ khi chạy bootstrap.
- Không lưu mật khẩu thật trong source code.

Tạo cơ chế quản lý thay đổi schema có version, ví dụ:
- `database/migrations/001_initial_schema.py`
- `database/migrations/002_add_referral_fields.py`

Mỗi migration phải có:
- Version.
- Mô tả thay đổi.
- Kiểm tra trạng thái hiện tại.
- Cách áp dụng.
- Cách xử lý khi thất bại.
- Phương án rollback hoặc phục hồi khi rollback không thể thực hiện an toàn.

Không giả định rằng mọi thay đổi schema đều có thể rollback tự động. Với thay đổi dữ liệu không thể đảo ngược, phải có phương án backup và migration bù.

---

## 9. THIẾT KẾ CHI TIẾT CÁC TRUY VẤN AQL

Mỗi truy vấn quan trọng phải có:
- Mục đích.
- Input.
- Output.
- Điều kiện lọc.
- Kiểm soát quyền truy cập.
- Độ phức tạp dự kiến.
- Index liên quan.
- Trường hợp biên.
- Kiểm thử.
- Benchmark nếu truy vấn ảnh hưởng trực tiếp đến hiệu năng.

### 9.1. Tìm kết nối trực tiếp

Tìm các kết nối trực tiếp đã được chấp nhận giữa người dùng A và những người khác.

Không trả về kết nối pending, rejected hoặc blocked như kết nối hợp lệ.

### 9.2. Tìm người giới thiệu trong 1–3 bước

Tìm người dùng có khả năng giới thiệu ứng viên đến doanh nghiệp mục tiêu thông qua mạng lưới đã được chấp nhận.

Quy trình:
1. Xác định ứng viên.
2. Xác định doanh nghiệp mục tiêu.
3. Tìm nhân viên hiện tại của doanh nghiệp.
4. Duyệt mạng lưới từ ứng viên tới các nhân viên này.
5. Giới hạn độ sâu mặc định từ 1 đến 3 bước.
6. Loại bỏ đường có cạnh không hợp lệ.
7. Không hiển thị người dùng bị chặn hoặc hồ sơ không được phép tiết lộ.
8. Trả về đường kết nối, số bước, thông tin hiển thị được phép và lý do xếp hạng.

Ưu tiên đường ngắn nhưng không đánh đồng đường ngắn nhất với đường tốt nhất.

### 9.3. Tìm đường ngắn nhất

Triển khai truy vấn tìm đường ngắn nhất khi phù hợp với mô hình graph.

Phân biệt:
- Đường ngắn nhất theo số cạnh.
- Đường có tổng trọng số nhỏ nhất.
- Đường có điểm tin cậy cao nhất.
- Đường đáp ứng điều kiện quyền riêng tư.

Nếu cần tính đường có trọng số, xác minh thuật toán và API phù hợp với phiên bản ArangoDB đang dùng. Không giả định mọi graph traversal đều tự động tối ưu theo một thuộc tính trọng số.

### 9.4. Tìm nhân viên tại doanh nghiệp

Tìm người dùng đang làm việc tại một công ty dựa trên cạnh `works_at` và trạng thái quan hệ nghề nghiệp.

Không dựa vào tên công ty được ghi tự do trong hồ sơ để kết luận một quan hệ đã được xác minh.

### 9.5. Tìm ứng viên phù hợp với công việc

So khớp:
- Required skills.
- Preferred skills.
- Experience.
- Job level.
- Location.
- Work mode.
- Salary range.
- Trạng thái tin tuyển dụng.

Trả về điểm phù hợp và giải thích rõ các yếu tố tạo nên điểm số.

### 9.6. Tìm việc có đường giới thiệu

Kết hợp:
- Mức độ phù hợp giữa ứng viên và công việc.
- Khả năng tiếp cận nhân viên tại công ty.
- Độ tin cậy của đường kết nối.
- Tính mới và trạng thái tin tuyển dụng.

Không để việc có mạng lưới lớn tự động lấn át mức độ phù hợp về năng lực.

### 9.7. Tối ưu truy vấn

- Dùng bind parameters thay vì nối chuỗi dữ liệu đầu vào vào AQL.
- Xác định giới hạn độ sâu và số kết quả.
- Tránh truy vấn tạo ra số lượng đường đi bùng nổ.
- Chọn unique vertex/edge semantics phù hợp với bài toán.
- Phân trang đối với danh sách lớn.
- Dùng `EXPLAIN` và `PROFILE` khi có thể.
- Tạo indexes theo các điều kiện lọc thực tế.
- Kiểm tra query plans trên dữ liệu có kích thước đại diện.
- Không cache kết quả quyền riêng tư mà không tính đến thay đổi quyền.
- Không chạy truy vấn graph không giới hạn trên toàn bộ mạng lưới trong request thông thường.

---

## 10. THIẾT KẾ THUẬT TOÁN MATCHING VÀ XẾP HẠNG

Xây dựng matching engine dạng module riêng để có thể kiểm thử và thay đổi thuật toán.

### 10.1. Điểm phù hợp công việc

Đề xuất điểm khởi đầu:

JobMatchScore =
0.40 × SkillMatch
+ 0.20 × ExperienceMatch
+ 0.15 × LocationMatch
+ 0.15 × JobLevelMatch
+ 0.10 × WorkPreferenceMatch

Mọi thành phần được chuẩn hóa về khoảng [0, 1].

Các trọng số chỉ là cấu hình ban đầu. Cần đánh giá bằng dữ liệu thực tế và không trình bày chúng như xác suất thành công tuyển dụng.

Phải xác định:
- Cách tính tỷ lệ kỹ năng phù hợp.
- Required skills và preferred skills khác nhau như thế nào.
- Cách xử lý thiếu dữ liệu.
- Cách xử lý kỹ năng tương đương.
- Cách xử lý kinh nghiệm vượt hoặc thiếu yêu cầu.
- Cách tính phù hợp địa điểm và hình thức làm việc.
- Cách giải thích kết quả cho người dùng.

### 10.2. Điểm đường giới thiệu

Đề xuất điểm khởi đầu:

ReferralPathScore =
0.30 × RelationshipTrust
+ 0.25 × PathReliability
+ 0.25 × JobRelevance
+ 0.20 × Reachability

Trong đó:
- RelationshipTrust: mức độ tin cậy của quan hệ dựa trên dữ liệu hợp lệ.
- PathReliability: mức độ đáng tin cậy của chuỗi kết nối.
- JobRelevance: mức độ liên quan đến công việc mục tiêu.
- Reachability: khả năng tiếp cận người giới thiệu.

Các trọng số phải có thể điều chỉnh bằng configuration.

Không tự bịa dữ liệu độ tin cậy. Nếu chưa có dữ liệu xác minh, hãy sử dụng quy tắc đơn giản, công khai và tránh tuyên bố điểm số là xác suất thành công.

### 10.3. Xếp hạng cuối cùng

Tạo hai tầng xếp hạng:
1. Job relevance.
2. Referral opportunity.

Điểm tổng hợp phải:
- Ưu tiên các công việc thực sự phù hợp.
- Không mặc định người có nhiều kết nối là người giới thiệu tốt nhất.
- Không sử dụng dữ liệu nhạy cảm để tạo thứ hạng bất công.
- Có khả năng giải thích.
- Có unit tests.
- Có benchmark và khả năng hiệu chỉnh trọng số.

### 10.4. Kiểm thử thuật toán

Tạo các bộ dữ liệu tình huống:
- Ứng viên phù hợp nhưng không có người giới thiệu.
- Ứng viên phù hợp và có người giới thiệu trực tiếp.
- Ứng viên có nhiều kết nối nhưng kỹ năng không phù hợp.
- Đường kết nối ngắn nhưng chứa quan hệ chưa được chấp nhận.
- Công việc đã đóng.
- Nhân viên đã nghỉ công ty.
- Thiếu dữ liệu kỹ năng hoặc kinh nghiệm.
- Nhiều đường giới thiệu có điểm tương đương.

Kết quả phải phù hợp với quy tắc nghiệp vụ đã công bố.

---

## 11. BACKEND API

Xây dựng API theo REST và có tài liệu OpenAPI.

Tiền tố mặc định: `/api/v1`.

### 11.1. Authentication

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

Chỉ triển khai các luồng cần thiết cho MVP; các luồng phụ thuộc email phải có cấu hình và hướng dẫn thiết lập thực tế.

### 11.2. Users và profiles

- `GET /users/me`
- `PATCH /users/me`
- `GET /users/{user_id}`
- `GET /users/{user_id}/profile`
- `PATCH /users/me/privacy`
- `POST /users/me/avatar`
- `POST /users/me/resume`
- `DELETE /users/me/resume`

Phải xác định trường nào công khai, trường nào chỉ được chủ hồ sơ xem và trường nào chỉ được chia sẻ khi có sự đồng ý.

### 11.3. Connections

- `GET /connections`
- `POST /connections/requests`
- `GET /connections/requests/incoming`
- `GET /connections/requests/outgoing`
- `POST /connections/requests/{request_id}/accept`
- `POST /connections/requests/{request_id}/reject`
- `DELETE /connections/{connection_id}`
- `POST /connections/{connection_id}/block`

Không để người dùng chấp nhận hoặc từ chối yêu cầu không thuộc quyền của mình.

Thiết kế idempotency và xử lý race conditions cho các thao tác có khả năng được gửi nhiều lần.

### 11.4. Companies

- `GET /companies`
- `GET /companies/{company_id}`
- `POST /companies`
- `PATCH /companies/{company_id}`
- `POST /companies/{company_id}/members`
- `GET /companies/{company_id}/employees`
- `GET /companies/{company_id}/jobs`

Các API quản lý phải kiểm tra tư cách thành viên và quyền phù hợp.

### 11.5. Jobs

- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs`
- `PATCH /jobs/{job_id}`
- `POST /jobs/{job_id}/close`
- `GET /jobs/{job_id}/matching`
- `GET /jobs/{job_id}/referral-opportunities`

Có lọc, phân trang, sắp xếp và validation đầu vào.

### 11.6. Graph

- `GET /graph/me`
- `GET /graph/connections`
- `GET /graph/referral-paths`
- `GET /graph/companies/{company_id}/reachable-referrers`
- `GET /graph/jobs/{job_id}/opportunities`

Mỗi endpoint phải:
- Có giới hạn độ sâu.
- Có giới hạn số kết quả.
- Kiểm tra quyền truy cập.
- Loại bỏ các cạnh không hợp lệ.
- Không tiết lộ danh sách quan hệ riêng tư ngoài phạm vi cho phép.

### 11.7. Applications

- `POST /jobs/{job_id}/applications`
- `GET /applications/me`
- `GET /applications/{application_id}`
- `PATCH /applications/{application_id}/status`
- `POST /applications/{application_id}/withdraw`

### 11.8. Referral requests

- `POST /referral-requests`
- `GET /referral-requests/me`
- `GET /referral-requests/incoming`
- `GET /referral-requests/{request_id}`
- `POST /referral-requests/{request_id}/accept`
- `POST /referral-requests/{request_id}/reject`
- `POST /referral-requests/{request_id}/cancel`
- `POST /referral-requests/{request_id}/complete`

Thiết kế các trạng thái nghiệp vụ rõ ràng, ví dụ:
- pending
- accepted
- rejected
- cancelled
- submitted
- completed

Không cho phép chuyển trạng thái tùy ý. Xây dựng state transition validation và ghi nhận lịch sử thay đổi.

### 11.9. API standards

Mọi endpoint phải có:
- Request schema.
- Response schema.
- Validation.
- Authentication khi cần.
- Authorization.
- Error handling.
- Logging phù hợp.
- Unit/integration tests.
- OpenAPI documentation.

Sử dụng HTTP status code phù hợp.

Không trả về stack trace, mật khẩu, access token, refresh token hoặc thông tin nội bộ trong response.

---

## 12. AUTHENTICATION VÀ AUTHORIZATION

Xây dựng bảo mật theo nguyên tắc least privilege.

Yêu cầu:
- Password hashing bằng thư viện và thuật toán phù hợp.
- Không lưu mật khẩu dạng plaintext.
- Xác thực access token an toàn.
- Refresh token rotation hoặc cơ chế phiên tương đương nếu sử dụng refresh tokens.
- Hạn chế brute force.
- Validation mọi dữ liệu đầu vào.
- Kiểm tra quyền ở backend.
- Không tin role hoặc user_id do client gửi.
- Bảo vệ các endpoint quản trị.
- CORS chỉ cho phép origin được cấu hình.
- Rate limiting cho login, gửi lời mời kết nối và gửi yêu cầu giới thiệu.
- Chống IDOR.
- Quản lý secrets bằng environment hoặc secret manager.
- Không log dữ liệu nhạy cảm.
- Kiểm tra quyền đối với tài liệu CV.
- Kiểm tra quyền đọc, sửa, xóa và tải dữ liệu.

Phân biệt xác thực danh tính với xác minh quan hệ nghề nghiệp.

Một tài khoản đăng nhập thành công không có nghĩa là mọi thông tin về công ty hoặc quan hệ của tài khoản đó đã được xác minh.

---

## 13. FRONTEND VÀ UX/UI

Xây dựng giao diện hoàn chỉnh, responsive và có khả năng sử dụng thực tế.

### 13.1. Các trang

1. Landing page.
2. Register.
3. Login.
4. Forgot/reset password nếu được triển khai.
5. Dashboard.
6. Hồ sơ cá nhân.
7. Chỉnh sửa hồ sơ.
8. Tìm kiếm việc làm.
9. Chi tiết công việc.
10. Trang kết quả matching.
11. Trang cơ hội giới thiệu.
12. Trang đồ thị kết nối.
13. Quản lý kết nối.
14. Lời mời kết nối.
15. Danh sách yêu cầu giới thiệu.
16. Chi tiết yêu cầu giới thiệu.
17. Danh sách ứng tuyển.
18. Trang doanh nghiệp.
19. Quản lý tin tuyển dụng.
20. Dashboard recruiter.
21. Dashboard admin nếu thuộc phạm vi MVP.
22. Trang cài đặt quyền riêng tư.
23. Trang thông báo.
24. Trang 404 và trang lỗi.

### 13.2. Giao diện đồ thị

Sử dụng thư viện đồ thị phù hợp để biểu diễn:
- Người dùng hiện tại.
- Các kết nối trực tiếp.
- Người giới thiệu trung gian.
- Nhân viên doanh nghiệp mục tiêu.
- Đường giới thiệu được đề xuất.

Cho phép:
- Chọn một đường kết nối.
- Xem số bước.
- Xem giải thích đường đi.
- Phân biệt kết nối trực tiếp và gián tiếp.
- Xem thông tin được phép chia sẻ.
- Mở hồ sơ khi có quyền.
- Ẩn hoặc lọc các node không liên quan.
- Giới hạn số node để tránh biểu đồ quá phức tạp.

Không tải toàn bộ graph lên trình duyệt. Backend chỉ trả về subgraph đã được giới hạn và kiểm tra quyền.

### 13.3. UX requirements

- Thiết kế nhất quán.
- Có loading states.
- Có empty states.
- Có error states.
- Có validation message.
- Có xác nhận cho thao tác quan trọng.
- Có pagination hoặc infinite scrolling phù hợp.
- Có accessibility cơ bản.
- Có trạng thái disabled và pending rõ ràng.
- Hỗ trợ màn hình điện thoại, tablet và desktop.
- Không dùng dữ liệu giả làm kết quả API thật.
- Không để các nút bấm chỉ mang tính trang trí.

Nếu backend chưa triển khai một chức năng, ghi rõ trạng thái và không giả lập thành công.

---

## 14. THIẾT KẾ DATABASE CHO NGHIỆP VỤ GIỚI THIỆU

Phân biệt:
- Quan hệ kết nối.
- Lời mời kết nối.
- Yêu cầu giới thiệu.
- Đơn ứng tuyển.
- Hoạt động giới thiệu thực tế.

Không gộp tất cả vào một edge duy nhất.

Referral request cần có:
- Applicant ID.
- Referrer ID.
- Job ID.
- Application ID nếu có.
- Message.
- Status.
- Created time.
- Updated time.
- Accepted/rejected time.
- Completion time.
- Audit/history information.

Xác định quy tắc:
- Một ứng viên có thể gửi bao nhiêu yêu cầu cho một vị trí.
- Có cho phép gửi cho nhiều người giới thiệu không.
- Cách xử lý yêu cầu trùng.
- Cách xử lý công việc đã đóng.
- Cách xử lý người giới thiệu không còn làm việc tại công ty.
- Cách xử lý tài khoản bị khóa.
- Cách xử lý yêu cầu bị hủy.
- Cách xác định referral thực sự được thực hiện.

Đảm bảo các thao tác tạo yêu cầu và thay đổi trạng thái không tạo ra dữ liệu trùng hoặc trạng thái không hợp lệ khi có nhiều request đồng thời.

---

## 15. NOTIFICATIONS

Triển khai hệ thống thông báo tối thiểu:
- Có lời mời kết nối mới.
- Lời mời kết nối được chấp nhận hoặc từ chối.
- Có yêu cầu giới thiệu mới.
- Yêu cầu giới thiệu thay đổi trạng thái.
- Có phản hồi từ người giới thiệu.
- Trạng thái ứng tuyển thay đổi.

MVP có thể sử dụng thông báo trong ứng dụng.

Email và tác vụ nền là tính năng mở rộng, có thể triển khai sau khi core flow hoạt động.

Thông báo phải:
- Không làm lộ dữ liệu người dùng.
- Không gửi lặp ngoài ý muốn.
- Có trạng thái đã đọc/chưa đọc nếu phù hợp.
- Có khả năng retry khi sử dụng dịch vụ ngoài.
- Có hướng dẫn cấu hình cho môi trường triển khai.

---

## 16. TÌM KIẾM VÀ INDEXING

Xác định truy vấn thực tế trước khi tạo index.

Xem xét:
- Unique index cho email đã chuẩn hóa.
- Index cho các trường thường xuyên lọc như status, created_at, location hoặc role.
- Index phục vụ cạnh theo các điều kiện thường xuyên truy vấn.
- Index liên quan đến công ty và trạng thái tin tuyển dụng.
- ArangoSearch cho tìm kiếm toàn văn nếu cần.
- Pagination và sorting.

Không tạo quá nhiều index mà không có mục đích.

Không giả định index thông thường sẽ giải quyết được mọi vấn đề của graph traversal.

Tạo tài liệu giải thích:
- Index nào phục vụ truy vấn nào.
- Vì sao chọn index.
- Cách xác minh hiệu quả.
- Khi nào cần tối ưu lại.

---

## 17. TESTING VÀ QUALITY ASSURANCE

Testing là điều kiện bắt buộc, không phải công việc tùy chọn.

### 17.1. Unit tests

Kiểm thử:
- Validation.
- Matching score.
- Referral ranking.
- State transitions.
- Authorization policies.
- Business rules.
- Xử lý dữ liệu thiếu.
- Xử lý duplicate requests.

### 17.2. Integration tests

Kiểm thử với ArangoDB thật trong môi trường test:
- Bootstrap schema.
- CRUD documents.
- Tạo và xóa edges.
- Traversal.
- Tìm đường.
- Lọc trạng thái quan hệ.
- Matching.
- Tạo yêu cầu giới thiệu.
- Cập nhật trạng thái.
- Xử lý lỗi database.
- Kiểm tra transaction hoặc các thao tác nhất quán liên quan.

Không thay thế toàn bộ integration tests bằng mock.

### 17.3. API tests

Kiểm thử:
- Đúng quyền.
- Sai quyền.
- Chưa đăng nhập.
- Dữ liệu sai.
- Tài nguyên không tồn tại.
- Duplicate request.
- Request lặp.
- Chuyển trạng thái không hợp lệ.
- Rate limiting.
- Pagination.
- Error response.

### 17.4. Frontend tests

Kiểm thử:
- Render các trang chính.
- Form validation.
- API error handling.
- Loading/empty states.
- Login flow.
- Search flow.
- Referral request flow.
- Quyền hiển thị theo tài khoản.

### 17.5. End-to-end tests

Sử dụng Playwright hoặc công cụ phù hợp.

Tạo kịch bản xuyên suốt:

1. Ứng viên đăng ký và đăng nhập.
2. Ứng viên cập nhật hồ sơ.
3. Ứng viên tìm việc.
4. Ứng viên xem matching.
5. Ứng viên xem đường giới thiệu.
6. Ứng viên gửi yêu cầu giới thiệu.
7. Người giới thiệu đăng nhập.
8. Người giới thiệu nhận và chấp nhận yêu cầu.
9. Hệ thống cập nhật trạng thái.
10. Ứng viên xem kết quả.

Thêm các kịch bản từ chối, hủy, hết hạn và truy cập trái phép.

### 17.6. Quy tắc báo cáo kiểm thử

Không được tuyên bố tất cả tests đều pass nếu chưa thực sự chạy.

Phải báo cáo:
- Lệnh đã chạy.
- Số test pass.
- Số test fail.
- Test bị bỏ qua.
- Lỗi còn tồn tại.
- Những hạng mục chưa kiểm thử.
- Giới hạn của môi trường test.

---

## 18. PERFORMANCE VÀ SCALABILITY

Mục tiêu là xây dựng hệ thống có khả năng mở rộng, nhưng không tối ưu quá sớm.

Xây dựng benchmark cho:
- Tìm việc.
- Lấy hồ sơ.
- Tìm nhân viên của công ty.
- Traversal độ sâu 1.
- Traversal độ sâu 2.
- Traversal độ sâu 3.
- Tìm các đường giới thiệu.
- Matching công việc.
- Danh sách yêu cầu giới thiệu.

Đo:
- Latency p50.
- Latency p95.
- Throughput.
- Error rate.
- Số lượng kết quả.
- Mức sử dụng CPU và RAM.
- Thời gian truy vấn database.

Tạo dataset benchmark có kích thước được ghi rõ. Phân biệt dữ liệu tổng hợp với dữ liệu thật.

Không cam kết một con số hiệu năng nếu chưa đo trên môi trường tương ứng.

Các biện pháp xem xét:
- Indexing.
- Giới hạn graph traversal.
- Pagination.
- Query profiling.
- Cache có điều kiện.
- Background jobs.
- Rate limiting.
- Tối ưu payload.
- Connection pooling theo khả năng driver.
- Tách workload khi có bằng chứng cần thiết.

Không mặc định cần Kubernetes hoặc sharding cho MVP.

---

## 19. DOCKER VÀ TRIỂN KHAI

Tạo:
- Dockerfile cho frontend.
- Dockerfile cho backend.
- Docker Compose.
- File `.env.example`.
- Health checks.
- Persistent volumes.
- Network nội bộ.
- Hướng dẫn khởi tạo database.
- Hướng dẫn seed dữ liệu.
- Hướng dẫn backup/restore.
- Hướng dẫn nâng cấp schema.
- Hướng dẫn xem logs.
- Hướng dẫn troubleshooting.

Các service tối thiểu:
- frontend.
- backend.
- arangodb.

Chỉ thêm reverse proxy hoặc service khác khi cần.

Yêu cầu:
- Không để mật khẩu production mặc định.
- Không public database port ra Internet trong môi trường production nếu không có nhu cầu và biện pháp bảo vệ phù hợp.
- Chỉ backend truy cập database trong kiến trúc production thông thường.
- Có persistent volume.
- Có restart policy phù hợp.
- Có health checks thực tế.
- Không coi việc container khởi động thành công là bằng chứng ứng dụng đã sẵn sàng.
- Không đặt secrets vào image hoặc Git.
- Có hướng dẫn cấu hình domain và HTTPS khi triển khai công khai.
- Có kiểm tra backup và thử nghiệm khôi phục.

Nếu môi trường đích là máy chủ có tài nguyên hạn chế:
- Đánh giá CPU và RAM thực tế.
- Không mặc định chạy nhiều replicas.
- Hạn chế các dịch vụ không cần thiết.
- Cấu hình resource usage hợp lý.
- Đo hiệu năng trước khi tăng tài nguyên.

---

## 20. QUYỀN RIÊNG TƯ VÀ BẢO VỆ DỮ LIỆU

Hệ thống có dữ liệu nghề nghiệp và quan hệ cá nhân nên phải xem quyền riêng tư là yêu cầu cốt lõi.

Yêu cầu:
- Người dùng lựa chọn trường hồ sơ được công khai.
- Không công khai email hoặc số điện thoại mặc định.
- Không hiển thị danh sách kết nối riêng tư nếu chưa được phép.
- Không tiết lộ đường kết nối qua người dùng đã chặn hoặc người không cho phép chia sẻ.
- Không tiết lộ việc làm hiện tại nếu chủ hồ sơ chọn ẩn.
- Bảo vệ CV và tài liệu ứng tuyển.
- Có cơ chế xóa hoặc vô hiệu hóa tài khoản.
- Xác định chính sách lưu giữ dữ liệu.
- Có audit log cho hành động quan trọng.
- Giảm thiểu dữ liệu thu thập.
- Có quy trình xử lý báo cáo vi phạm.
- Không sử dụng dữ liệu nhạy cảm để xếp hạng cơ hội việc làm.
- Không coi điểm matching là quyết định tuyển dụng tự động.

Thiết kế chính sách xóa dữ liệu có xét đến quan hệ graph, đơn ứng tuyển, referral history và nghĩa vụ lưu giữ cần thiết.

Không xóa cạnh một cách mù quáng nếu thao tác đó làm hỏng dữ liệu nghiệp vụ cần lưu giữ. Phải phân biệt dữ liệu đang hoạt động, dữ liệu lịch sử và dữ liệu cần xóa.

---

## 21. LOGGING, MONITORING VÀ ERROR HANDLING

Xây dựng:
- Structured logging.
- Request ID hoặc correlation ID.
- Error response thống nhất.
- Logging thời gian xử lý request.
- Logging lỗi database.
- Health endpoint.
- Readiness endpoint nếu cần.
- Metrics cơ bản.
- Audit log cho các hành động quan trọng.

Không log:
- Password.
- Token.
- Secrets.
- Nội dung CV không cần thiết.
- Thông tin cá nhân nhạy cảm không cần thiết.

Lỗi nội bộ phải được ghi lại ở server theo cách an toàn. Response gửi client chỉ chứa thông tin cần thiết.

---

## 22. DỮ LIỆU MẪU VÀ DEMO

Tạo seed script để dựng một mạng lưới minh họa có thể kiểm thử được.

Dữ liệu mẫu nên bao gồm:
- Ít nhất 15–30 người dùng.
- Một số doanh nghiệp.
- Một số tin tuyển dụng.
- Các kỹ năng.
- Các quan hệ trực tiếp và gián tiếp.
- Người dùng đang làm việc và đã rời doanh nghiệp.
- Kết nối đã chấp nhận và chưa chấp nhận.
- Các yêu cầu giới thiệu ở nhiều trạng thái.
- Các trường hợp ứng viên phù hợp hoặc không phù hợp với công việc.

Đây là dữ liệu phục vụ demo, không được trình bày là dữ liệu thật.

Tạo một kịch bản kiểm chứng quan trọng:

Ứng viên A không có kết nối trực tiếp với nhân viên công ty X, nhưng có một đường kết nối hợp lệ qua B và C. Hệ thống phải tìm được đường đó, giải thích số bước, xác định C có đang làm việc tại X hay không, kiểm tra trạng thái quan hệ và đề xuất quy trình yêu cầu giới thiệu phù hợp.

Tạo thêm các trường hợp:
- Đường bị đứt do một kết nối bị xóa.
- Một cạnh chưa được chấp nhận.
- C đã nghỉ công ty X.
- Công việc đã đóng.
- Ứng viên không đủ điều kiện truy cập thông tin của một người.
- Có nhiều đường giới thiệu.
- Có kết nối trùng hoặc yêu cầu trùng.

---

## 23. TÀI LIỆU PHẢI BÀN GIAO

Tạo đầy đủ các tài liệu sau:

1. `README.md`
   - Giới thiệu dự án.
   - Công nghệ.
   - Yêu cầu môi trường.
   - Cách cài đặt.
   - Cách chạy.
   - Cách chạy tests.
   - Cách sử dụng demo.

2. `docs/requirements.md`
   - Phạm vi.
   - Actors.
   - User stories.
   - Business rules.
   - Acceptance criteria.

3. `docs/architecture.md`
   - Kiến trúc.
   - Module boundaries.
   - Luồng dữ liệu.
   - Quyết định kỹ thuật.

4. `docs/database/graph-schema.md`
   - Vertex.
   - Edge.
   - Named graph.
   - Chiều quan hệ.
   - Quy tắc dữ liệu.

5. `docs/database/query-design.md`
   - Truy vấn AQL.
   - Input/output.
   - Index.
   - Độ phức tạp dự kiến.
   - Các lưu ý tối ưu.

6. `docs/api.md`
   - API endpoints.
   - Authentication.
   - Request/response.
   - Error codes.

7. `docs/security.md`
   - Authentication.
   - Authorization.
   - Quyền riêng tư.
   - Threat model cơ bản.

8. `docs/testing.md`
   - Các loại test.
   - Cách chạy.
   - Kết quả.
   - Giới hạn.

9. `docs/deployment.md`
   - Docker.
   - Environment variables.
   - Backup.
   - Restore.
   - Troubleshooting.

10. `docs/project-plan.md`
    - Các phase.
    - Trạng thái hoàn thành.
    - Các phụ thuộc.
    - Các rủi ro.
    - Việc còn lại.

11. `docs/decisions/`
    - Ghi lại các quyết định kiến trúc quan trọng và lý do lựa chọn.

Tài liệu phải phản ánh source code thực tế. Không ghi các chức năng chưa triển khai như thể đã hoàn thành.

---

## 24. CÁC GIAI ĐOẠN TRIỂN KHAI BẮT BUỘC

Thực hiện theo trình tự dưới đây.

### PHASE 0 — REPOSITORY AUDIT

Nhiệm vụ:
- Kiểm tra repository.
- Kiểm tra môi trường.
- Xác định các chức năng hiện có.
- Ghi nhận lỗi hiện tại.
- Xác định công nghệ và dependency.
- Tạo implementation plan.

Deliverables:
- Báo cáo hiện trạng.
- Sơ đồ cấu trúc.
- Danh sách thiếu sót.
- Kế hoạch thực hiện.
- Danh sách rủi ro.

Chưa thực hiện các thay đổi phá vỡ kiến trúc trước khi hoàn thành đánh giá.

### PHASE 1 — REQUIREMENTS VÀ ARCHITECTURE

Nhiệm vụ:
- Chốt phạm vi MVP.
- Viết user stories.
- Thiết kế module.
- Thiết kế API contracts.
- Thiết kế graph schema.
- Thiết kế luồng referral.
- Xác định security policies.

Deliverables:
- Tài liệu nghiệp vụ.
- Tài liệu kiến trúc.
- Graph schema.
- API contract.
- Acceptance criteria.

### PHASE 2 — ARANGODB FOUNDATION

Nhiệm vụ:
- Tạo bootstrap.
- Tạo collections.
- Tạo graph definitions.
- Tạo indexes.
- Tạo migration mechanism.
- Tạo seed data.
- Viết AQL queries.
- Kiểm thử graph traversal.

Deliverables:
- Database scripts.
- Graph schema.
- Seed script.
- AQL query module.
- Integration tests.

Điều kiện chuyển phase:
- Database có thể khởi tạo lặp lại.
- Schema đúng.
- Các truy vấn graph chính trả về kết quả đúng trên dữ liệu mẫu.
- Có tests chứng minh điều đó.

### PHASE 3 — BACKEND FOUNDATION

Nhiệm vụ:
- Thiết lập FastAPI.
- Cấu hình settings.
- Tích hợp ArangoDB.
- Xây dựng repositories.
- Xây dựng services.
- Xây dựng error handling.
- Xây dựng authentication.
- Xây dựng authorization.
- Tạo OpenAPI.

Deliverables:
- Backend có thể chạy.
- Database connection.
- Auth API.
- User/profile API.
- Test suite ban đầu.

### PHASE 4 — CORE BUSINESS MODULES

Triển khai lần lượt:
1. Users và profiles.
2. Companies.
3. Jobs.
4. Skills.
5. Connections.
6. Applications.
7. Referral requests.
8. Notifications.
9. Admin functions cần thiết.

Mỗi module phải có:
- Models hoặc schemas.
- Repository.
- Service.
- API routes.
- Validation.
- Authorization.
- Tests.
- Documentation.

Không chuyển sang module phụ thuộc khi module trước chưa đạt acceptance criteria.

### PHASE 5 — GRAPH ENGINE

Triển khai:
- Tìm kết nối trực tiếp.
- Tìm đường 1–3 bước.
- Tìm nhân viên doanh nghiệp.
- Tìm người giới thiệu phù hợp.
- Giải thích đường kết nối.
- Loại bỏ quan hệ không hợp lệ.
- Giới hạn kết quả.
- Tối ưu các truy vấn chính.

Tạo test cases riêng cho các tình huống graph.

### PHASE 6 — MATCHING ENGINE

Triển khai:
- Chuẩn hóa dữ liệu kỹ năng.
- Skill matching.
- Experience matching.
- Location và work preference matching.
- Job relevance scoring.
- Referral path scoring.
- Ranking.
- Giải thích điểm số.

Tạo cấu hình cho trọng số và tests.

### PHASE 7 — FRONTEND

Triển khai:
- Design system.
- Authentication.
- Dashboard.
- Profile.
- Job search.
- Job detail.
- Network graph.
- Referral workflow.
- Application tracking.
- Company/recruiter dashboard.
- Notifications.
- Responsive layout.

Mỗi trang phải kết nối API thực tế, xử lý loading/error/empty state và kiểm thử các hành vi chính.

### PHASE 8 — INTEGRATION VÀ END-TO-END

Nhiệm vụ:
- Tích hợp frontend và backend.
- Kiểm thử toàn bộ luồng.
- Xử lý lỗi.
- Kiểm tra API contracts.
- Kiểm tra phân quyền.
- Kiểm tra dữ liệu graph.
- Chạy regression tests.

Không chấp nhận việc frontend sử dụng dữ liệu giả trong các luồng đã yêu cầu kết nối backend thật.

### PHASE 9 — DOCKER VÀ PRODUCTION READINESS

Nhiệm vụ:
- Hoàn thiện Dockerfiles.
- Hoàn thiện Docker Compose.
- Health checks.
- Persistent storage.
- Environment configuration.
- Logging.
- Backup/restore.
- Reverse proxy nếu cần.
- HTTPS cho triển khai công khai.
- Kiểm tra secrets và các cấu hình mặc định nguy hiểm.

Chạy thử quy trình cài đặt từ môi trường sạch theo README.

### PHASE 10 — PERFORMANCE VÀ ACCEPTANCE

Nhiệm vụ:
- Chạy toàn bộ tests.
- Đo hiệu năng.
- Kiểm tra query plans.
- Kiểm tra quyền riêng tư.
- Kiểm tra bảo mật.
- Kiểm tra Docker.
- Kiểm tra khôi phục database.
- Đối chiếu acceptance criteria.
- Ghi nhận các lỗi còn tồn tại.

Deliverables:
- Test report.
- Performance report.
- Security checklist.
- Deployment guide.
- Danh sách hạn chế.
- Trạng thái bàn giao.

---

## 25. QUY TẮC THỰC HIỆN TỪNG PHASE

Đối với mỗi phase, hãy làm theo quy trình:

Bước 1: Phân tích yêu cầu và dependencies.

Bước 2: Xác định các file sẽ tạo hoặc sửa.

Bước 3: Triển khai phần nhỏ nhất có thể kiểm chứng.

Bước 4: Chạy formatter, linter và type checking nếu có.

Bước 5: Chạy các tests liên quan.

Bước 6: Nếu test thất bại, đọc lỗi thực tế, tìm nguyên nhân gốc và sửa lỗi.

Bước 7: Chạy lại các tests bị ảnh hưởng.

Bước 8: Cập nhật tài liệu.

Bước 9: Đối chiếu acceptance criteria.

Bước 10: Ghi lại trạng thái và những việc còn lại.

Không:
- Bỏ qua lỗi để tiếp tục một cách máy móc.
- Tắt tests để làm cho pipeline pass.
- Xóa assertions nhằm che giấu lỗi.
- Sử dụng `except Exception: pass` hoặc cơ chế tương đương để che lỗi.
- Thay bằng mock khi cần kiểm thử tích hợp thực tế.
- Tạo các hàm chỉ trả dữ liệu giả nhưng đặt tên như đã hoàn thành nghiệp vụ.
- Khẳng định đã chạy ứng dụng nếu chưa thực sự chạy.
- Khẳng định một chức năng hoàn thành chỉ vì đã tạo file source.

Nếu thiếu quyền truy cập hoặc công cụ để thực hiện một bước, ghi rõ giới hạn và cung cấp lệnh cụ thể để người dùng thực hiện.

---

## 26. QUY TẮC CHẤT LƯỢNG CODE

Tuân thủ:
- Single Responsibility Principle.
- Separation of Concerns.
- DRY khi thực sự hợp lý.
- Dependency inversion ở những nơi cần thiết.
- Explicit configuration.
- Type safety.
- Input validation.
- Consistent naming.
- Structured error handling.
- Testability.
- Secure defaults.

Không over-engineer.

Không tạo quá nhiều abstraction cho nghiệp vụ đơn giản.

Không viết truy vấn AQL lặp lại ở nhiều nơi.

Không hard-code database credentials.

Không để frontend tự quyết định quyền truy cập.

Không dùng dữ liệu đầu vào để ghép trực tiếp câu truy vấn.

Không sử dụng các dependency không cần thiết.

Mỗi module cần có ranh giới rõ ràng và có thể thay đổi mà không buộc toàn bộ hệ thống phải viết lại.

---

## 27. DEFINITION OF DONE

Một chức năng chỉ được xem là hoàn thành khi đáp ứng tất cả điều kiện áp dụng sau:

1. Source code đã được triển khai.
2. Có validation đầu vào.
3. Có xử lý lỗi.
4. Có authorization phù hợp.
5. Đã tích hợp với các module liên quan.
6. Có tests phù hợp.
7. Tests liên quan đã chạy và đạt yêu cầu.
8. Không có dữ liệu giả thay cho kết quả thật ngoài phạm vi demo.
9. Tài liệu đã cập nhật.
10. Có thể chạy theo hướng dẫn.
11. Không làm hỏng chức năng hiện có.
12. Có acceptance criteria chứng minh chức năng hoạt động.

Đối với các chức năng graph:
- Dữ liệu vertex và edge phải đúng.
- Chiều quan hệ phải đúng.
- Trạng thái quan hệ phải được lọc đúng.
- Không trả về đường đi không hợp lệ.
- Có giới hạn traversal.
- Có kiểm tra quyền riêng tư.
- Có tests cho đường đi đúng và đường đi không hợp lệ.

Đối với toàn bộ sản phẩm:
- Người dùng có thể đăng ký và đăng nhập.
- Người dùng có thể tạo hồ sơ.
- Doanh nghiệp có thể quản lý công việc theo quyền hạn.
- Ứng viên có thể tìm việc.
- Graph engine tìm được đường giới thiệu hợp lệ.
- Hệ thống có thể tạo và xử lý referral requests.
- Frontend hoạt động với backend thật.
- Docker Compose có thể khởi động hệ thống.
- Có hướng dẫn khởi tạo dữ liệu.
- Có hướng dẫn backup và restore.
- Có báo cáo kiểm thử trung thực.

---

## 28. CÁCH BÁO CÁO SAU MỖI PHASE

Sau mỗi phase, cung cấp báo cáo theo mẫu:

### Phase: [Tên phase]

**1. Mục tiêu**
- Các mục tiêu phải đạt.

**2. Công việc đã thực hiện**
- Những file đã tạo.
- Những file đã sửa.
- Những chức năng đã triển khai.

**3. Quyết định kỹ thuật**
- Lựa chọn kiến trúc.
- Lý do.
- Các giả định.

**4. Kiểm thử**
- Lệnh đã chạy.
- Kết quả thực tế.
- Tests pass/fail.
- Những phần chưa kiểm thử.

**5. Acceptance criteria**
- Đạt.
- Chưa đạt.
- Bằng chứng kiểm chứng.

**6. Vấn đề còn lại**
- Lỗi.
- Rủi ro.
- Dependencies.
- Việc cần xử lý tiếp.

**7. Phase tiếp theo**
- Công việc cụ thể.
- Điều kiện để bắt đầu.

Không dùng báo cáo dài để che giấu việc chưa triển khai. Hãy ưu tiên bằng chứng, file thực tế, kết quả tests và trạng thái rõ ràng.

---

## 29. YÊU CẦU BẮT ĐẦU THỰC HIỆN NGAY

Bây giờ hãy bắt đầu PHASE 0.

Không cần trình bày lại toàn bộ prompt này.

Nếu có quyền truy cập repository:
1. Kiểm tra trạng thái và cấu trúc source code.
2. Đọc các file quan trọng.
3. Phân tích những gì đã có.
4. Xác định những gì còn thiếu.
5. Tạo kế hoạch thực hiện phù hợp với repository.
6. Triển khai những công việc an toàn và có thể kiểm chứng trong phạm vi được phép.

Nếu repository chưa có source code, hãy chuẩn bị cấu trúc dự án mới theo kiến trúc đã mô tả.

Không cố hoàn thành toàn bộ hệ thống trong một lần sinh code. Làm từng phase, từng module, chạy tests và sửa lỗi liên tục.

Không dừng lại ở một bản kế hoạch lý thuyết. Hãy tiến hành công việc thực tế cho đến khi hoàn thành phạm vi có thể thực hiện trong phiên làm việc hiện tại, sau đó báo cáo trung thực những gì đã hoàn thành và bước tiếp theo.

**Ưu tiên tuyệt đối: ArangoDB graph schema đúng, truy vấn graph chính xác, quy trình giới thiệu hoạt động thực tế, bảo mật đúng và hệ thống có thể chạy được.**