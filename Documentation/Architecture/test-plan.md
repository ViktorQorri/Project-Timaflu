# Timaflu test plan

Refs #41.

## Scope
Unit, integration and acceptance testing for sales, purchasing, robot picking, distribution, weekly invoicing and acquisition. Incoming inventory is outside scope.

The school's Product-description.md does not require a separate automatic-test deliverable or a minimum code-coverage percentage. Issue #41 requests a test **plan**, and these checks support verification of the six case processes. Tests do not create additional business rules.

## Unit tests
Verify first-order and yearly customer discounts in correct sequence, minimum-stock lookup and manufacturer price sorting, delivery retry on the same day, unpaid invoice calculations, acquisition follow-up after one month, and concurrency-safe reservations.

## Integration tests
Use an isolated non-production MySQL instance. Compare schema.sql, migrations, the editable EER and SQL in repositories against queries.sql. Validate actual data and transaction behavior. Never fabricate database output.

## Acceptance tests
Exercise telephone orders, purchase orders after manual supplier contact, robot picking bins, delivery outcomes, weekly invoicing, and prospect conversion. Check mobile picking and distribution, keyboard access, Dutch UI, and no frontend JavaScript.

## Evidence
Run the Python unittest suite and git diff --check. Record test output, checked revision, relevant UML and use case references, screenshots and environment limitations. Do not claim real MySQL validation from fake repository tests.

## Executable acceptance test cases

All data below is fictional. Run these cases against a non-production MySQL instance after applicable branches are integrated. Record the tested commit SHA and resulting database rows.

| ID / traceability | Setup and input | Steps | Expected result |
|---|---|---|---|
| T01, AD05 / SD01 / Bestelling | Existing customer, order subtotal € 500, previous-year **paid** revenue € 12.000 | Add order lines by telephone, calculate, request customer approval | 5% order discount and the applicable annual discount in the specified sequence; no order persisted before approval |
| T02, AD05 / SD01 / Productbeschrijving | First order from new customer, previous-year paid revenue € 0 | Calculate order discount, first-order discount and customer discount | Discounts are accounted for in the documented sequence; do not silently treat the first-order discount as exclusion of the other categories |
| T03, AD04 / AD05 / Voorraadreservering | Warehouse has 3 units, another order has 1 unit reserved | Two sessions each attempt to reserve 2 units simultaneously | Exactly one reservation can succeed; the other must be rejected without double allocation. Verify on isolated MySQL |
| T04, AD02 / AD03 / LeveranciersAanbod | Three suppliers priced € 4, € 6 and € 9, cheapest cannot supply | Display shortage, compare offers and contact suppliers manually | Sorted offers with contacts; employee tries the next supplier. No automatic supplier order |
| T05, AD22 / AD23 / Deelorder | Order of 6 units, across robot aisles A (4) and B (2) | Generate suborders twice | Two aisle-specific suborders once; subsequent generation rejected; warehouse quantities not overallocated |
| T06, AD10 / AD11 / Verzamelbak | Robot receives a suborder and a uniquely coded collection bin is available | Robot scans the bin code, sends it to the information system, collects medicines and reports the suborder complete; when the bin becomes full it is moved to the roller conveyor | The system links the unique bin to the suborder, accepts the robot's completion message and offers the robot its next suborder. Do not require individual medicine scans: the case does not prescribe them |
| T07, AD12 / AD27 / Leverpoging | Courier arrives at delivery address with customer absent | Mark first absence, schedule same-day retry, mark outcome | Attempt history and order state reflect both attempts; no invented delivery success |
| T08, AD16 / AD18 / Factuur | Weekly delivered medicine items, VAT 9%, old unpaid invoice | Create invoice and retrieve unpaid balance | Only actually delivered items invoiced; discounts and amounts correspond to persisted historical transaction values |
| T09, AD20 / AD21 / Acquisitiebezoek | Prospect visited more than one month ago and has placed no order | Fetch follow-up list, call prospect, accept one-time incentive | Eligible prospect appears; account creation and 10% first order offer are recorded without automated marketing |
| T10, AD01 / Leverancier | New manufacturer with name, address, contact, phone, and price | Submit form and edit saved record | Database preserves supplier relation and price, validates input, does not remove historical references |
| T11, AD03 / Product.minimumvoorraad | Physical stock 2, minimum 5 | Open shortages, change minimum to 1, refresh | Initially shortage 3 displayed, after threshold change it disappears; physical stock remains 2 |
| T12, responsive | Phone-sized viewport 390 px and desktop 1440 px | Open picking and distribution, tab through controls and submit forms | No clipped controls, visible focus, comprehensible labels, no JavaScript dependency |

## Evidence and result register

| Check | Result | Evidence or limitation |
|---|---|---|
| Original main Python baseline | 19/19 passed | Reported in earlier repository test run on 2026-10-30 |
| Product catalog branch | 42/42 passed | `test_eer_product_catalog.py` included; no live MySQL check from this result alone |
| Local integrated branch | 62/62 passed | Python unittest on `integration/floris29-review` on 2026-10-30 |
| Direct MySQL 8.4 SQL | Passed selected operations | Disposable sandbox: 27 schema tables, shortage and supplier query, transaction rollbacks |
| Real Python repositories with MySQL | Passed selected operations | Manufacturer, prices, threshold, purchase recording, robot allocation and bin completion |
| Flask pages against MySQL | 14 of 14 HTTP 200 | Smoke test on isolated MySQL; not a full user workflow |
| T03, T06, T07, T08, T09, T12 | Not fully verified together | Require the relevant integrated transactions, robot bin registration and completion messages, or more functional/visual coverage. No medicine-by-medicine scanning requirement exists in the case |

Do not treat an HTTP 200, a mock, or a render test as proof of business correctness. Each PR must state whether a case was actually run, with concrete output, or remains a planned test.
