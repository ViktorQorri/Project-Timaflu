# Timaflu Design System

Dit document beschrijft het visuele systeem en de interfacepatronen van het Timaflu-medewerkersportaal. Het is gebaseerd op de huidige implementatie in `src/App.tsx` en `src/index.css`.

## 1. Ontwerpprincipes

Het portaal moet:

- betrouwbaar en professioneel aanvoelen;
- medische informatie rustig en overzichtelijk presenteren;
- belangrijke statussen direct herkenbaar maken;
- medewerkers alleen functies tonen die bij hun rol horen;
- ook bij veel operationele informatie scanbaar blijven;
- goed werken op desktop, tablet en mobiel.

De visuele stijl combineert een donkerblauwe basis met helder blauw voor interactie, lichte achtergronden en subtiele borders.

## 2. Kleuren

### Basiskleuren

| Token | Waarde | Gebruik |
|---|---:|---|
| `--navy` | `#123653` | Primaire tekst, footer en donkere vlakken |
| `--blue` | `#0f70b7` | Primaire acties, links, actieve navigatie en iconen |
| `--sky` | `#eaf5fb` | Lichte merkachtergronden en icoonvlakken |
| `--muted` | `#6d8292` | Secundaire tekst |
| `--line` | `#dce8ef` | Borders en scheidingslijnen |
| `--bg` | `#f5f8fa` | Algemene pagina-achtergrond |
| Wit | `#ffffff` | Kaarten, tabellen en invoervelden |

### Statuskleuren

| Status | Tekst | Achtergrond | Voorbeelden |
|---|---:|---:|---|
| In behandeling | `#0e70b8` | `#e5f2fb` | Wordt verzameld, onderweg, openstaand |
| Positief | `#267e55` | `#e3f5eb` | Afgeleverd, betaald, actief, op voorraad |
| Waarschuwing | `#ae6a18` | `#fff1dc` | Backorder, bijna op, vervallen |
| Kritiek | `#bd4646` | `#fde7e6` | Onder minimum, foutmelding |

Gebruik statuskleuren alleen voor betekenisvolle feedback. Gebruik nooit alleen kleur: toon altijd ook een tekstlabel.

## 3. Typografie

### Lettertypen

- **Manrope** — koppen, merknaam en belangrijke cijfers.
- **DM Sans** — lopende tekst, navigatie, formulieren en tabellen.

De fonts worden geladen via Google Fonts in `src/index.css`.

### Typografische hiërarchie

| Element | Richtlijn |
|---|---|
| Hero-titel | Manrope, 34–54 px, bold, compacte regelafstand |
| Paginatitel | Manrope, 36 px, bold |
| Sectietitel | Manrope, 25 px, bold |
| Kaarttitel | Manrope, 13–15 px, bold |
| Lopende tekst | DM Sans, 13–15 px |
| Tabeltekst | DM Sans, 9–11 px |
| Eyebrow | 9–10 px, uppercase, bold, letterspatiëring van circa 2 px |
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
| Buttons en velden | 7–8 px |
| Icoonvlakken | 8–9 px |
| Kaarten en panelen | 10–12 px |
| Statuslabels | 20 px |
| Profielfoto/indicator | 50% |

## 5. Layout

### Navigatie

- Hoogte desktop: 78 px.
- Logo links, navigatie gecentreerd en gebruikersprofiel rechts.
- Actieve pagina krijgt blauwe tekst en een blauwe onderlijn.
- Alleen pagina's waarvoor de huidige rol rechten heeft worden getoond.
- Op mobiel wordt de hoofdnavigatie vervangen door een menuknop.

### Contentbreedte

- Maximale contentbreedte: 1440 px.
- Content staat horizontaal gecentreerd.
- De horizontale paginamarge schaalt mee met de viewport.

### Grids

- Snelkoppelingen gebruiken een automatisch passende grid met een minimale kaartbreedte van 140 px.
- KPI-kaarten gebruiken vier kolommen op desktop, twee op tablet en één op kleine mobiele schermen.
- Dashboardpanelen gebruiken maximaal drie kolommen en klappen responsief onder elkaar.

## 6. Componenten

### Merklogo

Het Timaflu-logo bestaat uit:

- een blauw, afgerond vlak;
- een wit capsule-icoon;
- de woordmerkcombinatie `tima` + blauw `flu`.

Op donkere achtergronden wordt het icoonvlak wit met een blauw icoon.

### Primaire knop

- Blauwe achtergrond.
- Witte tekst.
- Radius van 8 px.
- Compacte schaduw.
- Duidelijk werkwoord als label.
- Pijl of plus-icoon mag de handeling ondersteunen.
- Hoverstatus gebruikt een donkerdere blauwtint.

Voorbeelden:

- `Nieuwe order`
- `Factuur maken`
- `Inloggen`
- `Rapport exporteren`

### Kaarten en panelen

- Witte achtergrond.
- Border met `--line`.
- Radius van 10–12 px.
- Schaduw alleen bij hover of om een zwevend element te benadrukken.
- Inhoud volgt steeds: titel, optionele toelichting en primaire informatie.

### Snelkoppeling

Een snelkoppeling bevat:

1. een lichtblauw icoonvlak;
2. een korte titel;
3. een blauwe pijl rechtsonder.

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
- Bewerkbare rollen zien een rijmenu; alleen-lezenrollen niet.
- Op mobiel mag de tabel horizontaal scrollen.

### Formuliervelden

- Hoogte: circa 48 px.
- Witte achtergrond en subtiele border.
- Icoon links is optioneel.
- Focusstatus: blauwe border met zachte blauwe focusring.
- Labels staan altijd boven het veld.
- Placeholdertekst is lichter dan ingevoerde tekst.
- Foutmeldingen staan in een lichtrood vlak onder de velden.

### Inlogscherm

Het inlogscherm bestaat op desktop uit twee vlakken:

- links: merkverhaal, donkere gradient en vertrouwenstekst;
- rechts: inlogformulier en informatie over demo-accounts.

Op mobiel staan deze vlakken onder elkaar.

Voor het huidige prototype zijn inlognaam en wachtwoord beide gelijk aan de functienaam. Deze gegevens worden niet opgeslagen.

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

## 8. Rollen en zichtbaarheid

De interface past navigatie, snelkoppelingen, dashboardinformatie en bewerkacties aan de ingelogde rol aan.

| Rol | Zichtbare onderdelen | Bewerkrechten |
|---|---|---|
| Verkoopmedewerker | Home, klanten, orders, voorraad | Klanten en orders |
| Magazijnmedewerker | Home, orders, voorraad | Orders en voorraad |
| Inkoopmedewerker | Home, voorraad, rapportages | Voorraad |
| Administratiemedewerker | Home, orders, facturen, rapportages | Facturen |
| Koerier | Home, klanten, leveringen | Leveringen |
| Accountmanager | Home, klanten, orders | Klanten |
| Directie | Alle onderdelen | Alleen lezen |
| Admin | Alle onderdelen | Volledig beheer |

Toegangsbeperkingen moeten visueel consequent zijn:

- verberg pagina's zonder toegang uit de navigatie;
- verberg niet-toegestane snelkoppelingen;
- verberg primaire bewerkknoppen bij alleen-lezenrechten;
- verberg rijmenu's wanneer een gebruiker niet mag bewerken;
- toon geen dashboardgegevens die buiten de rol vallen.

> De huidige versie is een frontendprototype. Voor productie moeten dezelfde rechten ook in de backend worden afgedwongen.

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

- Navigatie wordt een menuknop.
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
- Gebruik statussen zoals `Wordt verzameld`, `Verstuurd`, `Backorder` en `Afgeleverd`.
- Vermijd technische termen in de gebruikersinterface.

## 11. Implementatie

De kern van het designsysteem staat in:

- `src/index.css` — kleuren, typografie, layouts, componentstijlen en responsive gedrag;
- `src/App.tsx` — iconen, componentstructuur, pagina-inhoud en rolrechten.

Nieuwe schermen moeten bestaande tokens en componentpatronen hergebruiken voordat er nieuwe varianten worden toegevoegd.
