FROM python:3.9

ARG ENV_VARS

ENV ENV_VARS=${ENV_VARS} \
    POETRY_VERSION=1.1.13

WORKDIR /code

COPY poetry.lock pyproject.toml entrypoint.sh /code/

# install poetry
RUN pip install "poetry==$POETRY_VERSION"

RUN poetry install
