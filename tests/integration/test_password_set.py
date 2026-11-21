"""Forgot password and invites end to end: a code sent to the email or mobile sets a new password; no code, a wrong one, role 1 or a blocked user is refused; existing routes are unchanged.

Same real-app boot as test_http.py (support.app_start), against a throwaway database; codes are written to the otp table as /public/otp-send-* would after sending.
"""
import unittest

from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


@requires_postgres
class PasswordSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.handle = app_start(env={"config_postgres_url_master": cls.url})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        for path in ("/public/password-set", "/auth/login-email-password", "/auth/login-mobile-password", "/admin/user-create", "/admin/user-update"): cls.app.state.config_api[path]["rate_limit"] = {"mode": "inmemory", "limit": 1000, "window_sec": 60}
        cls.admin = {"Authorization": "Bearer " + app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def invite(self, username, **columns):
        """An admin adds a person as today, with a password nobody is told, then sets their email or mobile."""
        response = self.client.post("/admin/user-create", json={"role": 2, "username": username, "password": "random-unknown-1"}, headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        user_id = response.json()["message"]["id"]
        for column, value in columns.items():
            update = self.client.put("/admin/user-update", json={"id": user_id, column: value}, headers=self.admin)
            self.assertEqual(update.status_code, 200, update.text)
        return user_id

    def code(self, email=None, mobile=None, otp=482913):
        fetch(self.url, "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3)", otp, email, mobile)

    def password_set(self, status=200, **body):
        response = self.client.post("/public/password-set", json=body)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def login_email(self, email, password):
        return self.client.post("/auth/login-email-password", json={"role": 2, "email": email, "password": password})

    def test_an_invited_user_sets_a_first_password_with_an_email_code(self):
        user_id = self.invite("asha", email="asha@mgh.test")
        self.code(email="asha@mgh.test")
        self.assertEqual(self.password_set(role=2, email="Asha@MGH.test", otp=482913, password="asha-own-pass"), "password set")
        self.assertEqual(self.login_email("asha@mgh.test", "asha-own-pass").status_code, 200)
        self.assertNotEqual(self.login_email("asha@mgh.test", "random-unknown-1").status_code, 200, "the invite password no longer works")
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM log_users_password WHERE user_id = $1", user_id)[0]["n"] >= 1, True)
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM otp WHERE email = 'asha@mgh.test'"), [{"n": 0}], "a code works once")

    def test_forgot_password_with_a_mobile_code(self):
        self.invite("ravi", mobile="+919800000001")
        self.code(mobile="+919800000001", otp=111222)
        self.password_set(role=2, mobile="+919800000001", otp=111222, password="ravi-new-pass")
        self.assertEqual(self.client.post("/auth/login-mobile-password", json={"role": 2, "mobile": "+919800000001", "password": "ravi-new-pass"}).status_code, 200)

    def test_without_the_right_code_nothing_tells_whether_an_account_exists(self):
        self.invite("neha", email="neha@mgh.test")
        for email in ("neha@mgh.test", "nobody@mgh.test"):
            with self.subTest(email=email): self.assertEqual(self.password_set(400, role=2, email=email, otp=1, password="whatever-1"), "otp not found")
        self.code(email="neha@mgh.test", otp=555666)
        self.assertEqual(self.password_set(400, role=2, email="neha@mgh.test", otp=555667, password="whatever-1"), "invalid otp code")
        self.code(email="nobody@mgh.test", otp=777888)
        self.assertIn("no account with this email", self.password_set(404, role=2, email="nobody@mgh.test", otp=777888, password="whatever-1"), "only the owner of the email, holding its code, learns there is no account")

    def test_refusals(self):
        self.assertIn("role 1", self.password_set(403, role=1, email="admin@mgh.test", otp=1, password="whatever-1"))
        self.assertIn("one of email or mobile", self.password_set(400, role=2, email="a@mgh.test", mobile="+919800000009", otp=1, password="whatever-1"))
        self.assertIn("Password must be", self.password_set(400, role=2, email="a@mgh.test", otp=1, password="short"))
        self.assertEqual(self.client.post("/public/password-set", json={"role": 2, "email": "a@mgh.test", "otp": 1, "password": "whatever-1", "id": 5}).status_code, 400, "unknown fields are refused")
        blocked = self.invite("gone", email="gone@mgh.test")
        self.client.put("/admin/user-update", json={"id": blocked, "deactivated_at": "2026-01-01T00:00:00Z"}, headers=self.admin)
        self.code(email="gone@mgh.test", otp=999000)
        self.assertEqual(self.password_set(403, role=2, email="gone@mgh.test", otp=999000, password="whatever-1"), "account deactivated")

    def test_user_create_still_needs_a_password(self):
        response = self.client.post("/admin/user-create", json={"role": 2, "username": "nopass"}, headers=self.admin)
        self.assertEqual(response.status_code, 400, response.text)


if __name__ == "__main__":
    unittest.main()
