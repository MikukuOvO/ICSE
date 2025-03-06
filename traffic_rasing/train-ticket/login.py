import requests
import json
from loguru import logger


def login(self, username="fdse_microservice", password="111111") -> bool:
    """
    登陆并建立session，返回登陆结果
    """
    url = f"{self.address}/api/v1/users/login"

    headers = {
        'Origin': url,
        'Referer': f"{self.address}/client_login.html",
    }

    data = {
        "username": username,
        "password": password,
        "verificationCode": ""
    }

    # 获取cookies
    verify_url = self.address + '/api/v1/verifycode/generate'
    r = self.session.get(url=verify_url)
    r = self.session.post(url=url, headers=headers,
                            data= json.dumps(data), verify=False)

    if r.status_code == 200:
        data = r.json()
        data = data.get("data")
        self.uid = data.get("userId")
        self.token = data.get("token")
        self.session.headers.update(
            {"Authorization": f"Bearer {self.token}"}
        )
        logger.info(f"login success, uid: {self.uid}")
        return True
    else:
        logger.error("login failed")
        return False