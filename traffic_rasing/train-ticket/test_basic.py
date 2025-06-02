from locust import HttpUser, task, between

class BasicServiceUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def call_welcome(self):
        response = self.client.get("/api/v1/basicservice/welcome")
        if "Welcome to [ Basic Service ]" not in response.text:
            response.failure("Unexpected response: " + response.text)
