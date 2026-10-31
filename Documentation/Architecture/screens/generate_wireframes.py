"""Generate one non-interactive design wireframe per existing Timaflu activity diagram.

Process steps are copied from PlantUML. This tool does not add business rules,
data, controls or API features. Open screens/index.html in any browser.
"""
from pathlib import Path
from html import escape
import re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"uml/src/activity_diagrams"
DEST=Path(__file__).resolve().parent

GROUPS={
    "Inkoop":{1,2,3,24},
    "Verkoop":{4,5,6,7,28},
    "Orderpicking":{8,9,10,11,22,23},
    "Distributie":{12,13,14,15,26,27},
    "Administratie":{16,17,18,19,25},
    "Acquisitie":{20,21},
}

def process_name(stem):
    number=int(stem[2:4])
    return next(group for group,ids in GROUPS.items() if number in ids)

def get_actions(source):
    role="Systeem"
    actions=[]
    roles=[]
    for line in source.splitlines():
        line=line.strip()
        if line.startswith("|") and line.endswith("|"):
            role=line[1:-1].strip()
            if role not in roles: roles.append(role)
        elif line.startswith(":") and line.endswith(";"):
            value=line[1:-1].replace("\\n"," ").strip()
            if value:
                actions.append((role,"actie",value))
        elif line.startswith(("if (","while (","repeat while","elseif (")):
            question=line.split(" then ",1)[0].split(" is ",1)[0].strip()
            actions.append((role,"keuze",question))
        elif line.startswith("else ") or line.startswith("else("):
            actions.append((role,"keuze","Alternatieve uitkomst"))
        elif line.startswith("stop"):
            actions.append((role,"resultaat","Proces stopt"))
    return roles,actions

def page(title,body):
    return f"""<!doctype html>
<html lang="nl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | Timaflu</title><link rel="stylesheet" href="wireframes.css"></head>
<body><div class="page"><header class="top">
<a href="index.html" class="brand">tima<span>flu</span></a><nav class="breadcrumbs" aria-label="Schermontwerpen"><a href="index.html">Alle schermen</a></nav>
</header>{body}<footer>Procesgebonden wireframes • Bron: bestaande Timaflu-activity diagrams</footer></div></body></html>"""

def generate():
    files=sorted(SRC.glob("AD??_*.puml"))
    assert len(files)==28,("expected 28 existing activity diagrams",len(files))
    index=[]
    for f in files:
        group=process_name(f.stem)
        title=f.stem.split("_",1)[1].replace("_"," ")
        roles,actions=get_actions(f.read_text(encoding="utf-8-sig"))
        if not actions:
            raise ValueError(f"No readable steps found: {f.name}")
        steps="".join(
            f'<div class="step step--{("decision" if kind=="keuze" else "feedback" if kind=="resultaat" else "action")}">'
            f'<h3>{escape(role)} • {escape(kind)}</h3><p>{escape(value)}</p></div>'
            for role,kind,value in actions
        )
        labels="".join(f'<span class="pill">{escape(r)}</span>' for r in roles)
        body=f"""<section class="hero">
<div class="overline">{escape(group)} · {escape(f.stem[:4])}</div>
<h1>{escape(title)}</h1>
<p>Conceptscherm op basis van {escape(f.name)}. De stappen en keuzes hieronder komen uit de bron en tonen geen verzonnen testresultaten of werkende functies.</p></section>
<main class="board" id="main">
<aside class="panel"><h2>Betrokken rollen</h2>{labels}
<h2>Doel van dit ontwerp</h2><p>Een scanbare medewerkersweergave voor de beschreven processtappen.</p>
<p class="warning">Dit is een schermontwerp, geen werkende applicatie. Alleen goedgekeurde processtappen mogen later als functionaliteit worden uitgewerkt.</p>
<div class="source-links"><a href="../uml/src/activity_diagrams/{escape(f.name)}">Bron (PlantUML)</a>
<a href="../uml/export/activity_diagrams/{escape(f.stem)}.svg">Activity diagram (SVG)</a></div></aside>
<section class="panel" aria-label="Procesgebonden schermindeling"><h2>Schermonderdelen</h2>
<div class="process">{steps}</div></section></main>"""
        filename=f.stem+".html"
        (DEST/filename).write_text(page(title,body),encoding="utf-8")
        index.append((group,f.stem,title,filename,len(actions)))
    index_body="""<section class="hero"><div class="overline">Ontwerpdocumentatie</div>
<h1>Timaflu: procesgebonden schermontwerpen</h1>
<p>Alle 28 bestaande activity diagrams hebben een bijbehorend responsief wireframe. Dit zijn ontwerpen, geen extra bedrijfsregels of werkende interfaces.</p></section><main>"""
    for group in GROUPS:
        items=[entry for entry in index if entry[0]==group]
        cards="".join(
            f'<a class="index-link" href="{escape(name)}"><small>{escape(stem[:4])} · {len_steps} processtappen</small>{escape(title)}</a>'
            for _,stem,title,name,len_steps in items
        )
        index_body+=f'<section class="group"><h2>{escape(group)}</h2><div class="index-grid">{cards}</div></section>'
    index_body+="</main>"
    (DEST/"index.html").write_text(page("Schermontwerpen",index_body),encoding="utf-8")
    md=["# Timaflu schermontwerpen","# Bron en uitgangspunten",
        "Alle schermontwerpen zijn herleidbaar tot de originele activity diagrams, zonder extra bedrijfsregels.",
        "Open index.html voor een responsieve weergave. Deze documenten zijn geen werkende functies.",
        "",
        "| Proces | Activity diagram | Schermontwerp |",
        "|---|---|---|"]
    md += [f"| {group} | [`{stem}`](../uml/src/activity_diagrams/{stem}.puml) | [Schermontwerp]({filename}) |"
           for group,stem,_,filename,_ in index]
    md += ["","## Controle","- 28 activiteiten: 28 afzonderlijke HTML-ontwerpen.",
           "- Alle processtappen komen uit de originele PlantUML-bronnen.",
           "- CSS heeft een 760 px responsive breakpoint; mobiele picking- en distributieschermen gebruiken één kolom.",
           "- Geen JavaScript, dummyklanten, dummyprijzen of niet-functionele submitknoppen.",
           "- Geen wijziging van MySQL, backend of bedrijfsscenario's."]
    (DEST/"README.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    print(f"Generated {len(index)} wireframes for {len(GROUPS)} process groups")
if __name__=="__main__":
    generate()
