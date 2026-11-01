# Herstel testtraceability - 1 november 2026

## Doel
Herstel van historische tests en reproduceerbare SQL-testbewijzen die op main ontbraken. Geen productiecode gewijzigd.

## Herkomst
- Basis: origin/main op b1d91fb7fbf6df0ba71531e7cc03f7c5f6e71848.
- Herstelbron: commit 12b5dbe33354abf459b8e2dcdaa681a8221dbd3d (PR #94).
- Teruggezet: 19 Python-testbestanden onder code/backend en 5 SQL-fixture/uitvoerbestanden onder Documentation/Architecture/test-data.
- De historische tests zijn zonder inhoudelijke wijzigingen teruggezet; aanpassing aan de huidige code is vervolgwerk.

## Validatie na herstel
- python -m pytest code/backend --collect-only -q: 78 tests verzameld, exitcode 0.
- python -m pytest code/backend -q: 56 geslaagd, 22 mislukt, 14 subtests geslaagd, exitcode 1.
- De mislukkingen omvatten gewijzigde routes, schermcontracten, inkoopbevestiging, factuursnapshots en proceslogica.
- Deze commit is een traceability-herstel, geen bewijs dat de huidige software alle tests haalt.

## Vervolg
Koppel historische testcases aan de actuele requirements/usecases; beoordeel per mislukking of de implementatie of de verwachting moet worden aangepast. Bewaar oorspronkelijke tests en testoutput in Git-history.
