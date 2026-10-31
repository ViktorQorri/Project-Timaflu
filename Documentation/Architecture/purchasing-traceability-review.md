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
| Inkoopbestelling met datum en status volgen | Inkoopbestelling | `besteld_op` en `status_naam`, nullable voor bestaande onbekende waarden | `/reorder` toont vastgelegde orders; een nieuw record krijgt na handmatige bevestiging de status `besteld` en actuele datum | Issue #57; ontvangst blijft buiten scope |
| Voorraad ontvangen en boeken | Niet als eindproces geëist | Magazijnlocatie, maar geen ontvangstworkflow | Niet gebouwd | Expliciet buiten scope |

## Risico's en nog te verifiëren
1. **De concept-activity diagram AD02 in PR #71 tekent 'Send order to manufacturer' als systeemactie.** De huidige casus zegt dat de medewerker contact opneemt met de fabrikant. Geen automatische verzending ontwikkelen zonder opdrachtgever- of docentbevestiging.
2. **Contact opnemen met leveranciers blijft een handmatige taak.** Het systeem registreert alleen nadat de inkoper bevestigt dat de bestelling is geplaatst; verzending en ontvangst worden niet geautomatiseerd.
3. **Geen bewijs van live MySQL-integratie.** De geautomatiseerde tests gebruiken vervangende databaseverbindingen.
4. **Niet alle relaties en attributen van het volledige KD en EER zijn hiermee inhoudelijk gevalideerd.** Deze review dekt het voorraadsysteem en de inkoopstroom; de overige bedrijfsprocessen vragen een afzonderlijke traceability-controle.

## Afhankelijkheden
De wijziging voor issue #57 bouwt bovenop PR #83; PR #83 bouwt bovenop PR #82. Review en merge in die volgorde, met correcte base-branches, zonder de originele PR's over te slaan.
