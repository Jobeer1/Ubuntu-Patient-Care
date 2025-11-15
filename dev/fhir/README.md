# FHIR Development Sandbox

**Task**: P1-FHIR-001  
**Owner**: Dev3  
**Status**: ✅ Complete

## Overview

This is a lightweight FHIR R4 server for local development and testing. It uses HAPI FHIR (open-source Java implementation) and runs completely in Docker with no external dependencies.

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Port 8080 available

### Start the Server

```bash
cd dev/fhir
docker-compose up -d
```

### Verify It's Running

Wait ~30 seconds for startup, then test:

```bash
# Check health
curl http://localhost:8080/fhir/metadata

# Should return FHIR CapabilityStatement with HTTP 200
```

### Stop the Server

```bash
docker-compose down
```

### Reset All Data

```bash
docker-compose down -v
```

## What's Included

- **HAPI FHIR Server** (latest stable)
- **FHIR R4** specification
- **JSON encoding** (default)
- **CORS enabled** for browser testing
- **No authentication** (dev only - DO NOT use in production)
- **Persistent storage** via Docker volume

## Supported Resources

All FHIR R4 resources are supported. Key ones for Phase 1:

- `Patient` - patient demographics
- `Practitioner` - healthcare providers
- `Appointment` - scheduled visits
- `ServiceRequest` - orders for procedures
- `ImagingStudy` - radiology study metadata
- `DiagnosticReport` - clinical reports
- `Observation` - measurements and findings

## Testing Examples

### Create a Patient

```bash
curl -X POST http://localhost:8080/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Patient",
    "identifier": [{
      "system": "urn:openemr:pid",
      "value": "12345"
    }],
    "name": [{
      "family": "Doe",
      "given": ["John"]
    }],
    "gender": "male",
    "birthDate": "1980-01-01"
  }'
```

### Search for Patients

```bash
curl "http://localhost:8080/fhir/Patient?family=Doe"
```

### Get a Specific Patient

```bash
curl http://localhost:8080/fhir/Patient/1
```

## Configuration

The server is configured via environment variables in `docker-compose.yml`:

- **Port**: 8080 (change in `ports` section)
- **FHIR Version**: R4 (change `hapi.fhir.fhir_version`)
- **Base URL**: http://localhost:8080/fhir

## Data Persistence

Data is stored in a Docker volume `fhir-data`. It persists between container restarts but can be wiped with `docker-compose down -v`.

## Troubleshooting

### Server won't start
```bash
# Check logs
docker-compose logs -f fhir-server

# Common issues:
# - Port 8080 already in use (change port in docker-compose.yml)
# - Docker out of memory (increase Docker memory limit)
```

### Health check failing
```bash
# Wait longer - HAPI takes 30-60s to fully start
# Check if Java process is running
docker-compose exec fhir-server ps aux | grep java
```

### Can't connect from host
```bash
# Verify port mapping
docker-compose ps

# Test from inside container
docker-compose exec fhir-server curl http://localhost:8080/fhir/metadata
```

## Next Steps

- **P1-FHIR-002**: Create automated smoke tests for core resources
- **P1-FHIR-003**: Add OAuth2 token stub for authenticated testing
- **P1-FHIR-004**: Build mapping adapter to convert local data to FHIR

## Security Notes

⚠️ **WARNING**: This configuration is for DEVELOPMENT ONLY

- No authentication enabled
- CORS allows all origins
- All operations permitted (create, update, delete)
- Data not encrypted at rest

For production deployment, you MUST:
- Enable OAuth2/SMART-on-FHIR authentication
- Configure proper CORS origins
- Enable TLS/HTTPS
- Implement audit logging
- Restrict operations by role

## Resources

- [HAPI FHIR Documentation](https://hapifhir.io/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [FHIR REST API](https://hl7.org/fhir/R4/http.html)

---

**Created**: 2025-11-06  
**Last Updated**: 2025-11-06  
**Maintainer**: Dev3
