# Timaflu schermontwerpen
# Bron en uitgangspunten
Alle schermontwerpen zijn herleidbaar tot de originele activity diagrams, zonder extra bedrijfsregels.
Open index.html voor een responsieve weergave. Deze documenten zijn geen werkende functies.

| Proces | Activity diagram | Schermontwerp |
|---|---|---|
| Inkoop | [`AD01_Manage_manufacturer_data`](../uml/src/activity_diagrams/AD01_Manage_manufacturer_data.puml) | [Schermontwerp](AD01_Manage_manufacturer_data.html) |
| Inkoop | [`AD02_Reorder_products`](../uml/src/activity_diagrams/AD02_Reorder_products.puml) | [Schermontwerp](AD02_Reorder_products.html) |
| Inkoop | [`AD03_View_minimum_stock`](../uml/src/activity_diagrams/AD03_View_minimum_stock.puml) | [Schermontwerp](AD03_View_minimum_stock.html) |
| Verkoop | [`AD04_Check_stock`](../uml/src/activity_diagrams/AD04_Check_stock.puml) | [Schermontwerp](AD04_Check_stock.html) |
| Verkoop | [`AD05_Enter_order`](../uml/src/activity_diagrams/AD05_Enter_order.puml) | [Schermontwerp](AD05_Enter_order.html) |
| Verkoop | [`AD06_View_order_status`](../uml/src/activity_diagrams/AD06_View_order_status.puml) | [Schermontwerp](AD06_View_order_status.html) |
| Verkoop | [`AD07_Manage_customer_data`](../uml/src/activity_diagrams/AD07_Manage_customer_data.puml) | [Schermontwerp](AD07_Manage_customer_data.html) |
| Orderpicking | [`AD08_View_collection_bins`](../uml/src/activity_diagrams/AD08_View_collection_bins.puml) | [Schermontwerp](AD08_View_collection_bins.html) |
| Orderpicking | [`AD09_Pack_order`](../uml/src/activity_diagrams/AD09_Pack_order.puml) | [Schermontwerp](AD09_Pack_order.html) |
| Orderpicking | [`AD10_Register_collection_bin`](../uml/src/activity_diagrams/AD10_Register_collection_bin.puml) | [Schermontwerp](AD10_Register_collection_bin.html) |
| Orderpicking | [`AD11_Complete_sub-order`](../uml/src/activity_diagrams/AD11_Complete_sub-order.puml) | [Schermontwerp](AD11_Complete_sub-order.html) |
| Distributie | [`AD12_Register_delivery`](../uml/src/activity_diagrams/AD12_Register_delivery.puml) | [Schermontwerp](AD12_Register_delivery.html) |
| Distributie | [`AD13_View_assigned_trips`](../uml/src/activity_diagrams/AD13_View_assigned_trips.puml) | [Schermontwerp](AD13_View_assigned_trips.html) |
| Distributie | [`AD14_Look_up_delivery_time`](../uml/src/activity_diagrams/AD14_Look_up_delivery_time.puml) | [Schermontwerp](AD14_Look_up_delivery_time.html) |
| Distributie | [`AD15_Look_up_customer_phone_number`](../uml/src/activity_diagrams/AD15_Look_up_customer_phone_number.puml) | [Schermontwerp](AD15_Look_up_customer_phone_number.html) |
| Administratie | [`AD16_Create_invoice`](../uml/src/activity_diagrams/AD16_Create_invoice.puml) | [Schermontwerp](AD16_Create_invoice.html) |
| Administratie | [`AD17_View_delivered_orders`](../uml/src/activity_diagrams/AD17_View_delivered_orders.puml) | [Schermontwerp](AD17_View_delivered_orders.html) |
| Administratie | [`AD18_View_outstanding_invoices`](../uml/src/activity_diagrams/AD18_View_outstanding_invoices.puml) | [Schermontwerp](AD18_View_outstanding_invoices.html) |
| Administratie | [`AD19_Register_payment`](../uml/src/activity_diagrams/AD19_Register_payment.puml) | [Schermontwerp](AD19_Register_payment.html) |
| Acquisitie | [`AD20_Register_acquisition_visit`](../uml/src/activity_diagrams/AD20_Register_acquisition_visit.puml) | [Schermontwerp](AD20_Register_acquisition_visit.html) |
| Acquisitie | [`AD21_Follow_up_prospective_customer`](../uml/src/activity_diagrams/AD21_Follow_up_prospective_customer.puml) | [Schermontwerp](AD21_Follow_up_prospective_customer.html) |
| Orderpicking | [`AD22_Request_sub_order`](../uml/src/activity_diagrams/AD22_Request_sub_order.puml) | [Schermontwerp](AD22_Request_sub_order.html) |
| Orderpicking | [`AD23_Collect_sub_order`](../uml/src/activity_diagrams/AD23_Collect_sub_order.puml) | [Schermontwerp](AD23_Collect_sub_order.html) |
| Inkoop | [`AD24_Evaluate_new_medicine`](../uml/src/activity_diagrams/AD24_Evaluate_new_medicine.puml) | [Schermontwerp](AD24_Evaluate_new_medicine.html) |
| Administratie | [`AD25_Pay_purchase_invoices`](../uml/src/activity_diagrams/AD25_Pay_purchase_invoices.puml) | [Schermontwerp](AD25_Pay_purchase_invoices.html) |
| Distributie | [`AD26_Assign_delivery_trips`](../uml/src/activity_diagrams/AD26_Assign_delivery_trips.puml) | [Schermontwerp](AD26_Assign_delivery_trips.html) |
| Distributie | [`AD27_Handle_failed_delivery`](../uml/src/activity_diagrams/AD27_Handle_failed_delivery.puml) | [Schermontwerp](AD27_Handle_failed_delivery.html) |
| Verkoop | [`AD28_Update_annual_customer_discount`](../uml/src/activity_diagrams/AD28_Update_annual_customer_discount.puml) | [Schermontwerp](AD28_Update_annual_customer_discount.html) |

## Controle
- 28 activiteiten: 28 afzonderlijke HTML-ontwerpen.
- Alle processtappen komen uit de originele PlantUML-bronnen.
- CSS heeft een 760 px responsive breakpoint; mobiele picking- en distributieschermen gebruiken één kolom.
- Geen JavaScript, dummyklanten, dummyprijzen of niet-functionele submitknoppen.
- Geen wijziging van MySQL, backend of bedrijfsscenario's.

## Browsercontrole op Floris test

De volgende schermen zijn in Chrome met een echte Playwright-viewport gecontroleerd op
390 px (mobiel), 768 px (tablet) en 1440 px (desktop): AD23 orderpicking,
AD12 distributie, AD05 verkoop en de index. Bij alle twaalf weergaven was
de horizontale documentbreedte gelijk aan de viewportbreedte: geen overflow.

De screenshots zijn daadwerkelijk opgenomen op Floris test:
- [Orderpicking mobiel](previews/AD23_Collect_sub_order_390.png)
- [Orderpicking desktop](previews/AD23_Collect_sub_order_1440.png)
- [Distributie mobiel](previews/AD12_Register_delivery_390.png)
- [Distributie desktop](previews/AD12_Register_delivery_1440.png)

De titels en rollen zijn naar het Nederlands vertaald. De afzonderlijke
procesacties blijven letterlijk uit de PlantUML-bron afkomstig, zodat ze
zonder verzonnen proceslogica te vergelijken zijn.
