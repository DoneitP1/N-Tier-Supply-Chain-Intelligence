import logging
from typing import Any, Optional
import redis
import json
from core.config import settings

logger = logging.getLogger("ntier_cache")
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def init_semantic_cache():
    """
    Initializes a semantic cache in Redis.
    Uses Google Generative AI Embeddings to find semantically similar queries.
    """
    if not settings.google_api_key:
        logger.warning("Google API Key missing. Semantic caching disabled.")
        return

    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.google_api_key
        )
        
        # Redis URL from settings
        redis_url = settings.redis_url
        
        set_llm_cache(RedisSemanticCache(
            redis_url=redis_url,
            embedding=embeddings,
            score_threshold=0.95 # Only hits if 95% similar
        ))
        logger.info("Semantic cache initialized on Redis.")
    except Exception as e:
        logger.error(f"Failed to initialize semantic cache: {e}")

# Note: We call this in main.py lifespan

async def set_cache(key: str, value: Any, expire: int = 3600):
    """Sets a value in Redis cache."""
    try:
        redis_client.setex(key, expire, json.dumps(value))
    except Exception as e:
        logger.error(f"Cache set error: {e}")

async def get_cache(key: str) -> Optional[Any]:
    """Gets a value from Redis cache."""
    try:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None

async def delete_cache_pattern(pattern: str):
    """Deletes all keys matching a pattern."""
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated cache for pattern: {pattern}")
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
