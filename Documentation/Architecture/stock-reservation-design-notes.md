# Voorraadreserveringen: SQL-ontwerp en vervolgwerk

**Bron:** de gewenste situatie vraagt betrouwbare voorraadbeschikbaarheid bij telefonische bestellingen. Het activity diagram AD05_Enter_order bevat een reserveringsstap na controle van voldoende voorraad.

## Wijzigingen
- `code/database/schema.sql`: `Voorraadreservering` met één rij per bestaande `Bestelregel`, via samengestelde foreign key.
- `code/database/migrations/2026_10_29_inventory_reservations.sql`: toevoeging voor reeds bestaande MySQL-databases.
- `code/database/queries.sql` en `SalesStockRepository.find_products()`: fysieke voorraad minus gereserveerd, met aggregatie per product vóór de joins.
- `/orders`: toont fysieke, gereserveerde en beschikbare voorraad.

## Grenzen
- De reserveringstabel wordt **niet automatisch gevuld**. Dit moet later in de transactie voor het registreren van een klantbestelling gebeuren, samen met de bijbehorende `Bestelregel`.
- Bij picken, annuleren en afleveren moet een reservering worden vrijgegeven of verrekend, anders wordt de beschikbare voorraad onjuist. Dit hoort bij de nog te ontwikkelen orderworkflow.
- De bestaande MySQL Workbench-bron `eer.mwb` en het KD bevatten nog geen klasse/entiteit `Voorraadreservering`. Voor de definitieve oplevering moeten deze ontwerpen worden bijgewerkt of moet de groep kiezen voor een andere reserveringsmodellering. Dit is dus nog **geen volledige traceability**.
- Een echte MySQL-integratietest en tests voor gelijktijdig reserveren zijn nog niet uitgevoerd.
- Geen voorraadontvangstproces toegevoegd; dit is expliciet buiten scope.

## Mergevoorwaarden
1. Pas EER en, indien nodig, KD aan op het overeengekomen reserveringsmodel.
2. Implementeer transactiegebonden reserveren en vrijgeven bij de casusgebonden bestel- en orderpickingprocessen.
3. Valideer de migratie en queries op echte MySQL-data met orders, reserveringen en magazijnlocaties.
4. Controleer PR-afhankelijkheden #82, #83, #84 en #85 en review de gestapelde wijziging afzonderlijk.
