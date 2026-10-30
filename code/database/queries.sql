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
