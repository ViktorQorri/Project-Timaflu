# LU3: controle van software en bewijsstukken

**Peildatum:** 1 november 2026
**Gecontroleerde basisversie:** `9fde4f8` op `main`
**Doel:** aantonen wat daadwerkelijk gecontroleerd is en wat nog apart moet worden ingeleverd. Dit document is geen automatische toekenning van een beoordeling.

## Verplichte technische onderdelen

| Onderdeel | Status | Verifieerbaar bewijs |
|---|---|---|
| Database en EER | Geslaagd bij structurele controle | `python code/database/validate_eer_schema.py`: 28 SQL-tabellen komen overeen met `eer.mwb` |
| Usecasebeschrijvingen en activity diagrams | Geactualiseerd en visueel gecontroleerd | 28 usecasebeschrijvingen met 28 bijbehorende, actuele SVG-diagrammen in het Word-document; inhoudstafel bijgewerkt |
| DKD en Python | Geslaagd bij structurele controle | `python code/database/check_dkd_contract.py`: 29 unieke domeinklassen met voorgeschreven methoden en signatures |
| MySQL-queries per scherm | Geslaagd op geïsoleerde testdatabase | `python code/database/audit_ui_queries.py`: 29 schermen, 44 werkelijk uitgevoerde SQL-queries, 0 mislukte requests |
| Verkoop en kortingsberekening (SD01) | Geslaagd met echte MySQL-records | Eerste order: € 600,00 excl. btw, € 654,00 incl. btw, opeenvolgende kortingsstappen, eindtotaal € 531,21; offerte toont de kortingsregels |
| Inkoop bij ontbrekende voorraad (SD02) | Geslaagd met echte MySQL-records | Drie leveranciers op oplopende inkoopprijs, inclusief contactpersoon en telefoon; leveranciersoverzicht via Flask |
| Onbetaalde factuur / facturatie (SD03) | Factuurweergave geslaagd met MySQL | Opgeslagen weekfactuur met 9% btw, kortingsstappen en geleverde regels daadwerkelijk uit MySQL gerenderd. Volledige herinnering/incassoketen vraagt aanvullende demonstratie |
| Klant niet thuis (SD04) | Geslaagd met echte MySQL-mutaties | Na eerste mislukking wordt tweede poging op dezelfde dag ingepland; tweede mislukking wordt geregistreerd |
| Potentiële klant zonder bestelling (SD05) | Geslaagd met echte MySQL-mutaties | Prospect en bezoek vastgelegd; opvolging na kalendermaand; afwijzing en klantconversie met eenmalige korting vastgelegd |
| HTML/CSS zonder JavaScript | Structureel gecontroleerd | Flask/Jinja-templates en stylesheets, geen client-side JavaScript aangetroffen |
| Responsive orderpicking en distributie | Geslaagd via echte browser | 116 browsercontroles op 360, 390, 768 en 1440 px, met 0 fouten en 0 waarschuwingen. Breakpoints in `operations.css`, `deliveries.css` en `ui-system.css` |
| Online bereikbare database | Niet vastgesteld | De geïsoleerde localhost-MySQL-test bewijst niet dat de vereiste database online en gevuld is |
| Werkende fysieke magazijnrobots | Niet vastgesteld | De robot-API is aanwezig, maar fysieke robotcommunicatie is niet getest |

De MySQL-controle en alle vijf verplichte backendscenario-controles zijn uitgevoerd in een **tijdelijke Docker-container met MySQL 8.4**, uitsluitend op `127.0.0.1` met fictieve fixturegegevens. Die container is na de controle gestopt. Er is geen productie- of klantdatabase gewijzigd.

De query-uitvoer is lokaal gegenereerd in `deliverables/query-output-per-screen.md`. Dit bestand blijft overeenkomstig de repositoryafspraken buiten Git en hoort pas **bij de eindoplevering** in het databasepakket. De vier oplever-ZIP's worden nu niet gegenereerd.

### Opnieuw controleren bij de oplevering

1. Neem de definitieve `main`-versie en controleer `eer.mwb`, `schema.sql`, `queries.sql` en de backend.
2. Draai `code/database/audit_ui_queries.py` met de expliciete beveiligingsvariabelen op een **uitsluitend hiervoor bestemde lokale MySQL-testdatabase**. Het script verwijdert en maakt alleen zijn vaste testdatabase `timaflu_casus_test_94` opnieuw aan; voer het nooit tegen een bestaande werk- of productiedatabase uit.
3. Inspecteer het rapport, demonstreer de vijf verplichte scenario's ook tijdens het assessment en toon de vereiste online testdatabase aan.
4. Maak pas op het door de projectgroep gekozen oplevermoment de gevraagde backend-, frontend-, database- en ontwerp-ZIP's met `code/build_deliverables.py`.

## Toetsmatrijs LU3, module 2

| Criterium | Gewicht | Aangetoond / nog te doen |
|---|---:|---|
| Vergaderen: agenda | 5% | `Documentation/Meetings/agenda-2026-10-30.md` aanwezig |
| Vergaderen: notulen | 5% | Alleen invulsjabloon; werkelijke notulen en acties moeten uit een echte vergadering worden aangeleverd |
| Vergaderen: individuele rol | 10% | Niet afleidbaar uit broncode; bewijs in persoonlijk portfolio of assessment |
| Conflictpreventie: afspraken | 10% | `collaboration-agreements.md` bevat de vijf verplichte thema's |
| Conflictpreventie: herbeoordeling | 5% | Evaluatie 28 oktober is als voorbereiding vastgelegd; definitieve groepsbesluiten nog aantonen |
| Conflictpreventie: deelname | 5% | Individuele bijdragen met datum, rol en resultaat in persoonlijk portfolio |
| Softwareoplossing | 40% | Code en vijf MySQL-scenario's gecontroleerd; online database, queryoplevering en demonstratie afronden |
| Individuele reflectie | 10% | Minimaal drie uiteenlopende STARR-/Korthagenmomenten met passende acties voor de beoordeling Goed |
| Groepsreflectie | 10% | Werkelijke reflectiesessie en concrete groepacties aantonen |

**Knock-outvoorwaarde:** de vier SLB-opdrachten (*Terugblik op eerste resultaten*, *Bezoek aan stagiair*, *Intervisie*, *Van compliment tot kracht*) moeten afzonderlijk voldaan zijn. De repository kan dit niet aantonen.

### Bewijs verzamelen zonder fictieve uitkomsten

- [Invuldocument voor de vergadernotulen](../Meetings/notulen-2026-10-30-invuldocument.md). Vervang ontbrekende velden uitsluitend door echte verslagen of schriftelijk bevestigde groepsbesluiten.
- [Individuele portfolio- en reflectiechecklist](portfolio-en-reflectiechecklist.md). Persoonlijke reflecties en omstandigheden horen niet in een openbare repository.
- Bij besluiten over de groepsgrootte, stemverhouding, reviewer of taakverdeling zijn de **actuele, door de groep bevestigde afspraken** leidend; verander ze niet op basis van aannames.
