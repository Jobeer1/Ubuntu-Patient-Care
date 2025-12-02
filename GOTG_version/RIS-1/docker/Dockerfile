FROM python:3.10-slim

# Install minimal dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies (with minimal size)
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ .

# Create volumes for data persistence
VOLUME ["/app/data", "/app/uploads"]

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# Run app
CMD ["python", "app.py"]
