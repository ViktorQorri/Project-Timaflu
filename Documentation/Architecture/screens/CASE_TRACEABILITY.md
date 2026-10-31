# Casuscontrole van de schermontwerpen

## Bronnen en voorrang

De bron voor de ontwerpeisen is de inhoud van:

1. Documentation/brightspace/Current-processes.md (huidige bedrijfsprocessen).
2. Documentation/brightspace/Desired-process.md (gewenste situatie).
3. Documentation/brightspace/Product-description.md (formele product- en inlevereisen).

De 28 activity diagrams zijn gebruikt om schermen en processtappen herkenbaar te koppelen, **niet als bron voor extra bedrijfsregels**. Userstories en issuebeschrijvingen zijn geen leidend acceptatiecriterium. Als een diagram of userstory afwijkt van de casus, dient de casus als uitgangspunt en moet de afwijking worden besproken in plaats van ongemerkt een extra regel in te voeren.

## Controle per verplicht proces

| Proces | Casusvereisten in deze ontwerp-PR | Schermen |
|---|---|---|
| Verkoop | Telefonische bestelling, klantgegevens, voorraadcontrole, orderregels, kortingen, klantakkoord, afleverdatum/dagdeel, mogelijke backorder en orderstatus | AD04-AD07, AD28 |
| Inkoop | Minimumvoorraad, goedkoopste fabrikant eerst, telefonisch volgende fabrikant benaderen, contactpersoon/telefoon, koppeling verwijderen, product verwijderen, interne bestellijst beheren, nieuw medicijn ter directieoordeel | AD01-AD03, AD24 |
| Orderpicking | Robots per gang, deelorders, unieke verzamelbakcode, meerdere bakken per order, transport naar distributie en overzicht van complete orders | AD08-AD11, AD22-AD23 |
| Distributie | Gewone en spoedritten, leverdatum/dagdeel, koeriercontact, digitale ontvangst, eerste en tweede poging, terughalen goederen en bijwerken rooster | AD12-AD15, AD26-AD27 |
| Administratie | Wekelijkse facturen van werkelijk geleverde producten, verplichte factuuropmaak, 9% btw, kortingsstappen, factuurherinnering, betalingsregeling/incasso, geen deelbetaling, leveranciersfacturen | AD16-AD19, AD25 |
| Acquisitie | Persoonlijk bezoek, bezoekregistratie, opvolgen na minimaal een maand zonder order, 10% extra korting op eerste bestelling bij belangstelling en toestemming voor klantaccount | AD20-AD21 |

## Extra gecontroleerde casusdetails

- **AD02:** Drie verschillende gevolgen zijn zichtbaar: een fabrikant-medicijnkoppeling verwijderen, het medicijn zelf verwijderen en het medicijn uit de interne bestellijst halen. Deze handelingen zijn niet onderling uitwisselbaar.
- **AD05:** De verkoopmedewerker doet de telefonische order. Het scherm toont de uit klantgegevens afkomstige adressen, voorraadcontrole, berekende kortingen en klantakkoord. Zonder akkoord worden geen voorraadreserveringen vastgelegd.
- **AD12:** Bij ontvangst toont het ontwerp een afzonderlijk handtekeninggedeelte. De statische HTML bevat geen werkende handtekeningsoftware.
- **AD16:** Het conceptfactuurscherm toont datum, factuurnummer, Timaflu en klant met adressen, de geleverde regels en alle negen voorgeschreven bedrag- en kortingsregels uit de productbeschrijving. Onbekende bedrijfsgegevens en bedragen zijn bewust niet ingevuld.
- **AD27:** Het ontwerp laat het bezorgrooster op datum, een tweede poging later dezelfde dag en de opvolging na twee mislukte bezorgingen zien. Extra kosten horen bij de bestelling.
- **AD18:** Openstaande facturen volgen de casus: herinnering na één week, tweede herinnering na twee weken en telefonisch contact met voorstel voor een betalingsregeling na drie weken; bij weigering volgt incasso en een bestellingsblokkade.
- **AD24:** De productregistratie na directiegoedkeuring bevat de productcatalogusgegevens uit de casus, waaronder werkzame stoffen, bestelcode, verpakkingsgegevens, omschrijvingen en minimale bestelhoeveelheid.
- **AD26:** Reguliere koeriers halen uiterlijk om 17.00 uur op; bij spoed is ophalen na 17.00 uur mogelijk als een koerier beschikbaar is. De casus noemt daarnaast de reguliere levertijd en de maximale spoedtermijn.
- **AD28:** Jaarlijkse klantenkorting volgt de omzetstaffels van de casus. Het overzicht is read-only, de berekening op 31 december is een systeemtakenproces.

## Documentverschil dat niet door de ontwerp-PR wordt verzonnen

In Product-description.md staat bij de kortingberekening kortweg dat de *eerste bestelling van een klant* 10% korting krijgt. De casus Current-processes.md, onderdeel Acquisitie, beschrijft die 10% concreet als een **extra acquisitieaanbod na minimaal een maand zonder bestelling**, onder de voorwaarde dat een klantaccount mag worden aangemaakt. De schermontwerpen tonen daarom de eenmalige korting als voorwaardelijk onderdeel; ze kennen niet automatisch een korting toe aan elke eerste order. Dit verschil vraagt om afstemming bij de implementatie, niet om een nieuw bedrijfsregeltje in deze ontwerpen.

## Afbakening en controle

Deze repositorybestanden zijn **statische schermontwerpen**. Er is geen JavaScript, er worden geen verzonnen klantrecords of betalingen getoond en de knoppen zijn uitgeschakeld. De daadwerkelijk werkende frontend is een ander opleverdeel. De regressietests controleren structuur, relevante casuseisen en responsiviteit; ze vervangen geen handmatige opleverreview door een tweede teamlid.
