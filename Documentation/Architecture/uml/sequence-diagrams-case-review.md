# Casus- en traceabilitycontrole van de vijf sequence diagrams

**Scope:** de vijf verplichte sequence diagrams in PR #116 (vervolg op #93), niet het volledige Timaflu-systeem. De beschrijvende teksten in de diagrammen zijn Engelstalig; domeinklassen en methoden volgen de DKD-benamingen.

## Leidende bronnen (casus, niet de userstories)

1. [Current-processes.md](../../brightspace/Current-processes.md): de oorspronkelijke Timaflu-casus, met de feitelijke bedrijfsregels in Bestellingen, Voorraad, Distributie, Administratie en Acquisitie.
2. [Desired-process.md](../../brightspace/Desired-process.md): de expliciet gevraagde toekomstige situatie.
3. [Product-description.md](../../brightspace/Product-description.md): de verplichte in- en uitvoer van de vijf backendscenario's en de in te leveren sequence diagrams.

**Deze drie documenten zijn leidend.** Bestaande userstories, aannames in tickets, afwijkende backend-PR's of eerdere diagrammen overschrijven de casus niet.

Ondersteunend voor naamgeving en traceability, maar niet leidend voor procesregels: [Process-description.md](../../brightspace/Process-description.md), [DKD](src/domain/dkd-timaflu.puml), [activity diagrams](src/activity_diagrams) en de huidige backend. Als deze botsen met de casus, staat het verschil expliciet onder de open punten; het ontwerp wordt niet stilzwijgend aan een afwijkende userstory aangepast.

## Casusafdekking per sequence diagram

| Sequence diagram | Verplichte invoer | Verplichte uitkomst en uitzonderingen | Traceability |
| --- | --- | --- | --- |
| [SD01](src/sequence_diagrams/SD01_Klantenkorting.puml) | Klantnaam, klantadres en som van bestelde artikelen | 5% bestellingskorting vanaf € 500; eenmalig 10% bij eerste order; klantkorting 5/10/15% gebaseerd op omzet uit volledig betaalde facturen in het voorgaande kalenderjaar; bedragen **na elkaar** verrekenen; totaal plus korting teruggeven. Jaarpercentage wordt op 31 december voor volgend jaar vastgesteld. Geblokkeerde klant mag niet bestellen. | AD05, AD28, DKD `Customer`, `Order`, `CustomerDiscount`; casus Bestellingen en Administratie |
| [SD02](src/sequence_diagrams/SD02_ProductNietOpVoorraad.puml) | Productnaam; in het gewenste inkoopproces ook te bestellen hoeveelheid | Bij tekort leveranciers goedkoopste eerst, mét contactpersoon en telefoonnummer. Bij uitval de volgende fabrikant benaderen, bij stopzetting leverancier-productkoppeling kunnen verwijderen. Bij géén leverancier `removeFromInternalReorderList()` uitvoeren, **niet** `removeFromAssortment()`; assortimentsverwijdering is een afzonderlijke expliciete keuze. | AD02, DKD `Product` (met `internalReorderEligible`), `SupplierOffer`, `Supplier`, `PurchaseOrder`; casus Voorraad |
| [SD03](src/sequence_diagrams/SD03_KlantHeeftNietBetaald.puml) | Klantnummer en werkelijk geleverde regels per week | Factuur met datum, nummer, beide partijen en adressen, aantal/eenheidsprijs/regeltotaal, excl. btw, 9% btw, incl. btw en drie kortingsregels met tussen- en eindtotalen. Alleen geleverd factureren; **kortingen per bestelling behouden, nooit opnieuw 5% berekenen over samengevoegd weektotaal**. Eerste/tweede herinnering, na drie weken betalingsregeling, bij weigering incasso en bestelblokkade tot volledige betaling. `checkOrderBlock()` controleert een blokkade, maar stelt die niet in. | AD16, AD18, DKD `Invoice`, `DeliveryLine`, `OrderLine`, `Order`, `PaymentReminder`, `Customer`; casus Administratie |
| [SD04](src/sequence_diagrams/SD04_KlantNietThuis.puml) | Datum | Rooster met tijd, klant, adres, contactpersoon en telefoonnummer. Na mislukte eerste poging klant bellen en een **bericht achterlaten**; tweede poging **dezelfde dag inplannen**. Tweede uitkomst pas daarna vastleggen. Bij ontvangst laat de klant expliciet tekenen vóór de registratie als afgeleverd; bij opnieuw afwezig terug naar distributie, verkoop informeren, nieuwe afspraak en extra kosten met toelichting. | AD12, AD15, AD27, DKD `Courier`, `Route`, `DeliveryAttempt`, `Order`; casus Distributie |
| [SD05](src/sequence_diagrams/SD05_PotentieleKlantGeenBestelling.puml) | Bedrijf, contactpersoon, contactgegevens, adres, bezoekdatum en overzicht acquisitie | Eerste bezoek na telefonische afspraak, met catalogus, uitleg en informatiemap. Bezoek geregistreerd; overzicht van bedrijven zonder bestelling die minimaal **één kalendermaand** geleden zijn bezocht, met contactgegevens. Alleen bij interesse en toestemming eenmalige extra 10% op de eerste bestelling registreren en klantaccount aanmaken of bestaand account hergebruiken. Geen contact meer bij geen interesse. | AD20, AD21, DKD `AcquisitionVisit`, `ProspectiveCustomer`, `Customer`; casus Acquisitie |

## Casusvoorbeelden voor de inhoudelijke review

Deze voorbeelden zijn referentiegevallen uit de casusregels. Het zijn **geen** beweringen dat alle betrokken backendfuncties al op `main` werken.

| Diagram | Invoer / gebeurtenis | Verwachte uitkomst |
| --- | --- | --- |
| SD01 | Eerste bestelling € 500, vorige jaaromzet € 0, geen eerdere eenmalige korting | Orderkorting € 25,00; eenmalig 10% van € 475,00 = € 47,50; klantkorting 5% van € 427,50 = € 21,38; eindtotaal **€ 406,12**, bij afronding op centen per kortingsstap |
| SD01 | Herhaalbestelling € 500, betaalde jaaromzet precies € 10.000 | € 25,00 orderkorting, geen eersteorderkorting, daarna 10% klantkorting van € 475,00 = € 47,50; eindtotaal **€ 427,50** |
| SD01 | Herhaalbestelling € 500, betaalde jaaromzet precies € 20.000 | € 25,00 orderkorting, daarna 15% van € 475,00 = € 71,25; eindtotaal **€ 403,75** |
| SD02 | Medicijn onder minimumvoorraad, geen enkele leverancier kan leveren | Leveranciers op prijs geordend met naam, contactpersoon en telefoonnummer; geen inkooporder; van interne bestellijst af; niet automatisch uit verkoopassortiment |
| SD03 | Van de weekorder is maar één regel werkelijk geleverd | Factuur telt alleen die afgeleverde regel; 9% btw en alle drie kortingsvelden/tussenbedragen worden getoond |
| SD03 | Twee afzonderlijke orders van € 300 worden in dezelfde week geleverd | Geen nieuwe 5% bestellingskorting door weektotalisering op € 600; alleen bij de afzonderlijke orders vastgelegde kortingen opnemen |
| SD03 | Factuur 7, 14 of 21 dagen onbetaald | Respectievelijk eerste herinnering, tweede herinnering, voorstel betalingsregeling; incasso pas na weigering; geen deelbetalingen |
| SD04 | Koerier treft niemand aan bij eerste en tweede bezoek | Tweede bezoek **dezelfde dag gepland** vóór de uitkomst; pas na tweede mislukking definitief niet afgeleverd; retour distributie, verkoop maakt nieuwe afspraak en boekt onderbouwde kosten |
| SD05 | Bezoek op 30 september, controle op 31 oktober en nog nooit besteld | Prospect komt in opvolgoverzicht, samen met contactpersoon en contactgegevens. Bezoek op 1 oktober is op 31 oktober nog niet één kalendermaand oud |
| SD05 | Prospect heeft al een account, maar nog geen order | Nog steeds opvolgbaar; geen tweede klantaccount aanmaken; eenmalige prikkel slechts één keer registreren met toestemming |

## Belangrijke afbakeningen

1. **Verwijdering uit interne bestellijst is geen assortimentsverwijdering.** De casus schrijft bij uitputting van fabrikanten alleen verwijdering van de interne bestellijst voor. Daarom voert SD02 nu expliciet `Product.removeFromInternalReorderList()` uit en is deze methode met `internalReorderEligible` toegevoegd aan het DKD. `Product.removeFromAssortment()` blijft een **andere**, expliciete medewerkerskeuze uit de productbeschrijving. De voorraad wordt niet automatisch bijgeboekt; ontvangst van nieuwe voorraad is buiten scope.
2. **Eersteorderkorting en acquisitieprikkel:** de productbeschrijving schrijft 10% voor bij de eerste bestelling. De oorspronkelijke casus biedt een bezochte potentiële klant bij opvolging 10% *extra* op die eerste bestelling, boven op de normale bestelling-/klantenkortingen. De **officiële factuuropmaak kent één veld 'Eenmalige korting'**, niet twee losstaande 10%-velden. Daarom modelleren SD01 en SD05 precies **één eenmalige eersteorderkorting van 10%**, ook als het aanbod via acquisitie is gedaan; een tweede 10% zou zonder voorgeschreven kortingsregel worden verzonnen. `Customer.oneTimeDiscountGranted = true` geeft aan dat het acquisitieaanbod beschikbaar is; `Order.oneTimeDiscountApplied` betekent dat die ene korting daadwerkelijk op een bestelling is toegepast. Beide mogen niet als twee afzonderlijke kortingen worden berekend.
3. **Verschillende open backend-PR's:** [#94](https://github.com/ViktorQorri/Project-Timaflu/pull/94) verwerkt zowel de eenmalige als de klantkorting en gebruikt volledig betaalde facturen; [#99](https://github.com/ViktorQorri/Project-Timaflu/pull/99) vermeldt expliciet dat die kortingen exclusief zijn en gebruikt orderregels voor jaaromzet, niet volledig betaalde facturen. Het laatste botst met Product-description, Current-processes en AD28. De ontwerpen in deze PR volgen de casus en AD28, **niet** deze afwijkende implementatiedetails. Deze PR brengt geen wijzigingen aan in die backend-PR's.
4. **Factuur en btw:** de vaste 9% en de presentatievolgorde komen uit de schoolopdracht. De btw-behandeling van aanvullende bezorgkosten en het eigen concrete Timaflu-straatadres zijn niet bepaald in de casus; die worden niet gefabriceerd. Voor definitieve productie-facturen is vastlegging van deze details nodig.
5. **Usecase-traceability:** het oorspronkelijke `use_cases/informatiesysteem.puml` miste de acquisitiemedewerker met diens verplichte functies en noemde ten onrechte 'Klantnummer opzoeken' voor de koerier. Deze PR voegt de acquisitie-actor met bezoekregistratie, opvolgoverzicht en opvolging toe, maakt de tweede afleverpoging expliciet en corrigeert de telefoonnummerfunctie. De bestaande UCD bevat nog geen formele `UC05`/`UC16`-nummering. Daarom blijven de sequence-titels bij controleerbare activity diagram-verwijzingen. Gedetailleerde usecase-beschrijvingen vormen een afzonderlijk deelproduct.
6. **Ontwerp is niet hetzelfde als werkende backend:** een methode in een sequence diagram die in de DKD staat, is niet automatisch in `main` geïmplementeerd. Omdat de casus de interne bestellijst van het verkoopassortiment onderscheidt, voegt deze ontwerp-PR de DKD-methode `Product.removeFromInternalReorderList()` en het bijbehorende attribuut `internalReorderEligible` toe. Dit is een expliciete ontwerpvereiste en **geen claim dat deze methode al in de backend draait**. Backend- en databasetoetsing hoort bij de bijbehorende code-PR's; deze PR verandert geen SQL of applicatiecode.

## Controles

Vanaf de repository-root:

```powershell
python -m unittest discover -s Documentation/Architecture/uml/tests -p "test_*.py"
java -jar <pad-naar-plantuml.jar> -checkonly "Documentation/Architecture/uml/src/sequence_diagrams/*.puml"
java -jar <pad-naar-plantuml.jar> -tsvg -o ../../export/sequence_diagrams "Documentation/Architecture/uml/src/sequence_diagrams/*.puml"
git diff --check
```

De controles toetsen aanwezigheid, SVG/XML, DKD-methoden en de expliciete casusregels, maar vervangen geen inhoudelijke teamreview of een werkende end-to-end backendtest. Het team moet PR #116 beoordelen voordat deze in `main` wordt gemerged; PR #93 is de eerdere, door deze PR vervangen versie.
