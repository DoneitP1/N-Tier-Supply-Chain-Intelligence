import logging
from langchain_core.globals import set_llm_cache
from langchain_community.cache import RedisSemanticCache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.config import settings

logger = logging.getLogger("ntier_cache")

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
