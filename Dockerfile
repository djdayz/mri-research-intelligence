# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip \
    && /opt/venv/bin/pip install .

FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MRINSIGHT_ENVIRONMENT=production

RUN groupadd --system mrinsight \
    && useradd --system --gid mrinsight --home-dir /app --create-home mrinsight

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN mkdir -p /app/var/digests \
    && chown -R mrinsight:mrinsight /app

USER mrinsight

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/ready', timeout=3).read()"

CMD ["python", "-m", "uvicorn", "mrinsight.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
