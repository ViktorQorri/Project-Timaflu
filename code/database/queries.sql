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

-- =============
-- Manage customers (issue #8, AD07), /customers
-- Same queries as CustomerRepository, with example values instead of %s.
-- =========================================

-- Customer overview, GET /customers?q=...
-- Same SELECT as CustomerRepository.list_customers() with example parameters:
-- year 2026 (revenue and discount) and search 'Apotheek' (backend uses '%Apotheek%').
-- An empty search uses '%%' and returns every customer.
-- Annual revenue = delivered lines on invoices paid in that year; it is not stored.
SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
       af.adres AS afleveradres, ba.adres AS factuuradres,
       COALESCE(o.jaaromzet, 0) AS jaaromzet,
       kk.percentage AS kortingspercentage
FROM Klant AS k
JOIN Adres AS af ON af.adres_id = k.afleveradres_id
JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
LEFT JOIN (
    SELECT f.klant_id,
           SUM(lr.aantal_geleverd * br.prijs_per_eenheid) AS jaaromzet
    FROM Factuur AS f
    JOIN Leveringregel AS lr ON lr.factuur_id = f.factuur_id
    JOIN Levering AS l ON l.levering_id = lr.levering_id
    JOIN Bestelregel AS br ON br.bestelling_id = l.bestelling_id
                          AND br.product_id = lr.product_id
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
=======
-- Order discount calculation on the new order screen, /orders/new (issue #10, SD01).
-- Same SELECTs as DiscountRepository with example parameters.
-- Customer and product choices for the form.
SELECT klant_id, bedrijfsnaam
FROM Klant
ORDER BY bedrijfsnaam ASC;
SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking
FROM Product
ORDER BY productnaam ASC;
-- The chosen customer and the catalog price of each order line.
SELECT klant_id, bedrijfsnaam
FROM Klant
WHERE klant_id = 1;
SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking
FROM Product
WHERE product_id = 1;
-- SD01 countPreviousOrders(customer): 0 means first order, 10% one-time discount.
SELECT COUNT(*) AS aantal_bestellingen
FROM Bestelling
WHERE klant_id = 1;
-- SD01 sumPurchases(previousYear): annual revenue for the customer discount (Tabel 1).
SELECT COALESCE(SUM(r.aantal * r.prijs_per_eenheid), 0) AS jaaromzet
FROM Bestelling AS b
JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
WHERE b.klant_id = 1 AND YEAR(b.besteld_op) = 2025;

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
WHERE product_id = 1
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
=======
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
=======
-- Order status report for management, GET /reports?from=...&to=...
-- Same SELECT as OrderStatusReportRepository.list_orders() with example parameters.
-- Example period 2026-10-01 up to and including 2026-10-31; the app passes NULL
-- instead of a date when that side of the period is left empty.
-- The service groups the rows: 'backorder', 'afgeleverd', and every other status as open.
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
=======
-- Order status lookup for informing the customer, GET /orders?order=...
-- Same SELECT as OrderStatusNotificationRepository.search_orders() with example parameters.
-- Search term '1': the backend passes the order number only when the term is a number,
-- otherwise NULL, and uses LIKE %s with value '%1%' for the customer name.
SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
       b.gewenste_leverdatum, b.dagdeel, b.status_naam
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
WHERE b.bestelling_id = 1 OR k.bedrijfsnaam LIKE '%1%'
ORDER BY b.besteld_op DESC, b.bestelling_id DESC;

-- Order status of one order, GET /orders/1/status
-- Same SELECT as OrderStatusNotificationRepository.find_order() with example order 1.
-- afgeleverd_op is the trip date of the successful delivery attempt.
SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum, b.dagdeel,
       b.status_naam, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
       a.adres AS afleveradres, l.afgeleverd_op
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
JOIN Adres AS a ON a.adres_id = b.afleveradres_id
LEFT JOIN (
    SELECT lv.bestelling_id, MAX(r.ritdatum) AS afgeleverd_op
    FROM Levering AS lv
    JOIN Leverpoging AS lp ON lp.levering_id = lv.levering_id
    JOIN Rit AS r ON r.rit_id = lp.rit_id
    WHERE lp.resultaat = 'afgeleverd'
    GROUP BY lv.bestelling_id
) AS l ON l.bestelling_id = b.bestelling_id
WHERE b.bestelling_id = 1;

-- Order lines with reserved stock for the same screen, GET /orders/1/status
-- Same SELECT as OrderStatusNotificationRepository.find_order_lines() with example order 1.
-- For an order with status 'backorder', the backorder quantity is aantal - gereserveerd.
SELECT p.product_id, p.artikelnummer, p.productnaam, br.aantal,
       COALESCE(vr.aantal, 0) AS gereserveerd
FROM Bestelregel AS br
JOIN Product AS p ON p.product_id = br.product_id
LEFT JOIN Voorraadreservering AS vr
       ON vr.bestelling_id = br.bestelling_id
      AND vr.product_id = br.product_id
WHERE br.bestelling_id = 1
ORDER BY p.productnaam ASC;
