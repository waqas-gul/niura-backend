FROM python:3.11-slim-bullseye

# Set timezone
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    git \
    make \
    pkg-config \
    libssl-dev \
    libsasl2-dev \
    zlib1g-dev \
    libsasl2-2 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Build librdkafka
RUN git clone https://github.com/edenhill/librdkafka.git /tmp/librdkafka && \
    cd /tmp/librdkafka && \
    git checkout v2.3.0 && \
    ./configure --prefix=/usr && \
    make -j$(nproc) && \
    make install && \
    cd / && \
    rm -rf /tmp/librdkafka

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and migrations
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .

# IMPORTANT: Use Render's PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
