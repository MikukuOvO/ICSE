from locust import HttpUser, task, between
import random

class BasicServiceUser(HttpUser):
    # 设置虚拟用户在任务之间随机等待 1 到 3 秒
    wait_time = between(1, 3)
    MAX_USER = 256
    token = ""

    def admin_login(self):
        path = "/api/v1/users/login"
        user = {"username": "admin", "password": "222222"}
        response = self.client.post(path, json=user)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        self.token = response.json()['data']['token']
    
    @task(20)
    def user_service(self):
        path = "/api/v1/userservice/users"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers) 
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        num = random.randint(0, self.MAX_USER-1)
        path = f"/api/v1/userservice/users/user{num}"
        response = self.client.get(path)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        # users = response.json()['data']
        # user = random.choice(users)
        # response = self.client.put(f"/api/v1/userservice/users", json=user, headers=headers)
        # if response.status_code == 403:
        #     self.admin_login()
        #     headers = {
        #         "Authorization": f"Bearer {self.token}",
        #         "Content-Type": "application/json"
        #     }
        #     response = self.client.put(f"/api/v1/userservice/users", json=user, headers=headers)
        # if response.status_code != 200:
        #     response.failure("Unexpected response: " + response.text)

    @task(20)
    def route_service(self):
        path = "/api/v1/routeservice/routes"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers) 
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        routes = response.json()['data']
        route = random.choice(routes)
        stations = ",".join(route['stations'])
        distances = ",".join(map(str, route['distances']))
        body = {"id": route['id'], "stationList": stations, "distanceList": distances, "startStation": route['startStation'], "endStation": route['endStation']}
        response = self.client.post(path, json=body, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.post(path, json=route, headers=headers)
        if response.status_code != 200 and response.status_code != 201:
            response.failure("Unexpected response: " + response.text)
    
    @task(20)
    def train_service(self):
        path = "/api/v1/trainservice/trains"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers) 
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        trains = response.json()['data']
        train = random.choice(trains)
        response = self.client.put(path, json=train, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.put(path, json=train, headers=headers)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)

    @task(20)
    def travel_service(self):
        path = "/api/v1/travelservice/trips"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers) 
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        travels = response.json()['data']
        travel = random.choice(travels)
        trip_id = travel['tripId']['type'] + travel['tripId']['number']
        
        path = f"/api/v1/travelservice/routes/{trip_id}"
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)

        path = "/api/v1/travelservice/trips"
        travel['tripId'] = trip_id
        response = self.client.put(path, json=travel, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.put(path, json=travel, headers=headers)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        
    @task(10)
    def order_service(self):
        path = "/api/v1/orderservice/order"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers) 
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        orders = response.json()['data']
        order = random.choice(orders)
        response = self.client.put(path, json=order, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.put(path, json=order, headers=headers)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)

    @task(10)
    def auth_service(self):
        path = "/api/v1/users"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        response = self.client.get(path, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.get(path, headers=headers) 
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        user = random.randint(0, self.MAX_USER-1)
        path = "/api/v1/users/login"
        user = {"username": f"user{user}", "password": f"user{user}"}
        response = self.client.post(path, json=user)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
        self.token = response.json()['data']['token']