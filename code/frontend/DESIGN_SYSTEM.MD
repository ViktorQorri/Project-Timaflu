# Timaflu Design System

Dit document beschrijft het visuele systeem en de interfacepatronen van het Timaflu-medewerkersportaal. De website wordt door Flask gerenderd met Jinja-templates en CSS in `code/frontend/templates/` en `code/frontend/static/css/`.

## 1. Ontwerpprincipes

Het portaal moet:

- betrouwbaar en professioneel aanvoelen;
- medische informatie rustig en overzichtelijk presenteren;
- belangrijke statussen direct herkenbaar maken;
- de zes bedrijfsprocessen herkenbaar en consistent presenteren;
- ook bij veel operationele informatie scanbaar blijven;
- goed werken op desktop, tablet en mobiel.

De visuele stijl combineert een donkerblauwe basis met helder blauw voor interactie, lichte achtergronden en subtiele borders.

Het scherm Rapportages (`templates/reports.html`) is het referentiescherm. Nieuwe en bestaande schermen volgen dezelfde paginaopbouw (zie 5.4).

## 2. Kleuren

### Basiskleuren

| Token | Waarde | Gebruik |
|---|---:|---|
| `--color-navy` | `#123653` | Primaire tekst, footer en donkere vlakken |
| `--color-primary` | `#0f70b7` | Primaire acties, links, actieve navigatie en iconen |
| `--color-primary-light` | `#eaf5fb` | Lichte merkachtergronden en icoonvlakken |
| `--color-text-muted` | `#718696` | Secundaire tekst |
| `--color-line` | `#dce8ef` | Borders en scheidingslijnen |
| `--color-bg` | `#f5f8fa` | Algemene pagina-achtergrond |
| `--color-surface` | `#ffffff` | Kaarten, tabellen en invoervelden |

### Statuskleuren

| Status | Tokens | Tekst / achtergrond | Voorbeelden |
|---|---:|---:|---|
| In behandeling | `--color-info` / `--color-info-bg` | `#0e70b8` / `#e5f2fb` | Wordt verzameld, onderweg, openstaand |
| Positief | `--color-success` / `--color-success-bg` | `#267e55` / `#e3f5eb` | Afgeleverd, betaald, actief, op voorraad |
| Waarschuwing | `--color-warning` / `--color-warning-bg` | `#ae6a18` / `#fff1dc` | Backorder, bijna op, vervallen |
| Kritiek | `--color-danger` / `--color-danger-bg` | `#bd4646` / `#fde7e6` | Onder minimum, foutmelding |

Gebruik statuskleuren alleen voor betekenisvolle feedback. Gebruik nooit alleen kleur: toon altijd ook een tekstlabel.

## 3. Typografie

### Lettertypen

- **Manrope** — koppen, merknaam en belangrijke cijfers.
- **DM Sans** — lopende tekst, navigatie, formulieren en tabellen.

De fonts worden via Google Fonts geladen in `templates/base.html`.

### Typografische hiërarchie

| Element | Richtlijn |
|---|---|
| Hero-titel | Manrope, 34–54 px, bold, compacte regelafstand |
| Paginatitel | Manrope, 36 px, bold |
| Sectietitel | Manrope, 25 px, bold |
| Kaarttitel | Manrope, 13–15 px, bold |
| Lopende tekst | DM Sans, 13–15 px |
| Tabeltekst | DM Sans, 9–11 px |
| Eyebrow | DM Sans, 14 px, bold, blauw, gewone hoofdletters |
| KPI-waarde | Manrope, 26 px, bold |

Koppen gebruiken een kleine negatieve letterspatiëring voor een compacte, zakelijke uitstraling.

## 4. Afstanden en formaat

De interface gebruikt voornamelijk veelvouden van 4 px.

| Categorie | Waarden |
|---|---|
| Kleine ruimte | 4, 8, 10 px |
| Standaardruimte | 12, 14, 16 px |
| Sectieruimte | 20, 24, 32 px |
| Grote ruimte | 40, 48, 68 px |
| Pagina-padding | `clamp(24px, 4vw, 68px)` |

### Afronding

| Element | Radius |
|---|---:|
| Buttons | 20 px (capsule) |
| Invoervelden | 8 px |
| Icoonvlakken | 8–9 px |
| Kaarten en panelen | 10–12 px |
| Statuslabels | 20 px |
| Profielfoto/indicator | 50% |

## 5. Layout

### Navigatie

- De header heeft twee rijen: het woordmerk met het label `Medewerkersportaal`, daaronder de navigatie.
- Desktop- en mobiele navigatie gebruiken dezelfde lijst uit `base.html`.
- De actieve pagina krijgt blauwe tekst en een lichtblauwe achtergrond.
- Alle werkprocessen zijn beschikbaar; de huidige applicatie kent nog geen gebruikersrollen.
- Onder 1280 px vervangt een `Menu`-knop (native `<details>`, zonder JavaScript) de navigatierij.

### Contentbreedte

- Header, content en footer delen één container van maximaal 1320 px (`--container`).
- Content staat horizontaal gecentreerd.
- De horizontale paginamarge schaalt mee met de viewport.

### Paginaopbouw

Elk scherm volgt de opbouw van Rapportages:

1. Een intro op de achtergrond: `stock-dashboard__intro` met eyebrow, `h1`, toelichting en eventueel acties of een teller rechts.
2. Daaronder een stapel witte panelen met 18 px tussenruimte. Een `section` direct in `.stock-dashboard` is automatisch een paneel; elders gebruik je `.panel`.
3. Zoek- en filterformulieren (`.lookup-form`) direct in de pagina worden een eigen paneel, zoals het rapportfilter.
4. Een tabel in een paneel heeft geen eigen rand. Een losse `stock-dashboard__table-wrap` is zelf een paneel.
5. Herhaalde blokken binnen een paneel, zoals orders of facturen, gebruiken `.sub-panel`.

### Grids

- Snelkoppelingen gebruiken een automatisch passende grid met een minimale kaartbreedte van 140 px.
- KPI-kaarten gebruiken vier kolommen op desktop, twee op tablet en één op kleine mobiele schermen.
- Dashboardpanelen gebruiken maximaal drie kolommen en klappen responsief onder elkaar.

## 6. Componenten

### Merklogo

De huidige header gebruikt het woordmerk `tima` in navy en `flu` in blauw. Voeg geen los pictogram toe zolang er geen goedgekeurd logo-asset is.

### Primaire knop

- Blauwe achtergrond.
- Witte tekst.
- Capsulevorm (radius 20 px).
- Compacte schaduw.
- Duidelijk werkwoord als label.
- Pijl of plus-icoon mag de handeling ondersteunen.
- Hoverstatus gebruikt een donkerdere blauwtint.

Voorbeelden:

- `Nieuwe order`
- `Factuur maken`
- `Rapport exporteren`

### Kaarten en panelen

- Witte achtergrond.
- Border met `--line`.
- Radius van 11 px.
- Geen schaduw; alleen het mobiele menu zweeft en heeft er een.
- Inhoud volgt steeds: titel, optionele toelichting en primaire informatie.

### Snelkoppeling

Een snelkoppeling bevat:

1. een lichtblauw volgnummer-vlak;
2. een korte titel;
3. een korte omschrijving en een blauwe navigatie-indicator.

Bij hover beweegt de kaart maximaal 3 px omhoog.

### KPI-kaart

Een KPI-kaart bevat:

1. label en icoon;
2. grote numerieke waarde;
3. trend, periode of waarschuwing.

Positieve trends zijn groen. Aandachtspunten zijn oranje of rood.

### Statuslabel

- Capsulevorm.
- Korte statusnaam.
- Combinatie van tekst- en achtergrondkleur.
- Geen pictogram nodig wanneer de status als tekst duidelijk is.

### Tabellen

- Kolomkoppen zijn klein en gedempt.
- Rijen hebben subtiele horizontale lijnen.
- De primaire identificatie, zoals ordernummer, staat vet.
- Status staat in een statuslabel.
- Acties staan duidelijk bij de bijbehorende rij of sectie.
- Op mobiel mag de tabel horizontaal scrollen.

### Formuliervelden

- Hoogte: circa 48 px.
- Witte achtergrond en subtiele border.
- Icoon links is optioneel.
- Focusstatus: blauwe border met zachte blauwe focusring.
- Labels staan altijd boven het veld.
- Placeholdertekst is lichter dan ingevoerde tekst.
- Foutmeldingen staan in een lichtrood vlak onder de velden.

### Formulierfeedback

Formulieren tonen invoervelden en labels in een duidelijke leesvolgorde. Validatie- en serverfouten verschijnen als tekst in een foutvlak; succesmeldingen zijn zichtbaar na het opslaan.

## 7. Iconen

- Gebruik eenvoudige lijniconen met afgeronde uiteinden.
- Standaard lijngewicht: ongeveer 1.8 px.
- Gebruik `currentColor`, zodat iconen de kleur van hun component overnemen.
- Standaardmaten: 17, 18, 20, 22 of 24 px.
- Gebruik geen emoji als interface-icoon.

Beschikbare concepten zijn onder andere:

- capsule;
- gebruiker en klanten;
- orders en klembord;
- voorraad en doos;
- levering en vrachtwagen;
- factuur;
- rapportagegrafiek;
- kalender;
- telefoon;
- menu.

## 8. Toegang

De huidige schoolapplicatie heeft geen inlog- of rollenbeheer. De navigatie is daarom voor alle gebruikers gelijk. Voeg geen visuele rolbeperkingen toe zonder eerst echte autorisatie in de backend te implementeren.

## 9. Responsive gedrag

### Desktop

- Volledige navigatie.
- Meerkoloms dashboards.
- Loginpagina in twee kolommen.

### Tablet — tot circa 1100 px

- Kleinere navigatieafstanden.
- KPI-grid in twee kolommen.
- Dashboardpanelen worden gecombineerd of gestapeld.
- Profielinformatie wordt compacter.

### Mobiel — tot circa 760 px

- Navigatie blijft zonder JavaScript volledig bereikbaar en kan horizontaal scrollen.
- Hero en loginvlakken staan onder elkaar.
- Dashboard gebruikt één kolom.
- Pagina-padding wordt 20–24 px.
- Actiegebieden mogen de volledige breedte gebruiken.

### Klein mobiel — tot circa 430 px

- KPI-grid gebruikt één kolom.
- Tabellen scrollen horizontaal.
- Grote koppen worden verkleind.
- Secundaire informatie mag worden verborgen wanneer deze niet essentieel is.

## 10. Schrijfstijl

- Schrijf in helder Nederlands.
- Gebruik korte, actieve labels.
- Begin acties met een werkwoord.
- Gebruik consistente termen uit het bedrijfsproces.
- Gebruik bijvoorbeeld altijd `Leveringen`, niet afwisselend `Transport` of `Bezorging`.
- Gebruik statussen zoals `Nieuw`, `Wordt verzameld`, `Backorder`, `Ingepakt`, `Verstuurd` en `Afgeleverd`.
- Vermijd technische termen in de gebruikersinterface.

## 11. Implementatie

De kern van het designsysteem staat in:

- `templates/base.html`: documentstructuur, navigatie en de content-container;
- `static/css/ui-system.css`: tokens, typografie, header, paginaopbouw, panelen, formulieren, knoppen, tabellen, statuslabels en responsive basis;
- `static/css/order-status-report.css`: het referentiescherm Rapportages;
- `static/css/operations.css`, `customers.css`, `products.css`, `deliveries.css` en `order-status-notification.css`: alleen de interne layout van specifieke schermen, geen containers of kaartstijlen.

Nieuwe schermen moeten bestaande tokens en componentpatronen hergebruiken voordat er nieuwe varianten worden toegevoegd.
