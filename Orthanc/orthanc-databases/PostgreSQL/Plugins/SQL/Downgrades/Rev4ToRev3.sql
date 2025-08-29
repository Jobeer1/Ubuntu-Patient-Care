-- This file contains an SQL procedure to downgrade from schema Rev4 to Rev3 (version = 6).
-- It re-installs the old childcount trigger mechanisms

DO $$
DECLARE
    current_revision TEXT;
    expected_revision TEXT;
BEGIN
    expected_revision := '4';

    SELECT value INTO current_revision FROM GlobalProperties WHERE property = 4; -- GlobalProperty_DatabasePatchLevel

    IF current_revision != expected_revision THEN
        RAISE EXCEPTION 'Unexpected schema revision % to run this script.  Expected revision = %', current_revision, expected_revision;
    END IF;
END $$;

---

DROP TRIGGER IF EXISTS IncrementChildCount on Resources;
DROP TRIGGER IF EXISTS DecrementChildCount on Resources;

CREATE OR REPLACE FUNCTION UpdateChildCount()
RETURNS TRIGGER AS $body$
BEGIN
    IF TG_OP = 'INSERT' THEN
		IF new.parentId IS NOT NULL THEN
            -- try to increment the childcount from the parent
            -- note that we already have the lock on this row because the parent is locked in CreateInstance
			UPDATE Resources
		    SET childCount = childCount + 1
		    WHERE internalId = new.parentId AND childCount IS NOT NULL;
		
            -- this should only happen for old studies whose childCount has not yet been computed
            -- note: this child has already been added so it will be counted
		    IF NOT FOUND THEN
		        UPDATE Resources
                SET childCount = (SELECT COUNT(*)
		                              FROM Resources
		                              WHERE internalId = new.parentId)
		        WHERE internalId = new.parentId;
		    END IF;
        END IF;
	
    ELSIF TG_OP = 'DELETE' THEN

		IF old.parentId IS NOT NULL THEN

            -- Decrement the child count for the parent
            -- note that we already have the lock on this row because the parent is locked in DeleteResource
            UPDATE Resources
            SET childCount = childCount - 1
            WHERE internalId = old.parentId AND childCount IS NOT NULL;
		
            -- this should only happen for old studies whose childCount has not yet been computed
            -- note: this child has already been removed so it will not be counted
		    IF NOT FOUND THEN
		        UPDATE Resources
                SET childCount = (SELECT COUNT(*)
		                              FROM Resources
		                              WHERE internalId = new.parentId)
		        WHERE internalId = new.parentId;
		    END IF;
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

-----------

-- set the global properties that actually documents the DB version, revision and some of the capabilities
-- modify only the ones that have changed
DELETE FROM GlobalProperties WHERE property IN (4, 11);
INSERT INTO GlobalProperties VALUES (4, 3); -- GlobalProperty_DatabasePatchLevel
