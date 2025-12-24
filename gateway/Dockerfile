# FROM python:3.11-alpine


# RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev librdkafka-dev
# # Install system dependencies for psutil, pyodbc, etc.
# RUN apk update && apk add --no-cache \
#     gcc \
#     musl-dev \
#     python3-dev \
#     linux-headers \
#     build-base \
#     unixodbc-dev


    
# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY ./app ./app

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]




FROM python:3.11-slim-bullseye

# Set timezone to UTC and ensure proper time synchronization
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
    libssl1.1 \
    libsasl2-2 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Build librdkafka from source
RUN git clone https://github.com/edenhill/librdkafka.git /tmp/librdkafka && \
    cd /tmp/librdkafka && \
    git checkout v2.3.0 && \
    ./configure --prefix=/usr && \
    make -j$(nproc) && \
    make install && \
    cd / && \
    rm -rf /tmp/librdkafka

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]