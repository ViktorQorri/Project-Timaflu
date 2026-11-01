-- Isolated fictional data for weekly end-to-end MySQL tests (NOT real Timaflu data).
INSERT INTO Adres(adres) VALUES ('TEST: Factuurstraat 12, Breda'), ('TEST: Afleverstraat 8, Breda');
INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id)
VALUES ('TEST Apotheek B.V.','0612345678','TEST medewerker',2,1);
-- This is the 2026 rate determined from 2025 paid turnover, not an invoice-time guess.
INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage) VALUES (1, 2026, 5.00);
INSERT INTO Product(artikelnummer,bestelcode,productnaam,prijs_per_grootverpakking,
  aantal_detailverpakkingen,minimale_bestelhoeveelheid,minimumvoorraad)
VALUES('TEST-001','TEST-CODE','Testmedicijn',100.00,1,1,1);
INSERT INTO Bestelling(klant_id,afleveradres_id,betaaladres_id,besteld_op,
  gewenste_leverdatum,dagdeel,spoed,status_naam)
VALUES
(1,2,1,'2026-10-19 09:00:00','2026-10-22','ochtend',FALSE,'afgeleverd'),
(1,2,1,'2026-10-20 09:00:00','2026-10-22','middag',FALSE,'afgeleverd'),
(1,2,1,'2026-10-21 09:00:00','2026-10-22','ochtend',FALSE,'verstuurd'),
(1,2,1,'2026-10-29 09:00:00','2026-10-30','ochtend',FALSE,'afgeleverd');
INSERT INTO Bestelregel(bestelling_id,product_id,aantal,prijs_per_eenheid)
VALUES (1,1,6,100.00),(2,1,1,100.00),(3,1,1,100.00),(4,1,1,100.00);
INSERT INTO Levering(bestelling_id) VALUES (1),(2),(3),(4);
INSERT INTO Leveringregel(levering_id,product_id,aantal_geleverd)
VALUES (1,1,6),(2,1,1),(3,1,1),(4,1,1);
INSERT INTO Koerier(naam,beschikbaar) VALUES ('TEST koerier',TRUE);
INSERT INTO Rit(koerier_id,ritdatum) VALUES (1,'2026-10-22'),(1,'2026-10-30');
INSERT INTO Leverpoging(levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
VALUES
(1,1,1,'10:00:00','afgeleverd',TRUE),
(2,1,1,'11:00:00','afgeleverd',TRUE),
(3,1,1,'12:00:00',NULL,FALSE),
(4,1,2,'09:00:00','afgeleverd',TRUE);

-- Supplementary data so every database-backed GET screen has non-empty evidence.
INSERT INTO Adres(adres) VALUES ('TEST: Leveranciersweg 1'),('TEST: Prospectlaan 3');
INSERT INTO Leverancier(naam,adres_id,contactpersoon,telefoonnummer)
VALUES ('TEST Fabrikant',3,'TEST contactpersoon','0600000000');
INSERT INTO LeveranciersAanbod(leverancier_id,product_id,inkoopprijs)
VALUES (1,1,65.00);
INSERT INTO ProductWerkzameStof(product_id,stofnaam,hoeveelheid)
VALUES(1,'Teststof','50 mg');
INSERT INTO Magazijnlocatie(gang,schapnummer,product_id,aantal)
VALUES('A',1,1,10);
INSERT INTO Product(artikelnummer,bestelcode,productnaam,prijs_per_grootverpakking,
  aantal_detailverpakkingen,minimale_bestelhoeveelheid,minimumvoorraad)
VALUES('TEST-002','TEST-2','Testtekortproduct',15.00,1,1,9);
INSERT INTO PotentieleKlant(bedrijfsnaam,contactpersoon,contactgegevens,adres_id)
VALUES('TEST Prospectapotheek','TEST prospect','0600000001',4);
INSERT INTO Acquisitiebezoek(potentiele_klant_id,bezoekdatum)
VALUES(1,'2026-09-15');

-- Additional comparable suppliers demonstrate ascending purchase-price sorting.
INSERT INTO Adres(adres) VALUES ('TEST: Leveranciersweg 2'), ('TEST: Leveranciersweg 3');
INSERT INTO Leverancier(naam,adres_id,contactpersoon,telefoonnummer)
VALUES ('TEST Fabrikant duurder',5,'TEST contact duur','0600000002'),
       ('TEST Fabrikant goedkoper',6,'TEST contact goedkoop','0600000003');
INSERT INTO LeveranciersAanbod(leverancier_id,product_id,inkoopprijs)
VALUES (2,1,92.00),(3,1,42.00);
-- An already confirmed purchase order proves the purchasing overview.
INSERT INTO Inkoopbestelling (leverancier_id,besteld_op,status_naam)
VALUES (3,'2026-10-20 08:00:00','besteld');
INSERT INTO Inkoopbestelregel (inkoopbestelling_id,product_id,aantal)
VALUES (1,1,2);
-- A second prospect proves acquisition ordering by last visit.
INSERT INTO Adres(adres) VALUES ('TEST: Prospectlaan 4');
INSERT INTO PotentieleKlant(bedrijfsnaam,contactpersoon,contactgegevens,adres_id)
VALUES ('TEST Prospectapotheek tweede','TEST prospect 2','0600000004',7);
INSERT INTO Acquisitiebezoek(potentiele_klant_id,bezoekdatum)
VALUES (2,'2026-08-15');

-- Start: aanvullende fictieve beoordelingsgegevens voor alle frontendprocessen.
-- Gebruik alleen in de bestaande geisoleerde testdatabase, nooit in productie.
INSERT INTO Robot(robot_id, gang) VALUES (1, 'A'), (2, 'B');

INSERT INTO Adres(adres) VALUES
  ('TEST: Apotheek Noord, Bezorgstraat 5'),
  ('TEST: Apotheek Noord, Factuurstraat 5'),
  ('TEST: Apotheek Zuid, Bezorgstraat 12'),
  ('TEST: Apotheek Zuid, Factuurstraat 12');
INSERT INTO Klant(bedrijfsnaam, telefoonnummer, contactpersoon, afleveradres_id, betaaladres_id)
VALUES
  ('TEST Apotheek Noord', '0600000011', 'TEST contact Noord', 8, 9),
  ('TEST Apotheek Zuid', '0600000012', 'TEST contact Zuid', 10, 11);

INSERT INTO Product(artikelnummer, bestelcode, productnaam, prijs_per_grootverpakking,
                    aantal_detailverpakkingen, minimale_bestelhoeveelheid, minimumvoorraad)
VALUES ('TEST-003', 'TEST-PAK-3', 'Testzorgmiddel', 24.50, 5, 1, 4);
INSERT INTO ProductWerkzameStof(product_id, stofnaam, hoeveelheid)
VALUES (3, 'Teststof B', '20 mg');
INSERT INTO Magazijnlocatie(gang, schapnummer, product_id, aantal)
VALUES ('B', 2, 3, 10);
INSERT INTO LeveranciersAanbod(leverancier_id, product_id, inkoopprijs)
VALUES (1, 3, 14.10), (2, 3, 16.00);

UPDATE Koerier SET regio = 'Testregio Noord' WHERE koerier_id = 1;
INSERT INTO Koerier(naam, regio, extern, beschikbaar)
VALUES
  ('TEST koerier Zuid', 'Testregio Zuid', FALSE, TRUE),
  ('TEST externe spoedkoerier', NULL, TRUE, TRUE);

-- Vier verschillende magazijnstadia, met realistische gereserveerde voorraad.
INSERT INTO Bestelling(klant_id, afleveradres_id, betaaladres_id, besteld_op,
                      gewenste_leverdatum, dagdeel, spoed, status_naam, aantal_verhuisdozen)
VALUES
  (2, 8, 9, '2026-10-21 08:00:00', '2026-10-22', 'ochtend', FALSE, 'nieuw', 0),
  (3, 10, 11, '2026-10-21 08:15:00', '2026-10-22', 'middag', FALSE, 'wordt verzameld', 0),
  (2, 8, 9, '2026-10-21 08:30:00', '2026-10-22', 'ochtend', FALSE, 'wordt verzameld', 0),
  (3, 10, 11, '2026-10-21 09:00:00', '2026-10-22', 'middag', FALSE, 'ingepakt', 1),
  (2, 8, 9, '2026-10-21 09:30:00', '2026-10-22', 'middag', FALSE, 'verstuurd', 1);

INSERT INTO Bestelregel(bestelling_id, product_id, aantal, prijs_per_eenheid)
VALUES (5, 1, 2, 100.00),
       (6, 3, 3, 24.50),
       (7, 1, 1, 100.00),
       (8, 3, 1, 24.50),
       (9, 3, 2, 24.50);
INSERT INTO Voorraadreservering(bestelling_id, product_id, aantal)
VALUES (5, 1, 2), (6, 3, 3);

INSERT INTO Deelorder(bestelling_id, robot_id, afgerond)
VALUES (6, 2, FALSE), (7, 1, TRUE), (8, 2, TRUE), (9, 2, TRUE);
INSERT INTO Deelorderregel(deelorder_id, product_id, aantal)
VALUES (1, 3, 3), (2, 1, 1), (3, 3, 1), (4, 3, 2);
INSERT INTO Verzamelbak(unieke_code, deelorder_id)
VALUES ('TEST-BAK-B006', 1),
       ('TEST-BAK-A007-A', 2),
       ('TEST-BAK-A007-B', 2),
       ('TEST-BAK-B008', 3),
       ('TEST-BAK-B009', 4);

-- Order 8 is verpakt maar nog niet vrijgegeven. Order 9 heeft een mislukte
-- eerste bezorgpoging en een geplande tweede; leveringregels volgen pas na
-- een daadwerkelijk ondertekende aflevering.
INSERT INTO Levering(bestelling_id) VALUES (9);
INSERT INTO Leverpoging(levering_id, pogingnummer, rit_id, geplande_tijd, resultaat, ontvangst_getekend)
VALUES (5, 1, 1, '13:00:00', 'niet aanwezig', FALSE),
       (5, 2, 1, '15:30:00', NULL, FALSE);

-- Een oudere inkooporder heeft expliciet onbekende historische metadata.
INSERT INTO Inkoopbestelling(leverancier_id) VALUES (1);
INSERT INTO Inkoopbestelregel(inkoopbestelling_id, product_id, aantal)
VALUES (2, 3, 5);
-- Einde: fictieve beoordelingsgegevens voor orderpicking en distributie.
