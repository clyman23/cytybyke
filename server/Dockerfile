FROM python:3.9

RUN pip install Flask gunicorn firebase_admin

COPY src/ /app
WORKDIR /app

COPY config/ /app/config

ENV PORT 8080
ENV LOCAL False

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
