# Werkelijke MySQL-query-output per scherm

Uitgevoerd op geïsoleerde MySQL 8.4.13 met fictieve fixturegegevens.
Elke query hieronder is tijdens het echte GET-verzoek van de Flask-app
onderschept en de getoonde rijen zijn afkomstig van MySQL, niet verzonnen.
Schermen zonder dynamische databasegegevens zijn expliciet als statisch vermeld.

## Home en databasecontrole

Scherm: /
HTTP-status: 200

### Query 1
```sql
SELECT 1
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  [
    1
  ]
]
```

## Klanten (statisch scherm)

Scherm: /customers
HTTP-status: 200

*Geen SQL-query: statisch/placeholder-scherm.*

## Telefonische verkoop en beschikbaarheid

Scherm: /orders?q=Testmedicijn&quantity=1
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.productnaam, COALESCE(m.voorraad, 0) AS voorraad, COALESCE(r.gereserveerd, 0) AS gereserveerd, GREATEST(COALESCE(m.voorraad, 0) - COALESCE(r.gereserveerd, 0), 0) AS beschikbaar FROM Product AS p LEFT JOIN ( SELECT product_id, SUM(aantal) AS voorraad FROM Magazijnlocatie GROUP BY product_id ) AS m ON m.product_id = p.product_id LEFT JOIN ( SELECT product_id, SUM(aantal) AS gereserveerd FROM Voorraadreservering GROUP BY product_id ) AS r ON r.product_id = p.product_id WHERE (p.productnaam LIKE %s OR p.artikelnummer LIKE %s) AND p.in_assortiment = TRUE ORDER BY p.productnaam ASC
```
Parameters: ```json
["%Testmedicijn%", "%Testmedicijn%"]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "artikelnummer": "TEST-001",
    "productnaam": "Testmedicijn",
    "voorraad": "10",
    "gereserveerd": "0",
    "beschikbaar": "10"
  }
]
```

## Productcatalogus

Scherm: /products
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.bestelcode, p.productnaam, p.prijs_per_grootverpakking, p.verpakkingssoort, p.aantal_detailverpakkingen, p.korte_omschrijving, p.lange_omschrijving, p.minimale_bestelhoeveelheid, p.minimumvoorraad, p.in_assortiment FROM Product AS p WHERE p.in_assortiment = TRUE ORDER BY p.productnaam ASC, p.artikelnummer ASC
```
Parameters: ```json
[]
```
Resultaat: 2 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "artikelnummer": "TEST-001",
    "bestelcode": "TEST-CODE",
    "productnaam": "Testmedicijn",
    "prijs_per_grootverpakking": "100.00",
    "verpakkingssoort": null,
    "aantal_detailverpakkingen": 1,
    "korte_omschrijving": null,
    "lange_omschrijving": null,
    "minimale_bestelhoeveelheid": 1,
    "minimumvoorraad": 1,
    "in_assortiment": 1
  },
  {
    "product_id": 2,
    "artikelnummer": "TEST-002",
    "bestelcode": "TEST-2",
    "productnaam": "Testtekortproduct",
    "prijs_per_grootverpakking": "15.00",
    "verpakkingssoort": null,
    "aantal_detailverpakkingen": 1,
    "korte_omschrijving": null,
    "lange_omschrijving": null,
    "minimale_bestelhoeveelheid": 1,
    "minimumvoorraad": 9,
    "in_assortiment": 1
  }
]
```

### Query 2
```sql
SELECT w.product_id, w.stofnaam, w.hoeveelheid FROM ProductWerkzameStof AS w JOIN Product AS p ON p.product_id = w.product_id WHERE p.in_assortiment = TRUE ORDER BY w.stofnaam ASC
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "stofnaam": "Teststof",
    "hoeveelheid": "50 mg"
  }
]
```

## Product toevoegen: leverancierskeuze

Scherm: /products/new
HTTP-status: 200

### Query 1
```sql
SELECT leverancier_id, naam, contactpersoon, telefoonnummer, internetadres FROM Leverancier ORDER BY naam ASC
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "leverancier_id": 1,
    "naam": "TEST Fabrikant",
    "contactpersoon": "TEST contactpersoon",
    "telefoonnummer": "0600000000",
    "internetadres": null
  }
]
```

## Product bewerken

Scherm: /products/1/edit
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.bestelcode, p.productnaam, p.prijs_per_grootverpakking, p.verpakkingssoort, p.aantal_detailverpakkingen, p.korte_omschrijving, p.lange_omschrijving, p.minimale_bestelhoeveelheid, p.minimumvoorraad, p.in_assortiment FROM Product AS p WHERE p.product_id = %s AND p.in_assortiment = TRUE
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "artikelnummer": "TEST-001",
    "bestelcode": "TEST-CODE",
    "productnaam": "Testmedicijn",
    "prijs_per_grootverpakking": "100.00",
    "verpakkingssoort": null,
    "aantal_detailverpakkingen": 1,
    "korte_omschrijving": null,
    "lange_omschrijving": null,
    "minimale_bestelhoeveelheid": 1,
    "minimumvoorraad": 1,
    "in_assortiment": 1
  }
]
```

### Query 2
```sql
SELECT product_id, stofnaam, hoeveelheid FROM ProductWerkzameStof WHERE product_id = %s ORDER BY stofnaam ASC
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "stofnaam": "Teststof",
    "hoeveelheid": "50 mg"
  }
]
```

## Product verwijderen

Scherm: /products/1/remove
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.bestelcode, p.productnaam, p.prijs_per_grootverpakking, p.verpakkingssoort, p.aantal_detailverpakkingen, p.korte_omschrijving, p.lange_omschrijving, p.minimale_bestelhoeveelheid, p.minimumvoorraad, p.in_assortiment FROM Product AS p WHERE p.product_id = %s AND p.in_assortiment = TRUE
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "artikelnummer": "TEST-001",
    "bestelcode": "TEST-CODE",
    "productnaam": "Testmedicijn",
    "prijs_per_grootverpakking": "100.00",
    "verpakkingssoort": null,
    "aantal_detailverpakkingen": 1,
    "korte_omschrijving": null,
    "lange_omschrijving": null,
    "minimale_bestelhoeveelheid": 1,
    "minimumvoorraad": 1,
    "in_assortiment": 1
  }
]
```

### Query 2
```sql
SELECT product_id, stofnaam, hoeveelheid FROM ProductWerkzameStof WHERE product_id = %s ORDER BY stofnaam ASC
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "stofnaam": "Teststof",
    "hoeveelheid": "50 mg"
  }
]
```

## Minimumvoorraad

Scherm: /stock
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad, COALESCE(SUM(m.aantal), 0) AS voorraad FROM Product AS p LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id WHERE p.in_assortiment = TRUE GROUP BY p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad HAVING voorraad < p.minimumvoorraad ORDER BY (p.minimumvoorraad - voorraad) DESC, p.productnaam ASC
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 2,
    "artikelnummer": "TEST-002",
    "productnaam": "Testtekortproduct",
    "minimumvoorraad": 9,
    "voorraad": "0"
  }
]
```

## Goedkoopste leverancier

Scherm: /suppliers?product=Testmedicijn
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.productnaam, l.leverancier_id, l.naam AS leverancier, l.contactpersoon, l.telefoonnummer, a.inkoopprijs FROM Product AS p JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id WHERE p.productnaam LIKE %s AND p.intern_bestelbaar = TRUE AND p.in_assortiment = TRUE ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC
```
Parameters: ```json
["%Testmedicijn%"]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "productnaam": "Testmedicijn",
    "leverancier_id": 1,
    "leverancier": "TEST Fabrikant",
    "contactpersoon": "TEST contactpersoon",
    "telefoonnummer": "0600000000",
    "inkoopprijs": "65.00"
  }
]
```

## Orderpicking (statisch scherm)

Scherm: /order-picking
HTTP-status: 200

*Geen SQL-query: statisch/placeholder-scherm.*

## Distributierooster

Scherm: /deliveries?day=2026-10-22
HTTP-status: 200

### Query 1
```sql
SELECT lp.levering_id, lp.pogingnummer, lp.geplande_tijd, lp.resultaat, b.bestelling_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer, a.adres, r.ritdatum FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id JOIN Levering l ON l.levering_id=lp.levering_id JOIN Bestelling b ON b.bestelling_id=l.bestelling_id JOIN Klant k ON k.klant_id=b.klant_id JOIN Adres a ON a.adres_id=b.afleveradres_id WHERE r.ritdatum=%s ORDER BY lp.geplande_tijd
```
Parameters: ```json
["2026-10-22"]
```
Resultaat: 3 rij(en) (maximaal 15 getoond)
```json
[
  {
    "levering_id": 1,
    "pogingnummer": 1,
    "geplande_tijd": "10:00:00",
    "resultaat": "afgeleverd",
    "bestelling_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "adres": "TEST: Afleverstraat 8, Breda",
    "ritdatum": "2026-10-22"
  },
  {
    "levering_id": 2,
    "pogingnummer": 1,
    "geplande_tijd": "11:00:00",
    "resultaat": "afgeleverd",
    "bestelling_id": 2,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "adres": "TEST: Afleverstraat 8, Breda",
    "ritdatum": "2026-10-22"
  },
  {
    "levering_id": 3,
    "pogingnummer": 1,
    "geplande_tijd": "12:00:00",
    "resultaat": null,
    "bestelling_id": 3,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "adres": "TEST: Afleverstraat 8, Breda",
    "ritdatum": "2026-10-22"
  }
]
```

## Openstaande facturen

Scherm: /invoices?customer_id=1
HTTP-status: 200

### Query 1
```sql
SELECT f.factuur_id, f.factuurdatum, f.betaald_op, f.week_start, f.afzenderadres, f.factuuradres, f.betalingsregeling_geaccepteerd, f.incasso_ingeschakeld, f.bedrag_excl_btw, f.btw_bedrag, f.bedrag_incl_btw, f.bestellingskorting, f.bedrag_na_bestellingskorting, f.eenmalige_korting, f.bedrag_na_eenmalige_korting, f.klantenkorting, f.totaal_bedrag, k.bedrijfsnaam, a.adres FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id JOIN Adres a ON a.adres_id=k.betaaladres_id WHERE f.klant_id=%s AND f.betaald_op IS NULL ORDER BY f.factuurdatum DESC
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "factuur_id": 1,
    "factuurdatum": "2026-10-31",
    "betaald_op": null,
    "week_start": "2026-10-19",
    "afzenderadres": "TESTGEGEVENS: Fictieve Afzenderstraat 9, Breda",
    "factuuradres": "TEST: Factuurstraat 12, Breda",
    "betalingsregeling_geaccepteerd": null,
    "incasso_ingeschakeld": 0,
    "bedrag_excl_btw": "700.00",
    "btw_bedrag": "63.00",
    "bedrag_incl_btw": "763.00",
    "bestellingskorting": "32.70",
    "bedrag_na_bestellingskorting": "730.30",
    "eenmalige_korting": "62.13",
    "bedrag_na_eenmalige_korting": "668.17",
    "klantenkorting": "33.41",
    "totaal_bedrag": "634.76",
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "adres": "TEST: Factuurstraat 12, Breda",
    "lines": [
      {
        "quantity": 6,
        "unit_price": "100.00"
      },
      {
        "quantity": 1,
        "unit_price": "100.00"
      }
    ]
  }
]
```

### Query 2
```sql
SELECT l.aantal_geleverd AS quantity, b.prijs_per_eenheid AS unit_price FROM Leveringregel l JOIN Levering v ON v.levering_id=l.levering_id JOIN Bestelregel b ON b.bestelling_id=v.bestelling_id AND b.product_id=l.product_id WHERE l.factuur_id=%s
```
Parameters: ```json
[1]
```
Resultaat: 2 rij(en) (maximaal 15 getoond)
```json
[
  {
    "quantity": 6,
    "unit_price": "100.00"
  },
  {
    "quantity": 1,
    "unit_price": "100.00"
  }
]
```

## Weekfacturen

Scherm: /invoices/weekly?week_start=2026-10-19
HTTP-status: 200

### Query 1
```sql
SELECT DISTINCT b.klant_id FROM Leveringregel lr JOIN Levering l ON l.levering_id=lr.levering_id JOIN Bestelling b ON b.bestelling_id=l.bestelling_id WHERE lr.factuur_id IS NULL AND EXISTS ( SELECT 1 FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id WHERE lp.levering_id=l.levering_id AND lp.resultaat='afgeleverd' AND lp.ontvangst_getekend=TRUE AND r.ritdatum BETWEEN %s AND %s ) ORDER BY b.klant_id
```
Parameters: ```json
["2026-10-19", "2026-10-25"]
```
Resultaat: 0 rij(en) (maximaal 15 getoond)
```json
[]
```

## Uitgegeven factuur

Scherm: /invoices/issued/1
HTTP-status: 200

### Query 1
```sql
SELECT f.*, k.bedrijfsnaam, COALESCE(f.factuuradres,a.adres) AS adres FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id JOIN Adres a ON a.adres_id=k.betaaladres_id WHERE f.factuur_id=%s
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "factuur_id": 1,
    "klant_id": 1,
    "factuurdatum": "2026-10-31",
    "week_start": "2026-10-19",
    "afzenderadres": "TESTGEGEVENS: Fictieve Afzenderstraat 9, Breda",
    "factuuradres": "TEST: Factuurstraat 12, Breda",
    "betaald_op": null,
    "betalingsregeling_geaccepteerd": null,
    "incasso_ingeschakeld": 0,
    "bedrag_excl_btw": "700.00",
    "btw_bedrag": "63.00",
    "bedrag_incl_btw": "763.00",
    "bestellingskorting": "32.70",
    "bedrag_na_bestellingskorting": "730.30",
    "eenmalige_korting": "62.13",
    "bedrag_na_eenmalige_korting": "668.17",
    "klantenkorting": "33.41",
    "totaal_bedrag": "634.76",
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "adres": "TEST: Factuurstraat 12, Breda",
    "lines": [
      {
        "quantity": 6,
        "unit_price": "100.00",
        "order_id": 1
      },
      {
        "quantity": 1,
        "unit_price": "100.00",
        "order_id": 2
      }
    ]
  }
]
```

### Query 2
```sql
SELECT lr.aantal_geleverd AS quantity, br.prijs_per_eenheid AS unit_price, b.bestelling_id AS order_id FROM Leveringregel lr JOIN Levering l ON l.levering_id=lr.levering_id JOIN Bestelling b ON b.bestelling_id=l.bestelling_id JOIN Bestelregel br ON br.bestelling_id=b.bestelling_id AND br.product_id=lr.product_id WHERE lr.factuur_id=%s ORDER BY b.bestelling_id, lr.product_id
```
Parameters: ```json
[1]
```
Resultaat: 2 rij(en) (maximaal 15 getoond)
```json
[
  {
    "quantity": 6,
    "unit_price": "100.00",
    "order_id": 1
  },
  {
    "quantity": 1,
    "unit_price": "100.00",
    "order_id": 2
  }
]
```

## Acquisitie-opvolging

Scherm: /acquisition
HTTP-status: 200

### Query 1
```sql
SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon, p.contactgegevens, a.adres, p.klant_id, MAX(v.bezoekdatum) AS bezoekdatum FROM PotentieleKlant p JOIN Acquisitiebezoek v ON v.potentiele_klant_id=p.potentiele_klant_id JOIN Adres a ON a.adres_id=p.adres_id WHERE NOT EXISTS ( SELECT 1 FROM Bestelling b WHERE b.klant_id = p.klant_id ) GROUP BY p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,p.contactgegevens,a.adres,p.klant_id HAVING MAX(v.bezoekdatum)<=%s ORDER BY bezoekdatum
```
Parameters: ```json
["2026-09-30"]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "potentiele_klant_id": 1,
    "bedrijfsnaam": "TEST Prospectapotheek",
    "contactpersoon": "TEST prospect",
    "contactgegevens": "0600000001",
    "adres": "TEST: Prospectlaan 3",
    "klant_id": null,
    "bezoekdatum": "2026-09-15"
  }
]
```

## Rapportage (statisch scherm)

Scherm: /reports
HTTP-status: 200

*Geen SQL-query: statisch/placeholder-scherm.*

## Database API gezondheid

Scherm: /api/health
HTTP-status: 200

### Query 1
```sql
SELECT 1
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  [
    1
  ]
]
```
