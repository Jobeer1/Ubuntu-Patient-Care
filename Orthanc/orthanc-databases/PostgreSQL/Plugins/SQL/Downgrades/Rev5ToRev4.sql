-- This file contains an SQL procedure to downgrade from schema Rev5 to Rev4 (version = 6).
-- It removes the column that has been added in Rev5

-- these constraints were introduced in Rev5
ALTER TABLE AttachedFiles DROP COLUMN customData;

-- reinstall previous triggers
CREATE OR REPLACE FUNCTION CreateDeletedFilesTemporaryTable(
) RETURNS VOID AS $body$

BEGIN

    SET client_min_messages = warning;   -- suppress NOTICE:  relation "deletedresources" already exists, skipping
    
    -- note: temporary tables are created at session (connection) level -> they are likely to exist
    CREATE TEMPORARY TABLE IF NOT EXISTS DeletedFiles(
        uuid VARCHAR(64) NOT NULL,
        fileType INTEGER,
        compressedSize BIGINT,
        uncompressedSize BIGINT,
        compressionType INTEGER,
        uncompressedHash VARCHAR(40),
        compressedHash VARCHAR(40)
        );

    RESET client_min_messages;

    -- clear the temporary table in case it has been created earlier in the session
    DELETE FROM DeletedFiles;
END;

$body$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION AttachedFileDeletedFunc() 
RETURNS TRIGGER AS $body$
BEGIN
  INSERT INTO DeletedFiles VALUES
    (old.uuid, old.filetype, old.compressedSize,
     old.uncompressedSize, old.compressionType,
     old.uncompressedHash, old.compressedHash);
  RETURN NULL;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS AttachedFileDeleted on AttachedFiles;
CREATE TRIGGER AttachedFileDeleted
AFTER DELETE ON AttachedFiles
FOR EACH ROW
EXECUTE PROCEDURE AttachedFileDeletedFunc();


DROP TABLE IF EXISTS KeyValueStores;

DROP TABLE IF EXISTS Queues;

DROP INDEX IF EXISTS QueuesIndex;


DELETE FROM GlobalProperties WHERE property IN (4);
INSERT INTO GlobalProperties VALUES (4, 4); -- GlobalProperty_DatabasePatchLevel

