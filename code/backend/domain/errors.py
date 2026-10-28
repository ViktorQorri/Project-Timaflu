class DomainError(Exception):
    """A business rule was broken.

    Services raise it, the error handlers in app.py turn it into a message on the page
    or a 4xx JSON answer for the robots.
    """

    status_code = 400


class NotFoundError(DomainError):
    """The requested object does not exist, for example an unknown order or crate."""

    status_code = 404


class ConflictError(DomainError):
    """The request clashes with the current state, for example an order that is already delivered."""

    status_code = 409
