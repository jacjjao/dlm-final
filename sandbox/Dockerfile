FROM python:3.12-slim

RUN pip install --no-cache-dir numpy pandas

RUN groupadd -r sandbox && useradd -r -g sandbox -s /sbin/nologin sandbox

USER sandbox
WORKDIR /tmp
