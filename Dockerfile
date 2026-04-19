FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all files
COPY . .

# Install all Python requirements
RUN pip install --no-cache-dir -r django_app/requirements.txt
RUN pip install --no-cache-dir -r youtube_app/requirements.txt
RUN pip install --no-cache-dir -r fastapi_services/requirements.txt

# Create a directory for supervisor logs
RUN mkdir -p /var/log/supervisor

# Set Hugging Face specific Environment Variables
ENV DJANGO_SETTINGS_MODULE=config.settings
ENV PYTHONPATH="/app/django_app:/app/youtube_app:/app"
ENV PORT=7860

# Hugging Face Spaces run on port 7860 by default
EXPOSE 7860

# Run everything via Supervisor
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
