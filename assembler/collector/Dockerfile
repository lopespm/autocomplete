FROM python:3.8-alpine

RUN apk add --no-cache gcc musl-dev
RUN apk add --no-cache  librdkafka-dev

COPY requirements.txt /tmp/
RUN pip install --requirement /tmp/requirements.txt
