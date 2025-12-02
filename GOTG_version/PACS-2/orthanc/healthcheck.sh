#!/bin/bash
# Health check for Orthanc PACS
# Returns 0 if healthy, 1 if unhealthy

# Check if Orthanc is responding
if curl -f -s http://localhost:8042/system > /dev/null 2>&1; then
    echo "Orthanc is healthy"
    exit 0
else
    echo "Orthanc is unhealthy"
    exit 1
fi
