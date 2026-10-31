# Visuele controle van het Timaflu-portaal

De frontend in deze branch gebruikt het aangeleverde `code/frontend/DESIGN_SYSTEM.MD`. De toepassing blijft HTML, CSS en Jinja, zoals vereist door de schoolopdracht. Login, demo-rollen en eventuele React-functionaliteit zijn geen onderdeel van deze wijziging.

## Browsercontrole

De geïntegreerde Flask-app is met fictieve gegevens in een aparte MySQL 8.4-testdatabase geopend in Chrome. De controlleroutes en businesslogica zijn niet aangepast.

- 21 beschikbare pagina's of GET-routes;
- 3 schermbreedtes: 390 px, 768 px en 1440 px;
- 63 weergaven met HTTP 200;
- kleuren en de gedeelde stylesheet geladen;
- geen horizontale document-overloop;
- mobiele navigatie via native HTML `details/summary` zonder JavaScript;
- brede tabellen blijven binnen hun eigen horizontaal scrollbare container;
- alle bestaande 67 Python-tests plus 3 regressietests van het designsysteem zijn geslaagd.

Dit is een visuele en technische basiscontrole, **geen bewijs dat elke bedrijfsproceshandeling van de overige open PR's al werkt**. Bij de integratie van nieuwe procesfunctionaliteit moeten de betreffende schermen opnieuw worden gecontroleerd.

## Screenshots

De screenshots zijn gemaakt met verzonnen testproducten en testleveranciers.

| Scherm | Bestand |
|---|---|
| Home, desktop | [home_1440.png](home_1440.png) |
| Home, mobiel | [home_390.png](home_390.png) |
| Voorraad, mobiel | [stock_390.png](stock_390.png) |
| Productcatalogus, mobiel (tabel horizontaal gescrold) | [products_390.png](products_390.png) |
| Orderpicking, mobiel | [order-picking_390.png](order-picking_390.png) |
| Leveringen, mobiel | [deliveries_390.png](deliveries_390.png) |
| Bijbestellen, mobiel | [reorder-selected_390.png](reorder-selected_390.png) |
