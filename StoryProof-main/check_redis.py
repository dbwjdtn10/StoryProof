
import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    if r.ping():
        print("Redis connection successful!")
except Exception as e:
    print(f"Redis connection failed: {e}")
