from datetime import date
from flask import Blueprint, render_template, request
from db import get_connection
from repositories.sales_stock_repository import SalesStockRepository
from repositories.assessed_repository import AssessedRepository
from services.sales_stock_service import SalesStockService
from domain.business import Order
from domain.errors import DomainError

sales=Blueprint("sales",__name__)

@sales.get("/customers")
def customers():
    return render_template("customers.html")

@sales.get("/orders")
def orders():
    query=request.args.get("q","",type=str).strip()
    quantity=request.args.get("quantity","1",type=str)
    products=SalesStockService(SalesStockRepository(get_connection())).check(query,quantity) if query else []
    return render_template("orders.html",query=query,quantity=quantity,products=products)

@sales.post("/orders/calculate-discount")
def calculate_order_discount():
    try:
        customer_id=int(request.form["customer_id"])
        subtotal=request.form["subtotal"]
    except (TypeError,ValueError,KeyError) as exc:
        raise DomainError("Klantnummer en ordertotaal zijn verplicht.") from exc
    if customer_id<=0:
        raise DomainError("Klantnummer moet positief zijn.")
    repository=AssessedRepository(get_connection())
    customer,revenue=repository.customer_revenue(customer_id,date.today().year-1)
    first_order=repository.customer_order_count(customer_id)==0
    result=Order(subtotal,revenue,first_order).calculateTotalAmount()
    return render_template("discount.html",customer=customer,annual_revenue=revenue,
                           first_order=first_order,discount=result)
