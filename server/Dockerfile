FROM python:3.9

COPY src/ /app
WORKDIR /app

COPY config/ /app/config

RUN pip install flask gunicorn firebase_admin pyrebase4

ENV PORT 8080
ENV LOCAL Dev

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
