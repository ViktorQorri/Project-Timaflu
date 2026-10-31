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
    def __init__(self, subtotal, annualRevenue=0, firstOrder=False):
        self.subtotal = euro(subtotal)
        self.annualRevenue = euro(annualRevenue)
        self.firstOrder = firstOrder

    def calculateOrderDiscount(self):
        return euro(self.subtotal * Decimal("0.05")) if self.subtotal >= 500 else euro(0)

    def calculateOneTimeDiscount(self):
        return euro((self.subtotal - self.calculateOrderDiscount()) * Decimal("0.10")) if self.firstOrder else euro(0)

    def calculateCustomerDiscount(self):
        after = self.subtotal - self.calculateOrderDiscount() - self.calculateOneTimeDiscount()
        return euro(after * CustomerDiscount().determinePercentage(self.annualRevenue))

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

    def createWeeklyInvoice(self, customerName, customerAddress, lines, annualRevenue, firstOrder):
        """Use explicitly confirmed discount inputs; never default historical facts."""
        items = []
        for line in lines:
            qty = int(line["quantity"])
            if qty <= 0:
                raise ValueError("Aantal moet positief zijn")
            price = euro(line["unit_price"])
            items.append({"quantity": qty, "unit_price": price, "line_total": euro(qty * price)})
        subtotal = euro(sum((line["line_total"] for line in items), Decimal(0)))
        vat = euro(subtotal * Decimal("0.09"))
        gross = subtotal + vat
        discounts = Order(gross, annualRevenue, firstOrder).calculateTotalAmount()
        after_order = euro(gross - discounts["order_discount"])
        after_first_order = euro(after_order - discounts["first_order_discount"])
        return {"total_after_order_discount": after_order,
                "total_after_first_order_discount": after_first_order,
                "date": self.invoiceDate, "invoice_number": self.invoiceNumber,
                "customer_number": self.customerNumber, "customer_name": customerName,
                "customer_address": customerAddress, "lines": items,
                "total_ex_vat": subtotal, "vat_9_percent": vat, "total_incl_vat": gross,
                **discounts}

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
