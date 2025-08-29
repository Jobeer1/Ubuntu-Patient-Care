-- add the revision columns if not yet done

DO $body$
BEGIN
	IF NOT EXISTS (SELECT * FROM information_schema.columns WHERE table_schema='public' AND table_name='metadata' AND column_name='revision') THEN
		ALTER TABLE Metadata ADD COLUMN revision INTEGER;
	ELSE
		raise notice 'the metadata.revision column already exists';
	END IF;

	IF NOT EXISTS (SELECT * FROM information_schema.columns WHERE table_schema='public' AND table_name='attachedfiles' AND column_name='revision') THEN
		ALTER TABLE AttachedFiles ADD COLUMN revision INTEGER;
	ELSE
		raise notice 'the attachedfiles.revision column already exists';
	END IF;

END $body$;

