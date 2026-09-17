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
- Size limit: Enforces `config_blob_limit_size_kb` (default 50MB per file).
- File count limit: Enforces `config_blob_limit_upload` (default 10 files per batch).

### B. Direct Client Upload via Presigned URLs (`POST /private/blob-upload-url`)
Offloads server bandwidth by generating temporary write URLs for direct client-to-bucket uploads:
```bash
curl -X POST "http://localhost:8000/private/blob-upload-url?service=s3&container=my-bucket&count=2"   -H "Authorization: Bearer <token>"
```
Returns presigned URLs valid for `config_blob_expire_sec_upload` seconds.

### C. Azure Container SAS (`POST /private/blob-container-sas`)
Issues short-lived Shared Access Signature (SAS) tokens for Azure Blob containers.

---

## 4. Secure Previews (`POST /private/blob-preview-urls`)

Generates temporary, signed read-only URLs to share private files without making buckets public:
```bash
curl -X POST "http://localhost:8000/private/blob-preview-urls"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{"file_urls": ["https://my-bucket.s3.amazonaws.com/files/doc.pdf"]}'
```
URLs expire automatically after `config_blob_expire_sec_preview` seconds.

---

## 5. Deletion & Cleanup

| Operation | Endpoint | Access Tier |
| :--- | :--- | :--- |
| **Delete Specific Files** | `POST /my/blob-delete-url` | Authenticated user (must own file) |
| **Delete All User Files** | `POST /my/blob-delete-all` | Authenticated user |
| **Admin Delete Any File** | `POST /admin/blob-delete-url` | Superadmin (`role: 1`) |
