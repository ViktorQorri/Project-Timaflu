-- Preflight on legacy data: verify against the original invoices if these return rows.
-- SELECT factuur_id FROM Factuur WHERE bedrag_excl_btw IS NOT NULL AND btw_bedrag IS NOT NULL
--   AND bedrag_incl_btw IS NOT NULL AND bedrag_incl_btw <> bedrag_excl_btw + btw_bedrag;
-- SELECT factuur_id FROM Factuur WHERE extra_bezorgkosten_incl_btw <> extra_bezorgkosten_excl_btw + extra_bezorgkosten_btw;
-- Do not silently overwrite historical invoice data. Existing inconsistencies stop ALTER.
ALTER TABLE Factuur
    ADD CONSTRAINT ck_factuur_btw_totaal CHECK (
        bedrag_excl_btw IS NULL OR btw_bedrag IS NULL OR bedrag_incl_btw IS NULL
        OR bedrag_incl_btw = bedrag_excl_btw + btw_bedrag
    ),
    ADD CONSTRAINT ck_factuur_bezorgkosten_totaal CHECK (
        extra_bezorgkosten_incl_btw = extra_bezorgkosten_excl_btw + extra_bezorgkosten_btw
    );
