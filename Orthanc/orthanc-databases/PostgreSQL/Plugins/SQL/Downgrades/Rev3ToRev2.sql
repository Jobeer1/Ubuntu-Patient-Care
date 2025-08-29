-- This file contains an SQL procedure to downgrade from schema Rev3 to Rev2 (version = 6).
  -- It actually deletes the ChildCount table and triggers
  -- It actually does not uninstall ChildrenIndex2 because it is anyway more efficient than 
     -- ChildrenIndex and is not incompatible with previous revisions.

-- remove the childCount column in resources
DO $body$
BEGIN
	IF EXISTS (SELECT * FROM information_schema.columns WHERE table_schema='public' AND table_name='resources' AND column_name='childcount') THEN
		ALTER TABLE Resources DROP COLUMN childcount;
	ELSE
		raise notice 'the resources.childcount column does not exists';
	END IF;

END $body$;


------------------- re-install old CreateInstance function -------------------
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
        INSERT INTO "resources" VALUES (DEFAULT, 0, patient_public_id, NULL) RETURNING internalid INTO patient_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_patient := 0;
            SELECT internalid INTO patient_internal_id FROM "resources" WHERE publicId = patient_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction
    END;

	BEGIN
        INSERT INTO "resources" VALUES (DEFAULT, 1, study_public_id, patient_internal_id) RETURNING internalid INTO study_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_study := 0;
            SELECT internalid INTO study_internal_id FROM "resources" WHERE publicId = study_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction    END;
    END;

	BEGIN
	    INSERT INTO "resources" VALUES (DEFAULT, 2, series_public_id, study_internal_id) RETURNING internalid INTO series_internal_id;
    EXCEPTION
        WHEN unique_violation THEN
            is_new_series := 0;
            SELECT internalid INTO series_internal_id FROM "resources" WHERE publicId = series_public_id FOR UPDATE;  -- also locks the resource and its parent to prevent from deletion while we complete this transaction    END;
    END;

  	BEGIN
		INSERT INTO "resources" VALUES (DEFAULT, 3, instance_public_id, series_internal_id) RETURNING internalid INTO instance_internal_id;
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





DROP TRIGGER IF EXISTS DecrementChildCount ON Resources;
DROP TRIGGER IF EXISTS IncrementChildCount ON Resources;
DROP FUNCTION ComputeMissingChildCount;
DROP FUNCTION UpdateChildCount;

-- restore the previous PatientRecyclingOrder logic although it was buggy wrt protected patients
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
        UPDATE GlobalIntegers SET value = value + 1 WHERE key = 7 RETURNING value INTO newSeq;
        IF is_update > 0 THEN
            -- Note: Protected patients are not listed in this table !  So, they won't be updated
            UPDATE PatientRecyclingOrder SET seq = newSeq WHERE PatientRecyclingOrder.patientId = patient_id;
        ELSE
            INSERT INTO PatientRecyclingOrder VALUES (newSeq, patient_id);
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

INSERT INTO GlobalIntegers
    SELECT 7, CAST(COALESCE(MAX(seq), 0) AS BIGINT) FROM PatientRecyclingOrder
    ON CONFLICT DO NOTHING;

-----------

-- set the global properties that actually documents the DB version, revision and some of the capabilities
-- modify only the ones that have changed
DELETE FROM GlobalProperties WHERE property IN (4, 11);
INSERT INTO GlobalProperties VALUES (4, 2); -- GlobalProperty_DatabasePatchLevel
