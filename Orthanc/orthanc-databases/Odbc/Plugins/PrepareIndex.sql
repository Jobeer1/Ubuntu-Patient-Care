CREATE TABLE GlobalProperties(
       property INTEGER PRIMARY KEY,
       value ${LONGTEXT}
       );

CREATE TABLE ServerProperties(
       server VARCHAR(64) NOT NULL,
       property INTEGER NOT NULL,
       value ${LONGTEXT},
       PRIMARY KEY(server, property)
       );

CREATE TABLE Resources(
       internalId ${AUTOINCREMENT_TYPE},
       resourceType INTEGER NOT NULL,
       publicId VARCHAR(64) NOT NULL,
       parentId BIGINT
       );

CREATE TABLE MainDicomTags(
       id BIGINT NOT NULL,
       tagGroup INTEGER NOT NULL,
       tagElement INTEGER NOT NULL,
       value VARCHAR(255),
       PRIMARY KEY(id, tagGroup, tagElement),
       CONSTRAINT MainDicomTags1 FOREIGN KEY (id) REFERENCES Resources(internalId) ON DELETE CASCADE
       );

CREATE TABLE DicomIdentifiers(
       id BIGINT NOT NULL,
       tagGroup INTEGER NOT NULL,
       tagElement INTEGER NOT NULL,
       value VARCHAR(255),
       PRIMARY KEY(id, tagGroup, tagElement),
       CONSTRAINT DicomIdentifiers1 FOREIGN KEY (id) REFERENCES Resources(internalId) ON DELETE CASCADE
       );

CREATE TABLE Metadata(
       id BIGINT NOT NULL,
       type INTEGER NOT NULL,
       value ${LONGTEXT},
       revision INTEGER,
       PRIMARY KEY(id, type),
       CONSTRAINT Metadata1 FOREIGN KEY (id) REFERENCES Resources(internalId) ON DELETE CASCADE
       );
       
CREATE TABLE AttachedFiles(
       id BIGINT NOT NULL,
       fileType INTEGER,
       uuid VARCHAR(64) NOT NULL,
       compressedSize BIGINT,
       uncompressedSize BIGINT,
       compressionType INTEGER,
       uncompressedHash VARCHAR(40),
       compressedHash VARCHAR(40),
       revision INTEGER,
       PRIMARY KEY(id, fileType),
       CONSTRAINT AttachedFiles1 FOREIGN KEY (id) REFERENCES Resources(internalId) ON DELETE CASCADE
       );              

CREATE TABLE Changes(
       seq ${AUTOINCREMENT_TYPE},
       changeType INTEGER,
       internalId BIGINT NOT NULL,
       resourceType INTEGER,
       date VARCHAR(64),
       CONSTRAINT Changes1 FOREIGN KEY (internalId) REFERENCES Resources(internalId) ON DELETE CASCADE
       );
       
CREATE TABLE ExportedResources(
       seq ${AUTOINCREMENT_TYPE},
       resourceType INTEGER,
       publicId VARCHAR(64),
       remoteModality VARCHAR(64),
       patientId VARCHAR(64),
       studyInstanceUid VARCHAR(128),
       seriesInstanceUid VARCHAR(128),
       sopInstanceUid VARCHAR(128),
       date VARCHAR(64)
       ); 

CREATE TABLE PatientRecyclingOrder(
       seq ${AUTOINCREMENT_TYPE},
       patientId BIGINT NOT NULL,
       CONSTRAINT PatientRecyclingOrder1 FOREIGN KEY (patientId) REFERENCES Resources(internalId) ON DELETE CASCADE
       );

CREATE INDEX ChildrenIndex ON Resources(parentId);
CREATE INDEX PublicIndex ON Resources(publicId);
CREATE INDEX ResourceTypeIndex ON Resources(resourceType);
CREATE INDEX PatientRecyclingIndex ON PatientRecyclingOrder(patientId);

CREATE INDEX MainDicomTagsIndex ON MainDicomTags(id);
CREATE INDEX DicomIdentifiersIndex1 ON DicomIdentifiers(id);
CREATE INDEX DicomIdentifiersIndex2 ON DicomIdentifiers(tagGroup, tagElement);
CREATE INDEX DicomIdentifiersIndexValues ON DicomIdentifiers(value);

CREATE INDEX ChangesIndex ON Changes(internalId);



-- New tables wrt. Orthanc core
CREATE TABLE DeletedFiles(   -- Same structure as AttachedFiles
       id BIGINT NOT NULL,
       fileType INTEGER,
       uuid VARCHAR(64) NOT NULL,
       compressedSize BIGINT,
       uncompressedSize BIGINT,
       compressionType INTEGER,
       uncompressedHash VARCHAR(40),
       compressedHash VARCHAR(40),
       revision INTEGER
       );

CREATE TABLE DeletedResources(
       internalId BIGINT NOT NULL PRIMARY KEY,
       resourceType INTEGER NOT NULL,
       publicId VARCHAR(64) NOT NULL
       );



-- Set version of database to 6
INSERT INTO GlobalProperties VALUES(1, '6');
