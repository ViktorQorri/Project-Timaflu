# Gemeten MySQL-queryresultaten voor de vijf verplichte scenario's

Testdatum: 31 oktober 2026. Gecontroleerde codecommit: 0cb154b30876663fe6da08c92212640e49edfff0

Bronnen: code/database/schema.sql, Documentation/Architecture/test-data/fixtures_assessed.sql en selects_assessed.sql.

Deze tabellen zijn door MySQL 8.4 teruggegeven voor fictieve gegevens in een nieuw gemaakte en na afloop verwijderde lokale testdatabase.
Het uitvoerbare bewijs staat in run_caseproof_mysql.py; hiermee zijn ook zeven procespagina's met echte MySQL-verbindingen getest.

### 01. Verkoop: klantgegevens
| klant_id | bedrijfsnaam | eenmalige_korting_toegezegd | klantadres |
| --- | --- | --- | --- |
| 1 | Testapotheek Breda | 0 | Testapotheekstraat 1, Breda |

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
| factuur_id | factuurdatum | betaald_op | betalingsregeling_geaccepteerd | incasso_ingeschakeld | bedrag_excl_btw | btw_bedrag | bedrag_incl_btw | bestellingskorting | bedrag_na_bestellingskorting | eenmalige_korting | bedrag_na_eenmalige_korting | klantenkorting | totaal_bedrag | bedrijfsnaam | adres |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2026-10-31 | NULL | NULL | 0 | 20.00 | 1.80 | 21.80 | 0.00 | 21.80 | 0.00 | 21.80 | 1.09 | 20.71 | Testapotheek Breda | Testapotheekstraat 1, Breda |

### 03. Administratie: werkelijk geleverde factuurregels
| quantity | unit_price |
| --- | --- |
| 1 | 20.00 |

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

## Aanvullend, onafhankelijk MySQL-testbewijs uit de andere casusreview

De gelijktijdige code-review heeft met een andere, eveneens fictieve testdataset
en een eerdere codeversie apart de queryresultaten en bezorgovergangen vastgelegd.
Deze bestanden blijven behouden als **historisch aanvullend bewijs**, niet als
uitvoer van de hierboven genoemde actuele codecommit:

- [Oorspronkelijke MySQL 8.4-consoleuitvoer](test-data/mysql84_output_verified.txt)
- [Testscenario twee afzonderlijke bezorgpogingen](test-data/delivery_two_stage_assessed.sql)
- [Gemeten MySQL-uitvoer van die bezorgpogingen](test-data/delivery_two_stage_output.txt)

De uitvoer hierboven is de opnieuw gemeten uitkomst van de samengevoegde casusbranch
met de actuele SQL en testdata. Verschillende factuurregels in het historische
bewijs en dit resultaat betreffen verschillende testmomenten.
