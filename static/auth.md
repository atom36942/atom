# AI Prompt: Atom Framework Frontend Auth & Profile Implementation

**Task**: Generate a complete, production-ready frontend authentication and profile management module (e.g., React, Vue, or Vanilla JS) integrated with the Atom Framework backend.

---

## 1. Context & Core Rules
- **Backend Architecture**: RESTful API with JWT-based Bearer authentication.
- **State Persistence**: 
  - `localStorage.token`: Access JWT (short-lived).
  - `localStorage.token_refresh`: Refresh JWT (long-lived).
  - `localStorage.user`: JSON object for profile data (`username`, `name`, `country`).
  - `localStorage.login_time`: Unix timestamp of the last token acquisition.
- **Security Constraint**: Before *any* authenticated API hit, the frontend must check if the access token has expired.
- **Atomic Updates**: Profile updates support multiple fields, but password updates MUST be sent alone with only `id` and `password`.

---

## 2. API Specifications

### A. Authentication
- **Login**: `POST /auth/login-password-username`
  - Payload: `{ "type": 1, "username": "str", "password": "str" }`
  - Success: Store tokens, fetch profile, and redirect to dashboard.
- **Token Refresh**: `POST /my/token-refresh`
  - Path: `/my/token-refresh`
  - Header: `Authorization: Bearer <token_refresh>`
  - Success: Update `token`, `token_refresh`, and `login_time` in LocalStorage.

### B. Profile Management
- **Read Profile**: `GET /my/profile`
  - Header: `Authorization: Bearer <token>`
  - Action: Sync response to `localStorage.user`.
- **Update Profile**: `PUT /my/object-update?table=users`
  - Payload: `{ "id": int, "name": "str", "country": "str" }`
- **Update Password**: `PUT /my/object-update?table=users`
  - Payload: `{ "id": int, "password": "str" }`
  - *Must be a separate request from profile updates.*
- **Delete Account**: `DELETE /my/account-delete?mode=soft`
  - *Constraint*: Functional endpoint exists, but UI must currently intercept and show: `"Error: Account deletion not allowed in this environment"`.

---

## 3. Implementation Logic (State Machine)

### Token Expiry Check (Pre-Request)
For every request to a `/my/` or `/private/` route:
1. Calculate elapsed time: `elapsed = Date.now() - localStorage.login_time`.
2. Check if expired: `is_expired = elapsed > (localStorage.token_expiry_sec * 1000 - 60000)` (using a 60s safety buffer).
3. If `is_expired`, call `POST /my/token-refresh` first, update state, then proceed with the original request.

### Global Error Handling (Intercept)
If any API call returns `401 Unauthorized`:
1. Attempt `POST /my/token-refresh`.
2. If refresh succeeds, retry the original request.
3. If refresh fails with `401`, clear all `localStorage` and redirect to the login page.

### Logout Flow
1. Clear `token`, `token_refresh`, and `user` from `localStorage`.
2. Immediate redirect to `/`.

---

## 4. UI/UX Requirements
- **State Awareness**: UI components must react to `localStorage.user` changes.
- **Feedback**: Show toast notifications for "Session Renewed", "Profile Updated", and "Login Failed".
- **Loading States**: Disable forms and buttons during API calls.
- **Validation**:
  - Username: Regex `^(?=.{3,20}$)[a-z][a-z0-9_@-]*$`.
  - Password: Minimal 8 characters, no whitespace.

---

## 5. Output Expectation
Provided code should be:
1. **Clean**: Modularized API services/hooks.
2. **Robust**: Handled network failures and 500 errors gracefully.
3. **Type-Safe**: Use TypeScript interfaces for User and Token objects if applicable.
