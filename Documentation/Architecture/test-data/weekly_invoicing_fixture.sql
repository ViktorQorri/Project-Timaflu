-- Isolated fictional data for weekly end-to-end MySQL tests (NOT real Timaflu data).
INSERT INTO Adres(adres) VALUES ('TEST: Factuurstraat 12, Breda'), ('TEST: Afleverstraat 8, Breda');
INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id)
VALUES ('TEST Apotheek B.V.','0612345678','TEST medewerker',2,1);
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
