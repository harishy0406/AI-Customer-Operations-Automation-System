import json
import pickle

import numpy as np
from redis.asyncio import Redis

from src.api.config import get_settings

settings = get_settings()


class SemanticCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._namespace = "semantic_cache"

    def _cache_key(self, tenant_id: str, kb_version: int) -> str:
        return f"{self._namespace}:{tenant_id}:kb_{kb_version}"

    def _embedding_key(self, tenant_id: str, kb_version: int) -> str:
        return f"{self._namespace}_emb:{tenant_id}:kb_{kb_version}"

    async def get(self, query_embedding: list[float], tenant_id: str, kb_version: int) -> dict | None:
        if not settings.CACHE_ENABLED:
            return None
        cache_key = self._cache_key(tenant_id, kb_version)
        embedding_key = self._embedding_key(tenant_id, kb_version)

        embeddings_data = await self.redis.hgetall(embedding_key)
        if not embeddings_data:
            return None

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = query_vec / np.linalg.norm(query_vec)
        best_score = 0.0
        best_entry = None

        for entry_id, emb_bytes in embeddings_data.items():
            stored_vec = np.frombuffer(emb_bytes, dtype=np.float32)
            stored_norm = stored_vec / np.linalg.norm(stored_vec)
            similarity = float(np.dot(query_norm, stored_norm))
            if similarity > best_score and similarity >= settings.CACHE_SIMILARITY_THRESHOLD:
                best_score = similarity
                cached = await self.redis.hget(cache_key, entry_id)
                if cached:
                    best_entry = json.loads(cached)
                    best_entry["similarity"] = similarity

        return best_entry

    async def set(
        self, query_embedding: list[float], response_data: dict, tenant_id: str, kb_version: int, ttl: int | None = None
    ) -> None:
        if not settings.CACHE_ENABLED:
            return
        import uuid
        entry_id = str(uuid.uuid4())
        cache_key = self._cache_key(tenant_id, kb_version)
        embedding_key = self._embedding_key(tenant_id, kb_version)

        vec_bytes = np.array(query_embedding, dtype=np.float32).tobytes()

        await self.redis.hset(cache_key, entry_id, json.dumps(response_data))
        await self.redis.hset(embedding_key, entry_id, vec_bytes)

        ttl = ttl or settings.CACHE_TTL_SECONDS
        await self.redis.expire(cache_key, ttl)
        await self.redis.expire(embedding_key, ttl)

    async def invalidate_tenant(self, tenant_id: str, kb_version: int) -> None:
        cache_key = self._cache_key(tenant_id, kb_version)
        embedding_key = self._embedding_key(tenant_id, kb_version)
        await self.redis.delete(cache_key, embedding_key)

    async def clear_all(self) -> None:
        keys = await self.redis.keys(f"{self._namespace}:*")
        if keys:
            await self.redis.delete(*keys)
