import json

from locust import HttpUser, between, task


class MeshMasterUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Simulate fast user interactions

    def on_start(self):
        self.client.headers.update({"X-Kosatka-Key": "default-key"})  # Match default api_key

    @task(3)
    def get_nodes(self):
        self.client.get("/api/v1/nodes/")

    @task(5)
    def get_stats(self):
        self.client.get("/api/v1/stats/summary/")

    @task(2)
    def get_alerts(self):
        self.client.get("/api/v1/nodes/alerts/")

    @task(1)
    def check_health(self):
        self.client.get("/health")


class MeshAgentUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers.update({"X-Kosatka-Key": "default-key"})

    @task(1)
    def health_check(self):
        self.client.get("/health/")
