"""Case-focused regression checks for Timaflu's five required sequence diagrams.

Run from the repository root:
    python -m unittest discover -s Documentation/Architecture/uml/tests -p "test_*.py"

PlantUML render/syntax validation is an additional external check.
"""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


UML_ROOT = Path(__file__).resolve().parents[1]
SRC = UML_ROOT / "src" / "sequence_diagrams"
EXPORT = UML_ROOT / "export" / "sequence_diagrams"
DKD = UML_ROOT / "src" / "domain" / "dkd-timaflu.puml"
USE_CASE = UML_ROOT / "src" / "use_cases" / "informatiesysteem.puml"
USE_CASE_EXPORT = UML_ROOT / "export" / "use_cases" / "informatiesysteem.svg"
NAMES = {
    "SD01": "SD01_Klantenkorting",
    "SD02": "SD02_ProductNietOpVoorraad",
    "SD03": "SD03_KlantHeeftNietBetaald",
    "SD04": "SD04_KlantNietThuis",
    "SD05": "SD05_PotentieleKlantGeenBestelling",
}


class CaseTraceabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {
            code: (SRC / (name + ".puml")).read_text(encoding="utf-8")
            for code, name in NAMES.items()
        }

    def test_all_five_sources_and_svg_exports_are_present_and_well_formed(self):
        for code, name in NAMES.items():
            with self.subTest(diagram=code):
                source = self.sources[code]
                self.assertTrue(source.startswith("@startuml"))
                self.assertTrue(source.rstrip().endswith("@enduml"))
                svg_file = EXPORT / (name + ".svg")
                self.assertTrue(svg_file.is_file(), str(svg_file))
                xml = ET.parse(svg_file)
                self.assertTrue(xml.getroot().tag.endswith("svg"))
                self.assertIn("plantuml-src", svg_file.read_text(encoding="utf-8"))

    def test_domain_method_calls_trace_to_existing_dkd_methods(self):
        domain = DKD.read_text(encoding="utf-8")
        classes = {}
        for match in re.finditer(r"^class\s+(\w+)\s*\{(.*?)^\}", domain, re.M | re.S):
            classes[match.group(1)] = set(re.findall(r"^\s*(\w+)\([^\n]*\)", match.group(2), re.M))
        for code, text in self.sources.items():
            aliases = {}
            for match in re.finditer(
                r'^\s*(?:create\s+)?participant\s+"[^"\n]+:(\w+)"\s+as\s+(\w+)',
                text, re.M
            ):
                cls, alias = match.groups()
                self.assertIn(cls, classes, f"{code}: class {cls} not in DKD")
                aliases[alias] = cls
            for match in re.finditer(r'^\s*\w+\s*->\s*(\w+)\s*:\s*(\w+)\(', text, re.M):
                target, method = match.groups()
                if target in aliases:
                    self.assertIn(
                        method, classes[aliases[target]],
                        f"{code}: {aliases[target]}.{method} absent from DKD"
                    )

    def test_sd01_order_and_annual_discounts(self):
        sd = self.sources["SD01"]
        for term in ["customer name", "customer address", "sum of ordered product prices",
                     "fully paid invoices", "31 December", "EUR 500", "10%",
                     "EUR 10,000", "EUR 20,000", "15%", "next calendar year",
                     "checkOrderBlock()", "calculateAnnualRevenue()",
                     "determinePercentage(", "final total"]:
            self.assertIn(term, sd, term)
        methods = ["calculateOrderDiscount()", "calculateOneTimeDiscount()",
                   "calculateCustomerDiscount()"]
        self.assertEqual(sorted(sd.index(m) for m in methods),
                         [sd.index(m) for m in methods])
        self.assertIn("oneTimeDiscountGranted = true", sd)
        self.assertIn("oneTimeDiscountApplied", sd)
        self.assertIn("Store calendarYear = nextYear", sd)

    def test_sd02_suppliers_and_separate_inventory_removal(self):
        sd = self.sources["SD02"]
        for term in ["Input: product name", "ordered cheapest first", "contact persons",
                     "phone numbers", "removeSupplier(supplier)", "placeWithSupplier()",
                     "INTERNAL reorder list", "removeFromAssortment()",
                     "explicitly chooses to remove"]:
            self.assertIn(term, sd, term)
        no_supply = sd.split("alt No supplier can confirm delivery", 1)[1].split(
            "else Supplier confirmed delivery", 1
        )[0]
        self.assertNotIn("removeFromAssortment()", no_supply)
        self.assertIn("Do not remove it from the sales assortment", no_supply)
        self.assertIn("Purchasing -> Product: removeFromInternalReorderList()", no_supply)

    def test_sd03_all_invoice_fields_and_reminder_thresholds(self):
        sd = self.sources["SD03"]
        for term in ["customer number", "delivered items", "Timaflu name/address",
                     "customer name/billing address", "quantity, unit price, line total",
                     "total excluding VAT", "9% VAT", "total including VAT",
                     "order discount", "total after order discount", "one-time discount",
                     "total after one-time discount", "customer discount",
                     "final amount after customer discount", "additional delivery costs",
                     "at least 7 and under 14 days", "at least 14 and under 21 days",
                     "three weeks or more", "proposePaymentPlan()",
                     "enableDebtCollection()", "recordFullPayment(date)",
                     "sendToCustomer()", "two separate EUR 300 orders",
                     "Read per-order discounts agreed with customer"]:
            self.assertIn(term, sd, term)

    def test_sd04_two_separate_delivery_attempts(self):
        sd = self.sources["SD04"]
        for term in ["showSchedule(date)", "times, customers, addresses, contact persons and phone numbers",
                     "lookUpCustomerPhoneNumber(customer)", "SAME day",
                     "first:DeliveryAttempt", "second:DeliveryAttempt",
                     "recordReceiptSignature()", "markDelivered(timestamp)",
                     "setDeliveryTime(date, timeSlot)",
                     "recordAdditionalDeliveryCosts(amount, explanation)",
                     "Leave a notice at the delivery address",
                     "signed proof of receipt"]:
            self.assertIn(term, sd, term)
        self.assertLess(sd.index("First: markRecipientAbsent()"),
                        sd.index("Route: adjustSchedule()"))
        self.assertLess(sd.index("Route: adjustSchedule()"),
                        sd.index("Second: markRecipientAbsent()"))

    def test_sd05_acquisition_details_and_consented_first_order(self):
        sd = self.sources["SD05"]
        for term in ["company name, contact person, contact details",
                     "visit address and actual visit date",
                     "ONE CALENDAR MONTH", "hasPlacedOrder()",
                     "contact persons and contact details",
                     "existing customer account without orders is eligible",
                     "one-time extra 10% on the first order",
                     "permission for a customer account",
                     "billing/delivery addresses", "no duplicate account",
                     "createCustomerAccount()", "oneTimeDiscountGranted = true"]:
            self.assertIn(term.lower(), sd.lower(), term)

    def test_use_case_acquisition_and_distribution_trace_to_case(self):
        source = USE_CASE.read_text(encoding="utf-8")
        for label in ("Acquisitiemedewerker", "Acquisitiebezoek registreren",
                      "Acquisitieoverzicht bekijken", "Potentiele klant opvolgen",
                      "Telefoonnummer klant opzoeken",
                      "Tweede afleverpoging registreren"):
            self.assertIn(label, source)
        ET.parse(USE_CASE_EXPORT)

    def test_sd01_uses_paid_revenue_and_single_first_order_incentive(self):
        sd = self.sources["SD01"]
        self.assertIn("amounts ACTUALLY PAID", sd)
        self.assertIn("Do not use gross order values or unpaid invoices", sd)
        self.assertIn("SAME single 10% one-time discount", sd)
        self.assertIn("oneTimeDiscountApplied", sd)
        self.assertLess(sd.index("Order: calculateOneTimeDiscount()"),
                        sd.index("Order: calculateCustomerDiscount()"))

    def test_sd02_no_supplier_is_not_assortment_removal(self):
        sd = self.sources["SD02"]
        no_supply = sd.split("alt No supplier can confirm delivery", 1)[1].split(
            "else Supplier confirmed delivery", 1
        )[0]
        self.assertIn("Purchasing -> Product: removeFromInternalReorderList()", no_supply)
        self.assertIn("internalReorderEligible = false", no_supply)
        self.assertNotIn("Purchasing -> Product: removeFromAssortment()", no_supply)
        self.assertIn("opt Employee explicitly chooses", sd)
        self.assertIn("Purchasing -> Product: removeFromAssortment()", sd)
        domain = DKD.read_text(encoding="utf-8")
        self.assertIn("internalReorderEligible", domain)
        self.assertIn("removeFromInternalReorderList()", domain)

    def test_sd03_collection_is_a_action_and_block_is_checked_only_at_order_entry(self):
        sd = self.sources["SD03"]
        self.assertIn("Admin -> Agency: Engage debt collection", sd)
        self.assertIn("Invoice: enableDebtCollection()", sd)
        self.assertNotIn("Admin -> Customer: checkOrderBlock()", sd)
        self.assertIn("Customer.checkOrderBlock() in SD01 READS this state", sd)
        self.assertIn("Admin -> Invoice: recordFullPayment(date)", sd)

    def test_sd03_weekly_invoice_never_recalculates_threshold(self):
        sd = self.sources["SD03"]
        self.assertIn("Read per-order discounts agreed with customer", sd)
        self.assertIn("two separate EUR 300 orders", sd)
        self.assertIn("does", sd.lower())
        self.assertIn("Do not apply any discount again to the weekly subtotal", sd)
        self.assertLess(sd.index("Invoice -> DeliveryLine"),
                        sd.index("Invoice -> Order: Read per-order discounts"))

    def test_sd04_signature_precedes_delivery_mark_in_both_attempts(self):
        sd = self.sources["SD04"]
        self.assertEqual(sd.count("Request signature for the received medicines"), 2)
        self.assertEqual(sd.count("signed proof of receipt"), 2)
        self.assertIn("Leave a notice at the delivery address", sd)
        first = sd.split("alt Customer can still receive during first visit", 1)[1].split(
            "else Customer cannot receive during first visit", 1
        )[0]
        second = sd.split("alt Recipient present at second attempt", 1)[1].split(
            "else Recipient absent at second attempt", 1
        )[0]
        for part in (first, second):
            self.assertLess(part.index("Request signature"), part.index("recordReceiptSignature()"))
            self.assertLess(part.index("recordReceiptSignature()"), part.index("markDelivered(timestamp)"))

    def test_sd05_initial_visit_and_consent_precede_incentive(self):
        sd = self.sources["SD05"]
        for term in ("Arrange appointment", "product catalogue and discount terms",
                     "information folder", "Ask for company name and billing/delivery address",
                     "no duplicate account"):
            self.assertIn(term, sd)
        self.assertLess(sd.index("Hand over the information folder"),
                        sd.index("Visit: recordVisit("))
        self.assertLess(sd.index("permission for a customer account"),
                        sd.index("Prospect: offerOneTimeDiscount()"))


if __name__ == "__main__":
    unittest.main()
