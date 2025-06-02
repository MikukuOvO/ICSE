from locust import HttpUser, task, between

class UserBehavior(HttpUser):
    wait_time = between(1, 3)

    @task
    def login(self):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "username": "fdse_microservice",
            "password": "111111"
        }
        self.client.post("/api/v1/users/login", json=payload, headers=headers)
