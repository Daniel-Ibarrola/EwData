# base
FROM python:3.11-alpine

COPY requirements.txt /temp/requirements.txt
COPY server.py /src/server.py

RUN pip install -r /temp/requirements.txt

WORKDIR /src
