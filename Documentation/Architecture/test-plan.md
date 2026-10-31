# Timaflu test plan

Refs #41.

## Scope
Unit, integration and acceptance testing for sales, purchasing, robot picking, distribution, weekly invoicing and acquisition. Incoming inventory is outside scope.

The school's Product-description.md does not require a separate automatic-test deliverable or a minimum code-coverage percentage. Issue #41 requests a test **plan**, and these checks support verification of the six case processes. Tests do not create additional business rules.

## Unit tests
Verify first-order and yearly customer discounts in correct sequence, minimum-stock lookup and manufacturer price sorting, delivery retry on the same day, unpaid invoice calculations, acquisition follow-up after one month, and concurrency-safe reservations.

## Integration tests
Use an isolated non-production MySQL instance. Compare schema.sql, migrations, the editable EER and SQL in repositories against queries.sql. Validate actual data and transaction behavior. Never fabricate database output.

## Acceptance tests
Exercise telephone orders, purchase orders after manual supplier contact, robot picking bins, delivery outcomes, weekly invoicing, and prospect conversion. Check mobile picking and distribution, keyboard access, Dutch UI, and no frontend JavaScript.

## Evidence
Run the Python unittest suite and git diff --check. Record test output, checked revision, relevant UML and use case references, screenshots and environment limitations. Do not claim real MySQL validation from fake repository tests.

## Executable acceptance test cases

All data below is fictional. Run these cases against a non-production MySQL instance after applicable branches are integrated. Record the tested commit SHA and resulting database rows.

| ID / traceability | Setup and input | Steps | Expected result |
|---|---|---|---|
| T01, AD05 / SD01 / Bestelling | Existing customer, order subtotal € 500, previous-year **paid** revenue € 12.000 | Add order lines by telephone, calculate, request customer approval | 5% order discount and the applicable annual discount in the specified sequence; no order persisted before approval |
| T02, AD05 / SD01 / Productbeschrijving | First order from new customer, previous-year paid revenue € 0 | Calculate order discount, first-order discount and customer discount | Discounts are accounted for in the documented sequence; do not silently treat the first-order discount as exclusion of the other categories |
| T03, AD04 / AD05 / Voorraadreservering | Warehouse has 3 units, another order has 1 unit reserved | Two sessions each attempt to reserve 2 units simultaneously | Exactly one reservation can succeed; the other must be rejected without double allocation. Verify on isolated MySQL |
| T04, AD02 / AD03 / LeveranciersAanbod | Three suppliers priced € 4, € 6 and € 9, cheapest cannot supply | Display shortage, compare offers and contact suppliers manually | Sorted offers with contacts; employee tries the next supplier. No automatic supplier order |
| T05, AD22 / AD23 / Deelorder | Order of 6 units, across robot aisles A (4) and B (2) | Generate suborders twice | Two aisle-specific suborders once; subsequent generation rejected; warehouse quantities not overallocated |
| T06, AD10 / AD11 / Verzamelbak | Robot receives a suborder and a uniquely coded collection bin is available | Robot scans the bin code, sends it to the information system, collects medicines and reports the suborder complete; when the bin becomes full it is moved to the roller conveyor | The system links the unique bin to the suborder, accepts the robot's completion message and offers the robot its next suborder. Do not require individual medicine scans: the case does not prescribe them |
| T07, AD12 / AD27 / Leverpoging | Courier arrives at delivery address with customer absent | Mark first absence, schedule same-day retry, mark outcome | Attempt history and order state reflect both attempts; no invented delivery success |
| T08, AD16 / AD18 / Factuur | Weekly delivered medicine items, VAT 9%, old unpaid invoice | Create invoice and retrieve unpaid balance | Only actually delivered items invoiced; discounts and amounts correspond to persisted historical transaction values |
| T09, AD20 / AD21 / Acquisitiebezoek | Prospect visited more than one month ago and has placed no order | Fetch follow-up list, call prospect, accept one-time incentive | Eligible prospect appears; account creation and 10% first order offer are recorded without automated marketing |
| T10, AD01 / Leverancier | New manufacturer with name, address, contact, phone, and price | Submit form and edit saved record | Database preserves supplier relation and price, validates input, does not remove historical references |
| T11, AD03 / Product.minimumvoorraad | Physical stock 2, minimum 5 | Open shortages, change minimum to 1, refresh | Initially shortage 3 displayed, after threshold change it disappears; physical stock remains 2 |
| T12, responsive | Phone-sized viewport 390 px and desktop 1440 px | Open picking and distribution, tab through controls and submit forms | No clipped controls, visible focus, comprehensible labels, no JavaScript dependency |

## Aanvullende acceptatiegevallen uit de oorspronkelijke casus

De volgende tests volgen uitsluitend Current-processes.md, Desired-process.md en Product-description.md, en vormen geen aanvullende eisen uit GitHub-userstories.

| ID / bron | Invoer en stappen | Verwacht resultaat | Resultaat |
|---|---|---|---|
| T13, Distributie en Productbeschrijving scenario 4 | Klant is aanwezig bij het eerste bezoek; ondertekening bevestigen; aflevering registreren en dezelfde actie herhalen | Eerste levering wordt afgeleverd, orderstatus bijgewerkt, geen tweede bezoek gepland; dubbel registreren geweigerd | Geautomatiseerd: Python en geïsoleerd MySQL geslaagd; handmatige acceptatie nog open |
| T14, Inkoop en Productbeschrijving scenario 2 | Probeer bestelling te registreren zonder voorafgaand contact; herhaal na handmatig leverancierscontact | Zonder bevestiging geen bestelling; na bevestiging uitsluitend interne registratie, geen automatische leverancierverzending | Geautomatiseerd: formuliercontrole en MySQL-invoer geslaagd; geen echt leveranciersgesprek gevoerd |
| T15, Acquisitie en Productbeschrijving scenario 5 | Bezoek zonder contactgegevens opslaan; daarna volledig bezoek opslaan; na maand opvolging opvragen | Verplichte contactgegevens aanwezig; prospect zonder order blijft opvolgbaar, ook als er al een account is | Geautomatiseerd: verplichte gegevens en acquisitiequery gecontroleerd; handmatige acceptatie nog open |
| T16, Administratie en Productbeschrijving scenario 3 | Factuur opzoeken, herinneringen na eerste en tweede week, betalingsregeling na drie weken, incasso na weigering | Juiste volgorde; geen gedeeltelijke betaling of incasso voor de gestelde termijn; historische bedragen niet herberekend met aannames | Geautomatiseerd: openstaande facturen, herinneringen en wachttermijn getest; volledige incassoacceptatie nog open |
| T17, Acquisitie en AD21 | Na een maand nabellen; afwijzing vastleggen; opvolglijst opnieuw openen | Geen automatische verdere opvolging na afwijzing; bestaand account niet dupliceren | Geautomatiseerd: MySQL-conversie en definitieve afwijzing getest; handmatige acceptatie nog open |
| T18, Distributie en Productbeschrijving scenario 4 | Tweede afleverpoging mislukt; verkoop belt klant, legt nieuwe leverdatum, dagdeel en toegelichte extra kosten vast | Order blijft niet afgeleverd totdat werkelijk is bezorgd; nieuwe afspraak en kosten worden opgeslagen | Geautomatiseerd: Python en geïsoleerd MySQL geslaagd; klantcontact niet gesimuleerd als werkelijk uitgevoerd |
| T19, EER/schema-migratie | Pas de nieuwe acquisitie- en bezorgstatusmigraties toe op het schema van commit d936cd3; lees bestaande records | De booleans voor afsluiten van acquisitie en de toegezegde korting en de orderstatus zijn aanwezig; bestaande klantgegevens blijven leesbaar | MySQL 8.4-migratietest geslaagd op geïsoleerde testdatabase |

De originele casus verplicht geen automatische leveranciersverzending, individuele medicijnscans of ontvangst van inkomende voorraad. Deze functionaliteit wordt niet als acceptatievoorwaarde toegevoegd.

## Huidig geverifieerd testbewijs, 31 oktober 2026

De onderstaande resultaten zijn daadwerkelijk uitgevoerd op de lokale Laptop-verbinding van Floris test, met Python in een geïsoleerde virtuele omgeving en een afzonderlijke MySQL 8.4-Dockercontainer. Fictieve gegevens zijn gebruikt. Er zijn geen productiegegevens verwerkt.

| Onderdeel | Gecontroleerde versie en omgeving | Uitkomst |
| --- | --- | --- |
| PR #94 Python-regressies | Backendcommit 0cb154b met de samengevoegde review #117 en opvolgende bewijscommit; code/backend, unittest-discovery | **91 van 91 tests geslaagd** |
| MySQL 8.4-integration | run_caseproof_mysql.py op PR #94; schema.sql + fixtures_assessed.sql | **18 benoemde controles geslaagd** voor de vijf verplichte scenario's; zeven procespagina's HTTP 200 |
| Query-resultaten | query-results-assessed.md, gemeten op codecommit 0cb154b | Uitvoer uit echte MySQL SELECTs, inclusief openstaande factuur en leveranciersvolgorde |
| Migraties | run_caseproof_migrations.py: schema uit commit d936cd3, daarna twee casusmigraties | Geslaagd; beide kolommen en de bezorgstatus aanwezig, historische fictieve data behouden |
| Samengestelde branch | Tijdelijke worktree: integration/floris29-case-reviewed plus actuele PR #94-code, één base.html-conflict handmatig opgelost | **128 van 128 Python-tests geslaagd** en de MySQL-integratiecontrole geslaagd; niets naar integratiebranch gepusht |
| PR #104-documentatiebranch | Unit-tests voor bestaande main-code, zonder de nieuwe PR #94-code samen te voegen | Laatste gemeten baseline: 19 van 19; dit is geen bewijs voor de samengestelde applicatie |
| Aanvullende main-gebaseerde reviewbranch | Nieuwe branch op de huidige main na integratie-PR #118 en beide casuscorrectiebranches; MySQL 8.4 op aparte lokale testdatabase | **136 tests uitgevoerd: 135 geslaagd, 1 overgeslagen**; 18 van 18 benoemde MySQL-integratiecontroles geslaagd; zeven procespagina's HTTP 200 |


**Nog niet volledig aangetoond:** echte gebruikersacceptatie op 390 en 1440 pixels met toetsenbordbediening, werkelijke robot-/koerierinteractie, de volledig geïntegreerde online database en de SQL-uitvoer van alle overige schermen. De mobiele distributieweergave is nu wel technisch responsive opgebouwd zonder frontend JavaScript, maar een statische codecontrole vervangt geen handmatige visuele acceptatietest.

**Belangrijk voor GitHub-status:** de oorspronkelijke PR #94 is gesloten omdat de eerdere code via PR #118 in main is opgenomen. PR #104 is gemerged. Nieuwe commits op de oude headbranches veranderen die afgeronde PR's niet. De resterende verbeteringen zijn daarom opnieuw tegen de actuele main getest en in een aparte, niet-gemergede aanvullende reviewbranch samengebracht.

**Samenloop van reviews:** tijdens de controle is PR #117 met aanvullende tests voor onbetaalde facturen en de bezorgvolgorde in PR #94 samengevoegd. De nieuwe casuscontrole behoudt deze wijzigingen, controleert nu expliciet dat een bestaande klant zonder order opvolgbaar blijft, en bewaart beide historische MySQL-uitvoeren met hun eigen herkomst. De 91 en 128 tests en de 18 MySQL-controles zijn uitgevoerd na deze samenvoeging.

**Merge-afhankelijkheid:** bij een proefintegratie van de actuele backend met integration/floris29-case-reviewed ontstond uitsluitend een conflict in code/frontend/templates/base.html door de stijlverwijzingen. In de tijdelijke testworktree is dit opgelost door zowel het extra_styles-block als de picking-bins-stylesheet te behouden. Dit is nog geen merge naar main of naar de gedeelde integratiebranch.

## Evidence and result register

| Check | Result | Evidence or limitation |
|---|---|---|
| Original main Python baseline | 19/19 passed | Reported in earlier repository test run on 2026-10-30 |
| Product catalog branch | 42/42 passed | `test_eer_product_catalog.py` included; no live MySQL check from this result alone |
| Local integrated branch | 62/62 passed | Python unittest on `integration/floris29-review` on 2026-10-30 |
| Direct MySQL 8.4 SQL | Passed selected operations | Disposable sandbox: 27 schema tables, shortage and supplier query, transaction rollbacks |
| Real Python repositories with MySQL | Passed selected operations | Manufacturer, prices, threshold, purchase recording, robot allocation and bin completion |
| Flask pages against MySQL | 14 of 14 HTTP 200 | Smoke test on isolated MySQL; not a full user workflow |
| T03, T05, T06, T12 and full manual acceptance | Not fully verified together | Robot, concurrency and mobile visual/user acceptance still require integrated checks; selected T07-T09 database paths are now tested as above |

Do not treat an HTTP 200, a mock, or a render test as proof of business correctness. Each PR must state whether a case was actually run, with concrete output, or remains a planned test.

## T20-T27. Aanvullende controles op de huidige hoofdbranch

Dit zijn regressiecontroles van expliciete bronprocessen, geen extra
acceptatiecriteria uit userstories. Het actuele resultaat en de gebruikte
commando's staan in main-casus-vijf-rondes-20261031.md.

| Test | Bron en situatie | Verplicht resultaat |
| --- | --- | --- |
| T20 | Huidige processen > Voorraad: nieuw medicijn na directiebesluit | Product pas na expliciete bevestiging opnemen; directe backendaanroep mag niet om formulier heen |
| T21 | Huidige processen > Acquisitie: geen interesse na een maand | Formulier kan de opvolging bevestigend afsluiten, zodat niet opnieuw wordt nagebeld |
| T22 | Huidige processen > Inkoop: leverancier gestopt | Exact één werkende ontkoppelactie; product in assortiment behouden; interne bestellijst afzonderlijk beheren |
| T23 | Huidige processen > Bestellingen en Administratie: gesplitste levering | Kortingsgrens op oorspronkelijke order, korting alleen op werkelijk geleverde aantallen; eersteorderkorting niet vervallen voor later deel van dezelfde order |
| T24 | Huidige processen > Administratie: eerste/tweede herinnering en incasso | Geen dubbele herinneringen; tweede pas minimaal één week na eerste; incasso uitsluitend na bevestigde weigering |
| T25 | Gewenste processen: centraal klantbeheer en statusinformatie | De klantenlijst en bestelstatus lezen rechtstreeks de juiste adressen, contactgegevens, status, leverdag en dagdeel uit MySQL |
| T26 | Distributie en verkoop: ongeldig formulier | Foutieve invoer geeft een gecontroleerde 400 zonder onbedoelde mutatie of serverfout |
| T27 | Productbeschrijving > frontend, werkelijke uitgegeven factuur | De factuurregels zijn bij 390 px in Chrome met toetsenbord bereikbaar zonder horizontale documentoverflow; daarnaast blijven het 768- en 1440-px-scherm bruikbaar |
