-- Issue #57: existing purchase records have unknown original dates and state.
-- Do not backfill today's date or claim earlier orders were just placed.
-- This migration does not model supplier shipping or receipt of incoming stock.
ALTER TABLE Inkoopbestelling
    ADD COLUMN besteld_op DATETIME NULL,
    ADD COLUMN status_naam VARCHAR(30) NULL;
