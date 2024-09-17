import os
import sys
import redis
from celery import Celery

# Define constants and load environment variables
DIR = os.getcwd()
sys.path.append(DIR)  # Add the current directory to the system path

# Create a Celery app instance
app = Celery("tasks")
app.config_from_object("Executor.Scripts.CeleryScripts.celeryconfig")

# Redis client
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0)


def clear_celery_tasks():
    try:
        print("Attempting to clear Redis database...")
        result = redis_client.flushdb()
        print(f"Redis database cleared: {result}")
        return "All Celery tasks cleared from Redis"
    except redis.RedisError as e:
        print(f"Error clearing Redis database: {e}")
        return f"Failed to clear Celery tasks: {e}"


if __name__ == "__main__":
    print("Starting clear_tasks.py")
    result = clear_celery_tasks()
    print(result)
    print("Finished clear_tasks.py")
