-- Isolated fictional Timaflu data for the assessed scenario query outputs.
INSERT INTO Adres(adres) VALUES ('Testapotheekstraat 1, Breda');
INSERT INTO Adres(adres) VALUES ('Fabrikantweg 2, Breda');
INSERT INTO Adres(adres) VALUES ('Prospectlaan 3, Tilburg');
INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id)
VALUES ('Testapotheek Breda','0612345678','Testcontact',1,1);
INSERT INTO Leverancier(naam,adres_id,contactpersoon,telefoonnummer)
VALUES ('Fabrikant A',2,'Contact A','0611111111');
INSERT INTO Leverancier(naam,adres_id,contactpersoon,telefoonnummer)
VALUES ('Fabrikant B',2,'Contact B','0622222222');
INSERT INTO Product(artikelnummer,bestelcode,productnaam,prijs_per_grootverpakking,aantal_detailverpakkingen,minimale_bestelhoeveelheid,minimumvoorraad)
VALUES('TM-001','CODE-001','Testmedicijn',20.00,1,1,5);
INSERT INTO LeveranciersAanbod(leverancier_id,product_id,inkoopprijs)
VALUES (1,1,15.00),(2,1,12.00);
INSERT INTO Bestelling(klant_id,afleveradres_id,betaaladres_id,besteld_op,gewenste_leverdatum,dagdeel,spoed,status_naam)
VALUES (1,1,1,'2025-09-01 10:00:00','2025-09-02','ochtend',FALSE,'afgeleverd');
INSERT INTO Bestelregel(bestelling_id,product_id,aantal,prijs_per_eenheid)
VALUES (1,1,2,20.00);
INSERT INTO Factuur(klant_id,factuurdatum,betaald_op)
VALUES (1,'2025-09-05','2025-10-10');
-- This fictional invoice was explicitly calculated once, using the
-- case's first-order discount of 10% and 5% customer discount.
UPDATE Factuur SET bedrag_excl_btw=40.00, btw_bedrag=3.60,
    bedrag_incl_btw=43.60, bestellingskorting=0.00,
    bedrag_na_bestellingskorting=43.60, eenmalige_korting=4.36,
    bedrag_na_eenmalige_korting=39.24, klantenkorting=1.96,
    totaal_bedrag=37.28 WHERE factuur_id=1;
INSERT INTO Levering(bestelling_id) VALUES(1);
INSERT INTO Leveringregel(levering_id,product_id,aantal_geleverd,factuur_id)
VALUES(1,1,2,1);

-- Distinct unpaid 2026 invoice: only real delivered lines and explicit historical totals.
INSERT INTO Bestelling(klant_id,afleveradres_id,betaaladres_id,besteld_op,gewenste_leverdatum,dagdeel,spoed,status_naam)
VALUES (1,1,1,'2026-10-08 09:00:00','2026-10-09','ochtend',FALSE,'afgeleverd');
INSERT INTO Bestelregel(bestelling_id,product_id,aantal,prijs_per_eenheid)
VALUES (2,1,2,20.00);
INSERT INTO Factuur(klant_id,factuurdatum,betaald_op)
VALUES (1,'2026-10-10',NULL);
-- Previous-year net paid turnover is 37.28, so customer discount is 5%.
-- This is not a first order. The test total was explicitly calculated.
UPDATE Factuur SET bedrag_excl_btw=40.00, btw_bedrag=3.60,
    bedrag_incl_btw=43.60, bestellingskorting=0.00,
    bedrag_na_bestellingskorting=43.60, eenmalige_korting=0.00,
    bedrag_na_eenmalige_korting=43.60, klantenkorting=2.18,
    totaal_bedrag=41.42 WHERE factuur_id=2;
INSERT INTO Levering(bestelling_id) VALUES(2);
INSERT INTO Leveringregel(levering_id,product_id,aantal_geleverd,factuur_id)
VALUES(2,1,2,2);

INSERT INTO Koerier(naam,beschikbaar) VALUES ('Testkoerier',TRUE);
INSERT INTO Rit(koerier_id,ritdatum) VALUES(1,'2026-10-31');
INSERT INTO PotentieleKlant(bedrijfsnaam,contactpersoon,contactgegevens,adres_id)
VALUES('Prospectapotheek Tilburg','Prospectcontact','0633333333',3);
INSERT INTO Acquisitiebezoek(potentiele_klant_id,bezoekdatum) VALUES(1,'2026-09-15');

-- Additional unpaid example: a delivered order from October 2026.
-- The original paid 2025 invoice stays available for annual-revenue calculations.
INSERT INTO Bestelling(klant_id,afleveradres_id,betaaladres_id,besteld_op,gewenste_leverdatum,dagdeel,spoed,status_naam)
VALUES (1,1,1,'2026-10-25 10:00:00','2026-10-26','ochtend',FALSE,'afgeleverd');
INSERT INTO Bestelregel(bestelling_id,product_id,aantal,prijs_per_eenheid)
VALUES (2,1,1,20.00);
INSERT INTO Levering(bestelling_id) VALUES (2);
INSERT INTO Factuur(klant_id,factuurdatum,betaald_op)
VALUES (1,'2026-10-31',NULL);
-- 20.00 + 9% VAT, 0 order discount, no first-order incentive,
-- 5% customer discount as the 2025 paid turnover was below EUR 10,000.
UPDATE Factuur SET bedrag_excl_btw=20.00, btw_bedrag=1.80,
    bedrag_incl_btw=21.80, bestellingskorting=0.00,
    bedrag_na_bestellingskorting=21.80, eenmalige_korting=0.00,
    bedrag_na_eenmalige_korting=21.80, klantenkorting=1.09,
    totaal_bedrag=20.71 WHERE factuur_id=2;
INSERT INTO Leveringregel(levering_id,product_id,aantal_geleverd,factuur_id)
VALUES (2,1,1,2);

-- A different, not-yet-delivered shipment is the courier's planned same-day route.
INSERT INTO Bestelling(klant_id,afleveradres_id,betaaladres_id,besteld_op,gewenste_leverdatum,dagdeel,spoed,status_naam)
VALUES (1,1,1,'2026-10-30 12:00:00','2026-10-31','ochtend',FALSE,'verstuurd');
INSERT INTO Bestelregel(bestelling_id,product_id,aantal,prijs_per_eenheid)
VALUES (3,1,1,20.00);
INSERT INTO Levering(bestelling_id) VALUES (3);
INSERT INTO Leverpoging(levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
VALUES (3,1,1,'10:00:00',NULL,FALSE);

-- Acquisition boundary: account WITHOUT an order remains actionable;
-- an account WITH an order is excluded from the follow-up list.
INSERT INTO Adres(adres) VALUES ('Nieuwe apotheekstraat 4, Eindhoven');
INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id)
VALUES ('Testapotheek Eindhoven','0644444444','Contact Eindhoven',4,4);
INSERT INTO PotentieleKlant(bedrijfsnaam,contactpersoon,contactgegevens,adres_id,klant_id)
VALUES ('Testapotheek Eindhoven','Contact Eindhoven','0644444444',4,2),
       ('Testapotheek Breda','Testcontact','0612345678',1,1);
INSERT INTO Acquisitiebezoek(potentiele_klant_id,bezoekdatum)
VALUES (2,'2026-08-15'),(3,'2026-08-01');
