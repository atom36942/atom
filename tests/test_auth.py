"""Authentication contracts using real password hashing and JWT validation."""
import unittest

from argon2 import PasswordHasher
import jwt

from function import (
    func_auth_check_signup_role, func_auth_login_password,
    func_auth_signup_password, func_auth_user_find_or_create,
    func_otp_verify, func_token_encode, func_token_decode,
    func_middleware_check_token,
)
from tests.support import database


class AuthTests(unittest.IsolatedAsyncioTestCase):
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
        with self.assertRaisesRegex(Exception, "incorrect password"):
            await self.login(password="wrong")

    async def test_login_rejects_missing_ambiguous_and_invalid_identifiers(self):
        for rows, changes, message in [([], {}, "not found"),
                                     ([self.user, self.user], {"role": None}, "role is mandatory"),
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
            func_auth_check_signup_role=func_auth_check_signup_role,
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
                        func_auth_check_signup_role=func_auth_check_signup_role,
                        role=role, username="alice", password="secret", config_signup_allowed_roles=allowed)
        self.conn.fetch.assert_not_awaited()

    async def test_existing_social_user_can_login_when_signup_disabled(self):
        args = dict(client_postgres=self.pool, func_auth_check_signup_role=func_auth_check_signup_role,
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

    async def test_missing_secret_fails_token_creation(self):
        with self.assertRaisesRegex(Exception, "token secret key missing"):
            await self.tokens(config_token_secret_key="")

    async def test_otp_success_normalizes_identifier_and_consumes_code(self):
        self.conn.fetch.return_value = [{"id": 8, "otp": 123456, "is_valid": True}]
        result = await func_otp_verify(client_postgres=self.pool, otp=123456,
                                      email=" A@Example.Test ", mobile=None, config_otp_expiry_sec=300)
        self.assertEqual(result, "done")
        self.assertEqual(self.conn.fetch.await_args.args[1:], ("a@example.test",))
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
