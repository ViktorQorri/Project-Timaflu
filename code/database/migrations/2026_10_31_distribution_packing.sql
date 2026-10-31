-- Store the number of moving boxes used to pack an order.
ALTER TABLE Bestelling
    ADD COLUMN aantal_verhuisdozen INT NOT NULL DEFAULT 0,
    ADD CONSTRAINT chk_bestelling_aantal_verhuisdozen
        CHECK (aantal_verhuisdozen >= 0);
