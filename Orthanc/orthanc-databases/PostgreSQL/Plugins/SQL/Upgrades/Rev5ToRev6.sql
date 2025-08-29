CREATE SEQUENCE IF NOT EXISTS PatientRecyclingOrderSequence INCREMENT 1 START 1;

-- the protection mechanisms changed in rev 499.  We now use a metadata (18: IsProtected)
-- while, in the past, patients where protected by not appearing in the PatientRecyclingOrder

-- Step 1: Identify all patients that are not in PatientRecyclingOrder (those are the protected patients)
-- The "0" corresponds to "OrthancPluginResourceType_Patient"
WITH ProtectedPatients AS (
    SELECT r.internalId AS internalId
    FROM Resources r
    LEFT JOIN PatientRecyclingOrder pro ON r.internalId = pro.patientId
    WHERE r.resourceType = 0
    AND pro.patientId IS NULL
) 
, UnprotectedPatients AS (
    SELECT patientId AS internalId
    FROM PatientRecyclingOrder
    ORDER BY seq ASC
)

-- Step 2: Prepare the data for both metadata types
, MetadataToInsert AS (
    -- mark protected patient in 18: IsProtected
    SELECT internalId, 18 AS metadataType, 'true' AS metadataValue
    FROM ProtectedPatients    

    UNION ALL

    -- copy previous recycling order in 19: RecyclingOrder
    SELECT internalId, 19 AS metadataType, nextval('PatientRecyclingOrderSequence')::TEXT AS metadataValue
    FROM UnprotectedPatients    
)

-- Step 3: Insert the Metadata (since the metadata are new, there should not be any conflicts)
INSERT INTO Metadata (id, type, value, revision)
SELECT internalId, metadataType, metadataValue, 0
FROM MetadataToInsert
ON CONFLICT (id, type)
DO UPDATE SET value = EXCLUDED.value, revision = EXCLUDED.revision;

-- The PatientRecyclingOrder table can now be removed

DROP TABLE PatientRecyclingOrder;

DROP TRIGGER IF EXISTS PatientAdded on Resources;
DROP FUNCTION IF EXISTS PatientAddedFunc;
DROP FUNCTION IF EXISTS PatientAddedOrUpdated;

-- The DeletedResources trigger is not used anymore

DROP TRIGGER IF EXISTS ResourceDeleted ON Resources;
DROP FUNCTION IF EXISTS ResourceDeletedFunc();

-- The ON DELETE CASCADE on the Resources.parentId has been removed since this is now implemented 
-- in the DeleteResource function
-- Drop the existing foreign key constraint and add a new one without ON DELETE CASCADE in a single command
ALTER TABLE Resources
DROP CONSTRAINT IF EXISTS resources_parentid_fkey,
ADD CONSTRAINT resources_parentid_fkey FOREIGN KEY (parentId) REFERENCES Resources(internalId);