# Authentication and Authorization

This document details the authentication flow, token management, and security lifecycle handled by Atom's monolithic `core/function.py` logic and `core/app.py` middleware.

## 1. Authentication Flow Overview

Atom relies on a stateless JWT (JSON Web Token) approach coupled with real-time or cached database checks to provide robust security without compromising API latency.

The typical login flow involves:
1. User provides credentials (Email/Password or requests an OTP).
2. The system verifies the credentials.
3. `func_token_encode` generates a signed JWT containing user identity and role.
4. The client provides this JWT in the `Authorization: Bearer <token>` header for subsequent requests.

---

## 2. OTP Generation and Verification

For passwordless login or Multi-Factor Authentication (MFA), Atom uses a time-limited One-Time Password (OTP) model.

### Generating an OTP
The `func_otp_generate` creates a secure random numeric pin and stores it in the database for the given email or mobile number.
```python
otp_code = await app_state.func_otp_generate(
    client_postgres_pool=app_state.client_postgres_pool,
    email="user@example.com",
    mobile=None,
    config_otp_length=6
)
# You would then pass this `otp_code` to the SES or SNS client to send to the user.
```

### Verifying an OTP
The `func_otp_verify` checks if the OTP provided by the user is valid and has not expired.
```python
# Will raise an exception if OTP is invalid, expired, or doesn't match the email/mobile
await app_state.func_otp_verify(
    client_postgres_pool=app_state.client_postgres_pool,
    otp=123456,
    email="user@example.com",
    mobile=None,
    config_expiry_sec_otp=300 # 5 minutes
)
```

---

## 3. JWT Token Encoding

Once a user's identity is proven, you encode their token using `func_token_encode`. This JWT contains the essential claims required for role-based access.

```python
token_data = await app_state.func_token_encode(
    user={"id": 1, "role": 1, "email": "admin@example.com"},
    config_token_secret_key=app_state.config_token_secret_key,
    config_token_expiry_sec=3600,         # Access token expires in 1 hour
    config_token_refresh_expiry_sec=86400, # Refresh token expires in 24 hours
    config_token_key=["id", "role"]        # Keys from the user dict to encode in the JWT
)

# Returns: {"token": "ey...", "refresh_token": "ey...", "token_expiry": 170...}
```

---

## 4. Password Hashing

Atom uses Argon2 for secure password hashing. The hasher is initialized in `core/app.py` globally as `client_password_hasher`. 

When inserting new users via `func_postgres_create` or `func_postgres_update`, if the `password` field is present and maps to a configured column, the database abstraction layer will automatically hash the plaintext password using this client before writing it to the database.

---

## 5. Global Security Middleware

Every incoming request passes through the `app.middleware("http")` in `core/app.py`. The middleware enforces security declaratively based on `config_api` inside `core/config.py`.

1. **`func_middleware_check_auth`**: Validates the JWT signature and expiration. Sets `request.state.user`.
2. **`func_middleware_check_user_role`**: Checks if the user's role integer is allowed to access the specific endpoint path.
3. **`func_middleware_check_user_deactivated`**: Ensures the user account is not suspended.
4. **`func_middleware_check_user_deleted`**: Ensures the user account is not soft-deleted.

By relying on the middleware and `config_api`, individual router functions remain clean and solely focused on business logic.
