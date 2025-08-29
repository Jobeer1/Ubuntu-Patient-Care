DROP PROCEDURE IF EXISTS CreateInstance;

CREATE PROCEDURE CreateInstance(
       IN patient TEXT,
       IN study TEXT,
       IN series TEXT,
       IN instance TEXT,
       OUT isNewPatient BOOLEAN,
       OUT isNewStudy BOOLEAN,
       OUT isNewSeries BOOLEAN,
       OUT isNewInstance BOOLEAN,
       OUT patientKey BIGINT,
       OUT studyKey BIGINT,
       OUT seriesKey BIGINT,
       OUT instanceKey BIGINT)
BEGIN  
  DECLARE recyclingSeq BIGINT@

  SELECT internalId INTO instanceKey FROM Resources WHERE publicId = instance AND resourceType = 3@

  IF NOT instanceKey IS NULL THEN
    -- This instance already exists, stop here
    SELECT 0 INTO isNewInstance@
  ELSE
    SELECT internalId INTO patientKey FROM Resources WHERE publicId = patient AND resourceType = 0@
    SELECT internalId INTO studyKey FROM Resources WHERE publicId = study AND resourceType = 1@
    SELECT internalId INTO seriesKey FROM Resources WHERE publicId = series AND resourceType = 2@

    IF patientKey IS NULL THEN
       -- Must create a new patient
       IF NOT (studyKey IS NULL AND seriesKey IS NULL AND instanceKey IS NULL) THEN
          SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Broken invariant 1'@
       END IF@

       INSERT INTO Resources VALUES (DEFAULT, 0, patient, NULL)@
       SELECT LAST_INSERT_ID() INTO patientKey@
       SELECT 1 INTO isNewPatient@
    ELSE
       SELECT 0 INTO isNewPatient@
    END IF@

    IF patientKey IS NULL THEN
       SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Broken invariant 2'@
    END IF@

    IF studyKey IS NULL THEN
       -- Must create a new study
       IF NOT (seriesKey IS NULL AND instanceKey IS NULL) THEN
          SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Broken invariant 3'@
       END IF@

       INSERT INTO Resources VALUES (DEFAULT, 1, study, patientKey)@
       SELECT LAST_INSERT_ID() INTO studyKey@
       SELECT 1 INTO isNewStudy@
    ELSE
       SELECT 0 INTO isNewStudy@
    END IF@

    IF studyKey IS NULL THEN
       SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Broken invariant 4'@
    END IF@

    IF seriesKey IS NULL THEN
      -- Must create a new series
      IF NOT (instanceKey IS NULL) THEN
         SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Broken invariant 5'@
      END IF@

      INSERT INTO Resources VALUES (DEFAULT, 2, series, studyKey)@
       SELECT LAST_INSERT_ID() INTO seriesKey@
       SELECT 1 INTO isNewSeries@
    ELSE
       SELECT 0 INTO isNewSeries@
    END IF@
  
    IF (seriesKey IS NULL OR NOT instanceKey IS NULL) THEN
       SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Broken invariant 6'@
    END IF@

    INSERT INTO Resources VALUES (DEFAULT, 3, instance, seriesKey)@
    SELECT LAST_INSERT_ID() INTO instanceKey@
    SELECT 1 INTO isNewInstance@

    -- Move the patient to the end of the recycling order
    IF NOT isNewPatient THEN
       SELECT seq FROM PatientRecyclingOrder WHERE patientId = patientKey INTO recyclingSeq@
       
       IF NOT recyclingSeq IS NULL THEN
          -- The patient is not protected
          DELETE FROM PatientRecyclingOrder WHERE seq = recyclingSeq@
          INSERT INTO PatientRecyclingOrder VALUES (DEFAULT, patientKey)@
       END IF@
    END IF@
  END IF@
END;
