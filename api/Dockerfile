FROM python:3.11-slim

ARG ENV_VARS

ENV ENV_VARS=${ENV_VARS} \
    POETRY_VERSION=1.8.2 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# TODO: make dev and prod images, move this section to dev image only
ENV WATCHFILES_FORCE_POLLING=true \
    WATCHFILES_POLLING_INTERVAL=1

WORKDIR /code

COPY poetry.lock pyproject.toml entrypoint.sh /code/

RUN pip install "poetry==$POETRY_VERSION"

RUN poetry install

COPY . /code
