# Timaflu, visuele controle van de geïntegreerde casus

De schermen volgen `code/frontend/DESIGN_SYSTEM.MD` op basis van Flask/Jinja, HTML en CSS, zonder JavaScript. De businesslogica en routes voor de vijf verplichte scenario's blijven behouden.

## Verificatie op Floris test

- 21 bestaande GET-routes met echte, **fictieve** testgegevens in een geïsoleerde MySQL 8.4-database.
- 3 schermafmetingen: 390 px (mobiel), 768 px (tablet) en 1440 px (desktop).
- **63 van 63 browsercontroles geslaagd**: HTTP 200, gedeelde stylesheet actief, geen horizontale pagina-overloop, mobiele navigatie opent en geen scripts aanwezig.
- **110 van 110 Python-tests geslaagd** op de gecombineerde functionele ontwerpbranch.
- Gedeelde vormen voor de productcatalogus, voorraad, orderpicking, bezorging, facturen en acquisitie.
- De functionele formulieren voor tweede bezorgpoging, betalingsopvolging en acquisitie zijn behouden uit de backendscenario's.
- 28 afzonderlijke, niet-interactieve schermontwerpen horen bij PR #103. Dat zijn opleverschetsen, niet een tweede applicatie.
- De sequence diagrams uit PR #93 zijn **Engelstalig**; dit wijzigt alleen de taal van de portaalinterface niet.

De browsercontroles tonen de weergave. Ze vervangen geen volledige integratietests van alle zakelijke handelingen.

## Screenshots

De screenshots zijn nieuw vastgelegd nadat de functionele schermen met het design zijn geïntegreerd. Alle gegevens zijn fictief.

| Scherm | Desktop (1440 px) | Mobiel (390 px) |
|---|---|---|
| Home | [home desktop](home_case_1440.png) | [home mobiel](home_case_390.png) |
| Productcatalogus | [products desktop](products_case_1440.png) | [products mobiel](products_case_390.png) |
| Voorraad | [stock desktop](stock_case_1440.png) | [stock mobiel](stock_case_390.png) |
| Medicijnen bijbestellen | [reorder-selected desktop](reorder-selected_case_1440.png) | [reorder-selected mobiel](reorder-selected_case_390.png) |
| Orderpicking en verzamelbakken | [picking desktop](picking_case_1440.png) | [picking mobiel](picking_case_390.png) |
| Bezorgrooster en tweede poging | [deliveries desktop](deliveries_case_1440.png) | [deliveries mobiel](deliveries_case_390.png) |
| Factuur en betalingsopvolging | [invoices desktop](invoices_case_1440.png) | [invoices mobiel](invoices_case_390.png) |
| Acquisitiebezoek en opvolging | [acquisition desktop](acquisition_case_1440.png) | [acquisition mobiel](acquisition_case_390.png) |
