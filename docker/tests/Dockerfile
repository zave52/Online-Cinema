FROM python:3.13-slim
LABEL authors="zakhar"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off

RUN apt update

RUN python -m pip install --upgrade pip && \
    pip install poetry

COPY ./poetry.lock /usr/src/poetry/poetry.lock
COPY ./pyproject.toml /usr/src/poetry/pyproject.toml

COPY ./pytest.ini /usr/src/config/pytest.ini

RUN poetry config virtualenvs.create false

WORKDIR /usr/src/poetry

RUN poetry lock
RUN poetry install --no-root --only main

WORKDIR /usr/src/fastapi

COPY ./src .
