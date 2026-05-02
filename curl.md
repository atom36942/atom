# Endpoints

<details>
<summary><b>1. Sign Up</b></summary>

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
<summary><b>2. Login</b></summary>

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

<details>
<summary><b>3. My Profile</b></summary>

```bash
curl -X GET "$baseurl/my/profile" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json"
```
</details>

<details>
<summary><b>4. My Update Username</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=users" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "username": "new_username"
         }'
```
</details>

<details>
<summary><b>5. My Update Password</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=users" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "password": "new_password"
         }'
```
</details>

<details>
<summary><b>6. My Update Email</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=users&otp=123456" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "email": "new_email@example.com"
         }'
```
</details>

<details>
<summary><b>7. My Update Mobile</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=users&otp=123456" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "mobile": "1234567890"
         }'
```
</details>
