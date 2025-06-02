from locust import HttpUser, task, between

class BasicServiceUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def call_welcome(self):
        response = self.client.get("/api/v1/userservice/users")
        
