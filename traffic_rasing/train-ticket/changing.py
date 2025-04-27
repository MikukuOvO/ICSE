from locust import HttpUser, task, between, LoadTestShape
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
    
    # @task(20)
    # def user_service(self):
    #     path = "/api/v1/userservice/users"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     num = random.randint(0, self.MAX_USER-1)
    #     path = f"/api/v1/userservice/users/user{num}"
    #     response = self.client.get(path)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
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
        # routes = response.json()['data']
        # route = random.choice(routes)
        # stations = ",".join(route['stations'])
        # distances = ",".join(map(str, route['distances']))
        # body = {"id": route['id'], "stationList": stations, "distanceList": distances, "startStation": route['startStation'], "endStation": route['endStation']}
        # response = self.client.post(path, json=body, headers=headers)
        # if response.status_code == 403:
        #     self.admin_login()
        #     headers = {
        #         "Authorization": f"Bearer {self.token}",
        #         "Content-Type": "application/json"
        #     }
        #     response = self.client.post(path, json=route, headers=headers)
        # if response.status_code != 200 and response.status_code != 201:
        #     response.failure("Unexpected response: " + response.text)
    
    # @task(20)
    # def train_service(self):
    #     path = "/api/v1/trainservice/trains"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     trains = response.json()['data']
    #     train = random.choice(trains)
    #     response = self.client.put(path, json=train, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.put(path, json=train, headers=headers)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)

    # @task(20)
    # def travel_service(self):
    #     path = "/api/v1/travelservice/trips"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     travels = response.json()['data']
    #     travel = random.choice(travels)
    #     trip_id = travel['tripId']['type'] + travel['tripId']['number']
        
    #     # path = f"/api/v1/travelservice/routes/{trip_id}"
    #     # response = self.client.get(path, headers=headers)
    #     # if response.status_code == 403:
    #     #     self.admin_login()
    #     #     headers = {
    #     #         "Authorization": f"Bearer {self.token}",
    #     #         "Content-Type": "application/json"
    #     #     }
    #     #     response = self.client.get(path, headers=headers)
    #     # if response.status_code != 200:
    #     #     response.failure("Unexpected response: " + response.text)

    #     path = "/api/v1/travelservice/trips"
    #     travel['tripId'] = trip_id
    #     response = self.client.put(path, json=travel, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.put(path, json=travel, headers=headers)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
        
    @task(20)
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

    @task(20)
    def station_service(self):
        path = "/api/v1/stationservice/stations"
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
        stations = response.json()['data']
        station = random.choice(stations)
        response = self.client.put(path, json=station, headers=headers)
        if response.status_code == 403:
            self.admin_login()
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            response = self.client.put(path, json=station, headers=headers)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)

    # @task(5)
    # def auth_service(self):
    #     path = "/api/v1/users"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     user = random.randint(0, self.MAX_USER-1)
    #     path = "/api/v1/users/login"
    #     user = {"username": f"user{user}", "password": f"user{user}"}
    #     response = self.client.post(path, json=user)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     self.token = response.json()['data']['token']

    # @task(10)
    # def notification_service(self):
    #     path = "/api/v1/notifyservice/test_send_mail"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)

    # @task(10)
    # def payment_service(self):
    #     path = "/api/v1/paymentservice/payment"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    
    # @task(10)
    # def price_service(self):
    #     path = "/api/v1/priceservice/prices"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = { 
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     prices = response.json()['data']
    #     price = random.choice(prices)
    #     response = self.client.put(path, json=price, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.put(path, json=price, headers=headers)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)

    # @task(10)
    # def adminorder_service(self):
    #     path = "/api/v1/adminorderservice/adminorder"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)
    #     adminorders = response.json()['data']
    #     adminorder = random.choice(adminorders)
    #     response = self.client.put(path, json=adminorder, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.put(path, json=adminorder, headers=headers)
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)

    # @task(10)
    # def adminroute_service(self):
    #     path = "/api/v1/adminrouteservice/adminroute"
    #     headers = {
    #         "Authorization": f"Bearer {self.token}",
    #         "Content-Type": "application/json"
    #     }
    #     response = self.client.get(path, headers=headers)
    #     if response.status_code == 403:
    #         self.admin_login()
    #         headers = {
    #             "Authorization": f"Bearer {self.token}",
    #             "Content-Type": "application/json"
    #         }
    #         response = self.client.get(path, headers=headers) 
    #     if response.status_code != 200:
    #         response.failure("Unexpected response: " + response.text)

    
class ModifiedLoadShape(LoadTestShape):
    """
    A modified load test shape that follows this pattern:
    - Stable low traffic (0% to 20% of total time)
    - Quick ramp up to peak (20% to 40% of total time)
    - Sustained peak traffic (40% to 60% of total time)
    - Quick ramp down to low (60% to 80% of total time)
    - Stable low traffic (80% to 100% of total time)
    """
    # total_time = 3600*6      # 120 minutes in seconds; adjust as needed
    total_time = 3600
    max_users = 200        # peak concurrency; adjust to suit your test scale
    min_users = 20         # baseline/low traffic level
    
    # Control parameters for the curve shape
    stable_low_until = 0.20      # Maintain baseline until this point
    ramp_up_until = 0.40         # When to reach peak users
    plateau_until = 0.60         # Maintain peak until this point
    ramp_down_until = 0.80       # When to complete ramp down
    
    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.total_time:
            return None  # end the test

        # Ratio of how far along we are in the entire test (0 to 1)
        ratio = run_time / self.total_time
        
        # Calculate available user range (after reserving baseline traffic)
        available_range = self.max_users - self.min_users

        if ratio <= self.stable_low_until:
            # Stable low traffic at beginning
            user_count = self.min_users
        
        elif ratio <= self.ramp_up_until:
            # Linear ramp up from min to max
            ramp_duration = self.ramp_up_until - self.stable_low_until
            ramp_progress = (ratio - self.stable_low_until) / ramp_duration
            user_count = self.min_users + (available_range * ramp_progress)
        
        elif ratio <= self.plateau_until:
            # Sustained peak traffic
            user_count = self.max_users
            
        elif ratio <= self.ramp_down_until:
            # Linear ramp down from max to min
            ramp_duration = self.ramp_down_until - self.plateau_until
            ramp_progress = (ratio - self.plateau_until) / ramp_duration
            remaining_ratio = 1 - ramp_progress
            user_count = self.min_users + (available_range * remaining_ratio)
            
        else:
            # Stable low traffic at end
            user_count = self.min_users

        # Determine spawn rate based on user count
        spawn_rate = max(5, int(user_count / 10))

        return int(user_count), spawn_rate