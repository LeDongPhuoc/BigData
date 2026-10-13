# ADR 001 — ArangoDB graph foundation

Accepted 2026-10-11. Chọn single-server modular monolith; một canonical
connection/cặp + ANY traversal, quan hệ nghề nghiệp có chiều. Dùng named graph
definitions kết hợp explicit endpoint checks trong transaction writer/seed. Không tạo
cạnh friendship từ shared skill/employer. Embedded experience/education vì chưa
cần traversal qua các thực thể đó.

Migration JSON bất biến có checksum, journal và database lock; không Alembic.
Bootstrap không reset dữ liệu; schema drift cần migration chủ đích. DDL không
atomic nên từng migration có khả năng resume; fail giữ journal, nhả live lock.
Không tự rollback collections hay index unique vì có thể mất tính toàn vẹn.

Shortest valid path dùng bounded BFS + PRUNE + sorting, không dùng SHORTEST_PATH
rồi postfilter làm mất đường hợp lệ dài hơn. `uniqueVertices: path` giữ nhiều
đường; depth 3 + runtime/memory caps giới hạn workload nhưng dense graph vẫn cần
benchmark lớn ở Phase 10. Trust thiếu dữ liệu dùng neutral 0.5 và công khai;
điểm không là xác suất tuyển dụng. Referral baseline dùng 0.6×trust + 0.4/hops,
đường dài đáng tin có thể thắng; shortest mode ưu tiên hops riêng. Full reliability
và job relevance path scoring là Phase6.

Version được kiểm tra qua PyPI và official Docker metadata; API references:
[python-arango transactions](https://docs.python-arango.com/en/main/transaction.html),
[ArangoDB traversals](https://docs.arango.ai/arangodb/3.12/aql/graph-queries/traversals/),
[named graph integrity](https://docs.arango.ai/arangodb/3.12/graphs/),
[official image](https://hub.docker.com/_/arangodb).
