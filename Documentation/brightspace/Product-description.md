# Productbeschrijving

Hieronder kun je vinden wat we per product van jullie verwachten. Om te weten in welke weken deze producten aan bod komen, kun je hier klikken voor de weekplanning.

## Projectaanpak (summatief)

Maak een document waarin jullie opnemen:

- Hoe gaan jullie het samenwerken aanpakken?
  (hier mogen jullie ook de samenwerkingsafspraken in meenemen)
- Welke taken zijn er?
- Wie pakt welke taken op?
- Wanneer worden taken opgepakt?
- Wie heeft hoe lang aan welke taak gewerkt?
  **LET OP! Het samenwerken staat in dit project centraal, daarom moet iedereen aan <u>alle</u> deelproducten hebben meegewerkt. Dit moeten jullie laten zien in deze urenverantwoording.**

Dit is een levend document dat jullie uiteindelijk inleveren. Elke week vraagt jullie projectdocent inzicht in jullie projectproces. Zorg dus dat dit document te allen tijde up to date is. Het document wordt mede gebruikt om jullie individuele inbreng te bepalen.

## Eindproducten (summatief)

Hier vinden jullie informatie over de eindproducten waar jullie op beoordeeld zullen worden.

De scope van het project omvat de volgende bedrijfsprocessen:

- Verkoop van producten
- Inkoop van producten
- Orderpicking
- Distributie
- Administratie en facturatie
- Acquisitie

De scope van het project omvat **NIET**:

- Het ontvangen van nieuwe voorraad.

### Database met queries

Maak een goed ontworpen werkende en genormaliseerde database. Zorg dat deze online staat en gevuld is met voldoende relevante data. Schrijf vervolgens queries die ondersteunend zijn aan de frontend. Maak daarvoor per scherm de benodigde queries.

> **Voorbeeld**
> Een klant belt Timaflu om een bestelling te plaatsen. Hiervoor moet de verkoopmedewerker de klant in het systeem opzoeken. De verkoopmedewerker heeft een scherm om dit te doen. Dit scherm wordt gevuld door middel van een query.

**Technieken**

- MySQL

**In te leveren**

- Jullie uiteindelijke EER, kloppend aan de huidige werkende database.
- Een document met daarin duidelijk per scherm de benodigde queries. Bij elke query toon je de output die jullie database teruggeeft.

### Backend

Maak een backend in python die de frontend ondersteunt en gebruik maakt van de database. Zorg dat alle classes en methods aanwezig zijn. Hiervan mogen de classes en methods leeg zijn, met uitzondering van onderstaand:

**1. Berekenen van de korting van de bestelling (verkoopproces)**

- Invoer: klantnaam, klantadres en optelsom van de bestelde producten
- Bereken eventuele bestellingskorting
- Eerste bestelling van klant -> 10% korting
- Haal de bestellingskorting van het bedrag af
- bereken klantenkorting van afgelopen jaar op basis van aangekochte producten
- Haal de klantenkorting er af
- Uitkomst: totaal bedrag + gegeven korting.

**2. Wanneer een product niet op voorraad is (inkoopproces)**

- Invoer: Productnaam
- Uitkomst: lijst met leveranciers
  - Leveranciers die het medicijn het goedkoopst kan leveren, bovenaan.
  - Inclusief contactpersoon en telefoonnummer
  - Mogelijkheid tot verwijderen van leverancier van product
  - Mogelijkheid tot verwijderen van product

**3. Wanneer een klant niet betaald heeft (administratie)**

- Invoer: klantnummer
- Uitvoer: factuur met volgende opmaak:

```text
Datum                                                   factuurnummer
------------------------------------------------------------------
Timaflu                                                 naam bedrijf
Adres timaflu                                           adres bedrijf
------------------------------------------------------------------
Aantal              prijs per eenheid                   regel totaal
..                  ..                                  ..
..                  ..                                  ..
..                  ..                                  ..
                    Totaal excl btw                     ..
                    9% btw                              ..
                    Totaal incl btw                     ..
                    Bestellingskorting                  ..
                    Totaal incl bestellingskorting      ..
                    Eenmalige korting                   ..
                    Totaal incl eenmalige korting       ..
                    Klantenkorting                      ..
                    Totaal incl klantenkorting          ..
```

**4. Wanneer een klant bij levering niet aanwezig is (distributie)**

- Invoer: datum
- Uitkomst: rooster met tijden en klanten
  - Klantnaam, adres, Telefoonummer en contactpersoon
  - Niet aanwezig: markeren voor terugkomen op zelfde dag -> rooster aanpassen
    - Bij terugkomst: wel aanwezig: markeren afgeleverd
    - Bij terugkomst: niet aanwezig: markeren niet afgeleverd afgeleverd

**5. Als een potentiële klant nog geen bestelling heeft geplaatst (acquisitie)**

- Invoer: langs geweest bij: bedrijfsnaam, contactpersoon, contactgevens, adres en datum bezoek
- Uitvoer: bezoek toegevoegd
- Invoer: ”overzicht acquisitie”
- Uitvoer: Alle bedrijven die nog niet hebben besteld, en waar een maand of langer geleden iemand is langs geweest.
  - Contactpersoon + contactgevens
  - Optie: 10% korting + aanmaken klantaccount

Je mag voor het schrijven van de methods voorbeelddata (dummydata) gebruiken.

Zorg dat de code leesbaar, onderhoudbaar en gedocumenteerd is en dat er geen onnodige afhankelijkheden bestaan.

**Technieken**

- Python
- UML

**In te leveren**

- Jullie uiteindelijke klassendiagram, kloppend aan de huidige backend.
- Zipje van de code.

### Frontend

Maak een website met HTML en CSS, zonder libraries of JS etc, die bovenstaande bedrijfsprocessen ondersteunt. Zorg dat alle processen goed werken op desktopgrootte. De schermen voor de processen orderpicking en distributie zijn responsive en werken ook op mobiele apparaten.

**Technieken**

- HTML
- CSS

**In te leveren**

Een zipbestand met jullie website.

## Projectontwerp (voorwaardelijk)

Het project heeft verschillende voorwaardelijke ontwerpproducten. Deze moet je als groep maken en inleveren en dienen als ontwerp voor jullie eindproducten.

### Activity Diagrams

Maak activity diagrams van de gewenste situatie van de onderstaande processen. Je moet hiervoor zowel de informatie uit de casus gebruiken over de huidige situatie als de gewenste situatie.

- **Verkoop van producten**
- **Inkoop van producten**
- **Orderpicking**
  Door middel van robots.
- **Distributie**
  Wanneer orders klaargezet zijn voor verzending, zorgen de koeriers voor de bezorging bij de klant.
- **Administratie en facturatie**
  Wekelijks wordt de administratie bijgewerkt.
- **Acquisitie**
  Het actief werven van apotheken als nieuwe klanten.

### Use Cases

**Diagram**
Maak twee use case diagrammen:

- Voor het informatiesysteem dat je gaat ontwikkelen voor Timaflu. Dit informatiesysteem ondersteunt de medewerkers bij uitvoer van de bovenstaande bedrijfsprocessen.
- Voor één robot.

**Beschrijvingen**
Maak van alle primaire use cases ook een use case beschrijving. Maak in deze beschrijvingen zo veel mogelijk gebruik van de activity diagrams die je al gemaakt hebt (traceability).

### EER

Maak het enhanced entity-relationship diagram voor de nieuwe software die je gaat ontwikkelen voor Timaflu. Alle relevante stappen uit bovenstaande processen moeten hierin meegenomen worden.

**Let op**
Zorg dat je aandacht geeft aan het normaliseren van de database.

Dit wordt een omvangrijk EER!

### Schermontwerpen

Maak bij ieder activiteitendiagram de bijbehorende schermen. Denk daarbij per bedrijfsproces goed na welke stappen van de bedrijfsprocessen je uit wil voeren met het toekomstige informatiesysteem. Deze schermontwerpen vormen de basis voor het ontwikkelen van jullie frontend.

**Let op**
Het kan zijn dat je meerdere schermen ontwerpt per activiteitendiagram.

### Klassendiagram

Maak het klassendiagram ter ondersteuning van het ontwikkelen van de backend. Het volgende stappenplan kan jullie helpen om daar te komen:

1. arceer alle zelfstandig naamwoorden uit de casus.
2. Beoordeel de zelfstandig naamwoorden:
   1. haal de dubbele er uit
   2. is het een class?
   3. is het een attribuut?
3. zet dit in een klassendiagram. Dat betekent dus dat je alle classes gaat maken met methodes en attributen.
4. voeg nu de juiste associaties toe.

### Sequence diagrammen

Maak sequence diagrammen voor de volgende onderdelen. Dit zijn ook de onderdelen die uitgewerkt moeten zijn in de code.

- Berekenen van de klantenkorting (verkoopproces)
- Wanneer een product niet op voorraad is (inkoopproces)
- Wanneer een klant niet betaald heeft (administratie)
- Wanneer een klant bij levering niet aanwezig is (distributie)
- Als een potentiële klant nog geen bestelling heeft geplaatst (acquisitie)
