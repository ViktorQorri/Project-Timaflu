-- Stock shortage dashboard, GET /stock
-- Keep this query in sync with StockRepository.list_stock_below_minimum().
-- This version uses no parameters; its result depends on current warehouse data.
SELECT p.product_id, p.artikelnummer, p.productnaam,
       p.minimumvoorraad,
       COALESCE(SUM(m.aantal), 0) AS voorraad,
       EXISTS (
           SELECT 1 FROM LeveranciersAanbod AS a
           WHERE a.product_id = p.product_id
       ) AS heeft_leverancier
FROM Product AS p
LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
WHERE p.in_assortiment = TRUE
GROUP BY p.product_id, p.artikelnummer, p.productnaam,
         p.minimumvoorraad
HAVING voorraad < p.minimumvoorraad
ORDER BY (p.minimumvoorraad - voorraad) DESC,
         p.productnaam ASC;

-- Supplier offers for GET /suppliers?product=...
-- Example parameter 'Medication': backend uses LIKE %s with value '%Medication%'.
SELECT p.product_id, p.productnaam, l.leverancier_id, l.naam AS leverancier,
       l.contactpersoon, l.telefoonnummer, l.internetadres, a.inkoopprijs
FROM Product AS p
JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id
JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id
WHERE p.productnaam LIKE '%Medication%' AND p.intern_bestelbaar = TRUE AND p.in_assortiment = TRUE
ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC;



-- Purchasing: unlink a manufacturer that no longer supplies the medicine.
-- Mirrors SupplierRepository.remove_offer() with example identifiers.
DELETE FROM LeveranciersAanbod WHERE product_id=1 AND leverancier_id=2;

-- When all manufacturers have stopped supplying the medicine, remove the
-- internal reorder entry while preserving the sales catalog and history.
-- Mirrors SupplierRepository.remove_from_internal_reorder_list().
UPDATE Product SET intern_bestelbaar=FALSE WHERE product_id=1;

-- Recording a purchasing order after the employee has contacted the manufacturer.
-- The supplier-product relationship is validated by PurchaseOrderRepository.
SELECT 1 FROM LeveranciersAanbod AS a
JOIN Product AS p ON p.product_id = a.product_id
WHERE a.leverancier_id = 1 AND a.product_id = 1
  AND p.in_assortiment = TRUE AND p.intern_bestelbaar = TRUE;
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
WHERE (p.productnaam LIKE '%Medication%' OR p.artikelnummer LIKE '%Medication%')
  AND p.in_assortiment = TRUE
ORDER BY p.productnaam ASC;

-- AssessedRepository SQL for the five required backend scenarios.
-- Example literals replace the exact %s placeholders in repository SQL.
-- Output must be recorded from a real MySQL instance; never invented.

-- AssessedRepository.customer_revenue
-- Query 1 (illustrative input, not a claimed database result)
SELECT k.klant_id, k.bedrijfsnaam,
                                k.eenmalige_korting_toegezegd, a.adres AS klantadres FROM Klant k
                         JOIN Adres a ON a.adres_id=k.betaaladres_id
                         WHERE k.klant_id=1;
-- Query 2 (illustrative input, not a claimed database result)
SELECT 1 FROM Factuur WHERE klant_id=1
                         AND incasso_ingeschakeld=TRUE AND betaald_op IS NULL
                         LIMIT 1;
-- Query 3 (net paid invoice amounts; missing totals are detected in repository)
SELECT COUNT(*) AS paid_count,
                       COUNT(f.totaal_bedrag) AS known_amount_count,
                       COALESCE(SUM(f.totaal_bedrag),0) AS annual
                FROM Factuur AS f
                WHERE f.klant_id=1 AND f.betaald_op>= '2025-01-01' AND f.betaald_op< '2026-01-01';

-- AssessedRepository.customer_order_count
-- Query 1 (illustrative input, not a claimed database result)
SELECT COUNT(*) FROM Bestelling WHERE klant_id=1;

-- AssessedRepository.invoice_for_customer
-- Query 1 (illustrative input, not a claimed database result)
SELECT f.factuur_id, f.factuurdatum, f.betaald_op, f.betalingsregeling_geaccepteerd,
                       f.incasso_ingeschakeld,
       f.bedrag_excl_btw,
       f.btw_bedrag,
       f.bedrag_incl_btw,
       f.bestellingskorting,
       f.bedrag_na_bestellingskorting,
       f.eenmalige_korting,
       f.bedrag_na_eenmalige_korting,
       f.klantenkorting,
       f.totaal_bedrag,
       k.bedrijfsnaam, a.adres
                FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id
                JOIN Adres a ON a.adres_id=k.betaaladres_id
WHERE f.klant_id=1 AND f.betaald_op IS NULL
                ORDER BY f.factuurdatum DESC;
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

-- AssessedRepository.record_first_attempt_delivery
-- First visit: complete only after signed receipt, without a second attempt.
SELECT lp.resultaat FROM Leverpoging lp
                       JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=1 AND lp.pogingnummer=1 AND r.ritdatum='2026-10-30'
                       FOR UPDATE;
UPDATE Leverpoging SET resultaat='afgeleverd', ontvangst_getekend=TRUE
                       WHERE levering_id=1 AND pogingnummer=1;
UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
                       SET b.status_naam='afgeleverd' WHERE l.levering_id=1;

-- AssessedRepository.schedule_second_attempt
-- Query 1 (illustrative input, not a claimed database result)
SELECT lp.rit_id, lp.pogingnummer, lp.resultaat,
                              TIME_TO_SEC(lp.geplande_tijd) AS first_attempt_seconds
                       FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=1 AND r.ritdatum='2026-10-30'
                       ORDER BY lp.pogingnummer DESC FOR UPDATE;
-- Query 2 (illustrative input, not a claimed database result)
UPDATE Leverpoging SET resultaat='niet aanwezig',
                              ontvangst_getekend=FALSE
                       WHERE levering_id=1 AND pogingnummer=1;
-- Query 3 (illustrative input, not a claimed database result)
INSERT INTO Leverpoging
                       (levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
                       VALUES (1,2,1,'14:00:00',NULL,NULL);

-- AssessedRepository.record_second_attempt_outcome
-- Query 1 (illustrative input, not a claimed database result)
SELECT lp.resultaat FROM Leverpoging lp
                       JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=1 AND lp.pogingnummer=2 AND r.ritdatum='2026-10-30'
                       FOR UPDATE;
-- Query 2 (illustrative input, not a claimed database result)
UPDATE Leverpoging SET resultaat='afgeleverd', ontvangst_getekend=1
                       WHERE levering_id=1 AND pogingnummer=2;
-- Query 3 (illustrative input, not a claimed database result)
UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
                           SET b.status_naam='afgeleverd' WHERE l.levering_id=1;
-- If the second attempt also fails, do not leave the order marked dispatched or delivered.
UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
                           SET b.status_naam='niet afgeleverd' WHERE l.levering_id=1;

-- AssessedRepository.record_failed_delivery_followup
-- Sales confirms the new delivery agreement after two failed attempts.
SELECT b.bestelling_id, r.ritdatum FROM Bestelling b
                       JOIN Levering l ON l.bestelling_id=b.bestelling_id
                       JOIN Leverpoging lp ON lp.levering_id=l.levering_id AND lp.pogingnummer=2
                       JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE l.levering_id=1 AND lp.resultaat='niet aanwezig'
                       FOR UPDATE;
UPDATE Bestelling SET gewenste_leverdatum='2026-11-02', dagdeel='ochtend',
                       extra_bezorgkosten=10.00, toelichting_extra_bezorgkosten='Klant tweemaal afwezig'
                       WHERE bestelling_id=1;

-- AssessedRepository.prospect_followups
-- Query 1 (illustrative input, not a claimed database result)
SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
                       p.contactgegevens, a.adres, p.klant_id,
                       MAX(v.bezoekdatum) AS bezoekdatum
                FROM PotentieleKlant p JOIN Acquisitiebezoek v ON v.potentiele_klant_id=p.potentiele_klant_id
                JOIN Adres a ON a.adres_id=p.adres_id
                WHERE p.opvolging_afgesloten=FALSE AND NOT EXISTS (
                    SELECT 1 FROM Bestelling b WHERE b.klant_id = p.klant_id
                )
                GROUP BY p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,p.contactgegevens,a.adres,p.klant_id
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
-- Query 2: the most recent visit must have taken place at least a calendar month earlier.
SELECT MAX(bezoekdatum) AS laatste_bezoek FROM Acquisitiebezoek
WHERE potentiele_klant_id=1;
-- Query 3 (illustrative input, not a claimed database result)
INSERT INTO Adres (adres) VALUES ('Factuuradres 1');
-- Query 3 (illustrative input, not a claimed database result)
INSERT INTO Adres (adres) VALUES ('Afleveradres 1');
-- Query 4 (illustrative input, not a claimed database result)
INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id,eenmalige_korting_toegezegd)
                             VALUES('Testapotheek','0612345678','Contact',1,2,TRUE);
-- Query 5 (illustrative input, not a claimed database result)
UPDATE PotentieleKlant SET klant_id=1, opvolging_afgesloten=TRUE WHERE potentiele_klant_id=1;

-- AssessedRepository.close_prospect_followup (only after a month and explicit refusal)
-- Query 1: lock the prospective customer to avoid simultaneous conversion.
SELECT klant_id, opvolging_afgesloten FROM PotentieleKlant
WHERE potentiele_klant_id=1 FOR UPDATE;
-- Query 2: last visit must be at least one month old.
SELECT MAX(bezoekdatum) AS laatste_bezoek FROM Acquisitiebezoek
WHERE potentiele_klant_id=1;
-- Query 3: only when linked to an existing customer; do not retry someone who ordered.
SELECT COUNT(*) AS aantal FROM Bestelling WHERE klant_id=1;
-- Query 4: no more acquisition once interest is declined.
UPDATE PotentieleKlant SET opvolging_afgesloten=TRUE
WHERE potentiele_klant_id=1;

-- AssessedRepository.record_payment_action
-- Query 1 (illustrative input, not a claimed database result)
SELECT f.factuur_id,f.klant_id,f.factuurdatum,f.betaald_op FROM Factuur f WHERE f.factuur_id=1 FOR UPDATE;
-- Query 2 (illustrative input, not a claimed database result)
INSERT INTO Betalingsherinnering(factuur_id,volgnummer,verstuurd_op) VALUES(1,1,'2026-10-30');
-- Query 3 (illustrative input, not a claimed database result)
SELECT verstuurd_op FROM Betalingsherinnering WHERE factuur_id=1 AND volgnummer=1;
-- Hetzelfde SELECT wordt ook gebruikt voor volgnummer=2, om dubbele herinneringen te voorkomen.
SELECT verstuurd_op FROM Betalingsherinnering WHERE factuur_id=1 AND volgnummer=2;
-- Query 4 (illustrative input, not a claimed database result)
UPDATE Factuur SET betalingsregeling_geaccepteerd=TRUE WHERE factuur_id=1;
-- Query 5 (illustrative input, not a claimed database result)
UPDATE Factuur SET betalingsregeling_geaccepteerd=FALSE, incasso_ingeschakeld=TRUE WHERE factuur_id=1;
-- Query 6 (illustrative input, not a claimed database result)
UPDATE Factuur SET betaald_op='2026-10-30' WHERE factuur_id=1;

-- Issue #15: minimum stock settings overview.
SELECT p.product_id, p.artikelnummer, p.productnaam,
       p.minimumvoorraad,
       COALESCE(SUM(m.aantal), 0) AS voorraad
FROM Product AS p
LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
WHERE p.in_assortiment = TRUE
GROUP BY p.product_id, p.artikelnummer, p.productnaam,
         p.minimumvoorraad
ORDER BY p.productnaam, p.product_id;

-- Transactional minimum stock setting (repository uses %s).
SELECT product_id FROM Product WHERE product_id = 1 AND in_assortiment = TRUE FOR UPDATE;
UPDATE Product SET minimumvoorraad = 15 WHERE product_id = 1;

-- Product catalog, GET /products (issue #13)
-- Same SELECTs as ProductRepository.list_in_assortment(). No parameters.
SELECT p.product_id, p.artikelnummer, p.bestelcode, p.productnaam,
       p.prijs_per_grootverpakking, p.verpakkingssoort, p.aantal_detailverpakkingen,
       p.korte_omschrijving, p.lange_omschrijving, p.minimale_bestelhoeveelheid,
       p.minimumvoorraad, p.in_assortiment
FROM Product AS p
WHERE p.in_assortiment = TRUE
ORDER BY p.productnaam ASC, p.artikelnummer ASC;

SELECT w.product_id, w.stofnaam, w.hoeveelheid
FROM ProductWerkzameStof AS w
JOIN Product AS p ON p.product_id = w.product_id
WHERE p.in_assortiment = TRUE
ORDER BY w.stofnaam ASC;

-- Add product form, GET /products/new: the suppliers to choose from.
-- Same SELECT as SupplierRepository.list_all().
SELECT leverancier_id, naam, contactpersoon, telefoonnummer, internetadres
FROM Leverancier
ORDER BY naam ASC;

-- Add product, POST /products/new: check the chosen supplier exists.
-- Same SELECT as SupplierRepository.get_by_id() with example parameter 1.
SELECT leverancier_id, naam, contactpersoon, telefoonnummer, internetadres
FROM Leverancier
WHERE leverancier_id = 1;

-- Add or edit product: is the article number or order code already in use?
-- Same SELECT as ProductRepository.find_code_owners(). Example: a new product,
-- so the product to skip is NULL. When editing, NULL is the edited product_id.
SELECT product_id, artikelnummer, bestelcode, productnaam, in_assortiment
FROM Product
WHERE (artikelnummer = 'TIM-1001' OR bestelcode = 'BC-1001')
  AND (NULL IS NULL OR product_id <> NULL);

-- Add product, POST /products/new: ProductRepository.add().
-- The three statements are one transaction in the application.
INSERT INTO Product (
    artikelnummer, bestelcode, productnaam, prijs_per_grootverpakking,
    verpakkingssoort, aantal_detailverpakkingen, korte_omschrijving,
    lange_omschrijving, minimale_bestelhoeveelheid, minimumvoorraad
)
VALUES ('TIM-1001', 'BC-1001', 'Paracetamol 500 mg', 24.50, 'box', 20,
        'Pain relief and fever reduction', 'Tablets for mild to moderate pain.', 5, 40);
-- One INSERT per entered active ingredient.
INSERT INTO ProductWerkzameStof (product_id, stofnaam, hoeveelheid)
VALUES (LAST_INSERT_ID(), 'paracetamol', '500 mg');
-- In the application the new product_id comes from cursor.lastrowid.
INSERT INTO LeveranciersAanbod (leverancier_id, product_id, inkoopprijs)
VALUES (1, (SELECT product_id FROM Product WHERE artikelnummer = 'TIM-1001'), 18.75);

-- Edit product form, GET /products/<id>/edit: ProductRepository.get_by_id()
-- with example parameter 1.
SELECT p.product_id, p.artikelnummer, p.bestelcode, p.productnaam,
       p.prijs_per_grootverpakking, p.verpakkingssoort, p.aantal_detailverpakkingen,
       p.korte_omschrijving, p.lange_omschrijving, p.minimale_bestelhoeveelheid,
       p.minimumvoorraad, p.in_assortiment
FROM Product AS p
WHERE p.product_id = 1 AND p.in_assortiment = TRUE;

SELECT product_id, stofnaam, hoeveelheid
FROM ProductWerkzameStof
WHERE product_id = 1
ORDER BY stofnaam ASC;

-- Edit product, POST /products/<id>/edit: ProductRepository.update()
-- with example product 1. All statements are one transaction in the application;
-- the active ingredients are replaced as a whole.
SELECT product_id FROM Product
WHERE product_id = 1 AND in_assortiment = TRUE FOR UPDATE;
UPDATE Product
SET artikelnummer = 'TIM-1001', bestelcode = 'BC-1001', productnaam = 'Paracetamol 500 mg',
    prijs_per_grootverpakking = 25.00, verpakkingssoort = 'box',
    aantal_detailverpakkingen = 20, korte_omschrijving = 'Pain relief and fever reduction',
    lange_omschrijving = 'Tablets for mild to moderate pain.', minimale_bestelhoeveelheid = 5,
    minimumvoorraad = 50
WHERE product_id = 1;
DELETE FROM ProductWerkzameStof WHERE product_id = 1;
INSERT INTO ProductWerkzameStof (product_id, stofnaam, hoeveelheid)
VALUES (1, 'paracetamol', '500 mg');

-- Remove product, POST /products/<id>/remove: ProductRepository.remove_from_assortment()
-- with example product 1. The row stays, so orders, deliveries and invoices keep working.
UPDATE Product SET in_assortiment = FALSE
WHERE product_id = 1 AND in_assortiment = TRUE;

-- Issue #14: manufacturer management (repository uses %s placeholders).
SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon,
       l.telefoonnummer, l.internetadres
FROM Leverancier AS l
JOIN Adres AS a ON a.adres_id = l.adres_id
ORDER BY l.naam, l.leverancier_id;

SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon,
       l.telefoonnummer, l.internetadres
FROM Leverancier AS l
JOIN Adres AS a ON a.adres_id = l.adres_id
WHERE l.leverancier_id = 1;

-- One transaction: create an address and manufacturer.
INSERT INTO Adres (adres) VALUES ('Voorbeeldstraat 1, Breda');
INSERT INTO Leverancier (naam, adres_id, contactpersoon, telefoonnummer, internetadres)
VALUES ('Voorbeeldfabrikant', LAST_INSERT_ID(), 'Contactpersoon', '0761234567', 'https://example.org');

-- Update transaction checks existence and writes a new address before updating manufacturer.
SELECT adres_id FROM Leverancier WHERE leverancier_id = 1 FOR UPDATE;
INSERT INTO Adres (adres) VALUES ('Nieuw adres 2, Breda');
UPDATE Leverancier
SET naam = 'Voorbeeldfabrikant', adres_id = LAST_INSERT_ID(),
    contactpersoon = 'Contactpersoon', telefoonnummer = '0761234567',
    internetadres = 'https://example.org'
WHERE leverancier_id = 1;

SELECT product_id, productnaam, artikelnummer
FROM Product ORDER BY productnaam, product_id;

SELECT a.product_id, p.productnaam, a.inkoopprijs
FROM LeveranciersAanbod AS a
JOIN Product AS p ON p.product_id = a.product_id
WHERE a.leverancier_id = 1
ORDER BY p.productnaam, a.product_id;

-- One transaction: validate manufacturer and product before upserting purchase price.
SELECT 1 FROM Leverancier WHERE leverancier_id = 1;
SELECT 1 FROM Product WHERE product_id = 1;
INSERT INTO LeveranciersAanbod (leverancier_id, product_id, inkoopprijs)
VALUES (1, 1, 12.50)
ON DUPLICATE KEY UPDATE inkoopprijs = VALUES(inkoopprijs);

-- Issue #15: minimum stock settings overview.
SELECT p.product_id, p.artikelnummer, p.productnaam,
       p.minimumvoorraad,
       COALESCE(SUM(m.aantal), 0) AS voorraad
FROM Product AS p
LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
GROUP BY p.product_id, p.artikelnummer, p.productnaam,
         p.minimumvoorraad
ORDER BY p.productnaam, p.product_id;

-- Transactional minimum stock setting (repository uses %s).
SELECT product_id FROM Product WHERE product_id = 1 FOR UPDATE;
UPDATE Product SET minimumvoorraad = 15 WHERE product_id = 1;

-- Issue #16: robot order dispatch for an existing aisle-specific sub-order.
SELECT robot_id, gang FROM Robot WHERE robot_id = 1 AND gang = 'A';

SELECT deelorder_id, bestelling_id
FROM Deelorder WHERE robot_id = 1 AND afgerond = FALSE
ORDER BY deelorder_id ASC LIMIT 1;

SELECT dr.product_id, p.productnaam, dr.aantal
FROM Deelorderregel AS dr
JOIN Product AS p ON p.product_id = dr.product_id
WHERE dr.deelorder_id = 1
ORDER BY p.productnaam, dr.product_id;

-- Complete in one transaction, after a registered picking bin exists.
SELECT deelorder_id, afgerond
FROM Deelorder WHERE deelorder_id = 1 AND robot_id = 1 FOR UPDATE;
SELECT COUNT(*) AS bin_count FROM Verzamelbak WHERE deelorder_id = 1;
SELECT COUNT(*) AS line_count FROM Deelorderregel WHERE deelorder_id = 1;
UPDATE Deelorder SET afgerond = TRUE WHERE deelorder_id = 1;

-- Issue #16: allocate reserved quantities across robots / warehouse aisles.
-- All reads, assignments and writes run in one transaction.
SELECT bestelling_id FROM Bestelling WHERE bestelling_id = 1 FOR UPDATE;
SELECT COUNT(*) AS assigned_count FROM Deelorder WHERE bestelling_id = 1;
SELECT product_id, aantal FROM Voorraadreservering
WHERE bestelling_id = 1 ORDER BY product_id;

-- For each reserved product, lock its row to serialize concurrent allocations.
SELECT product_id FROM Product WHERE product_id = 7 FOR UPDATE;
SELECT r.robot_id, m.gang,
       SUM(m.aantal) AS physical_stock,
       COALESCE((
         SELECT SUM(dr.aantal)
         FROM Deelorderregel AS dr
         JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id
         WHERE dr.product_id = 7 AND d.robot_id = r.robot_id
       ), 0) AS already_assigned
FROM Magazijnlocatie AS m
JOIN Robot AS r ON r.gang = m.gang
WHERE m.product_id = 7
GROUP BY r.robot_id, m.gang
ORDER BY m.gang, r.robot_id;

INSERT INTO Deelorder (bestelling_id, robot_id) VALUES (1, 1);
INSERT INTO Deelorderregel (deelorder_id, product_id, aantal)
VALUES (LAST_INSERT_ID(), 7, 3);

-- Remove a manufacturer-product offer after manual confirmation; the product itself
-- remains in the assortment (Current-processes.md, purchasing).
SELECT 1 FROM LeveranciersAanbod
WHERE leverancier_id = 1 AND product_id = 1 FOR UPDATE;
DELETE FROM LeveranciersAanbod WHERE leverancier_id = 1 AND product_id = 1;
-- The SELECT and DELETE run in one transaction in ManufacturerRepository.remove_offer().

-- Persist a completed and explicitly calculated weekly invoice once.
-- This UPDATE may only run after the original order discounts are known.
-- The application checks that the snapshot has not previously been recorded.
SELECT factuur_id, totaal_bedrag FROM Factuur WHERE factuur_id=1 FOR UPDATE;
UPDATE Factuur SET
    bedrag_excl_btw=40.00, btw_bedrag=3.60, bedrag_incl_btw=43.60,
    bestellingskorting=0.00, bedrag_na_bestellingskorting=43.60,
    eenmalige_korting=4.36, bedrag_na_eenmalige_korting=39.24,
    klantenkorting=1.96, totaal_bedrag=37.28
WHERE factuur_id=1;
-- The amounts here illustrate the SQL shape, not any live customer's discount.

-- Registered picking bins for GET /order-picking
-- Same SELECT as PickingBinRepository.list_bins(); this version uses no parameters.
-- The bin location is the aisle of the robot that collects the sub-order.
SELECT v.unieke_code, v.deelorder_id, d.bestelling_id,
       d.robot_id, r.gang, d.afgerond
FROM Verzamelbak AS v
JOIN Deelorder AS d ON d.deelorder_id = v.deelorder_id
JOIN Robot AS r ON r.robot_id = d.robot_id
ORDER BY d.bestelling_id ASC, v.deelorder_id ASC, v.unieke_code ASC;

-- Registering a scanned picking bin, POST /api/picking-bins
-- Same statements as PickingBinRepository.register() with example values:
-- bin code 'VB-0001', sub-order 1, aisle 'A'.
-- Before the INSERT the application rejects a missing or completed sub-order,
-- an aisle other than r.gang, and a bin code that is already registered.
SELECT d.deelorder_id, d.bestelling_id, d.afgerond, r.gang
FROM Deelorder AS d
JOIN Robot AS r ON r.robot_id = d.robot_id
WHERE d.deelorder_id = 1
FOR UPDATE;
SELECT deelorder_id FROM Verzamelbak WHERE unieke_code = 'VB-0001';
INSERT INTO Verzamelbak (unieke_code, deelorder_id) VALUES ('VB-0001', 1);
-- The three statements are one transaction in the application.

-- BEGIN GENERATED WEEKLY INVOICE QUERIES
-- WeeklyInvoiceRepository.eligible_customers example 1
SELECT DISTINCT b.klant_id
                FROM Leveringregel lr
                JOIN Levering l ON l.levering_id=lr.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                WHERE lr.factuur_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM Leverpoging lp
                    JOIN Rit r ON r.rit_id=lp.rit_id
                    WHERE lp.levering_id=l.levering_id
                      AND lp.resultaat='afgeleverd'
                      AND lp.ontvangst_getekend=TRUE
                      AND r.ritdatum BETWEEN '2026-10-19' AND '2026-10-25'
                  )
                ORDER BY b.klant_id;

-- WeeklyInvoiceRepository._issue_customer example 1
SELECT k.bedrijfsnaam, a.adres AS factuuradres
                    FROM Klant k JOIN Adres a ON a.adres_id=k.betaaladres_id
                    WHERE k.klant_id=1 FOR UPDATE;

-- WeeklyInvoiceRepository._issue_customer example 2
SELECT factuur_id FROM Factuur
                    WHERE klant_id=1 AND week_start='2026-10-19' FOR UPDATE;

-- WeeklyInvoiceRepository._issue_customer example 3
SELECT lr.levering_id, lr.product_id, lr.aantal_geleverd AS quantity,
                           br.prijs_per_eenheid AS unit_price, b.bestelling_id AS order_id,
                           b.besteld_op, b.eenmalige_korting_toegepast AS first_used,
                           (SELECT SUM(ordered.aantal * ordered.prijs_per_eenheid)
                            FROM Bestelregel AS ordered
                            WHERE ordered.bestelling_id=b.bestelling_id) AS full_order_ex_vat
                    FROM Leveringregel lr
                    JOIN Levering l ON l.levering_id=lr.levering_id
                    JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                    JOIN Bestelregel br ON br.bestelling_id=b.bestelling_id
                                      AND br.product_id=lr.product_id
                    WHERE b.klant_id=1 AND lr.factuur_id IS NULL
                      AND EXISTS (
                        SELECT 1 FROM Leverpoging lp
                        JOIN Rit r ON r.rit_id=lp.rit_id
                        WHERE lp.levering_id=l.levering_id
                          AND lp.resultaat='afgeleverd'
                          AND lp.ontvangst_getekend=TRUE
                          AND r.ritdatum BETWEEN '2026-10-19' AND '2026-10-25'
                      )
                    ORDER BY b.besteld_op,b.bestelling_id,lr.levering_id,lr.product_id
                    FOR UPDATE;

-- WeeklyInvoiceRepository._issue_customer example 4
SELECT COUNT(*) AS paid_count,
                           COUNT(totaal_bedrag) AS known_amount_count,
                           COALESCE(SUM(totaal_bedrag),0) AS annual
                    FROM Factuur
                    WHERE klant_id=1 AND betaald_op >= '2025-01-01' AND betaald_op < '2026-01-01';

-- WeeklyInvoiceRepository._issue_customer example 5
SELECT bestelling_id FROM Bestelling WHERE klant_id=1
                    ORDER BY besteld_op,bestelling_id LIMIT 1;

-- WeeklyInvoiceRepository._issue_customer example 6
INSERT INTO Factuur
                    (klant_id,factuurdatum,week_start,afzenderadres,factuuradres)
                    VALUES (1,'2026-10-31','2026-10-19','Voorbeeldadres alleen voor test','Testapotheekstraat 1');

-- WeeklyInvoiceRepository._issue_customer example 7
UPDATE Leveringregel SET factuur_id=2
                        WHERE levering_id=2 AND product_id=1 AND factuur_id IS NULL;

-- WeeklyInvoiceRepository._issue_customer example 8
UPDATE Bestelling
                            SET eenmalige_korting_toegepast=TRUE
                            WHERE bestelling_id=2 AND eenmalige_korting_toegepast=FALSE;

-- WeeklyInvoiceRepository.issued_invoice example 1
SELECT f.*, k.bedrijfsnaam,
                       COALESCE(f.factuuradres,a.adres) AS adres
                FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id
                JOIN Adres a ON a.adres_id=k.betaaladres_id
                WHERE f.factuur_id=2;

-- WeeklyInvoiceRepository.issued_invoice example 2
SELECT lr.aantal_geleverd AS quantity,
                       br.prijs_per_eenheid AS unit_price, b.bestelling_id AS order_id
                FROM Leveringregel lr
                JOIN Levering l ON l.levering_id=lr.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                JOIN Bestelregel br ON br.bestelling_id=b.bestelling_id
                                  AND br.product_id=lr.product_id
                WHERE lr.factuur_id=2
                ORDER BY b.bestelling_id, lr.product_id;
-- END GENERATED WEEKLY INVOICE QUERIES

-- Ronde 4: actuele klantgegevens voor GET /customers, exact SalesCaseRepository.customers.
-- Voorbeeld invoer: naamdeel 'Apotheek'.
SELECT k.klant_id, k.bedrijfsnaam, k.telefoonnummer, k.contactpersoon,
       delivery.adres AS afleveradres, billing.adres AS factuuradres
FROM Klant AS k
JOIN Adres AS delivery ON delivery.adres_id=k.afleveradres_id
JOIN Adres AS billing ON billing.adres_id=k.betaaladres_id
WHERE ('Apotheek' = '' OR k.bedrijfsnaam LIKE '%Apotheek%')
ORDER BY k.bedrijfsnaam ASC, k.klant_id ASC;

-- Ronde 4: werkelijke bestelstatus voor GET /orders/status.
-- Voorbeeld: alle klanten zonder filter.
SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum,
       b.dagdeel, b.spoed, b.status_naam,
       k.klant_id, k.bedrijfsnaam, address.adres AS afleveradres
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id=b.klant_id
JOIN Adres AS address ON address.adres_id=b.afleveradres_id
WHERE (NULL IS NULL OR b.klant_id = NULL)
ORDER BY b.besteld_op DESC, b.bestelling_id DESC;
