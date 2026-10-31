# Casuscontrole van de schermontwerpen

## Bronnen en voorrang

De bron voor de ontwerpeisen is de inhoud van:

1. Documentation/brightspace/Current-processes.md (huidige bedrijfsprocessen).
2. Documentation/brightspace/Desired-process.md (gewenste situatie).
3. Documentation/brightspace/Product-description.md (formele product- en inlevereisen).

De **gewenste situatie** beschrijft wat Timaflu na digitalisering moet kunnen. Waar de gewenste situatie een werkwijze uit de huidige situatie vervangt, volgt het ontwerp de gewenste situatie. Bestaande procesregels die niet zijn vervangen, blijven uitgangspunt. De productbeschrijving bevat de formele inlevereisen. De 28 activity diagrams zijn gebruikt om schermen en processtappen herkenbaar te koppelen, **niet als bron voor extra bedrijfsregels**. Userstories en issuebeschrijvingen zijn geen leidend acceptatiecriterium. De README bevat per activity diagram directe verwijzingen naar de relevante paragrafen in de casus.

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
- **AD05:** De verkoopmedewerker doet de telefonische order. Het scherm toont besteldatum, de uit klantgegevens afkomstige adressen, artikel en minimale bestelhoeveelheid, spoedindicatie, voorraadcontrole, berekende kortingen en klantakkoord. Zonder akkoord worden geen voorraadreserveringen vastgelegd. Bij een eventueel later vastgesteld tekort kan verkoop de klant per ontbrekend artikel laten kiezen of dit later geleverd moet worden.
- **AD06:** Het ontwerp toont de in de gewenste situatie genoemde voorbeelden van orderstatus (wordt verzameld, verstuurd, backorder en afgeleverd); het systeem blijft de werkelijke status bepalen.
- **AD09:** Het adreslabel gebruikt klantnaam en afleveradres; de gewenste situatie schrijft het apart kunnen opzoeken van het telefoonnummer voor (AD15), niet dat het nummer op het adreslabel moet staan.
- **AD12:** Bij ontvangst toont het ontwerp een afzonderlijk handtekeninggedeelte. De statische HTML bevat geen werkende handtekeningsoftware.
- **AD16:** Het conceptfactuurscherm toont datum, factuurnummer, Timaflu en klant met adressen, de geleverde regels en alle negen voorgeschreven bedrag- en kortingsregels uit de productbeschrijving. Onbekende bedrijfsgegevens en bedragen zijn bewust niet ingevuld.
- **AD23:** Een medicijn kan in meerdere magazijnlocaties liggen; één magazijnlocatie bevat geen verschillende medicijnen. Een robot werkt alleen in de eigen gang.
- **AD27:** Het ontwerp laat het bezorgrooster op datum, een tweede poging later dezelfde dag en de opvolging na twee mislukte bezorgingen zien. De koerier kan het telefoonnummer in het systeem opzoeken, meldt de pogingen en laat bij een gesloten deur bericht achter. **Verkoop** legt de nieuwe afspraak, uitleg en eventuele extra kosten vast.
- **AD18:** Openstaande facturen volgen de casus: herinnering na één week, tweede herinnering na twee weken en telefonisch contact met voorstel voor een betalingsregeling na drie weken; bij weigering volgt incasso en een bestellingsblokkade.
- **AD24:** De productregistratie na directiegoedkeuring bevat de productcatalogusgegevens uit de casus, waaronder werkzame stoffen, bestelcode, verpakkingsgegevens, omschrijvingen en minimale bestelhoeveelheid. **Minimumvoorraad voor voorraadbewaking** is een ander gegeven dan de minimale bestelhoeveelheid en is afzonderlijk opgenomen, conform de gewenste situatie.
- **AD26:** Reguliere koeriers halen uiterlijk om 17.00 uur op; bij spoed is ophalen na 17.00 uur mogelijk als een koerier beschikbaar is en geldt de maximale bezorgtijd van drie uur. De oude standaardlevering (voor 16.00 uur besteld, volgende dag voor 12.00 uur) is geen verplicht af te dwingen afspraak voor alle nieuwe orders, omdat de **gewenste situatie** juist een door de klant gekozen datum en dagdeel mogelijk maakt.
- **AD28:** Jaarlijkse klantenkorting volgt de omzetstaffels van de casus. Het overzicht is read-only, de berekening op 31 december is een systeemtakenproces.

## Documentverschil dat niet door de ontwerp-PR wordt verzonnen

In Product-description.md staat bij de kortingberekening kortweg dat de *eerste bestelling van een klant* 10% korting krijgt. De casus Current-processes.md, onderdeel Acquisitie, beschrijft die 10% concreet als een **extra acquisitieaanbod na minimaal een maand zonder bestelling**, onder de voorwaarde dat een klantaccount mag worden aangemaakt. De schermontwerpen tonen daarom de eenmalige korting als voorwaardelijk onderdeel; ze kennen niet automatisch een korting toe aan elke eerste order. Dit verschil vraagt om afstemming bij de implementatie, niet om een nieuw bedrijfsregeltje in deze ontwerpen.

## Afbakening en controle

Deze repositorybestanden zijn **statische schermontwerpen**. Er is geen JavaScript, er worden geen verzonnen klantrecords of betalingen getoond en de knoppen zijn uitgeschakeld. De daadwerkelijk werkende frontend is een ander opleverdeel. De regressietests controleren structuur, relevante casuseisen en responsiviteit; ze vervangen geen handmatige opleverreview door een tweede teamlid. De beoordelingsmatrix toetst de **totale softwareoplossing** (database, backend en frontend); alleen een geslaagde beoordeling van deze ontwerp-PR bewijst niet dat de hele applicatie aan alle eisen voldoet.
