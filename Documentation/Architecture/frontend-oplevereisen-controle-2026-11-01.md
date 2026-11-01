# Controle frontendoplevereisen Timaflu (1 november 2026)

## Beoordelingskader
Bron: `Documentation/brightspace/Product-description.md`. De opdracht eist HTML/CSS zonder JavaScript of frontendlibraries, desktopgebruik voor zes bedrijfsprocessen, mobiele bruikbaarheid van orderpicking en distributie en een online database met voldoende relevante gegevens.

## Resultaten op de laatst onderzochte main (6415bb4)

| Eis | Oordeel | Bewijs en beperking |
| --- | --- | --- |
| HTML/CSS volgens huidige standaarden, zonder JS of frontendlibraries | Aannemelijk, niet formeel gevalideerd | `code/frontend/templates/base.html` gebruikt HTML5, `lang=nl`, viewport en CSS-bestanden. De eerder vastgelegde Chrome-run rapporteert geen JavaScript. Niet onafhankelijk gevalideerd met een HTML/CSS-validator. |
| Zes processen bruikbaar op desktop | Gedeeltelijk aangetoond | De bestaande route-inventaris en browsercontrole meten 30 GET-verzoeken op 1440 px. Een succesvolle GET is geen bewijs dat elke formulieractie of volledige procesgang werkt. Zie `Documentation/Architecture/casus-keten-en-eindcontrole-2026-11-01.md`. |
| Orderpicking en distributie mobiel | Gedeeltelijk aangetoond | De eerdere Chrome-run rapporteert schermcontroles op 390 en 768 px zonder horizontale documentoverflow. `code/frontend/static/css/operations.css` bevat mobiele mediaqueries voor de distributieformulieren. Echte touchbediening, leesbaarheid en complete mobiele proceshandelingen moeten apart worden geaccepteerd. |
| Voldoende data om de werking te beoordelen | Gedeeltelijk aangetoond | `code/database/audit_ui_queries.py` en `Documentation/Architecture/query-output-per-screen.md` tonen reproduceerbare fictieve gegevens, SQL en uitvoer per scherm. Dit bewijst testdatadekking, niet dat een online beoordelingsdatabase bereikbaar is. |

## Geconstateerde regressie en herstel
De CI-run voor `6415bb4` faalde op `test_eer_model_contains_purchase_tracking_columns`: het ingeleverde MySQL Workbench-bestand `eer.mwb` miste bij `inkoopbestelling` de velden `besteld_op` (DATETIME NULL) en `status_naam` (VARCHAR(30) NULL). De branch voegt alleen deze ontbrekende modelkolommen toe en laat database- en applicatiegedrag ongewijzigd. De drie tests in `test_purchase_order_tracking.py` zijn lokaal geslaagd na de correctie.

## Nog te bevestigen voor een definitieve beoordeling
1. Succesvolle GitHub Actions-run op de definitieve PR-commit.
2. Visuele en functionele acceptatie van de echte Flask-schermen op desktop en mobiel, met speciale aandacht voor orderpicking en distributie.
3. Bereikbare, afgeschermde online MySQL-beoordelingsomgeving met representatieve fictieve data. Geen productiedata of credentials in GitHub plaatsen.

De historische schermtestresultaten zijn indicatief en gelden niet automatisch voor latere commits. Een verklaring van volledige conformiteit zou op dit moment verder gaan dan het beschikbare bewijs.
