-- This file contains part of the changes required to upgrade from Revision 4 to Revision 5 (DB version 6)
-- It actually contains only the changes that:
   -- can not be executed with an idempotent statement in SQL
   -- or would polute the PrepareIndex.sql
-- This file is executed only if the current schema is in revision 4 and it is executed 
-- before PrepareIndex.sql that is idempotent.



DO $body$
BEGIN

    BEGIN
        ALTER TABLE AttachedFiles ADD COLUMN customData BYTEA;
    EXCEPTION
        WHEN duplicate_column THEN RAISE NOTICE 'column customData already exists in AttachedFiles.';
    END;

END $body$ LANGUAGE plpgsql;
