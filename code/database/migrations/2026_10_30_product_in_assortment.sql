-- Apply once to an existing Timaflu database. Do not run twice.
-- Issue #13: removing a product from the assortment keeps the row, because
-- orders, deliveries and invoices refer to it. Existing products stay in the assortment.
ALTER TABLE Product
    ADD COLUMN in_assortiment BOOLEAN NOT NULL DEFAULT TRUE
    AFTER minimumvoorraad;
