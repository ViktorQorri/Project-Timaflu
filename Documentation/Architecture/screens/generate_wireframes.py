"""Generate 28 non-interactive Timaflu UI screen designs from approved activities.

The screen structure uses fields and read-only table headings explicitly present in
Current-processes.md, Desired-process.md and activity diagrams. Controls are disabled
because this deliverable is a SCREEN DESIGN, not a second application.
"""
from pathlib import Path
from html import escape

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"uml/src/activity_diagrams"
DEST=Path(__file__).resolve().parent

GROUPS={
  "Inkoop":{1,2,3,24},
  "Verkoop":{4,5,6,7,28},
  "Orderpicking":{8,9,10,11,22,23},
  "Distributie":{12,13,14,15,26,27},
  "Administratie":{16,17,18,19,25},
  "Acquisitie":{20,21},
}
TITLES={
 1:"Fabrikantgegevens beheren",2:"Producten bijbestellen",3:"Minimumvoorraad controleren",
 4:"Voorraad controleren",5:"Bestelling invoeren",6:"Orderstatus bekijken",
 7:"Klantgegevens beheren",8:"Verzamelbakken bekijken",9:"Bestelling verpakken",
 10:"Verzamelbak registreren",11:"Deelorder afronden",12:"Levering registreren",
 13:"Toegewezen ritten bekijken",14:"Levertijd opzoeken",
 15:"Telefoonnummer klant opzoeken",16:"Factuur maken",
 17:"Afgeleverde bestellingen bekijken",18:"Openstaande facturen bekijken",
 19:"Betaling registreren",20:"Acquisitiebezoek registreren",
 21:"Potentiële klant opvolgen",22:"Deelorder aanvragen",
 23:"Deelorder verzamelen",24:"Nieuw medicijn beoordelen",
 25:"Inkoopfacturen betalen",26:"Bezorgritten toewijzen",
 27:"Mislukte levering afhandelen",28:"Jaarlijkse klantenkorting bijwerken",
}
FIELDS={
 1:["Fabrikant","Adres","Contactpersoon","Telefoonnummer","Website"],
 2:["Medicijn","Aantal","Fabrikant"],
 3:["Medicijn of artikelnummer"],
 4:["Medicijn of artikelnummer","Gevraagd aantal"],
 5:["Klant","Afleveradres","Factuuradres","Medicijn","Aantal","Leverdatum","Dagdeel"],
 6:["Bestelnummer of klantnaam"],
 7:["Apotheeknaam","Contactpersoon","Telefoonnummer","Afleveradres","Factuuradres"],
 8:["Bestelnummer of verzamelbakcode"],
 9:["Bestelnummer","Aantal dozen"],
 10:["Robotnummer","Deelordernummer","Unieke verzamelbakcode"],
 11:["Robotnummer","Deelordernummer"],
 12:["Bestelnummer","Aflevermoment","Ontvangst ondertekend"],
 13:["Koerier","Ritdatum"],
 14:["Bestelnummer"],
 15:["Bestelnummer"],
 16:["Klantnummer","Factuurdatum"],
 17:["Klantnummer","Periode"],
 18:["Klantnummer of factuurnummer"],
 19:["Factuurnummer","Ontvangen bedrag"],
 20:["Bedrijfsnaam","Contactpersoon","Contactgegevens","Adres","Bezoekdatum"],
 21:["Potentiële apotheek","Factuuradres","Afleveradres","Toestemming klantaccount"],
 22:["Robotnummer","Magazijngang"],
 23:["Deelordernummer","Magazijngang","Verzamelbakcode"],
 24:["Medicijn","Fabrikant","Inkoopprijs"],
 25:["Leveranciersfactuur","Factuurbedrag","Vervaldatum"],
 26:["Bestelnummer","Koerier","Afleverdatum","Dagdeel"],
 27:["Bestelnummer","Telefoonnummer klant","Tijd tweede poging"],
 28:["Kalenderjaar"],
}
COLUMNS={
 1:["Fabrikant","Contactpersoon","Telefoonnummer","Website"],
 2:["Fabrikant","Inkoopprijs","Contactpersoon","Telefoonnummer"],
 3:["Medicijn","Huidige voorraad","Minimumvoorraad","Tekort"],
 4:["Medicijn","Fysieke voorraad","Gereserveerd","Beschikbaar"],
 5:["Artikelnummer","Medicijn","Aantal","Prijs"],
 6:["Bestelnummer","Orderstatus","Backorder","Levermoment"],
 7:["Apotheek","Contactpersoon","Afleveradres","Factuuradres"],
 8:["Bestelnummer","Verzamelbakken","Bestelling compleet"],
 9:["Verzamelbak","Medicijn","Aantal"],
 10:["Verzamelbakcode","Deelordernummer","Magazijngang"],
 11:["Deelordernummer","Medicijn","Gevraagd aantal","Afgerond"],
 12:["Bestelnummer","Aflevermoment","Klant","Ontvangst"],
 13:["Rit","Bestelling","Klantadres","Levermoment"],
 14:["Bestelnummer","Leverdatum","Dagdeel"],
 15:["Klant","Contactpersoon","Telefoonnummer"],
 16:["Geleverd medicijn","Aantal","Prijs","Regeltotaal"],
 17:["Klant","Bestelnummer","Leverdatum","Geleverd bedrag"],
 18:["Factuurnummer","Klant","Factuurdatum","Openstaand bedrag"],
 19:["Factuurnummer","Factuurbedrag","Betaalstatus"],
 20:["Apotheek","Contactpersoon","Adres","Bezoekdatum"],
 21:["Apotheek","Laatste bezoek","Bestelling geplaatst"],
 22:["Deelordernummer","Magazijngang","Medicijn","Aantal"],
 23:["Medicijn","Magazijnlocatie","Aantal","Verzamelbak"],
 24:["Medicijn","Fabrikant","Inkoopprijs","Beoordeling"],
 25:["Fabrikant","Factuurnummer","Bedrag","Vervaldatum"],
 26:["Koerier","Bestelnummer","Afleveradres","Levermoment"],
 27:["Bestelnummer","Eerste poging","Tweede poging","Status"],
 28:["Klant","Betaalde jaaromzet","Kortingspercentage volgend jaar"],
}
ACTION={
 1:"Fabrikantgegevens opslaan",2:"Bevestigde inkooporder registreren",
 3:"Minimumvoorraad controleren",4:"Beschikbaarheid controleren",
 5:"Order ter goedkeuring voorleggen",6:"Orderstatus opzoeken",
 7:"Klantgegevens opslaan",8:"Verzamelbakken opzoeken",9:"Verpakking bevestigen",
 10:"Verzamelbakcode registreren",11:"Deelorder gereed melden",
 12:"Aflevering bevestigen",13:"Ritten bekijken",14:"Levermoment opzoeken",
 15:"Contactgegevens bekijken",16:"Factuur controleren",
 17:"Geleverde bestellingen bekijken",18:"Openstaande facturen bekijken",
 19:"Volledige betaling registreren",20:"Acquisitiebezoek registreren",
 21:"Potentiële klant opvolgen",22:"Volgende deelorder aanvragen",
 23:"Verzamelbak registreren",24:"Nieuw medicijn ter beoordeling voorleggen",
 25:"Inkoopfactuur betalen",26:"Rit toewijzen",
 27:"Mislukte levering registreren",28:"Jaarlijkse klantenkorting berekenen"
}
assert set(TITLES)==set(FIELDS)==set(COLUMNS)==set(ACTION)==set(range(1,29))
assert sum(len(x) for x in GROUPS.values())==28

def group_for(number):
 return next(k for k,v in GROUPS.items() if number in v)
def type_for(label):
 lower=label.lower()
 if "datum" in lower or "bezoekdatum" in lower or "vervaldatum" in lower:return "date"
 if "tijd" in lower and "dagdeel" not in lower:return "time"
 if any(word in lower for word in ("aantal","bedrag","prijs","kalenderjaar")):return "number"
 return "text"

def wrap(title,content):
 return f'''<!doctype html>
<html lang="nl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} | Timaflu</title><link rel="stylesheet" href="wireframes.css"></head>
<body><div class="page">
<header class="top"><a href="index.html" class="brand">tima<span>flu</span></a>
<nav class="breadcrumbs" aria-label="Schermontwerpen"><a href="index.html">Alle schermen</a></nav></header>
{content}
<footer>Schermontwerp • Timaflu • Bron: bestaande casus en activity diagrams</footer>
</div></body></html>'''

def design(number,source,stem):
 group=group_for(number)
 title=TITLES[number]
 inputs="\n".join(f'''<div class="screen-field">
<label for="field-{number}-{i}">{escape(label)}</label>
<input id="field-{number}-{i}" type="{type_for(label)}" placeholder="Vul {escape(label.lower())} in" disabled></div>'''
                 for i,label in enumerate(FIELDS[number]))
 headings="".join(f"<th scope='col'>{escape(x)}</th>" for x in COLUMNS[number])
 cols=len(COLUMNS[number])
 rows=f"<tr><td colspan='{cols}' class='empty-row'>Geen voorbeeldgegevens. Dit ontwerp gebruikt geen fictieve klant- of bedrijfsdata.</td></tr>"
 # Display only actually described data labels. No fabricated role permissions or actions.
 return wrap(title,f'''<section class="hero">
<span class="overline">{escape(group)} · AD{number:02d}</span>
<h1>{escape(title)}</h1>
<p>Schermontwerp voor de activiteit {escape(stem)}. De velden, resultaten en handelingen zijn herleidbaar tot de casus en het activity diagram. Het is geen werkende applicatie.</p></section>
<main class="board" id="main">
<section class="screen-panel" aria-labelledby="input-heading">
<span class="overline">Gebruikersinterface</span>
<h2 id="input-heading">Gegevens en handelingen</h2>
<div class="screen-fields">{inputs}</div>
<button type="button" disabled title="Alleen schermontwerp, geen werkende actie">{escape(ACTION[number])}</button>
<p class="screen-note">Bediening is in deze ontwerpschets uitgeschakeld. De werkende schermen horen bij de Flask/Jinja-applicatie.</p>
</section>
<section class="screen-panel" aria-labelledby="output-heading">
<span class="overline">Overzicht</span>
<h2 id="output-heading">Bijbehorende gegevens</h2>
<div class="screen-table-wrap"><table><thead><tr>{headings}</tr></thead><tbody>{rows}</tbody></table></div>
<div class="source-links"><a href="../uml/src/activity_diagrams/{escape(source)}">Activity diagram (PlantUML)</a>
<a href="../uml/export/activity_diagrams/{escape(stem)}.svg">Activity diagram (SVG)</a></div>
</section></main>''')

def generate():
 diagrams=sorted(SOURCE.glob("AD??_*.puml"))
 assert len(diagrams)==28,len(diagrams)
 items=[]
 for file in diagrams:
  number=int(file.stem[2:4])
  source=file.read_text(encoding="utf-8-sig")
  assert "@startuml" in source and "@enduml" in source
  output=file.stem+".html"
  (DEST/output).write_text(design(number,file.name,file.stem),encoding="utf-8")
  items.append((number,group_for(number),output))
 indexcards="\n".join(
  f'<a class="index-link" href="{escape(filename)}"><small>{escape(group)} · AD{number:02d}</small>{escape(TITLES[number])}</a>'
  for number,group,filename in items)
 (DEST/"index.html").write_text(wrap("Schermontwerpen",f'''<section class="hero">
<span class="overline">Ontwerpdocumentatie</span><h1>Timaflu: 28 schermontwerpen</h1>
<p>Voor iedere bestaande activiteit een invoer- en overzichtsontwerp. Alle bediening is uitgeschakeld, zodat ontwerp niet wordt verward met een werkende functie.</p>
</section><main class="index-grid">{indexcards}</main>'''),encoding="utf-8")
 readme=["# Timaflu schermontwerpen","","Voor elk van de 28 activity diagrams is een HTML/CSS-schermontwerp beschikbaar.",
 "Elk ontwerp toont de bij de casus en het diagram passende informatievelden, relevante tabelkolommen en een duidelijk als niet-werkend gemarkeerde handeling.",
 "Deze schermontwerpen zijn geen tweede applicatie. Alle actieve procesfunctionaliteit blijft in Flask/Jinja.",
 "Er zijn geen accounts, autorisatierollen, bedrijfsstatussen, verzonnen data of JavaScript toegevoegd.","",
 "| Proces | Activity diagram | Schermontwerp |","|---|---|---|"]
 for n,group,filename in items:
  stem=filename.removesuffix(".html")
  readme.append(f"| {group} | [AD{n:02d}](../uml/src/activity_diagrams/{stem}.puml) | [Ontwerp]({filename}) |")
 readme += ["","## Controle","- 28 afzonderlijke HTML-ontwerpen met veld- en tabelstructuur.",
             "- Uitgeschakelde controls om niet-functionaliteit expliciet te maken.",
             "- Responsive HTML/CSS, zonder JavaScript of React.",
             "- Niet van toepassing op de automatische backendscenario's.",
             "- In de werkende applicatie worden gegevens altijd via de database geladen."]
 (DEST/"README.md").write_text("\n".join(readme)+"\n",encoding="utf-8")
 print("Generated",len(items),"screen layouts, aligned to the existing 28 activity diagrams")

if __name__=="__main__":
 generate()
