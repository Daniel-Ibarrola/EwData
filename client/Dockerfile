# base
FROM python:3.11-alpine

COPY requirements.txt /temp/requirements.txt
COPY src/ /src/

RUN pip install -r /temp/requirements.txt

WORKDIR /src
