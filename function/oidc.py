# import
import re
import time
from typing import Any
import asyncpg
import jwt
from .auth import func_auth_check_signup_role
from .auth import func_auth_check_user_active
from .middleware import func_api_error

# function
def func_oidc_provider_check(*, name: str, provider: Any) -> None:
    """Stop startup on a bad config_oidc_provider entry: a lowercase name (it names the users column oidc_<name>), issuers (the first an https URL), a client_id, optional https jwks_uri (required with a {tenantid} issuer), tenants only with such an issuer, link_email true or false."""
    where = f"config_oidc_provider[{name!r}]"
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", name): raise ValueError(f"{where}: the name must be lowercase a-z, 0-9 or _ (it names the users column oidc_<name>)")
    if not isinstance(provider, dict): raise ValueError(f"{where}: must be a dict")
    if unknown := set(provider) - {"issuer", "client_id", "jwks_uri", "tenants", "link_email"}: raise ValueError(f"{where}: unknown keys {sorted(unknown)}")
    issuers = provider.get("issuer") if isinstance(provider.get("issuer"), (list, tuple)) else [provider.get("issuer")]
    client_ids = provider.get("client_id") if isinstance(provider.get("client_id"), (list, tuple)) else [provider.get("client_id")]
    if not all(isinstance(i, str) and i for i in issuers) or not issuers[0].startswith("https://"): raise ValueError(f"{where}: issuer must be an https URL, or a list of the values the provider puts in iss with an https URL first (discovery reads it)")
    if not all(isinstance(c, str) and c for c in client_ids): raise ValueError(f"{where}: client_id must be a text or a list of texts")
    if provider.get("jwks_uri") is not None and not str(provider["jwks_uri"]).startswith("https://"): raise ValueError(f"{where}: jwks_uri must be an https URL")
    is_template = any("{tenantid}" in i for i in issuers)
    if is_template and not provider.get("jwks_uri"): raise ValueError(f"{where}: an issuer with {{tenantid}} needs jwks_uri")
    if provider.get("tenants") is not None and (not is_template or not isinstance(provider["tenants"], (list, tuple)) or not all(isinstance(t, str) and t for t in provider["tenants"])): raise ValueError(f"{where}: tenants is a list of tenant ids, used with an issuer that has {{tenantid}}")
    if provider.get("link_email") not in (None, True, False): raise ValueError(f"{where}: link_email must be true or false")

def func_oidc_config_apply(*, values: dict) -> None:
    """Check config_oidc_provider and give each provider its users column oidc_<name> (the provider's sub, unique per role), blocked for the user's own and permission edits like the other login columns."""
    providers = values.get("config_oidc_provider") or {}
    if not isinstance(providers, dict): raise ValueError("config_oidc_provider must be a dict of provider name to settings")
    for name, provider in providers.items(): func_oidc_provider_check(name=name, provider=provider)
    postgres = values.get("config_postgres_schema_master")
    if not providers or not isinstance(postgres, dict) or not isinstance(postgres.get("table", {}).get("users"), dict): return
    users = list(postgres["table"]["users"].get("column") or [])
    names = {c.get("name") for c in users}
    columns = [f"oidc_{name}" for name in providers if f"oidc_{name}" not in names]
    users += [{"name": c, "datatype": "text", "unique": f"{c},role"} for c in columns]
    values["config_postgres_schema_master"] = {**postgres, "table": {**postgres["table"], "users": {**postgres["table"]["users"], "column": users}}}
    for key in ("config_column_users_my_blocked",):
        if isinstance(values.get(key), (list, tuple)): values[key] = [*values[key], *(c for c in [f"oidc_{name}" for name in providers] if c not in values[key])]

async def func_oidc_keys(*, client_http: Any, cache_oidc: dict, provider: dict, kid: str | None) -> list:
    """The provider's signing keys (PyJWK), from its jwks_uri or from the first issuer's /.well-known/openid-configuration; cached an hour, fetched again (at most once a minute) when the token's key id is unknown."""
    issuer = provider["issuer"][0] if isinstance(provider["issuer"], (list, tuple)) else provider["issuer"]
    now = time.time()
    jwks_uri = provider.get("jwks_uri") or (cache_oidc.get(("discovery", issuer)) or {}).get("value")
    if not jwks_uri:
        response = await client_http.get(issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=10)
        response.raise_for_status()
        jwks_uri = response.json().get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri.startswith("https://"): raise func_api_error(message=f"oidc discovery of {issuer} has no https jwks_uri", status_code=502)
        cache_oidc[("discovery", issuer)] = {"value": jwks_uri, "at": now}
    cached = cache_oidc.get(("jwks", jwks_uri))
    is_stale = not cached or now - cached["at"] > 3600 or (kid and kid not in {k.key_id for k in cached["value"]} and now - cached["at"] > 60)
    if is_stale:
        response = await client_http.get(jwks_uri, timeout=10)
        response.raise_for_status()
        cached = cache_oidc[("jwks", jwks_uri)] = {"value": jwt.PyJWKSet.from_dict(response.json()).keys, "at": now}
    return cached["value"]

async def func_oidc_verify(*, client_http: Any, cache_oidc: dict, provider: dict, id_token: str, nonce: str | None = None) -> dict:
    """The claims of an ID token the provider signed for this app: signature (asymmetric algorithms only), aud (one of client_id), iss (or a {tenantid} issuer with the token's tid, in tenants when set), exp, iat, sub, and nonce when the page sent one. 401 otherwise."""
    def invalid(reason): return func_api_error(message=f"oidc token invalid: {reason}", status_code=401)
    try: header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError: raise invalid("not a JWT") from None
    if header.get("alg") not in ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"): raise invalid(f"algorithm {header.get('alg')} not allowed")
    keys = await func_oidc_keys(client_http=client_http, cache_oidc=cache_oidc, provider=provider, kid=header.get("kid"))
    key = next((k for k in keys if k.key_id == header.get("kid")), None) if header.get("kid") else (keys[0] if len(keys) == 1 else None)
    if not key: raise invalid("signing key not found")
    client_ids = list(provider["client_id"]) if isinstance(provider["client_id"], (list, tuple)) else [provider["client_id"]]
    try: claims = jwt.decode(id_token, key=key.key, algorithms=[header["alg"]], audience=client_ids, leeway=60, options={"require": ["iss", "sub", "aud", "exp", "iat"], "verify_iss": False})
    except jwt.PyJWTError as e: raise invalid(str(e)) from None
    issuers = provider["issuer"] if isinstance(provider["issuer"], (list, tuple)) else [provider["issuer"]]
    tid = claims.get("tid")
    is_issuer = any(claims["iss"] == (i.replace("{tenantid}", str(tid)) if "{tenantid}" in i and tid else i) for i in issuers)
    if not is_issuer: raise invalid(f"issuer {claims['iss']} not allowed")
    if provider.get("tenants") and tid not in provider["tenants"]: raise invalid(f"tenant {tid} not allowed")
    if nonce is not None and claims.get("nonce") != nonce: raise invalid("nonce does not match")
    if not isinstance(claims["sub"], str) or not 0 < len(claims["sub"]) <= 255: raise invalid("sub")
    return claims

async def func_auth_oidc_user(*, client_postgres: asyncpg.Pool | None, name: str, provider: dict, claims: dict, role: int, source: int = None, config_signup_allowed_roles: list = None) -> dict:
    """The user of a verified OIDC sign-in: found by oidc_<name> (the token's sub) and role; else the user with the same email and role, now linked, when the email can be trusted (email_verified, or link_email for the provider); else a new user (signup policy applies). An untrusted email that another user has is refused."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    column, sub = f"oidc_{name}", claims["sub"]
    email = str(claims.get("email") or "").strip().lower() or None
    if email and "@" not in email: email = None
    is_email_trusted = bool(email) and (claims.get("email_verified") is True or provider.get("link_email") is True)
    async with client_postgres.acquire() as conn, conn.transaction():
        user = await conn.fetchrow(f'SELECT * FROM users WHERE "{column}"=$1 AND role=$2 ORDER BY id DESC LIMIT 1;', sub, role)  # noqa: S608 - column from a checked provider name
        if not user and email and (same := await conn.fetchrow('SELECT * FROM users WHERE lower("email")=$1 AND role=$2 ORDER BY id DESC LIMIT 1;', email, role)):
            if not is_email_trusted: raise func_api_error(message="email already used: log in with it first", status_code=409)
            if same[column] is not None: raise func_api_error(message=f"email already linked to another {name} account", status_code=409)
            func_auth_check_user_active(user=dict(same))
            user = await conn.fetchrow(f'UPDATE users SET "{column}"=$1, name=coalesce(name, $2) WHERE id=$3 RETURNING *;', sub, claims.get("name"), same["id"])  # noqa: S608 - column from a checked provider name
        if user:
            func_auth_check_user_active(user=dict(user))
            return dict(user)
        func_auth_check_signup_role(role=role, config_signup_allowed_roles=config_signup_allowed_roles)
        user = await conn.fetchrow(f'INSERT INTO users (role, "{column}", email, name, source) VALUES ($1, $2, $3, $4, $5) RETURNING *;', role, sub, email if is_email_trusted else None, claims.get("name"), source)  # noqa: S608 - column from a checked provider name
        return dict(user)
