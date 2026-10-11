# Verschillen huidige vs. gewenste situatie

## Algemeen
Het huidige proces is volgens de medewerkers niet verkeerd. Ze willen alleen af van:
- het geklieder in Excel-formulieren
- het handmatig doorgeven van informatie
- pak- en distributiebonnen
- papierwerk, mails en berichtjes

Met ICT moet het werk gestroomlijnder worden.

### Wat níét verandert
- **Telefonische verkoop blijft.** Persoonlijk contact is belangrijk voor Timaflu. Internetverkoop komt misschien later, maar valt nu buiten scope.
- Niet genoemd in de gewenste situatie, dus (voorlopig) ongewijzigd: kortingsregels, koeriersregio's, acquisitie, beoordeling van nieuwe medicijnen door inkoop/directie.

### Overkoepelende eisen
- **Betrouwbare leverancier:** bij een bestelling moet met zekerheid gezegd kunnen worden of een medicijn op voorraad is.
- **Orderstatus:** de klant moet precies kunnen weten hoe zijn order ervoor staat. Voorbeelden van statussen (lijst is niet compleet, bron zegt "etc."):
  - wordt verzameld
  - verstuurd
  - backorder
  - afgeleverd
- **Eén centrale plek** voor adressen, bestellingen, klantinformatie en fabrikantinformatie.
- **Geen schrijf- en rekenfouten** meer (o.a. bij de kortingsberekening).

## Vergelijking per onderdeel

| Onderdeel | Huidig | Gewenst |
|---|---|---|
| Bestelling opnemen | Telefonisch, genoteerd in Excel-orderformulier, geprint en in een bak gelegd | Telefonisch, vastgelegd in het systeem; geen printen meer |
| Voorraad bij bestelling | Verkoop weet niet precies wat er op voorraad is; ontbrekende producten blijken pas bij het verzamelen | Verkoop ziet direct en met zekerheid of een product op voorraad is |
| Kortingsberekening | Handmatig (5% bij ≥ €500 + klantkorting o.b.v. jaaromzet); veel fouten | Automatisch berekend door het systeem |
| Leveringsmoment | Vóór 16:00 besteld = volgende dag vóór 12:00 geleverd; klant heeft geen keuze | Klant geeft een **datum en dagdeel (ochtend/middag)** op waarop hij de bestelling kan ontvangen |
| Orderstatus | Onbekend voor klant en verkoop | Orderstatus altijd inzichtelijk |
| Verzamelen | 3 magazijnmedewerkers verzamelen met een winkelwagentje vanaf papieren orderformulier | Robots verzamelen volautomatisch (zie [Magazijn](#magazijn)) |
| Distributiehoek | Sticker met handgeschreven adres en klantnaam, handmatig koeriersoverzicht | Verzamelbakken per order samenvoegen, scherm toont welke order in welke bakken zit |
| Voorraadbeheer | Nattevingerwerk; magazijn meldt op gevoel aan inkoop wat besteld moet worden | Systeem bewaakt de minimale voorraad per medicijn |
| Inkoop | Interne bestelformulieren op papier, per product handmatig de goedkoopste fabrikant zoeken | Overzicht van producten onder minimumvoorraad, bijbestellen bij goedkoopste leverancier |
| Koerier | Geen telefoonnummer op sticker, koeriersoverzicht op papier | Levermoment en telefoonnummer opzoeken, toegewezen (spoed)ritten zien, aflevering bevestigen |
| Administratie | Factuur op basis van papieren formulieren, wekelijks handmatig bundelen | Inzicht in afgeleverde (te factureren) orders en onbetaalde facturen |

## Magazijn
- Robots nemen het verzamelen van orders over.
- Elke gang krijgt **één robot**, die alleen producten uit zijn eigen gang verzamelt.
- Daardoor kunnen **meerdere robots aan één order** werken.

### Verzamelproces (per robot)
1. Het systeem splitst de order op in deelorders per gang. *(Afgeleid: staat niet letterlijk in de bron, maar volgt uit "één robot per gang".)*
2. De robot ontvangt een deelorder.
3. De robot pakt een verzamelbak.
4. De robot scant de unieke code van de verzamelbak en stuurt deze naar het systeem (zo is bekend welke bak bij welke order hoort).
5. De robot verzamelt de medicijnen.
6. Zit de verzamelbak vol, dan zet de robot hem op de rollerbaan richting de distributiehoek.
   - **Deelorder compleet:** de robot meldt aan het systeem dat hij klaar is en krijgt een nieuwe order → terug naar stap 2.
   - **Deelorder niet compleet:** de robot pakt een nieuwe verzamelbak → terug naar stap 3.

> **Open vraag voor de opdrachtgever:** de bron beschrijft alleen wat er gebeurt als de bak *vol* is. Wat gebeurt er met een bak die niet vol is terwijl de deelorder al compleet is? (Aanname: die gaat ook de rollerbaan op.)

### Distributiehoek
1. De verzamelbakken van een order worden samengevoegd. Op een scherm is te zien welke order in welke verzamelbakken zit.
2. De medicijnen worden verpakt in verhuisdozen.
3. De order wordt gedistribueerd.

## Voorraad & inkoop
- Per medicijn wordt een **minimale voorraad** vastgelegd en door het systeem **bewaakt**.
- De inkoopmedewerker ziet in het systeem welke producten onder de minimumvoorraad zitten.
- Deze producten worden bijbesteld bij de **goedkoopste leverancier**.

## Koeriers
- **Levermoment** (datum + dagdeel) van een bestelling kunnen opzoeken.
- **Telefoonnummer** van een klant kunnen opzoeken, zodat de klant gebeld kan worden als de koerier voor een gesloten deur staat. *(Lost op: nu staat het nummer niet op de sticker en rijdt de koerier onnodig op en neer.)*
- Makkelijk kunnen zien welke **(spoed)ritten** aan hem zijn toegewezen.
- Kunnen aangeven wanneer een bestelling **daadwerkelijk is afgeleverd** (koppelt aan orderstatus *afgeleverd* en aan facturatie).

## Administratie
- Inzicht in welke orders zijn **afgeleverd** en dus **gefactureerd** moeten worden.
- Inzicht in welke **facturen nog niet betaald** zijn, zodat er actie ondernomen kan worden (herinnering, betalingsregeling, incasso).
