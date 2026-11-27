# Single sign-on (OIDC)

Users log in with an account they already have at an identity provider (Google, Microsoft Entra ID, Okta, Auth0, Keycloak, Cognito, Apple, LinkedIn, GitLab, any OpenID Connect provider), with no Atom password. One route, `/auth/login-oidc`, serves every provider; adding a provider is a setting, not code. Off until `config_oidc_provider` has an entry. Backend only: a page adds the provider's button. Part of [auth](auth.md).

| Term | Meaning |
|---|---|
| ID token | A JWT the provider signs after the user signs in there (password and 2FA at the provider; Atom never sees them) |
| `sub` (subject) | The user's permanent ID at that provider: never changes, never reused. Atom keeps only this, in `users.oidc_<provider>` |
| `iss` (issuer) | Who made the token, e.g. `https://accounts.google.com` |
| `aud` (audience) | Who the token is for: your app's `client_id` |
| `client_id` | Your app's public name at the provider. Not a secret (it is in every login URL), but per deployment, so it goes in `.env` |
| JWKS | The provider's public signing keys, read from its `/.well-known/openid-configuration` |

## Turn it on

1. Register the app at the provider. Allow only your real origins (`https://app.example.com`), and use a separate `client_id` with `http://localhost:<port>` for local work: the provider gives tokens only to registered origins, so nobody else's site can use your `client_id`.
2. Add the provider to `.env` (JSON on one line) and restart:
   ```
   config_oidc_provider={"google": {"issuer": ["https://accounts.google.com", "accounts.google.com"], "client_id": "123-abc.apps.googleusercontent.com"}, "microsoft": {"issuer": "https://login.microsoftonline.com/<tenant-id>/v2.0", "client_id": "<app-id>", "link_email": true}}
   ```

| Key | Required | Meaning |
|---|---|---|
| name (the dict key) | yes | Lowercase `a-z0-9_`; names the users column `oidc_<name>` |
| `issuer` | yes | The `iss` the provider sends, or a list of them (the first an https URL: discovery reads it). `{tenantid}` in it accepts any tenant's issuer (Microsoft multi-tenant) |
| `client_id` | yes | Text, or a list (web and mobile apps) |
| `jwks_uri` | with `{tenantid}` | The key set URL, skipping discovery (Microsoft multi-tenant: `https://login.microsoftonline.com/common/discovery/v2.0/keys`) |
| `tenants` | no | With `{tenantid}`: only these tenant ids (`tid`) |
| `link_email` | no | `true`: trust the token's email to link an existing user even without `email_verified` (your own Microsoft tenant) |

Startup refuses a bad entry. `/info` returns `oidc_provider` (`{name: {issuer, client_id}}`) so a page draws one button per provider.

## Flow

| Step | Who | What |
|---|---|---|
| 1 | Page | Reads `oidc_provider` from `/info`; the provider's JS library (Google Identity Services, MSAL, ...) signs the user in and returns the ID token |
| 2 | Page → Atom | `POST /auth/login-oidc {"provider": "google", "id_token": "eyJ...", "role": 2, "nonce": "..."}` (`nonce` and `source` optional) |
| 3 | Atom | Checks the signature with the provider's key (asymmetric algorithms only; keys cached an hour), `aud`, `iss` (and tenant), `exp`, and `nonce` when sent. Any failure: 401 `oidc token invalid: ...` |
| 4 | Atom | Finds or links or creates the user (below), then the usual finish: 2FA if the user has it, else the tokens |

## Which user

| Case | Result |
|---|---|
| A user has `oidc_<provider>` = `sub` and this role | That user |
| Else a user has the token's email and this role, and the email is trusted (`email_verified: true`, or `link_email`) | Linked: `oidc_<provider>` set on that user |
| Else the email is not trusted but another user has it | 409 `email already used: log in with it first` |
| Else that user is already linked to another account of this provider | 409 `email already linked to another <provider> account` |
| Else | New user (signup rules: `config_signup_allowed_roles`) with `oidc_<provider>`, `name`, and the email only when trusted |

So one person can log in with email OTP, Google and Microsoft and always reach the same user. Each role is its own user, as for every login.

## Columns in `users`

| Column | Holds |
|---|---|
| `oidc_<name>` | That provider's `sub`, unique per role; added at startup for each provider; blocked for `/my/user-update` |
| `email`, `name` | Filled from the token only for a new user (`name` also when empty at linking) |

Nothing else from the token is stored. `oidc_google` is always there: it is the old `google_login_id`, renamed with its data in 19.0.0.

## Not covered
- Providers without ID tokens (GitHub, X, classic Facebook login): they give only an access token, which Atom cannot prove was issued to this app. A project adds its own route for one.
- SAML.
