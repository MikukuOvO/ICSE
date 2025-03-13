from locust import HttpUser, task, between
import random

class BasicServiceUser(HttpUser):
    # 设置虚拟用户在任务之间随机等待 1 到 3 秒
    wait_time = between(1, 3)
    
    @task(20)
    def call_welcome(self):
        # 发送 GET 请求到 /api/v1/basicservice/welcome 接口
        path = "/api/v1/basicservice/welcome"
        response = self.client.get(path)
        # 如果需要可以添加简单的校验，比如检查响应内容是否包含 "Welcome to [ Basic Service ]"
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)

    @task(30)
    def get_user_list(self):
        path = "/api/v1/userservice/users"
        response = self.client.get(path)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)

    @task(50)
    def get_user(self):
        num = random.randint(0, 255)
        path = f"/api/v1/userservice/users/user{num}"
        response = self.client.get(path)
        if response.status_code != 200:
            response.failure("Unexpected response: " + response.text)
