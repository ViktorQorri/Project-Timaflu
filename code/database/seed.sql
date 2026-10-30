-- =========================================
-- SEED DATA
-- Example data to try every screen locally.
-- Run once, after schema.sql and the migrations. It adds to rows that are already
-- there: generated ids come from AUTO_INCREMENT and are linked through variables
-- set with LAST_INSERT_ID(). Robots, warehouse locations, article numbers and
-- bin codes must not exist yet.
-- Dates are relative to the day you run it: "previous year" and "this year"
-- follow CURDATE(), so the discount tiers and reports keep working.
-- Recent orders are a few days to two months old; run it after early March
-- so all of them fall in the current year.
-- =========================================

START TRANSACTION;

SET @y = YEAR(CURDATE());
SET @today = CURDATE();


-- =========================================
-- ADRESSEN
-- =========================================

INSERT INTO Adres (adres)
VALUES
    ('Lindelaan 12, 3521 AB Utrecht'),
    ('Postbus 2210, 3500 GE Utrecht'),
    ('Zuidplein 88, 3083 CW Rotterdam'),
    ('Bergweg 140, 3036 BH Rotterdam'),
    ('Bergweg 138, 3036 BH Rotterdam'),
    ('Havenstraat 5, 1781 AB Den Helder'),
    ('Vredeoordlaan 20, 5627 AH Eindhoven'),
    ('Industrieweg 40, 3606 AS Maarssen'),
    ('Transportweg 7, 2742 RH Waddinxveen'),
    ('Zernikepark 3, 9747 AN Groningen'),
    ('Marktplein 9, 3811 LE Amersfoort');
SET @a1 = LAST_INSERT_ID();
SET @a2 = @a1 + 1, @a3 = @a1 + 2, @a4 = @a1 + 3, @a5 = @a1 + 4, @a6 = @a1 + 5,
    @a7 = @a1 + 6, @a8 = @a1 + 7, @a9 = @a1 + 8, @a10 = @a1 + 9, @a11 = @a1 + 10;


-- =========================================
-- KLANTEN
-- Revenue in the previous year puts each customer in another discount tier:
-- k1 >= EUR 20.000 (15%), k2 between EUR 10.000 and 20.000 (10%),
-- k3 < EUR 10.000 (5%), k4 has never ordered (first order),
-- k5 only ordered this year (EUR 0 last year, 5%).
-- =========================================

INSERT INTO Klant (bedrijfsnaam, telefoonnummer, contactpersoon, afleveradres_id, betaaladres_id)
VALUES
    ('Apotheek De Linde', '030-5551234', 'M. Verhoeven', @a1, @a2),
    ('Apotheek Zuidplein', '010-5554321', 'R. Pinas', @a3, @a3),
    ('Huisartsenpraktijk Bergweg', '010-5556789', 'Dr. A. Yilmaz', @a4, @a5),
    ('Apotheek Het Anker', '0223-555456', 'J. de Boer', @a6, @a6),
    ('Zorgcentrum Vredeoord', '040-5559876', 'L. Hendriks', @a7, @a7);
SET @k1 = LAST_INSERT_ID();
SET @k2 = @k1 + 1, @k3 = @k1 + 2, @k4 = @k1 + 3, @k5 = @k1 + 4;

INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)
VALUES
    (@k1, @y, 15),
    (@k2, @y, 10),
    (@k3, @y, 5),
    (@k5, @y, 5);


-- =========================================
-- ACQUISITIE
-- The first prospect was visited over a month ago and has not ordered.
-- The second one became customer k4.
-- =========================================

INSERT INTO PotentieleKlant (bedrijfsnaam, contactpersoon, contactgegevens, adres_id, klant_id)
VALUES
    ('Apotheek Marktplein', 'E. Visser', '033-5557711, info@apotheekmarktplein.example', @a11, NULL),
    ('Apotheek Het Anker', 'J. de Boer', '0223-555456', @a6, @k4);
SET @pk1 = LAST_INSERT_ID();
SET @pk2 = @pk1 + 1;

INSERT INTO Acquisitiebezoek (potentiele_klant_id, bezoekdatum)
VALUES
    (@pk1, DATE_SUB(@today, INTERVAL 40 DAY)),
    (@pk2, DATE_SUB(@today, INTERVAL 25 DAY));


-- =========================================
-- PRODUCTEN
-- =========================================

INSERT INTO Product (artikelnummer, bestelcode, productnaam, prijs_per_grootverpakking,
                     verpakkingssoort, aantal_detailverpakkingen, korte_omschrijving, lange_omschrijving,
                     minimale_bestelhoeveelheid, minimumvoorraad)
VALUES
    ('ART-1001', 'BC-PAR500', 'Paracetamol 500 mg tabletten', 45.00, 'doos', 50,
        'Pijnstiller en koortsverlager', 'Doos met 50 doordrukstrips van 10 tabletten.', 5, 100),
    ('ART-1002', 'BC-IBU400', 'Ibuprofen 400 mg tabletten', 62.50, 'doos', 40,
        'Ontstekingsremmende pijnstiller', 'Doos met 40 doordrukstrips van 10 tabletten.', 5, 120),
    ('ART-1003', 'BC-AMO500', 'Amoxicilline 500 mg capsules', 118.00, 'doos', 30,
        'Antibioticum', 'Doos met 30 verpakkingen van 21 capsules.', 2, 50),
    ('ART-1004', 'BC-OME020', 'Omeprazol 20 mg capsules', 54.20, 'doos', 28,
        'Maagzuurremmer', 'Doos met 28 flacons van 30 maagsapresistente capsules.', 5, 40),
    ('ART-1005', 'BC-MET500', 'Metformine 500 mg tabletten', 39.90, 'doos', 60,
        'Bloedsuikerverlager', 'Doos met 60 doordrukstrips van 10 tabletten.', 5, 80),
    ('ART-1006', 'BC-SAL100', 'Salbutamol 100 mcg inhalator', 96.00, 'doos', 20,
        'Luchtwegverwijder', 'Doos met 20 aerosolen van 200 doses.', 2, 30),
    ('ART-1007', 'BC-SIM040', 'Simvastatine 40 mg tabletten', 71.30, 'doos', 30,
        'Cholesterolverlager', 'Doos met 30 doordrukstrips van 30 tabletten.', 5, 60),
    ('ART-1008', 'BC-INS100', 'Insuline glargine 100 E/ml pen', 312.00, 'koelverpakking', 5,
        'Langwerkende insuline', 'Koelverpakking met 5 voorgevulde pennen van 3 ml.', 1, 10);
SET @p1 = LAST_INSERT_ID();
SET @p2 = @p1 + 1, @p3 = @p1 + 2, @p4 = @p1 + 3, @p5 = @p1 + 4, @p6 = @p1 + 5,
    @p7 = @p1 + 6, @p8 = @p1 + 7;

INSERT INTO ProductWerkzameStof (product_id, stofnaam, hoeveelheid)
VALUES
    (@p1, 'paracetamol', '500 mg'),
    (@p2, 'ibuprofen', '400 mg'),
    (@p3, 'amoxicilline', '500 mg'),
    (@p4, 'omeprazol', '20 mg'),
    (@p5, 'metforminehydrochloride', '500 mg'),
    (@p6, 'salbutamol', '100 mcg per dosis'),
    (@p7, 'simvastatine', '40 mg'),
    (@p8, 'insuline glargine', '100 E/ml');


-- =========================================
-- MAGAZIJN
-- One robot per aisle. Ibuprofen, omeprazol, salbutamol and insuline
-- (after reservations) are below their minimum stock; omeprazol is out of stock.
-- =========================================

INSERT INTO Robot (robot_id, gang)
VALUES
    (1, 'A'), (2, 'B'), (3, 'C'), (4, 'D'), (5, 'E'), (6, 'F'), (7, 'G'), (8, 'H');

INSERT INTO Magazijnlocatie (gang, schapnummer, product_id, aantal)
VALUES
    ('A', 1, @p1, 250),
    ('A', 2, @p1, 150),
    ('A', 3, @p2, 80),
    ('B', 1, @p3, 60),
    ('C', 1, @p4, 0),
    ('D', 1, @p5, 300),
    ('E', 1, @p6, 25),
    ('F', 1, @p7, 150),
    ('G', 1, @p8, 12),
    ('H', 1, NULL, 0);


-- =========================================
-- LEVERANCIERS EN INKOOP
-- =========================================

INSERT INTO Leverancier (naam, adres_id, contactpersoon, telefoonnummer, internetadres)
VALUES
    ('MediSupply Nederland BV', @a8, 'S. de Vries', '0346-555010', 'https://medisupply.example'),
    ('Pharmadis Europe BV', @a9, 'M. Jansen', '0182-555220', 'https://pharmadis.example'),
    ('Noord Farma Distributie', @a10, 'I. Bakker', '050-5553300', 'https://noordfarma.example');
SET @s1 = LAST_INSERT_ID();
SET @s2 = @s1 + 1, @s3 = @s1 + 2;

INSERT INTO LeveranciersAanbod (leverancier_id, product_id, inkoopprijs)
VALUES
    (@s1, @p1, 30.00), (@s1, @p2, 41.00), (@s1, @p4, 35.50), (@s1, @p5, 25.00), (@s1, @p8, 220.00),
    (@s2, @p1, 31.50), (@s2, @p3, 79.00), (@s2, @p4, 34.90), (@s2, @p6, 64.00), (@s2, @p7, 47.00),
    (@s3, @p2, 40.50), (@s3, @p3, 81.00), (@s3, @p6, 62.50), (@s3, @p7, 48.20), (@s3, @p8, 215.00);

INSERT INTO Inkoopbestelling (leverancier_id)
VALUES (@s2);

INSERT INTO Inkoopbestelregel (inkoopbestelling_id, product_id, aantal)
VALUES (LAST_INSERT_ID(), @p4, 200);


-- =========================================
-- BESTELLINGEN
-- o1-o6: previous year, delivered and paid.
-- o10-o12: this year, delivered; o12 needed a second attempt.
-- o13: sent, delivery planned tomorrow.
-- o14: backorder, omeprazol is out of stock.
-- o15, o17: being picked by the robots. o16: urgent, no status yet.
-- =========================================

INSERT INTO Bestelling (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                        gewenste_leverdatum, dagdeel, spoed, status_naam, eenmalige_korting_toegepast)
VALUES
    (@k1, @a1, @a2, TIMESTAMP(MAKEDATE(@y - 1, 40), '09:12:00'), MAKEDATE(@y - 1, 42), 'ochtend', FALSE, 'afgeleverd', TRUE),
    (@k1, @a1, @a2, TIMESTAMP(MAKEDATE(@y - 1, 150), '14:03:00'), MAKEDATE(@y - 1, 152), 'middag', FALSE, 'afgeleverd', FALSE),
    (@k1, @a1, @a2, TIMESTAMP(MAKEDATE(@y - 1, 280), '10:47:00'), MAKEDATE(@y - 1, 282), 'ochtend', FALSE, 'afgeleverd', FALSE),
    (@k2, @a3, @a3, TIMESTAMP(MAKEDATE(@y - 1, 90), '11:20:00'), MAKEDATE(@y - 1, 92), 'ochtend', FALSE, 'afgeleverd', TRUE),
    (@k2, @a3, @a3, TIMESTAMP(MAKEDATE(@y - 1, 220), '15:35:00'), MAKEDATE(@y - 1, 222), 'middag', FALSE, 'afgeleverd', FALSE),
    (@k3, @a4, @a5, TIMESTAMP(MAKEDATE(@y - 1, 120), '08:58:00'), MAKEDATE(@y - 1, 122), 'ochtend', FALSE, 'afgeleverd', TRUE),
    (@k1, @a1, @a2, TIMESTAMP(DATE_SUB(@today, INTERVAL 60 DAY), '09:20:00'), DATE_SUB(@today, INTERVAL 58 DAY), 'ochtend', FALSE, 'afgeleverd', FALSE),
    (@k2, @a3, @a3, TIMESTAMP(DATE_SUB(@today, INTERVAL 40 DAY), '11:05:00'), DATE_SUB(@today, INTERVAL 38 DAY), 'middag', FALSE, 'afgeleverd', FALSE),
    (@k3, @a4, @a5, TIMESTAMP(DATE_SUB(@today, INTERVAL 20 DAY), '08:50:00'), DATE_SUB(@today, INTERVAL 18 DAY), 'ochtend', FALSE, 'afgeleverd', FALSE),
    (@k1, @a1, @a2, TIMESTAMP(DATE_SUB(@today, INTERVAL 3 DAY), '13:40:00'), DATE_ADD(@today, INTERVAL 1 DAY), 'ochtend', FALSE, 'verstuurd', FALSE),
    (@k2, @a3, @a3, TIMESTAMP(DATE_SUB(@today, INTERVAL 2 DAY), '10:10:00'), DATE_ADD(@today, INTERVAL 2 DAY), 'middag', FALSE, 'backorder', FALSE),
    (@k5, @a7, @a7, TIMESTAMP(DATE_SUB(@today, INTERVAL 1 DAY), '15:25:00'), DATE_ADD(@today, INTERVAL 1 DAY), 'middag', FALSE, 'wordt verzameld', TRUE),
    (@k3, @a4, @a5, TIMESTAMP(@today, '08:05:00'), DATE_ADD(@today, INTERVAL 1 DAY), 'ochtend', TRUE, NULL, FALSE),
    (@k1, @a1, @a2, TIMESTAMP(@today, '09:30:00'), DATE_ADD(@today, INTERVAL 2 DAY), 'ochtend', FALSE, 'wordt verzameld', FALSE);
SET @o1 = LAST_INSERT_ID();
SET @o2 = @o1 + 1, @o3 = @o1 + 2, @o4 = @o1 + 3, @o5 = @o1 + 4, @o6 = @o1 + 5,
    @o10 = @o1 + 6, @o11 = @o1 + 7, @o12 = @o1 + 8, @o13 = @o1 + 9, @o14 = @o1 + 10,
    @o15 = @o1 + 11, @o16 = @o1 + 12, @o17 = @o1 + 13;

INSERT INTO Bestelregel (bestelling_id, product_id, aantal, prijs_per_eenheid, afnemen_bij_tekort)
VALUES
    (@o1, @p8, 40, 312.00, NULL),
    (@o2, @p3, 60, 118.00, NULL),
    (@o3, @p1, 50, 45.00, NULL),
    (@o4, @p8, 20, 312.00, NULL),
    (@o5, @p6, 50, 96.00, NULL),
    (@o6, @p1, 40, 45.00, NULL),
    (@o6, @p4, 30, 54.20, NULL),
    (@o10, @p1, 30, 45.00, NULL),
    (@o10, @p2, 20, 62.50, NULL),
    (@o11, @p3, 10, 118.00, NULL),
    (@o11, @p5, 25, 39.90, NULL),
    (@o12, @p5, 20, 39.90, NULL),
    (@o12, @p4, 10, 54.20, NULL),
    (@o13, @p6, 10, 96.00, NULL),
    (@o13, @p1, 25, 45.00, NULL),
    (@o14, @p4, 40, 54.20, TRUE),
    (@o14, @p1, 20, 45.00, NULL),
    (@o15, @p2, 10, 62.50, NULL),
    (@o15, @p6, 5, 96.00, NULL),
    (@o15, @p7, 12, 71.30, NULL),
    (@o16, @p8, 2, 312.00, NULL),
    (@o17, @p8, 5, 312.00, NULL),
    (@o17, @p3, 15, 118.00, NULL);

-- Omeprazol on o14 is not reserved: there is no stock, so it is the backorder.
INSERT INTO Voorraadreservering (bestelling_id, product_id, aantal)
VALUES
    (@o14, @p1, 20),
    (@o15, @p2, 10),
    (@o15, @p6, 5),
    (@o15, @p7, 12),
    (@o16, @p8, 2),
    (@o17, @p8, 5),
    (@o17, @p3, 15);


-- =========================================
-- ORDERPICKING
-- d3 is done; d1, d2, d4 and d5 are still being collected.
-- d4 (aisle G) and d5 (aisle B) have no bin yet, so the robot API can register one.
-- =========================================

INSERT INTO Deelorder (bestelling_id, robot_id, afgerond)
VALUES
    (@o15, (SELECT robot_id FROM Robot WHERE gang = 'A'), FALSE),
    (@o15, (SELECT robot_id FROM Robot WHERE gang = 'E'), FALSE),
    (@o15, (SELECT robot_id FROM Robot WHERE gang = 'F'), TRUE),
    (@o17, (SELECT robot_id FROM Robot WHERE gang = 'G'), FALSE),
    (@o17, (SELECT robot_id FROM Robot WHERE gang = 'B'), FALSE);
SET @d1 = LAST_INSERT_ID();
SET @d2 = @d1 + 1, @d3 = @d1 + 2, @d4 = @d1 + 3, @d5 = @d1 + 4;

INSERT INTO Deelorderregel (deelorder_id, product_id, aantal)
VALUES
    (@d1, @p2, 10),
    (@d2, @p6, 5),
    (@d3, @p7, 12),
    (@d4, @p8, 5),
    (@d5, @p3, 15);

INSERT INTO Verzamelbak (unieke_code, deelorder_id)
VALUES
    ('VB-1001', @d3),
    ('VB-1002', @d1);


-- =========================================
-- DISTRIBUTIE
-- =========================================

INSERT INTO Koerier (naam, beschikbaar)
VALUES
    ('J. Smit', TRUE),
    ('F. El Amrani', TRUE),
    ('K. Mulder', FALSE);
SET @c1 = LAST_INSERT_ID();
SET @c2 = @c1 + 1;

INSERT INTO Rit (koerier_id, ritdatum)
VALUES
    (@c1, MAKEDATE(@y - 1, 42)),
    (@c2, MAKEDATE(@y - 1, 152)),
    (@c1, MAKEDATE(@y - 1, 282)),
    (@c2, MAKEDATE(@y - 1, 92)),
    (@c1, MAKEDATE(@y - 1, 222)),
    (@c2, MAKEDATE(@y - 1, 122)),
    (@c1, DATE_SUB(@today, INTERVAL 58 DAY)),
    (@c2, DATE_SUB(@today, INTERVAL 38 DAY)),
    (@c1, DATE_SUB(@today, INTERVAL 18 DAY)),
    (@c2, DATE_ADD(@today, INTERVAL 1 DAY));
SET @r1 = LAST_INSERT_ID();

-- Delivery n belongs to trip n: l1-l6 for o1-o6, l7-l9 for o10-o12, l10 for o13.
INSERT INTO Levering (bestelling_id)
VALUES
    (@o1), (@o2), (@o3), (@o4), (@o5), (@o6),
    (@o10), (@o11), (@o12), (@o13);
SET @l1 = LAST_INSERT_ID();

INSERT INTO Leverpoging (levering_id, pogingnummer, rit_id, geplande_tijd, resultaat, ontvangst_getekend)
VALUES
    (@l1, 1, @r1, '10:30:00', 'afgeleverd', TRUE),
    (@l1 + 1, 1, @r1 + 1, '14:15:00', 'afgeleverd', TRUE),
    (@l1 + 2, 1, @r1 + 2, '09:45:00', 'afgeleverd', TRUE),
    (@l1 + 3, 1, @r1 + 3, '11:00:00', 'afgeleverd', TRUE),
    (@l1 + 4, 1, @r1 + 4, '13:30:00', 'afgeleverd', TRUE),
    (@l1 + 5, 1, @r1 + 5, '10:00:00', 'afgeleverd', TRUE),
    (@l1 + 6, 1, @r1 + 6, '09:30:00', 'afgeleverd', TRUE),
    (@l1 + 7, 1, @r1 + 7, '14:00:00', 'afgeleverd', TRUE),
    (@l1 + 8, 1, @r1 + 8, '09:15:00', 'niet aanwezig', FALSE),
    (@l1 + 8, 2, @r1 + 8, '15:30:00', 'afgeleverd', TRUE),
    (@l1 + 9, 1, @r1 + 9, '10:45:00', NULL, NULL);


-- =========================================
-- ADMINISTRATIE
-- Invoice n belongs to delivery n for the first nine deliveries.
-- The eighth invoice (o11) is unpaid and had a first reminder.
-- =========================================

INSERT INTO Factuur (klant_id, factuurdatum, betaald_op, betalingsregeling_geaccepteerd, incasso_ingeschakeld)
VALUES
    (@k1, MAKEDATE(@y - 1, 47), MAKEDATE(@y - 1, 60), NULL, FALSE),
    (@k1, MAKEDATE(@y - 1, 157), MAKEDATE(@y - 1, 170), NULL, FALSE),
    (@k1, MAKEDATE(@y - 1, 287), MAKEDATE(@y - 1, 300), NULL, FALSE),
    (@k2, MAKEDATE(@y - 1, 97), MAKEDATE(@y - 1, 112), NULL, FALSE),
    (@k2, MAKEDATE(@y - 1, 227), MAKEDATE(@y - 1, 240), NULL, FALSE),
    (@k3, MAKEDATE(@y - 1, 127), MAKEDATE(@y - 1, 145), NULL, FALSE),
    (@k1, DATE_SUB(@today, INTERVAL 53 DAY), DATE_SUB(@today, INTERVAL 35 DAY), NULL, FALSE),
    (@k2, DATE_SUB(@today, INTERVAL 33 DAY), NULL, NULL, FALSE),
    (@k3, DATE_SUB(@today, INTERVAL 12 DAY), DATE_SUB(@today, INTERVAL 5 DAY), NULL, FALSE);
SET @f1 = LAST_INSERT_ID();

INSERT INTO Leveringregel (levering_id, product_id, aantal_geleverd, factuur_id)
VALUES
    (@l1, @p8, 40, @f1),
    (@l1 + 1, @p3, 60, @f1 + 1),
    (@l1 + 2, @p1, 50, @f1 + 2),
    (@l1 + 3, @p8, 20, @f1 + 3),
    (@l1 + 4, @p6, 50, @f1 + 4),
    (@l1 + 5, @p1, 40, @f1 + 5),
    (@l1 + 5, @p4, 30, @f1 + 5),
    (@l1 + 6, @p1, 30, @f1 + 6),
    (@l1 + 6, @p2, 20, @f1 + 6),
    (@l1 + 7, @p3, 10, @f1 + 7),
    (@l1 + 7, @p5, 25, @f1 + 7),
    (@l1 + 8, @p5, 20, @f1 + 8),
    (@l1 + 8, @p4, 10, @f1 + 8);

INSERT INTO Betalingsherinnering (factuur_id, volgnummer, verstuurd_op)
VALUES (@f1 + 7, 1, DATE_SUB(@today, INTERVAL 12 DAY));

COMMIT;
