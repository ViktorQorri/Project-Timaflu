DROP DATABASE IF EXISTS timaflu;
CREATE DATABASE timaflu;
USE timaflu;

-- ==========================================
-- ROLLEN EN GEBRUIKERS
-- ==========================================

CREATE TABLE Rol (
    rol_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE Gebruiker (
    gebruiker_id INT AUTO_INCREMENT PRIMARY KEY,
    voornaam VARCHAR(50) NOT NULL,
    achternaam VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    wachtwoord VARCHAR(255) NOT NULL,
    rol_id INT NOT NULL,

    FOREIGN KEY (rol_id)
        REFERENCES Rol(rol_id)
);

-- ==========================================
-- ADRESSEN
-- ==========================================

CREATE TABLE Adres (
    adres_id INT AUTO_INCREMENT PRIMARY KEY,
    straat VARCHAR(100) NOT NULL,
    huisnummer VARCHAR(10) NOT NULL,
    toevoeging VARCHAR(10),
    postcode VARCHAR(10) NOT NULL,
    plaats VARCHAR(100) NOT NULL
);

-- ==========================================
-- KLANTEN
-- ==========================================

CREATE TABLE Klant (
    klant_id INT AUTO_INCREMENT PRIMARY KEY,
    bedrijfsnaam VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    registratiedatum DATE,

    factuur_adres_id INT NOT NULL,
    lever_adres_id INT NOT NULL,

    FOREIGN KEY (factuur_adres_id)
        REFERENCES Adres(adres_id),

    FOREIGN KEY (lever_adres_id)
        REFERENCES Adres(adres_id)
);

CREATE TABLE KlantTelefoon (
    klant_telefoon_id INT AUTO_INCREMENT PRIMARY KEY,
    klant_id INT NOT NULL,
    telefoonnummer VARCHAR(20) NOT NULL,

    FOREIGN KEY (klant_id)
        REFERENCES Klant(klant_id)
);

-- ==========================================
-- LEVERANCIERS
-- ==========================================

CREATE TABLE Leverancier (
    leverancier_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    email VARCHAR(100),

    adres_id INT NOT NULL,

    FOREIGN KEY (adres_id)
        REFERENCES Adres(adres_id)
);

CREATE TABLE LeverancierTelefoon (
    leverancier_telefoon_id INT AUTO_INCREMENT PRIMARY KEY,
    leverancier_id INT NOT NULL,
    telefoonnummer VARCHAR(20) NOT NULL,

    FOREIGN KEY (leverancier_id)
        REFERENCES Leverancier(leverancier_id)
);

-- ==========================================
-- PRODUCTEN
-- ==========================================

CREATE TABLE Product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL,
    beschrijving TEXT,
    verkoopprijs DECIMAL(10,2) NOT NULL,
    minimumvoorraad INT NOT NULL,
    huidige_voorraad INT NOT NULL
);

CREATE TABLE ProductLeverancier (
    product_id INT,
    leverancier_id INT,
    inkoopprijs DECIMAL(10,2) NOT NULL,

    PRIMARY KEY (product_id, leverancier_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id),

    FOREIGN KEY (leverancier_id)
        REFERENCES Leverancier(leverancier_id)
);

-- ==========================================
-- ORDERSTATUSSEN
-- ==========================================

CREATE TABLE OrderStatus (
    status_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(50) NOT NULL UNIQUE
);

-- ==========================================
-- BESTELLINGEN
-- ==========================================

CREATE TABLE Bestelling (
    bestelling_id INT AUTO_INCREMENT PRIMARY KEY,

    klant_id INT NOT NULL,
    status_id INT NOT NULL,

    orderdatum DATETIME NOT NULL,

    korting_percentage DECIMAL(5,2) DEFAULT 0,

    FOREIGN KEY (klant_id)
        REFERENCES Klant(klant_id),

    FOREIGN KEY (status_id)
        REFERENCES OrderStatus(status_id)
);

CREATE TABLE BestellingRegel (
    regel_id INT AUTO_INCREMENT PRIMARY KEY,

    bestelling_id INT NOT NULL,
    product_id INT NOT NULL,

    aantal INT NOT NULL,
    prijs_per_stuk DECIMAL(10,2) NOT NULL,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id)
);

-- ==========================================
-- VOORRAADRESERVERING
-- ==========================================

CREATE TABLE VoorraadReservering (
    reservering_id INT AUTO_INCREMENT PRIMARY KEY,

    bestelling_id INT NOT NULL,
    product_id INT NOT NULL,

    aantal INT NOT NULL,
    reserveringsdatum DATETIME NOT NULL,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id),

    FOREIGN KEY (product_id)
        REFERENCES Product(product_id)
);

-- ==========================================
-- ROBOTS
-- ==========================================

CREATE TABLE Robot (
    robot_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(50) NOT NULL,
    gangnummer INT NOT NULL,
    status VARCHAR(50) NOT NULL
);

CREATE TABLE Deelorder (
    deelorder_id INT AUTO_INCREMENT PRIMARY KEY,

    bestelling_id INT NOT NULL,
    robot_id INT NOT NULL,

    status VARCHAR(50) NOT NULL,

    starttijd DATETIME,
    eindtijd DATETIME,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id),

    FOREIGN KEY (robot_id)
        REFERENCES Robot(robot_id)
);

CREATE TABLE Verzamelbak (
    bak_id INT AUTO_INCREMENT PRIMARY KEY,

    barcode VARCHAR(100) UNIQUE NOT NULL,
    locatie VARCHAR(100),

    bestelling_id INT,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id)
);

-- ==========================================
-- KOERIERS
-- ==========================================

CREATE TABLE Koerier (
    koerier_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(100) NOT NULL
);

CREATE TABLE KoerierTelefoon (
    koerier_telefoon_id INT AUTO_INCREMENT PRIMARY KEY,

    koerier_id INT NOT NULL,
    telefoonnummer VARCHAR(20) NOT NULL,

    FOREIGN KEY (koerier_id)
        REFERENCES Koerier(koerier_id)
);

-- ==========================================
-- LEVERSTATUSSEN
-- ==========================================

CREATE TABLE LeverStatus (
    status_id INT AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(50) NOT NULL UNIQUE
);

-- ==========================================
-- LEVERINGEN
-- ==========================================

CREATE TABLE Levering (
    levering_id INT AUTO_INCREMENT PRIMARY KEY,

    bestelling_id INT NOT NULL,
    koerier_id INT NOT NULL,
    status_id INT NOT NULL,

    geplande_datum DATE NOT NULL,
    dagdeel ENUM('Ochtend','Middag') NOT NULL,

    afleverdatum DATETIME,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id),

    FOREIGN KEY (koerier_id)
        REFERENCES Koerier(koerier_id),

    FOREIGN KEY (status_id)
        REFERENCES LeverStatus(status_id)
);

-- ==========================================
-- FACTUREN
-- ==========================================

CREATE TABLE Factuur (
    factuur_id INT AUTO_INCREMENT PRIMARY KEY,

    bestelling_id INT NOT NULL,

    factuurdatum DATE NOT NULL,
    bedrag DECIMAL(12,2) NOT NULL,

    betaald BOOLEAN DEFAULT FALSE,
    betaaldatum DATE,

    FOREIGN KEY (bestelling_id)
        REFERENCES Bestelling(bestelling_id)
);

CREATE TABLE BetalingsHerinnering (
    herinnering_id INT AUTO_INCREMENT PRIMARY KEY,

    factuur_id INT NOT NULL,

    herinnering_nummer INT NOT NULL,
    verzenddatum DATE NOT NULL,

    FOREIGN KEY (factuur_id)
        REFERENCES Factuur(factuur_id)
);

-- ==========================================
-- PROSPECTS
-- ==========================================

CREATE TABLE Prospect (
    prospect_id INT AUTO_INCREMENT PRIMARY KEY,

    bedrijfsnaam VARCHAR(100) NOT NULL,
    contactpersoon VARCHAR(100),
    email VARCHAR(100),
    status VARCHAR(50)
);

CREATE TABLE ProspectTelefoon (
    prospect_telefoon_id INT AUTO_INCREMENT PRIMARY KEY,

    prospect_id INT NOT NULL,
    telefoonnummer VARCHAR(20) NOT NULL,

    FOREIGN KEY (prospect_id)
        REFERENCES Prospect(prospect_id)
);

CREATE TABLE Bezoek (
    bezoek_id INT AUTO_INCREMENT PRIMARY KEY,

    prospect_id INT NOT NULL,
    gebruiker_id INT NOT NULL,

    bezoekdatum DATE NOT NULL,
    notities TEXT,

    FOREIGN KEY (prospect_id)
        REFERENCES Prospect(prospect_id),

    FOREIGN KEY (gebruiker_id)
        REFERENCES Gebruiker(gebruiker_id)
);

-- ==========================================
-- AUDIT LOG
-- ==========================================

CREATE TABLE AuditLog (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    gebruiker_id INT NOT NULL,
    actie VARCHAR(255) NOT NULL,
    datumtijd DATETIME NOT NULL,
    FOREIGN KEY (gebruiker_id)
        REFERENCES Gebruiker (gebruiker_id)
);