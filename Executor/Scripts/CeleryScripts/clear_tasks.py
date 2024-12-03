import redis
import os


def clear_tasks():
    try:
        print("Starting clear_tasks.py")
        print("Attempting to clear Redis database...")

        # Use the Redis URL from environment or fallback to the service name
        redis_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

        # Extract host and port from redis_url
        if "://" in redis_url:
            redis_url = redis_url.split("://")[-1]
        host, port = redis_url.split(":")[0], int(redis_url.split(":")[1].split("/")[0])

        r = redis.Redis(host=host, port=port)
        r.flushall()
        print("Successfully cleared Redis database")
        return True
    except Exception as e:
        print(f"Error clearing Redis database: {str(e)}")
        return False


if __name__ == "__main__":
    success = clear_tasks()
    print("Finished clear_tasks.py")
    if not success:
        print("Failed to clear Celery tasks")
