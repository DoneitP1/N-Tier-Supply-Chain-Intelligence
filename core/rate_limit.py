import time
from functools import wraps
from fastapi import Request, HTTPException, status
from core.config import settings
import redis

# Use the same redis connection pool as the rest of the app
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def rate_limit(requests: int, window: int):
    """
    Rate limiting decorator using Redis.
    :param requests: Number of requests allowed
    :param window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to find the request object in kwargs or args
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # If no request object is found, we can't rate limit by IP
                # This might happen if the decorator is misused
                return await func(*args, **kwargs)

            client_ip = request.client.host
            key = f"rate_limit:{func.__name__}:{client_ip}"
            
            current = redis_client.get(key)
            
            if current and int(current) >= requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
            
            # Increment and set expiry if it's the first request in the window
            pipeline = redis_client.pipeline()
            pipeline.incr(key)
            if not current:
                pipeline.expire(key, window)
            pipeline.execute()
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
