# base
FROM python:3.11-alpine

COPY requirements.txt /temp/requirements.txt
COPY main.py /src/main.py

RUN pip install -r /temp/requirements.txt

WORKDIR /src
