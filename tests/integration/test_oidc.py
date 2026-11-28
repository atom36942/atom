"""OIDC login end to end: /info lists the providers, /auth/login-oidc creates, finds and links users per provider, refuses an untrusted email that is taken, and 2FA still applies.

Same real-app boot as test_http.py (support.app_start), against a throwaway database; the provider's keys come from httpx.MockTransport, so nothing leaves the machine.
"""
import json
import time
import unittest

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
JWKS = {"keys": [{**jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True), "kid": "k1", "alg": "RS256", "use": "sig"}]}
PROVIDERS = {
    "google": {"issuer": ["https://accounts.google.com", "accounts.google.com"], "client_id": "google-app", "jwks_uri": "https://idp.test/google"},
    "microsoft": {"issuer": "https://login.microsoftonline.com/{tenantid}/v2.0", "client_id": "ms-app", "jwks_uri": "https://idp.test/microsoft", "tenants": ["tenant1"], "link_email": True},
}


def id_token(provider, sub, **claims):
    now = int(time.time())
    issuer = "https://accounts.google.com" if provider == "google" else "https://login.microsoftonline.com/tenant1/v2.0"
    body = {"iss": issuer, "aud": PROVIDERS[provider]["client_id"], "sub": sub, "iat": now, "exp": now + 300, **({"tid": "tenant1"} if provider == "microsoft" else {}), **claims}
    return jwt.encode(body, KEY, algorithm="RS256", headers={"kid": "k1"})


@requires_postgres
class OidcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        fetch(cls.url, "CREATE TABLE users (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, role smallint NOT NULL, google_login_id text, google_login_metadata jsonb)")    # a database from before 19.0.0
        fetch(cls.url, "INSERT INTO users (id, role, google_login_id) OVERRIDING SYSTEM VALUE VALUES (500, 5, 'g-old')")
        cls.handle = app_start(env={"config_postgres_url_master": cls.url, "config_oidc_provider": json.dumps(PROVIDERS), "config_signup_allowed_roles": "[5]", "config_totp_encryption_key": "totp-test-encryption-key-of-32-chars-or-more"})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        cls.app.state.client_http = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=JWKS)))
        for path in ("/auth/login-oidc", "/auth/login-email-password"): cls.app.state.config_api[path]["rate_limit"] = {"mode": "inmemory", "limit": 1000, "window_sec": 60}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def login(self, provider, token, status=200, role=5):
        response = self.client.post("/auth/login-oidc", json={"provider": provider, "id_token": token, "role": role})
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def user_id(self, tokens):
        return self.client.get("/my/profile", headers={"Authorization": "Bearer " + tokens["access_token"]}).json()["message"]["id"]

    def test_info_lists_providers_for_pages(self):
        info = self.client.get("/info").json()["message"]["oidc_provider"]
        self.assertEqual(info["microsoft"], {"issuer": PROVIDERS["microsoft"]["issuer"], "client_id": "ms-app"})
        self.assertNotIn("tenants", info["microsoft"])

    def test_a_column_per_provider_and_the_old_google_column_renamed(self):
        columns = {r["column_name"] for r in fetch(self.url, "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")}
        self.assertTrue({"oidc_google", "oidc_microsoft"} <= columns)
        self.assertNotIn("google_login_id", columns)

    def test_a_google_user_from_before_keeps_their_account(self):
        self.assertEqual(self.user_id(self.login("google", id_token("google", "g-old"))), 500)

    def test_one_person_many_providers_one_user(self):
        first = self.user_id(self.login("google", id_token("google", "g-ravi", email="Ravi@Example.test", email_verified=True, name="Ravi")))
        self.assertEqual(fetch(self.url, "SELECT email, name, oidc_google FROM users WHERE id = $1", first), [{"email": "ravi@example.test", "name": "Ravi", "oidc_google": "g-ravi"}])
        self.assertEqual(self.user_id(self.login("google", id_token("google", "g-ravi", email="new@example.test"))), first, "found by sub, whatever the email says now")
        self.assertEqual(self.user_id(self.login("microsoft", id_token("microsoft", "m-ravi", email="ravi@example.test"))), first, "link_email: Microsoft links by email")
        self.assertEqual(fetch(self.url, "SELECT oidc_microsoft FROM users WHERE id = $1", first), [{"oidc_microsoft": "m-ravi"}])
        self.assertIn("signup not allowed for role 6", self.login("google", id_token("google", "g-ravi"), status=403, role=6), "each role is its own user")

    def test_untrusted_email_that_is_taken_is_refused(self):
        self.login("google", id_token("google", "g-asha", email="asha@example.test", email_verified=True))
        self.assertIn("email already used", self.login("google", id_token("google", "g-other", email="asha@example.test", email_verified=False), status=409))
        self.assertIn("already linked to another google account", self.login("google", id_token("google", "g-other", email="asha@example.test", email_verified=True), status=409))

    def test_untrusted_email_alone_creates_a_user_without_it(self):
        user = self.user_id(self.login("google", id_token("google", "g-anon", email="anon@example.test", email_verified=False)))
        self.assertEqual(fetch(self.url, "SELECT email, oidc_google FROM users WHERE id = $1", user), [{"email": None, "oidc_google": "g-anon"}])

    def test_refusals(self):
        self.assertIn("tenant", self.login("microsoft", id_token("microsoft", "m-x", tid="other", iss="https://login.microsoftonline.com/other/v2.0"), status=401))
        self.assertIn("Audience", self.login("google", id_token("google", "g-x", aud="other-app"), status=401))
        self.assertEqual(self.client.post("/auth/login-oidc", json={"provider": "okta", "id_token": id_token("google", "g-x"), "role": 5}).status_code, 400)
        self.assertEqual(self.client.post("/auth/login-google", json={"google_token": "x", "role": 5}).status_code, 404, "the old route is gone")

    def test_two_factor_still_applies(self):
        tokens = self.login("google", id_token("google", "g-2fa", email="twofa@example.test", email_verified=True))
        user = self.user_id(tokens)
        self.client.post("/my/totp-setup", headers={"Authorization": "Bearer " + tokens["access_token"]})
        fetch(self.url, "UPDATE users SET totp_enabled_at = now() WHERE id = $1", user)
        self.assertEqual(set(self.login("google", id_token("google", "g-2fa"))), {"mfa_required", "mfa_token"})


if __name__ == "__main__":
    unittest.main()
