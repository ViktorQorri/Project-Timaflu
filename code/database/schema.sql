-- =========================================
-- 1. ADRES
-- Bron: huidige situatie, Bestellingen,
-- Voorraad en Acquisitie.
-- =========================================

CREATE TABLE Adres (
    adres_id INT AUTO_INCREMENT PRIMARY KEY,
    adres VARCHAR(255) NOT NULL
);


-- =========================================
-- 2. KLANT
-- Bron: huidige situatie, Bestellingen.
-- =========================================

CREATE TABLE Klant (
    klant_id INT AUTO_INCREMENT PRIMARY KEY,
    bedrijfsnaam VARCHAR(100) NOT NULL,
    telefoonnummer VARCHAR(25),
    contactpersoon VARCHAR(100),
    eenmalige_korting_toegezegd BOOLEAN NOT NULL DEFAULT FALSE,
    afleveradres_id INT NOT NULL,
    betaaladres_id INT NOT NULL,

    FOREIGN KEY (afleveradres_id)
        REFERENCES Adres(adres_id),

    FOREIGN KEY (betaaladres_id)
        REFERENCES Adres(adres_id)
);


-- =========================================
-- 3. POTENTIELE KLANT
-- Bron: huidige situatie, Acquisitie.
-- =========================================

CREATE TABLE PotentieleKlant (
    potentiele_klant_id INT AUTO_INCREMENT PRIMARY KEY,
    bedrijfsnaam VARCHAR(100) NOT NULL,
    contactpersoon VARCHAR(100),
    contactgegevens VARCHAR(255),
    adres_id INT NOT NULL,
    klant_id INT UNIQUE,
    opvolging_afgesloten BOOLEAN NOT NULL DEFAULT FALSE,

    FOREIGN KEY (adres_id)
        REFERENCES Adres(adres_id),

    FOREIGN KEY (klant_id)
        REFERENCES Klant(klant_id)
);


-- =========================================
-- 4. ACQUISITIEBEZOEK
-- Bron: productbeschrijving, Acquisitie.
-- =========================================

CREATE TABLE Acquisitiebezoek (
    bezoek_id INT AUTO_INCREMENT PRIMARY KEY,
    potentiele_klant_id INT NOT NULL,
    bezoekdatum DATE NOT NULL,

    FOREIGN KEY (potentiele_klant_id)
        REFERENCES PotentieleKlant(potentiele_klant_id)
);


-- =========================================
-- 5. PRODUCT
-- Bron: huidige situatie, Productcatalogus.
-- =========================================

CREATE TABLE Product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    artikelnummer VARCHAR(50) NOT NULL UNIQUE,
    bestelcode VARCHAR(50) NOT NULL UNIQUE,
    productnaam VARCHAR(100) NOT NULL,
    prijs_per_grootverpakking DECIMAL(10,2) NOT NULL,
    verpakkingssoort VARCHAR(50),
    aantal_detailverpakkingen INT NOT NULL,
    korte_omschrijving VARCHAR(255),
    lange_omschrijving TEXT,
    minimale_bestelhoeveelheid INT NOT NULL,
    minimumvoorraad INT NOT NULL,
    intern_bestelbaar BOOLEAN NOT NULL DEFAULT TRUE,
-- FALSE = verwijderd uit het assortiment. De rij blijft bestaan,
    -- omdat bestellingen, leveringen en facturen ernaar verwijzen.
    in_assortiment BOOLEAN NOT NULL DEFAULT TRUE,

    CHECK (prijs_per_grootverpakking >= 0),
    CHECK (aantal_detailverpakkingen > 0),
    CHECK (minimale_bestelhoeveelheid > 0),
    CHECK (minimumvoorraad >= 0)
);


-- =========================================
-- 6. PRODUCT WERKZAME STOF
-- Bron: huidige situatie, Productcatalogus.
-- =========================================

CREATE TABLE ProductWerkzameStof (
    product_id INT NOT NULL,
    stofnaam VARCHAR(100) NOT NULL,
    hoeveelheid VARCHAR(50) NOT NULL,

    PRIMARY KEY (product_id, stofnaam),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id)
);


-- =========================================
-- 7. MAGAZIJNLOCATIE
-- Bron: huidige situatie, Vestiging en
-- Voorraad; gewenste situatie, robots.
-- =========================================

CREATE TABLE Magazijnlocatie (
    gang CHAR(1) NOT NULL,
    schapnummer INT NOT NULL,
    product_id INT,
    aantal INT NOT NULL DEFAULT 0,

    PRIMARY KEY (gang, schapnummer),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    CHECK (gang IN (
        'A','B','C','D','E','F','G','H'
    )),
    CHECK (schapnummer BETWEEN 1 AND 40),
    CHECK (aantal >= 0),
    CHECK (product_id IS NOT NULL OR aantal = 0)
);


-- =========================================
-- 8. LEVERANCIER
-- Bron: huidige situatie, Voorraad.
-- =========================================

CREATE TABLE Leverancier (
    leverancier_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    adres_id INT NOT NULL,
    contactpersoon VARCHAR(100),
    telefoonnummer VARCHAR(25),
    internetadres VARCHAR(255),

    FOREIGN KEY (adres_id)
        REFERENCES Adres(adres_id)
);


-- =========================================
-- 9. LEVERANCIERSAANBOD
-- Bron: huidige situatie, Voorraad.
-- =========================================

CREATE TABLE LeveranciersAanbod (
    leverancier_id INT NOT NULL,
    product_id INT NOT NULL,
    inkoopprijs DECIMAL(10,2) NOT NULL,

    PRIMARY KEY (leverancier_id, product_id),

    FOREIGN KEY (leverancier_id)
        REFERENCES Leverancier(leverancier_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    CHECK (inkoopprijs >= 0)
);


-- =========================================
-- 10. INKOOPBESTELLING
-- Bron: huidige situatie, Voorraad.
-- =========================================

CREATE TABLE Inkoopbestelling (
    inkoopbestelling_id INT AUTO_INCREMENT PRIMARY KEY,
    leverancier_id INT NOT NULL,

    FOREIGN KEY (leverancier_id)
        REFERENCES Leverancier(leverancier_id)
);


-- =========================================
-- 11. INKOOPBESTELREGEL
-- Bron: huidige situatie, Voorraad.
-- =========================================

CREATE TABLE Inkoopbestelregel (
    inkoopbestelling_id INT NOT NULL,
    product_id INT NOT NULL,
    aantal INT NOT NULL,

    PRIMARY KEY (inkoopbestelling_id, product_id),

    FOREIGN KEY (inkoopbestelling_id)
        REFERENCES Inkoopbestelling(inkoopbestelling_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    CHECK (aantal > 0)
);


-- =========================================
-- 12. ORDERSTATUS
-- Bron: gewenste situatie, Orderstatus.
-- =========================================

CREATE TABLE OrderStatus (
    naam VARCHAR(40) PRIMARY KEY
);


-- =========================================
-- 13. BESTELLING
-- Bron: huidige situatie, Bestellingen;
-- gewenste situatie, levermoment.
-- =========================================

CREATE TABLE Bestelling (
    bestelling_id INT AUTO_INCREMENT PRIMARY KEY,
    klant_id INT NOT NULL,
    afleveradres_id INT NOT NULL,
    betaaladres_id INT NOT NULL,
    besteld_op DATETIME NOT NULL,
    gewenste_leverdatum DATE NOT NULL,
    dagdeel ENUM('ochtend', 'middag') NOT NULL,
    spoed BOOLEAN NOT NULL DEFAULT FALSE,
    status_naam VARCHAR(40),
    eenmalige_korting_toegepast BOOLEAN
        NOT NULL DEFAULT FALSE,
    extra_bezorgkosten DECIMAL(10,2)
        NOT NULL DEFAULT 0,
    toelichting_extra_bezorgkosten VARCHAR(255),

    FOREIGN KEY (klant_id)
        REFERENCES Klant(klant_id),

    FOREIGN KEY (afleveradres_id)
        REFERENCES Adres(adres_id),

    FOREIGN KEY (betaaladres_id)
        REFERENCES Adres(adres_id),

    FOREIGN KEY (status_naam)
        REFERENCES OrderStatus(naam),

    CHECK (extra_bezorgkosten >= 0)
);


-- =========================================
-- 14. BESTELREGEL
-- Bron: huidige situatie, Bestellingen.
-- =========================================

CREATE TABLE Bestelregel (
    bestelling_id INT NOT NULL,
    product_id INT NOT NULL,
    aantal INT NOT NULL,
    prijs_per_eenheid DECIMAL(10,2) NOT NULL,
    afnemen_bij_tekort BOOLEAN,

    PRIMARY KEY (bestelling_id, product_id),

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    CHECK (aantal > 0),
    CHECK (prijs_per_eenheid >= 0)
);


-- =========================================
-- 15. KLANTKORTING
-- Bron: huidige situatie, kortingsregels.
-- =========================================

-- Reservation of ordered medicine before robot picking, as shown in AD05 Enter_order.
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

CREATE TABLE Klantkorting (
    klant_id INT NOT NULL,
    kalenderjaar SMALLINT NOT NULL,
    percentage DECIMAL(5,2) NOT NULL,

    PRIMARY KEY (klant_id, kalenderjaar),

    FOREIGN KEY (klant_id)
        REFERENCES Klant(klant_id),

    CHECK (percentage IN (5, 10, 15))
);


-- =========================================
-- 16. ROBOT
-- Bron: gewenste situatie, Robots.
-- Robot-ID is alleen voor de demo.
-- =========================================

CREATE TABLE Robot (
    robot_id INT PRIMARY KEY,
    gang CHAR(1) UNIQUE
);


-- =========================================
-- 17. DEELORDER
-- Bron: gewenste situatie, Orderpicking.
-- =========================================

CREATE TABLE Deelorder (
    deelorder_id INT AUTO_INCREMENT PRIMARY KEY,
    bestelling_id INT NOT NULL,
    robot_id INT NOT NULL,
    afgerond BOOLEAN NOT NULL DEFAULT FALSE,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id),

    FOREIGN KEY (robot_id)
        REFERENCES Robot(robot_id)
);


-- =========================================
-- 18. DEELORDERREGEL
-- Bron: gewenste situatie, Orderpicking.
-- =========================================

CREATE TABLE Deelorderregel (
    deelorder_id INT NOT NULL,
    product_id INT NOT NULL,
    aantal INT NOT NULL,

    PRIMARY KEY (deelorder_id, product_id),

    FOREIGN KEY (deelorder_id)
        REFERENCES Deelorder(deelorder_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    CHECK (aantal > 0)
);


-- =========================================
-- 19. VERZAMELBAK
-- Bron: gewenste situatie, Verzamelen.
-- =========================================

CREATE TABLE Verzamelbak (
    unieke_code VARCHAR(50) PRIMARY KEY,
    deelorder_id INT NOT NULL,

    FOREIGN KEY (deelorder_id)
        REFERENCES Deelorder(deelorder_id)
);


-- =========================================
-- 20. KOERIER
-- Bron: huidige situatie, Distributie.
-- =========================================

CREATE TABLE Koerier (
    koerier_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    beschikbaar BOOLEAN NOT NULL DEFAULT FALSE
);


-- =========================================
-- 21. RIT
-- Bron: huidige en gewenste distributie.
-- =========================================

CREATE TABLE Rit (
    rit_id INT AUTO_INCREMENT PRIMARY KEY,
    koerier_id INT NOT NULL,
    ritdatum DATE NOT NULL,

    FOREIGN KEY (koerier_id)
        REFERENCES Koerier(koerier_id)
);


-- =========================================
-- 22. LEVERING
-- Bron: huidige en gewenste distributie.
-- =========================================

CREATE TABLE Levering (
    levering_id INT AUTO_INCREMENT PRIMARY KEY,
    bestelling_id INT NOT NULL,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id)
);


-- =========================================
-- 23. LEVERPOGING
-- Bron: huidige situatie, Distributie;
-- productbeschrijving, Distributie.
-- =========================================

CREATE TABLE Leverpoging (
    levering_id INT NOT NULL,
    pogingnummer INT NOT NULL,
    rit_id INT NOT NULL,
    geplande_tijd TIME NOT NULL,
    resultaat ENUM('afgeleverd', 'niet aanwezig'),
    ontvangst_getekend BOOLEAN,

    PRIMARY KEY (levering_id, pogingnummer),

    FOREIGN KEY (levering_id)
        REFERENCES Levering(levering_id),

    FOREIGN KEY (rit_id)
        REFERENCES Rit(rit_id),

    CHECK (pogingnummer > 0)
);


-- =========================================
-- 24. FACTUUR
-- Bron: huidige situatie, Administratie.
-- Wordt vóór Leveringregel aangemaakt
-- vanwege de foreign key.
-- =========================================

CREATE TABLE Factuur (
    factuur_id INT AUTO_INCREMENT PRIMARY KEY,
    klant_id INT NOT NULL,
    factuurdatum DATE NOT NULL,
    betaald_op DATE,
    betalingsregeling_geaccepteerd BOOLEAN,
    incasso_ingeschakeld BOOLEAN NOT NULL DEFAULT FALSE,
    bedrag_excl_btw DECIMAL(10,2) NULL,
    btw_bedrag DECIMAL(10,2) NULL,
    bedrag_incl_btw DECIMAL(10,2) NULL,
    bestellingskorting DECIMAL(10,2) NULL,
    bedrag_na_bestellingskorting DECIMAL(10,2) NULL,
    eenmalige_korting DECIMAL(10,2) NULL,
    bedrag_na_eenmalige_korting DECIMAL(10,2) NULL,
    klantenkorting DECIMAL(10,2) NULL,
    totaal_bedrag DECIMAL(10,2) NULL,

    FOREIGN KEY (klant_id)
        REFERENCES Klant(klant_id)
);


-- =========================================
-- 25. LEVERINGREGEL
-- Bron: huidige situatie, Distributie
-- en wekelijkse facturatie.
--
-- Factuur-ID vervangt aparte Factuurregel.
-- =========================================

CREATE TABLE Leveringregel (
    levering_id INT NOT NULL,
    product_id INT NOT NULL,
    aantal_geleverd INT NOT NULL,
    factuur_id INT,

    PRIMARY KEY (levering_id, product_id),

    FOREIGN KEY (levering_id)
        REFERENCES Levering(levering_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    FOREIGN KEY (factuur_id)
        REFERENCES Factuur(factuur_id),

    CHECK (aantal_geleverd > 0)
);


-- =========================================
-- 26. BETALINGSHERINNERING
-- Bron: huidige situatie, Administratie.
-- =========================================

CREATE TABLE Betalingsherinnering (
    factuur_id INT NOT NULL,
    volgnummer INT NOT NULL,
    verstuurd_op DATE NOT NULL,

    PRIMARY KEY (factuur_id, volgnummer),

    FOREIGN KEY (factuur_id)
        REFERENCES Factuur(factuur_id),

    CHECK (volgnummer IN (1, 2))
);


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

-- =========================================
-- ORDERSTATUSSEN UIT DE CASUS
-- =========================================

INSERT INTO OrderStatus (naam)
VALUES
    ('wordt verzameld'),
    ('verstuurd'),
    ('backorder'),
    ('afgeleverd'),
    ('niet afgeleverd');

