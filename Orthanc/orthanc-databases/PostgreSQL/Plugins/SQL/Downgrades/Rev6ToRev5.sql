-- This file contains an SQL procedure to downgrade from schema 6 to Rev5 (version = 6).


-- Re-installs the old PatientRecycling
-----------

CREATE TABLE IF NOT EXISTS PatientRecyclingOrder(
       seq BIGSERIAL NOT NULL PRIMARY KEY,
       patientId BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       CONSTRAINT UniquePatientId UNIQUE (patientId)
       );

CREATE INDEX IF NOT EXISTS PatientRecyclingIndex ON PatientRecyclingOrder(patientId);

DROP TRIGGER IF EXISTS PatientAdded ON Resources;

CREATE OR REPLACE FUNCTION PatientAddedOrUpdated(
    IN patient_id BIGINT,
    IN is_update BIGINT
    )
RETURNS VOID AS $body$
BEGIN
    DECLARE
        newSeq BIGINT;
    BEGIN
        IF is_update > 0 THEN
            -- Note: Protected patients are not listed in this table !  So, they won't be updated
            WITH deleted_rows AS (
                DELETE FROM PatientRecyclingOrder
                WHERE PatientRecyclingOrder.patientId = patient_id
                RETURNING patientId
            )
            INSERT INTO PatientRecyclingOrder (patientId)
            SELECT patientID FROM deleted_rows
            WHERE EXISTS(SELECT 1 FROM deleted_rows);
        ELSE
            INSERT INTO PatientRecyclingOrder VALUES (DEFAULT, patient_id);
        END IF;
    END;
END;
$body$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION PatientAddedFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  -- The "0" corresponds to "OrthancPluginResourceType_Patient"
  IF new.resourceType = 0 THEN
    PERFORM PatientAddedOrUpdated(new.internalId, 0);
  END IF;
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS PatientAdded on Resources;
CREATE TRIGGER PatientAdded
AFTER INSERT ON Resources
FOR EACH ROW
EXECUTE PROCEDURE PatientAddedFunc();

DROP FUNCTION IF EXISTS ProtectPatient(patient_id BIGINT);

DROP FUNCTION IF EXISTS UnprotectPatient;

-- repopulate the PatientRecyclingOrderTable
WITH UnprotectedPatients AS (SELECT r.internalId
  FROM Resources r
  RIGHT JOIN Metadata m ON r.internalId = m.id AND m.type = 19  -- 19 = PatientRecyclingOrder
  WHERE r.resourceType = 0
    AND NOT EXISTS (SELECT 1 FROM Metadata m
                    WHERE m.id = r.internalId AND m.type = 18 AND m.value = 'true') -- 18 = IsProtected
  ORDER BY CAST(m.value AS INTEGER) ASC)

INSERT INTO PatientRecyclingOrder (patientId)
SELECT internalId
FROM UnprotectedPatients;

DROP SEQUENCE IF EXISTS PatientRecyclingOrderSequence;

-- remove the IsProtected and PatientRecyclingOrder metadata
DELETE FROM Metadata WHERE type IN (18, 19);

-- Re-installs the old CreateInstance method
-----------

CREATE OR REPLACE FUNCTION CreateInstance(
  IN patient_public_id TEXT,
  IN study_public_id TEXT,
  IN series_public_id TEXT,
  IN instance_public_id TEXT,
  OUT is_new_patient BIGINT,
  OUT is_new_study BIGINT,
  OUT is_new_series BIGINT,
  OUT is_new_instance BIGINT,
  OUT patient_internal_id BIGINT,
  OUT study_internal_id BIGINT,
  OUT series_internal_id BIGINT,
  OUT instance_internal_id BIGINT) AS $body$

BEGIN
	is_new_patient := 1;
	is_new_study := 1;
	is_new_series := 1;
	is_new_instance := 1;

	BEGIN
        INSERT INTO "resources" VALUES (DEFAULT, 0, patient_public_id, NULL, 0) RETURNING internalid INTO patient_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_patient := 0;
            SELECT internalid INTO patient_internal_id FROM "resources" WHERE publicId = patient_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction
    END;

	BEGIN
        INSERT INTO "resources" VALUES (DEFAULT, 1, study_public_id, patient_internal_id, 0) RETURNING internalid INTO study_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_study := 0;
            SELECT internalid INTO study_internal_id FROM "resources" WHERE publicId = study_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction    END;
    END;

	BEGIN
	    INSERT INTO "resources" VALUES (DEFAULT, 2, series_public_id, study_internal_id, 0) RETURNING internalid INTO series_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_series := 0;
            SELECT internalid INTO series_internal_id FROM "resources" WHERE publicId = series_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction    END;
    END;

  	BEGIN
		INSERT INTO "resources" VALUES (DEFAULT, 3, instance_public_id, series_internal_id, 0) RETURNING internalid INTO instance_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_instance := 0;
            SELECT internalid INTO instance_internal_id FROM "resources" WHERE publicId = instance_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction
    END;

    IF is_new_instance > 0 THEN
        -- Move the patient to the end of the recycling order.
        PERFORM PatientAddedOrUpdated(patient_internal_id, 1);
    END IF;  
END;
$body$ LANGUAGE plpgsql;

-- Restore the DeleteResource function that has been optimized

------------------- DeleteResource function -------------------

CREATE OR REPLACE FUNCTION DeleteResource(
    IN id BIGINT,
    OUT remaining_ancestor_resource_type INTEGER,
    OUT remaining_anncestor_public_id TEXT) AS $body$

DECLARE
    deleted_row RECORD;
    locked_row RECORD;

BEGIN

    SET client_min_messages = warning;   -- suppress NOTICE:  relation "deletedresources" already exists, skipping
    
    -- note: temporary tables are created at session (connection) level -> they are likely to exist
    -- these tables are used by the triggers
    CREATE TEMPORARY TABLE IF NOT EXISTS DeletedResources(
        resourceType INTEGER NOT NULL,
        publicId VARCHAR(64) NOT NULL
        );

    RESET client_min_messages;

    -- clear the temporary table in case it has been created earlier in the session
    DELETE FROM DeletedResources;
    
    -- create/clear the DeletedFiles temporary table
    PERFORM CreateDeletedFilesTemporaryTable();

    -- Before deleting an object, we need to lock its parent until the end of the transaction to avoid that
    -- 2 threads deletes the last 2 instances of a series at the same time -> none of them would realize
    -- that they are deleting the last instance and the parent resources would not be deleted.
    -- Locking only the immediate parent is sufficient to prevent from this.
    SELECT * INTO locked_row FROM resources WHERE internalid = (SELECT parentid FROM resources WHERE internalid = id) FOR UPDATE;

    -- delete the resource itself
    DELETE FROM Resources WHERE internalId=id RETURNING * INTO deleted_row;
    -- note: there is a ResourceDeletedFunc trigger that will execute here and delete the parents if there are no remaining children + 

    -- If this resource still has siblings, keep track of the remaining parent
    -- (a parent that must not be deleted but whose LastUpdate must be updated)
    SELECT resourceType, publicId INTO remaining_ancestor_resource_type, remaining_anncestor_public_id
        FROM Resources 
        WHERE internalId = deleted_row.parentId
            AND EXISTS (SELECT 1 FROM Resources WHERE parentId = deleted_row.parentId);

END;

$body$ LANGUAGE plpgsql;


-- restore the DeletedResource trigger

------------------- ResourceDeleted trigger -------------------
DROP TRIGGER IF EXISTS ResourceDeleted ON Resources;

-- The following trigger combines 2 triggers from SQLite:
-- ResourceDeleted + ResourceDeletedParentCleaning
CREATE OR REPLACE FUNCTION ResourceDeletedFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  -- RAISE NOTICE 'ResourceDeletedFunc %', old.publicId;
  INSERT INTO DeletedResources VALUES (old.resourceType, old.publicId);
  
  -- If this resource is the latest child, delete the parent
  DELETE FROM Resources WHERE internalId = old.parentId
                              AND NOT EXISTS (SELECT 1 FROM Resources WHERE parentId = old.parentId);
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ResourceDeleted on Resources;
CREATE TRIGGER ResourceDeleted
AFTER DELETE ON Resources
FOR EACH ROW
EXECUTE PROCEDURE ResourceDeletedFunc();


-- remove the new DeleteAttachment function

DROP FUNCTION IF EXISTS DeleteAttachment;

-- Restore the ON DELETE CASCADE on the Resources.parentId 
-- Drop the existing foreign key constraint and add a new one without ON DELETE CASCADE in a single command
ALTER TABLE Resources
DROP CONSTRAINT IF EXISTS resources_parentid_fkey,
ADD CONSTRAINT resources_parentid_fkey FOREIGN KEY (parentId) REFERENCES Resources(internalId) ON DELETE CASCADE;


-- Remove the AuditLogs table
-----------

DROP INDEX IF EXISTS AuditLogsUserId;
DROP INDEX IF EXISTS AuditLogsResourceId;
DROP INDEX IF EXISTS AuditLogsAction;
DROP INDEX IF EXISTS AuditLogsSourcePlugin;
DROP TABLE IF EXISTS AuditLogs;

-- Remove the InvlalidChildCountsId index
DROP INDEX IF EXISTS InvlalidChildCountsId;

-- Restore the previous UpdateSingleStatistics function
CREATE OR REPLACE FUNCTION UpdateSingleStatistic(
    IN statistics_key INTEGER,
    OUT new_value BIGINT
) AS $body$
BEGIN

  -- Delete the current changes, sum them and update the GlobalIntegers row.
  -- New rows can be added in the meantime, they won't be deleted or summed.
  WITH deleted_rows AS (
      DELETE FROM GlobalIntegersChanges
      WHERE GlobalIntegersChanges.key = statistics_key
      RETURNING value
  )
  UPDATE GlobalIntegers
  SET value = value + (
      SELECT COALESCE(SUM(value), 0)
      FROM deleted_rows
  )
  WHERE GlobalIntegers.key = statistics_key
  RETURNING value INTO new_value;

END;
$body$ LANGUAGE plpgsql;


----------

-- set the global properties that actually documents the DB version, revision and some of the capabilities
-- modify only the ones that have changed
DELETE FROM GlobalProperties WHERE property IN (4, 11);
INSERT INTO GlobalProperties VALUES (4, 5); -- GlobalProperty_DatabasePatchLevel
