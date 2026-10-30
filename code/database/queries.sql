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
WHERE p.productnaam LIKE '%Medication%' AND p.in_assortiment = TRUE
ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC;

-- Recording a purchasing order after the employee has contacted the manufacturer.
-- The supplier-product relationship is validated by PurchaseOrderRepository.
SELECT 1 FROM LeveranciersAanbod AS a
JOIN Product AS p ON p.product_id = a.product_id
WHERE a.leverancier_id = 1 AND a.product_id = 1
  AND p.in_assortiment = TRUE;
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
