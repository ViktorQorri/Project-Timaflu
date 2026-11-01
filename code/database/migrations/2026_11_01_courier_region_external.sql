-- EER Koerier and case distribution: three regions and external rush couriers.
-- Existing couriers retain their records; staff must assign their actual region.
ALTER TABLE Koerier
    ADD COLUMN regio VARCHAR(100) NULL AFTER naam,
    ADD COLUMN extern BOOLEAN NOT NULL DEFAULT FALSE AFTER regio;
