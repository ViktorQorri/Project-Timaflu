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

-- =========================================
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
