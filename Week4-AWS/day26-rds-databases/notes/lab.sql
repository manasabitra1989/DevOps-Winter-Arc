-- Day 26: AWS RDS PostgreSQL lab
-- Run with psql after connecting to the intended database.
-- No credentials belong in this file.

CREATE TABLE lab_notes (
    id SERIAL PRIMARY KEY,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO lab_notes (note)
VALUES ('Day 26 RDS connection test');

SELECT id, note, created_at
FROM lab_notes
ORDER BY id;

-- After taking the manual snapshot, run this on the ORIGINAL database:
-- INSERT INTO lab_notes (note)
-- VALUES ('Added after snapshot');
--
-- On the RESTORED database, run the SELECT again. The original row should
-- exist; the row added after the snapshot should not.
