# ── Stage 1: build ───────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ─────────────────────────────────
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8005/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "2"]
