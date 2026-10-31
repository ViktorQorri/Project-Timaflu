"""Casusgerichte regressiecontrole van de 28 statische schermontwerpen."""
from html.parser import HTMLParser
from pathlib import Path

from screen_specs import SCREENS, TITLES, PROCESS_GROUPS, CASE_SOURCES, SCREEN_CASE_KEYS
from screen_states import SCREEN_STATES

ROOT = Path(__file__).resolve().parent
ARCHITECTURE = ROOT.parent


class Inspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.labels = []
        self.buttons = []
        self.tables = 0
        self.links = []
        self.states = 0
        self.scripts = 0
        self.violations = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if "id" in data:
            if data["id"] in self.ids:
                self.violations.append(f"Dubbel id: {data['id']}")
            self.ids.add(data["id"])
        if tag == "label":
            self.labels.append(data.get("for"))
        if tag in ("button", "input", "select", "textarea"):
            if "disabled" not in data:
                self.violations.append(f"Actieve control: {tag}")
        if tag == "button":
            self.buttons.append(data)
        if tag == "table":
            self.tables += 1
        if tag == "script":
            self.scripts += 1
        if tag == "a" and "href" in data:
            self.links.append(data["href"])
        if tag == "article" and "data-state-variant" in data:
            self.states += 1


def check():
    diagrams = sorted((ARCHITECTURE / "uml/src/activity_diagrams").glob("AD??_*.puml"))
    pages = sorted(ROOT.glob("AD??_*.html"))
    assert len(diagrams) == len(pages) == 28
    assert len(SCREENS) == len(TITLES) == 28
    assert sorted(n for numbers in PROCESS_GROUPS.values() for n in numbers) == list(range(1, 29))

    for number in range(1, 29):
        path = next(ROOT.glob(f"AD{number:02}_*.html"))
        source = path.read_text(encoding="utf-8")
        p = Inspector()
        p.feed(source)
        assert not p.violations, (path.name, p.violations)
        assert p.scripts == 0
        assert all(ref in p.ids for ref in p.labels), path.name
        assert "<main" in source and "<h1>" in source
        assert "scenario-panel" in source
        assert 'href="../uml/src/activity_diagrams/' in source
        assert source.count('class="scenario"') == len(SCREENS[number]["variants"])
        assert p.states == len(SCREEN_STATES.get(number, [])), (number, p.states)
        assert p.tables == (2 if number in (16, 27) else 1), (number, p.tables)
        assert len(p.buttons) >= len(SCREENS[number]["actions"])
        if SCREENS[number]["mode"] != "human":
            assert len(p.buttons) == 0, number
        for key in SCREEN_CASE_KEYS[number]:
            assert CASE_SOURCES[key][1] in p.links, (path.name, key)
        for link in p.links:
            if not link.startswith(("http:", "https:", "#")):
                path_without_fragment = link.split("#", 1)[0]
                assert (ROOT / path_without_fragment).resolve().exists(), (path.name, link)
        assert "executed on device:" not in source
        if p.states:
            assert 'class="state-grid"' in source

    a2 = next(ROOT.glob("AD02_*.html")).read_text(encoding="utf-8")
    for required in (
        "Inkoopprijs", "Contactpersoon", "Telefoonnummer",
        "Leverancier van dit medicijn verwijderen",
        "Medicijn verwijderen", "Uit interne bestellijst verwijderen",
        "Fabrikant gekoppeld aan dit medicijn",
    ):
        assert required in a2, required

    a5 = next(ROOT.glob("AD05_*.html")).read_text(encoding="utf-8")
    for required in (
        "Klant met betalingsblokkade", "Voorraad gewijzigd bij opslaan",
        "Totaalbedrag voor klantakkoord", "Voorlopige order annuleren",
        "Afleveradres uit klantgegevens", "Factuuradres uit klantgegevens",
        "Eenmalige korting", "Besteldatum", "Spoedbestelling",
        "Minimale bestelhoeveelheid van artikel",
        "Ontbrekend medicijn blijkt bij verzamelen",
    ):
        assert required in a5, required

    a6 = next(ROOT.glob("AD06_*.html")).read_text(encoding="utf-8")
    assert all(status in a6 for status in (
        "wordt verzameld", "verstuurd", "backorder", "afgeleverd"
    ))

    a9 = next(ROOT.glob("AD09_*.html")).read_text(encoding="utf-8")
    assert "Adreslabel bevat klantnaam en afleveradres" in a9
    assert "Adreslabel bevat klantnaam, afleveradres en telefoonnummer" not in a9
    assert "Spoedindicatie van order" in a9

    a23 = next(ROOT.glob("AD23_*.html")).read_text(encoding="utf-8")
    assert "Medicijn op meerdere locaties" in a23

    a16 = next(ROOT.glob("AD16_*.html")).read_text(encoding="utf-8")
    for required in (
        "Datum", "Factuurnummer", "Adres Timaflu", "Adres klant",
        "Aantal", "Prijs per eenheid", "Regeltotaal",
        "Totaal excl btw", "9% btw", "Totaal incl btw",
        "Bestellingskorting", "Totaal incl bestellingskorting",
        "Eenmalige korting", "Totaal incl eenmalige korting",
        "Klantenkorting", "Totaal incl klantenkorting",
    ):
        assert required in a16, required
    assert a16.index("Totaal excl btw") < a16.index("9% btw") < a16.index("Totaal incl btw")
    assert a16.index("Bestellingskorting") < a16.index("Totaal incl bestellingskorting")

    a12 = next(ROOT.glob("AD12_*.html")).read_text(encoding="utf-8")
    assert "signature-placeholder" in a12
    assert "Ontvangst bevestigd" in a12
    assert "Klant niet aanwezig" in a12

    a27 = next(ROOT.glob("AD27_*.html")).read_text(encoding="utf-8")
    for required in (
        "Bezorgrooster en tweede poging", "Ritdatum",
        "Contactpersoon", "Telefoonnummer", "Afleveradres",
        "Tweede poging dezelfde dag", "Ook tweede poging mislukt",
        "Extra bezorgkosten", "Koerier: eerste en tweede bezorgpoging",
        "Verkoop: afspraak na twee mislukte pogingen",
        "Wordt uit de klantgegevens geladen",
    ):
        assert required in a27, required

    a18 = next(ROOT.glob("AD18_*.html")).read_text(encoding="utf-8")
    assert "Tweede herinnering" in a18 and "drie weken" in a18

    a24 = next(ROOT.glob("AD24_*.html")).read_text(encoding="utf-8")
    for required in ("Werkzame stoffen", "Bestelcode", "Prijs per grootverpakking",
                     "Verpakkingssoort", "Detailverpakkingen per grootverpakking",
                     "Korte omschrijving", "Lange omschrijving", "Minimale bestelhoeveelheid",
                     "Minimumvoorraad voor voorraadbewaking"):
        assert required in a24 or required.lower() in a24.lower(), required

    a26 = next(ROOT.glob("AD26_*.html")).read_text(encoding="utf-8")
    assert "17.00 uur" in a26 and "maximaal drie uur" in a26
    assert "oude standaardtermijn is niet verplicht" in a26

    a28 = next(ROOT.glob("AD28_*.html")).read_text(encoding="utf-8")
    assert "Systeem- of robotmonitor" in a28
    assert "10.000" in a28 and "20.000" in a28

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("../../brightspace/") >= 28
    assert len(list((ROOT / "previews").glob("AD??_*.png"))) >= 12

    app = ROOT.parents[2] / "code/frontend/templates/base.html"
    assert "executed on device" not in app.read_text(encoding="utf-8")
    assert app.read_text(encoding="utf-8").rstrip().endswith("</html>")
    print("PASS: 28 ontwerpen, 28 PlantUML-links, casusvelden en factuurtotalen, "
          "afzonderlijke productacties, schermvarianten, disabled controls, "
          "geen scripts en een schone base.html")


if __name__ == "__main__":
    check()
