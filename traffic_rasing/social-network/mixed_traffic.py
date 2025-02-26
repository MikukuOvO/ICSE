# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import urllib.parse
import string
import random
import os
from locust import HttpUser, task, between

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
        # Generate a random user index (0 to max_user_index - 1)
        user_index = random.randint(0, max_user_index - 1)
        username = "username_" + str(user_index)
        user_id = str(user_index)
        
        # Helper functions similar to Lua's stringRandom and decRandom.
        def stringRandom(length):
            # Use letters (both cases) and digits as our charset.
            charset = string.ascii_letters + string.digits
            return ''.join(random.choice(charset) for _ in range(length))
        
        def decRandom(length):
            # Generate a numeric string.
            return ''.join(random.choice("0123456789") for _ in range(length))
        
        # Generate a base text of 256 random characters.
        text = stringRandom(256)
        
        # Determine random counts (Lua iterates from 0 to N, so we do N+1 iterations)
        num_user_mentions = random.randint(0, 5)
        num_urls = random.randint(0, 5)
        num_media = random.randint(0, 4)
        
        # Append user mentions.
        for _ in range(num_user_mentions + 1):
            while True:
                mention_id = random.randint(0, max_user_index - 1)
                if mention_id != user_index:
                    break
            text += " @username_" + str(mention_id)
        
        # Append URLs.
        for _ in range(num_urls + 1):
            text += " http://" + stringRandom(64)
        
        # Build media arrays.
        media_ids_list = []
        media_types_list = []
        for _ in range(num_media + 1):
            media_id = decRandom(18)
            media_ids_list.append('"' + media_id + '"')
            media_types_list.append('"png"')
        # Build JSON-like array strings.
        media_ids = "[" + ",".join(media_ids_list) + "]"
        media_types = "[" + ",".join(media_types_list) + "]"
        
        # Set header to use URL-encoded form data.
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        # Build the body string. We use urllib.parse.quote_plus to URL-encode each value.
        body = (
            "username=" + urllib.parse.quote_plus(username) +
            "&user_id=" + urllib.parse.quote_plus(user_id) +
            "&text=" + urllib.parse.quote_plus(text) +
            "&media_ids=" + urllib.parse.quote_plus(media_ids) +
            "&media_types=" + urllib.parse.quote_plus(media_types) +
            "&post_type=0"
        )
        
        # Define the API endpoint (path).
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