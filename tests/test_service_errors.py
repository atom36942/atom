"""Configuration failures precede service calls; failed deliveries never look successful."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from function import (
    func_auth_login_password, func_auth_signup_password, func_user_read_single,
    func_postgres_query_generator_ai, func_otp_send_email, func_otp_send_mobile,
)
from tests.support import database
from tests.test_errors import status_of


class ServiceErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_hasher_is_configuration_error_before_database_access(self):
        pool, conn = database()
        for operation, args in [
            (func_auth_login_password, dict(field="username", value="alice", password="x", role=2)),
            (func_auth_signup_password, dict(username="alice", password="x", role=2, config_signup_allowed_roles=[2])),
        ]:
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(Exception, "password hasher not initialized") as caught:
                    await operation(client_postgres=pool, client_password_hasher=None, **args)
                self.assertEqual(caught.exception.status_code, 500)
                conn.fetch.assert_not_awaited()
                pool.acquire.assert_not_called()

    async def test_missing_database_precedes_ai_client_and_profile_read(self):
        for operation, args in [
            (func_user_read_single, dict(user_id=7)),
            (func_postgres_query_generator_ai, dict(client_gemini=None, client_openai=None,
                cache_postgres_schema={}, config_query_runner_read_limit=10, ai="openai", question="x")),
        ]:
            with self.subTest(operation=operation.__name__):
                with self.assertRaisesRegex(Exception, "postgres client not initialized") as caught:
                    await operation(client_postgres=None, **args)
                self.assertEqual(caught.exception.status_code, 500)

    async def test_missing_delivery_keys_prevent_network_calls(self):
        for operation, args, state, message in [
            (func_otp_send_email, dict(service="resend", sender="a", email="b", otp=123456),
             SimpleNamespace(config_resend_key=None), "resend API key not configured"),
            (func_otp_send_mobile, dict(service="fast2sms", mobile="123", otp=123456),
             SimpleNamespace(config_fast2sms_key=None), "fast2sms API key not configured"),
        ]:
            with self.subTest(service=args["service"]), patch("function.messaging.httpx.AsyncClient") as client:
                with self.assertRaisesRegex(Exception, message) as caught:
                    await operation(app_state=state, **args)
                self.assertEqual(caught.exception.status_code, 500)
                client.assert_not_called()

    async def test_delivery_failures_are_502_without_provider_body(self):
        cases = [
            (func_otp_send_email, dict(service="resend", sender="a", email="b", otp=123456),
             SimpleNamespace(config_resend_key="key", config_resend_url="https://service.test"),
             "post", httpx.Response(401, text="private provider details")),
            (func_otp_send_mobile, dict(service="fast2sms", mobile="123", otp=123456),
             SimpleNamespace(config_fast2sms_key="key", config_fast2sms_url="https://service.test"),
             "get", httpx.Response(503, text="private provider details")),
            (func_otp_send_mobile, dict(service="fast2sms", mobile="123", otp=123456),
             SimpleNamespace(config_fast2sms_key="key", config_fast2sms_url="https://service.test"),
             "get", httpx.Response(200, json={"return": False})),
        ]
        for operation, args, state, method, response in cases:
            with self.subTest(service=args["service"], status=response.status_code):
                with patch("function.messaging.httpx.AsyncClient") as factory:
                    client = factory.return_value.__aenter__.return_value
                    setattr(client, method, AsyncMock(return_value=response))
                    with self.assertRaises(Exception) as caught:
                        await operation(app_state=state, **args)
                    status, body = await status_of(caught.exception)
                    self.assertEqual(status, 502)
                    self.assertNotIn("private provider details", body["message"])

    async def test_programming_errors_are_generic_500(self):
        for error in (AttributeError("private state"), KeyError("private field"), TypeError("private type")):
            with self.subTest(error=type(error).__name__):
                self.assertEqual(await status_of(error), (500, {"status": 0, "message": "internal server error"}))
