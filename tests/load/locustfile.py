"""
Locust Load Test

Load testing configuration for ScholarSync API.
"""

from locust import HttpUser, task, between

# TODO: Implement load tests
# - API endpoint load tests
# - Concurrent user simulation
# - Performance metrics


class ScholarSyncUser(HttpUser):
    """Simulated user for load testing."""
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        """Health check endpoint."""
        self.client.get("/health")

