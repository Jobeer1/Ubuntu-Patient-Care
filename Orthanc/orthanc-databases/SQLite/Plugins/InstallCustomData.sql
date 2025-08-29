
-- Add new column for customData
ALTER TABLE AttachedFiles ADD COLUMN customData TEXT;
ALTER TABLE DeletedFiles ADD COLUMN revision INTEGER;
ALTER TABLE DeletedFiles ADD COLUMN customData TEXT;


DROP TRIGGER AttachedFileDeleted;

CREATE TRIGGER AttachedFileDeleted
AFTER DELETE ON AttachedFiles
BEGIN
   INSERT INTO DeletedFiles VALUES(old.uuid, old.filetype, old.compressedSize,
                                   old.uncompressedSize, old.compressionType,
                                   old.uncompressedHash, old.compressedHash,
                                   old.revision, old.customData);
END;
