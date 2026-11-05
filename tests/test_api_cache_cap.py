"""The inmemory API response cache stays under config_api_cache_inmemory_max_kb per worker: over it, the oldest entries are dropped."""
import asyncio
import os
import unittest

from starlette.responses import Response

from function.middleware import func_middleware_api_cache

CACHE = {"mode": "inmemory", "ttl_sec": 60, "is_per_user": False}


class ApiCacheCapTests(unittest.TestCase):
    def set(self, cache, path, size, max_kb=2):
        body = os.urandom(size)    # random bytes do not shrink when gzipped, so each entry stores about its size
        asyncio.run(func_middleware_api_cache(mode="set", path=path, query_params={}, cache=CACHE, cache_api_response=cache, response=Response(content=body), config_api_cache_inmemory_max_kb=max_kb))

    def get(self, cache, path):
        return asyncio.run(func_middleware_api_cache(mode="get", path=path, query_params={}, cache=CACHE, cache_api_response=cache))

    def test_the_oldest_entries_go_when_the_cache_is_full(self):
        cache = {}
        for path in ("/a", "/b", "/c"): self.set(cache, path, 900)
        self.assertIsNone(self.get(cache, "/a"), "three 900-byte entries do not fit in 2 KB: the oldest went")
        self.assertIsNotNone(self.get(cache, "/b"))
        self.assertIsNotNone(self.get(cache, "/c"))
        self.assertLessEqual(sum(len(item["data"]) for item in cache.values()), 2048)

    def test_a_set_again_entry_counts_as_the_newest(self):
        cache = {}
        for path in ("/a", "/b", "/a", "/c"): self.set(cache, path, 900)
        self.assertEqual(sorted(cache), ["cache:api:/a?:0", "cache:api:/c?:0"])

    def test_a_value_holding_an_ampersand_is_its_own_entry(self):
        cache = {}
        asyncio.run(func_middleware_api_cache(mode="set", path="/a", query_params={"x": "1&y=2"}, cache=CACHE, cache_api_response=cache, response=Response(content=b"one")))
        self.assertIsNone(asyncio.run(func_middleware_api_cache(mode="get", path="/a", query_params={"x": "1", "y": "2"}, cache=CACHE, cache_api_response=cache)), "?x=1%26y%3D2 and ?x=1&y=2 are different queries")

    def test_the_kept_size_matches_the_entries(self):
        cache, size = {}, {"total": 0}
        for path, length in (("/a", 900), ("/b", 700), ("/a", 300), ("/c", 900), ("/d", 100)):
            asyncio.run(func_middleware_api_cache(mode="set", path=path, query_params={}, cache=CACHE, cache_api_response=cache, cache_api_response_bytes=size, response=Response(content=os.urandom(length)), config_api_cache_inmemory_max_kb=2))
            self.assertEqual(size["total"], sum(len(item["data"]) for item in cache.values()), f"after setting {path}")
        self.assertLessEqual(size["total"], 2048)

    def test_cleanup_takes_expired_entries_off_the_kept_size(self):
        from function.background import func_inmemory_cache_cleanup_periodic_task
        cache, size = {}, {"total": 0}
        for path in ("/a", "/b"): asyncio.run(func_middleware_api_cache(mode="set", path=path, query_params={}, cache=CACHE, cache_api_response=cache, cache_api_response_bytes=size, response=Response(content=os.urandom(500))))
        cache["cache:api:/a?:0"]["expire_at"] = 0
        async def one_round():
            task = asyncio.create_task(func_inmemory_cache_cleanup_periodic_task(cache_api_response=cache, cache_api_response_bytes=size, cache_ratelimiter={}, runtime_error_count={}, interval_sec=0))
            await asyncio.sleep(0.05)
            task.cancel()
        asyncio.run(one_round())
        self.assertEqual(list(cache), ["cache:api:/b?:0"])
        self.assertEqual(size["total"], len(cache["cache:api:/b?:0"]["data"]))

    def test_an_entry_bigger_than_the_cache_is_not_kept(self):
        cache = {}
        self.set(cache, "/small", 500)
        self.set(cache, "/huge", 5000)
        self.assertEqual(cache, {})


if __name__ == "__main__":
    unittest.main()
