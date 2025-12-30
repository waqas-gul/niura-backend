FROM python:3.11-slim

WORKDIR /app

# ===============================
# System dependencies
# ===============================
# - libGL, X11 → OpenCV
# - tesseract → pytesseract
# - ffmpeg → whisper
# - build-essential → torch wheels safety
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    tesseract-ocr \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ===============================
# Python dependencies
# ===============================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===============================
# App code
# ===============================
COPY app app

# ===============================
# Run server (BLOCKING)
# ===============================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
