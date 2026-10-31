-- Replay on a freshly imported isolated fixture database.
-- This is a TWO-STAGE demonstration; never use production data.
SELECT 'Before first absence' AS stage;
SELECT levering_id,pogingnummer,geplande_tijd,resultaat,ontvangst_getekend
FROM Leverpoging WHERE levering_id=3 ORDER BY pogingnummer;

START TRANSACTION;
UPDATE Leverpoging SET resultaat='niet aanwezig', ontvangst_getekend=FALSE
WHERE levering_id=3 AND pogingnummer=1;
INSERT INTO Leverpoging(levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
VALUES(3,2,1,'14:00:00',NULL,NULL);
COMMIT;

SELECT 'After scheduling (second outcome still pending)' AS stage;
SELECT levering_id,pogingnummer,geplande_tijd,resultaat,ontvangst_getekend
FROM Leverpoging WHERE levering_id=3 ORDER BY pogingnummer;

START TRANSACTION;
UPDATE Leverpoging SET resultaat='afgeleverd',ontvangst_getekend=TRUE
WHERE levering_id=3 AND pogingnummer=2 AND resultaat IS NULL;
UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
SET b.status_naam='afgeleverd' WHERE l.levering_id=3;
COMMIT;

SELECT 'After separately registering the second visit' AS stage;
SELECT lp.levering_id,lp.pogingnummer,lp.geplande_tijd,lp.resultaat,
       lp.ontvangst_getekend,b.status_naam
FROM Leverpoging lp JOIN Levering l ON l.levering_id=lp.levering_id
JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
WHERE lp.levering_id=3 ORDER BY lp.pogingnummer;
