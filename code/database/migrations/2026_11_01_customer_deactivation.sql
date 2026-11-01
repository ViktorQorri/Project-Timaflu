-- AD07: Deactivate customers while preserving order and invoice history.
-- Existing customer acquisition discount field remains unchanged.
ALTER TABLE Klant ADD COLUMN actief BOOLEAN NOT NULL DEFAULT TRUE;
