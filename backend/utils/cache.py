from django.core.cache import cache as django_cache, caches  # noqa
from django_redis import get_redis_connection


class CacheProxy:
    """Expose Django cache operations plus the DB1 Redis list primitives in use."""

    def __getattr__(self, item):
        return getattr(django_cache, item)

    @staticmethod
    def _redis():
        return get_redis_connection("default", write=True)

    def llen(self, key):
        return self._redis().llen(key)

    def lpush(self, key, *values):
        return self._redis().lpush(key, *values)

    def rpop(self, key):
        return self._redis().rpop(key)

    def hget(self, key, field):
        return self._redis().hget(key, field)

    def hset(self, key, field, value):
        return self._redis().hset(key, field, value)

    def redis_incr(self, key, count=1):
        """Increment a raw Redis key, creating it when absent."""
        return self._redis().incr(key, count)


cache = CacheProxy()
