"""PR 123: failed deliveries, customer follow-up, extra costs and weekly invoicing."""
from datetime import date, timedelta, time
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.business import Invoice
from domain.errors import ConflictError, DomainError
from services.distribution_service import DistributionService


class NoWriteRepository:
    def reschedule_failed_delivery(self, *args):
        raise AssertionError("Invalid input reached the database")


class RecordingRepository:
    def __init__(self):
        self.calls = []

    def reschedule_failed_delivery(self, *args):
        self.calls.append(args)


class FailedDeliveryCaseTests(TestCase):
    def test_sales_must_confirm_contact_with_customer(self):
        service = DistributionService(NoWriteRepository())
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(DomainError, "klant"):
            service.reschedule_failed_delivery(
                2, tomorrow, "ochtend", "2.50", "Twee mislukte pogingen", ""
            )

    def test_new_delivery_date_and_costs_are_validated(self):
        service = DistributionService(NoWriteRepository())
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        cases = [
            ("invalid", "ochtend", "2.00", "Twee pogingen"),
            (date.today().isoformat(), "ochtend", "2.00", "Twee pogingen"),
            (tomorrow, "avond", "2.00", "Twee pogingen"),
            (tomorrow, "middag", "-2.00", "Twee pogingen"),
            (tomorrow, "middag", "NaN", "Twee pogingen"),
            (tomorrow, "middag", "3.123", "Twee pogingen"),
            (tomorrow, "middag", "2.00", ""),
        ]
        for day, slot, cost, reason in cases:
            with self.subTest(day=day, slot=slot, cost=cost, reason=reason):
                with self.assertRaises(DomainError):
                    service.reschedule_failed_delivery(
                        2, day, slot, cost, reason, "yes"
                    )

    def test_valid_followup_calls_existing_order_repository(self):
        repo = RecordingRepository()
        new_day = date.today() + timedelta(days=1)
        result = DistributionService(repo).reschedule_failed_delivery(
            "2", new_day.isoformat(), "middag", "4,50",
            "Koerier trof niemand", "yes"
        )
        self.assertEqual(result, new_day)
        self.assertEqual(repo.calls, [
            (2, new_day, "middag", Decimal("4.50"), "Koerier trof niemand")
        ])

    def test_invoice_adds_extra_delivery_cost_without_order_discount_on_fee(self):
        issued = Invoice(1, "101", date(2026, 11, 1)).createWeeklyInvoice(
            "Apotheek", "Adres",
            [{"bestelling_id": 20, "quantity": 2, "unit_price": Decimal("20"),
              "besteld_ex_btw": Decimal("40"),
              "eenmalige_korting_toegepast": False,
              "extra_bezorgkosten": Decimal("7.50")}],
            Decimal("0"), False,
        )
        self.assertEqual(issued["total_ex_vat"], Decimal("40.00"))
        self.assertEqual(issued["vat_9_percent"], Decimal("3.60"))
        self.assertEqual(issued["order_discount"], Decimal("0.00"))
        self.assertEqual(issued["customer_discount"], Decimal("2.18"))
        self.assertEqual(issued["extra_delivery_costs"], Decimal("7.50"))
        self.assertEqual(issued["total"], Decimal("48.92"))

    def test_fee_once_per_order_even_with_multiple_delivered_lines(self):
        issued = Invoice(1, "101", date(2026, 11, 1)).createWeeklyInvoice(
            "Apotheek", "Adres", [
                {"bestelling_id": 20, "quantity": 1, "unit_price": Decimal("10"),
                 "extra_bezorgkosten": Decimal("4.50")},
                {"bestelling_id": 20, "quantity": 2, "unit_price": Decimal("20"),
                 "extra_bezorgkosten": Decimal("4.50")},
            ], Decimal("0"), False,
        )
        self.assertEqual(issued["extra_delivery_costs"], Decimal("4.50"))
        self.assertEqual(issued["total"], Decimal("56.27"))

    def test_delivery_page_shows_sales_followup_only_after_second_failure(self):
        app = create_app()
        app.testing = True
        second = {
            "levering_id": 3, "pogingnummer": 2, "resultaat": "niet aanwezig",
            "status_naam": "niet afgeleverd", "geplande_tijd": time(12, 0),
            "bestelling_id": 4, "bedrijfsnaam": "Apotheek A",
            "adres": "Teststraat 1", "contactpersoon": "Test",
            "telefoonnummer": "0612345678",
        }
        with app.test_client() as client:
            with patch("routes.distribution.get_connection", return_value=object()):
                with patch("routes.distribution.DistributionService") as service:
                    service.return_value.orders_with_bins.return_value = []
                    service.return_value.orders_to_schedule.return_value = []
                    service.return_value.couriers.return_value = []
                    with patch("routes.distribution.AssessedRepository") as assessed:
                        assessed.return_value.delivery_schedule.return_value = [second]
                        response = client.get("/deliveries")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nieuwe bezorgafspraak vastleggen", response.data)
        self.assertIn(b"Extra bezorgkosten", response.data)

    def test_rescheduling_route_uses_agreed_customer_details(self):
        app = create_app()
        app.testing = True
        tomorrow = date.today() + timedelta(days=1)
        with app.test_client() as client:
            with patch("routes.distribution._service") as service:
                service.return_value.reschedule_failed_delivery.return_value = tomorrow
                response = client.post("/deliveries/3/reschedule", data={
                    "new_date": tomorrow.isoformat(), "part_of_day": "middag",
                    "additional_cost": "4.50",
                    "explanation": "Twee keer niemand thuis",
                    "customer_contact_confirmed": "yes",
                })
        self.assertEqual(response.status_code, 302)
        self.assertIn(tomorrow.isoformat(), response.headers["Location"])
        service.return_value.reschedule_failed_delivery.assert_called_once_with(
            3, tomorrow.isoformat(), "middag", "4.50",
            "Twee keer niemand thuis", "yes"
        )
