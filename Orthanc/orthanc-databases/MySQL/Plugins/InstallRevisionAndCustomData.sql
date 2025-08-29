ALTER TABLE AttachedFiles ADD COLUMN revision INTEGER;
ALTER TABLE DeletedFiles ADD COLUMN revision INTEGER;
ALTER TABLE Metadata ADD COLUMN revision INTEGER;

ALTER TABLE AttachedFiles ADD COLUMN customData LONGTEXT;
ALTER TABLE DeletedFiles ADD COLUMN customData LONGTEXT;

DROP TRIGGER AttachedFileDeleted;

CREATE TRIGGER AttachedFileDeleted
AFTER DELETE ON AttachedFiles
FOR EACH ROW
  BEGIN
    INSERT INTO DeletedFiles VALUES(old.uuid, old.filetype, old.compressedSize,
                                    old.uncompressedSize, old.compressionType,
                                    old.uncompressedHash, old.compressedHash,
                                    old.revision, old.customData)@
  END;


DROP TRIGGER ResourceDeleted;

CREATE TRIGGER ResourceDeleted
BEFORE DELETE ON Resources
FOR EACH ROW
  BEGIN
    INSERT INTO DeletedFiles SELECT uuid, fileType, compressedSize, uncompressedSize, compressionType, uncompressedHash, compressedHash, revision, customData FROM AttachedFiles WHERE id=old.internalId@
  END;