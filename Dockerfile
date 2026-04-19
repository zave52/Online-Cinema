FROM python:3.13.12-alpine3.23

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/app

WORKDIR /tmp/build

COPY pyproject.toml uv.lock README.md ./

RUN apk add --no-cache --virtual build-deps \
    uv \
    && uv export --frozen --no-group dev --no-group test --no-group ops > requirements.txt \
    && uv pip install --system -r requirements.txt \
    && rm -f requirements.txt \
    && apk del build-deps

WORKDIR /opt/app

COPY src/ .
COPY alembic.ini /opt/alembic/alembic.ini
COPY scripts/run_migration.sh scripts/run_web_server_dev.sh scripts/run_web_server_prod.sh /scripts/

EXPOSE 8000
