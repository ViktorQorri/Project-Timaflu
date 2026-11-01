-- Deze migratie volgt op 2026_11_01_delivery_charges.sql en 2026_10_31_invoice_snapshot.sql.
-- Alleen de redundante, rekenkundig afleidbare kolommen worden verwijderd.
-- CHECK stopt de migratie als oude, uitgegeven facturen afwijkende of niet-
-- reconstrueerbare tussen/eindtotalen bevatten; herstel eerst vanaf bronfacturen.
ALTER TABLE Factuur
    ADD CONSTRAINT ck_factuur_3nf_preflight CHECK (
        (extra_bezorgkosten_incl_btw =
            extra_bezorgkosten_excl_btw + extra_bezorgkosten_btw)
        AND (bedrag_incl_btw IS NULL OR (
            bedrag_excl_btw IS NOT NULL AND btw_bedrag IS NOT NULL
            AND bedrag_incl_btw = bedrag_excl_btw + btw_bedrag
        ))
        AND (bedrag_na_bestellingskorting IS NULL OR (
            bedrag_excl_btw IS NOT NULL AND btw_bedrag IS NOT NULL
            AND bestellingskorting IS NOT NULL
            AND bedrag_na_bestellingskorting =
                bedrag_excl_btw + btw_bedrag - bestellingskorting
        ))
        AND (bedrag_na_eenmalige_korting IS NULL OR (
            bedrag_excl_btw IS NOT NULL AND btw_bedrag IS NOT NULL
            AND bestellingskorting IS NOT NULL AND eenmalige_korting IS NOT NULL
            AND bedrag_na_eenmalige_korting =
                bedrag_excl_btw + btw_bedrag - bestellingskorting - eenmalige_korting
        ))
        AND (totaal_bedrag IS NULL OR (
            bedrag_excl_btw IS NOT NULL AND btw_bedrag IS NOT NULL
            AND bestellingskorting IS NOT NULL AND eenmalige_korting IS NOT NULL
            AND klantenkorting IS NOT NULL
            AND totaal_bedrag =
                bedrag_excl_btw + btw_bedrag - bestellingskorting
                - eenmalige_korting - klantenkorting
                + extra_bezorgkosten_excl_btw + extra_bezorgkosten_btw
        ))
    );

ALTER TABLE Factuur
    DROP CHECK ck_factuur_3nf_preflight,
    DROP COLUMN extra_bezorgkosten_incl_btw,
    DROP COLUMN bedrag_incl_btw,
    DROP COLUMN bedrag_na_bestellingskorting,
    DROP COLUMN bedrag_na_eenmalige_korting,
    DROP COLUMN totaal_bedrag,
    ADD CONSTRAINT ck_factuur_bedragen CHECK (
        extra_bezorgkosten_excl_btw >= 0 AND extra_bezorgkosten_btw >= 0
        AND (bedrag_excl_btw IS NULL OR bedrag_excl_btw >= 0)
        AND (btw_bedrag IS NULL OR btw_bedrag >= 0)
        AND (bestellingskorting IS NULL OR bestellingskorting >= 0)
        AND (eenmalige_korting IS NULL OR eenmalige_korting >= 0)
        AND (klantenkorting IS NULL OR klantenkorting >= 0)
    );

-- Berekeningen zijn niet opgeslagen: de basistabel blijft in 3NF.
-- NULL in historische bronbedragen blijft NULL; onbekende omzet wordt niet verzonnen.
CREATE VIEW FactuurOverzicht AS
SELECT f.*,
       f.extra_bezorgkosten_excl_btw + f.extra_bezorgkosten_btw
           AS extra_bezorgkosten_incl_btw,
       f.bedrag_excl_btw + f.btw_bedrag AS bedrag_incl_btw,
       f.bedrag_excl_btw + f.btw_bedrag - f.bestellingskorting
           AS bedrag_na_bestellingskorting,
       f.bedrag_excl_btw + f.btw_bedrag
           - f.bestellingskorting - f.eenmalige_korting
           AS bedrag_na_eenmalige_korting,
       f.bedrag_excl_btw + f.btw_bedrag
           - f.bestellingskorting - f.eenmalige_korting - f.klantenkorting
           + f.extra_bezorgkosten_excl_btw + f.extra_bezorgkosten_btw
           AS totaal_bedrag
FROM Factuur AS f;
