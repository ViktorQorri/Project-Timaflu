"""Statische, casusgetrouwe schermontwerpen voor alle 28 activity diagrams.

De uitvoer bevat geen JavaScript en maakt geen databaseverbinding.
Acties zijn bewust disabled: dit is het ontwerp, niet de applicatie.
"""
from html import escape

from screen_specs import SCREENS, CASE_SOURCES, SCREEN_CASE_KEYS
from screen_states import SCREEN_STATES


def e(value):
    return escape(str(value), quote=True)


def button(label):
    return (f'<button type="button" disabled '
            f'title="Alleen ontwerpschets, geen werkende actie">{e(label)}</button>')


def display_source(label):
    lower = label.lower()
    if "handtekening" in lower:
        return "Wordt bij aflevering door de klant vastgelegd"
    if "besteldatum" in lower:
        return "Wordt automatisch vastgelegd bij het opnemen van de order"
    if "minimale bestel" in lower:
        return "Wordt uit de productcatalogus geladen"
    if "spoedindicatie" in lower:
        return "Wordt uit de geselecteerde bestelling geladen"
    if any(word in lower for word in ("afleveradres", "factuuradres", "telefoonnummer")):
        return "Wordt uit de klantgegevens geladen"
    return "Wordt uit de bestaande systeemregistratie geladen"


def input_control(number, index, field):
    label, kind, options = field
    fid = f"field-{number}-{index}"
    if kind == "display":
        return (
            '<div class="screen-field">'
            f'<span class="field-label">{e(label)}</span>'
            f'<div class="screen-display">{e(display_source(label))}</div>'
            '</div>'
        )
    if kind == "checkbox":
        control = f'<input id="{fid}" type="checkbox" disabled>'
    elif kind == "select":
        options_html = '<option value="">Maak een keuze</option>'
        options_html += "".join(f'<option>{e(option)}</option>'
                                for option in options)
        control = f'<select id="{fid}" disabled>{options_html}</select>'
    elif kind == "textarea":
        control = f'<textarea id="{fid}" rows="3" disabled></textarea>'
    else:
        kind = kind if kind in {"text", "number", "date", "time", "tel", "url"} else "text"
        control = (f'<input id="{fid}" type="{kind}" '
                   f'placeholder="{e(label)}" disabled>')
    return (
        f'<div class="screen-field"><label for="{fid}">{e(label)}</label>'
        f'{control}</div>'
    )


def render_order_breakdown():
    rows = [
        "Subtotaal van de bestelregels",
        "Bestellingskorting (5% bij minimaal € 500)",
        "Eenmalige korting (10% op eerste bestelling indien van toepassing)",
        "Klantenkorting op basis van vorig jaar",
        "Totaalbedrag voor klantakkoord",
    ]
    cells = "".join(
        f'<dt>{e(label)}</dt><dd>&euro; &hellip;</dd>' for label in rows
    )
    return (
        '<section class="order-breakdown" aria-labelledby="order-breakdown-heading">'
        '<h3 id="order-breakdown-heading">Berekening voor klantakkoord</h3>'
        f'<dl class="calculation-grid">{cells}</dl>'
        '<p class="screen-note">De backend bepaalt de daadwerkelijk toepasselijke '
        'kortingen en berekent het totaal. Geen fictieve bedragen.</p>'
        '</section>'
    )


def render_invoice_document():
    required = [
        "Totaal excl btw",
        "9% btw",
        "Totaal incl btw",
        "Bestellingskorting",
        "Totaal incl bestellingskorting",
        "Eenmalige korting",
        "Totaal incl eenmalige korting",
        "Klantenkorting",
        "Totaal incl klantenkorting",
    ]
    totals = "".join(
        f'<dt>{e(label)}</dt><dd>&euro; &hellip;</dd>'
        for label in required
    )
    return f"""<section class="invoice-document" aria-labelledby="invoice-document-heading">
<span class="overline">Verplicht factuurschermontwerp uit de productbeschrijving</span>
<h2 id="invoice-document-heading">Conceptfactuur</h2>
<div class="invoice-topline">
<div><strong>Datum</strong><span>Uit factuurgegevens</span></div>
<div><strong>Factuurnummer</strong><span>Uit factuurgegevens</span></div>
</div>
<div class="invoice-parties">
<div><strong>Timaflu</strong><span>Adres Timaflu uit bedrijfsgegevens</span></div>
<div><strong>Naam bedrijf (klant)</strong><span>Adres klant uit klantgegevens</span></div>
</div>
<p class="table-scroll-hint">Veeg horizontaal om de volledige factuurregels te bekijken.</p>
<div class="invoice-lines-wrap" tabindex="0" role="region" aria-label="Factuurregels, horizontaal scrollbaar">
<table class="invoice-lines" aria-label="Gefactureerde, geleverde bestelregels">
<thead><tr>
<th scope="col">Omschrijving medicijn</th>
<th scope="col">Aantal</th>
<th scope="col">Prijs per eenheid</th>
<th scope="col">Regeltotaal</th>
</tr></thead>
<tbody><tr><td colspan="4" class="empty-row">
Geleverde regels en eventuele extra bezorgkosten worden uit het systeem geladen.
</td></tr></tbody>
</table>
</div>
<div class="invoice-summary">
<h3>Factuurtotalen en kortingen</h3>
<dl class="invoice-totals">{totals}</dl>
</div>
<p class="screen-note">De opmaak volgt Product-description.md. Bedragen, datum,
factuurnummer, adresgegevens en bestelregels worden niet verzonnen. Extra
bezorgkosten komen uitsluitend uit reeds geregistreerde gegevens.</p>
</section>"""


def render_supplier_management():
    return """<section class="case-detail" aria-labelledby="supplier-management-heading">
<span class="overline">Productbeheer bij voorraadtekort</span>
<h2 id="supplier-management-heading">Leverancierskoppeling en medicijn beheren</h2>
<p>De onderstaande twee beheeracties worden afzonderlijk aangeboden.
Ze staan los van het verwijderen uit de interne bestellijst.</p>
<div class="screen-fields">
<div class="screen-field">
<label for="supplier-product">Geselecteerd medicijn</label>
<input id="supplier-product" type="text" placeholder="Medicijn of artikelnummer" disabled>
</div>
<div class="screen-field">
<label for="supplier-link">Fabrikant gekoppeld aan dit medicijn</label>
<select id="supplier-link" disabled>
<option value="">Selecteer een fabrikant uit de leverancierslijst</option>
</select>
</div>
</div>
<div class="screen-actions">
<button type="button" disabled title="Alleen ontwerpschets, geen werkende actie">
Leverancier van dit medicijn verwijderen</button>
<button type="button" disabled title="Alleen ontwerpschets, geen werkende actie">
Medicijn verwijderen</button>
</div>
<p class="screen-note">Een leverancierskoppeling verwijderen betekent niet de
fabrikant overal verwijderen. De twee mogelijkheden zijn expliciet voorgeschreven
bij het niet-voorraadscenario in Product-description.md.</p>
</section>"""


def render_signature_design():
    return """<section class="signature-section" aria-labelledby="signature-heading">
<span class="overline">Digitale ontvangst bij levering</span>
<h2 id="signature-heading">Handtekening klant</h2>
<div class="signature-placeholder" role="img" aria-label="Statisch ontwerp van het digitale handtekeningveld">
<span>Plaats voor digitale ontvangsthandtekening</span>
<span class="signature-line" aria-hidden="true"></span>
</div>
<div class="signature-meta">
<div><strong>Bestelnummer</strong><span>Uit geselecteerde rit</span></div>
<div><strong>Aflevertijdstip</strong><span>Bij bevestiging vastleggen</span></div>
</div>
<p class="screen-note">Schets van de ondertekening, geen werkende tekenfunctie.
In de Flask/Jinja-applicatie moet de handtekening bij aflevering worden opgeslagen.</p>
</section>"""


def render_delivery_schedule():
    return """<section class="case-detail" aria-labelledby="delivery-schedule-heading">
<span class="overline">Verplicht overzicht voor de bezorging</span>
<h2 id="delivery-schedule-heading">Bezorgrooster en tweede poging</h2>
<div class="screen-fields">
<div class="screen-field">
<label for="delivery-roster-date">Ritdatum</label>
<input id="delivery-roster-date" type="date" disabled>
</div>
</div>
<p class="table-scroll-hint">Veeg horizontaal om alle kolommen van het bezorgrooster te zien.</p>
<div class="screen-table-wrap" tabindex="0" role="region" aria-label="Bezorgrooster, horizontaal scrollbaar">
<table aria-label="Rooster van toegewezen ritten">
<thead><tr>
<th scope="col">Tijd / dagdeel</th><th scope="col">Klantnaam</th>
<th scope="col">Afleveradres</th><th scope="col">Contactpersoon</th>
<th scope="col">Telefoonnummer</th><th scope="col">Bezorgpoging</th>
</tr></thead>
<tbody><tr><td colspan="6" class="empty-row">
Klant- en ritgegevens worden uit het systeem geladen.</td></tr></tbody>
</table>
</div>
<p class="screen-note">Na een eerste mislukte levering komt dezelfde bestelling
later die dag opnieuw op het rooster. Bij een tweede mislukking volgt
terugbrengen en afstemming met verkoop over een nieuwe afspraak.</p>
</section>"""


def render_states(number):
    states = SCREEN_STATES.get(number, ())
    if not states:
        return ""
    parts = []
    for index, item in enumerate(states, 1):
        values = "".join(
            f'<dt>{e(label)}</dt><dd>{e(value)}</dd>'
            for label, value in item["values"]
        )
        action_html = "".join(button(label) for label in item["actions"])
        actions = (f'<div class="state-actions">{action_html}</div>'
                   if action_html else
                   '<p class="screen-note">Geen handmatige actie in deze processtatus.</p>')
        actor = (f'<p class="state-actor">Uitvoerder: {e(item["actor"])}</p>'
                 if item["actor"] else "")
        parts.append(
            f'<article class="state-card state-card--{e(item["tone"])}" '
            f'data-state-variant="{index}">'
            f'<div class="state-header"><h3>{e(item["title"])}</h3>'
            f'<span class="state-pill">{e(item["status"])}</span></div>'
            f'<p class="state-message">{e(item["message"])}</p>'
            f'<dl class="state-values">{values}</dl>{actions}{actor}</article>'
        )
    return (
        '<section class="state-gallery" aria-labelledby="states-heading">'
        '<span class="overline">Concreet uitgewerkte schermvarianten</span>'
        '<h2 id="states-heading">Schermtoestanden bij beslismomenten</h2>'
        '<p>Deze statische varianten tonen de informatie en meldingen die '
        'bij de verschillende casusuitkomsten zichtbaar moeten zijn.</p>'
        f'<div class="state-grid">{"".join(parts)}</div></section>'
    )


def render(number, stem, title, group, wrap):
    spec = SCREENS[number]
    fields = "\n".join(
        input_control(number, i, f) for i, f in enumerate(spec["fields"])
    )
    headings = "".join(
        f'<th scope="col">{e(column)}</th>' for column in spec["columns"]
    )
    actions = "".join(button(label) for label in spec["actions"])
    scenarios = "".join(
        f'<article class="scenario"><h3>{e(name)}</h3><p>{e(desc)}</p></article>'
        for name, desc in spec["variants"]
    )
    notes = "".join(f'<li>{e(note)}</li>' for note in spec["notes"])
    case_links = "".join(
        f'<a href="{e(CASE_SOURCES[key][1])}">{e(CASE_SOURCES[key][0])}</a>'
        for key in SCREEN_CASE_KEYS[number]
    )
    read_only = spec["mode"] in ("robot", "automatic")
    if number == 27:
        # De koerier registreert pogingen; uitsluitend verkoop maakt de
        # nieuwe leverafspraak en legt de extra bezorgkosten vast.
        courier = "".join(input_control(number, i, spec["fields"][i])
                          for i in (0, 1))
        sales = "".join(input_control(number, i, spec["fields"][i])
                        for i in range(2, len(spec["fields"])))
        form = (
            '<section class="role-block" aria-labelledby="courier-role">'
            '<h3 id="courier-role">Koerier: eerste en tweede bezorgpoging</h3>'
            '<p>Bestelnummer en het opzoekbare klanttelefoonnummer voor een '
            'gesloten deur.</p>'
            f'<div class="screen-fields">{courier}</div>'
            '<div class="screen-actions">'
            + "".join(button(action) for action in spec["actions"][:2])
            + '</div></section>'
            '<section class="role-block" aria-labelledby="sales-role">'
            '<h3 id="sales-role">Verkoop: afspraak na twee mislukte pogingen</h3>'
            '<p>Pas nadat de koerier de niet-geleverde medicijnen heeft '
            'teruggebracht, legt verkoop het nieuwe moment en de extra kosten '
            'met toelichting vast.</p>'
            f'<div class="screen-fields">{sales}</div>'
            '<div class="screen-actions">'
            + "".join(button(action) for action in spec["actions"][2:])
            + '</div></section>'
        )
        action_area = ""
    elif read_only:
        form = ('<p class="screen-note">Dit zijn getoonde systeemgegevens, '
                'geen handmatige invoervelden.</p>'
                + f'<div class="screen-fields">{fields}</div>')
        action_area = '<p class="screen-note">Geen handmatige actie in dit proces.</p>'
    else:
        form = (f'<div class="screen-fields">{fields}</div>' if fields else
                '<p class="screen-note">Dit scherm start vanuit een overzicht '
                'zonder handmatige invoer.</p>')
        action_area = (
            f'<div class="screen-actions">{actions}</div>'
            if actions else
            '<p class="screen-note">Geen handmatige actie in dit proces.</p>'
        )
    details = []
    if number == 2:
        details.append(render_supplier_management())
    if number == 5:
        details.append(render_order_breakdown())
    if number == 16:
        details.append(render_invoice_document())
    if number == 12:
        details.append(render_signature_design())
    if number == 27:
        details.append(render_delivery_schedule())
    content = f"""<section class="hero">
<span class="overline">{e(group)} &middot; AD{number:02d}</span>
<h1>{e(title)}</h1>
<p>{e(spec["purpose"])}</p>
<div class="screen-meta">
<span><strong>Uitvoerder:</strong> {e(spec["actor"])}</span>
<span><strong>Type:</strong> {'Systeem- of robotmonitor' if read_only else 'Gebruikersscherm'}</span>
</div>
</section>
<main class="screen-main" id="main">
<div class="board">
<section class="screen-panel" aria-labelledby="input-heading">
<span class="overline">{'Read-only procesmonitor' if read_only else 'Gebruikersinterface'}</span>
<h2 id="input-heading">{'Systeeminformatie' if read_only else 'Invoer en handelingen'}</h2>
{form}{action_area}
<p class="screen-note">Deze statische schets is niet de werkende applicatie.
Proceslogica en gegevensuitwisseling horen bij Flask/Jinja en de backend.</p>
</section>
<section class="screen-panel" aria-labelledby="output-heading">
<span class="overline">Resultaten</span>
<h2 id="output-heading">Bijbehorend overzicht</h2>
<p class="table-scroll-hint">Veeg horizontaal om alle tabelkolommen te bekijken.</p>
<div class="screen-table-wrap" tabindex="0" role="region" aria-label="Resultatentabel, horizontaal scrollbaar"><table>
<thead><tr>{headings}</tr></thead>
<tbody><tr><td colspan="{len(spec['columns'])}" class="empty-row">
Geen voorbeeldgegevens. De werkende applicatie laadt deze informatie uit de database.
</td></tr></tbody></table></div>
<div class="source-links">
{case_links}
<a href="../uml/src/activity_diagrams/{e(stem)}.puml">Activity diagram (PlantUML)</a>
<a href="../uml/export/activity_diagrams/{e(stem)}.svg">Activity diagram (SVG)</a>
</div>
</section></div>
{"".join(details)}
{render_states(number)}
<section class="scenario-panel" aria-labelledby="scenario-heading">
<span class="overline">Herleidbaarheid naar casus en proces</span>
<h2 id="scenario-heading">Ondersteunde procesuitkomsten</h2>
<div class="scenario-grid">{scenarios}</div>
{f'<ul class="case-notes">{notes}</ul>' if notes else ''}
</section>
</main>"""
    return wrap(title, content)
