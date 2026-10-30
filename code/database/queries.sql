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
