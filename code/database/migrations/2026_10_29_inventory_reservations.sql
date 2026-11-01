-- Apply once to an existing Timaflu database. Do not run twice.
-- Kept apart from physical warehouse quantity. Created only after a real sale is recorded.
CREATE TABLE Voorraadreservering (
    bestelling_id INT NOT NULL,
    product_id INT NOT NULL,
    aantal INT NOT NULL,
    PRIMARY KEY (bestelling_id, product_id),
    FOREIGN KEY (bestelling_id, product_id)
        REFERENCES Bestelregel(bestelling_id, product_id),
    CHECK (aantal > 0)
);
