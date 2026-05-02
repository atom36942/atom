# Auth Endpoints

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

# My Endpoints

<details>
<summary><b>1. My Profile</b></summary>

```bash
curl -X GET "$baseurl/my/profile" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json"
```
</details>

<details>
<summary><b>2. My Token Refresh</b></summary>

```bash
curl -X POST "$baseurl/my/token-refresh" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json"
```
</details>

<details>
<summary><b>3. My Update Username</b></summary>

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
<summary><b>4. My Update Password</b></summary>

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
<summary><b>5. My Update Email</b></summary>

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
<summary><b>6. My Update Mobile</b></summary>

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

<details>
<summary><b>7. My Update Profile</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=users" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "name": "John Doe",
           "email_communication": "john@example.com",
           "mobile_communication": "9876543210",
           "country": "USA",
           "state": "New York",
           "city": "New York",
           "address": "123 Main St",
           "title": "Senior Software Engineer",
           "description": "Experienced developer with a passion for high-density architectures.",
           "dob": "1990-01-01",
           "gender": 1
         }'
```
</details>

<details>
<summary><b>8. My Delete Account</b></summary>

```bash
curl -X DELETE "$baseurl/my/account-delete?mode=soft" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json"
```
</details>

<details>
<summary><b>9. My Create Object</b></summary>

```bash
curl -X POST "$baseurl/my/object-create?table=test" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "Sample Title",
           "description": "Sample description for the test object."
         }'
```
</details>

<details>
<summary><b>10. My Read Objects</b></summary>

```bash
curl -X GET "$baseurl/my/object-read?table=test&title=ilike,%25sample%25&limit=10&page=1&order=id desc" \
     -H "Authorization: Bearer $token"
```
</details>

<details>
<summary><b>11. My Update Object</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=test" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "title": "Updated Title"
         }'
```
</details>

<details>
<summary><b>12. My Delete Objects</b></summary>

```bash
curl -X POST "$baseurl/my/ids-delete" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "table": "test",
           "ids": "1,2,3"
         }'
```
</details>

<details>
<summary><b>13. My Update Objects (Bulk)</b></summary>

```bash
curl -X PUT "$baseurl/my/object-update?table=test" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "obj_list": [
             { "id": 1, "title": "Bulk Update 1" },
             { "id": 2, "title": "Bulk Update 2" }
           ]
         }'
```
</details>

# Admin Endpoints

<details>
<summary><b>1. Admin Sync</b></summary>

```bash
curl -X GET "$baseurl/admin/sync" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json"
```
</details>

<details>
<summary><b>2. Admin Postgres Runner</b></summary>

```bash
curl -X POST "$baseurl/admin/postgres-runner" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "mode": "read",
           "query": "SELECT * FROM users LIMIT 10"
         }'
```
</details>

<details>
<summary><b>3. Admin Postgres Export</b></summary>

```bash
curl -X POST "$baseurl/admin/postgres-export" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "query": "SELECT * FROM users"
         }' --output users_export.csv
```
</details>

<details>
<summary><b>4. Admin Postgres Import (Create)</b></summary>

```bash
curl -X POST "$baseurl/admin/postgres-import" \
     -H "Authorization: Bearer $token" \
     -F "mode=create" \
     -F "table=test" \
     -F "file=@/path/to/your/file.csv" \
     -F "is_serialize=1"
```
</details>

<details>
<summary><b>5. Admin Create Object</b></summary>

```bash
curl -X POST "$baseurl/admin/object-create?table=test" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "title": "Admin Created Test",
           "category": "Documentation",
           "description": "A sample object created via the admin interface.",
           "price": 99.99
         }'
```
</details>

<details>
<summary><b>6. Admin Read Objects</b></summary>

```bash
curl -X GET "$baseurl/admin/object-read?table=test&limit=10&page=1&order=id desc" \
     -H "Authorization: Bearer $token"
```
</details>

<details>
<summary><b>7. Admin Update Object</b></summary>

```bash
curl -X PUT "$baseurl/admin/object-update?table=test" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "id": 1,
           "title": "Admin Updated Test Title"
         }'
```
</details>

<details>
<summary><b>8. Admin Delete Objects</b></summary>

```bash
curl -X POST "$baseurl/admin/ids-delete" \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{
           "table": "test",
           "ids": "1,2,3"
         }'
```
</details>
