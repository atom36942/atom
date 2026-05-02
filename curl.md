# API Documentation (CURL)

This document provides a collection of `curl` commands for the available API endpoints. Use these as samples to integrate with the frontend.

> [!TIP]
> Use `baseurl` as a placeholder for the application host and `token` for the authorization header.

---

## Authentication

<details>
<summary><b>1. Sign Up (Username & Password)</b></summary>

```bash
curl -X POST "$baseurl/auth/signup-username-password" \
     -H "Content-Type: application/json" \
     -d '{
           "type": 1,
           "username": "sample_user",
           "password": "sample_password"
         }'
```
</details>

<details>
<summary><b>2. Login (Username & Password)</b></summary>

```bash
curl -X POST "$baseurl/auth/login-username-password" \
     -H "Content-Type: application/json" \
     -d '{
           "type": 1,
           "username": "sample_user",
           "password": "sample_password"
         }'
```
</details>
