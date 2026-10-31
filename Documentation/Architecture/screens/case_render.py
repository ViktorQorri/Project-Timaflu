"""Render static, case-traceable HTML sketches for each approved activity."""
from html import escape
from screen_specs import SCREENS


def e(v):
    return escape(str(v), quote=True)


def input_control(number, idx, field):
    label, kind, options = field
    fid = f"field-{number}-{idx}"
    if kind == "display":
        control = '<div class="screen-display" aria-label="Onderdeel van werkende applicatie">Wordt vastgelegd in de werkende applicatie</div>'
    elif kind == "checkbox":
        control = f'<input id="{fid}" type="checkbox" disabled>'
    elif kind == "select":
        items = '<option>Maak een keuze</option>' + ''.join(f'<option>{e(o)}</option>' for o in options)
        control = f'<select id="{fid}" disabled>{items}</select>'
    elif kind == "textarea":
        control = f'<textarea id="{fid}" rows="2" disabled></textarea>'
    else:
        typ = kind if kind in {"text", "date", "time", "number", "tel", "url"} else "text"
        control = f'<input id="{fid}" type="{typ}" placeholder="{e(label)}" disabled>'
    if kind in {"display"}:
        return f'<div class="screen-field"><span class="field-label">{e(label)}</span>{control}</div>'
    return f'<div class="screen-field"><label for="{fid}">{e(label)}</label>{control}</div>'


def html_invoice():
    return """<section class="invoice-preview" aria-label="Factuurberekening en klantkorting">
<h3>Prijs- en factuuroverzicht</h3>
<div class="invoice-grid">
<span>Subtotaal bestelregels</span><output>€ …</output>
<span>9% btw (bij facturatie)</span><output>€ …</output>
<span>Totaal inclusief btw</span><output>€ …</output>
<span>Bestellingskorting (5% bij € 500 of meer)</span><output>€ …</output>
<span>Eenmalige korting (indien toegekend)</span><output>€ …</output>
<span>Klantenkorting voorgaand jaar</span><output>€ …</output>
<strong>Te betalen totaal</strong><output>€ …</output>
</div>
<p class="screen-note">De bedragen zijn bewust leeg. De werkende backend berekent en vult ze.</p>
</section>"""


def render(number, stem, title, group, wrap):
    s = SCREENS[number]
    fields = '\n'.join(input_control(number, idx, field)
                       for idx, field in enumerate(s["fields"]))
    headings = ''.join(f'<th scope="col">{e(col)}</th>' for col in s["columns"])
    actions = ''.join(f'<button type="button" disabled title="Ontwerpschets, geen werkende actie">{e(a)}</button>'
                      for a in s["actions"])
    variants = ''.join(f'<article class="scenario"><h3>{e(name)}</h3><p>{e(desc)}</p></article>'
                       for name, desc in s["variants"])
    notes = ''.join(f'<li>{e(note)}</li>' for note in s["notes"])
    read_only = s["mode"] in ("robot", "automatic")
    if read_only:
        edit = ('<p class="screen-note">Alle velden hieronder zijn getoonde systeemgegevens, geen handmatige invoer.</p>'
                + (f'<div class="screen-fields">{fields}</div>' if fields else ''))
    else:
        edit = (f'<div class="screen-fields">{fields}</div>' if fields else
                '<p class="screen-note">Deze activiteit start vanuit een overzicht, zonder handmatige invoer.</p>')
    action_section = (f'<div class="screen-actions">{actions}</div>' if actions else
                      '<p class="screen-note">Geen handmatige schermacties: deze activiteit wordt door de robot of het systeem uitgevoerd.</p>')
    content = f"""
<section class="hero">
<span class="overline">{e(group)} · AD{number:02d}</span>
<h1>{e(title)}</h1>
<p>{e(s["purpose"])}</p>
<div class="screen-meta"><span><strong>Uitvoerder:</strong> {e(s["actor"])}</span><span><strong>Type:</strong> {'Systeem- / robotmonitor' if read_only else 'Gebruikersscherm'}</span></div>
</section>
<main class="screen-main" id="main">
<div class="board">
<section class="screen-panel" aria-labelledby="input-heading">
<span class="overline">{'Read-only procesmonitor' if read_only else 'Gebruikersinterface'}</span>
<h2 id="input-heading">{'Systeeminformatie' if read_only else 'Invoer en handelingen'}</h2>
{edit}
{action_section}
<p class="screen-note">Dit is uitsluitend een statisch schermontwerp. De actieve bedrijfslogica hoort bij Flask/Jinja, de backend en de database.</p>
</section>
<section class="screen-panel" aria-labelledby="output-heading">
<span class="overline">Resultaten</span><h2 id="output-heading">Bijbehorend overzicht</h2>
<div class="screen-table-wrap"><table><thead><tr>{headings}</tr></thead><tbody>
<tr><td colspan="{len(s["columns"])}" class="empty-row">Nog geen gegevens weergegeven. Geen verzonnen klant-, medicijn- of transactiegegevens.</td></tr>
</tbody></table></div>
{html_invoice() if s["invoice"] else ''}
<div class="source-links"><a href="../uml/src/activity_diagrams/{e(stem)}.puml">Activity diagram (PlantUML)</a>
<a href="../uml/export/activity_diagrams/{e(stem)}.svg">Activity diagram (SVG)</a></div>
</section></div>
<section class="scenario-panel" aria-labelledby="scenario-heading">
<span class="overline">Bijbehorende procesuitkomsten</span><h2 id="scenario-heading">Situaties die het scherm moet ondersteunen</h2>
<div class="scenario-grid">{variants}</div>
{f'<ul class="case-notes">{notes}</ul>' if notes else ''}
</section>
</main>"""
    return wrap(title, content)
