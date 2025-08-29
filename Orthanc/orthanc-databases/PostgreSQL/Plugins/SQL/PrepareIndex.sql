-- This SQL file creates a DB in Rev5 directly
-- It is also run after upgrade scripts to create new tables and or create/replace triggers and functions.
-- This script is self contained, it contains everything that needs to be run to create an Orthanc DB.
-- Note to developers: 
--   - it is and must stay idempotent.
--   - it is executed when the DB is "locked", only one Orthanc instance can execute it at a given time.                

CREATE TABLE IF NOT EXISTS GlobalProperties(
       property INTEGER PRIMARY KEY,
       value TEXT
       );

CREATE TABLE IF NOT EXISTS Resources(
       internalId BIGSERIAL NOT NULL PRIMARY KEY,
       resourceType INTEGER NOT NULL,
       publicId VARCHAR(64) NOT NULL,
    --    parentId BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       parentId BIGINT REFERENCES Resources(internalId),
	   childCount INTEGER,
       CONSTRAINT UniquePublicId UNIQUE (publicId)
       );

CREATE TABLE IF NOT EXISTS MainDicomTags(
       id BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       tagGroup INTEGER,
       tagElement INTEGER,
       value TEXT,
       PRIMARY KEY(id, tagGroup, tagElement)
       );

CREATE TABLE IF NOT EXISTS DicomIdentifiers(
       id BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       tagGroup INTEGER,
       tagElement INTEGER,
       value TEXT,
       PRIMARY KEY(id, tagGroup, tagElement)
       );

CREATE TABLE IF NOT EXISTS Metadata(
       id BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       type INTEGER NOT NULL,
       value TEXT,
       revision INTEGER,
       PRIMARY KEY(id, type)
       );

CREATE TABLE IF NOT EXISTS AttachedFiles(
       id BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       fileType INTEGER,
       uuid VARCHAR(64) NOT NULL,
       compressedSize BIGINT,
       uncompressedSize BIGINT,
       compressionType INTEGER,
       uncompressedHash VARCHAR(40),
       compressedHash VARCHAR(40),
       revision INTEGER,
       customData BYTEA,           -- new in schema rev 5
       PRIMARY KEY(id, fileType)
       );              

CREATE TABLE IF NOT EXISTS Changes(
       seq BIGSERIAL NOT NULL PRIMARY KEY,
       changeType INTEGER,
       internalId BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
       resourceType INTEGER,
       date VARCHAR(64)
       );

CREATE TABLE IF NOT EXISTS ExportedResources(
       seq BIGSERIAL NOT NULL PRIMARY KEY,
       resourceType INTEGER,
       publicId VARCHAR(64),
       remoteModality TEXT,
       patientId VARCHAR(64),
       studyInstanceUid TEXT,
       seriesInstanceUid TEXT,
       sopInstanceUid TEXT,
       date VARCHAR(64)
       ); 

CREATE TABLE IF NOT EXISTS Labels(
        id BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
        label TEXT, 
        PRIMARY KEY(id, label)
        );

CREATE TABLE IF NOT EXISTS GlobalIntegers(
       key INTEGER PRIMARY KEY,
       value BIGINT);
-- GlobalIntegers keys:
-- 0: CompressedSize
-- 1: UncompressedSize
-- 2: PatientsCount
-- 3: StudiesCount
-- 4: SeriesCount
-- 5: InstancesCount
-- 6: ChangeSeq
-- 7: PatientRecyclingOrderSeq  (removed in 7.0)

CREATE TABLE IF NOT EXISTS ServerProperties(
        server VARCHAR(64) NOT NULL,
        property INTEGER, value TEXT, 
        PRIMARY KEY(server, property)
        );

DO $$
DECLARE
    pg_version text;
BEGIN
    SELECT version() INTO pg_version;

    IF substring(pg_version from 'PostgreSQL (\d+)\.')::int >= 11 THEN
        -- PostgreSQL 11 or later

        -- new ChildrenIndex2 introduced in Rev3 (replacing previous ChildrenIndex)
        EXECUTE 'CREATE INDEX IF NOT EXISTS ChildrenIndex2 ON Resources USING btree (parentId ASC NULLS LAST) INCLUDE (publicId, internalId)';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS ChildrenIndex2 ON Resources USING btree (parentId ASC NULLS LAST, publicId, internalId)';
    END IF;
END $$;


CREATE INDEX IF NOT EXISTS PublicIndex ON Resources(publicId);
CREATE INDEX IF NOT EXISTS ResourceTypeIndex ON Resources(resourceType);

CREATE INDEX IF NOT EXISTS MainDicomTagsIndex ON MainDicomTags(id);
CREATE INDEX IF NOT EXISTS DicomIdentifiersIndex1 ON DicomIdentifiers(id);
CREATE INDEX IF NOT EXISTS DicomIdentifiersIndex2 ON DicomIdentifiers(tagGroup, tagElement);
CREATE INDEX IF NOT EXISTS DicomIdentifiersIndex3 ON DicomIdentifiers(tagGroup, tagElement, value);
CREATE INDEX IF NOT EXISTS DicomIdentifiersIndexValues ON DicomIdentifiers(value);

CREATE INDEX IF NOT EXISTS ChangesIndex ON Changes(internalId);
CREATE INDEX IF NOT EXISTS LabelsIndex1 ON LABELS(id);
CREATE INDEX IF NOT EXISTS LabelsIndex2 ON LABELS(label);

------------------- Trigram index creation -------------------


-- Apply fix for performance issue (speed up wildcard search by using GIN trigrams). This implements the patch suggested
-- in issue #47, BUT we also keep the original "DicomIdentifiersIndexValues", as it leads to better
-- performance for "strict" searches (i.e. searches involving no wildcard).
-- https://www.postgresql.org/docs/current/static/pgtrgm.html
-- https://orthanc.uclouvain.be/bugs/show_bug.cgi?id=47

DO $body$
begin
	IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name='pg_trgm') THEN
		CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE INDEX IF NOT EXISTS DicomIdentifiersIndexValues2 ON DicomIdentifiers USING gin(value gin_trgm_ops);
	ELSE
		RAISE NOTICE 'pg_trgm extension is not available on you system';
	END IF;
END $body$;


--------------------- PatientRecyclingOrder -------------------
-- from rev 99, we always maintain a PatientRecyclingOrder metadata, no matter if the patient is protected or not
CREATE OR REPLACE FUNCTION PatientAddedOrUpdated(
    IN patient_id BIGINT
    )
RETURNS VOID AS $body$
BEGIN
    DECLARE
        newSeq BIGINT;
    BEGIN
        INSERT INTO Metadata (id, type, value, revision)
        VALUES (patient_id, 19, nextval('PatientRecyclingOrderSequence')::TEXT, 0)
        ON CONFLICT (id, type)
        DO UPDATE SET value = EXCLUDED.value, revision = EXCLUDED.revision;
    END;
END;
$body$ LANGUAGE plpgsql;


------------------- DeleteResource function -------------------

CREATE OR REPLACE FUNCTION DeleteResource(
    IN id BIGINT,
    OUT remaining_ancestor_resource_type INTEGER,
    OUT remaining_anncestor_public_id TEXT) AS $body$

DECLARE
    deleted_resource_row RECORD;
    deleted_parent_row RECORD;
    deleted_grand_parent_row RECORD;
    deleted_grand_grand_parent_row RECORD;

    locked_parent_row RECORD;
    locked_resource_row RECORD;

BEGIN

    SET client_min_messages = warning;   -- suppress NOTICE:  relation "deletedresources" already exists, skipping

    -- note: temporary tables are created at connection level -> they are likely to exist.
    -- These tables are used by the triggers
    CREATE TEMPORARY TABLE IF NOT EXISTS DeletedResources(
        resourceType INTEGER NOT NULL,
        publicId VARCHAR(64) NOT NULL
        );

    RESET client_min_messages;

    -- clear the temporary table in case it has been created earlier in the connection
    DELETE FROM DeletedResources;

    -- create/clear the DeletedFiles temporary table
    PERFORM CreateDeletedFilesTemporaryTable();


    -- Before deleting an object, we need to lock its parent until the end of the transaction to avoid that
    -- 2 threads deletes the last 2 instances of a series at the same time -> none of them would realize
    -- that they are deleting the last instance and the parent resources would not be deleted.
    -- Locking only the immediate parent is sufficient to prevent from this.
    SELECT * INTO locked_parent_row FROM resources WHERE internalid = (SELECT parentid FROM resources WHERE internalid = id) FOR UPDATE;

    -- Before deleting the resource itself, we lock it to retrieve the resourceType and to make sure not 2 connections try to
    -- delete it at the same time
    SELECT * INTO locked_resource_row FROM resources WHERE internalid = id FOR UPDATE;

    -- before delete the resource itself, we must delete its grand-grand-children, the grand-children and its children no to violate 
    -- the parentId referencing an existing primary key constrain.  This is actually implementing the ON DELETE CASCADE that was on the parentId in previous revisions.
    
    -- If this resource has grand-grand-children, delete them
    if locked_resource_row.resourceType < 1 THEN
        WITH grand_grand_children_to_delete AS (SELECT grandGrandChildLevel.internalId, grandGrandChildLevel.resourceType, grandGrandChildLevel.publicId
                                                FROM Resources childLevel
                                                INNER JOIN Resources grandChildLevel ON childLevel.internalId = grandChildLevel.parentId
                                                INNER JOIN Resources grandGrandChildLevel ON grandChildLevel.internalId = grandGrandChildLevel.parentId
                                                WHERE childLevel.parentId = id),
        
        deleted_grand_grand_children_rows AS (DELETE FROM Resources WHERE internalId IN (SELECT internalId FROM grand_grand_children_to_delete)
                                              RETURNING resourceType, publicId)

        INSERT INTO DeletedResources SELECT resourceType, publicId FROM deleted_grand_grand_children_rows; 
    END IF;

    -- If this resource has grand-children, delete them
    if locked_resource_row.resourceType < 2 THEN
        WITH grand_children_to_delete AS (SELECT grandChildLevel.internalId, grandChildLevel.resourceType, grandChildLevel.publicId
                                          FROM Resources childLevel
                                          INNER JOIN Resources grandChildLevel ON childLevel.internalId = grandChildLevel.parentId
                                          WHERE childLevel.parentId = id),
        
        deleted_grand_children_rows AS (DELETE FROM Resources WHERE internalId IN (SELECT internalId FROM grand_children_to_delete)
                                        RETURNING resourceType, publicId)

        INSERT INTO DeletedResources SELECT resourceType, publicId FROM deleted_grand_children_rows; 
    END IF;

    -- If this resource has children, delete them
    if locked_resource_row.resourceType < 3 THEN
        WITH deleted_children AS (DELETE FROM Resources 
                                  WHERE parentId = id
                                  RETURNING resourceType, publicId)
        INSERT INTO DeletedResources SELECT resourceType, publicId FROM deleted_children; 
    END IF;


    -- delete the resource itself
    DELETE FROM Resources WHERE internalId=id RETURNING * INTO deleted_resource_row;

    -- keep track of the deleted resources for C++ code
    INSERT INTO DeletedResources VALUES (deleted_resource_row.resourceType, deleted_resource_row.publicId);
  
    -- If this resource still has siblings, keep track of the remaining parent
    -- (a parent that must not be deleted but whose LastUpdate must be updated)
    SELECT resourceType, publicId INTO remaining_ancestor_resource_type, remaining_anncestor_public_id
        FROM Resources 
        WHERE internalId = deleted_resource_row.parentId
            AND EXISTS (SELECT 1 FROM Resources WHERE parentId = deleted_resource_row.parentId);

	IF deleted_resource_row.resourceType > 0 THEN
        -- If this resource is the latest child, delete the parent
        DELETE FROM Resources WHERE internalId = deleted_resource_row.parentId
                                    AND NOT EXISTS (SELECT 1 FROM Resources WHERE parentId = deleted_resource_row.parentId)
                                    RETURNING * INTO deleted_parent_row;
        IF FOUND THEN
            INSERT INTO DeletedResources VALUES (deleted_parent_row.resourceType, deleted_parent_row.publicId);

            IF deleted_parent_row.resourceType > 0 THEN
                -- If this resource is the latest child, delete the parent
                DELETE FROM Resources WHERE internalId = deleted_parent_row.parentId
                                    AND NOT EXISTS (SELECT 1 FROM Resources WHERE parentId = deleted_parent_row.parentId)
                                    RETURNING * INTO deleted_grand_parent_row;
                IF FOUND THEN
                    INSERT INTO DeletedResources VALUES (deleted_grand_parent_row.resourceType, deleted_grand_parent_row.publicId);

                    IF deleted_grand_parent_row.resourceType > 0 THEN
                        -- If this resource is the latest child, delete the parent
                        DELETE FROM Resources WHERE internalId = deleted_grand_parent_row.parentId
                                            AND NOT EXISTS (SELECT 1 FROM Resources WHERE parentId = deleted_grand_parent_row.parentId)
                                            RETURNING * INTO deleted_grand_parent_row;
                        IF FOUND THEN
                            INSERT INTO DeletedResources VALUES (deleted_grand_parent_row.resourceType, deleted_grand_parent_row.publicId);
                        END IF;
                    END IF;
                END IF;
            END IF;
        END IF;
    END IF;

END;

$body$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION CreateDeletedFilesTemporaryTable(
) RETURNS VOID AS $body$

BEGIN

    SET client_min_messages = warning;   -- suppress NOTICE:  relation "DeletedFiles" already exists, skipping

    -- note: temporary tables created at connection level -> they are likely to exist
    CREATE TEMPORARY TABLE IF NOT EXISTS DeletedFiles(
        uuid VARCHAR(64) NOT NULL,
        fileType INTEGER,
        compressedSize BIGINT,
        uncompressedSize BIGINT,
        compressionType INTEGER,
        uncompressedHash VARCHAR(40),
        compressedHash VARCHAR(40),
        revision INTEGER,
        customData BYTEA
        );

    RESET client_min_messages;

    -- clear the temporary table in case it has been created earlier in the connection
    DELETE FROM DeletedFiles;
END;

$body$ LANGUAGE plpgsql;

-- Keep track of deleted files such that the C++ code knows which files have been deleted.
-- Attached files are deleted by cascade when the related resource is deleted.
CREATE OR REPLACE FUNCTION AttachedFileDeletedFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  INSERT INTO DeletedFiles VALUES
    (old.uuid, old.filetype, old.compressedSize,
     old.uncompressedSize, old.compressionType,
     old.uncompressedHash, old.compressedHash,
     old.revision, old.customData);
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS AttachedFileDeleted on AttachedFiles;
CREATE TRIGGER AttachedFileDeleted
AFTER DELETE ON AttachedFiles
FOR EACH ROW
EXECUTE PROCEDURE AttachedFileDeletedFunc();


CREATE OR REPLACE FUNCTION DeleteAttachment(
    IN resource_id BIGINT,
    IN file_type INTEGER) 
RETURNS VOID AS $body$
BEGIN
    -- create/clear the DeletedFiles temporary table
    PERFORM CreateDeletedFilesTemporaryTable();

    DELETE FROM AttachedFiles WHERE id = resource_id AND fileType = file_type;
END;
$body$ LANGUAGE plpgsql;


------------------- Fast Statistics -------------------

-- initial population of GlobalIntegers if not already there
INSERT INTO GlobalIntegers
    SELECT 0, CAST(COALESCE(SUM(compressedSize), 0) AS BIGINT) FROM AttachedFiles
    ON CONFLICT DO NOTHING;

INSERT INTO GlobalIntegers
    SELECT 1, CAST(COALESCE(SUM(uncompressedSize), 0) AS BIGINT) FROM AttachedFiles
    ON CONFLICT DO NOTHING;

INSERT INTO GlobalIntegers
    SELECT 2, CAST(COALESCE(COUNT(*), 0) AS BIGINT) FROM Resources WHERE resourceType = 0  -- Count patients
    ON CONFLICT DO NOTHING;

INSERT INTO GlobalIntegers
    SELECT 3, CAST(COALESCE(COUNT(*), 0) AS BIGINT) FROM Resources WHERE resourceType = 1  -- Count studies
    ON CONFLICT DO NOTHING;

INSERT INTO GlobalIntegers
    SELECT 4, CAST(COALESCE(COUNT(*), 0) AS BIGINT) FROM Resources WHERE resourceType = 2  -- Count series
    ON CONFLICT DO NOTHING;

INSERT INTO GlobalIntegers
    SELECT 5, CAST(COALESCE(COUNT(*), 0) AS BIGINT) FROM Resources WHERE resourceType = 3  -- Count instances
    ON CONFLICT DO NOTHING;


-- this table stores all changes that needs to be performed to the GlobalIntegers table
-- This way, each transaction can add row independently in this table without having to lock
-- any row (which was the case with previous FastTotalSize).
-- These changes will be applied at regular interval by an external thread or when someone
-- requests the statistics
CREATE TABLE IF NOT EXISTS GlobalIntegersChanges(
    key INTEGER,
    value BIGINT);

CREATE OR REPLACE FUNCTION UpdateSingleStatistic(
    IN statistics_key INTEGER,
    OUT new_value BIGINT
) AS $body$
BEGIN

  -- Delete the current changes, sum them and update the GlobalIntegers row.
  -- New rows can be added in the meantime, they won't be deleted or summed.
  WITH rows_to_delete AS (
    SELECT ctid
    FROM GlobalIntegersChanges
    WHERE GlobalIntegersChanges.key = statistics_key
    LIMIT 10000                  -- by default, the UpdateSingleStatistics is called every seconds -> we should never get more than 10000 entries to compute so this is mainly useful to catch up with long standing entries from previous plugins version without the Housekeeping thread (see https://discourse.orthanc-server.org/t/increase-in-cpu-usage-of-database-after-update-to-orthanc-1-12-7/6057/6)
  ), 
  deleted_rows AS (
      DELETE FROM GlobalIntegersChanges
      WHERE GlobalIntegersChanges.ctid IN (SELECT ctid FROM rows_to_delete)
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


CREATE OR REPLACE FUNCTION UpdateStatistics(
  OUT patients_cunt BIGINT,
  OUT studies_count BIGINT,
  OUT series_count BIGINT,
  OUT instances_count BIGINT,
  OUT total_compressed_size BIGINT,
  OUT total_uncompressed_size BIGINT
) AS $body$
BEGIN

  SELECT UpdateSingleStatistic(0) INTO total_compressed_size;
  SELECT UpdateSingleStatistic(1) INTO total_uncompressed_size;
  SELECT UpdateSingleStatistic(2) INTO patients_cunt;
  SELECT UpdateSingleStatistic(3) INTO studies_count;
  SELECT UpdateSingleStatistic(4) INTO series_count;
  SELECT UpdateSingleStatistic(5) INTO instances_count;

END;
$body$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION IncrementResourcesTrackerFunc()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO GlobalIntegersChanges VALUES(new.resourceType + 2, 1);
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION DecrementResourcesTrackerFunc()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO GlobalIntegersChanges VALUES(old.resourceType + 2, -1);
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION AttachedFileIncrementSizeFunc()
RETURNS TRIGGER AS $body$
BEGIN
  INSERT INTO GlobalIntegersChanges VALUES(0, new.compressedSize);
  INSERT INTO GlobalIntegersChanges VALUES(1, new.uncompressedSize);
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION AttachedFileDecrementSizeFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  INSERT INTO GlobalIntegersChanges VALUES(0, -old.compressedSize);
  INSERT INTO GlobalIntegersChanges VALUES(1, -old.uncompressedSize);
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS AttachedFileIncrementSize on AttachedFiles;
CREATE TRIGGER AttachedFileIncrementSize
AFTER INSERT ON AttachedFiles
FOR EACH ROW
EXECUTE PROCEDURE AttachedFileIncrementSizeFunc();

DROP TRIGGER IF EXISTS AttachedFileDecrementSize on AttachedFiles;
CREATE TRIGGER AttachedFileDecrementSize
AFTER DELETE ON AttachedFiles
FOR EACH ROW
EXECUTE PROCEDURE AttachedFileDecrementSizeFunc();

DROP TRIGGER IF EXISTS IncrementResourcesTracker on Resources;
CREATE TRIGGER IncrementResourcesTracker
AFTER INSERT ON Resources
FOR EACH ROW
EXECUTE PROCEDURE IncrementResourcesTrackerFunc();

DROP TRIGGER IF EXISTS DecrementResourcesTracker on Resources;
CREATE TRIGGER DecrementResourcesTracker
AFTER DELETE ON Resources
FOR EACH ROW
EXECUTE PROCEDURE DecrementResourcesTrackerFunc();


------------------- InsertOrUpdateMetadata function -------------------
CREATE OR REPLACE FUNCTION InsertOrUpdateMetadata(resource_ids BIGINT[],
                                                  metadata_types INTEGER[], 
                                                  metadata_values TEXT[],
                                                  revisions INTEGER[])
RETURNS VOID AS $body$
BEGIN
  	FOR i IN 1 .. ARRAY_LENGTH(resource_ids, 1) LOOP
		-- RAISE NOTICE 'Parameter %: % % %', i, resource_ids[i], metadata_types[i], metadata_values[i];
		INSERT INTO Metadata VALUES(resource_ids[i], metadata_types[i], metadata_values[i], revisions[i]) 
          ON CONFLICT (id, type) DO UPDATE SET value = EXCLUDED.value, revision = EXCLUDED.revision;
	END LOOP;
  
END;
$body$ LANGUAGE plpgsql;


------------------- GetLastChange function -------------------
DROP TRIGGER IF EXISTS InsertedChange ON Changes;

-- insert the value if not already there
INSERT INTO GlobalIntegers
    SELECT 6, CAST(COALESCE(MAX(seq), 0) AS BIGINT) FROM Changes
    ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION InsertedChangeFunc() 
RETURNS TRIGGER AS $body$
BEGIN
    UPDATE GlobalIntegers SET value = new.seq WHERE key = 6;
    RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS InsertedChange on Changes;
CREATE TRIGGER InsertedChange
AFTER INSERT ON Changes
FOR EACH ROW
EXECUTE PROCEDURE InsertedChangeFunc();


------------------- CreateInstance function -------------------
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
	-- Assume the parent series already exists to minimize exceptions.  
    -- Most of the instances are not the first of their series - especially when we need high performances.

	is_new_patient := 1;
	is_new_study := 1;
	is_new_series := 1;
	is_new_instance := 1;

	-- First, check if the series already exists
	SELECT internalid INTO series_internal_id FROM "resources" WHERE publicId = series_public_id;

	IF series_internal_id IS NOT NULL THEN
	    -- RAISE NOTICE 'series-found %', series_internal_id;
		is_new_patient := 0;
		is_new_study := 0;
		is_new_series := 0;

		-- If the series exists, insert the instance directly
		BEGIN
			INSERT INTO "resources" VALUES (DEFAULT, 3, instance_public_id, series_internal_id, 0) RETURNING internalid INTO instance_internal_id;
		EXCEPTION
			WHEN unique_violation THEN
				is_new_instance := 0;
				SELECT internalid INTO instance_internal_id FROM "resources" WHERE publicId = instance_public_id;
		END;

    	SELECT internalid INTO patient_internal_id FROM "resources" WHERE publicId = patient_public_id;
		SELECT internalid INTO study_internal_id FROM "resources" WHERE publicId = study_public_id;

	ELSE
	    -- RAISE NOTICE 'series-not-found';

		-- If the series does not exist, execute the "full" steps
		BEGIN
			INSERT INTO "resources" VALUES (DEFAULT, 0, patient_public_id, NULL, 0) RETURNING internalid INTO patient_internal_id;
		EXCEPTION
			WHEN unique_violation THEN
				is_new_patient := 0;
				SELECT internalid INTO patient_internal_id FROM "resources" WHERE publicId = patient_public_id;
		END;
	
		BEGIN
			INSERT INTO "resources" VALUES (DEFAULT, 1, study_public_id, patient_internal_id, 0) RETURNING internalid INTO study_internal_id;
		EXCEPTION
			WHEN unique_violation THEN
				is_new_study := 0;
				SELECT internalid INTO study_internal_id FROM "resources" WHERE publicId = study_public_id;
		END;
	
		BEGIN
			INSERT INTO "resources" VALUES (DEFAULT, 2, series_public_id, study_internal_id, 0) RETURNING internalid INTO series_internal_id;
		EXCEPTION
			WHEN unique_violation THEN
				is_new_series := 0;
				SELECT internalid INTO series_internal_id FROM "resources" WHERE publicId = series_public_id;
		END;
	
		BEGIN
			INSERT INTO "resources" VALUES (DEFAULT, 3, instance_public_id, series_internal_id, 0) RETURNING internalid INTO instance_internal_id;
		EXCEPTION
			WHEN unique_violation THEN
				is_new_instance := 0;
				SELECT internalid INTO instance_internal_id FROM "resources" WHERE publicId = instance_public_id;
		END;

	END IF;


	IF is_new_instance > 0 THEN
		-- Move the patient to the end of the recycling order.
		PERFORM PatientAddedOrUpdated(patient_internal_id);
	END IF;
END;
$body$ LANGUAGE plpgsql;


-- function to compute a statistic in a ReadOnly transaction
CREATE OR REPLACE FUNCTION ComputeStatisticsReadOnly(
    IN statistics_key INTEGER,
    OUT accumulated_value BIGINT
) RETURNS BIGINT AS $body$

DECLARE
    current_value BIGINT;
    
BEGIN

    SELECT VALUE FROM GlobalIntegers
    INTO current_value
    WHERE key = statistics_key;

    SELECT COALESCE(SUM(value), 0) + current_value FROM GlobalIntegersChanges
    INTO accumulated_value
    WHERE key = statistics_key;

END;
$body$ LANGUAGE plpgsql;


-- -- new in Rev3

-- Computes the childCount for a number of resources for which it has not been computed yet.
-- This is actually used only after an update to Rev3.  A thread will call this function
-- at regular interval to update all missing values and stop once all values have been processed.
CREATE OR REPLACE FUNCTION ComputeMissingChildCount(
    IN batch_size BIGINT,
    OUT updated_rows_count BIGINT
) RETURNS BIGINT AS $body$
BEGIN
	UPDATE Resources AS r
    SET childCount = (SELECT COUNT(childLevel.internalId)
                      FROM Resources AS childLevel
                      WHERE childLevel.parentId = r.internalId)
    WHERE internalId IN (
        SELECT internalId FROM Resources
        WHERE resourceType < 3 AND childCount IS NULL
        LIMIT batch_size);
    
    -- Get the number of rows affected
    GET DIAGNOSTICS updated_rows_count = ROW_COUNT;
END;
$body$ LANGUAGE plpgsql;


-- -- new in rev4

-- This table records all resource entries whose childCount column is currently invalid
-- because of recent addition/removal of a child.
-- This way, each transaction that is adding/removing a child can add row independently 
-- in this table without having to lock the parent resource row.
-- At regular interval, the DB housekeeping thread updates the childCount column of
-- resources with an entry in this table.
CREATE TABLE IF NOT EXISTS InvalidChildCounts(
    id BIGINT REFERENCES Resources(internalId) ON DELETE CASCADE,
    updatedAt TIMESTAMP DEFAULT NOW());

-- note: an index has been added in rev6

-- Updates the Resources.childCount column with the delta that have not been committed yet.
-- A thread will call this function at regular interval to update all pending values.
CREATE OR REPLACE FUNCTION UpdateInvalidChildCounts(
    OUT updated_rows_count BIGINT
) RETURNS BIGINT AS $body$
DECLARE
  locked_resources_ids BIGINT[];
BEGIN

    -- Lock the resources rows asap to prevent deadlocks
    -- that will need to be retried
    SELECT ARRAY(SELECT internalId
                 FROM Resources
                 WHERE internalId IN (SELECT DISTINCT id FROM InvalidChildCounts)
                 FOR UPDATE SKIP LOCKED)
    INTO locked_resources_ids;

    -- New rows can be added in the meantime, they won't be taken into account this time.
    WITH deleted_rows AS (
        DELETE FROM InvalidChildCounts
        WHERE id = ANY(locked_resources_ids)
        RETURNING id
    )

	UPDATE Resources
    SET childCount = (SELECT COUNT(childLevel.internalId)
                      FROM Resources AS childLevel
                      WHERE childLevel.parentId = Resources.internalId)
    WHERE internalid = ANY(locked_resources_ids);
    
    -- Get the number of rows affected
    GET DIAGNOSTICS updated_rows_count = ROW_COUNT;

END;
$body$ LANGUAGE plpgsql;



DROP TRIGGER IF EXISTS IncrementChildCount on Resources;
DROP TRIGGER IF EXISTS DecrementChildCount on Resources;

CREATE OR REPLACE FUNCTION UpdateChildCount()
RETURNS TRIGGER AS $body$
BEGIN
    IF TG_OP = 'INSERT' THEN
		IF new.parentId IS NOT NULL THEN
            -- mark the parent's childCount as invalid
			INSERT INTO InvalidChildCounts VALUES(new.parentId);
        END IF;
	
    ELSIF TG_OP = 'DELETE' THEN

		IF old.parentId IS NOT NULL THEN
            BEGIN
                -- mark the parent's childCount as invalid
                INSERT INTO InvalidChildCounts VALUES(old.parentId);
            EXCEPTION
                -- when deleting the last child of a parent, the insert will fail (this is expected)
                WHEN foreign_key_violation THEN NULL;
            END;
        END IF;
        
    END IF;
    RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

CREATE TRIGGER IncrementChildCount
AFTER INSERT ON Resources
FOR EACH ROW
EXECUTE PROCEDURE UpdateChildCount();

CREATE TRIGGER DecrementChildCount
AFTER DELETE ON Resources
FOR EACH ROW
WHEN (OLD.parentId IS NOT NULL)
EXECUTE PROCEDURE UpdateChildCount();


-- new in 1.12.8 (rev 5)

CREATE TABLE IF NOT EXISTS KeyValueStores(
       storeId TEXT NOT NULL,
       key TEXT NOT NULL,
       value BYTEA NOT NULL,
       PRIMARY KEY(storeId, key)  -- Prevents duplicates
       );

CREATE TABLE IF NOT EXISTS Queues (
       id BIGSERIAL NOT NULL PRIMARY KEY,
       queueId TEXT NOT NULL,
       value BYTEA NOT NULL
);

CREATE INDEX IF NOT EXISTS QueuesIndex ON Queues (queueId, id);

-- new in rev 6

CREATE SEQUENCE IF NOT EXISTS PatientRecyclingOrderSequence INCREMENT 1 START 1;

CREATE OR REPLACE FUNCTION ProtectPatient(patient_id BIGINT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO Metadata (id, type, value, revision) -- 18 = IsProtected
    VALUES (patient_id, 18, 'true', 0)
    ON CONFLICT (id, type)
    DO UPDATE SET value = EXCLUDED.value, revision = EXCLUDED.revision;
END;
$$ LANGUAGE plpgsql;

-- remove IsProtected and update PatientRecyclingOrder
CREATE OR REPLACE FUNCTION UnprotectPatient(patient_id BIGINT)
RETURNS VOID AS $$
BEGIN
    DELETE FROM Metadata WHERE id = patient_id AND type = 18; -- 18 = IsProtected

    INSERT INTO Metadata (id, type, value, revision)
    VALUES (patient_id, 19, nextval('PatientRecyclingOrderSequence')::TEXT, 0)
    ON CONFLICT (id, type)
    DO UPDATE SET value = EXCLUDED.value, revision = EXCLUDED.revision;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS AuditLogs (
    ts TIMESTAMP DEFAULT NOW(),
    sourcePlugin TEXT NOT NULL,
    userId TEXT NOT NULL,
    resourceType INTEGER NOT NULL,
    resourceId VARCHAR(64) NOT NULL,
    action TEXT NOT NULL,
    logData BYTEA
);

CREATE INDEX IF NOT EXISTS AuditLogsUserId ON AuditLogs (userId);
CREATE INDEX IF NOT EXISTS AuditLogsResourceId ON AuditLogs (resourceId);
CREATE INDEX IF NOT EXISTS AuditLogsAction ON AuditLogs (action);
CREATE INDEX IF NOT EXISTS AuditLogsSourcePlugin ON AuditLogs (sourcePlugin);

CREATE INDEX IF NOT EXISTS InvalidChildCountsId ON InvalidChildCounts (id); -- see https://discourse.orthanc-server.org/t/increase-in-cpu-usage-of-database-after-update-to-orthanc-1-12-7/6057/6



-- set the global properties that actually documents the DB version, revision and some of the capabilities
DELETE FROM GlobalProperties WHERE property IN (1, 4, 6, 10, 11, 12, 13, 14);
INSERT INTO GlobalProperties VALUES (1, 6); -- GlobalProperty_DatabaseSchemaVersion
INSERT INTO GlobalProperties VALUES (4, 6); -- GlobalProperty_DatabasePatchLevel
INSERT INTO GlobalProperties VALUES (6, 1); -- GlobalProperty_GetTotalSizeIsFast
INSERT INTO GlobalProperties VALUES (10, 1); -- GlobalProperty_HasTrigramIndex
INSERT INTO GlobalProperties VALUES (11, 3); -- GlobalProperty_HasCreateInstance  -- this is actually the 3rd version of HasCreateInstance
INSERT INTO GlobalProperties VALUES (12, 1); -- GlobalProperty_HasFastCountResources
INSERT INTO GlobalProperties VALUES (13, 1); -- GlobalProperty_GetLastChangeIndex
INSERT INTO GlobalProperties VALUES (14, 1); -- GlobalProperty_HasComputeStatisticsReadOnly
