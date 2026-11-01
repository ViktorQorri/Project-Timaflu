"""Remaining case-domain classes from the DKD.

The school permits non-assessed methods to remain unimplemented.
No additional business functions are introduced.
"""

class Address:
    def __init__(self):
        self.address = None

    def updateAddress(self, address):
        pass


class OrderLine:
    def __init__(self):
        self.quantity = None
        self.unitPrice = None
        self.acceptShortage = None

    def adjustQuantity(self, quantity):
        pass

    def recordShortageChoice(self, accept):
        pass


class StockReservation:
    def __init__(self):
        self.reservedQuantity = None


class OrderStatus:
    def __init__(self):
        self.name = None


class ProductActiveIngredient:
    def __init__(self):
        self.ingredientName = None
        self.quantity = None


class Supplier:
    def __init__(self):
        self.name = None
        self.contactPerson = None
        self.phoneNumber = None
        self.website = None

    def updateDetails(self):
        pass


class SupplierOffer:
    def __init__(self):
        self.purchasePrice = None


class PurchaseOrder:
    def __init__(self):
        pass

    def placeWithSupplier(self):
        pass


class PurchaseOrderLine:
    def __init__(self):
        self.quantity = None


class Aisle:
    def __init__(self):
        self.letter = None


class WarehouseLocation:
    def __init__(self):
        self.shelfNumber = None
        self.quantity = None


class Robot:
    def __init__(self):
        pass

    def receiveSuborder(self, suborder):
        pass

    def pickCollectionBin(self):
        pass

    def scanCollectionBin(self, collectionBin):
        pass

    def collectMedicines(self):
        pass

    def placeBinOnConveyor(self):
        pass

    def markSuborderComplete(self):
        pass


class Suborder:
    def __init__(self):
        self.completed = None

    def checkCompleteness(self):
        pass

    def assignToRobot(self, robot):
        pass


class SuborderLine:
    def __init__(self):
        self.quantity = None


class CollectionBin:
    def __init__(self):
        self.uniqueCode = None

    def registerForSuborder(self, suborder):
        pass


class Courier:
    def __init__(self):
        self.name = None
        self.available = None
        self.inHouseCourier = None
        self.region = None

    def reportArrival(self):
        pass

    def reportAvailability(self):
        pass

    def viewAssignedRoutes(self):
        pass

    def lookUpCustomerPhoneNumber(self, customer):
        pass

    def lookUpDeliveryTime(self, order):
        pass


class Delivery:
    def __init__(self):
        pass


class DeliveryLine:
    def __init__(self):
        self.quantityDelivered = None


class PurchaseInvoice:
    def __init__(self):
        self.amount = None
        self.paidOn = None

    def pay(self):
        pass
