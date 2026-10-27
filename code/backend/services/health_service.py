class HealthService:
    """Reports whether the parts the backend depends on are available."""

    def __init__(self, health_repository):
        """
        Args:
            health_repository: A HealthRepository, or a fake one in tests.
        """
        self.health_repository = health_repository

    def database_is_reachable(self):
        """
        Returns:
            True when the database answers a query.
        """
        return self.health_repository.ping()
