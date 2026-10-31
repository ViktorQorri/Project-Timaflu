-- Case: after acceptance or definitive rejection, acquisition leaves further action to sales or stops.
ALTER TABLE PotentieleKlant
    ADD COLUMN opvolging_afgesloten BOOLEAN NOT NULL DEFAULT FALSE;
-- Case: persist the explicit first-order incentive promised by acquisition.
ALTER TABLE Klant
    ADD COLUMN eenmalige_korting_toegezegd BOOLEAN NOT NULL DEFAULT FALSE;
