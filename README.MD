# Timaflu

School project: an information system for Timaflu, a wholesaler of medicines that supplies pharmacies. The system supports employees in Timaflu's business processes.

## Scope

In scope:

- Sales of products
- Purchasing of products
- Order picking (using robots)
- Distribution
- Administration and invoicing
- Acquisition

Out of scope: receiving new stock.

## Final products

| Product | Technology | Deliverables |
| --- | --- | --- |
| Database with queries | MySQL | EER, document with queries per screen and their output |
| Backend | Python, UML | Class diagram and zip of the code |
| Frontend | HTML, CSS (no libraries or JS) | Zip of the website |

## Design products (conditional)

- Activity diagrams (desired situation of all six processes)
- Use case diagrams (information system and one robot) with use case descriptions
- EER
- Screen designs
- Class diagram
- Sequence diagrams

All products must be traceable to each other: the same entities and naming in diagrams, database and code.

## Software architecture

The frontend (HTML and CSS only) is rendered by a Python backend (Flask) that reads and writes a MySQL database. The robots use a JSON API on the same backend. See [Documentation/Architecture/architecture.md](Documentation/Architecture/architecture.md) for the full description and the diagram.
## Bewerkbare diagrambronnen

Het EER is bewerkbaar in MySQL Workbench (`eer.mwb`) en heeft een actuele SVG-export.
De architectuur gebruikt `architecture.drawio` en de bijbehorende SVG.
Activity diagrams, usecase-diagrammen, DKD en sequence diagrams hebben PlantUML-bronnen
in `Documentation/Architecture/uml/src/` en overeenkomstige exports in `uml/export/`.
Behoud bij wijzigingen de afstemming tussen diagrammen, MySQL en Python.

## Casus en oplevering

De oorspronkelijke casus in `Documentation/brightspace/` is leidend.
De verplichte EER blijft beschikbaar als
[SVG](Documentation/Architecture/eer-mysql-verified.svg) en het bewerkbare
MySQL Workbench-model als `eer.mwb`. Het aanvullende draw.io-exportmodel is
verwijderd. De actuele MySQL-queryuitvoer per scherm staat in
[query-output-per-screen.md](Documentation/Architecture/query-output-per-screen.md).
Dit rapport is op een geÃ¯soleerde MySQL 8.4-database gemeten. Bij wijzigingen aan
schermen of queries moet opnieuw worden gemeten met
`python code/database/audit_ui_queries.py`; dat produceert een bijgewerkt
`deliverables/query-output-per-screen.md`.
Met `python code/build_deliverables.py --output-dir deliverables` zijn de vier
schoolarchieven ook uit een schone checkout te maken. Een opnieuw gemeten
lokaal rapport krijgt voorrang op het ingecheckte bewijs.


## Documentation

| Document | Location |
| --- | --- |
| Collaboration agreements | [Documentation/Conflict-prevention/collaboration-agreements.md](Documentation/Conflict-prevention/collaboration-agreements.md) |
| Projectaanpak en taakverdeling | [Documentation/Projectbeheer/projectaanpak.md](Documentation/Projectbeheer/projectaanpak.md) |
| Controle schoolcriteria | [Documentation/Projectbeheer/beoordelingscontrole.md](Documentation/Projectbeheer/beoordelingscontrole.md) |
| Reflectiewerkblad | [Documentation/Projectbeheer/reflectie-werkblad.md](Documentation/Projectbeheer/reflectie-werkblad.md) |
| Notulen ter verificatie | [Documentation/Meetings/notulen-2026-10-30-ter-verificatie.md](Documentation/Meetings/notulen-2026-10-30-ter-verificatie.md) |
| Software architecture | [Documentation/Architecture/architecture.md](Documentation/Architecture/architecture.md) |
| Databasequeries en echte output | [Queryrapport](Documentation/Architecture/query-output-per-screen.md), opgenomen in `timaflu-database-en-queries.zip` |
| Schermontwerpen en traceability | [Documentation/Architecture/screens/README.md](Documentation/Architecture/screens/README.md) |
| API-specificatie | [Documentation/Architecture/api-specification.md](Documentation/Architecture/api-specification.md) |
| Domain class diagram (PlantUML), sources and multiplicities | [DKD (PlantUML)](Documentation/Architecture/uml/src/domain/dkd-timaflu.puml) |
| Product description | [Documentation/brightspace/Product-description.md](Documentation/brightspace/Product-description.md) |
| Process description | [Documentation/brightspace/Process-description.md](Documentation/brightspace/Process-description.md) |
| Current processes | [Documentation/brightspace/Current-processes.md](Documentation/brightspace/Current-processes.md) |
| Desired process | [Documentation/brightspace/Desired-process.md](Documentation/brightspace/Desired-process.md) |
| Differences current vs. desired | [Documentation/brightspace/Differences-current-vs-desired.md](Documentation/brightspace/Differences-current-vs-desired.md) |

## Working agreements in brief

- Planning and tasks: GitHub Project (leading planning)
- Code and files: this repository, one branch per ticket, changes via pull request
- Every pull request is reviewed by at least 1 other group member before it is merged
- Communication: WhatsApp for short and urgent messages, Discord for substantive discussion
- Decisions: 3 of the 5 votes under current collaboration agreements v2.0

See the [collaboration agreements](Documentation/Conflict-prevention/collaboration-agreements.md) for the full agreements.
