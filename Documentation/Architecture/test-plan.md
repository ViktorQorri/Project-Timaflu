# Timaflu test plan

Refs #41.

## Scope
Unit, integration and acceptance testing for sales, purchasing, robot picking, distribution, weekly invoicing and acquisition. Incoming inventory is outside scope.

## Unit tests
Verify first-order and yearly customer discounts in correct sequence, minimum-stock lookup and manufacturer price sorting, delivery retry on the same day, unpaid invoice calculations, acquisition follow-up after one month, and concurrency-safe reservations.

## Integration tests
Use an isolated non-production MySQL instance. Compare schema.sql, migrations, the editable EER and SQL in repositories against queries.sql. Validate actual data and transaction behavior. Never fabricate database output.

## Acceptance tests
Exercise telephone orders, purchase orders after manual supplier contact, robot picking bins, delivery outcomes, weekly invoicing, and prospect conversion. Check mobile picking and distribution, keyboard access, Dutch UI, and no frontend JavaScript.

## Evidence
Run the Python unittest suite and git diff --check. Record test output, checked revision, relevant UML and use case references, screenshots and environment limitations. Do not claim real MySQL validation from fake repository tests.
