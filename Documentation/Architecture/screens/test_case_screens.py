"""Regression checks for 28 casus-based static screen designs."""
from pathlib import Path
from html.parser import HTMLParser
import sys
from screen_specs import SCREENS

ROOT = Path(__file__).resolve().parent

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.labels = []
        self.buttons = []
        self.fields = []
        self.tables = 0
        self.links = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            assert a["id"] not in self.ids, f"duplicate id {a['id']}"
            self.ids.add(a["id"])
        if tag == "label":
            self.labels.append(a.get("for"))
        if tag in ("button", "input", "select", "textarea"):
            self.fields.append((tag, a))
            assert "disabled" in a, (tag, a)
        if tag == "button":
            self.buttons.append(a)
        if tag == "table":
            self.tables += 1
        if tag == "a" and "href" in a:
            self.links.append(a["href"])

def run():
    assert len(list(ROOT.glob("AD??_*.html"))) == 28
    for n in range(1, 29):
        path = next(ROOT.glob(f"AD{n:02}_*.html"))
        source = path.read_text(encoding="utf-8")
        p = Inspector()
        p.feed(source)
        assert p.tables == 1, path.name
        assert "<main" in source and "<h1>" in source and "scenario-panel" in source
        assert len(source.split('class="scenario"')) - 1 == len(SCREENS[n]["variants"])
        assert all(identifier in p.ids for identifier in p.labels), path.name
        for link in p.links:
            if not link.startswith(("http:", "https:", "#")):
                assert (ROOT / link).resolve().exists(), (path.name, link)
        if SCREENS[n]["mode"] != "human":
            assert len(p.buttons) == 0, path.name
        else:
            assert len(p.buttons) == len(SCREENS[n]["actions"]), path.name
        if n in (5, 16):
            assert "invoice-preview" in source
        assert "mac.home" not in source
    base = (ROOT.parents[2] / "code/frontend/templates/base.html").read_text(encoding="utf-8")
    assert "executed on device" not in base
    assert base.rstrip().endswith("</html>")
    print("PASS: 28 screen designs, 28 source links, roles, disabled controls, branches, invoices and clean base.html")


if __name__ == "__main__":
    run()
