-- Stock shortage dashboard, GET /stock
-- Keep this query in sync with StockRepository.list_stock_below_minimum().
-- This version uses no parameters; its result depends on current warehouse data.
SELECT p.product_id, p.artikelnummer, p.productnaam,
       p.minimumvoorraad,
       COALESCE(SUM(m.aantal), 0) AS voorraad
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
       l.contactpersoon, l.telefoonnummer, a.inkoopprijs
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
  AND p.in_assortiment = TRUE;
INSERT INTO Inkoopbestelling (leverancier_id, besteld_op, status_naam)
VALUES (1, CURRENT_TIMESTAMP, 'besteld');
INSERT INTO Inkoopbestelregel (inkoopbestelling_id, product_id, aantal)
VALUES (LAST_INSERT_ID(), 1, 10);
-- Both INSERT statements are one transaction in the application.

-- Recorded supplier orders, GET /reorder.
-- Mirrors PurchaseOrderRepository.list_recorded(); legacy unknown fields stay NULL.
SELECT i.inkoopbestelling_id, i.besteld_op, i.status_naam,
       l.naam AS leverancier, p.productnaam, r.aantal
FROM Inkoopbestelling AS i
JOIN Leverancier AS l ON l.leverancier_id = i.leverancier_id
JOIN Inkoopbestelregel AS r
  ON r.inkoopbestelling_id = i.inkoopbestelling_id
JOIN Product AS p ON p.product_id = r.product_id
ORDER BY i.besteld_op DESC, i.inkoopbestelling_id DESC, p.productnaam;

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

-- Acquisition follow-up overview, GET /acquisition
-- Show open prospects last visited at least one month ago and without an order.
SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
       p.contactgegevens, a.adres, MAX(v.bezoekdatum) AS laatste_bezoek
FROM PotentieleKlant AS p
JOIN Adres AS a ON a.adres_id = p.adres_id
JOIN Acquisitiebezoek AS v ON v.potentiele_klant_id = p.potentiele_klant_id
WHERE p.status = 'open'
  AND NOT EXISTS (
      SELECT 1 FROM Bestelling AS b WHERE b.klant_id = p.klant_id
  )
GROUP BY p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
         p.contactgegevens, a.adres
HAVING MAX(v.bezoekdatum) <= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
ORDER BY laatste_bezoek ASC, p.bedrijfsnaam ASC;

-- Register a prospect and the acquisition visit in one transaction.
INSERT INTO Adres (adres) VALUES ('Voorbeeldstraat 1, Utrecht');
INSERT INTO PotentieleKlant (bedrijfsnaam, contactpersoon, contactgegevens, adres_id, status)
VALUES ('Voorbeeld Apotheek', 'A. Contact', '030-1234567', 1, 'open');
INSERT INTO Acquisitiebezoek (potentiele_klant_id, bezoekdatum) VALUES (1, '2026-10-31');

-- Lock and check an acquisition follow-up before recording its outcome.
SELECT klant_id, status, bedrijfsnaam, contactpersoon
FROM PotentieleKlant WHERE potentiele_klant_id = 1 FOR UPDATE;
SELECT MAX(bezoekdatum) <= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) AS is_due
FROM Acquisitiebezoek WHERE potentiele_klant_id = 1;
SELECT bestelling_id FROM Bestelling WHERE klant_id = 1 LIMIT 1;

-- Close a follow-up when the pharmacy is not interested or does not consent.
UPDATE PotentieleKlant SET status = 'geen_interesse'
WHERE potentiele_klant_id = 1;
UPDATE PotentieleKlant SET status = 'geen_toestemming'
WHERE potentiele_klant_id = 1;

-- Convert an interested prospect into a customer and grant the one-time discount.
INSERT INTO Adres (adres) VALUES ('Afleverstraat 1, Utrecht');
INSERT INTO Adres (adres) VALUES ('Factuurstraat 1, Utrecht');
INSERT INTO Klant (bedrijfsnaam, telefoonnummer, contactpersoon, afleveradres_id,
                   betaaladres_id, eenmalige_korting_toegekend)
VALUES ('Voorbeeld Apotheek', '030-1234567', 'A. Contact', 2, 3, TRUE);
UPDATE PotentieleKlant
SET klant_id = 1, status = 'geconverteerd'
WHERE potentiele_klant_id = 1;

-- Distribution corner overview, GET /deliveries
-- Group registered collection bins by their customer order.
SELECT b.bestelling_id, b.status_naam, b.spoed, b.gewenste_leverdatum,
       b.dagdeel, b.aantal_verhuisdozen, k.bedrijfsnaam,
       af.adres AS afleveradres, d.deelorder_id, d.afgerond,
       v.unieke_code, r.gang
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
JOIN Adres AS af ON af.adres_id = b.afleveradres_id
JOIN Deelorder AS d ON d.bestelling_id = b.bestelling_id
LEFT JOIN Verzamelbak AS v ON v.deelorder_id = d.deelorder_id
LEFT JOIN Robot AS r ON r.robot_id = d.robot_id
WHERE (b.status_naam IS NULL OR b.status_naam NOT IN ('verstuurd', 'afgeleverd'))
  AND EXISTS (
      SELECT 1 FROM Deelorder AS d2
      JOIN Verzamelbak AS v2 ON v2.deelorder_id = d2.deelorder_id
      WHERE d2.bestelling_id = b.bestelling_id
  )
ORDER BY b.bestelling_id DESC, d.deelorder_id ASC, v.unieke_code ASC;

-- Product lines shown while packing one customer order.
SELECT p.artikelnummer, p.productnaam, br.aantal, br.afnemen_bij_tekort
FROM Bestelregel AS br
JOIN Product AS p ON p.product_id = br.product_id
WHERE br.bestelling_id = 1
ORDER BY p.productnaam ASC;

-- Register packing after all sub-orders of the order have been completed.
SELECT bestelling_id, status_naam
FROM Bestelling WHERE bestelling_id = 1 FOR UPDATE;
SELECT deelorder_id, afgerond
FROM Deelorder WHERE bestelling_id = 1 FOR UPDATE;
SELECT v.unieke_code
FROM Verzamelbak AS v
JOIN Deelorder AS d ON d.deelorder_id = v.deelorder_id
WHERE d.bestelling_id = 1 LIMIT 1;
UPDATE Bestelling
SET aantal_verhuisdozen = 2, status_naam = 'ingepakt'
WHERE bestelling_id = 1;

-- Release a packed order for distribution.
SELECT status_naam, aantal_verhuisdozen
FROM Bestelling WHERE bestelling_id = 1 FOR UPDATE;
UPDATE Bestelling SET status_naam = 'verstuurd'
WHERE bestelling_id = 1;
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
                             WHERE lp.levering_id=1 AND r.ritdatum='2026-10-30'
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
FROM Product WHERE in_assortiment = TRUE ORDER BY productnaam, product_id;

SELECT a.product_id, p.productnaam, a.inkoopprijs
FROM LeveranciersAanbod AS a
JOIN Product AS p ON p.product_id = a.product_id
WHERE a.leverancier_id = 1 AND p.in_assortiment = TRUE
ORDER BY p.productnaam, a.product_id;

-- One transaction: validate manufacturer and product before upserting purchase price.
SELECT 1 FROM Leverancier WHERE leverancier_id = 1;
SELECT 1 FROM Product WHERE product_id = 1 AND in_assortiment = TRUE;
INSERT INTO LeveranciersAanbod (leverancier_id, product_id, inkoopprijs)
VALUES (1, 1, 12.50)
ON DUPLICATE KEY UPDATE inkoopprijs = VALUES(inkoopprijs);

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
-- =========================================
-- Manage customers (issue #8, AD07), /customers
-- Same queries as CustomerRepository, with example values instead of %s.
-- =========================================

-- Customer overview, GET /customers?q=...
-- Same SELECT as CustomerRepository.list_customers() with example parameters:
-- year 2026 (revenue and discount) and search 'Apotheek' (backend uses '%Apotheek%').
-- An empty search uses '%%' and returns every customer.
-- Annual revenue = persisted net totals from paid invoices; unknown if any total is missing.
SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
       af.adres AS afleveradres, ba.adres AS factuuradres,
       CASE
           WHEN o.paid_count IS NULL THEN 0
           WHEN o.paid_count = o.known_amount_count THEN o.jaaromzet
           ELSE NULL
       END AS jaaromzet,
       kk.percentage AS kortingspercentage
FROM Klant AS k
JOIN Adres AS af ON af.adres_id = k.afleveradres_id
JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
LEFT JOIN (
    SELECT f.klant_id,
           COUNT(*) AS paid_count,
           COUNT(f.totaal_bedrag) AS known_amount_count,
           SUM(f.totaal_bedrag) AS jaaromzet
    FROM Factuur AS f
    WHERE YEAR(f.betaald_op) = 2026
    GROUP BY f.klant_id
) AS o ON o.klant_id = k.klant_id
LEFT JOIN Klantkorting AS kk ON kk.klant_id = k.klant_id
                            AND kk.kalenderjaar = 2026
WHERE k.bedrijfsnaam LIKE '%Apotheek%' OR k.contactpersoon LIKE '%Apotheek%'
   OR k.telefoonnummer LIKE '%Apotheek%'
ORDER BY k.bedrijfsnaam ASC, k.klant_id ASC;

-- One customer for the edit and delete screens, GET /customers/1/edit and /customers/1/delete
-- Same SELECT as CustomerRepository.find_customer().
SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
       af.adres AS afleveradres, ba.adres AS factuuradres
FROM Klant AS k
JOIN Adres AS af ON af.adres_id = k.afleveradres_id
JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
WHERE k.klant_id = 1;

-- Create a customer, POST /customers
-- Same statements as CustomerRepository.create(), in one transaction.
-- 101 and 102 stand for the adres_id values returned by the two Adres inserts.
INSERT INTO Adres (adres) VALUES ('Markt 1, 4811 AA Breda');
INSERT INTO Adres (adres) VALUES ('Postbus 10, 4800 AA Breda');
INSERT INTO Klant (bedrijfsnaam, telefoonnummer, contactpersoon,
                   afleveradres_id, betaaladres_id)
VALUES ('Apotheek De Markt', '076 123 45 67', 'J. Jansen', 101, 102);

-- Edit a customer, POST /customers/1/edit
-- Same statements as CustomerRepository.update(), in one transaction.
-- The SELECT locks the customer and returns the current addresses. Only a changed
-- address gets a new Adres row (here the delivery address, new adres_id 103),
-- so existing orders keep the address they were placed with.
SELECT k.afleveradres_id, af.adres AS afleveradres,
       k.betaaladres_id, ba.adres AS factuuradres
FROM Klant AS k
JOIN Adres AS af ON af.adres_id = k.afleveradres_id
JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
WHERE k.klant_id = 1
FOR UPDATE;
INSERT INTO Adres (adres) VALUES ('Markt 2, 4811 AA Breda');
UPDATE Klant
SET bedrijfsnaam = 'Apotheek De Markt', telefoonnummer = '076 123 45 67', contactpersoon = 'J. Jansen',
    afleveradres_id = 103, betaaladres_id = 102
WHERE klant_id = 1;

-- Delete a customer, POST /customers/1/delete
-- Same statements as CustomerRepository.delete(), in one transaction.
-- The DELETE statements only run when all three counts are 0.
SELECT klant_id FROM Klant WHERE klant_id = 1 FOR UPDATE;
SELECT (SELECT COUNT(*) FROM Bestelling WHERE klant_id = 1) AS bestellingen,
       (SELECT COUNT(*) FROM Factuur WHERE klant_id = 1) AS facturen,
       (SELECT COUNT(*) FROM PotentieleKlant WHERE klant_id = 1) AS acquisities;
DELETE FROM Klantkorting WHERE klant_id = 1;
DELETE FROM Klant WHERE klant_id = 1;
-- Order discount calculation on the new order screen, /orders/new (issue #10, SD01).
-- Same SELECTs as DiscountRepository with example parameters.
-- Customer and product choices for the form.
SELECT klant_id, bedrijfsnaam
FROM Klant
ORDER BY bedrijfsnaam ASC;
SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking
FROM Product
WHERE in_assortiment = TRUE
ORDER BY productnaam ASC;
-- The chosen customer and the catalog price of each order line.
SELECT klant_id, bedrijfsnaam
FROM Klant
WHERE klant_id = 1;
SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking
FROM Product
WHERE product_id = 1 AND in_assortiment = TRUE;
-- SD01 countPreviousOrders(customer): 0 means first order, 10% one-time discount.
SELECT COUNT(*) AS aantal_bestellingen
FROM Bestelling
WHERE klant_id = 1;
-- SD01 sumPurchases(previousYear): persisted net paid invoice totals for Tabel 1.
-- Missing historical totals are detected rather than treated as zero.
SELECT COUNT(*) AS paid_count,
       COUNT(f.totaal_bedrag) AS known_amount_count,
       COALESCE(SUM(f.totaal_bedrag), 0) AS jaaromzet
FROM Factuur AS f
WHERE f.klant_id = 1
  AND f.betaald_op >= '2025-01-01'
  AND f.betaald_op < '2026-01-01';

-- Enter a telephone order, /orders/new (issues #9 and #10, AD05 Enter order).
-- Same queries as OrderRepository with example parameters.
-- A customer whose unpaid invoice is with the debt collection agency cannot order.
SELECT COUNT(*) AS aantal_facturen
FROM Factuur
WHERE klant_id = 1 AND betaald_op IS NULL AND incasso_ingeschakeld = TRUE;
-- Available stock of one product: physical stock minus reservations.
SELECT GREATEST(
    COALESCE((SELECT SUM(aantal) FROM Magazijnlocatie WHERE product_id = 1), 0)
    - COALESCE((SELECT SUM(aantal) FROM Voorraadreservering WHERE product_id = 1), 0),
    0) AS beschikbaar;
-- Saving the order, run as one transaction. Lock the customer and read its addresses.
SELECT klant_id, afleveradres_id, betaaladres_id
FROM Klant
WHERE klant_id = 1
FOR UPDATE;
-- First order: no earlier orders (same query as countPreviousOrders above).
SELECT COUNT(*) AS aantal_bestellingen
FROM Bestelling
WHERE klant_id = 1;
-- Per product, in product order: lock it, read the price, then count the available stock again.
SELECT product_id, prijs_per_grootverpakking
FROM Product
WHERE product_id = 1 AND in_assortiment = TRUE
FOR UPDATE;
INSERT INTO Bestelling (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                        gewenste_leverdatum, dagdeel, spoed, status_naam,
                        eenmalige_korting_toegepast)
VALUES (1, 1, 2, NOW(), '2026-11-02', 'ochtend', FALSE, NULL, FALSE);
INSERT INTO Bestelregel (bestelling_id, product_id, aantal, prijs_per_eenheid,
                         afnemen_bij_tekort)
VALUES (15, 1, 20, 45.00, NULL);
-- Only for lines with enough stock; a short line is saved with afnemen_bij_tekort = TRUE.
INSERT INTO Voorraadreservering (bestelling_id, product_id, aantal)
VALUES (15, 1, 20);
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
-- Issue #16: robot order dispatch for an existing aisle-specific sub-order.
-- Orders waiting to be split, shown on the order-picking screen.
SELECT b.bestelling_id, k.bedrijfsnaam, b.gewenste_leverdatum,
       b.dagdeel, b.spoed
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
WHERE b.status_naam IN ('nieuw', 'wordt verzameld')
  AND EXISTS (
      SELECT 1 FROM Voorraadreservering AS vr
      WHERE vr.bestelling_id = b.bestelling_id
  )
  AND NOT EXISTS (
      SELECT 1 FROM Deelorder AS d
      WHERE d.bestelling_id = b.bestelling_id
  )
ORDER BY b.spoed DESC, b.gewenste_leverdatum ASC, b.bestelling_id ASC;

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
SELECT bestelling_id, status_naam
FROM Bestelling WHERE bestelling_id = 1 FOR UPDATE;
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
UPDATE Bestelling SET status_naam = 'wordt verzameld'
WHERE bestelling_id = 1;
-- Remove a manufacturer-product offer after manual confirmation; the product itself
-- remains in the assortment (Current-processes.md, purchasing).
SELECT 1 FROM LeveranciersAanbod
WHERE leverancier_id = 1 AND product_id = 1 FOR UPDATE;
DELETE FROM LeveranciersAanbod WHERE leverancier_id = 1 AND product_id = 1;
-- The SELECT and DELETE run in one transaction in ManufacturerRepository.remove_offer().

-- Issue #27: order status report, GET /reports.
-- Optional date bounds are inclusive; the end date includes the whole day.
SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
       b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam,
       COUNT(r.product_id) AS aantal_regels
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
LEFT JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
WHERE ('2026-10-01' IS NULL OR b.besteld_op >= '2026-10-01')
  AND ('2026-10-31' IS NULL OR b.besteld_op < '2026-10-31' + INTERVAL 1 DAY)
GROUP BY b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
         b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam
ORDER BY b.besteld_op DESC, b.bestelling_id DESC;

-- Issue #29: find orders for the sales employee to inform the customer.
SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
       b.gewenste_leverdatum, b.dagdeel, b.status_naam
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
WHERE b.bestelling_id = 15 OR k.bedrijfsnaam LIKE '%Apotheek%'
ORDER BY b.besteld_op DESC, b.bestelling_id DESC;

SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum, b.dagdeel,
       b.status_naam, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
       l.afgeleverd_op
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
LEFT JOIN (
    SELECT lv.bestelling_id, MAX(r.ritdatum) AS afgeleverd_op
    FROM Levering AS lv
    JOIN Leverpoging AS lp ON lp.levering_id = lv.levering_id
    JOIN Rit AS r ON r.rit_id = lp.rit_id
    WHERE lp.resultaat = 'afgeleverd'
    GROUP BY lv.bestelling_id
) AS l ON l.bestelling_id = b.bestelling_id
WHERE b.bestelling_id = 15;

SELECT p.product_id, p.artikelnummer, p.productnaam, br.aantal,
       COALESCE(vr.aantal, 0) AS gereserveerd
FROM Bestelregel AS br
JOIN Product AS p ON p.product_id = br.product_id
LEFT JOIN Voorraadreservering AS vr
       ON vr.bestelling_id = br.bestelling_id
      AND vr.product_id = br.product_id
WHERE br.bestelling_id = 15
ORDER BY p.productnaam ASC;
