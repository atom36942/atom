"""Authentication contracts using real password hashing and JWT validation."""
import asyncio
import statistics
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from argon2 import PasswordHasher
import jwt

from function import (
    func_user_last_active_update, func_background_run,
    func_auth_check_config, func_auth_login_password,
    func_auth_signup_password, func_auth_user_find_or_create,
    func_otp_verify, func_token_encode, func_token_decode,
    func_middleware_check_token,
)
from tests.support import database
from router.auth import router


class AuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_last_active_update_writes_to_the_given_pool(self):
        pool = SimpleNamespace(execute=AsyncMock())
        await func_user_last_active_update(client_postgres=pool, user_id=7)
        pool.execute.assert_awaited_once_with("UPDATE users SET last_active_at=NOW() WHERE id=$1", 7)
        with self.assertRaisesRegex(Exception, "postgres client not initialized"):
            await func_user_last_active_update(client_postgres=None, user_id=7)

    async def test_background_run_is_tracked_and_counts_failures(self):
        app_state = SimpleNamespace(runtime_background_tasks=set(), runtime_error_count={"background_task": 0})
        done = asyncio.Event()
        async def work(): done.set()
        async def fail(): raise RuntimeError("db down")
        func_background_run(app_state=app_state, coroutine=work())
        func_background_run(app_state=app_state, coroutine=fail())
        self.assertEqual(len(app_state.runtime_background_tasks), 2)
        await asyncio.wait_for(done.wait(), 1)
        for _ in range(5): await asyncio.sleep(0)
        self.assertEqual((app_state.runtime_background_tasks, app_state.runtime_error_count["background_task"]), (set(), 1))

    def setUp(self):
        self.pool, self.conn = database()
        self.hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
        self.user = {"id": 7, "role": 5, "username": "alice", "password": self.hasher.hash("correct")}
        self.conn.fetch.return_value = [self.user]
        self.secret = "atom-test-secret-that-is-at-least-32-bytes-long"

    async def login(self, **changes):
        args = dict(client_postgres=self.pool, client_password_hasher=self.hasher,
                    field="username", value="alice", password="correct", role=5)
        return await func_auth_login_password(**(args | changes))

    async def tokens(self, **changes):
        args = dict(user=self.user, config_token_secret_key=self.secret,
                    config_access_token_expires_sec=60, config_refresh_token_expires_sec=120,
                    config_column_token_encode=["id", "role"])
        return await func_token_encode(**(args | changes))

    async def decode(self, token, **changes):
        return await func_token_decode(**(dict(headers={"Authorization": "Bearer " + token},
                                              config_token_secret_key=self.secret) | changes))

    async def test_password_login_verifies_real_hash(self):
        self.assertEqual(await self.login(), self.user)
        self.assertEqual(self.conn.fetch.await_args.args[1:], (5, "alice"))
        with self.assertRaisesRegex(Exception, "invalid credentials"):
            await self.login(password="wrong")

    async def test_unknown_user_and_missing_hash_fail_like_a_wrong_password(self):
        for rows in ([], [{**self.user, "password": None}]):
            with self.subTest(rows=len(rows)):
                self.conn.fetch.return_value = rows
                with self.assertRaisesRegex(Exception, "^invalid credentials$"):
                    await self.login()

    async def test_login_rejects_missing_ambiguous_and_invalid_identifiers(self):
        for rows, changes, message in [([self.user, self.user], {"role": None}, "role is mandatory"),
                                     ([self.user], {"field": "username; DROP TABLE users"}, "invalid auth field")]:
            with self.subTest(message=message):
                self.conn.fetch.reset_mock()
                self.conn.fetch.return_value = rows
                with self.assertRaisesRegex(Exception, message):
                    await self.login(**changes)
                if "field" in changes:
                    self.conn.fetch.assert_not_awaited()

    async def test_signup_hashes_password_before_insert(self):
        result = await func_auth_signup_password(
            client_postgres=self.pool, client_password_hasher=self.hasher,
            role=5, username="alice", password="new-password", config_signup_allowed_roles=[5])
        self.assertEqual(result["id"], 7)
        sql, role, username, hashed, source = self.conn.fetch.await_args.args
        self.assertTrue(self.hasher.verify(hashed, "new-password"))
        self.assertNotIn("new-password", sql)
        self.assertEqual((role, username, source), (5, "alice", None))

    async def test_signup_denials_never_insert(self):
        for role, allowed in [(5, []), (1, [1, 5]), (9, [5])]:
            with self.subTest(role=role, allowed=allowed):
                with self.assertRaisesRegex(Exception, "signup"):
                    await func_auth_signup_password(
                        client_postgres=self.pool, client_password_hasher=self.hasher,
                        role=role, username="alice", password="secret", config_signup_allowed_roles=allowed)
        self.conn.fetch.assert_not_awaited()

    async def test_existing_social_user_can_login_when_signup_disabled(self):
        args = dict(client_postgres=self.pool,
                    field="email", value="a@example.test", role=5, config_signup_allowed_roles=[])
        self.assertEqual(await func_auth_user_find_or_create(**args), self.user)
        self.conn.fetch.return_value = []
        with self.assertRaisesRegex(Exception, "signup disabled"):
            await func_auth_user_find_or_create(**args)
        self.assertEqual(self.conn.fetch.await_count, 2)  # Both calls only looked up a user.

    async def test_tokens_round_trip_without_password_and_enforce_token_type(self):
        tokens = await self.tokens()
        for token_type, path in [("access", "/my/profile"), ("refresh", "/my/token-refresh")]:
            user = await self.decode(tokens[token_type + "_token"])
            self.assertEqual(user, {"id": 7, "role": 5, "_token_type": token_type})
            await func_middleware_check_token(user_dict=user, url_path=path, is_token=True)
            wrong_path = "/my/profile" if token_type == "refresh" else "/my/token-refresh"
            with self.assertRaisesRegex(Exception, "token required"):
                await func_middleware_check_token(user_dict=user, url_path=wrong_path, is_token=True)

    async def test_expired_and_wrongly_signed_tokens_are_rejected(self):
        expired = await self.tokens(config_access_token_expires_sec=-60)
        with self.assertRaises(jwt.ExpiredSignatureError):
            await self.decode(expired["access_token"])
        tokens = await self.tokens()
        with self.assertRaises(jwt.InvalidSignatureError):
            await self.decode(tokens["access_token"], config_token_secret_key="a-different-test-secret-at-least-32-bytes")

    async def test_missing_auth_is_public_only(self):
        self.assertEqual(await func_token_decode(headers={}, config_token_secret_key=self.secret), {})
        await func_middleware_check_token(user_dict={}, url_path="/public/example")
        for policy in ({"is_token": True}, {"user_check_role": [5]}, {"user_check_deleted": ["token"]}):
            with self.subTest(policy=policy), self.assertRaisesRegex(Exception, "authorization token missing"):
                await func_middleware_check_token(user_dict={}, url_path="/my/profile", **policy)

    async def test_missing_secret_stops_auth_routes_before_side_effects(self):
        for route in router.routes:
            if route.path == "/auth/login-password":
                continue
            for secret in (None, ""):
                with self.subTest(path=route.path, secret=secret):
                    state = SimpleNamespace(
                        config_token_secret_key=secret,
                        func_auth_check_config=func_auth_check_config,
                        func_request_param_read=AsyncMock(),
                        func_auth_signup_password=AsyncMock(),
                        func_auth_user_find_or_create=AsyncMock(),
                        func_auth_login_password=AsyncMock(),
                        func_otp_verify=AsyncMock(),
                        func_token_encode=AsyncMock())
                    request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(client_postgres=self.pool))
                    with self.assertRaisesRegex(Exception, "token secret key missing") as caught:
                        await route.endpoint(request=request)
                    self.assertEqual(caught.exception.status_code, 500)
                    for value in vars(state).values():
                        if isinstance(value, AsyncMock):
                            value.assert_not_awaited()

    async def test_missing_postgres_is_reported_before_missing_token_secret(self):
        for route in router.routes:
            if route.path == "/auth/login-password":
                continue
            for secret in (None, "", self.secret):
                with self.subTest(path=route.path, secret=secret):
                    read = AsyncMock()
                    request = SimpleNamespace(
                        app=SimpleNamespace(state=SimpleNamespace(
                            config_token_secret_key=secret, func_auth_check_config=func_auth_check_config, func_request_param_read=read)),
                        state=SimpleNamespace(client_postgres=None))
                    with self.assertRaisesRegex(Exception, "postgres client not initialized") as caught:
                        await route.endpoint(request=request)
                    self.assertEqual(caught.exception.status_code, 500)
                    read.assert_not_awaited()

    async def test_missing_secret_fails_token_creation(self):
        with self.assertRaisesRegex(Exception, "token secret key missing"):
            await self.tokens(config_token_secret_key="")

    async def test_otp_success_normalizes_identifier_and_consumes_code(self):
        self.conn.fetch.return_value = [{"id": 8, "otp": 123456, "is_valid": True}]
        result = await func_otp_verify(client_postgres=self.pool, otp=123456,
                                      email=" A@Example.Test ", mobile=None, config_otp_expiry_sec=300)
        self.assertEqual(result, "done")
        self.assertEqual(self.conn.fetch.await_args.args[1:], ("a@example.test", 300.0))
        self.conn.execute.assert_awaited_once_with("DELETE FROM otp WHERE id = $1;", 8)

    async def test_missing_wrong_and_expired_otps_are_not_consumed(self):
        for rows, message in [([], "not found"),
                              ([{"id": 8, "otp": 654321, "is_valid": True}], "invalid otp"),
                              ([{"id": 8, "otp": 123456, "is_valid": False}], "expired")]:
            with self.subTest(message=message):
                self.conn.fetch.return_value = rows
                with self.assertRaisesRegex(Exception, message):
                    await func_otp_verify(client_postgres=self.pool, otp=123456,
                                          email="a@example.test", mobile=None, config_otp_expiry_sec=300)
        self.conn.execute.assert_not_awaited()

    async def test_each_guess_is_counted_against_the_attempt_cap_before_comparing(self):
        self.conn.fetch.return_value = [{"id": 8, "otp": 654321, "is_valid": True}]
        with self.assertRaisesRegex(Exception, "invalid otp"):
            await func_otp_verify(client_postgres=self.pool, otp=123456, email="a@example.test", mobile=None,
                                  config_otp_expiry_sec=300, config_otp_max_attempt=3)
        sql, otp_id, cap = self.conn.fetchval.await_args.args
        self.assertIn("SET attempt = attempt + 1 WHERE id = $1 AND attempt < $2", sql)
        self.assertEqual((otp_id, cap), (8, 3))

    async def test_exhausted_code_is_rejected_with_429_even_when_correct(self):
        self.conn.fetch.return_value = [{"id": 8, "otp": 123456, "is_valid": True}]
        self.conn.fetchval.return_value = None
        with self.assertRaisesRegex(Exception, "attempts exceeded") as caught:
            await func_otp_verify(client_postgres=self.pool, otp=123456, email="a@example.test", mobile=None, config_otp_expiry_sec=300)
        self.assertEqual(caught.exception.status_code, 429)
        self.conn.execute.assert_not_awaited()

    async def test_expired_code_does_not_spend_an_attempt(self):
        self.conn.fetch.return_value = [{"id": 8, "otp": 123456, "is_valid": False}]
        with self.assertRaisesRegex(Exception, "expired"):
            await func_otp_verify(client_postgres=self.pool, otp=123456, email="a@example.test", mobile=None, config_otp_expiry_sec=300)
        self.conn.fetchval.assert_not_awaited()

    async def test_password_verify_does_not_block_the_event_loop(self):
        hasher = PasswordHasher()    # production cost, about 30 ms per verify
        password_hash = hasher.hash("correct")
        started = time.perf_counter()
        hasher.verify(password_hash, "correct")
        one_verify = time.perf_counter() - started
        self.conn.fetch.return_value = [self.user | {"password": password_hash}]
        gaps, done = [], asyncio.Event()
        async def ticker():
            last = time.perf_counter()
            while not done.is_set():
                await asyncio.sleep(0.001)
                now = time.perf_counter()
                gaps.append(now - last)
                last = now
        task = asyncio.create_task(ticker())
        await asyncio.gather(*(func_auth_login_password(client_postgres=self.pool, client_password_hasher=hasher, field="username", value="alice", password="correct", role=5) for _ in range(5)))
        done.set()
        await task
        self.assertLess(statistics.median(gaps), one_verify / 4)    # blocking verifies make every gap a whole verify long
