"""Stock checks and saving a telephone order with its lines and reservations (AD05 Enter order)."""
from datetime import date
from decimal import Decimal

from domain.errors import ConflictError, NotFoundError

BLOCKED_MESSAGE = (
    "Deze klant kan geen bestelling plaatsen: een onbetaalde factuur ligt bij het incassobureau."
)

# Customers whose unpaid invoice went to a debt collection agency cannot order (case, Administratie).
BLOCKED_QUERY = """
    SELECT COUNT(*) AS aantal_facturen
    FROM Factuur
    WHERE klant_id = %s AND betaald_op IS NULL AND incasso_ingeschakeld = TRUE
"""

# Physical stock in every warehouse location minus what is already reserved for other orders.
AVAILABLE_QUERY = """
    SELECT GREATEST(
        COALESCE((SELECT SUM(aantal) FROM Magazijnlocatie WHERE product_id = %s), 0)
        - COALESCE((SELECT SUM(aantal) FROM Voorraadreservering WHERE product_id = %s), 0),
        0) AS beschikbaar
"""


class OrderRepository:
    def __init__(self, connection):
        self.connection = connection

    def is_customer_blocked(self, customer_id):
        """Return True when an unpaid invoice of the customer is with the debt collection agency."""
        with self.connection.cursor(dictionary=True) as cur:
            cur.execute(BLOCKED_QUERY, (customer_id,))
            return int(cur.fetchone()["aantal_facturen"]) > 0

    def available_stock(self, product_id):
        """Return how many units of the product can still be sold."""
        with self.connection.cursor(dictionary=True) as cur:
            cur.execute(AVAILABLE_QUERY, (product_id, product_id))
            return int(cur.fetchone()["beschikbaar"])

    def save_order(self, customer_id, lines, delivery_date, part_of_day, urgent,
                   expected_first_order=None, expected_one_time_discount=None,
                   expected_discount_year=None, expected_customer_discount_percentage=None):
        """Save the order, its lines and the reservations in one transaction.

        The customer and every product are locked first and the stock is counted again,
        so two sales employees cannot sell the same units. A line that is short now and
        was not accepted as backorder rejects the whole order, so the employee can revise it.
        Lines with enough stock are reserved; short lines are saved as backorder.

        Args:
            customer_id: The customer placing the order.
            lines: Dicts with product_id, productnaam, quantity and backorder (accepted by the customer).
            delivery_date: The agreed delivery date.
            part_of_day: "ochtend" or "middag".
            urgent: True for an urgent order.
            expected_*: Values calculated for the customer before approval; reject
                changed first-order status or annual rate instead of changing the quote.

        Returns:
            A dict with the new order_id, first_order and the product ids saved as backorder.
        """
        conn = self.connection
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """SELECT klant_id, afleveradres_id, betaaladres_id, actief
                       FROM Klant
                       WHERE klant_id = %s
                       FOR UPDATE""",
                    (customer_id,),
                )
                customer = cur.fetchone()
                if customer is None:
                    raise NotFoundError("Deze klant bestaat niet.")
                if not customer.get("actief", True):
                    raise ConflictError("Deze klant is gedeactiveerd en kan geen bestelling plaatsen.")
                cur.execute(BLOCKED_QUERY, (customer_id,))
                if int(cur.fetchone()["aantal_facturen"]) > 0:
                    raise ConflictError(BLOCKED_MESSAGE)
                cur.execute(
                    """SELECT COUNT(*) AS aantal_bestellingen
                       FROM Bestelling
                       WHERE klant_id = %s""",
                    (customer_id,),
                )
                first_order = int(cur.fetchone()["aantal_bestellingen"]) == 0
                if expected_first_order is not None and first_order != expected_first_order:
                    raise ConflictError("Er is inmiddels een andere bestelling geplaatst. Bereken de korting opnieuw.")
                one_time_discount = first_order
                if expected_one_time_discount is not None and expected_one_time_discount != one_time_discount:
                    raise ConflictError("De eerste-orderkorting is gewijzigd. Bereken opnieuw.")

                discount_year = date.today().year
                if expected_discount_year is not None and expected_discount_year != discount_year:
                    raise ConflictError("Het kalenderjaar is gewijzigd. Bereken de order opnieuw.")
                cur.execute(
                    """SELECT percentage FROM Klantkorting
                       WHERE klant_id = %s AND kalenderjaar = %s FOR UPDATE""",
                    (customer_id, discount_year),
                )
                recorded_rate = cur.fetchone()
                if recorded_rate is None and not first_order:
                    raise ConflictError(
                        f"De klantenkorting voor {discount_year} is niet vastgelegd."
                    )
                discount_rate = (
                    Decimal(recorded_rate["percentage"])
                    if recorded_rate is not None else Decimal("5.00")
                )
                if (expected_customer_discount_percentage is not None
                        and Decimal(expected_customer_discount_percentage) != discount_rate):
                    raise ConflictError("De klantenkorting is gewijzigd. Bereken opnieuw.")

                priced = []
                # Lock in product order, so two orders with the same products cannot deadlock.
                for line in sorted(lines, key=lambda line: line["product_id"]):
                    cur.execute(
                        """SELECT product_id, prijs_per_grootverpakking
                           FROM Product
                           WHERE product_id = %s
                           FOR UPDATE""",
                        (line["product_id"],),
                    )
                    product = cur.fetchone()
                    if product is None:
                        raise NotFoundError("Dit medicijn staat niet in de catalogus.")
                    if "expected_price" in line and product["prijs_per_grootverpakking"] != line["expected_price"]:
                        raise ConflictError("De catalogusprijs is gewijzigd. Bereken het totaal opnieuw.")
                    cur.execute(AVAILABLE_QUERY, (line["product_id"], line["product_id"]))
                    available = int(cur.fetchone()["beschikbaar"])
                    if ("expected_available" in line
                            and available != line["expected_available"]):
                        raise ConflictError(
                            "De beschikbare voorraad is veranderd. "
                            "Bereken opnieuw en vraag de klant opnieuw akkoord."
                        )
                    short = available < line["quantity"]
                    if short and not line["backorder"]:
                        raise ConflictError(
                            f"De voorraad is veranderd: er zijn nog {available} van {line['productnaam']} "
                            "beschikbaar. Pas de order aan of noteer de regel als backorder."
                        )
                    priced.append({**line, "price": product["prijs_per_grootverpakking"], "short": short})

                backorders = [line["product_id"] for line in priced if line["short"]]
                if recorded_rate is None:
                    # New customers registered after last December need the 5% base rate.
                    # Do not persist it until the customer approves the actual order.
                    cur.execute(
                        """INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)
                           VALUES (%s, %s, %s)""",
                        (customer_id, discount_year, discount_rate),
                    )
                cur.execute(
                    """INSERT INTO Bestelling (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                                               gewenste_leverdatum, dagdeel, spoed, status_naam,
                                               eenmalige_korting_toegepast)
                       VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)""",
                    (customer_id, customer["afleveradres_id"], customer["betaaladres_id"], delivery_date,
                     part_of_day, urgent,
                     "backorder" if backorders else "wordt verzameld", one_time_discount),
                )
                order_id = cur.lastrowid
                for line in priced:
                    cur.execute(
                        """INSERT INTO Bestelregel (bestelling_id, product_id, aantal, prijs_per_eenheid,
                                                    afnemen_bij_tekort)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (order_id, line["product_id"], line["quantity"], line["price"],
                         True if line["short"] else None),
                    )
                    if not line["short"]:
                        cur.execute(
                            """INSERT INTO Voorraadreservering (bestelling_id, product_id, aantal)
                               VALUES (%s, %s, %s)""",
                            (order_id, line["product_id"], line["quantity"]),
                        )
            conn.commit()
            return {"order_id": order_id, "first_order": first_order, "backorders": backorders}
        except Exception:
            conn.rollback()
            raise
