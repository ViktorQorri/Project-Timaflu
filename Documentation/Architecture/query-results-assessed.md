# Werkelijke MySQL-queryuitvoer voor de vijf verplichte scenario's

Dit is **werkelijk uitgevoerde query-output** van een geïsoleerde MySQL 8.4.13-testdatabase, gevuld met uitsluitend fictieve fixturegegevens. Er zijn geen klant- of productiegegevens gebruikt.

- Schema: `code/database/schema.sql`.
- Fixture: [fixtures_assessed.sql](test-data/fixtures_assessed.sql).
- Uitgevoerde SELECTs: [selects_assessed.sql](test-data/selects_assessed.sql).
- Ruwe, automatisch vastgelegde uitvoer: [mysql84_output_verified.txt](test-data/mysql84_output_verified.txt).
- Verificatiedatum: 31 oktober 2026.
- Scenario's: verkoop, inkoop, administratie, distributie en acquisitie.

De fixture bevat een **openstaande factuur** en een afzonderlijke betaalde factuur uit het voorgaande kalenderjaar. De query-output toont de openstaande factuur en de omzet van de betaalde factuur. De acquisitiequery gebruikt `NOT EXISTS` op `Bestelling`, zodat een bestaand account zonder bestelling niet uit de opvolglijst verdwijnt.

## Uitvoer

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
|          2 | 2026-10-31   | NULL       |           20.00 |       1.80 |           21.80 |               0.00 |                        21.80 |              0.00 |                       21.80 |           1.09 |         20.71 | Testapotheek Breda | Testapotheekstraat 1, Breda |
+------------+--------------+------------+-----------------+------------+-----------------+--------------------+------------------------------+-------------------+-----------------------------+----------------+---------------+--------------------+-----------------------------+
+------------------------------------------------------+
| proces                                               |
+------------------------------------------------------+
| 03. Administratie: werkelijk geleverde factuurregels |
+------------------------------------------------------+
+----------+------------+
| quantity | unit_price |
+----------+------------+
|        1 |      20.00 |
+----------+------------+
+------------------------------------------+
| proces                                   |
+------------------------------------------+
| 04. Distributie: rooster voor 31 oktober |
+------------------------------------------+
+-------------+--------------+---------------+-----------+---------------+--------------------+----------------+----------------+-----------------------------+------------+
| levering_id | pogingnummer | geplande_tijd | resultaat | bestelling_id | bedrijfsnaam       | contactpersoon | telefoonnummer | adres                       | ritdatum   |
+-------------+--------------+---------------+-----------+---------------+--------------------+----------------+----------------+-----------------------------+------------+
|           3 |            1 | 10:00:00      | NULL      |             3 | Testapotheek Breda | Testcontact    | 0612345678     | Testapotheekstraat 1, Breda | 2026-10-31 |
+-------------+--------------+---------------+-----------+---------------+--------------------+----------------+----------------+-----------------------------+------------+
+------------------------------------------------------------+
| proces                                                     |
+------------------------------------------------------------+
| 05. Acquisitie: nog geen order, bezoek ouder dan een maand |
+------------------------------------------------------------+
+---------------------+--------------------------+-------------------+-----------------+------------------------------------+----------+-------------+
| potentiele_klant_id | bedrijfsnaam             | contactpersoon    | contactgegevens | adres                              | klant_id | bezoekdatum |
+---------------------+--------------------------+-------------------+-----------------+------------------------------------+----------+-------------+
|                   2 | Testapotheek Eindhoven   | Contact Eindhoven | 0644444444      | Nieuwe apotheekstraat 4, Eindhoven |        2 | 2026-08-15  |
|                   1 | Prospectapotheek Tilburg | Prospectcontact   | 0633333333      | Prospectlaan 3, Tilburg            |     NULL | 2026-09-15  |
+---------------------+--------------------------+-------------------+-----------------+------------------------------------+----------+-------------+
```

## Bezorgpoging in twee aparte transacties

- [Uitgevoerde SQL](test-data/delivery_two_stage_assessed.sql) en [werkelijke MySQL-uitvoer](test-data/delivery_two_stage_output.txt).
- Na de eerste afwezigheid staat poging 2 om 14:00 uur ingepland met resultaat `NULL`.
- Pas bij het afzonderlijk vastleggen van de tweede uitkomst verandert poging 2 naar `afgeleverd`, met expliciet bevestigde ontvangst en aangepaste bestelstatus.
- De applicatie verifieert de handtekeningbevestiging, niet een ingescande of cryptografisch opgeslagen handtekening.

## Afbakening en resterende opleverpunten

- Dit bewijst de **SELECT-uitvoer voor de vijf getoonde scenario's**, niet automatisch alle andere schermqueries, HTTP-routes of transacties van het hele informatiesysteem.
- De factuuruitvoer is afkomstig van vooraf vastgelegde bedragen en werkelijk geleverde regels. Oudere facturen zonder opgeslagen kortingen of totaalbedragen mogen niet met aannames worden gereconstrueerd.
- Voor de definitieve factuurlay-out moet het **werkelijke afzenderadres van Timaflu** uit een betrouwbare bron worden ingevuld. De casus levert dit adres niet.
- Voor de totale eindoplevering moeten de samengevoegde EER, online database, screenshots en query-output per scherm, de use-cases, en de integratie met overige proces-PR's nog als geheel worden gevalideerd.
