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
| [SD02](src/sequence_diagrams/SD02_ProductNietOpVoorraad.puml) | Productnaam; in het gewenste inkoopproces ook te bestellen hoeveelheid | Bij tekort leveranciers goedkoopste eerst, mét contactpersoon en telefoonnummer. Bij uitval de volgende fabrikant benaderen, bij stopzetting leverancier-productkoppeling kunnen verwijderen. Bij géén leverancier uitsluitend van **interne bestellijst** verwijderen; afzonderlijke mogelijkheid om product expliciet uit het assortiment te halen. | AD02, DKD `Product`, `SupplierOffer`, `Supplier`, `PurchaseOrder`; casus Voorraad |
| [SD03](src/sequence_diagrams/SD03_KlantHeeftNietBetaald.puml) | Klantnummer en werkelijk geleverde regels per week | Factuur met datum, nummer, beide partijen en adressen, aantal/eenheidsprijs/regeltotaal, excl. btw, 9% btw, incl. btw en de drie kortingsregels met tussen- en eindtotalen. Alleen werkelijk geleverd factureren. Bij één en twee weken herinnering; na drie weken betalingsregeling, bij weigering incasso en bestelblokkade tot volledige betaling. | AD16, AD18, DKD `Invoice`, `DeliveryLine`, `OrderLine`, `Order`, `PaymentReminder`, `Customer`; casus Administratie |
| [SD04](src/sequence_diagrams/SD04_KlantNietThuis.puml) | Datum | Rooster met tijd, klant, adres, contactpersoon en telefoonnummer. Na eerste mislukte poging bellen; bij niet bereikbaar opnieuw aanbieden **dezelfde dag**. Tweede uitkomst pas registreren na de poging. Bij afgeleverd is handtekening vereist; bij opnieuw afwezig terug naar distributie, verkoop informeren, nieuwe afspraak en extra kosten met toelichting. | AD12, AD15, AD27, DKD `Courier`, `Route`, `DeliveryAttempt`, `Order`; casus Distributie |
| [SD05](src/sequence_diagrams/SD05_PotentieleKlantGeenBestelling.puml) | Bedrijf, contactpersoon, contactgegevens, adres, bezoekdatum en overzicht acquisitie | Bezoek geregistreerd; overzicht van bedrijven zonder bestelling die minimaal **één kalendermaand** geleden zijn bezocht, inclusief contactgegevens. Alleen bij interesse en toestemming eenmalige 10% eersteorderprikkel registreren en klantaccount maken of bestaand account hergebruiken. Geen contact meer bij geen interesse. | AD20, AD21, DKD `AcquisitionVisit`, `ProspectiveCustomer`, `Customer`; casus Acquisitie |

## Casusvoorbeelden voor de inhoudelijke review

Deze voorbeelden zijn referentiegevallen uit de casusregels. Het zijn **geen** beweringen dat alle betrokken backendfuncties al op `main` werken.

| Diagram | Invoer / gebeurtenis | Verwachte uitkomst |
| --- | --- | --- |
| SD01 | Eerste bestelling € 500, vorige jaaromzet € 0, geen eerdere eenmalige korting | Orderkorting € 25,00; eenmalig 10% van € 475,00 = € 47,50; klantkorting 5% van € 427,50 = € 21,38; eindtotaal **€ 406,12**, bij afronding op centen per kortingsstap |
| SD01 | Herhaalbestelling € 500, betaalde jaaromzet precies € 10.000 | € 25,00 orderkorting, geen eersteorderkorting, daarna 10% klantkorting van € 475,00 = € 47,50; eindtotaal **€ 427,50** |
| SD01 | Herhaalbestelling € 500, betaalde jaaromzet precies € 20.000 | € 25,00 orderkorting, daarna 15% van € 475,00 = € 71,25; eindtotaal **€ 403,75** |
| SD02 | Medicijn onder minimumvoorraad, geen enkele leverancier kan leveren | Leveranciers op prijs geordend met naam, contactpersoon en telefoonnummer; geen inkooporder; van interne bestellijst af; niet automatisch uit verkoopassortiment |
| SD03 | Van de weekorder is maar één regel werkelijk geleverd | Factuur telt alleen die afgeleverde regel; 9% btw en alle drie kortingsvelden/tussenbedragen worden getoond |
| SD03 | Factuur 7, 14 of 21 dagen onbetaald | Respectievelijk eerste herinnering, tweede herinnering, voorstel betalingsregeling; incasso pas na weigering; geen deelbetalingen |
| SD04 | Koerier treft niemand aan bij eerste en tweede bezoek | Tweede bezoek **dezelfde dag gepland** vóór de uitkomst; pas na tweede mislukking definitief niet afgeleverd; retour distributie, verkoop maakt nieuwe afspraak en boekt onderbouwde kosten |
| SD05 | Bezoek op 30 september, controle op 31 oktober en nog nooit besteld | Prospect komt in opvolgoverzicht, samen met contactpersoon en contactgegevens. Bezoek op 1 oktober is op 31 oktober nog niet één kalendermaand oud |
| SD05 | Prospect heeft al een account, maar nog geen order | Nog steeds opvolgbaar; geen tweede klantaccount aanmaken; eenmalige prikkel slechts één keer registreren met toestemming |

## Belangrijke afbakeningen

1. **Verwijdering uit interne bestellijst is geen assortimentsverwijdering.** De casus schrijft bij uitputting van fabrikanten alleen verwijdering van de interne bestellijst voor. `Product.removeFromAssortment()` is daarom uitsluitend een aparte, expliciete medewerkerskeuze uit de productbeschrijving. De voorraad wordt niet automatisch bijgeboekt; ontvangst van nieuwe voorraad is buiten scope.
2. **Eersteorderkorting en acquisitieprikkel:** de productbeschrijving noemt 10% bij de eerste bestelling; de casus noemt na een acquisitiebezoek 10% *extra* bij de eerste bestelling. Het DKD kent maar één eenmalige korting voor dit proces. Bij de acquisitie betekent `Customer.oneTimeDiscountGranted = true` dat het aanbod **beschikbaar** is, niet dat de korting al op een order is verrekend. `Order.oneTimeDiscountApplied` geeft de daadwerkelijke toepassing aan. SD01/SD05 volgen daarom het bestaande model van één toepassing van die 10%, zonder dezelfde incentive dubbel toe te kennen. **Groepsbesluit nodig:** moet die acquisitieprikkel werkelijk een **aanvullende** afzonderlijke 10% boven op de generieke eersteorderkorting zijn? Zo ja, DKD, implementatie, factuurberekening én beide diagrammen samen aanpassen. Dit is geen stilzwijgend vastgestelde businessregel.
3. **Verschillende open backend-PR's:** [#94](https://github.com/ViktorQorri/Project-Timaflu/pull/94) verwerkt zowel de eenmalige als de klantkorting en gebruikt volledig betaalde facturen; [#99](https://github.com/ViktorQorri/Project-Timaflu/pull/99) vermeldt expliciet dat die kortingen exclusief zijn en gebruikt orderregels voor jaaromzet, niet volledig betaalde facturen. Het laatste botst met Product-description, Current-processes en AD28. De ontwerpen in deze PR volgen de casus en AD28, **niet** deze afwijkende implementatiedetails. Deze PR brengt geen wijzigingen aan in die backend-PR's.
4. **Factuur en btw:** de vaste 9% en de presentatievolgorde komen uit de schoolopdracht. De btw-behandeling van aanvullende bezorgkosten en het eigen concrete Timaflu-straatadres zijn niet bepaald in de casus; die worden niet gefabriceerd. Voor definitieve productie-facturen is vastlegging van deze details nodig.
5. **Nog niet vastgelegde usecase-ID's:** `use_cases/informatiesysteem.puml` heeft geen formele `UC05`/`UC16`/enzovoorts en bevat nog geen expliciete acquisitie-actor. Daarom gebruiken de sequence-titels uitsluitend bestaande AD-verwijzingen; de volledige usecase-traceability moet in het aparte usecase-deelproduct worden afgerond.
6. **Ontwerp is niet hetzelfde als werkende backend:** een methode in een sequence diagram die in de DKD staat, is niet automatisch in `main` geïmplementeerd. Backend- en databasetoetsing hoort bij de bijbehorende code-PR's. De diagrammen introduceren geen nieuwe SQL of backendfuncties.

## Controles

Vanaf de repository-root:

```powershell
python -m unittest discover -s Documentation/Architecture/uml/tests -p "test_*.py"
java -jar <pad-naar-plantuml.jar> -checkonly "Documentation/Architecture/uml/src/sequence_diagrams/*.puml"
java -jar <pad-naar-plantuml.jar> -tsvg -o ../../export/sequence_diagrams "Documentation/Architecture/uml/src/sequence_diagrams/*.puml"
git diff --check
```

De controles toetsen aanwezigheid, SVG/XML, DKD-methoden en de expliciete casusregels, maar vervangen geen inhoudelijke teamreview of een werkende end-to-end backendtest. Het team moet PR #116 beoordelen voordat deze in `main` wordt gemerged; PR #93 is de eerdere, door deze PR vervangen versie.
