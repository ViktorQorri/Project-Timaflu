# Werkelijke MySQL-queryuitvoer voor de vijf verplichte scenario's

Dit is **daadwerkelijke uitvoer van een geïsoleerde MySQL 8.4-testdatabase**, gevuld
met fictieve fixturegegevens. Er zijn geen productiegegevens gebruikt.

- Schema: `code/database/schema.sql` uit PR #94
- Fixture: [fixtures_assessed.sql](test-data/fixtures_assessed.sql)
- Uitgevoerde SELECTs: [selects_assessed.sql](test-data/selects_assessed.sql)
- Testdatum: 31 oktober 2026
- Scenario's: verkoop, inkoop, administratie, distributie en acquisitie

De uitgevoerde SELECTs gebruiken dezelfde kolommen, filters en sortering als de
relevante repository-methoden. Dit is **geen bewijs** dat alle transacties van de
applicatie volledig werken, en deze uitvoer bevat **geen verzonnen resultaten**.

## Vastgelegde uitvoer

```text
+----------------------------+
| proces                     |
+----------------------------+
| 01. Verkoop: klantgegevens |
+----------------------------+
+----------+--------------------+
| klant_id | bedrijfsnaam       |
+----------+--------------------+
|        1 | Testapotheek Breda |
+----------+--------------------+
+---------------------------------------------------------+
| proces                                                  |
+---------------------------------------------------------+
| 01. Verkoop: betaalde jaaromzet 2025, bruto regelbedrag |
+---------------------------------------------------------+
+--------+
| annual |
+--------+
|  40.00 |
+--------+
+------------------------------------------------+
| proces                                         |
+------------------------------------------------+
| 02. Inkoop: leveranciers op prijs gerangschikt |
+------------------------------------------------+
+------------+--------------+----------------+-------------+----------------+----------------+-------------+
| product_id | productnaam  | leverancier_id | leverancier | contactpersoon | telefoonnummer | inkoopprijs |
+------------+--------------+----------------+-------------+----------------+----------------+-------------+
|          1 | Testmedicijn |              2 | Fabrikant B | Contact B      | 0622222222     |       12.00 |
|          1 | Testmedicijn |              1 | Fabrikant A | Contact A      | 0611111111     |       15.00 |
+------------+--------------+----------------+-------------+----------------+----------------+-------------+
+-----------------------------------------+
| proces                                  |
+-----------------------------------------+
| 03. Administratie: factuurkop en status |
+-----------------------------------------+
+------------+--------------+------------+--------------------+-----------------------------+
| factuur_id | factuurdatum | betaald_op | bedrijfsnaam       | adres                       |
+------------+--------------+------------+--------------------+-----------------------------+
|          1 | 2025-09-05   | 2025-10-10 | Testapotheek Breda | Testapotheekstraat 1, Breda |
+------------+--------------+------------+--------------------+-----------------------------+
+------------------------------------------------------+
| proces                                               |
+------------------------------------------------------+
| 03. Administratie: werkelijk geleverde factuurregels |
+------------------------------------------------------+
+----------+------------+
| quantity | unit_price |
+----------+------------+
|        2 |      20.00 |
+----------+------------+
+------------------------------------------+
| proces                                   |
+------------------------------------------+
| 04. Distributie: rooster voor 31 oktober |
+------------------------------------------+
+-------------+--------------+---------------+-----------+---------------+--------------------+----------------+----------------+-----------------------------+------------+
| levering_id | pogingnummer | geplande_tijd | resultaat | bestelling_id | bedrijfsnaam       | contactpersoon | telefoonnummer | adres                       | ritdatum   |
+-------------+--------------+---------------+-----------+---------------+--------------------+----------------+----------------+-----------------------------+------------+
|           1 |            1 | 10:00:00      | NULL      |             1 | Testapotheek Breda | Testcontact    | 0612345678     | Testapotheekstraat 1, Breda | 2026-10-31 |
+-------------+--------------+---------------+-----------+---------------+--------------------+----------------+----------------+-----------------------------+------------+
+------------------------------------------------------------+
| proces                                                     |
+------------------------------------------------------------+
| 05. Acquisitie: nog geen order, bezoek ouder dan een maand |
+------------------------------------------------------------+
+---------------------+--------------------------+-----------------+-----------------+-------------------------+-------------+
| potentiele_klant_id | bedrijfsnaam             | contactpersoon  | contactgegevens | adres                   | bezoekdatum |
+---------------------+--------------------------+-----------------+-----------------+-------------------------+-------------+
|                   1 | Prospectapotheek Tilburg | Prospectcontact | 0633333333      | Prospectlaan 3, Tilburg | 2026-09-15  |
+---------------------+--------------------------+-----------------+-----------------+-------------------------+-------------+
```

## Nog open voor de eindoplevering

- De huidige jaaromzetquery telt bruto geleverde regels van betaalde facturen;
  zonder opgeslagen kortingsbedragen is dit niet aantoonbaar de netto betaalde omzet.
- `AssessedRepository.invoice_for_customer()` haalt echte geleverde regels op,
  maar het historisch toegepaste kortingsbedrag is nog niet in `Factuur` vastgelegd.
  De hier getoonde factuurregels mogen daarom niet als een gevalideerd definitief
  factuurtotaal worden gepresenteerd.
- Volgens `AGENTS.md` is er een bronconflict: `SupplierRepository.find_offers()`
  vereist `p.intern_bestelbaar = TRUE`, maar de overeenkomstige voorbeeldquery
  in `queries.sql` mist deze voorwaarde. De leidende versie moet worden bevestigd
  voordat dit definitief wordt gesynchroniseerd.
- De uitvoer van alle overige schermquery's moet eveneens op de uiteindelijke
  samengestelde database worden vastgelegd.
