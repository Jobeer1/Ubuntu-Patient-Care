CREATE TABLE IF NOT EXISTS GlobalIntegers(
       property INTEGER PRIMARY KEY,
       value BIGINT
       );


DELETE FROM GlobalIntegers WHERE property = 0;

INSERT INTO GlobalIntegers
SELECT 0, COALESCE(MAX(seq), 0) FROM Changes;


DROP TRIGGER IF EXISTS ChangeAdded;

CREATE TRIGGER ChangeAdded
AFTER INSERT ON Changes
FOR EACH ROW
BEGIN
  UPDATE GlobalIntegers SET value = new.seq WHERE property = 0@
END;
