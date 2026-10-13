# AQL query contracts

Source: `database/aql/*.aql`; `database/queries.py` chỉ mở rộng include từ tên file
cố định, bind mọi input, không nối dữ liệu người dùng vào câu truy vấn. AQL runtime
5 giây, memory 64 MiB, cache off, fail_on_warning. Actor_id internal phải do auth
service cấp. `as_of` server UTC dùng cho employment, không cho client tùy ý đổi
thời điểm để lách quyền.

| Method / AQL | Input | Output và filters | Index | Chi phí dự kiến |
| --- | --- | --- | --- | --- |
| direct_connections | actor_id, offset 0–1000, limit 1–100 | accepted/nondeleted, active/discoverable, no block; id/name/headline | edge + connections_in/out_status | O(degree), sort theo ID |
| employees / company_employees | actor_id, company_id, as_of, pagination | current+verified, start/end dates, company active, discoverable/employment_visible, no viewer block | company_current_employees | O(E_company), sort; có thể lọc sau index |
| referral_paths | actor_id, company_id, optional job_id, depth 1–3, pagination | named graph chỉ connections; PRUNE invalid edges/nodes/privacy/block; endpoint current employee; optional job phải open và thuộc company | edge/vertex-centric + works_at | O(b^d + E_company), sort các path hợp lệ |
| shortest_path | actor_id, target_id, depth 1–3 | Cùng referral_paths với company null và limit1; ngắn nhất trong các đường có consent | edge/status | O(b^d), không claim weighted shortest |
| job_matches | actor_id, optional job_id, pagination, weights | open job + active company; required/preferred skill levels/years, experience, level, location/mode, salary diagnostics | jobs_open_recent, has_skill, job_requires_skill, job_at_company | O(J×R + S), sort job score |
| jobs_with_referral | actor_id, optional job_id, depth, pagination | Chỉ đủ required skills/experience; best path có consent; rank job score trước path; closed/no path bị loại | tổng hợp các index trên | O(J×(R+b^d+E_company)); cần benchmark lại khi J lớn |

Mọi path gồm vertices DTO, edges id/status/trust, referrer DTO, hops, trust,
current_verified_employee, path_score, next_step và explanation. Các graph DTO
không chứa email/phone/role/private attributes. Referral path_score mặc định =
0.6×mean trust + 0.4×(1/hops), weights configurable và tổng1. Sort score DESC,
hops ASC, path_key ASC. Shortest mode sort hops ASC trước score. Một đường dài
hơn nhưng trust tốt có thể được đề xuất trước đường ngắn; shortest query vẫn tìm
đúng đường ngắn nhất có consent. Trust khai báo là synthetic ở demo; thiếu thì 0.5;
không phải xác suất thành công. `uniqueVertices: path` giữ đường thay thế; không
global-dedupe vì global có thể chọn một đường tùy ý và mất alternatives.

`PRUNE` được kiểm tra cả ở root nên điều kiện cạnh phải có guard `e != null`;
`FILTER !invalid` loại luôn node tại điểm dừng. Viewer block check loại endpoint
hoặc intermediary dù cạnh trên đường hiện tại là accepted. Chỉ traversal xã hội
restricted, không đi vòng qua skills/companies để tạo false connection.

Matching baseline đã chốt: required/preferred ratio có trọng số importance;
nếu cả hai loại có yêu cầu thì skill = 0.8×required + 0.2×preferred, chỉ một loại
thì dùng ratio loại đó; không có requirements thì skill=0. Experience = min(1,
years/min_years), requirement zero →1. Remote location →1, otherwise same location;
level exact-match và work_mode nằm trong preference →1. Weights mặc định
0.4/0.2/0.15/0.15/0.1, configurable và tổng1. Salary overlap nullable là diagnostic,
không bí mật thêm trọng số; salary VND trong MVP. `eligible` chỉ kiểm tra required
skills và min experience, không là quyết định tuyển dụng. Nâng ranking/candidate
search cho recruiter ở Phase 6, không coi baseline là model đã hiệu chỉnh.

Offset pagination ổn định với dữ liệu tĩnh; dữ liệu thay đổi có thể dịch trang,
không hứa snapshot across requests. Missing ID → empty result; malformed ID,
depth/limit/offset/time sai → ValueError nội bộ, Phase3 map 422.
Shortest target tự là actor → no positive-hop path. Quyền đổi không cache.
Status accepted nhưng thiếu accepted_at cũng bị loại. Path baseline không đo
path reliability hay xác suất; ranking đầy đủ/hiệu chỉnh là Phase6.

EXPLAIN/PROFILE cho cả 5 AQL và shortest/depth variants nằm trong
`docs/reports/benchmark.json`. Integration `test_explain_profile_and_indexes`
chứng minh TraversalNode + works_at index. Benchmark đo 1,134 users, 1,128
connections, 1,012 works_at; branching10/depth3, 20 lần/query, serial local Docker.
Không suy rộng latency này thành SLA production; dense/cyclic/high-degree graph,
job catalog lớn, cluster và tải đồng thời cần Phase10.
