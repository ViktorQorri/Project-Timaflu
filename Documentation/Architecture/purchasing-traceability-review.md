# Traceability: voorraad en inkoop

**Review:** 29 oktober 2026
**Status:** controle van de huidige bronbestanden en open PR's. Geen goedkeuring van de groep.

## Leidende documenten
- [Huidige processen](../brightspace/Current-processes.md), sectie Voorraad.
- [Gewenste processen](../brightspace/Desired-process.md), alinea over minimale voorraad en goedkoopste leverancier.
- [Productbeschrijving](../brightspace/Product-description.md), backendscenario product niet op voorraad.
- [Klassendiagram](uml/src/domain/dkd-timaflu.puml).
- EER-bronbestand: [eer.mwb](../../eer.mwb), te vergelijken met [schema.sql](../../code/database/schema.sql).
- Activity diagrams AD02_Reorder_products en AD03_View_minimum_stock in open PR #71.

## Gecontroleerde verbanden
| Casusverplichting | KD | EER en SQL | Implementatie | Conclusie |
| --- | --- | --- | --- | --- |
| Minimumvoorraad per medicijn bewaken | Product.minimumStock / checkMinimumStock() | Product.minimumvoorraad; Magazijnlocatie.aantal | PR #82, /stock | Past binnen casus |
| Goedkoopste leverancier voor product zoeken | Product.findSuppliersByPrice(), SupplierOffer.purchasePrice | LeveranciersAanbod.inkoopprijs gekoppeld aan Product en Leverancier | PR #83, /suppliers | Past binnen casus |
| Contactpersoon en telefoonnummer leverancier tonen | Supplier.contactPerson / phoneNumber | Leverancier.contactpersoon / telefoonnummer | PR #83 | Verplicht backendscenario |
| Inkoopbestelling en bestelregel vastleggen | PurchaseOrder.placeWithSupplier(), PurchaseOrderLine.quantity | Inkoopbestelling en Inkoopbestelregel | Deze PR, POST /purchase-orders | Past bij digitaliseren inkoop, alleen na handmatige bevestiging |
| Inkoopbestelling met datum en status volgen | Geen passende velden in PurchaseOrder | Geen datum/status in Inkoopbestelling | Niet gebouwd | Extra issue-eis, niet expliciet in oorspronkelijke casus |
| Voorraad ontvangen en boeken | Niet als eindproces geëist | Magazijnlocatie, maar geen ontvangstworkflow | Niet gebouwd | Expliciet buiten scope |

## Risico's en nog te verifiëren
1. **De concept-activity diagram AD02 in PR #71 tekent 'Send order to manufacturer' als systeemactie.** De huidige casus zegt dat de medewerker contact opneemt met de fabrikant. Geen automatische verzending ontwikkelen zonder opdrachtgever- of docentbevestiging.
2. **Inkooporderregistratie heeft in de bestaande EER en SQL geen datum of status.** Voeg deze niet uitsluitend op basis van issue #57 toe. Leg deze afwijking vast bij de issue-review.
3. **Controleer vóór het mergen de definitieve bronversie van PR #71** tegen het KD, EER en de werkende code. Een open PR geldt niet als definitief ontwerp.
4. **Geen bewijs van live MySQL-integratie.** De geautomatiseerde tests gebruiken vervangende databaseverbindingen.
5. **Niet alle relaties en attributen van het volledige KD en EER zijn hiermee inhoudelijk gevalideerd.** Deze review dekt het voorraadsysteem en de inkoopstroom; de overige bedrijfsprocessen vragen een afzonderlijke traceability-controle.

## Afhankelijkheden
De wijziging voor issue #57 bouwt bovenop PR #83; PR #83 bouwt bovenop PR #82. Review en merge in die volgorde, met correcte base-branches, zonder de originele PR's over te slaan.
