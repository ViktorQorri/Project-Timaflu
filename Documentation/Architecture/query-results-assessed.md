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
+--------------------------------------------+
| proces                                     |
+--------------------------------------------+
| 01. Verkoop: netto betaalde jaaromzet 2025 |
+--------------------------------------------+
+------------+--------------------+--------+
| paid_count | known_amount_count | annual |
+------------+--------------------+--------+
|          1 |                  1 |  37.28 |
+------------+--------------------+--------+
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
+------------+--------------+------------+-----------------+------------+-----------------+--------------------+------------------------------+-------------------+-----------------------------+----------------+---------------+--------------------+-----------------------------+
| factuur_id | factuurdatum | betaald_op | bedrag_excl_btw | btw_bedrag | bedrag_incl_btw | bestellingskorting | bedrag_na_bestellingskorting | eenmalige_korting | bedrag_na_eenmalige_korting | klantenkorting | totaal_bedrag | bedrijfsnaam       | adres                       |
+------------+--------------+------------+-----------------+------------+-----------------+--------------------+------------------------------+-------------------+-----------------------------+----------------+---------------+--------------------+-----------------------------+
|          1 | 2025-09-05   | 2025-10-10 |           40.00 |       3.60 |           43.60 |               0.00 |                        43.60 |              4.36 |                       39.24 |           1.96 |         37.28 | Testapotheek Breda | Testapotheekstraat 1, Breda |
+------------+--------------+------------+-----------------+------------+-----------------+--------------------+------------------------------+-------------------+-----------------------------+----------------+---------------+--------------------+-----------------------------+
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

- De jaaromzetquery telt het historisch vastgelegde **netto betaalde** factuurtotaal.
  Als een betaalde legacy-factuur geen snapshot heeft, weigert de backend een betrouwbare jaaromzet te verzinnen.
- `AssessedRepository.invoice_for_customer()` haalt echte geleverde regels op,
  en leest de eenmaal vastgelegde bedragen uit `Factuur`.
  Onbekende bedragen van oudere facturen blijven expliciet onbekend en worden niet stilzwijgend herberekend.
- `SupplierRepository.find_offers()` en `queries.sql` hanteren beide
  `intern_bestelbaar = TRUE` én `in_assortiment = TRUE`: de interne inkooplijst
  is een andere productstatus dan de verkoopcatalogus. Dit volgt de casus.
- De uitvoer van alle overige schermquery's moet eveneens op de uiteindelijke
  samengestelde database worden vastgelegd.
