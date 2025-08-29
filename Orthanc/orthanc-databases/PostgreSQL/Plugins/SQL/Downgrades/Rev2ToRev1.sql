-- This file contains an SQL procedure to downgrade from schema Rev2 to Rev1 (version = 6, revision = 1).
-- It reinstalls all triggers and temporary tables that have been removed or replaced in Rev2

-- note: we don't not remove the unique constraints that have been added - they should not 
--       create any issues.

-- these constraints were introduced in Rev2
ALTER TABLE Resources DROP CONSTRAINT UniquePublicId;
ALTER TABLE PatientRecyclingOrder DROP CONSTRAINT UniquePatientId;

-- the CreateInstance has been replaced in Rev2, reinstall the Rev1
DROP FUNCTION CreateInstance;
CREATE FUNCTION CreateInstance(
  IN patient TEXT,
  IN study TEXT,
  IN series TEXT,
  IN instance TEXT,
  OUT isNewPatient BIGINT,
  OUT isNewStudy BIGINT,
  OUT isNewSeries BIGINT,
  OUT isNewInstance BIGINT,
  OUT patientKey BIGINT,
  OUT studyKey BIGINT,
  OUT seriesKey BIGINT,
  OUT instanceKey BIGINT) AS $body$

DECLARE
  patientSeq BIGINT;
  countRecycling BIGINT;

BEGIN
  SELECT internalId FROM Resources INTO instanceKey WHERE publicId = instance AND resourceType = 3;

  IF NOT (instanceKey IS NULL) THEN
    -- This instance already exists, stop here
    isNewInstance := 0;
  ELSE
    SELECT internalId FROM Resources INTO patientKey WHERE publicId = patient AND resourceType = 0;
    SELECT internalId FROM Resources INTO studyKey WHERE publicId = study AND resourceType = 1;
    SELECT internalId FROM Resources INTO seriesKey WHERE publicId = series AND resourceType = 2;

    IF patientKey IS NULL THEN
      -- Must create a new patient
      IF NOT (studyKey IS NULL AND seriesKey IS NULL AND instanceKey IS NULL) THEN
         RAISE EXCEPTION 'Broken invariant';
      END IF;

      INSERT INTO Resources VALUES (DEFAULT, 0, patient, NULL) RETURNING internalId INTO patientKey;
      isNewPatient := 1;
    ELSE
      isNewPatient := 0;
    END IF;
  
    IF (patientKey IS NULL) THEN
       RAISE EXCEPTION 'Broken invariant';
    END IF;

    IF studyKey IS NULL THEN
      -- Must create a new study
      IF NOT (seriesKey IS NULL AND instanceKey IS NULL) THEN
         RAISE EXCEPTION 'Broken invariant';
      END IF;

      INSERT INTO Resources VALUES (DEFAULT, 1, study, patientKey) RETURNING internalId INTO studyKey;
      isNewStudy := 1;
    ELSE
      isNewStudy := 0;
    END IF;

    IF (studyKey IS NULL) THEN
       RAISE EXCEPTION 'Broken invariant';
    END IF;

    IF seriesKey IS NULL THEN
      -- Must create a new series
      IF NOT (instanceKey IS NULL) THEN
         RAISE EXCEPTION 'Broken invariant';
      END IF;

      INSERT INTO Resources VALUES (DEFAULT, 2, series, studyKey) RETURNING internalId INTO seriesKey;
      isNewSeries := 1;
    ELSE
      isNewSeries := 0;
    END IF;
  
    IF (seriesKey IS NULL OR NOT instanceKey IS NULL) THEN
       RAISE EXCEPTION 'Broken invariant';
    END IF;

    INSERT INTO Resources VALUES (DEFAULT, 3, instance, seriesKey) RETURNING internalId INTO instanceKey;
    isNewInstance := 1;

    -- Move the patient to the end of the recycling order
    SELECT seq FROM PatientRecyclingOrder WHERE patientId = patientKey INTO patientSeq;

    IF NOT (patientSeq IS NULL) THEN
       -- The patient is not protected
       SELECT COUNT(*) FROM (SELECT * FROM PatientRecyclingOrder WHERE seq >= patientSeq LIMIT 2) AS tmp INTO countRecycling;
       IF countRecycling = 2 THEN
          -- The patient was not at the end of the recycling order
          DELETE FROM PatientRecyclingOrder WHERE seq = patientSeq;
          INSERT INTO PatientRecyclingOrder VALUES(DEFAULT, patientKey);
       END IF;
    END IF;
  END IF;  
END;

$body$ LANGUAGE plpgsql;


-- these tables have been deleted in Rev2:
CREATE TABLE DeletedFiles(
       uuid VARCHAR(64) NOT NULL,      -- 0
       fileType INTEGER,               -- 1
       compressedSize BIGINT,          -- 2
       uncompressedSize BIGINT,        -- 3
       compressionType INTEGER,        -- 4
       uncompressedHash VARCHAR(40),   -- 5
       compressedHash VARCHAR(40)      -- 6
       );

CREATE TABLE RemainingAncestor(
       resourceType INTEGER NOT NULL,
       publicId VARCHAR(64) NOT NULL
       );

CREATE TABLE DeletedResources(
       resourceType INTEGER NOT NULL,
       publicId VARCHAR(64) NOT NULL
       );


-- these triggers have been introduced in Rev2, remove them
DROP TRIGGER IF EXISTS IncrementResourcesTracker on Resources;
DROP TRIGGER IF EXISTS DecrementResourcesTracker on Resources;
DROP FUNCTION IF EXISTS IncrementResourcesTrackerFunc;
DROP FUNCTION IF EXISTS DecrementResourcesTrackerFunc;

-- this trigger has been removed in Rev2, reinstall it
CREATE OR REPLACE FUNCTION CountResourcesTrackerFunc()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE GlobalIntegers SET value = value + 1 WHERE key = new.resourceType + 2;
    RETURN new;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE GlobalIntegers SET value = value - 1 WHERE key = old.resourceType + 2;
    RETURN old;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER CountResourcesTracker
AFTER INSERT OR DELETE ON Resources
FOR EACH ROW
EXECUTE PROCEDURE CountResourcesTrackerFunc();

-- this trigger was introduced in Rev2, remove it:
DROP FUNCTION IF EXISTS InsertOrUpdateMetadata;

-- reinstall old triggers:
CREATE OR REPLACE FUNCTION AttachedFileIncrementSizeFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  UPDATE GlobalIntegers SET value = value + new.compressedSize WHERE key = 0;
  UPDATE GlobalIntegers SET value = value + new.uncompressedSize WHERE key = 1;
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION AttachedFileDecrementSizeFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  UPDATE GlobalIntegers SET value = value - old.compressedSize WHERE key = 0;
  UPDATE GlobalIntegers SET value = value - old.uncompressedSize WHERE key = 1;
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER AttachedFileIncrementSize ON AttachedFiles;
CREATE TRIGGER AttachedFileIncrementSize
AFTER INSERT ON AttachedFiles
FOR EACH ROW
EXECUTE PROCEDURE AttachedFileIncrementSizeFunc();

DROP TRIGGER AttachedFileDecrementSize ON AttachedFiles;
CREATE TRIGGER AttachedFileDecrementSize
AFTER DELETE ON AttachedFiles
FOR EACH ROW
EXECUTE PROCEDURE AttachedFileDecrementSizeFunc();

-- these functions have been introduced in Rev2:
DROP FUNCTION IF EXISTS UpdateStatistics;
DROP FUNCTION IF EXISTS UpdateSingleStatistic;

-- this table has been introduced in Rev2:
DROP TABLE IF EXISTS GlobalIntegersChanges;

-- these functions have been introduced in Rev2:
DROP FUNCTION IF EXISTS CreateDeletedFilesTemporaryTable;
DROP FUNCTION IF EXISTS DeleteResource;

-- reinstall this old trigger:
CREATE OR REPLACE FUNCTION ResourceDeletedFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  --RAISE NOTICE 'Delete resource %', old.parentId;
  INSERT INTO DeletedResources VALUES (old.resourceType, old.publicId);
  
  -- http://stackoverflow.com/a/11299968/881731
  IF EXISTS (SELECT 1 FROM Resources WHERE parentId = old.parentId) THEN
    -- Signal that the deleted resource has a remaining parent
    INSERT INTO RemainingAncestor
      SELECT resourceType, publicId FROM Resources WHERE internalId = old.parentId;
  ELSE
    -- Delete a parent resource when its unique child is deleted 
    DELETE FROM Resources WHERE internalId = old.parentId;
  END IF;
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ResourceDeleted ON Resources;
CREATE TRIGGER ResourceDeleted
AFTER DELETE ON Resources
FOR EACH ROW
EXECUTE PROCEDURE ResourceDeletedFunc();

-- reinstall this old trigger:
CREATE OR REPLACE FUNCTION PatientAddedFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  -- The "0" corresponds to "OrthancPluginResourceType_Patient"
  IF new.resourceType = 0 THEN
    INSERT INTO PatientRecyclingOrder VALUES (DEFAULT, new.internalId);
  END IF;
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS PatientAdded ON Resources;
CREATE TRIGGER PatientAdded
AFTER INSERT ON Resources
FOR EACH ROW
EXECUTE PROCEDURE PatientAddedFunc();


-- set the global properties that actually documents the DB version, revision and some of the capabilities
-- modify only the ones that have changed
DELETE FROM GlobalProperties WHERE property IN (4, 11);
INSERT INTO GlobalProperties VALUES (4, 1); -- GlobalProperty_DatabasePatchLevel
INSERT INTO GlobalProperties VALUES (11, 2); -- GlobalProperty_HasCreateInstance