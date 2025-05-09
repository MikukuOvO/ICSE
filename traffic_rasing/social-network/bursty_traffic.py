# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import urllib.parse
import math
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


class BurstyLoadShape(LoadTestShape):
    """
    A bursty load test shape with controlled traffic spikes followed by periods of calm.
    
    This pattern simulates workloads with sudden, significant increases in traffic
    that appear randomly and subside gradually, which is common in event-driven systems
    or during flash sales/events.
    """
    total_time = 7200       # 120 minutes in seconds
    base_users = 20         # baseline user count during normal periods
    max_burst = 200         # maximum users during a burst (reduced from 450)
    
    # Burst parameters
    burst_duration = 240    # how long each burst lasts (4 min, increased for gradual transitions)
    calm_duration = 480     # minimum time between bursts (8 min)
    num_bursts = 8          # target number of bursts during the test
    
    def __init__(self):
        super().__init__()
        # Pre-calculate burst start times
        self.burst_times = []
        available_time = self.total_time - (self.num_bursts * self.burst_duration)
        min_spacing = self.calm_duration
        
        # First burst after some initial calm period
        first_burst = random.randint(min_spacing, int(available_time/5))
        self.burst_times.append(first_burst)
        
        remaining_bursts = self.num_bursts - 1
        remaining_time = self.total_time - first_burst - self.burst_duration
        
        for i in range(remaining_bursts):
            # Calculate latest this burst can start to maintain minimum spacing
            latest_start = self.total_time - (remaining_bursts - i) * (self.burst_duration + min_spacing)
            
            # Calculate earliest this burst can start based on previous burst
            earliest_start = self.burst_times[-1] + self.burst_duration + min_spacing
            
            if latest_start <= earliest_start:
                # Can't fit all remaining bursts with constraints
                burst_time = earliest_start
            else:
                burst_time = random.randint(earliest_start, latest_start)
                
            self.burst_times.append(burst_time)
            
    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.total_time:
            return None  # end the test

        # Check if we're in a burst period
        in_burst = False
        for burst_start in self.burst_times:
            burst_end = burst_start + self.burst_duration
            if burst_start <= run_time < burst_end:
                in_burst = True
                progress = (run_time - burst_start) / self.burst_duration
                
                # Shape of burst: more gradual ramp up and down
                if progress < 0.35:  # Ramp up (first 35% of burst - more gradual)
                    ramp_progress = progress / 0.35
                    # Use a smooth curve (quadratic) for more gradual initial ramp
                    curve_factor = ramp_progress * ramp_progress
                    user_count = self.base_users + (self.max_burst - self.base_users) * curve_factor
                elif progress > 0.65:  # Ramp down (last 35% of burst - more gradual)
                    ramp_progress = (progress - 0.65) / 0.35
                    # Use a smooth curve for gentler ramp down
                    curve_factor = 1 - (ramp_progress * ramp_progress)
                    user_count = self.base_users + (self.max_burst - self.base_users) * curve_factor
                else:  # Plateau (middle 30% of burst)
                    user_count = self.max_burst
                    
                # Add very small noise for realism (reduced from original)
                user_count = int(user_count * random.uniform(0.97, 1.03))
                break
        
        if not in_burst:
            # Between bursts: baseline with controlled fluctuations
            # Use sine wave for natural-feeling fluctuations around base level
            fluctuation = math.sin(run_time / 300) * 0.1  # 10% fluctuation with 5-minute period
            user_count = int(self.base_users * (1 + fluctuation))
        
        # Ensure reasonable bounds
        user_count = max(50, min(300, user_count))
        
        # More conservative spawn rate to prevent overwhelming the system
        # Higher spawn rates during increase periods, lower during decreases
        if in_burst and progress < 0.35:
            # Faster spawn during ramp up
            spawn_rate = max(5, int(user_count / 12))
        elif in_burst and progress > 0.65:
            # Slower despawn during ramp down
            spawn_rate = max(3, int(user_count / 25))
        else:
            # Normal spawn rate otherwise
            spawn_rate = max(4, int(user_count / 15))

        return user_count, spawn_rate