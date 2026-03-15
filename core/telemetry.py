import time
import logging
from functools import wraps
from prometheus_client import Summary, Counter

# Prometheus Metrics
LLM_LATENCY = Summary('llm_call_latency_seconds', 'Time spent processing LLM requests', ['provider', 'task_type'])
LLM_CALLS = Counter('llm_calls_total', 'Total number of LLM calls', ['provider', 'task_type', 'status'])

logger = logging.getLogger("ntier_telemetry")

def track_llm_performance(provider: str, task_type: str):
    """
    Decorator to track LLM call latency and success rates.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"LLM call failed ({provider}/{task_type}): {e}")
                raise e
            finally:
                latency = time.time() - start_time
                LLM_LATENCY.labels(provider=provider, task_type=task_type).observe(latency)
                LLM_CALLS.labels(provider=provider, task_type=task_type, status=status).inc()
                logger.info(f"LLM Telemetry: {provider}/{task_type} took {latency:.2f}s [Status: {status}]")
        
        # Determine if original is sync or async
        if hasattr(func, "__call__") and not hasattr(func, "__await__"):
            # Simplified for this project as most LLM calls are async ainvoke
            return async_wrapper
        return async_wrapper
    return decorator
