FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./entrypoint.sh /code/entrypoint.sh

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt