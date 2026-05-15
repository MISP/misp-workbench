FROM python:3.11-slim AS base

ARG ENV_VARS
ARG POETRY_GROUPS=""

ENV ENV_VARS=${ENV_VARS} \
    POETRY_VERSION=2.4.1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY poetry.lock pyproject.toml poetry.toml entrypoint.sh /code/

RUN pip install "poetry==$POETRY_VERSION"

RUN poetry install ${POETRY_GROUPS:+--with $POETRY_GROUPS}

COPY . /code

# dev stage
FROM base AS dev

ENV WATCHFILES_FORCE_POLLING=true \
    WATCHFILES_POLLING_INTERVAL=1