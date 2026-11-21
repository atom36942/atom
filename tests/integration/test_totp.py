"""2FA end to end: off by default, setup, enable, login in two steps, one use per code, recovery codes, admin reset, disable.

Same real-app boot as test_http.py (support.app_start), against a throwaway database.
"""
import base64
import time
import unittest

from function import func_totp_code
from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


@requires_postgres
class TotpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.handle = app_start(env={"config_postgres_url_master": cls.url, "config_totp_encryption_key": "totp-test-encryption-key-of-32-chars-or-more"})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        for path in ("/auth/login-username-password", "/auth/login-totp", "/my/totp-setup", "/my/totp-enable", "/my/totp-disable"): cls.app.state.config_api[path]["rate_limit"] = {"mode": "inmemory", "limit": 1000, "window_sec": 60}
        cls.admin = {"Authorization": "Bearer " + app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def message(self, response, status=200):
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def login(self, username):
        return self.message(self.client.post("/auth/login-username-password", json={"username": username, "password": "pass-1234", "role": 5}))

    def user(self, username):
        app_login(self.client, path="/auth/signup-username-password", body={"role": 5, "username": username, "password": "pass-1234"})
        tokens = self.login(username)
        return {"Authorization": "Bearer " + tokens["access_token"]}, self.message(self.client.get("/my/profile", headers={"Authorization": "Bearer " + tokens["access_token"]}))["id"]

    @staticmethod
    def code(secret, offset=0, step=None):
        raw = base64.b32decode(secret + "=" * (-len(secret) % 8))
        return func_totp_code(secret=raw, step=(step if step is not None else int(time.time() // 30)) + offset)

    def enable(self, headers):
        setup = self.message(self.client.post("/my/totp-setup", headers=headers))
        recovery = self.message(self.client.post("/my/totp-enable", json={"code": self.code(setup["secret"])}, headers=headers))["recovery_codes"]
        return setup, recovery

    def test_info_tells_pages_2fa_is_available(self):
        self.assertIs(self.message(self.client.get("/info"))["is_totp_enabled"], True)

    def test_off_by_default_login_is_unchanged(self):
        self.user("plain")
        tokens = self.login("plain")
        self.assertIn("access_token", tokens)
        self.assertNotIn("mfa_required", tokens)

    def test_setup_enable_and_two_step_login(self):
        headers, user_id = self.user("ravi")
        setup = self.message(self.client.post("/my/totp-setup", headers=headers))
        self.assertTrue(setup["uri"].startswith("otpauth://totp/"))
        self.assertIn("access_token", self.login("ravi"), "set up but not enabled: login still one step")
        self.assertEqual(self.message(self.client.post("/my/totp-enable", json={"code": "000000"}, headers=headers), 400), "code invalid")
        recovery = self.message(self.client.post("/my/totp-enable", json={"code": self.code(setup["secret"])}, headers=headers))["recovery_codes"]
        self.assertEqual(len(recovery), 10)
        [row] = fetch(self.url, "SELECT totp_secret, totp_enabled_at, cardinality(totp_recovery) AS n FROM users WHERE id = $1", user_id)
        self.assertNotIn(setup["secret"], row["totp_secret"], "stored encrypted")
        self.assertEqual(row["n"], 10)
        profile = self.message(self.client.get("/my/profile", headers=headers))
        self.assertNotIn("totp_secret", profile)
        self.assertNotIn("totp_recovery", profile)
        self.assertIsNotNone(profile["totp_enabled_at"], "a page reads the user's 2FA state from /my/profile")

        first = self.login("ravi")
        self.assertEqual(set(first), {"mfa_required", "mfa_token"})
        self.assertEqual(self.client.get("/my/profile", headers={"Authorization": "Bearer " + first["mfa_token"]}).status_code, 401, "an mfa token opens no route")
        self.assertEqual(self.message(self.client.post("/auth/login-totp", json={"mfa_token": first["mfa_token"], "code": "000000"}), 401), "code invalid")
        spent = fetch(self.url, "SELECT totp_last_step FROM users WHERE id = $1", user_id)[0]["totp_last_step"]    # steps from the database, not the clock, so a 30-second boundary mid-test changes nothing
        self.assertEqual(self.message(self.client.post("/auth/login-totp", json={"mfa_token": first["mfa_token"], "code": self.code(setup["secret"], step=spent)}), 401), "code invalid", "enable already spent this step's code")
        tokens = self.message(self.client.post("/auth/login-totp", json={"mfa_token": first["mfa_token"], "code": self.code(setup["secret"], 1, step=spent)}))
        self.assertEqual(self.message(self.client.get("/my/profile", headers={"Authorization": "Bearer " + tokens["access_token"]}))["id"], user_id)
        self.assertEqual(self.client.post("/auth/login-totp", json={"mfa_token": first["mfa_token"], "code": self.code(setup["secret"], 1, step=spent)}).status_code, 401, "a code works once")
        self.assertEqual(self.message(self.client.post("/auth/login-totp", json={"mfa_token": tokens["access_token"], "code": recovery[0]}), 401), "mfa token invalid or expired")

        self.message(self.client.post("/auth/login-totp", json={"mfa_token": self.login("ravi")["mfa_token"], "code": recovery[0].lower()}))
        self.assertEqual(self.client.post("/auth/login-totp", json={"mfa_token": self.login("ravi")["mfa_token"], "code": recovery[0]}).status_code, 401, "a recovery code works once")
        self.assertEqual(fetch(self.url, "SELECT cardinality(totp_recovery) AS n FROM users WHERE id = $1", user_id), [{"n": 9}])
        self.assertIn("already on", self.message(self.client.post("/my/totp-setup", headers=headers), 400))

    def test_disable_needs_a_code_and_clears_everything(self):
        headers, user_id = self.user("asha")
        _, recovery = self.enable(headers)
        self.assertEqual(self.client.post("/my/totp-disable", json={"code": "000000"}, headers=headers).status_code, 401)
        self.assertEqual(self.message(self.client.post("/my/totp-disable", json={"code": recovery[3]}, headers=headers)), "2FA off")
        self.assertEqual(fetch(self.url, "SELECT totp_secret, totp_enabled_at, totp_last_step, totp_recovery FROM users WHERE id = $1", user_id), [dict.fromkeys(("totp_secret", "totp_enabled_at", "totp_last_step", "totp_recovery"))])
        self.assertIn("access_token", self.login("asha"))

    def test_only_an_admin_turns_it_off_for_a_user(self):
        headers, user_id = self.user("lost-phone")
        self.enable(headers)
        self.assertIn("only by an admin", self.message(self.client.put("/my/user-update", json={"totp_enabled_at": None}, headers=headers), 400))
        self.assertIn("can only be cleared", self.message(self.client.put("/admin/user-update", json={"id": user_id, "totp_enabled_at": "2026-01-01T00:00:00Z"}, headers=self.admin), 400))
        self.message(self.client.put("/admin/user-update", json={"id": user_id, "totp_enabled_at": None}, headers=self.admin))
        self.assertEqual(fetch(self.url, "SELECT totp_secret, totp_recovery FROM users WHERE id = $1", user_id), [{"totp_secret": None, "totp_recovery": None}], "the trigger clears the rest")
        self.assertIn("access_token", self.login("lost-phone"))

    def test_without_the_key_2fa_is_not_configured(self):
        headers, _ = self.user("nokey")
        key, self.app.state.config_totp_encryption_key = self.app.state.config_totp_encryption_key, None
        try: self.assertIn("2FA not configured", self.message(self.client.post("/my/totp-setup", headers=headers), 400))
        finally: self.app.state.config_totp_encryption_key = key


if __name__ == "__main__":
    unittest.main()
