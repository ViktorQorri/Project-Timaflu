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

-- Sales reports for management, GET /reports/sales?start=...&end=...&grouping=...
-- Keep these queries in sync with SalesReportRepository.
-- Example period 2026-01-01 up to and including 2026-12-31: the backend passes
-- the day after the last day as the (excluded) end date.
-- Revenue = aantal * prijs_per_eenheid of the order lines, excluding VAT and discounts.

-- Revenue per customer, SalesReportRepository.revenue_per_customer().
SELECT k.klant_id, k.bedrijfsnaam,
       COUNT(DISTINCT b.bestelling_id) AS aantal_bestellingen,
       SUM(r.aantal * r.prijs_per_eenheid) AS omzet
FROM Bestelling AS b
JOIN Klant AS k ON k.klant_id = b.klant_id
JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
WHERE b.besteld_op >= '2026-01-01' AND b.besteld_op < '2027-01-01'
GROUP BY k.klant_id, k.bedrijfsnaam
ORDER BY omzet DESC, k.bedrijfsnaam ASC;

-- Revenue per period, SalesReportRepository.revenue_per_period().
-- Example grouping per month '%Y-%m'; the backend also uses '%Y-%m-%d' (day),
-- '%x-W%v' (ISO week) and '%Y' (year).
SELECT DATE_FORMAT(b.besteld_op, '%Y-%m') AS periode,
       COUNT(DISTINCT b.bestelling_id) AS aantal_bestellingen,
       SUM(r.aantal * r.prijs_per_eenheid) AS omzet
FROM Bestelling AS b
JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
WHERE b.besteld_op >= '2026-01-01' AND b.besteld_op < '2027-01-01'
GROUP BY periode
ORDER BY periode ASC;

-- Best-selling medicines, SalesReportRepository.best_selling_products().
SELECT p.product_id, p.artikelnummer, p.productnaam,
       SUM(r.aantal) AS aantal_verkocht,
       SUM(r.aantal * r.prijs_per_eenheid) AS omzet
FROM Bestelregel AS r
JOIN Bestelling AS b ON b.bestelling_id = r.bestelling_id
JOIN Product AS p ON p.product_id = r.product_id
WHERE b.besteld_op >= '2026-01-01' AND b.besteld_op < '2027-01-01'
GROUP BY p.product_id, p.artikelnummer, p.productnaam
ORDER BY aantal_verkocht DESC, omzet DESC, p.productnaam ASC
LIMIT 10;
