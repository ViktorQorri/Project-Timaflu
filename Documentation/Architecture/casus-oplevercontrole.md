# Casusconformiteit en oplevercontrole (31 oktober 2026)

## Leidende documenten

De beoordelingsopdracht [Product-description.md](../brightspace/Product-description.md)
is leidend voor de vijf verplichte uitgewerkte backendmethoden. De feitelijke
processtappen staan in [Current-processes.md](../brightspace/Current-processes.md)
en [Desired-process.md](../brightspace/Desired-process.md).
Afwijkingen worden niet stilzwijgend aangevuld met fictieve bedrijfsgegevens.

## 1. Wekelijkse facturatie: werkende transactie

De administratie gebruikt het scherm `/invoices/weekly` of het CLI-commando
`flask --app app issue-weekly-invoices --week-start 2026-10-19`.
Dit commando **wordt niet vanzelf ingepland**. Een echte serverbeheerder kan
het in een scheduler op maandag voor de vorige volledige week uitvoeren.

De code kiest per klant daadwerkelijk afgeleverde `Leveringregel`-regels,
gekoppeld aan een `Leverpoging` met `resultaat='afgeleverd'` en
`ontvangst_getekend=TRUE`. De datum komt uit de bijbehorende `Rit`.
Ongetekende, ontbrekende of eerder gefactureerde regels worden uitgesloten.

Binnen één database-transactie per klant:

1. klant vergrendelen; controleren of de week niet eerder is gefactureerd;
2. echte leveringsregels en historische betaalde jaaromzet ophalen;
3. kortingen **per bestelling** berekenen, inclusief maximaal één eerste-orderkorting;
4. factuur met week, factuuradres en bevestigd afzenderadres aanmaken;
5. alle negen definitieve bedragvelden als onveranderbare snapshot vastleggen;
6. de leveringsregels en eventuele eerste-order-markering koppelen;
7. commit; bij elke fout volgt rollback van alle wijzigingen.

Er geldt een unieke index op `(klant_id, week_start)`. Herhaald uitvoeren geeft
geen dubbele factuur. Facturen worden niet per e-mail verzonden: daar is geen
verifieerbare verzendvoorziening of ontvangersproces voor opgeleverd.
Het scherm `/invoices/issued/<id>` toont ook eerder betaalde facturen en de
historisch vastgelegde adressen en bedragen.

## 2. Kortingsinterpretatie

- **Verplichte beoordeling:** de productbeschrijving zegt letterlijk dat de
  eerste bestelling van een klant 10% korting krijgt. Deze expliciete eis
  wordt gevolgd voor alle nieuwe klanten.
- De acquisitiecasus beschrijft diezelfde 10% als incentive nadat een apotheek
  langer dan een maand nog niet heeft besteld. Dit wordt als **dezelfde
  eenmalige eerste-orderkorting** behandeld en niet als nog eens 10% extra.
- Een bestelling boven of gelijk aan € 500 krijgt 5% bestellingskorting.
  Daarna volgt maximaal één eerste-orderkorting en vervolgens de 5%, 10%
  of 15% klantenkorting op basis van de netto betaalde facturen van het
  vorige kalenderjaar. Alleen opgeslagen historische factuurbedragen tellen.
- De factuur bevat uitsluitend werkelijk geleverde aantallen.
  Bij meerdere bestellingen in één week worden de kortingsberekeningen
  per bestelling gedaan en vervolgens opgeteld, niet over de volledige week.

Bij een nieuwe order waarvan een deel pas later wordt geleverd, wordt de
eenmalige eerste-orderkorting alleen op de **eerste gefactureerde levering**
van die order toegepast. Dit voorkomt een tweede 10%-korting in de volgende
week. De rubric zegt niet expliciet hoe te handelen bij gesplitste leveringen;
dit is de gekozen, gedocumenteerde boekingsregel.

## 3. Timaflu-adres, feit versus fictie

Noch de originele casus noch de productbeschrijving bevat een echt
straat- of postadres van Timaflu. De gevraagde factuurlay-out **bevat**
wel een plek voor `Adres Timaflu`. Daarom:

- `TIMAFLU_ADDRESS` in `code/backend/.env` is verplicht voor uitgifte.
- Het adres wordt op het moment van uitgifte als snapshot opgeslagen.
- Bij ontbreken weigert de backend nieuwe facturen met een duidelijke fout.
- Fictieve adressen in de tests zijn consequent gemarkeerd met `TEST`
  en worden niet als echte Timaflu-bedrijfsgegevens opgevoerd.

De feitelijke waarde kan pas worden ingevuld nadat een bevoegde projectgenoot
of de docent een echt adres heeft aangeleverd. **Niet ingevuld = geen uitgifte
in de echte omgeving.**

## 4. Definitieve database en diagrammen

De canonicale EER is [eer-mysql-verified.drawio](eer-mysql-verified.drawio),
met [SVG](eer-mysql-verified.svg) en
[JSON-structuur](eer-mysql-schema.json), gegenereerd uit de
`information_schema` van de **daadwerkelijk uitgevoerde**
MySQL 8.4-testdatabase. Het bestand omvat alle tabellen, kolommen,
primaire sleutels en foreign keys, inclusief `Voorraadreservering`,
`Inkoopfactuur` en de nieuwe weekfactuurvelden.

Het bestaande `eer.mwb` is een **ouder Workbench-ontwerpbestand** en mag niet
meer als de definitieve EER worden ingeleverd zonder dit ontwerp opnieuw uit
de actuele MySQL-database te importeren. De nieuwe .drawio is nu de
aangewezen, bewerkbare bron, de .svg de visuele export.

Het canonicale backendklassendiagram is
[class-diagram-backend.puml](class-diagram-backend.puml), met
[SVG](class-diagram-backend.svg) en [klasse-index](class-index.json).
Het wordt uit de werkelijke Python-klassen en methoden gegenereerd.
De oudere domein-PUML is een procesontwerp en niet de volledige broncode-index.

## 5. Test- en querybewijs

- [query-output-per-screen.md](query-output-per-screen.md): alle 17 GET-schermen/API-
  controlepunten, HTTP-code en echte MySQL-queryuitvoer; statische schermen
  expliciet aangeduid.
- [test_weekly_invoice_mysql.py](../../code/backend/test_weekly_invoice_mysql.py):
  werkelijke MySQL-, Flask- en rollbacktests.
- [generate_weekly_queries.py](../../code/database/generate_weekly_queries.py):
  borgt automatische synchronisatie van repository-SQL met
  [queries.sql](../../code/database/queries.sql).
- [generate_eer.py](../../code/database/generate_eer.py) en
  [generate_backend_uml.py](../../code/database/generate_backend_uml.py):
  reproduceren de diagrammen uit werkende DB en code.
- GitHub Actions:
  [timaflu-case-proof.yml](../../.github/workflows/timaflu-case-proof.yml)
  bouwt op een online runner een geïsoleerde MySQL-service en toetst
  de tests, SQL, EER en het resultaat van de schermqueries.

Een **blijvend publiek bereikbaar gehost MySQL-systeem** is niet aangemaakt:
de opdracht bevat geen geautoriseerde productiehosting of DB-beheerrechten.
De lokale Docker-database en de tijdelijk online GitHub Actions-service
bewijzen wel dat het schema en de applicatie op MySQL kunnen werken.
Een permanent online databaseadres moet bij de definitieve deploy worden
vastgelegd en met de docent worden gedeeld.

## 6. Deploy en migratie

- Op een verse MySQL-database: `code/database/schema.sql`.
- Bestaande database: eerst back-up, vervolgens **eenmalig**
  `code/database/migrations/2026_10_31_weekly_issuance.sql`. Oude facturen
  krijgen geen gefingeerde `week_start` of aangepaste historische bedragen.
- Vul `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
  `SECRET_KEY` en het feitelijke `TIMAFLU_ADDRESS` in, buiten Git.
- Python-dependencies installeren en `python -m unittest discover`
  uitvoeren. Automatische productie-uitgifte alleen na scheduler-configuratie.
