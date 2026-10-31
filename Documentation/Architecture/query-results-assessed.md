# Gemeten MySQL-queryresultaten voor de vijf verplichte scenario's

Testdatum: 31 oktober 2026. Gecontroleerde codecommit: 997f7333af17c81be8196be59c5b0a41957bfb90

Bronnen: code/database/schema.sql, Documentation/Architecture/test-data/fixtures_assessed.sql en selects_assessed.sql.

Deze tabellen zijn door MySQL 8.4 teruggegeven voor fictieve gegevens in een nieuw gemaakte en na afloop verwijderde lokale testdatabase.
Het uitvoerbare bewijs staat in run_caseproof_mysql.py; hiermee zijn ook de vijf bijbehorende Flask-pagina's met echte MySQL-verbindingen getest.

### 01. Verkoop: klantgegevens
| klant_id | bedrijfsnaam |
| --- | --- |
| 1 | Testapotheek Breda |

### 01. Verkoop: netto betaalde jaaromzet 2025
| paid_count | known_amount_count | annual |
| --- | --- | --- |
| 1 | 1 | 37.28 |

### 02. Inkoop: leveranciers op prijs gerangschikt
| product_id | productnaam | leverancier_id | leverancier | contactpersoon | telefoonnummer | inkoopprijs |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Testmedicijn | 2 | Fabrikant B | Contact B | 0622222222 | 12.00 |
| 1 | Testmedicijn | 1 | Fabrikant A | Contact A | 0611111111 | 15.00 |

### 03. Administratie: factuurkop en status
| factuur_id | factuurdatum | betaald_op | bedrag_excl_btw | btw_bedrag | bedrag_incl_btw | bestellingskorting | bedrag_na_bestellingskorting | eenmalige_korting | bedrag_na_eenmalige_korting | klantenkorting | totaal_bedrag | bedrijfsnaam | adres |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2026-10-10 | NULL | 40.00 | 3.60 | 43.60 | 0.00 | 43.60 | 0.00 | 43.60 | 2.18 | 41.42 | Testapotheek Breda | Testapotheekstraat 1, Breda |

### 03. Administratie: werkelijk geleverde factuurregels
| quantity | unit_price |
| --- | --- |
| 2 | 20.00 |

### 04. Distributie: rooster voor 31 oktober
| levering_id | pogingnummer | geplande_tijd | resultaat | bestelling_id | bedrijfsnaam | contactpersoon | telefoonnummer | adres | ritdatum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 1 | 10:00:00 | NULL | 3 | Testapotheek Breda | Testcontact | 0612345678 | Testapotheekstraat 1, Breda | 2026-10-31 |

### 05. Acquisitie: nog geen order, bezoek ouder dan een maand
| potentiele_klant_id | bedrijfsnaam | contactpersoon | contactgegevens | adres | klant_id | bezoekdatum |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | Testapotheek Eindhoven | Contact Eindhoven | 0644444444 | Nieuwe apotheekstraat 4, Eindhoven | 2 | 2026-08-15 |
| 1 | Prospectapotheek Tilburg | Prospectcontact | 0633333333 | Prospectlaan 3, Tilburg | NULL | 2026-09-15 |

## Interpretatie en beperkingen

- De testdatabase bevat alleen fictieve, niet-productiegegevens.
- De geslaagde tests bewijzen de gecontroleerde vijf scenario's en deze SQL-outputs, niet automatisch alle integratiepaden van het volledige project.
- Visuele en keyboardtests op echte mobiele apparaten zijn hiermee niet uitgevoerd.
- Onbekende historische factuurbedragen worden niet met aannames aangevuld.
- De output per scherm van overige proces-PR's moet op de geïntegreerde eindversie afzonderlijk worden gemeten.
