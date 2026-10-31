# Casusverificatie issue #15: minimumvoorraad en leveranciersvergelijking

## Leidende bronnen

- `Documentation/brightspace/Current-processes.md`, sectie Voorraad: fysieke voorraad, handmatig contact met fabrikanten en goedkoopste leverancier.
- `Documentation/brightspace/Desired-process.md`: per medicijn minimumvoorraad bewaken en zichtbare tekorten voor de inkoopmedewerker.
- `Documentation/brightspace/Product-description.md`: bij onvoldoende voorraad een leverancierslijst met goedkoopste eerst, contactpersoon en telefoonnummer; mogelijkheid om leverancier/product te verwijderen in het volledige inkoopproces.
- `Documentation/brightspace/Process-description.md`: traceability tussen eisen, ontwerp, SQL, frontend/backend en testen.
- Activity diagrams `AD03_View_minimum_stock` en `AD02_Reorder_products`; sequence diagram voor niet op voorraad in de afzonderlijke diagram-PR.

## Oplevering en afbakening

| Casusonderdeel | Werking | Bestand |
| --- | --- | --- |
| Minimumvoorraad per medicijn | Instelbare niet-negatieve drempel, transactie met validatie | `stock_service.py`, `stock_repository.py`, `stock_minimums.html` |
| Voorraadtekort | Vergelijkt fysieke voorraad op alle magazijnlocaties met minimum; zonder locatie geldt 0 | `stock_repository.py`, `stock.html` |
| Zichtbare signalering | In het inkoopoverzicht; geen extra mails of achtergrondmeldingen | `stock.html` |
| Productnaam als invoer | Zoekresultaat toont eerst medicijnen met artikelnummer; de medewerker selecteert het juiste product | `supplier_repository.py`, `suppliers.html` |
| Leveranciers per medicijn | Selectie op unieke `product_id`; inkoopprijs oplopend; contactpersoon en telefoonnummer | `supplier_repository.py`, `suppliers.html` |
| Handmatig bestellen | De inkoper neemt zelf contact op; verwerken na bevestiging hoort bij #57/#109 | `routes/purchasing.py` en afzonderlijke PR #109 |

Een zoekterm is geen unieke productidentiteit. Productnamen kunnen in de huidige database dubbel voorkomen. Daarom leidt een handmatige zoekopdracht **direct naar de leverancierslijst bij precies één overeenkomend product**, zoals het verplichte backendscenario verlangt. Bij meerdere overeenkomende medicijnen worden **geen leveranciers of bestelknoppen** getoond totdat de medewerker op basis van artikelnummer het juiste product selecteert. Zo ontstaan geen verkeerde leverancier-productcombinaties. Het inkoopoverzicht linkt rechtstreeks met een unieke `product_id`.

Bij een minimumvoorraad van 0 zijn nooit tekorten zichtbaar voor het betreffende product omdat fysieke voorraad niet negatief is. Dit gedrag wordt duidelijk in de interface uitgelegd; de casus schrijft niet expliciet een minimum van 1 voor. Er worden geen automatische inkoopbestellingen, nieuwe inkoopstatussen of voorraadontvangsten geïntroduceerd.

## Verificatie op Floris test, 31 oktober 2026

- **56 Python-tests geslaagd** na de nieuwste aanpassing.
- **MySQL 8.4 + Flask tegen geïsoleerde testdatabase geslaagd**: 28 statements voor het schema uitgevoerd; twee producten met dezelfde naam, afzonderlijke artikelcodes en prijzen getest.
- Test: meerdere magazijnlocaties optellen, nul magazijnlocaties, uit assortiment verwijderde producten uitsluiten, minimum 0, foutieve drempel weigeren, minimumdrempel opslaan zonder fysieke voorraad aan te passen, leveranciers op product-id en oplopende inkoopprijs, correcte contactgegevens, ongeldige en onbekende product-id.
- Test: een unieke productnaam leidt direct naar de leverancierslijst; bij meerdere overeenkomende producten toont de zoekopdracht ze afzonderlijk zonder leveranciers of bestelknop. Na keuze verschijnen alleen leveranciers van het geselecteerde product.
- `code/database/queries.sql` bevat de schermqueries met voorbeeldwaarden overeenkomstig de repositoryqueries.

## Afhankelijkheden en mergecontrole

- PR #101 levert de productcatalogus en `in_assortiment`-kolom.
- PR #106 levert fabrikantbeheer, prijzen en het verwijderen van koppelingen.
- PR #109 levert de casusconforme handmatig bevestigde inkoopworkflow.
- PR #94 levert onder andere het aparte begrip `intern_bestelbaar`. Bij het combineren moeten die filters zorgvuldig behouden worden.

De PR blijft gericht op `feature/gh13-manage-product-catalog`, niet op `main`. Een volledige integratie van alle afzonderlijke PR's is **niet** door deze verificatie bewezen. Een droge mergecheck tussen #15 en #106 toont conflicts in `routes/purchasing.py` en `queries.sql`; met #94 ook in de leverancierrepository, querydocumentatie en leverancierspagina. Deze conflicten horen bij de gezamenlijke mergecontrole; verander andere branches niet vanuit issue #15.
