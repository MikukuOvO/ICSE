# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import urllib.parse
import string
import random
import os
from locust import HttpUser, task, between, LoadTestShape

max_user_index = int(os.getenv("MAX_USER_INDEX", 962))

class UserBehavior(HttpUser):
    wait_time = between(1, 2)

    @task(65)
    def read_home_timeline(self):
        user_id = str(random.randint(0, max_user_index - 1))
        start = str(random.randint(0, 100))
        stop = str(int(start) + 10)
        path = f"/wrk2-api/home-timeline/read?user_id={user_id}&start={start}&stop={stop}"

        with self.client.get(path, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {response.status_code}")

    @task(20)
    def compose_post(self):
        user_index = random.randint(0, max_user_index - 1)
        username = "username_" + str(user_index)
        user_id = str(user_index)

        def stringRandom(length):
            charset = string.ascii_letters + string.digits
            return ''.join(random.choice(charset) for _ in range(length))

        def decRandom(length):
            return ''.join(random.choice("0123456789") for _ in range(length))

        text = stringRandom(256)
        num_user_mentions = random.randint(0, 5)
        num_urls = random.randint(0, 5)
        num_media = random.randint(0, 4)

        # Append user mentions
        for _ in range(num_user_mentions + 1):
            while True:
                mention_id = random.randint(0, max_user_index - 1)
                if mention_id != user_index:
                    break
            text += " @username_" + str(mention_id)

        # Append URLs
        for _ in range(num_urls + 1):
            text += " http://" + stringRandom(64)

        # Build media arrays
        media_ids_list = []
        media_types_list = []
        for _ in range(num_media + 1):
            media_id = decRandom(18)
            media_ids_list.append('"' + media_id + '"')
            media_types_list.append('"png"')

        media_ids = "[" + ",".join(media_ids_list) + "]"
        media_types = "[" + ",".join(media_types_list) + "]"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        body = (
            "username=" + urllib.parse.quote_plus(username) +
            "&user_id=" + urllib.parse.quote_plus(user_id) +
            "&text=" + urllib.parse.quote_plus(text) +
            "&media_ids=" + urllib.parse.quote_plus(media_ids) +
            "&media_types=" + urllib.parse.quote_plus(media_types) +
            "&post_type=0"
        )

        path = "/wrk2-api/post/compose"
        with self.client.post(path, data=body, headers=headers, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {response.status_code}")

    @task(15)
    def read_user_timeline(self):
        user_id = str(random.randint(0, max_user_index - 1))
        start = str(random.randint(0, 100))
        stop = str(int(start) + 10)
        path = f"/wrk2-api/user-timeline/read?user_id={user_id}&start={start}&stop={stop}"

        with self.client.get(path, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {response.status_code}")


class ConstantLoadShape(LoadTestShape):
    """
    A constant load test shape that maintains a steady level of traffic.
    Small random fluctuations (±15%) are added to simulate minor variations
    in a predominantly constant workload pattern.
    """
    total_time = 7200       # 120 minutes in seconds
    avg_users = 200         # target number of users
    fluctuation_pct = 0.15  # allow 15% random fluctuation
    
    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.total_time:
            return None  # end the test

        # Add small random fluctuations to create minor variations
        # while keeping the overall pattern relatively constant
        fluctuation = random.uniform(-self.fluctuation_pct, self.fluctuation_pct)
        user_count = int(self.avg_users * (1 + fluctuation))
        
        # Ensure we don't have negative users
        user_count = max(10, user_count)
        
        # Determine spawn rate based on user count
        spawn_rate = max(5, int(user_count / 10))

        return user_count, spawn_rate