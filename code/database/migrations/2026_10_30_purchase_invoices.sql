-- Inkoopfacturen: expliciet onderdeel van de administratie uit de casus.
CREATE TABLE Inkoopfactuur (
    inkoopfactuur_id INT AUTO_INCREMENT PRIMARY KEY,
    leverancier_id INT NOT NULL,
    factuurdatum DATE NOT NULL,
    bedrag DECIMAL(10,2) NOT NULL,
    betaald_op DATE,
    FOREIGN KEY (leverancier_id) REFERENCES Leverancier(leverancier_id),
    CHECK (bedrag >= 0)
);
