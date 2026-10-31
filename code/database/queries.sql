-- Stock shortage dashboard, GET /stock
-- Keep this query in sync with StockRepository.list_stock_below_minimum().
-- This version uses no parameters; its result depends on current warehouse data.
SELECT p.product_id, p.artikelnummer, p.productnaam,
       p.minimumvoorraad,
       COALESCE(SUM(m.aantal), 0) AS voorraad
FROM Product AS p
LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
GROUP BY p.product_id, p.artikelnummer, p.productnaam,
         p.minimumvoorraad
HAVING voorraad < p.minimumvoorraad
ORDER BY (p.minimumvoorraad - voorraad) DESC,
         p.productnaam ASC;

-- Supplier offers for GET /suppliers?product=...
-- Example parameter 'Medication': backend uses LIKE %s with value '%Medication%'.
SELECT p.product_id, p.productnaam, l.leverancier_id, l.naam AS leverancier,
       l.contactpersoon, l.telefoonnummer, a.inkoopprijs
FROM Product AS p
JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id
JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id
WHERE p.productnaam LIKE '%Medication%'
ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC;

-- Recording a purchasing order after the employee has contacted the manufacturer.
-- The supplier-product relationship is validated by PurchaseOrderRepository.
SELECT 1 FROM LeveranciersAanbod
WHERE leverancier_id = 1 AND product_id = 1;
INSERT INTO Inkoopbestelling (leverancier_id) VALUES (1);
INSERT INTO Inkoopbestelregel (inkoopbestelling_id, product_id, aantal)
VALUES (LAST_INSERT_ID(), 1, 10);
-- Both INSERT statements are one transaction in the application.

-- Telephone-sales availability lookup, GET /orders?q=...&quantity=...
-- Same SELECT as SalesStockRepository.find_products() with example parameters.
-- Availability = physical stock minus stock reserved for open orders.
SELECT p.product_id, p.artikelnummer, p.productnaam,
       COALESCE(m.voorraad, 0) AS voorraad,
       COALESCE(r.gereserveerd, 0) AS gereserveerd,
       GREATEST(COALESCE(m.voorraad, 0) -
                COALESCE(r.gereserveerd, 0), 0) AS beschikbaar
FROM Product AS p
LEFT JOIN (
    SELECT product_id, SUM(aantal) AS voorraad
    FROM Magazijnlocatie GROUP BY product_id
) AS m ON m.product_id = p.product_id
LEFT JOIN (
    SELECT product_id, SUM(aantal) AS gereserveerd
    FROM Voorraadreservering GROUP BY product_id
) AS r ON r.product_id = p.product_id
WHERE p.productnaam LIKE '%Medication%' OR p.artikelnummer LIKE '%Medication%'
ORDER BY p.productnaam ASC;

-- AssessedRepository SQL for the five required backend scenarios.
-- Example literals replace the exact %s placeholders in repository SQL.
-- Output must be recorded from a real MySQL instance; never invented.

-- AssessedRepository.customer_revenue
-- Query 1 (illustrative input, not a claimed database result)
SELECT klant_id, bedrijfsnaam FROM Klant WHERE klant_id=1;
-- Query 2 (illustrative input, not a claimed database result)
SELECT 1 FROM Factuur WHERE klant_id=1
                         AND incasso_ingeschakeld=TRUE AND betaald_op IS NULL
                         LIMIT 1;
-- Query 3 (illustrative input, not a claimed database result)
SELECT COALESCE(SUM(l.aantal_geleverd * b.prijs_per_eenheid),0) AS annual
                FROM Factuur f JOIN Leveringregel l ON l.factuur_id=f.factuur_id
                JOIN Levering v ON v.levering_id=l.levering_id
                JOIN Bestelregel b ON b.bestelling_id=v.bestelling_id AND b.product_id=l.product_id
                WHERE f.klant_id=1 AND f.betaald_op>= '2025-01-01' AND f.betaald_op< '2026-01-01';

-- AssessedRepository.customer_order_count
-- Query 1 (illustrative input, not a claimed database result)
SELECT COUNT(*) FROM Bestelling WHERE klant_id=1;

-- AssessedRepository.invoice_for_customer
-- Query 1 (illustrative input, not a claimed database result)
SELECT f.factuur_id, f.factuurdatum, f.betaald_op, f.betalingsregeling_geaccepteerd,
                       f.incasso_ingeschakeld, k.bedrijfsnaam, a.adres
                FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id
                JOIN Adres a ON a.adres_id=k.betaaladres_id
                WHERE f.klant_id=1 ORDER BY f.factuurdatum DESC;
-- Query 2 (illustrative input, not a claimed database result)
SELECT l.aantal_geleverd AS quantity, b.prijs_per_eenheid AS unit_price
                    FROM Leveringregel l JOIN Levering v ON v.levering_id=l.levering_id
                    JOIN Bestelregel b ON b.bestelling_id=v.bestelling_id AND b.product_id=l.product_id
                    WHERE l.factuur_id=1;

-- AssessedRepository.delivery_schedule
-- Query 1 (illustrative input, not a claimed database result)
SELECT lp.levering_id, lp.pogingnummer, lp.geplande_tijd, lp.resultaat,
                       b.bestelling_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                       a.adres, r.ritdatum
                FROM Leverpoging lp
                JOIN Rit r ON r.rit_id=lp.rit_id
                JOIN Levering l ON l.levering_id=lp.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                JOIN Klant k ON k.klant_id=b.klant_id
                JOIN Adres a ON a.adres_id=b.afleveradres_id
                WHERE r.ritdatum='2026-10-30' ORDER BY lp.geplande_tijd;

-- AssessedRepository.register_delivery_attempt
-- Query 1 (illustrative input, not a claimed database result)
SELECT lp.rit_id, lp.pogingnummer, lp.resultaat
                             FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id
                             WHERE lp.levering_id=1 AND r.ritdatum=CURRENT_DATE()
                             ORDER BY lp.pogingnummer DESC FOR UPDATE;
-- Query 2 (illustrative input, not a claimed database result)
UPDATE Leverpoging SET resultaat='niet aanwezig' WHERE levering_id=1 AND pogingnummer=1;
-- Query 3 (illustrative input, not a claimed database result)
INSERT INTO Leverpoging (levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
                             VALUES (1,2,1,'14:00:00','niet aanwezig',0);
-- Query 4 (illustrative input, not a claimed database result)
UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id SET b.status_naam='afgeleverd' WHERE l.levering_id=1;

-- AssessedRepository.prospect_followups
-- Query 1 (illustrative input, not a claimed database result)
SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
                       p.contactgegevens, a.adres, MAX(v.bezoekdatum) AS bezoekdatum
                FROM PotentieleKlant p JOIN Acquisitiebezoek v ON v.potentiele_klant_id=p.potentiele_klant_id
                JOIN Adres a ON a.adres_id=p.adres_id
                WHERE p.klant_id IS NULL
                GROUP BY p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,p.contactgegevens,a.adres
                HAVING MAX(v.bezoekdatum)<='2026-09-30'
                ORDER BY bezoekdatum;

-- AssessedRepository.record_visit
-- Query 1 (illustrative input, not a claimed database result)
INSERT INTO Adres (adres) VALUES ('Voorbeeldstraat 1');
-- Query 2 (illustrative input, not a claimed database result)
INSERT INTO PotentieleKlant (bedrijfsnaam,contactpersoon,contactgegevens,adres_id) VALUES ('Testapotheek','Contact','0612345678',1);
-- Query 3 (illustrative input, not a claimed database result)
INSERT INTO Acquisitiebezoek (potentiele_klant_id,bezoekdatum) VALUES (1,'2026-09-30');

-- AssessedRepository.register_prospect_customer
-- Query 1 (illustrative input, not a claimed database result)
SELECT * FROM PotentieleKlant WHERE potentiele_klant_id=1 FOR UPDATE;
-- Query 2 (illustrative input, not a claimed database result)
INSERT INTO Adres (adres) VALUES ('Factuuradres 1');
-- Query 3 (illustrative input, not a claimed database result)
INSERT INTO Adres (adres) VALUES ('Afleveradres 1');
-- Query 4 (illustrative input, not a claimed database result)
INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id)
                             VALUES('Testapotheek','0612345678','Contact',1,2);
-- Query 5 (illustrative input, not a claimed database result)
UPDATE PotentieleKlant SET klant_id=1 WHERE potentiele_klant_id=1;

-- AssessedRepository.record_payment_action
-- Query 1 (illustrative input, not a claimed database result)
SELECT f.factuur_id,f.klant_id,f.factuurdatum,f.betaald_op FROM Factuur f WHERE f.factuur_id=1 FOR UPDATE;
-- Query 2 (illustrative input, not a claimed database result)
INSERT INTO Betalingsherinnering(factuur_id,volgnummer,verstuurd_op) VALUES(1,1,'2026-10-30');
-- Query 3 (illustrative input, not a claimed database result)
SELECT 1 FROM Betalingsherinnering WHERE factuur_id=1 AND volgnummer=1;
-- Query 4 (illustrative input, not a claimed database result)
UPDATE Factuur SET betalingsregeling_geaccepteerd=TRUE WHERE factuur_id=1;
-- Query 5 (illustrative input, not a claimed database result)
UPDATE Factuur SET betalingsregeling_geaccepteerd=FALSE, incasso_ingeschakeld=TRUE WHERE factuur_id=1;
-- Query 6 (illustrative input, not a claimed database result)
UPDATE Factuur SET betaald_op='2026-10-30' WHERE factuur_id=1;
