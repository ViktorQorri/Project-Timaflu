-- Output samples for actual MySQL 8.4, fictional data only.
SELECT '01. Verkoop: klantgegevens' AS proces;
SELECT klant_id, bedrijfsnaam FROM Klant WHERE klant_id=1;
SELECT '01. Verkoop: netto betaalde jaaromzet 2025' AS proces;
SELECT COUNT(*) AS paid_count, COUNT(f.totaal_bedrag) AS known_amount_count,
       COALESCE(SUM(f.totaal_bedrag),0) AS annual
FROM Factuur AS f
WHERE f.klant_id=1 AND f.betaald_op>='2025-01-01' AND f.betaald_op<'2026-01-01';
SELECT '02. Inkoop: leveranciers op prijs gerangschikt' AS proces;
SELECT p.product_id,p.productnaam,l.leverancier_id,l.naam AS leverancier,
l.contactpersoon,l.telefoonnummer,a.inkoopprijs
FROM Product AS p JOIN LeveranciersAanbod AS a ON a.product_id=p.product_id
JOIN Leverancier AS l ON l.leverancier_id=a.leverancier_id
WHERE p.productnaam LIKE '%Testmedicijn%' AND p.intern_bestelbaar=TRUE AND p.in_assortiment=TRUE
ORDER BY p.productnaam,a.inkoopprijs ASC,l.naam ASC;
SELECT '03. Administratie: factuurkop en status' AS proces;
SELECT f.factuur_id,f.factuurdatum,f.betaald_op,
       f.bedrag_excl_btw,f.btw_bedrag,f.bedrag_incl_btw,
       f.bestellingskorting,f.bedrag_na_bestellingskorting,
       f.eenmalige_korting,f.bedrag_na_eenmalige_korting,
       f.klantenkorting,f.totaal_bedrag,
k.bedrijfsnaam,a.adres
FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id
JOIN Adres a ON a.adres_id=k.betaaladres_id
WHERE f.klant_id=1 AND f.betaald_op IS NULL ORDER BY f.factuurdatum DESC;
SELECT '03. Administratie: werkelijk geleverde factuurregels' AS proces;
SELECT l.aantal_geleverd AS quantity,b.prijs_per_eenheid AS unit_price
FROM Leveringregel l JOIN Levering v ON v.levering_id=l.levering_id
JOIN Bestelregel b ON b.bestelling_id=v.bestelling_id AND b.product_id=l.product_id
WHERE l.factuur_id=2;
SELECT '04. Distributie: rooster voor 31 oktober' AS proces;
SELECT lp.levering_id,lp.pogingnummer,lp.geplande_tijd,lp.resultaat,
b.bestelling_id,k.bedrijfsnaam,k.contactpersoon,k.telefoonnummer,
a.adres,r.ritdatum
FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id
JOIN Levering l ON l.levering_id=lp.levering_id
JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
JOIN Klant k ON k.klant_id=b.klant_id
JOIN Adres a ON a.adres_id=b.afleveradres_id
WHERE r.ritdatum='2026-10-31' ORDER BY lp.geplande_tijd;
SELECT '05. Acquisitie: nog geen order, bezoek ouder dan een maand' AS proces;
SELECT p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,
p.contactgegevens,a.adres,p.klant_id,MAX(v.bezoekdatum) AS bezoekdatum
FROM PotentieleKlant p JOIN Acquisitiebezoek v ON v.potentiele_klant_id=p.potentiele_klant_id
JOIN Adres a ON a.adres_id=p.adres_id
WHERE p.opvolging_afgesloten=FALSE AND NOT EXISTS (
  SELECT 1 FROM Bestelling b WHERE b.klant_id=p.klant_id
)
GROUP BY p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,p.contactgegevens,a.adres,p.klant_id
HAVING MAX(v.bezoekdatum)<='2026-09-30'
ORDER BY bezoekdatum;
