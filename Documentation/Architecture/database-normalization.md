# Databasenormalisatie en factuurhistorie

- Bestelregel: (bestelling_id, product_id) bepaalt aantal en prijs.
- Leveringregel: (levering_id, product_id) bepaalt aantal en factuurtoewijzing. De applicatie factureert individuele regels, dus levering_id bepaalt factuur_id niet noodzakelijk.
- PotentieleKlant bewaart historische acquisitiegegevens; Klant bewaart operationele gegevens. Dit is niet automatisch een overtreding van 3NF.
- Factuur bewaart historische bedragen zoals uitgegeven. Dit is bewust gedenormaliseerd om historische facturen reproduceerbaar te houden.

Het schema beschermt nu de interne btw-sommen en bezorgkosten via CHECK-constraints. Voor bestaande databases moeten de preflight queries in de migratie eerst worden gedraaid en eventuele afwijkingen aan de hand van originele facturen worden onderzocht. Historische NULL-waarden worden niet opnieuw berekend.

**Conclusie:** operationele tabellen zijn grotendeels genormaliseerd, maar het factuurmodel gebruikt bewust historische snapshots. Deze wijziging verbetert de consistentie en claimt niet dat de gehele database strikt 3NF is.
