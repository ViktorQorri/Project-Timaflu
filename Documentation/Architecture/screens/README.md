# Timaflu schermontwerpen

Voor elk van de 28 activity diagrams is een HTML/CSS-schermontwerp beschikbaar.
Elk ontwerp toont de bij de casus en het diagram passende informatievelden, relevante tabelkolommen en een duidelijk als niet-werkend gemarkeerde handeling.
Deze schermontwerpen zijn geen tweede applicatie. Alle actieve procesfunctionaliteit blijft in Flask/Jinja.
Er zijn geen accounts, autorisatierollen, bedrijfsstatussen, verzonnen data of JavaScript toegevoegd.

| Proces | Activity diagram | Schermontwerp |
|---|---|---|
| Inkoop | [AD01](../uml/src/activity_diagrams/AD01_Manage_manufacturer_data.puml) | [Ontwerp](AD01_Manage_manufacturer_data.html) |
| Inkoop | [AD02](../uml/src/activity_diagrams/AD02_Reorder_products.puml) | [Ontwerp](AD02_Reorder_products.html) |
| Inkoop | [AD03](../uml/src/activity_diagrams/AD03_View_minimum_stock.puml) | [Ontwerp](AD03_View_minimum_stock.html) |
| Verkoop | [AD04](../uml/src/activity_diagrams/AD04_Check_stock.puml) | [Ontwerp](AD04_Check_stock.html) |
| Verkoop | [AD05](../uml/src/activity_diagrams/AD05_Enter_order.puml) | [Ontwerp](AD05_Enter_order.html) |
| Verkoop | [AD06](../uml/src/activity_diagrams/AD06_View_order_status.puml) | [Ontwerp](AD06_View_order_status.html) |
| Verkoop | [AD07](../uml/src/activity_diagrams/AD07_Manage_customer_data.puml) | [Ontwerp](AD07_Manage_customer_data.html) |
| Orderpicking | [AD08](../uml/src/activity_diagrams/AD08_View_collection_bins.puml) | [Ontwerp](AD08_View_collection_bins.html) |
| Orderpicking | [AD09](../uml/src/activity_diagrams/AD09_Pack_order.puml) | [Ontwerp](AD09_Pack_order.html) |
| Orderpicking | [AD10](../uml/src/activity_diagrams/AD10_Register_collection_bin.puml) | [Ontwerp](AD10_Register_collection_bin.html) |
| Orderpicking | [AD11](../uml/src/activity_diagrams/AD11_Complete_sub-order.puml) | [Ontwerp](AD11_Complete_sub-order.html) |
| Distributie | [AD12](../uml/src/activity_diagrams/AD12_Register_delivery.puml) | [Ontwerp](AD12_Register_delivery.html) |
| Distributie | [AD13](../uml/src/activity_diagrams/AD13_View_assigned_trips.puml) | [Ontwerp](AD13_View_assigned_trips.html) |
| Distributie | [AD14](../uml/src/activity_diagrams/AD14_Look_up_delivery_time.puml) | [Ontwerp](AD14_Look_up_delivery_time.html) |
| Distributie | [AD15](../uml/src/activity_diagrams/AD15_Look_up_customer_phone_number.puml) | [Ontwerp](AD15_Look_up_customer_phone_number.html) |
| Administratie | [AD16](../uml/src/activity_diagrams/AD16_Create_invoice.puml) | [Ontwerp](AD16_Create_invoice.html) |
| Administratie | [AD17](../uml/src/activity_diagrams/AD17_View_delivered_orders.puml) | [Ontwerp](AD17_View_delivered_orders.html) |
| Administratie | [AD18](../uml/src/activity_diagrams/AD18_View_outstanding_invoices.puml) | [Ontwerp](AD18_View_outstanding_invoices.html) |
| Administratie | [AD19](../uml/src/activity_diagrams/AD19_Register_payment.puml) | [Ontwerp](AD19_Register_payment.html) |
| Acquisitie | [AD20](../uml/src/activity_diagrams/AD20_Register_acquisition_visit.puml) | [Ontwerp](AD20_Register_acquisition_visit.html) |
| Acquisitie | [AD21](../uml/src/activity_diagrams/AD21_Follow_up_prospective_customer.puml) | [Ontwerp](AD21_Follow_up_prospective_customer.html) |
| Orderpicking | [AD22](../uml/src/activity_diagrams/AD22_Request_sub_order.puml) | [Ontwerp](AD22_Request_sub_order.html) |
| Orderpicking | [AD23](../uml/src/activity_diagrams/AD23_Collect_sub_order.puml) | [Ontwerp](AD23_Collect_sub_order.html) |
| Inkoop | [AD24](../uml/src/activity_diagrams/AD24_Evaluate_new_medicine.puml) | [Ontwerp](AD24_Evaluate_new_medicine.html) |
| Administratie | [AD25](../uml/src/activity_diagrams/AD25_Pay_purchase_invoices.puml) | [Ontwerp](AD25_Pay_purchase_invoices.html) |
| Distributie | [AD26](../uml/src/activity_diagrams/AD26_Assign_delivery_trips.puml) | [Ontwerp](AD26_Assign_delivery_trips.html) |
| Distributie | [AD27](../uml/src/activity_diagrams/AD27_Handle_failed_delivery.puml) | [Ontwerp](AD27_Handle_failed_delivery.html) |
| Verkoop | [AD28](../uml/src/activity_diagrams/AD28_Update_annual_customer_discount.puml) | [Ontwerp](AD28_Update_annual_customer_discount.html) |

## Controle
- 28 afzonderlijke HTML-ontwerpen met veld- en tabelstructuur.
- Uitgeschakelde controls om niet-functionaliteit expliciet te maken.
- Responsive HTML/CSS, zonder JavaScript of React.
- Niet van toepassing op de automatische backendscenario's.
- In de werkende applicatie worden gegevens altijd via de database geladen.
