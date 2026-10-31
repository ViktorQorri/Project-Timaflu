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
