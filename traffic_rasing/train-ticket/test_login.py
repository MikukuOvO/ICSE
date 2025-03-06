from locust import HttpUser, task, between

class UserBehavior(HttpUser):
    # 设置用户请求之间的等待时间，单位为秒
    wait_time = between(1, 3)

    @task
    def login(self):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "username": "fdse_microservice",  # 注意去掉可能存在的空格
            "password": "111111"
        }
        # 发起 POST 请求，路径前缀由 --host 参数指定
        self.client.post("/api/v1/users/login", json=payload, headers=headers)
