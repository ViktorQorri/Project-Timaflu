# Beoordelingscontrole Timaflu

**Peildatum:** 1 november 2026. **Bron:** toetsmatrijs LU3, module 2 en de originele Timaflu-productbeschrijving. Deze controle onderscheidt aanwezige documenten, technisch uitgevoerde controles en bewijs dat alleen de deelnemers/docent kunnen leveren.

## 1. Vergaderen (20%)

| Subcriterium | Weging | Bevinding en bewijs | Status |
| --- | ---: | --- | --- |
| Agenda | 5% | [Agenda 30 oktober](../Meetings/agenda-2026-10-30.md) geeft thema's, doelen, rollen, plaats en verdeling van 15 minuten. | Aanwezig |
| Notulen | 5% | Er was geen bevestigd notulenverslag in de repository; er is nu een [verificatieblad](../Meetings/notulen-2026-10-30-ter-verificatie.md), **geen** vastgesteld verslag. | Niet aangetoond |
| Rollen en eigen bijdrage tijdens vergadering | 10% | Voorzitter/notulist stonden ingepland, maar voorbereiding en actieve individuele deelname kunnen niet uit een agenda worden bewezen. | Vereist echte beoordeling |

## 2. Conflictpreventie (20%)

| Subcriterium | Weging | Bevinding en bewijs | Status |
| --- | ---: | --- | --- |
| Concrete groepsafspraken | 10% | [Samenwerkingsafspraken v2.0](../Conflict-prevention/collaboration-agreements.md) behandelen organisatie, communicatie, omgangsvormen, besluiten en consequenties. | Aanwezig, groepsgoedkeuring v2.0 nog aantonen |
| Herbeoordeling afspraken in individueel portfolio | 5% | [Evaluatie 28 oktober](../Conflict-prevention/evaluation-2026-10-28.md) met motivering en voorstellen aanwezig. Individuele portfolioverwerking is niet gezien. | Gedeeltelijk |
| Aantoonbare individuele deelname | 5% | [Projectaanpak](projectaanpak.md) toont voorbeeldissues en taken, maar nog geen individuele uren- en bijdrageverantwoording over het hele project. | Niet volledig aangetoond |

## 3. Softwareoplossing (40%)

| Producteis | Controle op actuele main en deze herstelbranch | Status |
| --- | --- | --- |
| Zes casusprocessen | Processen verkoop, inkoop, robotpicking, distributie, administratie/facturatie en acquisitie zijn aanwezig in routes, ontwerpen en usecases. | Structureel aanwezig |
| Geen ontvangst inkomende voorraad | Niet opgenomen als operationeel bedrijfsproces. | Conform afbakening |
| Vijf verplichte Python-scenario's | Kortingen, leverancierprijsvolgorde, openstaande factuur, tweede bezorgpoging en acquisitieopvolging functioneel uitgevoerd met fictieve gegevens. | Geselecteerde controles geslaagd |
| MySQL en EER | `validate_eer_schema.py` controleerde 28 tabellen en overeenstemming met het Workbench-model; een geïsoleerde MySQL 8.4-database was beschikbaar voor de schermquerycontrole. | Technisch gecontroleerd |
| Queries per scherm met echte output | Op geïsoleerde MySQL: **29 medewerkersschermen, 41 queries, 0 mislukte GET-controles**. [Actuele output](../Architecture/query-output-per-screen.md) is nu in het project aanwezig. | Gecontroleerd |
| Backend-DKD | `check_dkd_contract.py`: 29 unieke domeinklassen en hun voorgeschreven methoden/signaturen gecontroleerd. | Gecontroleerd |
| Activity diagrams en schermontwerpen | 28 bron-activity diagrams en 28 statische HTML-ontwerpen; 5 sequence diagrams; 2 usecase-diagrammen. | Aanwezig |
| Beschrijvingen primaire usecases | Word-document bijgewerkt met 28 traceerbare UC-beschrijvingen inclusief tekststappen; oorspronkelijke illustraties behouden. | Bijgewerkt, teamreview vereist |
| HTML/CSS zonder JavaScript | Chrome op breedtes 390, 768 en 1440 px: 29 URLs x 3 breedtes = **87 controles**, zonder scripts, ontbrekende stylesheets of horizontale pagina-overloop. De betalingsherinnering gaf terecht 400 wanneer deze volgens de factuurdatum nog niet verstuurd mocht worden. | Technische browsercontrole geslaagd |
| Backend/frontend/database/ontwerp ZIP's | Vier archieven kunnen uit een schone checkout worden gebouwd, met het actuele querybewijs en het bewerkbare Workbench-EER. | Opleverprocedure hersteld |
| Online MySQL-database | Gecontroleerde database was een wegwerpbare **lokale** MySQL 8.4-container. Een online, met relevante data gevulde einddatabase is hiermee **niet aangetoond**. | Open |
| Handmatige docentacceptatie / echte hardware | Gebruiksvriendelijkheid, feitelijke robots, koeriers en docentfeedback kunnen niet door alleen deze tests worden bewezen. | Open |
| Jinja-templates in HTML/CSS-oplevering | De browser ontvangt HTML/CSS, maar de ingeleverde templates bevatten Jinja-expressies. Laat docent expliciet bevestigen dat dit aan de eis voldoet. | Docentafstemming open |

De 87 browsercontroles bewijzen een responsieve weergave bij de gekozen breedtes; ze zijn **geen** volledig gebruikersonderzoek of uitputtende end-to-end test van iedere POST-actie. Testbestanden in Git zijn eerder op verzoek verwijderd; bovenstaande controles zijn buiten de repository uitgevoerd.

## 4. Reflecteren (20%)

| Subcriterium | Weging | Bevinding | Status |
| --- | ---: | --- | --- |
| Individueel, minimaal drie uiteenlopende STARR-momenten voor beoordeling 'goed' | 10% | [Werkblad](reflectie-werkblad.md) met controleerbare gebeurtenissen en vragen; geen eigen ervaringen ingevuld. | Individueel aan te leveren |
| Groepsreflectiesessie en actiepunten | 10% | De evaluatie en een invulschema zijn aanwezig, maar een werkelijk gehouden sessie en bijdragen zijn niet vastgesteld. | Groep moet uitvoeren en vastleggen |

## Hoogste resterende prioriteiten

1. **Online database voor de einddemo:** host een veilige test-/demo-MySQL, vul relevante fictieve casusdata, test de website tegen deze database en bewijs de bereikbaarheid. Gebruik geen echte medicijnklanten; voeg geen wachtwoorden aan Git toe.
2. **Groepsadministratie en notulen:** vul de werkelijke Clockify-uren, aantoonbare bijdragen per deelproduct en de werkelijk vastgestelde notulen/besluiten aan. Niet gokken.
3. **Portfolio en docentafstemming:** ieder groepslid voltooit drie echte STARR-reflecties; voer de groepsreflectie uit en leg feedback vast. Vraag bevestiging over de Jinja-frontend en toon de vier officiële ZIP's tijdens de eindoplevering.

**Belangrijk:** deze beoordeling is geen toegekend schoolcijfer. De toetsmatrijs toetst behalve documenten ook gedrag tijdens assess­ments. Een geslaagde technische controle vervangt dat niet.