"""API keys end to end: create, use on a route whose auth has api_key, scopes, expiry, owner checks, delete.

Same real-app boot as test_http.py (support.app_start), against a throwaway database.
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
class ApiKeyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.handle = app_start(env={"config_postgres_url_master": cls.url})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        cls.app.state.config_api["/my/profile"]["auth"] = ["jwt", "api_key"]    # a project opts a route in from config_extend.py
        cls.app.state.config_api["/my/object-read"]["auth"] = ["jwt", "api_key"]
        cls.app.state.config_api["/my/api-key-create"]["rate_limit"] = {"mode": "inmemory", "limit": 1000, "window_sec": 60}    # the limit test makes more keys than the 10 a minute allowed
        cls.admin = app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})
        cls.alice = app_login(cls.client, path="/auth/signup-username-password", body={"role": 5, "username": "alice", "password": "alice-pass"})
        cls.alice_id = cls.client.get("/my/profile", headers=cls.bearer(cls.alice)).json()["message"]["id"]

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def setUp(self):
        self.app.state.cache_token.clear()

    @staticmethod
    def bearer(token):
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def apikey(key):
        return {"Authorization": f"Bearer {key}"}

    def message(self, response, status=200):
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def create(self, **body):
        return self.message(self.client.post("/my/api-key-create", json={"name": "test", **body}, headers=self.bearer(self.alice)))

    def test_key_acts_as_its_owner_and_only_its_hash_is_stored(self):
        created = self.create(name="script")
        self.assertTrue(created["key"].startswith("atk_"))
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.apikey(created["key"])))["id"], self.alice_id)
        [row] = fetch(self.url, "SELECT key_hash, key_prefix, created_by_id FROM api_key WHERE id=$1", created["id"])
        self.assertNotEqual(row["key_hash"], created["key"])
        self.assertEqual((row["key_prefix"], row["created_by_id"]), (created["key"][:12], self.alice_id))
        listed = self.message(self.client.get("/my/object-read", params={"table": "api_key"}, headers=self.bearer(self.alice)))["obj_list"]    # the generic read lists the owner's keys, never the hash
        self.assertIn(created["id"], [k["id"] for k in listed])
        self.assertNotIn("key_hash", listed[0])

    def test_route_without_api_key_in_auth_refuses_a_key(self):
        key = self.create()["key"]
        for method, path in (("post", "/my/api-key-create"), ("post", "/my/token-refresh"), ("get", "/admin/object-read")):
            with self.subTest(path=path):
                self.assertEqual(self.message(getattr(self.client, method)(path, headers=self.apikey(key)), 401), "api_key not allowed on this route")

    def test_scopes_limit_the_key_and_must_name_api_key_routes(self):
        key = self.create(scopes=["/my/object-read"])["key"]
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.apikey(key)), 403), "api key scopes do not include this route")
        self.message(self.client.get("/my/object-read", params={"table": "test"}, headers=self.apikey(key)))
        self.assertIn("auth has api_key", self.message(self.client.post("/my/api-key-create", json={"name": "x", "scopes": ["/admin/object-read"]}, headers=self.bearer(self.alice)), 400))

    def test_unknown_expired_and_inactive_owner_are_401(self):
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.apikey("atk_unknown")), 401), "api key invalid or expired")
        expired = "atk_expired-test-key"    # api_key refuses UPDATE, so an expired row is inserted as such
        fetch(self.url, "INSERT INTO api_key (created_by_id, name, key_hash, key_prefix, expires_at) VALUES ($1, 'old', encode(sha256($2::bytea), 'hex'), 'atk_expired', now() - interval '1 second')", self.alice_id, expired.encode())
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.apikey(expired)), 401), "api key invalid or expired")
        bob = app_login(self.client, path="/auth/signup-username-password", body={"role": 5, "username": "bob", "password": "bob-pass"})
        bob_key = self.message(self.client.post("/my/api-key-create", json={"name": "b"}, headers=self.bearer(bob)))["key"]
        fetch(self.url, "UPDATE users SET deactivated_at=now() WHERE username='bob'")
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.apikey(bob_key)), 401), "api key owner is deleted or deactivated")

    def test_generic_delete_own_key_and_admin_delete_any(self):
        own, other = self.create(), self.create()
        self.app.state.config_api_key_cache_sec = 0    # no cache: a deleted key stops on the next request
        try:
            self.message(self.client.post("/my/object-delete", json={"table": "api_key", "ids": [own["id"]]}, headers=self.bearer(self.alice)))
            self.assertEqual(self.client.get("/my/profile", headers=self.apikey(own["key"])).status_code, 401)
            self.message(self.client.post("/admin/object-delete", json={"table": "api_key", "ids": [other["id"]]}, headers=self.bearer(self.admin)))
            self.assertEqual(self.client.get("/my/profile", headers=self.apikey(other["key"])).status_code, 401)
        finally: self.app.state.config_api_key_cache_sec = 60

    def test_others_cannot_delete_and_nobody_can_create_or_update_through_generic_routes(self):
        created = self.create()
        carol = app_login(self.client, path="/auth/signup-username-password", body={"role": 5, "username": "carol", "password": "carol-pass"})
        self.assertEqual(self.message(self.client.post("/my/object-delete", json={"table": "api_key", "ids": [created["id"]]}, headers=self.bearer(carol))), "0 ids deleted")
        self.assertEqual(self.client.post("/my/object-create", params={"table": "api_key"}, json={"name": "x", "key_hash": "h", "key_prefix": "p"}, headers=self.bearer(self.alice)).status_code, 400)
        updated = self.client.put("/my/object-update", params={"table": "api_key"}, json={"id": created["id"], "name": "renamed"}, headers=self.bearer(self.alice))
        self.assertNotEqual(updated.status_code, 200, updated.text)    # the database refuses every UPDATE of api_key
        self.assertEqual(fetch(self.url, "SELECT name FROM api_key WHERE id=$1", created["id"]), [{"name": "test"}])

    def test_key_limit_per_user(self):
        fetch(self.url, "DELETE FROM api_key WHERE created_by_id=$1", self.alice_id)
        for _ in range(self.app.state.config_api_key_max): self.create()
        self.assertIn("limit reached", self.message(self.client.post("/my/api-key-create", json={"name": "x"}, headers=self.bearer(self.alice)), 400))
        fetch(self.url, "DELETE FROM api_key WHERE created_by_id=$1", self.alice_id)


if __name__ == "__main__":
    unittest.main()
