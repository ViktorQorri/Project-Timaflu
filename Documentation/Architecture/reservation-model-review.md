# Ontwerpuitwerking voor voorraadreserveringen

**Doel:** de in PR #86 geïntroduceerde tabel Voorraadreservering zichtbaar maken in het KD en een EER-bron.

## KD
- Nieuwe klasse `StockReservation` met attribuut `reservedQuantity`.
- Associatie: `OrderLine 1 -> 0..1 StockReservation`.
- Geen los reserverings-ID; de combinatie bestelling/product wordt uit de bestaande `Bestelregel` overgenomen.

## EER
- De nieuwe entiteit is uitgewerkt in [eer-stock-reservation.puml](uml/src/domain/eer-stock-reservation.puml).
- De tabel heeft `bestelling_id`, `product_id`, `aantal` en een samengestelde FK naar `Bestelregel`.
- Het originele MySQL Workbench-bestand [eer.mwb](../../eer.mwb) is **niet automatisch aangepast**. De nieuwe entiteit en relatie moeten daarin nog worden overgenomen, waarna het complete EER tegen `schema.sql` kan worden gecontroleerd. Gebruik deze PR dus niet als bewijs dat het volledige Workbench-EER al overeenkomt met de database.

## Scope en openstaande werkzaamheden
- Voorraadbeschikbaarheid bij telefonische verkoop is expliciet gevraagd in de casus; reserveren verschijnt in het activity diagram AD05.
- De database en Python lezen reserveringen, maar het aanmaken en vrijgeven bij orderpicking/annuleren is nog niet uitgewerkt.
- Voordat wordt gemerged moet de groep toetsen of het reserveringsmodel voor de volledige orderlevenscyclus voldoende is.
- Een live integratietest tegen MySQL ontbreekt.
- Dit is een **ontwerp-PR**, niet een implementatie- of migratie-PR. Hij bouwt rechtstreeks op #86.
