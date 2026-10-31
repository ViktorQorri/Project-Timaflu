-- Product-description.md scenario 4: record a second failed delivery without pretending it was delivered.
INSERT IGNORE INTO OrderStatus (naam) VALUES ('niet afgeleverd');
