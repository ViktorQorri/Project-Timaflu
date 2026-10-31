-- Existing supplier orders have unknown dates and statuses; do not infer them.
ALTER TABLE Inkoopbestelling
    ADD COLUMN besteld_op DATETIME NULL,
    ADD COLUMN status_naam VARCHAR(30) NULL;
