-- This file contains part of the changes required to upgrade from Revision 2 to Revision 3 (DB version 6 and revision 2)
-- It actually contains only the changes that:
   -- can not be executed with an idempotent statement in SQL
   -- or would polute the PrepareIndex.sql
   -- do facilite an up-time upgrade
-- This file is executed only if the current schema is in revision 2 and it is executed 
-- before PrepareIndex.sql that is idempotent.


-- create a new ChildrenIndex2 that is replacing ChildrenIndex.
-- We create it in this partial update so it can be created while the system is up !
DO $$
DECLARE
    pg_version text;
BEGIN
    SELECT version() INTO pg_version;

    IF substring(pg_version from 'PostgreSQL (\d+)\.')::int >= 11 THEN
        -- PostgreSQL 11 or later
        EXECUTE 'CREATE INDEX IF NOT EXISTS ChildrenIndex2 ON Resources USING btree (parentId ASC NULLS LAST) INCLUDE (publicId, internalId)';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS ChildrenIndex2 ON Resources USING btree (parentId ASC NULLS LAST, publicId, internalId)';
    END IF;
END $$;

DROP INDEX IF EXISTS ChildrenIndex;  -- replaced by ChildrenIndex2 but no need to uninstall ChildrenIndex2 when downgrading

-- add the childCount columns in Resources if not yet done

DO $body$
BEGIN
	IF NOT EXISTS (SELECT * FROM information_schema.columns WHERE table_schema='public' AND table_name='resources' AND column_name='childcount') THEN
		ALTER TABLE Resources ADD COLUMN childcount INTEGER;
	ELSE
		raise notice 'the resources.childcount column already exists';
	END IF;

END $body$;



-- other changes performed in PrepareIndex.sql:
  -- add ChildCount triggers
