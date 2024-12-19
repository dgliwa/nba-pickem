import redis
import os

client = redis.Redis.from_url(os.environ.get("REDIS_URL"))
