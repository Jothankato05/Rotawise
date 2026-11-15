# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY rotawise ./rotawise
COPY web ./web
COPY data ./data

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

ENV PORT=8000 WEB_CONCURRENCY=2
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/v1/health',timeout=2)"

# Gunicorn manages Uvicorn workers: graceful restarts, worker timeouts.
# Access logging is off on purpose: the app writes its own structured logs
# without IP addresses or phone numbers (see web/privacy.html).
CMD ["sh", "-c", "exec gunicorn rotawise.api.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY} -b 0.0.0.0:${PORT} --timeout 30 --graceful-timeout 20 --keep-alive 5"]
