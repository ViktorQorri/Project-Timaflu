-- Apply to existing Timaflu databases BEFORE deploying weekly invoicing.
-- Run ONCE, after a backup. Existing legacy invoices retain NULL week_start
-- and keep their historical amounts unchanged; no backfill is invented.
ALTER TABLE Factuur
    ADD COLUMN week_start DATE NULL AFTER factuurdatum,
    ADD COLUMN afzenderadres VARCHAR(255) NULL AFTER week_start,
    ADD COLUMN factuuradres VARCHAR(255) NULL AFTER afzenderadres,
    ADD CONSTRAINT uq_factuur_klant_week UNIQUE (klant_id, week_start);
