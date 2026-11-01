"""Domeinmethoden voor de vijf expliciet verplichte Timaflu-scenario's.

Voorbeeldgegevens zijn toegestaan volgens Product-description.md.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange


def euro(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Bedrag moet eindig en niet-negatief zijn")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CustomerDiscount:
    def determinePercentage(self, annualRevenue, calendarYear=None):
        value = euro(annualRevenue)
        return Decimal("0.05") if value < 10000 else (
            Decimal("0.10") if value < 20000 else Decimal("0.15"))


class Order:
    def __init__(self, subtotal, annualRevenue=0, firstOrder=False, orderThresholdBase=None,
                 customerDiscountPercentage=None, orderTotal=None):
        self.subtotal = euro(subtotal)
        # Both the original assessed API (orderTotal) and the live invoice
        # workflow (orderThresholdBase) refer to the same original order total.
        if orderTotal is not None:
            if (orderThresholdBase is not None
                    and euro(orderThresholdBase) != euro(orderTotal)):
                raise ValueError("Tegenstrijdige oorspronkelijke ordertotalen.")
            orderThresholdBase = orderTotal
        self.annualRevenue = euro(annualRevenue)
        self.firstOrder = firstOrder
        self.customerDiscountPercentage = customerDiscountPercentage
        # Partial deliveries retain the discount eligibility of the original order.
        self.orderThresholdBase = (
            self.subtotal if orderThresholdBase is None else euro(orderThresholdBase)
        )

    def calculateOrderDiscount(self):
        return euro(self.subtotal * Decimal("0.05")) if self.orderThresholdBase >= 500 else euro(0)

    def calculateOneTimeDiscount(self):
        return euro((self.subtotal - self.calculateOrderDiscount()) * Decimal("0.10")) if self.firstOrder else euro(0)

    def calculateCustomerDiscount(self):
        after = self.subtotal - self.calculateOrderDiscount() - self.calculateOneTimeDiscount()
        percentage = (
            CustomerDiscount().determinePercentage(self.annualRevenue)
            if self.customerDiscountPercentage is None
            else Decimal(str(self.customerDiscountPercentage)) / Decimal("100")
        )
        return euro(after * percentage)

    def calculateTotalAmount(self):
        a = self.calculateOrderDiscount()
        b = self.calculateOneTimeDiscount()
        c = self.calculateCustomerDiscount()
        return {"subtotal": self.subtotal, "order_discount": a,
                "first_order_discount": b, "customer_discount": c,
                "total": euro(self.subtotal - a - b - c)}

    def setDeliveryTime(self, date, timeSlot):
        # Other case processes: school explicitly permits an empty method.
        pass

    def changeOrderStatus(self, status):
        # Other case processes: school explicitly permits an empty method.
        pass

    def recordAdditionalDeliveryCosts(self, amount, explanation):
        # Other case processes: school explicitly permits an empty method.
        pass

    def recordOrder(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def recordCustomerApproval(self, approval):
        # Other case processes: school explicitly permits an empty method.
        pass

    def markAsUrgent(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def getOrderStatus(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def splitIntoSuborders(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def viewCollectionBins(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def packageOrder(self):
        # Other case processes: school explicitly permits an empty method.
        pass


class Invoice:
    def __init__(self, customerNumber, invoiceNumber, invoiceDate, paidOn=None):
        self.customerNumber = customerNumber
        self.invoiceNumber = invoiceNumber
        self.invoiceDate = invoiceDate
        self.paidOn = paidOn
        self.paymentPlanAccepted = None
        self.debtCollectionEnabled = False

    def createWeeklyInvoice(self, customerName, customerAddress, lines, annualRevenue, firstOrder,
                            orderTotal=None):
        """Bundle delivered lines on one invoice, retaining discounts per order.

        The case gives an order-level 5% discount and first-order 10% discount,
        while administration invoices delivered products together each week.
        A weekly subtotal must never make smaller orders eligible for 5%.
        """
        items = []
        orders = {}
        for line in lines:
            qty = int(line["quantity"])
            if qty <= 0:
                raise ValueError("Aantal moet positief zijn")
            price = euro(line["unit_price"])
            item = {"quantity": qty, "unit_price": price, "line_total": euro(qty * price)}
            items.append(item)
            order_id = line.get("bestelling_id", "__single_order__")
            group = orders.setdefault(order_id, {
                "items": [],
                "annual_revenue": line.get("annual_revenue", annualRevenue),
                "annual_discount_percentage": line.get("annual_discount_percentage"),
                "first_order": bool(line.get("eenmalige_korting_toegepast", firstOrder)),
                "original_total": line.get("besteld_ex_btw"),
                "extra_cost": euro(line.get("extra_bezorgkosten", 0)),
            })
            if (group["first_order"] != bool(line.get("eenmalige_korting_toegepast", firstOrder))
                    or group["annual_revenue"] != line.get("annual_revenue", annualRevenue)
                    or group["annual_discount_percentage"] != line.get("annual_discount_percentage")
                    or group["extra_cost"] != euro(line.get("extra_bezorgkosten", 0))):
                raise ValueError("Tegenstrijdige kortingsgegevens voor dezelfde bestelling")
            group["items"].append(item)

        amounts = {key: Decimal("0.00") for key in (
            "total_ex_vat", "vat_9_percent", "total_incl_vat",
            "order_discount", "total_after_order_discount", "first_order_discount",
            "total_after_first_order_discount", "customer_discount",
            "extra_delivery_costs", "total"
        )}
        for group in orders.values():
            net = euro(sum((item["line_total"] for item in group["items"]), Decimal(0)))
            vat = euro(net * Decimal("0.09"))
            gross = net + vat
            original_net = group["original_total"]
            threshold_base = (
                euro(orderTotal) if orderTotal is not None
                else euro(euro(original_net) * Decimal("1.09"))
                if original_net is not None else gross
            )
            discount = Order(
                gross, group["annual_revenue"], group["first_order"], threshold_base,
                group["annual_discount_percentage"]
            ).calculateTotalAmount()
            amounts["total_ex_vat"] += net
            amounts["vat_9_percent"] += vat
            amounts["total_incl_vat"] += gross
            amounts["order_discount"] += discount["order_discount"]
            amounts["total_after_order_discount"] += gross - discount["order_discount"]
            amounts["first_order_discount"] += discount["first_order_discount"]
            amounts["total_after_first_order_discount"] += (
                gross - discount["order_discount"] - discount["first_order_discount"]
            )
            amounts["customer_discount"] += discount["customer_discount"]
            amounts["extra_delivery_costs"] += group["extra_cost"]
            # Costs caused by customer absence are charged separately after the
            # medicine discounts; they do not make the order eligible for 5%.
            amounts["total"] += discount["total"] + group["extra_cost"]
        return {
            "date": self.invoiceDate, "invoice_number": self.invoiceNumber,
            "customer_number": self.customerNumber, "customer_name": customerName,
            "customer_address": customerAddress, "lines": items,
            "subtotal": amounts["total_incl_vat"], **amounts,
        }

    def createWeeklyInvoiceForOrders(self, customerName, customerAddress, orders, annualRevenue):
        """Aggregate actual delivered order lines, calculating discounts per order.

        The 5% threshold belongs to an order, not the sum of different orders.
        10% applies only once to the first order, not again for acquisition.
        """
        if not orders:
            from domain.errors import DomainError
            raise DomainError("Geen afgeleverde regels om te factureren.")
        fields = ("total_ex_vat", "vat_9_percent", "total_incl_vat",
                  "order_discount", "total_after_order_discount",
                  "first_order_discount", "total_after_first_order_discount",
                  "customer_discount", "total")
        totals = {key: Decimal("0.00") for key in fields}
        all_lines = []
        for order in orders:
            detail = self.createWeeklyInvoice(
                customerName, customerAddress, order["lines"],
                annualRevenue, order["first_order"], order.get("order_total")
            )
            for key in fields:
                totals[key] = euro(totals[key] + detail[key])
            for line in detail["lines"]:
                all_lines.append({**line, "order_id": order["order_id"]})
        return {
            "date": self.invoiceDate, "invoice_number": self.invoiceNumber,
            "customer_number": self.customerNumber, "customer_name": customerName,
            "customer_address": customerAddress, "lines": all_lines,
            "subtotal": totals["total_incl_vat"],
            **totals,
        }

    def checkPaymentArrears(self, today):
        if self.paidOn:
            return "paid"
        days = (today - self.invoiceDate).days
        return ("contact_payment_plan" if days >= 21 else
                "second_reminder" if days >= 14 else
                "first_reminder" if days >= 7 else "no_action")

    def proposePaymentPlan(self, accepted):
        self.paymentPlanAccepted = bool(accepted)

    def enableDebtCollection(self, customer):
        if self.paymentPlanAccepted is not False:
            raise ValueError("Incasso volgt pas na weigering betalingsregeling")
        self.debtCollectionEnabled = True
        customer.blocked = True

    def sendToCustomer(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def recordFullPayment(self, date):
        # Other case processes: school explicitly permits an empty method.
        pass


class PaymentReminder:
    def __init__(self, sequenceNumber):
        if sequenceNumber not in (1, 2):
            raise ValueError("Alleen eerste en tweede herinnering")
        self.sequenceNumber = sequenceNumber
        self.sentOn = None

    def send(self, today):
        self.sentOn = today
        return {"sequence_number": self.sequenceNumber, "sent_on": today}


class Customer:
    def __init__(self, companyName, deliveryAddress="", billingAddress=""):
        self.companyName = companyName
        self.deliveryAddress = deliveryAddress
        self.billingAddress = billingAddress
        self.blocked = False
        self.oneTimeDiscountGranted = False

    def checkOrderBlock(self):
        return self.blocked

    def calculateAnnualRevenue(self):
        # Other case processes: school explicitly permits an empty method.
        pass

    def updateDetails(self):
        # Other case processes: school explicitly permits an empty method.
        pass


class DeliveryAttempt:
    def __init__(self, attemptNumber):
        if attemptNumber not in (1, 2):
            raise ValueError("Alleen twee afleverpogingen")
        self.attemptNumber = attemptNumber
        self.result = None

    def markRecipientAbsent(self):
        self.result = "niet aanwezig"

    def markDelivered(self, timestamp):
        self.result = "afgeleverd"
        self.actuallyDeliveredOn = timestamp

    def recordReceiptSignature(self):
        # Other case processes: school explicitly permits an empty method.
        pass


class Route:
    def __init__(self, routeDate, deliveries):
        self.routeDate = routeDate
        self.deliveries = [dict(x) for x in deliveries if x["date"] == routeDate]

    def showSchedule(self, dateValue):
        return self.deliveries if dateValue == self.routeDate else []

    def adjustSchedule(self, orderId, secondAttempt=None):
        for delivery in self.deliveries:
            if delivery["order_id"] == orderId:
                delivery["first_attempt"] = "niet aanwezig"
                delivery["second_attempt"] = secondAttempt or "scheduled"
                return self.deliveries
        raise ValueError("Bestelling niet in rooster")

    def assignToCourier(self, courier):
        # Other case processes: school explicitly permits an empty method.
        pass


class AcquisitionVisit:
    def recordVisit(self, companyName, contactPerson, contactDetails, address, visitDate):
        if (not all((companyName.strip(), contactPerson.strip(),
                     contactDetails.strip(), address.strip()))
                or not isinstance(visitDate, date)):
            from domain.errors import DomainError
            raise DomainError("Bedrijf, contactpersoon, contactgegevens, adres en datum zijn verplicht")
        return {"company": companyName, "contact": contactPerson,
                "contact_details": contactDetails, "address": address, "date": visitDate}


class ProspectiveCustomer:
    def __init__(self, companyName, ordered=False, followUpClosed=False):
        self.companyName = companyName
        self.ordered = ordered
        self.followUpClosed = followUpClosed

    def hasPlacedOrder(self):
        return self.ordered

    def checkFollowUpAfterOneMonth(self, lastVisitDate, today):
        m = today.month - 1 or 12
        y = today.year - int(today.month == 1)
        cutoff = date(y, m, min(today.day, monthrange(y, m)[1]))
        return not self.hasPlacedOrder() and not self.followUpClosed and lastVisitDate <= cutoff

    def offerOneTimeDiscount(self):
        return Decimal("0.10")

    def createCustomerAccount(self, billingAddress, deliveryAddress, consent):
        if not consent:
            raise ValueError("Account vereist toestemming")
        if not billingAddress or not deliveryAddress:
            raise ValueError("Beide adressen zijn verplicht")
        return Customer(self.companyName, deliveryAddress, billingAddress)
