from flask import Blueprint, render_template

acquisition = Blueprint("acquisition", __name__)


@acquisition.get("/acquisition")
def index():
    """Show the acquisition page."""
    return render_template("acquisition.html")
