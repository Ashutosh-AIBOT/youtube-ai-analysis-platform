FROM python:3.10-slim as base
RUN apt-get update && apt-get install -y ffmpeg yt-dlp && rm -rf /var/lib/apt/lists/*

# YouTube Service (uses youtube-ai env)
FROM base as youtube
WORKDIR /app/youtube_app
COPY youtube_app/requirements.txt .
RUN pip install -r requirements.txt
COPY youtube_app/ .
CMD uvicorn main:app --host 0.0.0.0 --port 8005

# Sentiment Service
FROM base as sentiment
WORKDIR /app/fastapi_services/sentiment
COPY fastapi_services/requirements.txt /app/fastapi_services/
RUN pip install -r /app/fastapi_services/requirements.txt
COPY fastapi_services/sentiment/ .
CMD uvicorn main:app --host 0.0.0.0 --port 8010

# RAG Worker
FROM base as rag
WORKDIR /app/fastapi_services/rag_worker
COPY fastapi_services/requirements.txt /app/fastapi_services/
RUN pip install -r /app/fastapi_services/requirements.txt
COPY fastapi_services/rag_worker/ .
CMD uvicorn main:app --host 0.0.0.0 --port 8011

# Django App
FROM base as django
WORKDIR /app/django_app
COPY django_app/requirements.txt .
RUN pip install -r requirements.txt
COPY django_app/ .
RUN python manage.py collectstatic --noinput
CMD python manage.py runserver 0.0.0.0:7860
