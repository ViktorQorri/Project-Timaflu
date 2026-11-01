# Timaflu: aantoonbare casusdekking na herstel

## Bron en afbakening

Toetsingsvolgorde: `Documentation/brightspace/Current-processes.md`,
`Desired-process.md` en de verplichte schoolproducten uit
`Product-description.md`. Activity diagrams en userstories kunnen geen
nieuwe procesregels voorschrijven.

De vijf voorgeschreven backendscenario's worden functioneel uitgevoerd met
MySQL. De overige casusprocessen zijn nu verder doorverbonden tot een
praktisch bedienbare keten, maar een test is geen vervanging voor acceptatie
door echte medewerkers en gekoppelde hardware.

## Aansluiting per bedrijfsproces

| Proces | Werkend en controleerbaar | Nog niet extern aantoonbaar |
| --- | --- | --- |
| Verkoop | Medewerker selecteert klant, medicijnen, aantallen, spoed, dagdeel en datum. Per tekort kiest de klant afzien of later afnemen. Nieuwe, getekende prijsbevestiging met eenmalig token en expliciet klantakkoord. In één transactie worden bestelregels, voorraadreserveringen en ganggebonden robotdeelorders vastgelegd. Bij gewijzigde voorraad/prijs moet de klant opnieuw akkoord geven. | Echte telefonische klanttoestemming kan de software alleen door een medewerker laten bevestigen. |
| Voorraad en inkoop | Fysieke voorraad en reserveringen apart gevolgd. Minimale voorraad, leveranciers op inkoopprijs en handmatig bevestigde inkooporders. Robotafronding boekt feitelijke aantallen per schap af en geeft de bijbehorende reserveringen vrij in dezelfde transactie. | Bestaande papieren inventaris en echte robot/scanner moeten bij ingebruikname overeenkomen; inkomende voorraadontvangst behoort niet tot de casus. |
| Orderpicking en distributie | Robots registreren unieke bakken. Afronding is niet dubbel mogelijk. Afgeronde deelorders kunnen worden verpakt, waarna een levering wordt klaargezet. Toewijzing aan beschikbare koerier na handmatige controle; een eerste en een tweede poging op dezelfde dag. Na tweemaal afwezig blijven de mislukte pogingen bewaard en worden al verpakte regels naar een nieuwe levering op de afgesproken dag verplaatst. | Werkelijke koerier/regiobeschikbaarheid, fysieke verpakking, rollerbaan en handtekening worden door mensen/apparaten gemeld. |
| Administratie | Alleen afgeleverde en ondertekende regels worden wekelijks gefactureerd, met vastgelegde bedragen en adressen. Herinneringen, regeling en incasso volgen de beschreven stappen. Eenmalig met de klant afgesproken herbezorgkosten komen afzonderlijk in de weekfactuur, met onveranderlijke koppeling en controle op dubbele facturering. | Voor extra bezorgkosten noemt de casus geen btw-percentage. Facturatie van die toeslag wordt geweigerd zonder expliciet geconfigureerd, juridisch geverifieerd percentage. |
| Acquisitie | Bezoekregistratie, opvolging na één maand zonder bestelling, klantaccount na toestemming met eersteorderkorting en expliciete beëindiging bij afwijzing. | Telefonisch contact zelf wordt niet opgenomen of geautomatiseerd. |
| Documentatie en frontend | PHP/JS-vrije Jinja-frontend, databasequeryvoorbeelden, bewerkbaar EER op basis van echte MySQL, gegenereerd klassendiagram en responsieve schermontwerpen. | Het oude `eer.mwb` is niet de canonieke definitieve EER; gebruik `eer-mysql-verified.drawio`. |

## Extra bezorgkosten en btw

`Bestelling.extra_bezorgkosten` wordt als **met de klant afgesproken bedrag
inclusief eventuele btw** vastgelegd. De code bepaalt het btw-aandeel pas
wanneer `TIMAFLU_DELIVERY_COST_VAT_PERCENT` expliciet is ingevuld. Zonder
waarde mag een factuur met een bezorgtoeslag niet worden aangemaakt. De
casus geeft geen percentage en daarom bestaat **geen standaardtarief**.

De schemawijziging staat in
`code/database/migrations/2026_11_01_delivery_charges.sql`.
Eerdere facturen en oorspronkelijke bedragen worden niet herberekend.
Elke bezorgtoeslag wordt gekoppeld aan maximaal één vastgelegde factuur.

## Vijfvoudig bewijs

De GitHub Actions-workflow `.github/workflows/timaflu-case-proof.yml`
voert vijf onafhankelijke rondes uit van:

1. Volledige Python-suite inclusief tests tegen geïsoleerde MySQL 8.4;
2. Robotconcurrentie op een apart aangemaakte en verwijderde testdatabase;
3. De vijf verplichte backendscenario's en de upgrade van het oudere schema;
4. De 28 casusschermontwerpen en het UML-testsysteem.

Na de vijf rondes controleert de CI ook exact de gespiegelde SQL, de
gegenereerde backendklassen, werkelijke query-output per scherm en EER
tegen `information_schema`. Zie de actuele PR-status en Actions-log;
een groene eerdere run is geen bewijs voor een latere commit.

De live ketentests zijn te vinden in
`code/backend/test_case_live_order_chain.py` en controleren:
klantakkoord, beschikbaarheid, reservatie, robotafboeking, verzamelbak,
verpakken, koeriersplanning, ondertekende aflevering en weekfactuur,
plus voorraadtekort en herbezorging met kosten.

## Voor inzet buiten de testomgeving

- Echt bedrijfsafzenderadres `TIMAFLU_ADDRESS`, productionele MySQL en
  een vast veilig `SECRET_KEY` ontbreken nog als aangeleverde gegevens.
- Valideer en vul het juiste btw-tarief voor extra bezorgkosten in vóór
  daadwerkelijke facturatie van die kosten.
- Test fysieke robots, scanner, rollerbaan, regionale bezorging,
  medewerkersacceptatie en een beveiligde productieomgeving afzonderlijk.
- De originele opdracht staat backendstubs toe buiten de vijf verplichte
  scenario's. De software wordt daarom niet als volledig commercieel
  product of officieel geaccepteerde productieomgeving beschreven.
