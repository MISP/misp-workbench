FROM python:3.9

ARG ENV_VARS

ENV ENV_VARS=${ENV_VARS} \
    POETRY_VERSION=1.1.13 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /code
COPY . /code

COPY poetry.lock pyproject.toml entrypoint.sh /code/

RUN pip install "poetry==$POETRY_VERSION"

RUN poetry install
