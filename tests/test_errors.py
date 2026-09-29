"""HTTP status codes from func_api_error, middleware checks, and known infrastructure failures."""
import asyncio
import unittest
import asyncpg
import httpx
import jwt
import orjson
import redis.exceptions

from function import (
    func_api_error, func_middleware_api_response_error, func_middleware_check_active, func_middleware_check_ratelimiter,
    func_middleware_check_role, func_middleware_check_token, func_middleware_check_user_deactivated,
    func_auth_check_signup_role, func_token_decode,
)


async def status_of(error):
    message, response = await func_middleware_api_response_error(exception=error, is_traceback=False, sentry_dsn=None)
    return response.status_code, orjson.loads(response.body)


class ErrorStatusTests(unittest.IsolatedAsyncioTestCase):
    async def raised(self, coro):
        try:
            await coro
        except Exception as error:
            return await status_of(error)
        self.fail("expected an exception")

    async def test_plain_exceptions_stay_400_with_the_same_envelope(self):
        self.assertEqual(await status_of(Exception("invalid limit")), (400, {"status": 0, "message": "invalid limit"}))

    async def test_func_api_error_sets_status_and_keeps_message(self):
        error = func_api_error(message="access denied", status_code=403)
        self.assertIsInstance(error, Exception)
        self.assertEqual(await status_of(error), (403, {"status": 0, "message": "access denied"}))

    async def test_middleware_checks_return_their_http_status(self):
        role = dict(client_postgres=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)
        user_state = dict(client_postgres=None, client_redis=None, cache_users_deactivated={}, config_redis_cache_ttl_sec=60)
        limiter = {"cache_ratelimiter": {}, "client_redis": None, "url_path": "/x", "identifier": "7"}
        for label, coro, expected in [
            ("disabled endpoint", lambda: func_middleware_check_active(is_active=False), 404),
            ("missing token", lambda: func_middleware_check_token(user_dict={}, url_path="/my/x", is_token=True), 401),
            ("refresh token on access route", lambda: func_middleware_check_token(user_dict={"_token_type": "refresh"}, url_path="/my/x", is_token=True), 401),
            ("wrong role", lambda: func_middleware_check_role(user_dict={"id": 7, "role": 9}, user_check_role={"mode": "token", "roles": [1]}, **role), 403),
            ("role claim not in token", lambda: func_middleware_check_role(user_dict={"id": 7}, user_check_role={"mode": "token", "roles": [1]}, **role), 500),
            ("deactivated user", lambda: func_middleware_check_user_deactivated(user_dict={"id": 7, "deactivated_at": "2026-01-01"}, user_check_deactivated={"mode": "token"}, **user_state), 403),
            ("redis limiter without redis", lambda: func_middleware_check_ratelimiter(rate_limit={"mode": "redis", "limit": 1, "window_sec": 60}, **limiter), 500),
        ]:
            with self.subTest(label):
                self.assertEqual((await self.raised(coro()))[0], expected)

    async def test_rate_limit_returns_429_after_the_limit(self):
        args = dict(client_redis=None, rate_limit={"mode": "inmemory", "limit": 1, "window_sec": 60}, url_path="/x", identifier="7", cache_ratelimiter={})
        await func_middleware_check_ratelimiter(**args)
        self.assertEqual((await self.raised(func_middleware_check_ratelimiter(**args)))[0], 429)

    async def test_signup_policy_denials_are_403(self):
        for allowed in ([], [5]):
            with self.subTest(allowed=allowed):
                try:
                    func_auth_check_signup_role(role=1, config_signup_allowed_roles=allowed)
                except Exception as error:
                    self.assertEqual((await status_of(error))[0], 403)
                else:
                    self.fail("expected an exception")

    async def test_bad_or_expired_tokens_are_401(self):
        expired = jwt.encode({"exp": 1, "data": "{}", "type": "access"}, "k" * 32)
        for token in ("not-a-jwt", expired):
            with self.subTest(token=token[:12]):
                status, body = await self.raised(func_token_decode(headers={"Authorization": f"Bearer {token}"}, config_token_secret_key="k" * 32))
                self.assertEqual((status, body["message"]), (401, "authentication token invalid"))

    async def test_infrastructure_failures_are_server_side_statuses(self):
        request = httpx.Request("GET", "https://service.test")
        for error, expected in [
            (asyncpg.exceptions.DeadlockDetectedError("deadlock"), 409), (asyncpg.exceptions.SerializationError("conflict"), 409),
            (asyncpg.exceptions.ConnectionDoesNotExistError("closed"), 503), (asyncpg.exceptions.TooManyConnectionsError("full"), 503),
            (asyncpg.exceptions.InterfaceError("pool closed"), 503), (ConnectionRefusedError("refused"), 503), (asyncio.TimeoutError(), 503),
            (redis.exceptions.ConnectionError("down"), 503), (redis.exceptions.ResponseError("bad command"), 500),
            (httpx.ConnectError("down", request=request), 502),
            (httpx.HTTPStatusError("bad", request=request, response=httpx.Response(503, request=request)), 502),
            (asyncpg.exceptions.UniqueViolationError("duplicate"), 400), (asyncpg.PostgresError("syntax"), 400),
        ]:
            with self.subTest(error=type(error).__name__):
                self.assertEqual((await status_of(error))[0], expected)


if __name__ == "__main__":
    unittest.main()
