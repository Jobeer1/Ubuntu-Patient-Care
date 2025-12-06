# Database Migrations

## Overview

This directory contains SQL migration scripts for the MCP server database.

## Migration Files

### 001_patient_access.sql
**Created**: 2025-10-21
**Purpose**: Patient-level access control

**Tables Added**:
1. `patient_relationships` - Links users to their patient records
2. `doctor_patient_assignments` - Links doctors to assigned patients
3. `family_access` - Links parents to children's records
4. `pacs_connection_config` - PACS connection configuration
5. `access_audit_log` - Audit trail for access attempts

**Indexes**: 12 indexes for performance
**Foreign Keys**: 9 foreign key constraints

## Running Migrations

### Manual Method

```bash
# Navigate to MCP server directory
cd 4-PACS-Module/Orthanc/mcp-server

# Run migration
sqlite3 mcp_server.db < migrations/001_patient_access.sql

# Verify tables created
sqlite3 mcp_server.db "SELECT name FROM sqlite_master WHERE type='table';"
```

### Python Script Method

```python
# Use the migration script
python scripts/run_migration.py migrations/001_patient_access.sql
```

## Rollback

To rollback migration 001:

```sql
DROP TABLE IF EXISTS access_audit_log;
DROP TABLE IF EXISTS pacs_connection_config;
DROP TABLE IF EXISTS family_access;
DROP TABLE IF EXISTS doctor_patient_assignments;
DROP TABLE IF EXISTS patient_relationships;
```

## Testing Migrations

After running migration, test with sample data:

```sql
-- Test patient relationship
INSERT INTO patient_relationships (user_id, patient_identifier, relationship_type, created_by)
VALUES (1, 'MRN-12345', 'self', 1);

-- Test doctor assignment
INSERT INTO doctor_patient_assignments (doctor_user_id, patient_identifier, assigned_by)
VALUES (2, 'MRN-12345', 1);

-- Test family access
INSERT INTO family_access (parent_user_id, child_patient_identifier, relationship, verified, verified_by)
VALUES (1, 'MRN-67890', 'parent', 1, 1);

-- Verify
SELECT * FROM patient_relationships;
SELECT * FROM doctor_patient_assignments;
SELECT * FROM family_access;
```

## Migration History

| Version | Date | Description | Status |
|---------|------|-------------|--------|
| 001 | 2025-10-21 | Patient access control | ✅ Ready |

## Best Practices

1. **Always backup** database before running migrations
2. **Test migrations** on development database first
3. **Document changes** in this README
4. **Version control** all migration files
5. **Never modify** existing migration files (create new ones)

## Troubleshooting

### Error: Table already exists
- Migration was already run
- Check with: `SELECT name FROM sqlite_master WHERE type='table';`

### Error: Foreign key constraint failed
- Ensure referenced tables exist
- Check user IDs are valid

### Error: Unique constraint failed
- Duplicate entry attempted
- Check existing data first

## Next Steps

After running migration 001:
1. Verify all tables created
2. Check indexes created
3. Test foreign key constraints
4. Insert sample data
5. Proceed to Task 1.2 (PACS Connector)
