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
