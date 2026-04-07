# Auth & Profile Frontend Flow Description

This document describes the authentication and profile management flow for the frontend developer.

## Global Configuration
- **Authorization Header**: `Authorization: Bearer <token>`
- **LocalStorage (LS) Keys**:
  - `token`: Access JWT token.
  - `token_refresh`: Refresh JWT token.
  - `user`: User profile data (JSON object).

---

## 1. Login Module
- **Endpoint**: `POST /auth/login-password-username`
- **Request Body**:
  ```json
  {
    "type": 1, 
    "username": "user123",
    "password": "password123"
  }
  ```
- **Flow**:
  1. User submits login form.
  2. On success, store `token` and `token_refresh` in LocalStorage.
  3. Fetch full profile and store in `user` LS key (see Profile Read).
  4. Trigger redirect to the "My Profile" dashboard.

---

## 2. My Profile Module
- **Endpoint**: `GET /my/profile`
- **Trigger**: Page open, page refresh, or after successful login.
- **Flow**:
  1. Fetch profile using active `token`.
  2. Map only `username`, `name`, and `country` to the `user` LocalStorage object.
  3. Update UI to display the mapped fields.

---

## 3. Token Refresh Module
- **Endpoint**: `POST /my/token-refresh`
- **Trigger**: Check `exp` of the current `token`. If close to expiry or on 401 response, trigger refresh.
- **Flow**:
  1. Send request with `token_refresh` in Authorization header.
  2. Replace `token` and `token_refresh` in LocalStorage with the new values.
  3. Retry the failed request if triggered by a 401.

---

## 4. Logout Module
- **Trigger**: User clicks logout button.
- **Flow**:
  1. Clear all LocalStorage keys (`token`, `token_refresh`, `user`).
  2. Redirect the user to the homepage (`/`).

---

## 5. My Profile Update Module
- **Endpoint**: `PUT /my/object-update?table=users`
- **Request Body**:
  ```json
  {
    "id": 123,
    "name": "New Name",
    "country": "New Country"
  }
  ```
- **Flow**:
  1. On success, update the `user` LocalStorage object with new values.
  2. Sync UI to reflect the changes.

---

## 6. Update Password Module
- **Endpoint**: `PUT /my/object-update?table=users`
- **Constraint**: Must only send `id` and `password` (single column update rule).
- **Request Body**:
  ```json
  {
    "id": 123,
    "password": "newpassword123"
  }
  ```
- **Flow**:
  1. Standard update request.
  2. No changes required to `user` LS object.

---

## 7. Account Delete Module
- **Endpoint**: `DELETE /my/account-delete?mode=soft`
- **Flow**:
  1. Spec: Currently, this action should show an error message (Account deletion disabled). 
  2. Frontend should display: "Error: Account deletion not allowed in this environment".

---

---

## Token Lifecycle & Refresh Strategy

### 1. Token Types
- **Access Token (`token`)**: Short-lived (e.g. 3 days). Sent with every authenticated request in the `Authorization: Bearer <token>` header.
- **Refresh Token (`token_refresh`)**: Long-lived (e.g. 300 days). Specifically used to generate new access/refresh tokens.

### 2. Expiry Management
On successful login or profile fetch, the backend provides `token_expiry_sec` (for the access token) and `token_refresh_expiry_sec` (for the refresh token).

**Frontend Implementation**:
- Store the `login_time` (timestamp) when tokens are received.
- **Pre-request Check**: Before every API call, the frontend should calculate if the current `token` is valid:
  ```javascript
  const isExpired = (Date.now() - login_time) > (token_expiry_sec * 1000 - 60000); // 60s buffer
  ```
- If `isExpired` is true, pause the outgoing request and trigger the **Token Refresh Flow**.

### 3. Token Refresh Flow
1. **Request**: Call `POST /my/token-refresh`.
2. **Authentication**: Use the `token_refresh` in the Bearer header (`Authorization: Bearer <token_refresh>`).
3. **Response**: Receive new `token`, `token_refresh`, and updated expiry values.
4. **Resync**: Update LocalStorage with new values and a fresh `login_time`.
5. **Resume**: Proceed with the original pending API request using the new access `token`.

### 4. Fallback: 401 Unauthorized
Even with pre-checks, a request might fail with a `401 Unauthorized` (e.g., if the user changed their password or the token was revoked).
- If an API returns `401`, the frontend should attempt one **Token Refresh Flow**.
- If the refresh also fails with `401`, the user session is officially dead. Clear LocalStorage and redirect to Login.

---

## Audit Checklist
- [ ] Verify `type` code for login matches the deployment environment (default `1`).
- [ ] Ensure JWT expiration logic handles background/inactive tabs.
- [ ] Confirm table name `users` is used for all `/my/object-update` calls relating to profiles.

