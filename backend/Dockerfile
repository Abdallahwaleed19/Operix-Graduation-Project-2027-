# =============================================================================
# Operix Main Backend — Production Dockerfile (Fly.io)
# =============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/ai-services \
    PORT=8080

WORKDIR /app

# System packages required for psycopg, pymupdf, and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (core backend + AI services)
COPY requirements.txt /app/requirements.txt
COPY ai-services/requirements.txt /app/ai-services/requirements.txt
COPY ai-services/llm_rag_assistant/requirements.txt /app/ai-services/llm_rag_assistant/requirements.txt

RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt && \
    pip install -r /app/ai-services/requirements.txt && \
    pip install -r /app/ai-services/llm_rag_assistant/requirements.txt

# Copy backend source and AI services
COPY app /app/app
COPY ai-services /app/ai-services
COPY run.py /app/run.py

# Ensure persistent storage mount points exist and run as non-root user
RUN useradd --create-home --shell /bin/bash operix && \
    mkdir -p /data/storage/evidence /data/storage/reports && \
    chown -R operix:operix /app /data/storage

USER operix

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8080/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
