FROM python:3.10-slim

LABEL maintainer="GOTG Emergency Medicine" \
      description="GOTG Dictation-3: Voice Dictation & Injury Assessment System"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies with optimization
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create data directory
RUN mkdir -p /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:5000/api/dictation/health')" || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DICTATION_DB_PATH=/data/dictation.db \
    RIS1_DB_PATH=/data/ris1.db \
    WHISPER_MODEL=tiny \
    PORT=5000

# Expose port
EXPOSE 5000

# Run application
CMD ["python3", "app.py"]
