"""Postgres queries per request for Atom's busiest routes, counted exactly on a throwaway database.

Timings vary 20-30% between CI runs, so this test counts what does not vary: the queries each
request sends (its background work included). A change that adds a query to one of these routes
fails here; if the change means it, update BUDGET in the same commit, so the reason is in the diff.
Each request runs once to warm up (asyncpg's type lookup on a new connection, a first cache miss),
then is counted on its second run.
"""
import time
import unittest

import asyncpg

from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import requires_postgres

# label: (method, path, needs a token, JSON body, Postgres queries allowed)
BUDGET = {
    "login": ("POST", "/auth/login-username-password", False, {"username": "budget", "password": "budget-pass"}, 1),
    "token-refresh": ("POST", "/my/token-refresh", "refresh", None, 1),
    "profile": ("GET", "/my/profile", True, None, 2),    # the user row, and last_active_at (config_is_profile_update_last_active_at)
    "object-create": ("POST", "/my/object-create?table=test", True, {"title": "budget"}, 1),
    "object-read-my": ("GET", "/my/object-read?table=test&limit=20", True, None, 1),
    "object-read-public-cached": ("GET", "/public/object-read?table=test&limit=20", False, None, 0),
    "object-read-public-uncached": ("GET", "/public/object-read?table=test&limit=20&is_disable_cache=true", False, None, 1),
    "object-update": ("PUT", "/my/object-update?table=test", True, {"id": 1, "title": "budget 2"}, 1),
    "info": ("GET", "/info", False, None, 0),
}


@requires_postgres
class QueryBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queries = []
        cls.create_pool = asyncpg.create_pool
        def counting_pool(*args, **kwargs):
            # every pool connection reports each query it runs (asyncpg query logger)
            init = kwargs.pop("init", None)
            async def counting_init(conn):
                conn.add_query_logger(lambda record: cls.queries.append(record.query))
                if init: await init(conn)
            return cls.create_pool(*args, init=counting_init, **kwargs)
        asyncpg.create_pool = counting_pool
        cls.db_name, url = create_database()
        try:
            # periodic tasks (buffer flush, cleanups) stay quiet so only requests send queries; API logging goes to the buffer, not a query
            cls.handle = app_start(env={"config_postgres_url_master": url, "config_postgres_buffer_flush_auto_sec": "3600"})
        except BaseException:
            asyncpg.create_pool = cls.create_pool
            drop_database(cls.db_name)
            raise
        cls.client = cls.handle["client"]
        app_login(cls.client, path="/auth/signup-username-password", body={"username": "budget", "password": "budget-pass", "role": 5})
        tokens = cls.client.post("/auth/login-username-password", json={"username": "budget", "password": "budget-pass"}).json()["message"]
        cls.tokens = {True: tokens["access_token"], "refresh": tokens["refresh_token"]}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally:
            asyncpg.create_pool = cls.create_pool
            drop_database(cls.db_name)

    def idle_wait(self):
        """Wait for the request's background work (such as last_active_at), so its queries count for it, not the next request."""
        for _ in range(500):
            if not self.handle["app"].state.runtime_background_tasks: return
            time.sleep(0.01)
        self.fail("background tasks did not finish")

    def request_queries(self, *, method, path, token, body):
        headers = {"Authorization": f"Bearer {self.tokens[token]}"} if token else {}
        self.queries.clear()
        response = self.client.request(method, path, headers=headers, json=body)
        self.idle_wait()
        self.assertEqual(response.status_code, 200, f"{method} {path}: {response.text[:200]}")
        return list(self.queries)

    def test_queries_per_request_stay_within_budget(self):
        over = []
        for label, (method, path, token, body, allowed) in BUDGET.items():
            with self.subTest(label):
                self.request_queries(method=method, path=path, token=token, body=body)    # warm up
                queries = self.request_queries(method=method, path=path, token=token, body=body)
                if len(queries) != allowed: over.append(f"{label}: {len(queries)} queries, budget {allowed}:\n    " + "\n    ".join(" ".join(query.split())[:150] for query in queries))
        self.assertFalse(over, "Postgres queries per request changed; if the change means it, update BUDGET in tests/integration/test_query_budget.py:\n" + "\n".join(over))


if __name__ == "__main__":
    unittest.main()
