# syntax=docker/dockerfile:1
# Multi-stage production container for Health Deck

# ==============================================================================
# Stage 1: Build Frontend Assets
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Production Python Application Runner
# ==============================================================================
FROM python:3.12-slim AS runner

# Avoid buffering and writing bytecode
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEALTHDECK_ENV=production \
    HEALTHDECK_UPLOADS_DIR=/app/uploads \
    HEALTHDECK_REPORTS_DIR=/app/reports \
    HF_HOME=/app/.cache/huggingface \
    PORT=8000

WORKDIR /app

# Install minimal OS dependencies for audio processing, postgres, and container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Python production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download and cache faster-whisper model to prevent cold-start latency on first audio triage
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8', download_root='/app/.cache/whisper')" || true
ENV HEALTHDECK_WHISPER_CACHE=/app/.cache/whisper

# Create unprivileged application user and persistent volume directories
RUN useradd -m -u 1001 healthdeck && \
    mkdir -p /app/uploads /app/reports /app/.cache/whisper /app/.cache/huggingface && \
    chown -R healthdeck:healthdeck /app

# Copy application source code
COPY core/ ./core/
COPY assets/ ./assets/
COPY backend.py .
COPY scripts/ ./scripts/

# Copy compiled frontend distribution
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Secure ownership
RUN chown -R healthdeck:healthdeck /app

# Switch to non-root execution
USER healthdeck

# Expose HTTP port
EXPOSE 8000

# Declare persistent storage volumes
VOLUME ["/app/uploads", "/app/reports"]

# Production container liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch ASGI application server
CMD ["sh", "-c", "uvicorn backend:app --host 0.0.0.0 --port ${PORT}"]
