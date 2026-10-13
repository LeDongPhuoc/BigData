# Build dependency của backend

`setuptools-84.0.0-py3-none-any.whl` được tải từ PyPI để bước đóng gói source backend không phải tải lại build dependency mỗi lần sửa code. Wheel được kiểm tra SHA-256 ngay trong Dockerfile trước khi cài. Runtime dependencies tiếp tục theo `requirements.lock`.

- Nguồn metadata: https://pypi.org/pypi/setuptools/84.0.0/json
- Nguồn wheel: https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl
- SHA-256: `51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670`.

Khi thay version phải đối chiếu checksum chính thức và cập nhật cả wheel/Dockerfile/tài liệu. Cách này xử lý lỗi timeout mạng ở bước build dependency; build mới từ đầu vẫn cần tải base image và runtime dependencies nếu máy chưa có cache.
