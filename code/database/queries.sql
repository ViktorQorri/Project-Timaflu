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
