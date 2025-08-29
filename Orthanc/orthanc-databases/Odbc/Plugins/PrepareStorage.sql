CREATE TABLE StorageArea(
       uuid VARCHAR(64) NOT NULL PRIMARY KEY,
       content ${BINARY} NOT NULL,
       type INTEGER NOT NULL);
