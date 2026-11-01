# Timaflu: controle klassendiagram en Python-implementatie

## Bronnen en toetsingsvolgorde

- `Documentation/brightspace/Current-processes.md` en `Desired-process.md` beschrijven de casus.
- `Documentation/brightspace/Product-description.md` bepaalt welke vijf backendscenario's echt moeten werken. Andere klassen en methoden mogen volgens de opdracht leeg zijn.
- `Documentation/Architecture/uml/src/domain/dkd-timaflu.puml` is het oorspronkelijke domeinklassendiagram.
- `Documentation/Architecture/class-diagram-backend.puml` is uitsluitend de uit code gegenereerde weergave. Alleen die export controleren kan een ontbrekende methode verhullen.

## Aangepast

1. `Product.removeFromInternalReorderList()` was niet aanwezig, ondanks de vermelding in het DKD. De methode zet nu de in-memory interne bestelbaarheid op onwaar en laat `in_assortment` ongemoeid.
2. `ProductRepository` leest de bestaande MySQL-kolom `intern_bestelbaar` nu mee en zet die om in de domeinstatus. De werkelijke persistente wijziging blijft bij de bestaande `SupplierRepository.remove_from_internal_reorder_list()`. Hierdoor ontstaan geen nieuwe of afwijkende SQL-queries in `queries.sql`.
3. `ProductActiveIngredient`, `Supplier` en `SupplierOffer` waren dubbel aanwezig in `domain.case_stubs` en hun gebruikte domeinmodules. De ongebruikte doublures zijn verwijderd. `Supplier.updateDetails()` is in de echte `domain.supplier.Supplier` opgenomen, zoals het DKD vraagt; de applicatie gebruikt voor het aanpassen van leveranciersgegevens de repository.
4. `code/database/check_dkd_contract.py` controleert de oorspronkelijke **29 domeinklassen**, uniciteit van klassedefinities, alle vermelde methoden, het minimale aantal DKD-parameters en de gescheiden status van interne bestellijst en verkoopassortiment. Dit script is onafhankelijk van de uit code gegenereerde UML-export.
5. `class-diagram-backend.puml`, `.svg` en `class-index.json` zijn opnieuw gegenereerd op basis van de daadwerkelijke bijgewerkte backend.

## Reproduceerbare controles op Floris test

Uitgangspunt voor de gerichte herstelbranch: `main` op commit `4e1eaf771474370e2d94c8219fc703d6ee3bee02` (na PR #126 en #129).

- `python code/database/check_dkd_contract.py`: geslaagd, 29 unieke DKD-domeinklassen.
- `python code/database/generate_backend_uml.py --check`: geslaagd, 67 Python-klassen in actuele backend.
- `python code/database/generate_weekly_queries.py --check`: geslaagd.
- `python -m compileall -q code/backend`: geslaagd.
- Historische relevante scenario-tests zijn **tijdelijk en uitsluitend voor deze controle** vanuit een oudere projectversie in de lokale werkmap uitgevoerd, daarna verwijderd. Met 22 testmodules: **185 tests, 169 geslaagd, 16 overgeslagen, 0 fouten**. Die bestanden worden niet teruggebracht in de repository, overeenkomstig PR #126.
- `git diff --check`: geslaagd.

## Wat nog niet afgetekend kan worden

**EER is in bewerking door een ander teamlid.** Het EER of `eer.mwb` wordt in deze PR **niet** gewijzigd en de PR wordt niet gemerged. De bestaande Workbench-export was bij een afzonderlijke vergelijking met `eer-mysql-schema.json` nog vijf velden achter: `Bestelling.aantal_verhuisdozen`, `Inkoopbestelling.besteld_op` en `status_naam`, plus `Koerier.regio` en `extern`. Ook stond `Bestelling.status_naam` in Workbench nog als nullable terwijl de MySQL-snapshot dat niet aangeeft. Na het nieuwe EER-werk moet deze vergelijking opnieuw op de nieuwste `main` worden uitgevoerd; gebruik geen oudere EER-export als definitieve oplevering.

De 16 overgeslagen historische tests zijn hoofdzakelijk databasegebonden. De uitgevoerde mock-/Python-tests zijn dus **geen bewijs** dat alle vijf schoolscenario's tegen een verse MySQL 8.4-instance zijn getest. Echte fysieke robots, transportband, koeriers en productiebeveiliging zijn evenmin geaccepteerd. Omdat PR #126 de eerdere CI- en testsuite bewust heeft verwijderd, worden ze hier niet eigenmachtig hersteld. Voor het inhoudelijke aftekenen zijn een geïsoleerde MySQL-integratietest en een controle van het actuele EER nodig.

## Volgende controle voor merge

- Vergelijk na afronding van het EER-werk het definitieve model **kolom voor kolom** met het werkelijke MySQL-schema.
- Controleer de vijf verplichte scenario's in een geïsoleerde MySQL-testomgeving.
- Laat minimaal één ander groepslid de PR beoordelen, volgens de samenwerkingsafspraken. Merge pas daarna.
