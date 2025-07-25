import json
import time
import atexit
import threading
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.save_interval = 360  # Save interval: 1 hour
        
        # Load cache from file
        self.load_cache()

        # Register the save_cache method to be called when the program exits
        atexit.register(self.save_cache)

        # Start a separate thread to save the cache periodically
        self.save_thread = threading.Thread(target=self.save_cache_periodically)
        self.save_thread.daemon = True  # Daemonize the thread so it will be terminated when the main thread exits
        self.save_thread.start()
        print(type(self.cache))

    def get(self, key):
        if key in self.cache:
            # If the key exists, move it to the end (most recently used)
            value = self.cache[key]
            del self.cache[key]
            self.cache[key] = value
            return value
        else:
            return None

    def set(self, key, value):
        # Set the current time
        current_time = time.time()
        # Set the expiration time for the key (current time + 30 minutes)
        expiration_time = current_time + 1800  # 30 minutes * 60 seconds

        # Check if the cache is full
        if len(self.cache) >= self.capacity:
            # If so, remove the least recently used item (the first item in the cache)
            self.cache.popitem(last=False)
            # first_key = next(iter(self.cache))
            # self.cache.pop(first_key)

        # Add the new key-value pair to the cache with its expiration time
        self.cache[key] = (value, expiration_time)

    def save_cache(self):
        # Save the cache to a JSON file
        with open("cache.json", "w") as f:
            json.dump(self.cache, f)

    def load_cache(self):
        # Load the cache from the JSON file
        try:
            with open("cache.json", "r") as f:
                items = json.load(f)
                self.cache = OrderedDict(items)
        except FileNotFoundError:
            pass

    def save_cache_periodically(self):
        while True:
            time.sleep(self.save_interval)
            self.save_cache()
            for k, v in self.cache:
                if v[1] < time.time():
                    del self.cache[k]

    def clear(self):
        # Clear the cache
        self.cache.clear()

# # Example usage:
# cache = LRUCache(capacity=15)  # Cache capacity: 15

# # Add a key-value pair to the cache
# cache.set("key1", "value1")

# # Retrieve the value from the cache
# print(cache.get("key1"))  # Output: value1

# # Wait for 30 minutes (simulating the expiration time)
# time.sleep(1800)

# # Retrieve the value after 30 minutes
# print(cache.get("key1"))  # Output: None
