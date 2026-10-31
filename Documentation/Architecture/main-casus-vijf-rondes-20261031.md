# Casuscontrole van main in vijf onafhankelijke rondes

**Datum:** 31 oktober 2026
**Gecontroleerde basis:** ViktorQorri/Project-Timaflu, main op commit 5cd9ef2bb09b9b724e160e5b7b0582636a61380f
**Testcomputer:** Floris test, uitsluitend geïsoleerde lokale MySQL 8.4 met fictieve gegevens
**Resultaat:** de vijf voorgeschreven backendscenario's en de hier genoemde regressies zijn succesvol gecontroleerd. Dit is geen verklaring dat alle bedrijfsprocessen al volledig operationeel zijn.

## Bronnen en beoordelingsvolgorde

1. Documentation/brightspace/Current-processes.md: feitelijke processen voor verkoop, inkoop/voorraad, magazijn, distributie, administratie en acquisitie.
2. Documentation/brightspace/Desired-process.md: de gewenste centrale informatievoorziening, robots, voorraad, orderstatus en distributie.
3. Documentation/brightspace/Product-description.md: de verplichte schoolproducten, de vijf volledig werkende backendscenario's, frontendvoorwaarden, UML, EER en echte MySQL-resultaten.
4. Diagrammen en code moeten overeenkomen met 1 t/m 3. GitHub-userstories mogen geen zelfstandige bedrijfsregels toevoegen.

De productbeschrijving staat toe dat andere backendmethoden nog stubs zijn; dat maakt een ontbrekende complete gebruikersworkflow niet automatisch bewezen. Een ontwerp, een gerenderde pagina en een werkelijk uitgevoerde transactie hebben verschillende bewijskracht.

## Casusdekking per proces

| Proces | Aantoonbaar gerealiseerd in deze audit | Resterende afbakening |
| --- | --- | --- |
| Verkoop | 5%-orderkorting, 10% eersteorderkorting, klantenkorting op betaalde jaaromzet, actuele voorraad- en reserveringsraadpleging, echte klant-/adreslijst en orderstatus uit MySQL | Het volledige telefonisch invoeren, klant laten goedkeuren en atomair opslaan van een nieuwe order met reservering is nog geen werkende portaalworkflow |
| Inkoop en voorraad | Tekorten, handmatige fabrikantvergelijking van goedkoop naar duur, contactgegevens, bevestigde inkooporder, leveranciersrelatie verwijderen, interne bestellijst apart, minimumvoorraad en directiebevestiging bij nieuw assortiment | Werkelijke fysieke voorraadmutaties na robotpicking/uitgifte zijn niet als volledige keten bewezen; voorraadontvangst is expliciet niet voorgeschreven |
| Orderpicking | Ganggebonden robotdeelorders, unieke bakcodes, afrondingsmelding en tests op gelijktijdige opdrachten, overzicht van geregistreerde bakken | Echte robot/scanner/rollerbaan, verpakking en fysieke afboekingen zijn niet met de hardware getest |
| Distributie | Rooster met klantcontact, ondertekende aflevering, tweede poging later op dezelfde dag, na tweemaal afwezig nieuwe datum en vastgelegde extra kosten, verbeterde foutafhandeling | Werkelijke rittoewijzing en koerierapparaten zijn niet end-to-end geaccepteerd; extra bezorgkosten zijn nog niet aantoonbaar meegenomen in de weekfactuur |
| Administratie | Wekelijkse bundelfacturen voor alleen geregistreerd afgeleverde producten, bedragssnapshots, 9% btw en kortingen, idempotentie, betaling, herinneringen, minimaal zeven dagen tussen eerste en tweede, betalingsregeling en incasso na bevestigde weigering | Het echte afzenderadres ontbreekt in de casus; correcte verwerking van extra bezorgkosten inclusief btw-behandeling is niet afgeleid uit de bron |
| Acquisitie | Bezoek vastleggen, opvolging na minstens één maand zonder bestelling, nieuw klantaccount met afgesproken incentive en expliciete afwijzing waarbij verdere opvolging stopt | Geen echte telefonie-/contactintegratie; accountaanmaak en afwijzing zijn expliciete medewerkeracties |

## Herstel in deze verbeterbranch

- **Leveranciersbeheer:** dubbele links en letterlijke ongeldige tekens verwijderd; exact één werkende leverancierontkoppeling met bevestiging, afzonderlijke productverwijdering en afzonderlijke interne-bestellijstactie.
- **Acquisitie:** de al aanwezige serveractie voor definitief afwijzen is nu bereikbaar vanuit het echte scherm en vraagt expliciete bevestiging.
- **Assortiment:** voor nieuwe medicijnen wordt het besluit van de directie handmatig bevestigd, ook bij rechtstreekse backendaanroepen. Dit is geen formeel bevoegdheden- of identiteitsbewijs; daarvoor schrijft de casus geen techniek voor.
- **Weekfacturen:** de € 500-grens wordt getoetst op de oorspronkelijke volledige bestelling, terwijl de korting uitsluitend over daadwerkelijk geleverde regels wordt berekend. Een deel van dezelfde eerste bestelling behoudt de 10%-korting bij latere aflevering; niet-gerelateerde latere orders krijgen die korting niet. Dit is een gedocumenteerde interpretatie van de casus voor gesplitste leveringen, geen aanvullende userstoryregel.
- **Betalingsopvolging:** dubbele herinneringen geweigerd, minimaal één week tussen herinnering 1 en 2 en expliciete weigering van de regeling vereist voordat incasso wordt geregistreerd.
- **Invoervalidatie:** foutieve bezorgdatum, bezorgpoging, leveringsnummer en ongeldige kortingsbedragen geven gecontroleerde HTTP 400-responses in plaats van een ongecontroleerde serverfout.
- **Centrale informatie:** de voorheen statische klantenpagina leest klant, contactpersoon, telefoonnummer en beide adressen uit MySQL; een nieuw read-only orderstatusscherm leest echte bestellingen, leverdatum, dagdeel, spoedindicatie en status.
- **Responsive uitgegeven factuur:** de daadwerkelijke factuurregels staan in een horizontaal scrollbare tabel met toetsenbordfocus; de mobiele documentbreedte blijft binnen de viewport.
- **Bewijs en documentatie:** SQL-voorbeeldqueries synchroon, query-output opnieuw uitgevoerd, backendklassendiagram vernieuwd en LF-instellingen voor reproduceerbare diagrammen vastgezet.

## Vijf volledig herhaalde verificaties

De vijf runs zijn onafhankelijk uitgevoerd op dezelfde inhoudelijke codewijzigingen op Floris test. Elke run omvatte tien groepen en stopte bij een fout.

| Controlegroep | Uitvoering per ronde | Resultaat |
| --- | --- | --- |
| Python-regressies | 155 tests, 144 geslaagd, 11 overgeslagen omdat ze een aparte MySQL-opt-in vereisen | 5 van 5 rondes geslaagd |
| Werkelijke MySQL 8.4 | 10 factuur- en regresstests, 1 robotconcurrentietest, 18 GET-routes en 21 daadwerkelijk uitgevoerde SQL-queries | 5 van 5 rondes geslaagd |
| De vijf schoolscenario's | Werkelijke transacties voor verkoop, inkoop, facturatie, distributie en acquisitie, inclusief zeven werkende procespagina's | 5 van 5 rondes geslaagd |
| Migratie uit bestaand schema | Historische kolommen voor acquisitie en leverstatus met behoud van testdata | 5 van 5 rondes geslaagd |
| Casusontwerpen | 28 schermontwerpen, traceerbare velden, schemareferenties en geen JavaScript | 5 van 5 rondes geslaagd |
| Chrome-viewports | 28 ontwerpen maal 390, 768 en 1440 px: 84 checks, geen documentoverflow | 5 van 5 rondes geslaagd |
| UML | 14 automatische diagramcontroles | 5 van 5 rondes geslaagd |
| Python-klassendiagram | Reproduceerbaar, 59 echte klassen | 5 van 5 rondes geslaagd |
| SQL-synchronisatie | Generatie en controle van de weekfactuurqueries tegen de repositories | 5 van 5 rondes geslaagd |
| Git-integriteit | git diff --check op de wijzigingen | 5 van 5 rondes geslaagd |

Aanvullend is het bewerkbare EER met 28 MySQL-tabellen en 37 foreign-keykolommen vijfmaal daadwerkelijk gecontroleerd. De 18 echt werkende Flask-pagina's en JSON-API zijn daarnaast **vijfmaal op 390, 768 en 1440 px** in Chrome geladen (270 aanvullende HTTP-/viewportcontroles), met alle stijlen en fonts geladen. Hierbij is de echte factuurtabel-overloop ontdekt en hersteld; de JSON-healthendpoint is als JSON en niet als HTML beoordeeld. De onafhankelijke MySQL-tests zijn niet als overgeslagen tests meegerekend; zij zijn daadwerkelijk gestart op de lokale MySQL-testdatabase. Na de controles wordt de tijdelijke databasecontainer verwijderd.

Lokale verifieerbare consolelog op Floris test: C:\Users\Lapto\timaflu_case_audit_5x.log. De log bevat per ronde de tien geslaagde groepen en hun resultaten, zonder productiegegevens.

## Nog niet als volledig casusconform te bewijzen

1. **De gehele telefonische orderketen:** orderregels invoeren, klantakkoord afwachten, bestelling opslaan, voorraad reserveren, robotopdracht genereren en vervolgens fysieke voorraad afboeken zijn niet allemaal via één aantoonbare workflow verbonden. Alleen afzonderlijke componenten en de vijf voorgeschreven backendscenario's zijn getest.
2. **Fysieke magazijnmutaties:** automatische afboeking van daadwerkelijk gepakte/verzonden aantallen en sluitende verschillencontrole ontbreken als volledig aangetoonde keten. Zonder die stap kan een voorraadrapport na echte uitgifte verouderd zijn.
3. **Extra bezorgkosten op factuur:** de casus vereist dat ze bij de bestelling worden vastgelegd en aan de klant worden doorberekend. De registratie bestaat, maar de weekfactuur telt die kosten nog niet aantoonbaar mee. De btw-behandeling van deze kosten wordt niet in de bron gespecificeerd; hier is geen fictief percentage gekozen. Dit is een inhoudelijke restafwijking, geen geslaagde test.
4. **Overige beheerschermen:** klanten kunnen nu read-only worden gevonden, maar volledig wijzigen/verwijderen en algemene directierapportages zijn nog geen volledig werkende processen in deze branch. Buiten de vijf verplichte backendscenario's zijn stubs volgens de productbeschrijving toegestaan.
5. **Opleveromgeving:** het echte Timaflu-afzenderadres, online productie-MySQL, apparaatkoppelingen en feitelijke acceptatie door gebruikers zijn niet beschikbaar. De casus geeft geen straatadres; dit mag niet worden verzonnen. Screenshots en HTTP 200 alleen bewijzen geen fysieke procescorrectheid.
6. **Formele schooloplevering:** individueel projectbewijs, volledige handmatige EER/DKD-beoordeling en toegankelijke toetsenbordtests op echte apparaten vergen menselijke verificatie.

Deze resterende punten moeten expliciet zichtbaar blijven bij de PR-beoordeling. Er is geen uitspraak gedaan dat de gehele applicatie 100% productie- of casusgereed is.

## Reproduceerbare controles

- Backend: python -m unittest discover -p test_*.py vanuit code/backend.
- Verplichte scenario's en migraties: Documentation/Architecture/test-data/run_caseproof_mysql.py en run_caseproof_migrations.py met afzonderlijke, uitsluitend lokale MySQL-configuratie.
- Werkelijke schermoutput: code/database/audit_ui_queries.py, resultaten in Documentation/Architecture/query-output-per-screen.md.
- Klassendiagram: python code/database/generate_backend_uml.py --check.
- SQL: python code/database/generate_weekly_queries.py --check.
- EER: python code/database/generate_eer.py --database timaflu_casus_test_94 --check na het opzetten van de testdatabase.
- Statische schermen: Documentation/Architecture/screens/test_case_screens.py en test_browser_screens.py.
- Extra regressies: code/backend/test_main_case_audit.py en test_weekly_invoice_mysql.py.
- Aanvullende onafhankelijke functionele Chrome-test: vijf runs met 18 endpoints op 390/768/1440 px, uitsluitend met fictieve MySQL-records. De test is lokaal uitgevoerd op Floris test.
- GitHub Actions: .github/workflows/timaflu-case-proof.yml.

**Toetsingsprincipe:** de oorspronkelijke casus en het verplichte productdocument gaan altijd vóór afwijkende GitHub-userstories. Niet-beschreven hardwareprotocollen, rollen, productieadressen en fiscale aannames zijn niet toegevoegd.
