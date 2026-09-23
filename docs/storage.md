# 🗄️ Object & Cloud Storage (S3 & Azure Blob)

Atom provides pluggable object storage across **AWS S3** (or S3-compatible APIs like MinIO) and **Azure Blob Storage** behind a single unified API.

---

## 1. Supported Storage Backends

| Backend | `service` Key | Required Configurations | Description |
| :--- | :--- | :--- | :--- |
| **AWS S3 / MinIO** | `s3` | `config_aws_access_key_id`, `config_aws_secret_access_key`, `config_aws_s3_region_name` | Industry-standard object storage. |
| **Azure Blob** | `azure` | `config_azure_blob_connection_string` | Microsoft Azure Blob container storage. |

Registry in `config.py`:
```python
config_blob_services = ["s3", "azure"]
```

---

## 2. Tracking in the `blob` Table

Every uploaded asset is recorded in PostgreSQL in the `blob` table (`config_postgres["table"]["blob"]`) to support auditing, ownership verification, and automatic cleanup:
- `created_by_id`: Owner user ID (derived from JWT token).
- `service`: `s3` or `azure`.
- `type`: `1` (direct file upload) or `2` (presigned URL).
- `file_url`: Permanent storage URL.
- `deleted_at`, `deleted_by_id`: Soft-delete markers.

---

## 3. Upload Methods

### A. Direct Server Upload (`POST /private/blob-upload-file`)
Streams multipart form files through the server to the cloud bucket:
```bash
curl -X POST "http://localhost:8000/private/blob-upload-file"   -H "Authorization: Bearer <token>"   -F "service=s3"   -F "container=my-bucket"   -F "file=@./invoice.pdf"
```
- Size limit: Enforces `config_blob_limit_size_kb` (default 500KB per file), reading at most the limit plus one byte into memory. Multipart parsing still happens before this check; configure request-body limits at your ingress.
- File count limit: Enforces `config_blob_limit_upload` (default 100 files per batch).

### B. Direct Client Upload via Presigned URLs (`POST /private/blob-upload-url`)
Offloads server bandwidth by generating temporary write URLs for direct client-to-bucket uploads:
```bash
curl -X POST "http://localhost:8000/private/blob-upload-url?service=s3&container=my-bucket&count=2"   -H "Authorization: Bearer <token>"
```
Returns presigned URLs valid for `config_blob_expire_sec_upload` seconds.

### C. Azure Container SAS (`POST /private/blob-container-sas`)
Issues Shared Access Signature (SAS) tokens for Azure Blob containers. This grants
container-wide read access, so the handler requires role `1`, checked against the
current database role. A stale admin claim in a token is insufficient.

---

## 4. Secure Previews (`POST /my/blob-preview-urls`)

Generates temporary, signed read-only URLs for the caller's `user_<id>/` files:
```bash
curl -X POST "http://localhost:8000/my/blob-preview-urls"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"service": "s3", "urls": ["https://my-bucket.s3.amazonaws.com/user_7/doc.pdf"]}'
```
URLs expire automatically after `config_blob_expire_sec_preview` seconds.

Send `Authorization: Bearer <access_token>` and a JSON body with two required
fields: `service` (`s3` or `azure`, subject to `config_blob_services`) and `urls`
(a list of stored file URLs for that service). No query parameters or user ID are
required; ownership comes from the authenticated user.

The response contains only signed preview URLs, in the exact request order.
`message[i]` corresponds to `urls[i]`; duplicates are preserved. Invalid or
unauthorized entries fail the entire request instead of being skipped. Signing
does not check whether an object exists in storage. Example with a shortened,
illustrative signature:

```json
{
  "status": 1,
  "message": [
    "https://my-bucket.s3.ap-south-1.amazonaws.com/user_7/doc.pdf?X-Amz-Signature=..."
  ]
}
```

An object outside the caller's prefix returns HTTP 400 with
`{"status": 0, "message": "blob preview allowed only for own files"}`.

Signed URLs are bearer credentials: anyone holding one can use it until expiry.
S3 upload policies include the configured size limit. Azure direct-upload SAS does
not apply Atom's server-side file-size check; use the server upload endpoint when
that limit must be enforced. Cloud account permissions must restrict which
buckets/containers Atom can access. File type and malware checks are application
policy and are not performed by these generic blob helpers.

---

## 5. Deletion & Cleanup

| Operation | Endpoint | Access Tier |
| :--- | :--- | :--- |
| **Delete Specific Files** | `POST /my/blob-delete-url` | Authenticated user (must own file) |
| **Delete All User Files** | `POST /my/blob-delete-all` | Authenticated user |
| **Admin Delete Any File** | `POST /admin/blob-delete-url` | Superadmin (`role: 1`) |
