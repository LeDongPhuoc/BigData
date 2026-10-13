FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.lock \
    && useradd --uid 10001 --create-home app
COPY docker/build-wheels/setuptools-84.0.0-py3-none-any.whl /tmp/build-wheels/
RUN python -c "import hashlib,pathlib; p=pathlib.Path('/tmp/build-wheels/setuptools-84.0.0-py3-none-any.whl'); assert hashlib.sha256(p.read_bytes()).hexdigest() == '51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670'" \
    && pip install --no-cache-dir --no-index --no-deps /tmp/build-wheels/setuptools-84.0.0-py3-none-any.whl
COPY backend ./backend
COPY database ./database
RUN pip install --no-cache-dir --no-build-isolation --no-deps .
USER 10001
EXPOSE 8000
CMD ["uvicorn", "backend.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
