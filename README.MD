# Timaflu

School project: an information system for Timaflu, a wholesaler of medicines that supplies pharmacies. The system supports employees in Timaflu's business processes. We are working on it in a group of 6.

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
## Diagrams with draw.io

We create all diagrams in [draw.io](https://www.drawio.com/) (diagrams.net).

- Save the source files as `.drawio` in the repository so everyone can edit them.
- Also export each diagram as `.png` or `.svg` with the same file name, so it can be viewed directly in documents and on GitHub.
- Use clear file names, for example `activity-sales.drawio` and `activity-sales.png`.
- When making changes, always update both the `.drawio` file and the export so they do not drift apart.
- Use the same names in diagrams as in the other products (traceability).

Work with the draw.io extension in VS Code (`hediet.vscode-drawio`).

## Documentation

| Document | Location |
| --- | --- |
| Collaboration agreements | [Documentation/Conflict-prevention/collaboration-agreements.md](Documentation/Conflict-prevention/collaboration-agreements.md) |
| Software architecture | [Documentation/Architecture/architecture.md](Documentation/Architecture/architecture.md) |
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
- Decisions: at least 4 of the 6 votes

See the [collaboration agreements](Documentation/Conflict-prevention/collaboration-agreements.md) for the full agreements.
