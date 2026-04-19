FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg libpq-dev gcc curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r django_app/requirements.txt
RUN pip install --no-cache-dir -r youtube_app/requirements.txt
RUN pip install --no-cache-dir -r fastapi_services/requirements.txt
# We leave the CMD empty and define the start command in render.yaml
