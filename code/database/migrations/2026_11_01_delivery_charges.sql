-- Eenmalige uitbreiding van een bestaande Timaflu-database.
-- Uitvoeren na migraties tot en met 2026-10-31.
ALTER TABLE Factuur
  ADD COLUMN extra_bezorgkosten_excl_btw DECIMAL(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN extra_bezorgkosten_btw DECIMAL(10,2) NOT NULL DEFAULT 0,
  ADD COLUMN extra_bezorgkosten_incl_btw DECIMAL(10,2) NOT NULL DEFAULT 0;
ALTER TABLE Bestelling
  ADD COLUMN extra_bezorgkosten_factuur_id INT NULL,
  ADD CONSTRAINT fk_bestelling_bezorgkosten_factuur
    FOREIGN KEY (extra_bezorgkosten_factuur_id) REFERENCES Factuur(factuur_id);
