# Werkelijke MySQL-query-output per scherm

Uitgevoerd op geïsoleerde MySQL 8.4.13 met fictieve fixturegegevens.
Elke query hieronder is tijdens het echte GET-verzoek van de Flask-app
onderschept en de getoonde rijen zijn afkomstig van MySQL, niet verzonnen.
Schermen zonder dynamische databasegegevens zijn expliciet als statisch vermeld.
De robotinterface /api/robots/<id>/next is geen medewerkersscherm:
deze API wordt afzonderlijk op gang-/robotvalidatie getest.

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

## Klanten zoeken: centrale klantgegevens

Scherm: /customers?q=TEST
HTTP-status: 200

### Query 1
```sql
SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer, af.adres AS afleveradres, ba.adres AS factuuradres, CASE WHEN o.paid_count IS NULL THEN 0 WHEN o.paid_count = o.known_amount_count THEN o.jaaromzet ELSE NULL END AS jaaromzet, kk.percentage AS kortingspercentage FROM Klant AS k JOIN Adres AS af ON af.adres_id = k.afleveradres_id JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id LEFT JOIN ( SELECT f.klant_id, COUNT(*) AS paid_count, COUNT(f.totaal_bedrag) AS known_amount_count, SUM(f.totaal_bedrag) AS jaaromzet FROM Factuur AS f WHERE YEAR(f.betaald_op) = %s GROUP BY f.klant_id ) AS o ON o.klant_id = k.klant_id LEFT JOIN Klantkorting AS kk ON kk.klant_id = k.klant_id AND kk.kalenderjaar = %s WHERE k.actief = TRUE AND (k.bedrijfsnaam LIKE %s OR k.contactpersoon LIKE %s OR k.telefoonnummer LIKE %s) ORDER BY k.bedrijfsnaam ASC, k.klant_id ASC
```
Parameters: ```json
[2026, 2027, "%TEST%", "%TEST%", "%TEST%"]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "afleveradres": "TEST: Afleverstraat 8, Breda",
    "factuuradres": "TEST: Factuurstraat 12, Breda",
    "jaaromzet": "0",
    "kortingspercentage": null
  }
]
```

## Klantgegevens en adressen bewerken (AD07)

Scherm: /customers/1/edit
HTTP-status: 200

### Query 1
```sql
SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer, af.adres AS afleveradres, ba.adres AS factuuradres FROM Klant AS k JOIN Adres AS af ON af.adres_id = k.afleveradres_id JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id WHERE k.klant_id = %s AND k.actief = TRUE
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "afleveradres": "TEST: Afleverstraat 8, Breda",
    "factuuradres": "TEST: Factuurstraat 12, Breda"
  }
]
```

## Klant deactiveren, historie bewaren (AD07)

Scherm: /customers/1/deactivate
HTTP-status: 200

### Query 1
```sql
SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer, af.adres AS afleveradres, ba.adres AS factuuradres FROM Klant AS k JOIN Adres AS af ON af.adres_id = k.afleveradres_id JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id WHERE k.klant_id = %s AND k.actief = TRUE
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "afleveradres": "TEST: Afleverstraat 8, Breda",
    "factuuradres": "TEST: Factuurstraat 12, Breda"
  }
]
```

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

## Telefonische orderinvoer met actuele klant- en productgegevens

Scherm: /orders/new
HTTP-status: 200

### Query 1
```sql
SELECT klant_id, bedrijfsnaam FROM Klant WHERE actief=TRUE ORDER BY bedrijfsnaam, klant_id
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V."
  }
]
```

### Query 2
```sql
SELECT product_id, productnaam, artikelnummer, minimale_bestelhoeveelheid, prijs_per_grootverpakking FROM Product WHERE in_assortiment=TRUE ORDER BY productnaam
```
Parameters: ```json
[]
```
Resultaat: 2 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "productnaam": "Testmedicijn",
    "artikelnummer": "TEST-001",
    "minimale_bestelhoeveelheid": 1,
    "prijs_per_grootverpakking": "100.00"
  },
  {
    "product_id": 2,
    "productnaam": "Testtekortproduct",
    "artikelnummer": "TEST-002",
    "minimale_bestelhoeveelheid": 1,
    "prijs_per_grootverpakking": "15.00"
  }
]
```

## Bestellingen en echte orderstatus

Scherm: /orders/status
HTTP-status: 200

### Query 1
```sql
SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam, k.klant_id, k.bedrijfsnaam, address.adres AS afleveradres FROM Bestelling AS b JOIN Klant AS k ON k.klant_id=b.klant_id JOIN Adres AS address ON address.adres_id=b.afleveradres_id WHERE (%s IS NULL OR b.klant_id = %s) ORDER BY b.besteld_op DESC, b.bestelling_id DESC
```
Parameters: ```json
[null, null]
```
Resultaat: 4 rij(en) (maximaal 15 getoond)
```json
[
  {
    "bestelling_id": 4,
    "besteld_op": "2026-10-29 09:00:00",
    "gewenste_leverdatum": "2026-10-30",
    "dagdeel": "ochtend",
    "spoed": 0,
    "status_naam": "afgeleverd",
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "afleveradres": "TEST: Afleverstraat 8, Breda"
  },
  {
    "bestelling_id": 3,
    "besteld_op": "2026-10-21 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "ochtend",
    "spoed": 0,
    "status_naam": "verstuurd",
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "afleveradres": "TEST: Afleverstraat 8, Breda"
  },
  {
    "bestelling_id": 2,
    "besteld_op": "2026-10-20 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "middag",
    "spoed": 0,
    "status_naam": "gefactureerd",
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "afleveradres": "TEST: Afleverstraat 8, Breda"
  },
  {
    "bestelling_id": 1,
    "besteld_op": "2026-10-19 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "ochtend",
    "spoed": 0,
    "status_naam": "gefactureerd",
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "afleveradres": "TEST: Afleverstraat 8, Breda"
  }
]
```

## Orderstatus zoeken op nummer (AD06)

Scherm: /orders?order=1
HTTP-status: 200

### Query 1
```sql
SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op, b.gewenste_leverdatum, b.dagdeel, b.status_naam FROM Bestelling AS b JOIN Klant AS k ON k.klant_id = b.klant_id WHERE b.bestelling_id = %s OR k.bedrijfsnaam LIKE %s ESCAPE '!' ORDER BY b.besteld_op DESC, b.bestelling_id DESC
```
Parameters: ```json
[1, "%1%"]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "bestelling_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "besteld_op": "2026-10-19 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "ochtend",
    "status_naam": "gefactureerd"
  }
]
```

## Orderregels en geregistreerde tekortafspraken (AD06)

Scherm: /orders/1/status
HTTP-status: 200

### Query 1
```sql
SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum, b.dagdeel, b.status_naam, k.bedrijfsnaam FROM Bestelling AS b JOIN Klant AS k ON k.klant_id = b.klant_id WHERE b.bestelling_id = %s
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "bestelling_id": 1,
    "besteld_op": "2026-10-19 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "ochtend",
    "status_naam": "gefactureerd",
    "bedrijfsnaam": "TEST Apotheek B.V."
  }
]
```

### Query 2
```sql
SELECT p.artikelnummer, p.productnaam, br.aantal, br.prijs_per_eenheid, br.afnemen_bij_tekort, COALESCE(vr.aantal, 0) AS gereserveerd, COALESCE(( SELECT SUM(dr.aantal) FROM Deelorderregel AS dr JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id WHERE d.bestelling_id = br.bestelling_id AND dr.product_id = br.product_id AND d.afgerond = FALSE ), 0) AS in_open_deelorder, COALESCE(( SELECT SUM(dr.aantal) FROM Deelorderregel AS dr JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id WHERE d.bestelling_id = br.bestelling_id AND dr.product_id = br.product_id AND d.afgerond = TRUE ), 0) AS in_afgeronde_deelorder, COALESCE(( SELECT SUM(lr.aantal_geleverd) FROM Levering AS lv JOIN Leveringregel AS lr ON lr.levering_id = lv.levering_id WHERE lv.bestelling_id = br.bestelling_id AND lr.product_id = br.product_id AND NOT EXISTS ( SELECT 1 FROM Leverpoging AS lp WHERE lp.levering_id = lv.levering_id AND lp.resultaat = 'afgeleverd' AND lp.ontvangst_getekend = TRUE ) ), 0) AS in_open_levering, COALESCE(( SELECT SUM(lr.aantal_geleverd) FROM Levering AS lv JOIN Leveringregel AS lr ON lr.levering_id = lv.levering_id WHERE lv.bestelling_id = br.bestelling_id AND lr.product_id = br.product_id AND EXISTS ( SELECT 1 FROM Leverpoging AS lp WHERE lp.levering_id = lv.levering_id AND lp.resultaat = 'afgeleverd' AND lp.ontvangst_getekend = TRUE ) ), 0) AS aantal_afgeleverd FROM Bestelregel AS br JOIN Product AS p ON p.product_id = br.product_id LEFT JOIN Voorraadreservering AS vr ON vr.bestelling_id = br.bestelling_id AND vr.product_id = br.product_id WHERE br.bestelling_id = %s ORDER BY p.productnaam ASC, p.product_id ASC
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "artikelnummer": "TEST-001",
    "productnaam": "Testmedicijn",
    "aantal": 6,
    "prijs_per_eenheid": "100.00",
    "afnemen_bij_tekort": null,
    "gereserveerd": 0,
    "in_open_deelorder": "0",
    "in_afgeronde_deelorder": "0",
    "in_open_levering": "0",
    "aantal_afgeleverd": "6"
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
SELECT p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad, COALESCE(SUM(m.aantal), 0) AS voorraad, EXISTS ( SELECT 1 FROM LeveranciersAanbod AS a WHERE a.product_id = p.product_id ) AS heeft_leverancier FROM Product AS p LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id WHERE p.in_assortiment = TRUE GROUP BY p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad HAVING voorraad < p.minimumvoorraad ORDER BY (p.minimumvoorraad - voorraad) DESC, p.productnaam ASC
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
    "voorraad": "0",
    "heeft_leverancier": 0
  }
]
```

## Goedkoopste leverancier

Scherm: /suppliers?product=Testmedicijn
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.productnaam, l.leverancier_id, l.naam AS leverancier, l.contactpersoon, l.telefoonnummer, l.internetadres, a.inkoopprijs FROM Product AS p JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id WHERE p.productnaam LIKE %s AND p.intern_bestelbaar = TRUE AND p.in_assortiment = TRUE ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC
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
    "internetadres": null,
    "inkoopprijs": "65.00"
  }
]
```

## Fabrikanten en contactgegevens

Scherm: /manufacturers
HTTP-status: 200

### Query 1
```sql
SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon, l.telefoonnummer, l.internetadres FROM Leverancier AS l JOIN Adres AS a ON a.adres_id = l.adres_id ORDER BY l.naam, l.leverancier_id
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
    "adres": "TEST: Leveranciersweg 1",
    "contactpersoon": "TEST contactpersoon",
    "telefoonnummer": "0600000000",
    "internetadres": null
  }
]
```

## Fabrikant toevoegen

Scherm: /manufacturers/new
HTTP-status: 200

*Geen SQL-query: statisch/placeholder-scherm.*

## Fabrikant bewerken

Scherm: /manufacturers/1/edit
HTTP-status: 200

### Query 1
```sql
SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon, l.telefoonnummer, l.internetadres FROM Leverancier AS l JOIN Adres AS a ON a.adres_id = l.adres_id WHERE l.leverancier_id = %s
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "leverancier_id": 1,
    "naam": "TEST Fabrikant",
    "adres": "TEST: Leveranciersweg 1",
    "contactpersoon": "TEST contactpersoon",
    "telefoonnummer": "0600000000",
    "internetadres": null
  }
]
```

## Inkoopprijzen van fabrikant beheren

Scherm: /manufacturers/1/prices
HTTP-status: 200

### Query 1
```sql
SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon, l.telefoonnummer, l.internetadres FROM Leverancier AS l JOIN Adres AS a ON a.adres_id = l.adres_id WHERE l.leverancier_id = %s
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "leverancier_id": 1,
    "naam": "TEST Fabrikant",
    "adres": "TEST: Leveranciersweg 1",
    "contactpersoon": "TEST contactpersoon",
    "telefoonnummer": "0600000000",
    "internetadres": null
  }
]
```

### Query 2
```sql
SELECT product_id, productnaam, artikelnummer FROM Product WHERE in_assortiment = TRUE ORDER BY productnaam, product_id
```
Parameters: ```json
[]
```
Resultaat: 2 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "productnaam": "Testmedicijn",
    "artikelnummer": "TEST-001"
  },
  {
    "product_id": 2,
    "productnaam": "Testtekortproduct",
    "artikelnummer": "TEST-002"
  }
]
```

### Query 3
```sql
SELECT a.product_id, p.productnaam, a.inkoopprijs FROM LeveranciersAanbod AS a JOIN Product AS p ON p.product_id = a.product_id WHERE a.leverancier_id = %s AND p.in_assortiment = TRUE ORDER BY p.productnaam, a.product_id
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "product_id": 1,
    "productnaam": "Testmedicijn",
    "inkoopprijs": "65.00"
  }
]
```

## Inkoop bij minimumvoorraad

Scherm: /reorder
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad, COALESCE(SUM(m.aantal), 0) AS voorraad, EXISTS ( SELECT 1 FROM LeveranciersAanbod AS a WHERE a.product_id = p.product_id ) AS heeft_leverancier FROM Product AS p LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id WHERE p.in_assortiment = TRUE GROUP BY p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad HAVING voorraad < p.minimumvoorraad ORDER BY (p.minimumvoorraad - voorraad) DESC, p.productnaam ASC
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
    "voorraad": "0",
    "heeft_leverancier": 0
  }
]
```

### Query 2
```sql
SELECT i.inkoopbestelling_id, i.besteld_op, i.status_naam, l.naam AS leverancier, p.productnaam, r.aantal FROM Inkoopbestelling AS i JOIN Leverancier AS l ON l.leverancier_id = i.leverancier_id JOIN Inkoopbestelregel AS r ON r.inkoopbestelling_id = i.inkoopbestelling_id JOIN Product AS p ON p.product_id = r.product_id ORDER BY i.besteld_op DESC, i.inkoopbestelling_id DESC, p.productnaam
```
Parameters: ```json
[]
```
Resultaat: 0 rij(en) (maximaal 15 getoond)
```json
[]
```

## Minimumvoorraad per medicijn instellen

Scherm: /stock/minimums
HTTP-status: 200

### Query 1
```sql
SELECT p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad, COALESCE(SUM(m.aantal), 0) AS voorraad FROM Product AS p LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id WHERE p.in_assortiment = TRUE GROUP BY p.product_id, p.artikelnummer, p.productnaam, p.minimumvoorraad ORDER BY p.productnaam, p.product_id
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
    "productnaam": "Testmedicijn",
    "minimumvoorraad": 1,
    "voorraad": "10"
  },
  {
    "product_id": 2,
    "artikelnummer": "TEST-002",
    "productnaam": "Testtekortproduct",
    "minimumvoorraad": 9,
    "voorraad": "0"
  }
]
```

## Adreslabel voor een werkelijk verpakte order

Scherm: /deliveries/1/label
HTTP-status: 200

### Query 1
```sql
SELECT b.bestelling_id, b.spoed, b.aantal_verhuisdozen, k.bedrijfsnaam, k.telefoonnummer, a.adres AS afleveradres FROM Bestelling AS b JOIN Klant AS k ON k.klant_id = b.klant_id JOIN Adres AS a ON a.adres_id = b.afleveradres_id WHERE b.bestelling_id = %s
```
Parameters: ```json
[1]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "bestelling_id": 1,
    "spoed": 0,
    "aantal_verhuisdozen": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "telefoonnummer": "0612345678",
    "afleveradres": "TEST: Afleverstraat 8, Breda"
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
SELECT b.bestelling_id, b.status_naam, b.spoed, b.gewenste_leverdatum, b.dagdeel, b.aantal_verhuisdozen, k.bedrijfsnaam, af.adres AS afleveradres, d.deelorder_id, d.afgerond, v.unieke_code, r.gang, EXISTS ( SELECT 1 FROM Deelorder AS picked JOIN Deelorderregel AS picked_line ON picked_line.deelorder_id = picked.deelorder_id WHERE picked.bestelling_id = b.bestelling_id AND picked.afgerond = TRUE AND picked_line.aantal > 0 ) AS heeft_verzameld FROM Bestelling AS b JOIN Klant AS k ON k.klant_id = b.klant_id JOIN Adres AS af ON af.adres_id = b.afleveradres_id JOIN Deelorder AS d ON d.bestelling_id = b.bestelling_id LEFT JOIN Verzamelbak AS v ON v.deelorder_id = d.deelorder_id LEFT JOIN Robot AS r ON r.robot_id = d.robot_id WHERE b.status_naam NOT IN ('verstuurd', 'afgeleverd', 'gefactureerd') AND EXISTS ( SELECT 1 FROM Deelorder AS d2 JOIN Verzamelbak AS v2 ON v2.deelorder_id = d2.deelorder_id WHERE d2.bestelling_id = b.bestelling_id ) ORDER BY b.bestelling_id DESC, d.deelorder_id ASC, v.unieke_code ASC
```
Parameters: ```json
[]
```
Resultaat: 0 rij(en) (maximaal 15 getoond)
```json
[]
```

### Query 2
```sql
SELECT b.bestelling_id, b.gewenste_leverdatum, b.dagdeel, b.spoed, k.bedrijfsnaam, k.telefoonnummer, a.adres AS afleveradres FROM Bestelling AS b JOIN Klant AS k ON k.klant_id = b.klant_id JOIN Adres AS a ON a.adres_id = b.afleveradres_id WHERE b.status_naam = 'verstuurd' -- Rebooking is allowed only when every earlier delivery failed twice. AND NOT EXISTS ( SELECT 1 FROM Levering AS l LEFT JOIN Leverpoging AS retry ON retry.levering_id = l.levering_id AND retry.pogingnummer = 2 WHERE l.bestelling_id = b.bestelling_id AND (retry.resultaat IS NULL OR retry.resultaat <> 'niet aanwezig') ) -- Never create another delivery for the same scheduled date. AND NOT EXISTS ( SELECT 1 FROM Levering AS l JOIN Leverpoging AS lp ON lp.levering_id = l.levering_id JOIN Rit AS r ON r.rit_id = lp.rit_id WHERE l.bestelling_id = b.bestelling_id AND r.ritdatum = b.gewenste_leverdatum ) ORDER BY b.spoed DESC, b.gewenste_leverdatum, b.bestelling_id
```
Parameters: ```json
[]
```
Resultaat: 0 rij(en) (maximaal 15 getoond)
```json
[]
```

### Query 3
```sql
SELECT koerier_id, naam, regio, extern, beschikbaar FROM Koerier ORDER BY naam, koerier_id
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "koerier_id": 1,
    "naam": "TEST koerier",
    "regio": null,
    "extern": 0,
    "beschikbaar": 1
  }
]
```

### Query 4
```sql
SELECT lp.levering_id, lp.pogingnummer, lp.geplande_tijd, lp.resultaat, b.bestelling_id, b.status_naam, b.spoed, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer, ko.koerier_id, ko.naam AS koerier, ko.regio AS koeriersregio, a.adres, r.ritdatum FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id JOIN Koerier ko ON ko.koerier_id=r.koerier_id JOIN Levering l ON l.levering_id=lp.levering_id JOIN Bestelling b ON b.bestelling_id=l.bestelling_id JOIN Klant k ON k.klant_id=b.klant_id JOIN Adres a ON a.adres_id=b.afleveradres_id WHERE r.ritdatum=%s ORDER BY b.spoed DESC, lp.geplande_tijd, lp.levering_id
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
    "status_naam": "gefactureerd",
    "spoed": 0,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "koerier_id": 1,
    "koerier": "TEST koerier",
    "koeriersregio": null,
    "adres": "TEST: Afleverstraat 8, Breda",
    "ritdatum": "2026-10-22",
    "can_register_first_attempt": false,
    "can_register_second_attempt": false,
    "can_reschedule": false
  },
  {
    "levering_id": 2,
    "pogingnummer": 1,
    "geplande_tijd": "11:00:00",
    "resultaat": "afgeleverd",
    "bestelling_id": 2,
    "status_naam": "gefactureerd",
    "spoed": 0,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "koerier_id": 1,
    "koerier": "TEST koerier",
    "koeriersregio": null,
    "adres": "TEST: Afleverstraat 8, Breda",
    "ritdatum": "2026-10-22",
    "can_register_first_attempt": false,
    "can_register_second_attempt": false,
    "can_reschedule": false
  },
  {
    "levering_id": 3,
    "pogingnummer": 1,
    "geplande_tijd": "12:00:00",
    "resultaat": null,
    "bestelling_id": 3,
    "status_naam": "verstuurd",
    "spoed": 0,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "contactpersoon": "TEST medewerker",
    "telefoonnummer": "0612345678",
    "koerier_id": 1,
    "koerier": "TEST koerier",
    "koeriersregio": null,
    "adres": "TEST: Afleverstraat 8, Breda",
    "ritdatum": "2026-10-22",
    "can_register_first_attempt": true,
    "can_register_second_attempt": false,
    "can_reschedule": false
  }
]
```

## Openstaande facturen

Scherm: /invoices?customer_id=1
HTTP-status: 200

### Query 1
```sql
SELECT f.factuur_id, f.factuurdatum, f.betaald_op, f.week_start, f.afzenderadres, f.factuuradres, f.betalingsregeling_geaccepteerd, f.incasso_ingeschakeld, f.extra_bezorgkosten_excl_btw, f.extra_bezorgkosten_btw, f.extra_bezorgkosten_incl_btw, f.bedrag_excl_btw, f.btw_bedrag, f.bedrag_incl_btw, f.bestellingskorting, f.bedrag_na_bestellingskorting, f.eenmalige_korting, f.bedrag_na_eenmalige_korting, f.klantenkorting, f.totaal_bedrag, k.bedrijfsnaam, a.adres FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id JOIN Adres a ON a.adres_id=k.betaaladres_id WHERE f.klant_id=%s AND f.betaald_op IS NULL ORDER BY f.factuurdatum DESC
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
    "extra_bezorgkosten_excl_btw": "0.00",
    "extra_bezorgkosten_btw": "0.00",
    "extra_bezorgkosten_incl_btw": "0.00",
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

### Query 3
```sql
SELECT i.inkoopfactuur_id, i.factuurdatum, i.bedrag, l.naam AS leverancier FROM Inkoopfactuur AS i JOIN Leverancier AS l ON l.leverancier_id = i.leverancier_id WHERE i.betaald_op IS NULL ORDER BY i.factuurdatum, i.inkoopfactuur_id
```
Parameters: ```json
[]
```
Resultaat: 0 rij(en) (maximaal 15 getoond)
```json
[]
```

### Query 4
```sql
SELECT b.bestelling_id, k.klant_id, k.bedrijfsnaam, MAX(r.ritdatum) AS afgeleverd_op, SUM(lr.aantal_geleverd * br.prijs_per_eenheid) AS subtotaal, b.extra_bezorgkosten FROM Leveringregel AS lr JOIN Levering AS l ON l.levering_id = lr.levering_id JOIN Bestelling AS b ON b.bestelling_id = l.bestelling_id JOIN Klant AS k ON k.klant_id = b.klant_id JOIN Bestelregel AS br ON br.bestelling_id = b.bestelling_id AND br.product_id = lr.product_id JOIN Leverpoging AS lp ON lp.levering_id = lr.levering_id AND lp.resultaat = 'afgeleverd' JOIN Rit AS r ON r.rit_id = lp.rit_id WHERE lr.factuur_id IS NULL GROUP BY b.bestelling_id, k.klant_id, k.bedrijfsnaam, b.extra_bezorgkosten ORDER BY afgeleverd_op, k.bedrijfsnaam, b.bestelling_id
```
Parameters: ```json
[]
```
Resultaat: 1 rij(en) (maximaal 15 getoond)
```json
[
  {
    "bestelling_id": 4,
    "klant_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "afgeleverd_op": "2026-10-30",
    "subtotaal": "100.00",
    "extra_bezorgkosten": "0.00"
  }
]
```

## Weekfacturen

Scherm: /invoices/weekly?week_start=2026-10-19
HTTP-status: 200

### Query 1
```sql
SELECT DISTINCT b.klant_id FROM Leveringregel lr JOIN Levering l ON l.levering_id=lr.levering_id JOIN Bestelling b ON b.bestelling_id=l.bestelling_id WHERE (lr.factuur_id IS NULL OR (b.extra_bezorgkosten > 0 AND b.extra_bezorgkosten_factuur_id IS NULL)) AND EXISTS ( SELECT 1 FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id WHERE lp.levering_id=l.levering_id AND lp.resultaat='afgeleverd' AND lp.ontvangst_getekend=TRUE AND r.ritdatum BETWEEN %s AND %s ) ORDER BY b.klant_id
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
    "extra_bezorgkosten_excl_btw": "0.00",
    "extra_bezorgkosten_btw": "0.00",
    "extra_bezorgkosten_incl_btw": "0.00",
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
    ],
    "delivery_charges": []
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

### Query 3
```sql
SELECT bestelling_id, extra_bezorgkosten, toelichting_extra_bezorgkosten FROM Bestelling WHERE extra_bezorgkosten_factuur_id=%s ORDER BY bestelling_id
```
Parameters: ```json
[1]
```
Resultaat: 0 rij(en) (maximaal 15 getoond)
```json
[]
```

## Acquisitie-opvolging

Scherm: /acquisition
HTTP-status: 200

### Query 1
```sql
SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon, p.contactgegevens, a.adres, MAX(v.bezoekdatum) AS laatste_bezoek FROM PotentieleKlant AS p JOIN Adres AS a ON a.adres_id = p.adres_id JOIN Acquisitiebezoek AS v ON v.potentiele_klant_id = p.potentiele_klant_id WHERE p.opvolging_afgesloten = FALSE AND NOT EXISTS ( SELECT 1 FROM Bestelling AS b WHERE b.klant_id = p.klant_id ) GROUP BY p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon, p.contactgegevens, a.adres HAVING MAX(v.bezoekdatum) <= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) ORDER BY laatste_bezoek ASC, p.bedrijfsnaam ASC
```
Parameters: ```json
[]
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
    "laatste_bezoek": "2026-09-15"
  }
]
```

## Orderstatusoverzicht

Scherm: /reports
HTTP-status: 200

### Query 1
```sql
SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op, b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam, COUNT(r.product_id) AS aantal_regels FROM Bestelling AS b JOIN Klant AS k ON k.klant_id = b.klant_id LEFT JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id WHERE (%s IS NULL OR b.besteld_op >= %s) AND (%s IS NULL OR b.besteld_op < %s + INTERVAL 1 DAY) GROUP BY b.bestelling_id, k.bedrijfsnaam, b.besteld_op, b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam ORDER BY b.besteld_op DESC, b.bestelling_id DESC
```
Parameters: ```json
[null, null, null, null]
```
Resultaat: 4 rij(en) (maximaal 15 getoond)
```json
[
  {
    "bestelling_id": 4,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "besteld_op": "2026-10-29 09:00:00",
    "gewenste_leverdatum": "2026-10-30",
    "dagdeel": "ochtend",
    "spoed": 0,
    "status_naam": "afgeleverd",
    "aantal_regels": 1
  },
  {
    "bestelling_id": 3,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "besteld_op": "2026-10-21 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "ochtend",
    "spoed": 0,
    "status_naam": "verstuurd",
    "aantal_regels": 1
  },
  {
    "bestelling_id": 2,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "besteld_op": "2026-10-20 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "middag",
    "spoed": 0,
    "status_naam": "gefactureerd",
    "aantal_regels": 1
  },
  {
    "bestelling_id": 1,
    "bedrijfsnaam": "TEST Apotheek B.V.",
    "besteld_op": "2026-10-19 09:00:00",
    "gewenste_leverdatum": "2026-10-22",
    "dagdeel": "ochtend",
    "spoed": 0,
    "status_naam": "gefactureerd",
    "aantal_regels": 1
  }
]
```

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
