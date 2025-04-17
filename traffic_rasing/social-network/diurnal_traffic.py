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


class ModifiedLoadShape(LoadTestShape):
    """
    A modified load test shape that follows this pattern:
    - Stable low traffic (0% to 20% of total time)
    - Quick ramp up to peak (20% to 40% of total time)
    - Sustained peak traffic (40% to 60% of total time)
    - Quick ramp down to low (60% to 80% of total time)
    - Stable low traffic (80% to 100% of total time)
    """
    total_time = 7200      # 120 minutes in seconds; adjust as needed
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