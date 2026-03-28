FROM python:3.13.12-alpine3.23
LABEL authors="zakhar"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /tmp/build

COPY pyproject.toml uv.lock README.md ./

RUN apk add --no-cache --virtual build-deps \
    uv \
    && uv export --frozen --group test --no-group dev --no-group ops > requirements.txt \
    && uv pip install --system -r requirements.txt \
    && rm -f requirements.txt \
    && apk del build-deps

WORKDIR /opt/app

COPY src .
COPY pytest.ini .