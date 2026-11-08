FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock.txt && useradd --uid 10001 --create-home app
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
USER 10001:10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8443", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--ssl-keyfile", "/tls/server.key", "--ssl-certfile", "/tls/server.crt"]
