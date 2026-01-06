# ================================================================================
# Multi-Stage Build: Reduces final image size by 60-70%
# Stage 1: Build dependencies and download models
# Stage 2: Runtime image with only necessary files
# ================================================================================

# ===============================
# Stage 1: Builder
# ===============================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install to a specific directory
COPY requirements.txt .

# Install PyTorch CPU-only version first (saves ~2GB vs CUDA version)
RUN pip install --no-cache-dir --prefix=/install \
    torch==2.1.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python packages
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Pre-download Whisper model to cache it in the image
# This reduces container startup time from 2 minutes to ~5 seconds
# Set PYTHONPATH so Python can find the installed packages
ENV PYTHONPATH="/install/lib/python3.11/site-packages"
RUN python3 -c "import whisper; whisper.load_model('base', download_root='/models')"

# ===============================
# Stage 2: Runtime
# ===============================
FROM python:3.11-slim

WORKDIR /app

# ===============================
# System dependencies (runtime only)
# ===============================
# Only install runtime libraries, not build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    tesseract-ocr \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# Copy from builder
# ===============================
# Copy installed Python packages
COPY --from=builder /install /usr/local

# Copy pre-downloaded Whisper model
COPY --from=builder /models /root/.cache/whisper

# ===============================
# App code
# ===============================
COPY app app

# ===============================
# Health check
# ===============================
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8003/api/health || exit 1

# ===============================
# Run server (BLOCKING)
# ===============================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
