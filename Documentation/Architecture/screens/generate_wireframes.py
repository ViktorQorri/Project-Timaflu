"""Reproduceerbare HTML/CSS-schermontwerpen voor de 28 Timaflu-activities.

Enige databron voor schermvelden, acties, inhoud en procesgroepen:
screen_specs.py. Schermtoestanden: screen_states.py.
De generator voegt geen eigen bedrijfsregels toe.
"""
from html import escape
from pathlib import Path

from case_render import render
from screen_specs import PROCESS_GROUPS, SCREENS, TITLES, CASE_SOURCES, SCREEN_CASE_KEYS
from screen_states import SCREEN_STATES

ARCHITECTURE = Path(__file__).resolve().parents[1]
SOURCE = ARCHITECTURE / "uml" / "src" / "activity_diagrams"
DEST = Path(__file__).resolve().parent


def group_for(number):
    return next(group for group, numbers in PROCESS_GROUPS.items()
                if number in numbers)


def wrap(title, content):
    title = escape(title)
    return f"""<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Timaflu</title>
<link rel="stylesheet" href="wireframes.css">
</head>
<body><div class="page">
<header class="top">
<a href="index.html" class="brand">tima<span>flu</span></a>
<nav class="breadcrumbs" aria-label="Schermontwerpen"><a href="index.html">Alle schermen</a></nav>
</header>
{content}
<footer>Schermontwerp &bull; Timaflu &bull; Gebaseerd op de bestaande casus en activity diagrams</footer>
</div></body></html>"""


def make_readme(items):
    lines = [
        "# Timaflu schermontwerpen",
        "",
        "Voor elk van de 28 bestaande activity diagrams is minimaal één "
        "statisch HTML/CSS-schermontwerp beschikbaar. De ontwerpen tonen "
        "casusgebonden gegevens, acties, resultaatkolommen en afwijkende situaties.",
        "De belangrijkste beslismomenten hebben daarnaast afzonderlijke "
        "zichtbare schermtoestanden; dit zijn géén werkende backendfuncties.",
        "",
        "## Herleidbaarheid",
        "",
        "| Proces | Bronnen uit de casus | Activity diagram | Schermontwerp |",
        "|---|---|---|---|",
    ]
    for number, group, filename in items:
        stem = filename.removesuffix(".html")
        sources = ", ".join(
            f"[{CASE_SOURCES[key][0]}]({CASE_SOURCES[key][1]})"
            for key in SCREEN_CASE_KEYS[number]
        )
        lines.append(
            f"| {group} | {sources} "
            f"| [AD{number:02d}](../uml/src/activity_diagrams/{stem}.puml)"
            f" | [Ontwerp]({filename}) |"
        )
    lines += [
        "",
        "## Uitgangspunten uit de schoolcasus",
        "",
        "- Telefonische verkoop en telefonische inkoop blijven bestaan.",
        "- Geen fictieve klantgegevens, bedragen, leverancierprijzen of extra gebruikersrollen.",
        "- De bestel- en klantenkorting en de factuurspecificatie worden getoond "
        "zoals beschreven in Product-description.md.",
        "- Bij AD02 zijn het verwijderen van een leverancierskoppeling, "
        "het verwijderen van een product en het verwijderen uit de interne "
        "bestellijst aparte handelingen.",
        "- Orderpicking door robots en de jaarafsluiting zijn read-only "
        "procesoverzichten, geen handmatige invoerschermen.",
        "- Bij levering staan digitale ondertekening en bij een mislukte "
        "levering beide bezorgpogingen als schermtoestanden uitgewerkt.",
        "- Alle knoppen en invoervelden in deze ontwerpbijlagen zijn uitgeschakeld.",
        "- PR #114 behandelt de toepassing van de huisstijl op de werkende "
        "Flask/Jinja-frontend; deze ontwerpen vervangen die functionaliteit niet.",
        "",
        "## Reproduceren en controleren",
        "",
        "- screen_specs.py: één bron voor 28 titels, groepen, velden, acties en tabellen.",
        "- screen_states.py: casusgebonden uitzonderingssituaties als schermvarianten.",
        "- case_render.py: herbruikbare HTML-uitvoer, factuurvoorbeeld en ontwerpvarianten.",
        "- python generate_wireframes.py: vernieuwt de 28 HTML-bestanden, index en deze README.",
        "- python test_case_screens.py: controleert bronlinks, verplichte inhoud "
        "en semantiek van de 28 ontwerpen.",
        "- python test_browser_screens.py: controleert 28 schermen op 390, 768 en 1440 px.",
        "- In previews/ staan screenshots van belangrijke casusschermen op 390 en 1440 px: AD02, AD05, AD09, AD12, AD16, AD23 en AD27.",
        "- Geen JavaScript, React, nieuwe bedrijfsstatussen of fictieve gegevens.",
        "",
        "## Brondocumenten",
        "",
        "- [Casuscontrole en voorrangsregels](CASE_TRACEABILITY.md)",
        "- Documentation/brightspace/Product-description.md",
        "- Documentation/brightspace/Current-processes.md",
        "- Documentation/brightspace/Desired-process.md",
        "- De 28 PlantUML activity diagrams in ../uml/src/activity_diagrams/.",
    ]
    return "\n".join(lines) + "\n"


def generate():
    diagrams = sorted(SOURCE.glob("AD??_*.puml"))
    assert len(diagrams) == len(SCREENS) == 28
    assert all(number in SCREENS for number in SCREEN_STATES)
    items = []
    for diagram in diagrams:
        number = int(diagram.stem[2:4])
        source = diagram.read_text(encoding="utf-8-sig")
        assert "@startuml" in source and "@enduml" in source
        filename = diagram.stem + ".html"
        content = render(number, diagram.stem, TITLES[number],
                         group_for(number), wrap)
        (DEST / filename).write_text(content, encoding="utf-8")
        items.append((number, group_for(number), filename))
    assert [item[0] for item in items] == list(range(1, 29))
    cards = "\n".join(
        f'<a class="index-link" href="{escape(filename)}">'
        f'<small>{escape(group)} &middot; AD{number:02d}</small>'
        f'{escape(TITLES[number])}</a>'
        for number, group, filename in items
    )
    index = (
        '<section class="hero"><span class="overline">Ontwerpdocumentatie</span>'
        '<h1>Timaflu: 28 schermontwerpen</h1>'
        '<p>Per activity diagram zijn de relevante velden, handelingen, '
        'procesuitkomsten en waar nodig afzonderlijke schermtoestanden ontworpen. '
        'Alle bediening is uitgeschakeld.</p></section>'
        f'<main class="index-grid" id="main">{cards}</main>'
    )
    (DEST / "index.html").write_text(wrap("Schermontwerpen", index),
                                     encoding="utf-8")
    (DEST / "README.md").write_text(make_readme(items), encoding="utf-8")
    print(f"Generated {len(items)} static HTML screen designs from the case specs")


if __name__ == "__main__":
    generate()
