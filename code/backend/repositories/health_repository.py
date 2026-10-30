class HealthRepository:
    """Database checks that do not belong to one aggregate."""

    def __init__(self, connection):
        """
        Args:
            connection: An open mysql.connector connection.
        """
        self.connection = connection

    def ping(self):
        """Run a trivial query.

        Returns:
            True when the database answers. A connection problem raises mysql.connector.Error.
        """
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone() == (1,)
