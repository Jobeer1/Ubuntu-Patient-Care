# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for compute workloads
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI for container execution
RUN curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh get-docker.sh

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for compute work
RUN mkdir -p /app/workspace/{jobs,models,data,results} \
    && mkdir -p /app/logs

# Create non-root user with Docker access
RUN useradd --create-home --shell /bin/bash worker \
    && usermod -aG docker worker \
    && chown -R worker:worker /app
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# Default command
CMD ["python", "worker.py"]