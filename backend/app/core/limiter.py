from slowapi import Limiter
from slowapi.util import get_remote_address

# Single shared limiter — import this everywhere instead of creating new instances.
# In-memory store is fine for single-process deploys; swap to Redis-backed storage
# for multi-instance deployments to share state across workers.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
