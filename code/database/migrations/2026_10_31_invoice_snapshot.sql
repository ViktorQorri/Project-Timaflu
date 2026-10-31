-- Historical invoice snapshots: NULL means the actual applied amount was not stored.
-- Never backfill unknown discounts by recomputing with current values.
ALTER TABLE Factuur
    ADD COLUMN bedrag_excl_btw DECIMAL(10,2) NULL,
    ADD COLUMN btw_bedrag DECIMAL(10,2) NULL,
    ADD COLUMN bedrag_incl_btw DECIMAL(10,2) NULL,
    ADD COLUMN bestellingskorting DECIMAL(10,2) NULL,
    ADD COLUMN bedrag_na_bestellingskorting DECIMAL(10,2) NULL,
    ADD COLUMN eenmalige_korting DECIMAL(10,2) NULL,
    ADD COLUMN bedrag_na_eenmalige_korting DECIMAL(10,2) NULL,
    ADD COLUMN klantenkorting DECIMAL(10,2) NULL,
    ADD COLUMN totaal_bedrag DECIMAL(10,2) NULL;
