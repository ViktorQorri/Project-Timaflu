-- Add the order lifecycle states required by issue #12 to an existing database.
INSERT IGNORE INTO OrderStatus (naam)
VALUES ('nieuw'), ('ingepakt'), ('niet afgeleverd'), ('gefactureerd');

UPDATE Bestelling
SET status_naam = 'nieuw'
WHERE status_naam IS NULL;

ALTER TABLE Bestelling
    MODIFY COLUMN status_naam VARCHAR(40) NOT NULL DEFAULT 'nieuw';
