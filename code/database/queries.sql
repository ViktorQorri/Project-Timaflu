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
UPDATE Deelorder SET afgerond = TRUE WHERE deelorder_id = 1;
