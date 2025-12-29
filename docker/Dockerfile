# syntax=docker/dockerfile:1.4
# NinjaMediaManager Dockerfile
# Multi-stage build for React frontend + Python backend
# Enable BuildKit for parallel builds: DOCKER_BUILDKIT=1

# Stage 1: Build frontend (runs in parallel with deps stage)
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build production bundle
RUN npm run build

# Stage 2: Download external dependencies (runs in parallel with frontend)
FROM debian:bookworm-slim AS deps

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Deno, pgs-to-srt, and tessdata in parallel
RUN mkdir -p /opt/tessdata /opt/pgs-to-srt /opt/deno \
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/opt/deno sh \
    && curl -L -o /tmp/pgs-to-srt.zip https://github.com/NinjaNymo/pgs-to-srt/releases/download/V5/pgs-to-srt.zip \
    && unzip /tmp/pgs-to-srt.zip -d /opt \
    && rm /tmp/pgs-to-srt.zip \
    && curl -L -o /opt/tessdata/eng.traineddata \
        https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata \
    && curl -L -o /opt/tessdata/nor.traineddata \
        https://github.com/tesseract-ocr/tessdata_fast/raw/main/nor.traineddata

# Stage 3: Python dependencies (runs in parallel with frontend and deps)
FROM python:3.11-slim AS python-deps

WORKDIR /app

# Copy and install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 4: Production image - combines all stages
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MEDIA_PATH=/media
ENV OUTPUT_PATH=/output
ENV CONFIG_PATH=/config
ENV DENO_INSTALL="/opt/deno"
ENV PATH="/opt/deno/bin:$PATH"

# Install only runtime system dependencies (no curl/unzip needed anymore)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    mkvtoolnix \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python packages from python-deps stage
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy Deno, pgs-to-srt, and tessdata from deps stage
COPY --from=deps /opt/deno /opt/deno
COPY --from=deps /opt/pgs-to-srt /opt/pgs-to-srt
COPY --from=deps /opt/tessdata /opt/tessdata

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist ./static

# Create directories for volumes
RUN mkdir -p /media /output /config

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/|| exit 1

# Run the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
