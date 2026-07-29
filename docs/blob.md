# Blob Storage

Atom provides file storage over pluggable backends — **AWS S3** and **Azure Blob** — behind one API. Uploads can be done directly through the server or via presigned URLs, and every stored object is tracked in the `blob` table so it can be previewed and cleaned up.

Backends are chosen per-request with a `service` param, validated against `config_blob_services` (`["s3", "azure"]`). The relevant client (`client_s3` / `client_azure_blob`) must be configured (see the [README](../readme.md#configuration)) or the call errors.

Logic lives in `func_blob_*` functions in [`function.py`](../function.py); endpoints span `router/private.py`, `router/my.py`, and `router/admin.py`.

---

## The `blob` table

Every upload records a row (`config_postgres["table"]["blob"]`):

| Column | Meaning |
|--------|---------|
| `created_by_id` | Owner (from the token). |
| `type` | `1` = file, `2` = presigned URL (`config_column_int_mapping`). |
| `service` | `s3` or `azure`. |
| `file_url` | The stored object's URL. |
| `deleted_at` / `deleted_by_id` | Soft-delete markers. |

This ownership + soft-delete tracking is what powers per-user cleanup and the retention purge.

---

## Uploading

### Direct upload — `POST /private/blob-upload-file`
Multipart form: `service`, `container`, and one or more `file`s. The server streams the file(s) to the backend and records `blob` rows.

```bash
curl -X POST "http://localhost:8000/private/blob-upload-file" \
  -H "Authorization: Bearer <token>" \
  -F "service=s3" -F "container=my-bucket" -F "file=@./photo.jpg"
```

- Enforces `config_blob_limit_size_kb` (per file) and `config_blob_limit_upload` (file count).

### Presigned upload — `POST /private/blob-upload-url`
Query: `service`, `container`, `count`. Returns `count` presigned URLs the **client** uploads to directly (offloading bandwidth from the server). URLs expire after `config_blob_expire_sec_upload`.

### Azure container SAS — `POST /private/blob-container-sas`
Returns a short-lived SAS token for an Azure container (S3 is rejected — use presigned URLs there).

---

## Previewing — `POST /private/blob-preview-urls`
Given stored object URLs, returns time-limited **preview/read** URLs (`func_blob_preview_urls_get`), valid for `config_blob_expire_sec_preview`. Use these to show private files to a client without making the bucket public.

---

## Deleting

| Endpoint | Scope |
|----------|-------|
| `POST /my/blob-delete-url` | Delete specific URLs the caller owns. |
| `POST /my/blob-delete-all` | Delete all of the caller's blobs (batched, `func_blob_delete_all`). |
| `POST /admin/blob-delete-url` | Admin delete of any URLs (role 1). |

Deletes remove the object from the backend and mark the `blob` row deleted. Rows past `config_users_delete_data_retention_day` are purged from storage by the user-deletion worker (`script/worker_users_delete.py`) — see [workers.md](workers.md).

---

## Container admin (`/admin/*`)

- `GET /admin/blob-container-read` — list containers/buckets for a service (`func_blob_containers_read`).
- `POST /admin/blob-container-ops` — create/manage containers (`func_blob_container_ops`).

Both are role-restricted to admins.

---

## Choosing an upload path

| Use | When |
|-----|------|
| Direct (`blob-upload-file`) | Small files, server-side control, simplest client. |
| Presigned (`blob-upload-url`) | Large files or high volume — client uploads straight to storage. |
| SAS (Azure) | Client needs scoped, time-boxed container access. |

---

📚 [Back to README](../readme.md)
