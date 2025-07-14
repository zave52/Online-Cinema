FROM python:3.13-slim
LABEL authors="zakhar"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off
ENV ALEMBIC_CONFIG=/usr/src/alembic/alembic.ini

RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    dos2unix \
    && apt clean

RUN python -m pip install --upgrade pip && \
    pip install poetry

COPY ./poetry.lock /usr/src/poetry/poetry.lock
COPY ./pyproject.toml /usr/src/poetry/pyproject.toml
COPY ./alembic.ini /usr/src/alembic/alembic.ini

RUN poetry config virtualenvs.create false

WORKDIR /usr/src/poetry

RUN poetry lock
RUN poetry install --no-root --only main

WORKDIR /usr/src/fastapi

COPY ./src .

COPY ./scripts /scripts

RUN dos2unix /scripts/*.sh

RUN chmod +x /scripts/*.sh
