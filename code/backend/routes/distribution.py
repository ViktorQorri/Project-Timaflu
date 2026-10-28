from flask import Blueprint, render_template

distribution = Blueprint("distribution", __name__)


@distribution.get("/deliveries")
def deliveries():
    """Show the deliveries page."""
    return render_template("deliveries.html")
