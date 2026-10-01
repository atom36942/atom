"""Real SQL against a throwaway PostgreSQL database built by Atom's own schema init."""
import asyncio
import unittest
from types import SimpleNamespace

import asyncpg
from argon2 import PasswordHasher

import function
from function import (
    func_auth_login_password, func_auth_signup_password, func_otp_generate, func_otp_verify,
    func_postgres_create, func_postgres_delete, func_postgres_read, func_postgres_schema_init,
    func_postgres_schema_read, func_postgres_update,
)
from tests.integration.support import config_postgres, create_database, drop_database, requires_postgres

HASHER = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)


async def schema_init(url):
    pool = await asyncpg.create_pool(url, min_size=1, max_size=2)
    try:
        app_state = SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})
        return await func_postgres_schema_init(app_state=app_state, client_postgres=pool, config_postgres=config_postgres(),
                                               root_user_password_hash=HASHER.hash("root-test-password"))
    finally:
        await pool.close()


@requires_postgres
class PostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.template, template_url = create_database()
        asyncio.run(schema_init(template_url))

    @classmethod
    def tearDownClass(cls):
        drop_database(cls.template)

    async def asyncSetUp(self):
        # A fresh copy of the initialised schema per test; Atom blocks TRUNCATE, so tests never clean up tables.
        self.db_name, self.url = await asyncio.to_thread(create_database, self.template)
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=25)
        self.schema = await func_postgres_schema_read(client_postgres=self.pool)

    async def asyncTearDown(self):
        await self.pool.close()
        await asyncio.to_thread(drop_database, self.db_name)

    async def create(self, table, rows, mode="now", buffer=None):
        return await func_postgres_create(client_postgres=self.pool, client_postgres_conn=None, client_password_hasher=HASHER,
                                          cache_postgres_schema=self.schema, cache_postgres_buffer={} if buffer is None else buffer,
                                          config_column_regex={}, buffer_limit=10, mode=mode, table=table, obj_list=rows)

    async def read(self, **changes):
        args = dict(client_postgres=self.pool, client_password_hasher=HASHER, cache_postgres_schema=self.schema,
                    config_sql_read_limit_max=1000, config_sql_read_relation_fetch_limit_max=100, table="test", filter=[],
                    limit=100, page=1, order="id asc", column="*", relation=[], config_column_read_blocked=["password"])
        return await func_postgres_read(**(args | changes))

    async def titles(self, *filters, **changes):
        return [r["title"] for r in await self.read(filter=list(filters), **changes)]

    async def seed_tests(self):
        return await self.create("test", [
            {"title": "alpha", "status": 1, "rating": 4.5, "tags": ["api", "db"], "metadata": {"k": "v"}, "created_by_id": 1},
            {"title": "beta", "status": 2, "rating": 2.0, "tags": ["ui"], "metadata": {"k": "w"}, "created_by_id": 1},
            {"title": "gamma", "status": None, "rating": None, "tags": [], "metadata": {}, "created_by_id": 2},
        ])

    async def test_schema_init_is_idempotent_and_seeds_root_admin(self):
        self.assertEqual(await schema_init(self.url), "database init done")
        self.assertIn("attempt", self.schema["otp"])
        admin = await self.pool.fetchrow("SELECT role, password FROM users WHERE username = 'admin'")
        self.assertEqual(admin["role"], 1)
        self.assertTrue(HASHER.verify(admin["password"], "root-test-password"))

    async def test_filters_run_as_real_sql(self):
        await self.seed_tests()
        for filters, expected in [
            (["status = 1"], ["alpha"]), (["status in 1,2"], ["alpha", "beta"]), (["rating between 2 AND 4"], ["beta"]),
            (["title ilike %AL%"], ["alpha"]), (["status = null"], ["gamma"]), (["status != null"], ["alpha", "beta"]),
            ([{"tags": "overlap,api|ui"}], ["alpha", "beta"]), ([{"tags": "contains,api|db"}], ["alpha"]),
            ([{"metadata": "contains,k|v"}], ["alpha"]), ([{"metadata": "exists,k"}], ["alpha", "beta"]),
            (["title = alpha OR title = gamma"], ["alpha", "gamma"]), (["status >= 1", "title != alpha"], ["beta"]),
        ]:
            with self.subTest(filters=filters):
                self.assertEqual(await self.titles(*filters), expected)

    async def test_is_true_and_blocked_password_on_users(self):
        await self.create("users", [{"username": "u1", "role": 5, "is_protected": True, "password": "secret"},
                                    {"username": "u2", "role": 5, "is_protected": False, "password": "secret"},
                                    {"username": "u3", "role": 5, "is_protected": None, "password": "secret"}])
        read = lambda *f: self.read(table="users", filter=["username in u1,u2,u3", *f], order="username asc")
        self.assertEqual([r["username"] for r in await read("is_protected is true")], ["u1"])
        self.assertEqual([r["username"] for r in await read("is_protected is not true")], ["u2", "u3"])
        self.assertTrue(all("password" not in r for r in await read()))
        stored = await self.pool.fetchval("SELECT password FROM users WHERE username = 'u1'")
        self.assertTrue(HASHER.verify(stored, "secret"))

    async def test_sorting_and_pagination_fetch_one_extra_row(self):
        await self.seed_tests()
        self.assertEqual(await self.titles(order="title desc", limit=1, page=1), ["gamma", "beta"])
        self.assertEqual(await self.titles(order="title desc", limit=1, page=3), ["alpha"])

    async def test_update_and_delete_respect_ownership(self):
        alpha_id, beta_id, gamma_id = await self.seed_tests()
        update = lambda owner: func_postgres_update(client_postgres=self.pool, client_postgres_conn=None, client_password_hasher=HASHER,
                                                    cache_postgres_schema=self.schema, config_column_regex={}, table="test",
                                                    obj_list=[{"id": gamma_id, "title": "renamed"}], created_by_id=owner)
        self.assertEqual(await update(1), [])
        self.assertEqual(await update(2), [gamma_id])
        self.assertEqual(await self.titles(f"id = {gamma_id}"), ["renamed"])
        delete = lambda owner: func_postgres_delete(client_postgres=self.pool, client_postgres_conn=None, cache_postgres_schema=self.schema,
                                                    table="test", ids=[alpha_id], created_by_id=owner)
        self.assertEqual(await delete(2), 0)
        self.assertEqual(await delete(1), 1)
        self.assertEqual(await self.titles(), ["beta", "renamed"])

    async def test_relations_count_fetch_and_one_to_one(self):
        alpha_id, beta_id, _ = await self.seed_tests()
        await self.create("test_comment", [{"test_id": alpha_id, "description": f"c{i}", "created_by_id": 1} for i in range(3)])
        rows = await self.read(filter=[f"id in {alpha_id},{beta_id}"], relation=["id,test_comment,test_id,count,*", "id,test_comment,test_id,fetch|2,id,description"])
        self.assertEqual([(r["title"], r["test_comment_count"]) for r in rows], [("alpha", 3), ("beta", 0)])
        self.assertEqual([c["description"] for c in rows[0]["test_comment"]], ["c2", "c1"])
        self.assertEqual(rows[1]["test_comment"], [])
        comments = await self.read(table="test_comment", relation=["test_id,test,id,fetch|1,id,title"])
        self.assertEqual({c["test"]["title"] for c in comments}, {"alpha"})

    async def test_buffered_create_writes_only_on_flush(self):
        buffer = {}
        self.assertEqual(await self.create("test", [{"title": f"b{i}", "created_by_id": 1} for i in range(3)], mode="buffer", buffer=buffer), "buffered")
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM test"), 0)
        self.assertEqual(await self.create("test", None, mode="flush", buffer=buffer), "flushed")
        self.assertEqual(await self.titles(), ["b0", "b1", "b2"])

    async def verify_otp(self, code, email="a@example.test"):
        try:
            return await func_otp_verify(client_postgres=self.pool, otp=code, email=email, mobile=None, config_otp_expiry_sec=600, config_otp_max_attempt=5)
        except Exception as error:
            return getattr(error, "status_code", 400), str(error)

    async def test_cleanup_age_boundary_and_table_isolation(self):
        from datetime import datetime, timezone, timedelta
        from function.background import func_otp_cleanup, func_log_api_cleanup
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        async with self.pool.acquire() as conn:
            for created_at in (cutoff - timedelta(seconds=1), cutoff, cutoff + timedelta(seconds=1)):
                await conn.execute("INSERT INTO otp (otp, created_at) VALUES (123456, $1)", created_at)
                await conn.execute("INSERT INTO log_api (created_at) VALUES ($1)", created_at)
            self.assertEqual(await func_otp_cleanup(conn=conn, cutoff=cutoff, timeout_sec=5), 1)
            self.assertEqual(await conn.fetchval("SELECT count(*) FROM log_api"), 3)
            self.assertEqual(await func_log_api_cleanup(conn=conn, cutoff=cutoff, timeout_sec=5), 1)
            self.assertEqual(await conn.fetchval("SELECT count(*) FROM otp"), 2)
            self.assertEqual(await conn.fetchval("SELECT count(*) FROM log_api"), 2)

    async def test_otp_success_consumes_code_and_wrong_guesses_are_capped(self):
        code = await func_otp_generate(client_postgres=self.pool, email="a@example.test", mobile=None, config_otp_length=6)
        self.assertEqual(await self.verify_otp(code + 1 if code < 999999 else code - 1), (400, "invalid otp code"))
        self.assertEqual(await self.verify_otp(code), "done")
        self.assertEqual(await self.pool.fetchval("SELECT count(*) FROM otp"), 0)
        code = await func_otp_generate(client_postgres=self.pool, email="a@example.test", mobile=None, config_otp_length=6)
        wrong = code + 1 if code < 999999 else code - 1
        results = await asyncio.gather(*[self.verify_otp(wrong) for _ in range(20)])
        self.assertEqual(sum(r == (400, "invalid otp code") for r in results), 5)
        self.assertEqual(sum(r[0] == 429 for r in results), 15)
        self.assertEqual((await self.verify_otp(code))[0], 429)

    async def test_expired_otp_does_not_spend_attempts(self):
        await self.pool.execute("INSERT INTO otp (otp, email, created_at) VALUES (123456, 'old@example.test', now() - interval '1 hour')")
        self.assertEqual(await self.verify_otp(123456, "old@example.test"), (400, "otp code expired"))
        self.assertEqual(await self.pool.fetchval("SELECT attempt FROM otp"), 0)

    async def test_password_signup_and_login(self):
        user = await func_auth_signup_password(client_postgres=self.pool, client_password_hasher=HASHER, role=5, username="alice",
                                               password="correct", config_signup_allowed_roles=[5])
        login = lambda **c: func_auth_login_password(**(dict(client_postgres=self.pool, client_password_hasher=HASHER, field="username",
                                                             value="alice", password="correct", role=5) | c))
        self.assertEqual((await login())["id"], user["id"])
        for changes in ({"password": "wrong"}, {"value": "nobody"}, {"role": 6}):
            with self.subTest(changes=changes), self.assertRaisesRegex(Exception, "^invalid credentials$"):
                await login(**changes)


if __name__ == "__main__":
    unittest.main()
