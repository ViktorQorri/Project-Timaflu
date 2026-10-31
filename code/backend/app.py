from pathlib import Path
from datetime import date
import click

from flask import Flask, jsonify, render_template, request
from mysql.connector import Error as DatabaseError
from werkzeug.exceptions import HTTPException

from config import Config
from db import close_connection
from domain.errors import DomainError
from routes.acquisition import acquisition
from routes.administration import administration
from routes.weekly_invoices import weekly_invoices
from routes.api import api
from routes.distribution import distribution
from routes.home import home
from routes.order_picking import order_picking
from routes.purchasing import purchasing
from routes.reports import reports
from routes.sales import sales

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

# Dutch texts for the standard HTTP errors, whose own descriptions are English.
HTTP_MESSAGES = {
    400: "Het verzoek is ongeldig.",
    403: "Je hebt geen toegang tot deze pagina.",
    404: "Deze pagina bestaat niet.",
    405: "Deze actie is hier niet toegestaan.",
}


def create_app(config=Config):
    """Create the Flask app and register the routes and error handlers.

    Args:
        config: The settings class, Config by default.

    Returns:
        The Flask app.
    """
    app = Flask(
        __name__,
        template_folder=FRONTEND / "templates",
        static_folder=FRONTEND / "static",
    )
    app.config.from_object(config)
    app.teardown_appcontext(close_connection)

    app.register_blueprint(home)
    app.register_blueprint(sales)
    app.register_blueprint(purchasing)
    app.register_blueprint(order_picking)
    app.register_blueprint(distribution)
    app.register_blueprint(administration)
    app.register_blueprint(weekly_invoices)
    app.register_blueprint(acquisition)
    app.register_blueprint(reports)
    app.register_blueprint(api, url_prefix="/api")

    @app.cli.command("issue-weekly-invoices")
    @click.option("--week-start", required=True, help="Maandag jjjj-mm-dd van een afgesloten week")
    def issue_weekly_invoices_cli(week_start):
        """Use from a verified weekly scheduler; do not send email."""
        from db import get_connection
        from repositories.weekly_invoice_repository import WeeklyInvoiceRepository
        try:
            start = date.fromisoformat(week_start)
        except ValueError as exc:
            raise click.ClickException("Ongeldige week_start.") from exc
        try:
            ids = WeeklyInvoiceRepository(get_connection()).issue_week(
                start, app.config["TIMAFLU_ADDRESS"]
            )
        except DomainError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Weekfacturen vastgelegd: {len(ids)}; IDs: {','.join(map(str, ids))}")

    register_error_handlers(app)
    return app


def register_error_handlers(app):
    """Turn errors into an error page for the browser, or a JSON answer for the robots.

    Args:
        app: The Flask app.
    """

    def respond(status, message):
        if request.path.startswith("/api/"):
            return jsonify(error=message), status
        return render_template("error.html", status=status, message=message), status

    @app.errorhandler(DomainError)
    def domain_error(error):
        return respond(error.status_code, str(error))

    @app.errorhandler(HTTPException)
    def http_error(error):
        # Keep a description given with abort(), replace the standard English one.
        if error.description == type(error).description:
            message = HTTP_MESSAGES.get(error.code, "Er ging iets mis met dit verzoek.")
        else:
            message = error.description
        return respond(error.code, message)

    @app.errorhandler(DatabaseError)
    def database_error(error):
        app.logger.error("Database error", exc_info=error)
        return respond(503, "De database is niet bereikbaar. Probeer het later opnieuw.")

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.error("Unexpected error", exc_info=error)
        return respond(500, "Er ging iets mis. Probeer het later opnieuw.")


if __name__ == "__main__":
    create_app().run(debug=True)
