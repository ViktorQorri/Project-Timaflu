-- Add acquisition follow-up state and the one-time discount granted on conversion.
ALTER TABLE Klant
    ADD COLUMN eenmalige_korting_toegekend BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE PotentieleKlant
    ADD COLUMN status ENUM('open', 'geconverteerd', 'geen_interesse', 'geen_toestemming')
        NOT NULL DEFAULT 'open';
