import json
import time
import atexit
import threading
import sched
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.save_interval = 3600  # Save interval: 1 hour
        self.cleanup_interval = 300  # Cleanup interval: 5 minutes
        self.scheduler = sched.scheduler(time.time, time.sleep)

        # Load cache from file
        self.load_cache()

        # Register the save_cache method to be called when the program exits
        atexit.register(self.save_cache)

        # Start a separate thread to save the cache periodically
        self.save_thread = threading.Thread(target=self.save_cache_periodically)
        self.save_thread.daemon = True  # Daemonize the thread so it will be terminated when the main thread exits
        self.save_thread.start()

        # Start a separate thread to perform cache cleanup periodically
        self.cleanup_thread = threading.Thread(target=self.cleanup_cache_periodically)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()

    def get(self, key):
        if key in self.cache:
            value, expiration_time = self.cache[key]
            if expiration_time < time.time():
                del self.cache[key]
                return None
            else:
                # Move the key to the end (most recently used)
                del self.cache[key]
                self.cache[key] = (value, expiration_time)
                return value
        else:
            return None

    def set(self, key, value):
        # Set the expiration time for the key (current time + 30 minutes)
        expiration_time = time.time() + 1800  # 30 minutes * 60 seconds

        # Check if the cache is full
        if len(self.cache) >= self.capacity:
            # If so, remove the least recently used item (the first item in the cache)
            self.cache.popitem(last=False)

        # Add the new key-value pair to the cache with its expiration time
        self.cache[key] = (value, expiration_time)

    def save_cache(self):
        # Save the cache to a JSON file
        with open("cache.json", "w") as f:
            json.dump(list(self.cache.items()), f)

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

    def cleanup_cache_periodically(self):
        while True:
            time.sleep(self.cleanup_interval)
            self.cleanup_cache()

    def cleanup_cache(self):
        current_time = time.time()
        print(self.cache)
        keys_to_remove = [key for key, (_, expiration_time) in self.cache.items() if expiration_time < current_time]
        for key in keys_to_remove:
            del self.cache[key]

    def clear(self):
        # Clear the cache
        self.cache.clear()
