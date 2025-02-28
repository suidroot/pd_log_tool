FROM python:3.8-slim

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get upgrade -y 
RUN apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config

WORKDIR /app

COPY webproject/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY webproject/ /app