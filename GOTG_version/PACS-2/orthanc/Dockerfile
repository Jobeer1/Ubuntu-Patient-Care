# Lightweight Orthanc DICOM Server for Hostile Environments
FROM orthancteam/orthanc:24.11.3

# Install essential tools only
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install minimal Python dependencies for scripts
RUN pip3 install --no-cache-dir requests

# Create necessary directories
RUN mkdir -p /var/lib/orthanc/db \
    /etc/orthanc \
    /usr/share/orthanc/plugins

# Copy optimized configuration
COPY orthanc.json /etc/orthanc/orthanc.json

# Health check script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Expose ports
EXPOSE 4242 8042

# Set working directory
WORKDIR /var/lib/orthanc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Start Orthanc
CMD ["Orthanc", "/etc/orthanc/orthanc.json"]
