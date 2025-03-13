import requests

# 目标 API 地址（请替换为实际的注册接口地址）
API_URL = "http://192.168.58.2:32677/api/v1/userservice/users/register"

# 生成 256 个用户
def generate_users():
    users = []
    for i in range(256):
        username = f"user{i}"
        password = f"user{i}"  # 统一的密码，可修改
        users.append({"userName": username, "password": password, "userId": i})
    return users

# 发送 POST 请求注册用户
def register_users(users):
    for user in users:
        response = requests.post(API_URL, json=user)
        if response.status_code == 201:
            print(f"注册成功: {user['userName']}")
        else:
            print(f"注册失败: {user['userName']} - {response.text}")

if __name__ == "__main__":
    users = generate_users()
    register_users(users)