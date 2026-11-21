"""OIDC building blocks: the provider settings check, the users column per provider, and ID token verification against a local signing key (no network)."""
import asyncio
import time
import unittest

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import rsa

import config
from function import func_oidc_config_apply
from function import func_oidc_provider_check
from function import func_oidc_verify

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EC_KEY = ec.generate_private_key(ec.SECP256R1())
ISSUER = "https://idp.test"
JWKS_URI = "https://idp.test/keys"
PROVIDER = {"issuer": ISSUER, "client_id": "app-1"}


def jwk(key, kid, alg):
    algorithm = jwt.algorithms.RSAAlgorithm if alg.startswith("RS") else jwt.algorithms.ECAlgorithm
    return {**algorithm.to_jwk(key.public_key(), as_dict=True), "kid": kid, "alg": alg, "use": "sig"}


def token(claims=None, key=KEY, kid="k1", alg="RS256", **override):
    now = int(time.time())
    body = {"iss": ISSUER, "aud": "app-1", "sub": "user-1", "iat": now, "exp": now + 300, "email": "ravi@x.com", "email_verified": True, **(claims or {})}
    for name, value in override.items():
        if value is None: body.pop(name, None)
        else: body[name] = value
    return jwt.encode(body, key, algorithm=alg, headers={"kid": kid})


class Http:
    """client_http stand-in: serves discovery and the key set, and counts requests."""
    def __init__(self, keys):
        self.keys, self.urls = keys, []
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(self.handle))

    def handle(self, request):
        self.urls.append(str(request.url))
        if str(request.url) == ISSUER + "/.well-known/openid-configuration": return httpx.Response(200, json={"issuer": ISSUER, "jwks_uri": JWKS_URI})
        if str(request.url) == JWKS_URI: return httpx.Response(200, json={"keys": self.keys})
        return httpx.Response(404)

    async def get(self, url, **kwargs): return await self.client.get(url, **kwargs)


def verify(http, id_token, provider=PROVIDER, cache=None, nonce=None):
    return asyncio.run(func_oidc_verify(client_http=http, cache_oidc={} if cache is None else cache, provider=provider, id_token=id_token, nonce=nonce))


class ProviderCheckTests(unittest.TestCase):
    def test_good_entries_pass(self):
        func_oidc_provider_check(name="google", provider={"issuer": ["https://accounts.google.com", "accounts.google.com"], "client_id": "g"})
        func_oidc_provider_check(name="microsoft", provider={"issuer": "https://login.microsoftonline.com/{tenantid}/v2.0", "client_id": ["web", "mobile"], "jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys", "tenants": ["t1"], "link_email": True})

    def test_bad_entries_stop_startup(self):
        for label, name, provider, message in (
            ("upper-case name", "Google", PROVIDER, "lowercase"),
            ("unknown key", "x", {**PROVIDER, "secret": "s"}, "unknown keys"),
            ("http issuer", "x", {**PROVIDER, "issuer": "http://idp.test"}, "issuer"),
            ("no client_id", "x", {"issuer": ISSUER}, "client_id"),
            ("template without jwks_uri", "x", {**PROVIDER, "issuer": "https://idp.test/{tenantid}"}, "needs jwks_uri"),
            ("tenants without template", "x", {**PROVIDER, "tenants": ["t1"]}, "tenants"),
            ("link_email not a bool", "x", {**PROVIDER, "link_email": "yes"}, "link_email"),
        ):
            with self.subTest(label), self.assertRaisesRegex(ValueError, message): func_oidc_provider_check(name=name, provider=provider)

    def test_each_provider_gets_its_users_column_blocked_for_own_edits(self):
        values = {"config_oidc_provider": {"google": PROVIDER, "okta": PROVIDER}, "config_postgres": config.config_postgres, "config_column_users_my_blocked": list(config.config_column_users_my_blocked), "config_permission_user_column_blocked": list(config.config_permission_user_column_blocked)}
        func_oidc_config_apply(values=values)
        columns = [c for c in values["config_postgres"]["table"]["users"] if c["name"].startswith("oidc_")]
        self.assertEqual(columns, [{"name": "oidc_google", "datatype": "text", "old": "google_login_id", "unique": "oidc_google,role"}, {"name": "oidc_okta", "datatype": "text", "unique": "oidc_okta,role"}])
        for key in ("config_column_users_my_blocked", "config_permission_user_column_blocked"):
            with self.subTest(key): self.assertEqual([c for c in values[key] if c.startswith("oidc_")], ["oidc_google", "oidc_okta"])
        self.assertNotIn("oidc_okta", [c["name"] for c in config.config_postgres["table"]["users"]], "config.py itself is not changed")


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.http = Http([jwk(KEY, "k1", "RS256"), jwk(EC_KEY, "e1", "ES256")])

    def test_a_good_token_gives_its_claims_and_discovery_is_cached(self):
        cache = {}
        self.assertEqual(verify(self.http, token(), cache=cache)["sub"], "user-1")
        self.assertEqual(verify(self.http, token(key=EC_KEY, kid="e1", alg="ES256"), cache=cache)["sub"], "user-1")
        self.assertEqual(self.http.urls, [ISSUER + "/.well-known/openid-configuration", JWKS_URI], "discovery and keys fetched once")

    def test_refusals(self):
        for label, id_token, message in (
            ("other audience", token(aud="other-app"), "Audience"),
            ("other issuer", token(iss="https://evil.test"), "issuer"),
            ("expired", token(exp=int(time.time()) - 3600), "expired"),
            ("no sub", token(sub=None), "sub"),
            ("signed by another key", token(key=OTHER_KEY), "Signature"),
            ("unknown key id", token(kid="k9"), "signing key not found"),
            ("symmetric algorithm", jwt.encode({"iss": ISSUER}, "x" * 32, algorithm="HS256", headers={"kid": "k1"}), "algorithm HS256"),
            ("not a JWT", "abc", "not a JWT"),
        ):
            with self.subTest(label), self.assertRaisesRegex(Exception, message) as caught: verify(self.http, id_token)
            self.assertEqual(caught.exception.status_code, 401)

    def test_nonce_must_match_when_sent(self):
        self.assertEqual(verify(self.http, token({"nonce": "n1"}), nonce="n1")["nonce"], "n1")
        with self.assertRaisesRegex(Exception, "nonce"): verify(self.http, token({"nonce": "n1"}), nonce="n2")

    def test_several_client_ids_and_issuer_spellings(self):
        provider = {"issuer": [ISSUER, "idp.test"], "client_id": ["web", "app-1"]}
        self.assertEqual(verify(self.http, token(iss="idp.test"), provider=provider)["sub"], "user-1")

    def test_tenant_issuer_and_allowed_tenants(self):
        provider = {"issuer": "https://idp.test/{tenantid}/v2.0", "client_id": "app-1", "jwks_uri": JWKS_URI, "tenants": ["t1"]}
        cache = {}
        self.assertEqual(verify(self.http, token({"tid": "t1"}, iss="https://idp.test/t1/v2.0"), provider=provider, cache=cache)["tid"], "t1")
        with self.assertRaisesRegex(Exception, "tenant t2 not allowed"): verify(self.http, token({"tid": "t2"}, iss="https://idp.test/t2/v2.0"), provider=provider, cache=cache)
        with self.assertRaisesRegex(Exception, "issuer"): verify(self.http, token({"tid": "t1"}, iss="https://idp.test/t2/v2.0"), provider=provider, cache=cache)
        self.assertEqual(self.http.urls, [JWKS_URI], "jwks_uri skips discovery")

    def test_a_new_key_id_fetches_the_keys_again_at_most_once_a_minute(self):
        cache = {}
        verify(self.http, token(), cache=cache)
        self.http.keys.append(jwk(OTHER_KEY, "k2", "RS256"))
        with self.assertRaisesRegex(Exception, "signing key not found"): verify(self.http, token(key=OTHER_KEY, kid="k2"), cache=cache)
        cache[("jwks", JWKS_URI)]["at"] -= 61
        self.assertEqual(verify(self.http, token(key=OTHER_KEY, kid="k2"), cache=cache)["sub"], "user-1")


if __name__ == "__main__":
    unittest.main()
