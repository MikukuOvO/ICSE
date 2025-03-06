from locust import HttpUser, task, between

class BasicServiceUser(HttpUser):
    # 设置虚拟用户在任务之间随机等待 1 到 3 秒
    wait_time = between(1, 3)
    
    @task
    def call_welcome(self):
        # 发送 GET 请求到 /api/v1/basicservice/welcome 接口
        response = self.client.get("/api/v1/basicservice/welcome")
        # 如果需要可以添加简单的校验，比如检查响应内容是否包含 "Welcome to [ Basic Service ]"
        if "Welcome to [ Basic Service ]" not in response.text:
            response.failure("Unexpected response: " + response.text)
