"""Capture actual MySQL queries and resulting database changes for Timaflu form actions.

Every scenario uses the isolated fixture database populated by audit_ui_queries.py.
Application commits are intercepted and each scenario is rolled back, so no
test action leaks into another case and no non-test database is modified.
"""
from __future__ import annotations
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch
import json
import re
import mysql.connector
from audit_ui_queries import RecorderConnection, RecorderCursor, MODULES

ROOT=Path(__file__).resolve().parents[2]
DEBUG=ROOT/"deliverables/_mutation_audit.json"

def step(url, data=None, json_data=None, today=None):
    item={"url":url}
    if data is not None:item["data"]=data
    if json_data is not None:item["json"]=json_data
    if today:item["today"]=today
    return item

PRODUCT={
    "article_number":"TEST-NEW-003", "order_code":"TEST-NEW-ORDER",
    "product_name":"TEST nieuw medicijn", "price_per_bulk_package":"32.50",
    "package_type":"Doos", "number_of_retail_packages":"2",
    "short_description":"Fictief testartikel", "long_description":"Uitsluitend testdata",
    "minimum_order_quantity":"1","minimum_stock":"5",
    "supplier_id":"1","purchase_price":"12.50","management_approved":"yes",
    "ingredient_name":["Teststof nieuw"],"ingredient_quantity":["20 mg"]
}
UPDATED_PRODUCT={
    **PRODUCT, "article_number":"TEST-001","order_code":"TEST-CODE",
    "product_name":"TEST medicijn bijgewerkt",
    "price_per_bulk_package":"101.00",
    "ingredient_name":["Teststof"], "ingredient_quantity":["50 mg"]
}
COMPLETE_ROBOT=step("/api/robots/1/complete",json_data={
    "aisle":"A","suborder_id":1,"collected":[{"product_id":1,"quantity":1}]
})
FIRST_ABSENT=step("/deliveries/first-attempt",data={
    "day":"2026-10-22","delivery_id":"3","outcome":"niet aanwezig","second_time":"15:00"
})
SECOND_ABSENT=step("/deliveries/second-attempt",data={
    "day":"2026-10-22","delivery_id":"3","outcome":"niet aanwezig",
    "receipt_signed":"0","time":"15:00"
})
FIRST_SUCCESS=step("/deliveries/first-attempt/delivered",data={
    "day":"2026-10-22","delivery_id":"3","signature_confirmed":"yes"
})
PACK=step("/deliveries/6/pack",data={"box_count":"1"})
RELEASE=step("/deliveries/6/release",data={})
ACTIONS=[
  dict(ad="AD01",name="Fabrikant aanmaken",steps=[step("/manufacturers/new",{
      "naam":"TEST nieuwe fabrikant","adres":"TEST: Fabrikantenlaan 10",
      "contactpersoon":"TEST contact","telefoonnummer":"0600000099","internetadres":"example.invalid"
  })],verify="SELECT leverancier_id,naam FROM Leverancier WHERE naam='TEST nieuwe fabrikant'"),
  dict(ad="AD01",name="Fabrikantgegevens wijzigen",steps=[step("/manufacturers/1/edit",{
      "naam":"TEST Fabrikant bijgewerkt","adres":"TEST: Leveranciersweg 1",
      "contactpersoon":"TEST contactpersoon","telefoonnummer":"0611111111","internetadres":"example.invalid"
  })],verify="SELECT naam,telefoonnummer FROM Leverancier WHERE leverancier_id=1 AND naam='TEST Fabrikant bijgewerkt'"),
  dict(ad="AD01",name="Inkoopprijs bij fabrikant vastleggen",steps=[step("/manufacturers/1/prices",{
      "product_id":"2","price":"12.40"
  })],verify="SELECT leverancier_id,product_id,inkoopprijs FROM LeveranciersAanbod WHERE leverancier_id=1 AND product_id=2"),
  dict(ad="AD01",name="Aanbod van fabrikant ontkoppelen",steps=[step("/manufacturers/1/prices/1/remove",{
      "confirmed":"yes"
  })],verify="SELECT product_id,leverancier_id FROM LeveranciersAanbod WHERE leverancier_id=1 AND product_id=1",
  expect_rows=0),
  dict(ad="AD02",name="Leveranciersaanbod ontkoppelen",steps=[step("/suppliers/remove-offer",{
      "product_id":"1","supplier_id":"2","product_name":"Testmedicijn","confirmed":"yes"
  })],verify="SELECT leverancier_id,product_id FROM LeveranciersAanbod WHERE leverancier_id=2 AND product_id=1",
  expect_rows=0),
  dict(ad="AD02",name="Medicijn uit interne bestellijst",steps=[step("/suppliers/remove-product",{
      "product_id":"2","product_name":"Testtekortproduct","confirmed":"yes"
  })],verify="SELECT product_id,intern_bestelbaar,in_assortiment FROM Product WHERE product_id=2 AND intern_bestelbaar=0 AND in_assortiment=1"),
  dict(ad="AD02",name="Inkooporder na telefonisch contact registreren",steps=[step("/purchase-orders",{
      "supplier_id":"3","product_id":"1","quantity":"2",
      "confirmed":"yes","supplier_contact_confirmed":"yes"
  })],verify="SELECT i.inkoopbestelling_id,r.aantal FROM Inkoopbestelling i JOIN Inkoopbestelregel r USING(inkoopbestelling_id) WHERE i.inkoopbestelling_id > 1 AND r.aantal=2"),
  dict(ad="AD02",name="Tekort bij goedkope leverancier bestellen",pre=[
      ["INSERT INTO LeveranciersAanbod (leverancier_id,product_id,inkoopprijs) VALUES (3,2,7.00)",[]]
  ],steps=[step("/reorder",{
      "product_id":"2","supplier_id":"3","quantity":"5","confirmed":"yes"
  })],verify="SELECT r.product_id,r.aantal FROM Inkoopbestelregel r WHERE r.product_id=2 AND r.aantal=5"),
  dict(ad="AD03",name="Minimumvoorraad wijzigen",steps=[step("/stock/minimums/2",{
      "minimumvoorraad":"11"
  })],verify="SELECT minimumvoorraad FROM Product WHERE product_id=2 AND minimumvoorraad=11"),
  dict(ad="AD05",name="Telefonische bestelling na expliciet akkoord",special="quote_confirm",steps=[
      step("/orders/quote",{
          "customer_id":"1","day":"2026-11-04","slot":"ochtend","urgent":"no",
          "product_id":["1"],"quantity":["1"],"shortage":["skip"]
      })
  ],verify="SELECT bestelling_id,status_naam FROM Bestelling WHERE bestelling_id>7"),
  dict(ad="AD07",name="Nieuwe klant registreren",steps=[step("/customers",{
      "bedrijfsnaam":"TEST nieuwe apotheek","contactpersoon":"TEST klantcontact",
      "telefoonnummer":"0612345670","afleveradres":"TEST: Afleveradres nieuw",
      "factuuradres":"TEST: Factuuradres nieuw"
  })],verify="SELECT klant_id,bedrijfsnaam FROM Klant WHERE bedrijfsnaam='TEST nieuwe apotheek'"),
  dict(ad="AD07",name="Klantgegevens aanpassen",steps=[step("/customers/1/edit",{
      "bedrijfsnaam":"TEST Apotheek bijgewerkt B.V.",
      "contactpersoon":"TEST aangepast","telefoonnummer":"0612345678",
      "afleveradres":"TEST: Afleverstraat 8, Breda",
      "factuuradres":"TEST: Factuurstraat 12, Breda"
  })],verify="SELECT klant_id,bedrijfsnaam FROM Klant WHERE klant_id=1 AND bedrijfsnaam='TEST Apotheek bijgewerkt B.V.'"),
  dict(ad="AD10",name="Verzamelbak bij robotdeelorder registreren",steps=[step("/api/picking-bins",json_data={
      "bin_code":"TEST-BAK-NIEUW","sub_order_id":1,"aisle":"A"
  })],verify="SELECT unieke_code,deelorder_id FROM Verzamelbak WHERE unieke_code='TEST-BAK-NIEUW'"),
  dict(ad="AD11",name="Robotdeelorder afronden",steps=[COMPLETE_ROBOT],
      verify="SELECT deelorder_id,afgerond FROM Deelorder WHERE deelorder_id=1 AND afgerond=1"),
  dict(ad="AD09",name="Klantorder verpakken na robotafronding",steps=[COMPLETE_ROBOT,PACK],
      verify="SELECT bestelling_id,aantal_verhuisdozen FROM Bestelling WHERE bestelling_id=6 AND aantal_verhuisdozen=1"),
  dict(ad="AD09",name="Verpakte order vrijgeven",steps=[COMPLETE_ROBOT,PACK,RELEASE],
      verify="SELECT bestelling_id,status_naam FROM Bestelling WHERE bestelling_id=6 AND status_naam='verstuurd'"),
  dict(ad="AD12",name="Eerste bezorgpoging mislukt: tweede plannen",steps=[FIRST_ABSENT],
      verify="SELECT levering_id,pogingnummer,geplande_tijd FROM Leverpoging WHERE levering_id=3 AND pogingnummer=2"),
  dict(ad="AD12",name="Eerste bezorgpoging succesvol afgeleverd",steps=[FIRST_SUCCESS],
      verify="SELECT levering_id,pogingnummer,resultaat,ontvangst_getekend FROM Leverpoging WHERE levering_id=3 AND pogingnummer=1 AND resultaat='afgeleverd'"),
  dict(ad="AD27",name="Tweede bezorgpoging mislukt",steps=[FIRST_ABSENT,SECOND_ABSENT],
      verify="SELECT levering_id,pogingnummer,resultaat FROM Leverpoging WHERE levering_id=3 AND pogingnummer=2 AND resultaat='niet aanwezig'"),
  dict(ad="AD27",name="Nieuwe afspraak na twee mislukte pogingen",steps=[
      FIRST_ABSENT,SECOND_ABSENT,step("/deliveries/3/reschedule",{
          "new_date":"2026-11-05","part_of_day":"ochtend",
          "additional_cost":"12.00","explanation":"TEST: tweemaal niet thuis",
          "customer_contact_confirmed":"yes"
      })
  ],verify="SELECT bestelling_id,gewenste_leverdatum,extra_bezorgkosten FROM Bestelling WHERE bestelling_id=3 AND gewenste_leverdatum='2026-11-05'"),
  dict(ad="AD16",name="Weekfacturen uitgeven na bevestiging",steps=[step("/invoices/weekly",{
      "week_start":"2026-10-19","invoice_approved":"yes"
  })],verify="SELECT klant_id,week_start FROM Factuur WHERE klant_id=2 AND week_start='2026-10-19'"),
  dict(ad="AD18",name="Herinnering als verzonden registreren",steps=[step("/invoices/1/reminders/1/sent",{
      "sent_confirmed":"yes"
  },today="2026-11-08")],verify="SELECT factuur_id FROM Factuur WHERE factuur_id=1"),
  dict(ad="AD19",name="Volledige factuurbetaling registreren",steps=[step("/invoices/actions",{
      "customer_id":"1","invoice_id":"1","action":"mark_paid",
      "received_amount":"634.76"
  })],verify="SELECT factuur_id,betaald_op FROM Factuur WHERE factuur_id=1 AND betaald_op IS NOT NULL"),
  dict(ad="AD20",name="Acquisitiebezoek registreren",steps=[step("/acquisition/prospects",{
      "company_name":"TEST Derde prospect","contact_person":"TEST prospect contact",
      "contact_details":"0600000033","address":"TEST: Acquisitielaan 9",
      "visit_date":"2026-09-01"
  })],verify="SELECT potentiele_klant_id,bedrijfsnaam FROM PotentieleKlant WHERE bedrijfsnaam='TEST Derde prospect'"),
  dict(ad="AD21",name="Opvolging na afwijzing beëindigen",steps=[step("/acquisition/prospects/1/follow-up",{
      "outcome":"no_interest","decision_confirmed":"yes"
  })],verify="SELECT potentiele_klant_id,opvolging_afgesloten FROM PotentieleKlant WHERE potentiele_klant_id=1 AND opvolging_afgesloten=1"),
  dict(ad="AD21",name="Opvolging met klantaccount en korting",steps=[step("/acquisition/prospects/2/follow-up",{
      "outcome":"convert","delivery_address":"TEST: Levering nieuwe klant",
      "invoice_address":"TEST: Factuur nieuwe klant","phone_number":"0611111122"
  })],verify="SELECT potentiele_klant_id,klant_id FROM PotentieleKlant WHERE potentiele_klant_id=2 AND klant_id IS NOT NULL"),
  dict(ad="AD22",name="Robotdeelorders genereren",steps=[step("/api/orders/7/suborders",json_data={})],
      verify="SELECT deelorder_id,bestelling_id FROM Deelorder WHERE bestelling_id=7"),
  dict(ad="AD23",name="Order vanuit orderpicking naar robots",steps=[step("/order-picking/orders/7/dispatch",{})],
      verify="SELECT deelorder_id,bestelling_id FROM Deelorder WHERE bestelling_id=7"),
  dict(ad="AD24",name="Nieuw medicijn na directiegoedkeuring",steps=[step("/products/new",PRODUCT)],
      verify="SELECT product_id,productnaam FROM Product WHERE artikelnummer='TEST-NEW-003'"),
  dict(ad="AD24",name="Bestaand medicijn wijzigen",steps=[step("/products/1/edit",UPDATED_PRODUCT)],
      verify="SELECT product_id,productnaam FROM Product WHERE product_id=1 AND productnaam='TEST medicijn bijgewerkt'"),
  dict(ad="AD24",name="Medicijn uit assortiment verwijderen",steps=[step("/products/2/remove",{})],
      verify="SELECT product_id,in_assortiment FROM Product WHERE product_id=2 AND in_assortiment=0"),
  dict(ad="AD25",name="Inkoopfactuur als betaald registreren",steps=[step("/purchase-invoices/1/paid",{
      "payment_confirmed":"yes"
  })],verify="SELECT inkoopfactuur_id,betaald_op FROM Inkoopfactuur WHERE inkoopfactuur_id=1 AND betaald_op IS NOT NULL"),
  dict(ad="AD26",name="Koerier toevoegen",steps=[step("/deliveries/couriers",{
      "name":"TEST Koerier twee","region":"Breda","external":"no"
  })],verify="SELECT koerier_id,naam FROM Koerier WHERE naam='TEST Koerier twee'"),
  dict(ad="AD26",name="Koeriersregio wijzigen",steps=[step("/deliveries/couriers/1/region",{
      "region":"Breda"
  })],verify="SELECT koerier_id,regio FROM Koerier WHERE koerier_id=1 AND regio='Breda'"),
  dict(ad="AD26",name="Beschikbaarheid koerier wijzigen",steps=[step("/deliveries/couriers/1/availability",{
      "available":"0"
  })],verify="SELECT koerier_id,beschikbaar FROM Koerier WHERE koerier_id=1 AND beschikbaar=0"),
  dict(ad="AD26",name="Verpakte order aan koerier toewijzen",steps=[
      COMPLETE_ROBOT,PACK,RELEASE,
      step("/deliveries/couriers/1/region",{"region":"Breda"}),
      step("/deliveries/schedule",{
          "order_id":"6","courier_id":"1","time":"09:30","region_confirmed":"yes"
      })
  ],verify="SELECT l.levering_id,l.bestelling_id FROM Levering l WHERE l.bestelling_id=6"),
  dict(ad="AD28",name="Klantenkorting per jaar vaststellen",pre=[
      ["UPDATE Factuur SET betaald_op='2026-11-01' WHERE factuur_id=1",[]]
  ],steps=[step("/invoices/annual-discounts",{"discounts_confirmed":"yes"},today="2026-12-31")],
      verify="SELECT klant_id,kalenderjaar,percentage FROM Klantkorting WHERE kalenderjaar=2027"),
]
class MutationCursor(RecorderCursor):
    def execute(self, sql, params=()):
        result=super().execute(sql, params)
        verb=re.match(r"^\s*(INSERT|UPDATE|DELETE|REPLACE)\b",sql,re.I)
        if verb:
            self.entry["affected_rows"]=self.cursor.rowcount
            if verb[1].upper()=="INSERT": self.entry["last_insert_id"]=self.cursor.lastrowid
        return result
class NoCommitConnection(RecorderConnection):
    def cursor(self,**kwargs):
        return MutationCursor(self.connection.cursor(**kwargs),self.output)
    def commit(self):
        self.commits_requested=getattr(self,"commits_requested",0)+1

def record_mutations(app, options):
    outcomes=[]
    bad=[]
    for case in ACTIONS:
        statements=[]
        connection=mysql.connector.connect(**options)
        proxy=NoCommitConnection(connection,statements)
        case_result={"ad":case["ad"],"name":case["name"],"steps":[], "verification":None}
        try:
            with connection.cursor() as cur:
                for sql,params in case.get("pre",[]):
                    cur.execute(sql,params)
            with app.test_client() as client:
                for n,st in enumerate(case["steps"]):
                    with ExitStack() as stack:
                        for module in MODULES:
                            stack.enter_context(patch(module+".get_connection",return_value=proxy))
                        if st.get("today"):
                            simulated_date=date.fromisoformat(st["today"])
                            class FrozenDate(date):
                                @classmethod
                                def today(cls):
                                    return simulated_date
                            stack.enter_context(patch("routes.administration.date", FrozenDate))
                            stack.enter_context(patch("repositories.assessed_repository.date", FrozenDate))
                        if "json" in st:
                            response=client.post(st["url"],json=st["json"])
                        else:
                            response=client.post(st["url"],data=st.get("data",{}))
                    status=response.status_code
                    case_result["steps"].append({"url":st["url"],"status":status,
                        "input":st.get("data",st.get("json",{}))})
                    if status not in (200,201,302,303):
                        raise RuntimeError(f"{st['url']} status {status}, body={response.get_data(as_text=True)[:220]}")
                    if case.get("special")=="quote_confirm" and n==0:
                        match=re.search(r'name="quote_token"\s+value="([^"]+)"',response.get_data(as_text=True))
                        if not match:raise RuntimeError("Quote lacked signed token")
                        with ExitStack() as stack:
                            for module in MODULES:
                                stack.enter_context(patch(module+".get_connection",return_value=proxy))
                            approved=client.post("/orders/confirm",data={
                                "quote_token":match[1],"customer_approved":"yes"
                            })
                        case_result["steps"].append({"url":"/orders/confirm","status":approved.status_code,
                                                    "input":{"customer_approved":"yes","quote_token":"<signed fixture token>"}})
                        if approved.status_code not in (302,303):
                            raise RuntimeError("Order confirmation failed "+str(approved.status_code))
            with connection.cursor(dictionary=True) as cur:
                cur.execute(case["verify"])
                actual=cur.fetchall()
            expected_count=case.get("expect_rows",1)
            if (len(actual)>0) != (expected_count>0):
                raise RuntimeError(f"Readback had unexpected number of rows {len(actual)}")
            if not any(entry.get("affected_rows",0)>0 for entry in statements):
                raise RuntimeError("Action did not change any SQL rows")
            case_result["verification"]={"sql":case["verify"],"row_count":len(actual),"rows":actual[:15]}
            case_result["sql"]=[{
                "sql":entry["sql"],"params":entry["params"],
                "row_count":entry["row_count"],
                "rows":entry["results"][:15],
                **({key:entry[key] for key in ("affected_rows","last_insert_id") if key in entry})
            } for entry in statements]
            case_result["result"]="passed"
        except Exception as exc:
            case_result["result"]="failed"
            case_result["error"]=f"{type(exc).__name__}: {exc}"
            case_result["sql"]=[{"sql":e["sql"],"params":e["params"],"rows":e["results"],
                                  "affected_rows":e.get("affected_rows")} for e in statements]
            bad.append(f"{case['ad']} {case['name']}: {case_result['error']}")
        finally:
            connection.rollback()
            connection.close()
        outcomes.append(case_result)
        print(f"ACTION {case_result['result'].upper():6} {case['ad']} {case['name']}")
    DEBUG.parent.mkdir(parents=True,exist_ok=True)
    DEBUG.write_text(json.dumps(outcomes,indent=2,ensure_ascii=False,default=str),encoding="utf8")
    print(f"ACTION_TOTAL={len(ACTIONS)} ACTION_PASS={len(ACTIONS)-len(bad)} ACTION_FAIL={len(bad)}")
    for failure in bad:print("FAILURE",failure)
    if bad:raise RuntimeError(f"{len(bad)} mutation scenarios failed; see {DEBUG}")
    return outcomes
