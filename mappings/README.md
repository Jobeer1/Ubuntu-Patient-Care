# FHIR Data Mapping Tables

**Task**: P1-MAP-001  
**Status**: ✅ Complete

## Overview

CSV mapping tables documenting field-level transformations between local database schemas and FHIR R4 resources.

## Files

- `openemr_patient_mapping.csv` - OpenEMR patient table → FHIR Patient resource
- `orthanc_imaging_mapping.csv` - Orthanc/DICOM metadata → FHIR ImagingStudy resource

## Usage

### For Developers

Use these tables to:
1. Understand field mappings when writing adapters
2. Validate transformation logic
3. Document new resource mappings
4. Generate adapter code

### For Reviewers

Use these tables to:
1. Verify mapping completeness
2. Check FHIR compliance
3. Validate data type conversions
4. Review privacy/security considerations

## CSV Format

```
Local Field, Type, Example, FHIR Resource, FHIR Path, FHIR Type, Notes
```

**Columns**:
- **Local Field**: Database column name
- **Type**: SQL data type
- **Example**: Sample value
- **FHIR Resource**: Target FHIR resource type
- **FHIR Path**: FHIRPath expression to target field
- **FHIR Type**: FHIR data type
- **Notes**: Transformation rules, special handling

## Examples

### Patient Mapping

```csv
OpenEMR Field,Type,Example,FHIR Resource,FHIR Path,FHIR Type,Notes
pid,VARCHAR(255),12345,Patient,identifier[system=urn:openemr:pid].value,string,Primary patient identifier
fname,VARCHAR(255),John,Patient,name[0].given[0],string,First/given name
sex,VARCHAR(255),M,Patient,gender,code,M→male F→female U→unknown O→other
```

### ImagingStudy Mapping

```csv
Orthanc/DICOM Field,DICOM Tag,Type,Example,FHIR Resource,FHIR Path,FHIR Type,Notes
StudyInstanceUID,0020000D,UI,1.2.840...,ImagingStudy,identifier[system=urn:dicom:uid].value,string,Prepend with urn:oid:
StudyDate,00080020,DA,20251106,ImagingStudy,started (date part),date,YYYYMMDD → YYYY-MM-DD
```

## Data Type Conversions

### Date/Time
- **OpenEMR DATE** → **FHIR date**: `YYYY-MM-DD` (no conversion needed)
- **DICOM DA** → **FHIR date**: `YYYYMMDD` → `YYYY-MM-DD`
- **DICOM TM** → **FHIR time**: `HHMMSS` → `HH:MM:SS`
- **DICOM DT** → **FHIR dateTime**: `YYYYMMDDHHMMSS` → `YYYY-MM-DDTHH:MM:SSZ`

### Codes
- **OpenEMR sex** → **FHIR gender**: `M`→`male`, `F`→`female`, `U`→`unknown`, `O`→`other`
- **DICOM Modality** → **FHIR modality**: Direct mapping (CT, MR, US, XR, etc.)

### Identifiers
- **OpenEMR PID** → **FHIR identifier**: System = `urn:openemr:pid`
- **DICOM UID** → **FHIR identifier**: System = `urn:dicom:uid`, prepend `urn:oid:`
- **SSN** → **FHIR identifier**: System = `http://hl7.org/fhir/sid/us-ssn`

## Validation Rules

### Required Fields
- **Patient**: identifier, name (at minimum family name)
- **ImagingStudy**: identifier, status, subject

### Optional But Recommended
- **Patient**: gender, birthDate, telecom
- **ImagingStudy**: started, modality, numberOfSeries

### Privacy Considerations
- SSN should be encrypted at rest
- Driver's license requires consent
- Contact information requires patient consent
- Deceased information is sensitive

## Adding New Mappings

1. Create new CSV file: `mappings/<source>_<resource>_mapping.csv`
2. Use same column structure
3. Document all transformations in Notes column
4. Add validation rules to this README
5. Update adapter code to match mapping
6. Add tests for new mappings

## References

- [FHIR Patient Resource](https://hl7.org/fhir/R4/patient.html)
- [FHIR ImagingStudy Resource](https://hl7.org/fhir/R4/imagingstudy.html)
- [DICOM Standard](https://www.dicomstandard.org/)
- [OpenEMR Database Schema](https://www.open-emr.org/wiki/index.php/Database_Structure)

---

**Created**: 2025-11-06  
**Maintainer**: Dev3
