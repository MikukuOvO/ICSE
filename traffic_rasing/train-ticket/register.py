import requests
import random

def admin_login():
    API_URL = "http://192.168.49.2:32677/api/v1/users/login"
    user = {"username": "admin", "password": "222222"}
    response = requests.post(API_URL, json=user)
    return response.json()['data']['token']

def register_users():
    API_URL = "http://192.168.49.2:32677/api/v1/userservice/users/register"
    MAX_USER = 256
    users = []
    for i in range(MAX_USER):
        username = f"user{i}"
        password = f"user{i}"  # 统一的密码，可修改
        users.append({"userName": username, "password": password, "userId": i})
    for user in users:
        response = requests.post(API_URL, json=user)
        if response.status_code == 201:
            print(f"注册成功: {user['userName']}")
        else:
            print(f"注册失败: {user['userName']} - {response.text}")

def add_stations(token):
    API_URL = "http://192.168.49.2:32677/api/v1/stationservice/stations"
    MAX_STATION = 100
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    stations = []
    for i in range(MAX_STATION):
        id = i
        name = f"station{i}"
        stayTime = random.randint(0, 10)
        stations.append({"id": id, "name": name, "stayTime": stayTime})
    for station in stations:
        response = requests.post(API_URL, json=station, headers=headers)
        if response.status_code == 201:
            print(f"Succeed: {station['id']}")
        else:
            print(f"Fail: {station['id']} - {response.text}")

def get_routes(token):
    API_URL = "http://192.168.49.2:32677/api/v1/routeservice/routes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(API_URL, headers=headers)
    print(response.json())

def test_routes(token):
    path = "http://192.168.49.2:32677/api/v1/routeservice/routes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(path, headers=headers)
    print(response.json())
    routes = response.json()['data']
    route = random.choice(routes)
    stations = ",".join(route['stations'])
    distances = ",".join(map(str, route['distances']))
    body = {"id": route['id'], "stationList": stations, "distanceList": distances, "startStation": route['startStation'], "endStation": route['endStation']}
    response = requests.post(path, json=body, headers=headers)
    print(response.json())

def test(token):
    API_URL = "http://192.168.49.2:32677/api/v1/stationservice/stations"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(API_URL, headers=headers)
    print(response.json())


if __name__ == "__main__":
    # register_users()
    token = admin_login()
    print(token)
    # add_stations(token)
    # get_routes(token)
    test(token)
    