CREATE TABLE Files(
       path TEXT PRIMARY KEY NOT NULL,
       time INTEGER NOT NULL,
       size INTEGER NOT NULL,
       isDicom INTEGER NOT NULL,
       instanceId TEXT NOT NULL
       );

CREATE TABLE Attachments(
       uuid TEXT PRIMARY KEY NOT NULL,
       instanceId NOT NULL
       );

CREATE INDEX InstancesIndex ON Files(instanceId);
